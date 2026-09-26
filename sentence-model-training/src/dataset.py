"""
PyTorch Dataset and Dynamic Batch Collation for Continuous ISL.
Supports variable-length keypoint sequences and English word-token targets from CSV or JSON annotations.

Terminology Note:
The available sentence annotations are English transcript tokens used as sequence
targets for CTC training. They are not manually annotated ISL glosses.
"""

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch
from torch.utils.data import Dataset

from .vocabulary import GlossVocabulary, tokenize_english_transcript, tokenize_gloss_sequence

logger = logging.getLogger(__name__)


def check_ctc_validity(input_length: int, target_length: int, sample_id: Optional[str] = None) -> bool:
    """
    Validates the CTC mathematical constraint: input sequence length >= target sequence length.
    
    CTC alignment requires at least as many temporal frames as output tokens.
    """
    if target_length > input_length:
        sample_info = f" for sample '{sample_id}'" if sample_id else ""
        logger.warning(
            f"CTC constraint violation{sample_info}: "
            f"target length ({target_length}) exceeds input frame length ({input_length})."
        )
        return False
    return True


def resolve_keypoint_path(
    keypoints_dir: Path,
    uid: str,
    pattern: str = "{uid}.npy",
) -> Path:
    """
    Resolves the keypoint file path for a given UID using a configurable pattern.
    
    If the specified pattern doesn't exist, checks standard fallbacks (.npz, .npy).
    """
    candidate = keypoints_dir / pattern.format(uid=uid)
    if candidate.exists():
        return candidate

    # Fallback checks
    fallbacks = [
        keypoints_dir / f"{uid}.npy",
        keypoints_dir / f"{uid}.npz",
        keypoints_dir / f"{uid}_keypoints.npy",
        keypoints_dir / f"{uid}_keypoints.npz",
    ]
    for fb in fallbacks:
        if fb.exists():
            return fb

    # Return primary candidate path (will be reported on missing file error)
    return candidate


class SentenceISLDataset(Dataset):
    """
    Dataset for variable-length Continuous ISL sentence sequences.
    
    Each sample contains:
        - keypoints: Tensor of shape (T, 543, 3)
        - target: Tensor of shape (L,) containing target word token IDs
        - input_len / input_length: int (T)
        - target_len / target_length: int (L)
        - sample_id: str (UID)
        - text: str (Original English transcript)
    """

    def __init__(
        self,
        samples: Optional[List[Dict]] = None,
        csv_path: Optional[Union[str, Path]] = None,
        annotations_file: Optional[Union[str, Path]] = None,
        keypoints_dir: Optional[Union[str, Path]] = None,
        vocab: Optional[GlossVocabulary] = None,
        uid_col: str = "uid",
        text_col: str = "SIGN GLOSSES",
        split_col: Optional[str] = None,
        split_val: Optional[str] = None,
        keypoint_filename_pattern: str = "{uid}.npy",
        max_seq_len: int = 512,
        min_seq_len: int = 8,
        debug_mode: bool = False,
        debug_num_samples: int = 16,
    ):
        self.vocab = vocab if vocab is not None else GlossVocabulary()
        self.max_seq_len = max_seq_len
        self.min_seq_len = min_seq_len
        self.debug_mode = debug_mode
        self.keypoints_dir = Path(keypoints_dir) if keypoints_dir else None
        self.uid_col = uid_col
        self.text_col = text_col
        self.split_col = split_col
        self.split_val = split_val
        self.keypoint_filename_pattern = keypoint_filename_pattern

        if debug_mode:
            logger.info(f"Initializing SentenceISLDataset in DEBUG_MODE with {debug_num_samples} synthetic samples.")
            self.samples = self._generate_synthetic_samples(debug_num_samples)
        elif samples is not None:
            self.samples = samples
        elif csv_path is not None and Path(csv_path).exists():
            self.samples = self._load_from_csv(
                csv_path=Path(csv_path),
                uid_col=self.uid_col,
                text_col=self.text_col,
                split_col=self.split_col,
                split_val=self.split_val,
                pattern=self.keypoint_filename_pattern,
            )
        elif annotations_file is not None and Path(annotations_file).exists():
            ann_path = Path(annotations_file)
            if ann_path.suffix.lower() == ".csv":
                self.samples = self._load_from_csv(
                    csv_path=ann_path,
                    uid_col=self.uid_col,
                    text_col=self.text_col,
                    split_col=self.split_col,
                    split_val=self.split_val,
                    pattern=self.keypoint_filename_pattern,
                )
            else:
                self.samples = self._load_from_annotations(ann_path)
        else:
            self.samples = []

    def _generate_synthetic_samples(self, n_samples: int) -> List[Dict]:
        """Generate synthetic samples for testing and smoke verification."""
        test_phrases = [
            "GOOD MORNING",
            "THANK YOU",
            "HOW ARE YOU",
            "WHAT IS NAME",
            "NICE MEET YOU",
        ]
        # Register words into vocabulary
        for p in test_phrases:
            for w in tokenize_english_transcript(p):
                self.vocab.add_token(w)

        synthetic = []
        for i in range(n_samples):
            phrase = test_phrases[i % len(test_phrases)]
            tokens = tokenize_english_transcript(phrase)
            target_ids = self.vocab.encode_tokens(tokens)
            t_len = np.random.randint(24, 64)  # Variable sequence length (T >= L)
            # Synthetic 543 3D landmarks
            dummy_kp = np.random.randn(t_len, 543, 3).astype(np.float32) * 0.1
            synthetic.append({
                "sample_id": f"synthetic_{i:04d}",
                "keypoints": dummy_kp,
                "text": phrase,
                "tokens": tokens,
                "glosses": tokens,
                "target_ids": target_ids,
                "gloss_ids": target_ids,
            })
        return synthetic

    def _load_from_csv(
        self,
        csv_path: Path,
        uid_col: str,
        text_col: str,
        split_col: Optional[str] = None,
        split_val: Optional[str] = None,
        pattern: str = "{uid}.npy",
    ) -> List[Dict]:
        """
        Load samples from CSV annotation file.
        
        Reads UID, English sentence transcript, applies tokenization, and resolves keypoint paths.
        """
        loaded = []
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise ValueError(f"CSV file '{csv_path}' is empty or has no header.")
            if uid_col not in reader.fieldnames:
                raise ValueError(
                    f"UID column '{uid_col}' not found in CSV '{csv_path}'. "
                    f"Available columns: {reader.fieldnames}"
                )
            if text_col not in reader.fieldnames:
                raise ValueError(
                    f"Text column '{text_col}' not found in CSV '{csv_path}'. "
                    f"Available columns: {reader.fieldnames}"
                )

            for row_idx, row in enumerate(reader):
                # Filter by split if configured
                if split_col and split_val:
                    if split_col in row and row[split_col].strip() != str(split_val).strip():
                        continue

                uid = row[uid_col].strip()
                raw_text = row[text_col].strip()
                tokens = tokenize_gloss_sequence(raw_text)
                target_ids = self.vocab.encode_tokens(tokens)

                kp_path = None
                if self.keypoints_dir:
                    kp_path = resolve_keypoint_path(self.keypoints_dir, uid, pattern=pattern)

                loaded.append({
                    "sample_id": uid,
                    "keypoint_path": kp_path,
                    "text": raw_text,
                    "tokens": tokens,
                    "glosses": tokens,       # Compatibility alias
                    "target_ids": target_ids,
                    "gloss_ids": target_ids,  # Compatibility alias
                })

        logger.info(f"Loaded {len(loaded)} samples from CSV '{csv_path.name}'.")
        return loaded

    def _load_from_annotations(self, annotations_file: Path) -> List[Dict]:
        """Load samples from JSON annotations file."""
        with open(annotations_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        loaded = []
        for item in data:
            video_id = str(item.get("video_id") or item.get("id") or item.get("uid"))
            raw_text = item.get("text") or item.get("english") or ""
            glosses = item.get("glosses", [])
            if isinstance(glosses, str):
                glosses = glosses.split()
            
            if not glosses and raw_text:
                tokens = tokenize_english_transcript(raw_text)
            else:
                tokens = [g.lower() for g in glosses]

            target_ids = self.vocab.encode_tokens(tokens)

            # Keypoint file path
            kp_path = None
            if self.keypoints_dir:
                kp_path = resolve_keypoint_path(
                    self.keypoints_dir, video_id, pattern=self.keypoint_filename_pattern
                )

            loaded.append({
                "sample_id": video_id,
                "keypoint_path": kp_path,
                "text": raw_text,
                "tokens": tokens,
                "glosses": tokens,
                "target_ids": target_ids,
                "gloss_ids": target_ids,
            })
        logger.info(f"Loaded {len(loaded)} samples from JSON '{annotations_file.name}'.")
        return loaded

    def validate_ctc_targets(self) -> Dict[str, Any]:
        """
        Validate all samples in the dataset for CTC compatibility (input_len >= target_len).
        
        Returns summary dictionary with valid/invalid counts and violating sample IDs.
        """
        valid_samples = []
        invalid_samples = []

        for idx, sample in enumerate(self.samples):
            uid = sample.get("sample_id", f"idx_{idx}")
            target_len = len(sample.get("target_ids", []))
            
            # Check length if keypoints are in memory or need inspection
            t_len = None
            if "keypoints" in sample:
                t_len = sample["keypoints"].shape[0]
            elif sample.get("keypoint_path") and sample["keypoint_path"].exists():
                kp_p = sample["keypoint_path"]
                try:
                    if str(kp_p).endswith(".npz"):
                        with np.load(kp_p) as npz:
                            kp = npz["keypoints"] if "keypoints" in npz else npz["arr_0"]
                    else:
                        kp = np.load(kp_p)
                    t_len = kp.shape[0]
                except Exception as e:
                    invalid_samples.append({"sample_id": uid, "reason": f"Corrupt file: {e}"})
                    continue

            if t_len is not None:
                if t_len > self.max_seq_len:
                    t_len = self.max_seq_len
                if not check_ctc_validity(t_len, target_len, sample_id=uid):
                    invalid_samples.append({
                        "sample_id": uid,
                        "input_len": t_len,
                        "target_len": target_len,
                        "reason": f"target_len ({target_len}) > input_len ({t_len})",
                    })
                else:
                    valid_samples.append(uid)
            else:
                valid_samples.append(uid)

        logger.info(
            f"CTC Validation Summary: {len(valid_samples)} valid samples, "
            f"{len(invalid_samples)} invalid samples."
        )
        return {
            "valid_count": len(valid_samples),
            "invalid_count": len(invalid_samples),
            "invalid_samples": invalid_samples,
        }

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Union[torch.Tensor, str, int]]:
        sample = self.samples[idx]
        sample_id = str(sample.get("sample_id", f"idx_{idx}"))

        # 1. Load keypoints (from memory or cached disk file)
        if "keypoints" in sample:
            kp = sample["keypoints"]
        elif "keypoint_path" in sample and sample["keypoint_path"] is not None:
            p = Path(sample["keypoint_path"])
            if not p.exists():
                raise FileNotFoundError(
                    f"Keypoint file not found for sample UID '{sample_id}'. "
                    f"Expected path: '{p.resolve()}'"
                )
            if str(p).endswith(".npz"):
                with np.load(p) as npz:
                    kp = npz["keypoints"] if "keypoints" in npz else npz["arr_0"]
            else:
                kp = np.load(p)
        else:
            raise ValueError(f"No keypoint data or path found for sample UID '{sample_id}'")

        # Ensure float32 array
        kp = np.asarray(kp, dtype=np.float32)

        # Truncate if exceeds max_seq_len
        if kp.shape[0] > self.max_seq_len:
            kp = kp[:self.max_seq_len]

        t_len = kp.shape[0]

        # 2. Target Token IDs
        target_ids = sample.get("target_ids")
        if target_ids is None:
            target_ids = sample.get("gloss_ids")
        if target_ids is None:
            tokens = sample.get("tokens", [])
            target_ids = self.vocab.encode_tokens(tokens)
        
        target_len = len(target_ids)

        # 3. CTC length check
        check_ctc_validity(t_len, target_len, sample_id=sample_id)

        return {
            "keypoints": torch.from_numpy(kp).float(),   # Shape: (T, 543, 3)
            "target": torch.tensor(target_ids, dtype=torch.long),  # Shape: (L,)
            "input_len": t_len,
            "target_len": target_len,
            "input_length": t_len,
            "target_length": target_len,
            "sample_id": sample_id,
            "text": str(sample.get("text", "")),
        }


def collate_variable_length(batch: List[Dict]) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Collate variable-length keypoints and target word-token sequences into a padded batch.
    
    Transforms keypoints from (N, T_max, 543, 3) -> (N, 3, T_max, 543) for ST-GCN.
    
    Returns:
        padded_keypoints: FloatTensor of shape (N, C=3, T_max, V=543)
        padded_targets:   LongTensor of shape (N, L_max)
        input_lengths:    LongTensor of shape (N,)
        target_lengths:   LongTensor of shape (N,)
    """
    batch_size = len(batch)

    input_lengths = torch.tensor([item["input_len"] for item in batch], dtype=torch.long)
    target_lengths = torch.tensor([item["target_len"] for item in batch], dtype=torch.long)

    max_t = int(torch.max(input_lengths).item())
    max_l = int(torch.max(target_lengths).item()) if target_lengths.numel() > 0 and torch.max(target_lengths).item() > 0 else 1

    num_landmarks = 543
    num_channels = 3

    # Allocate zero-padded tensors
    padded_keypoints_raw = torch.zeros((batch_size, max_t, num_landmarks, num_channels), dtype=torch.float32)
    padded_targets = torch.zeros((batch_size, max_l), dtype=torch.long)

    for i, item in enumerate(batch):
        kp = item["keypoints"]  # (T, 543, 3)
        tgt = item["target"]    # (L,)
        t_len = item["input_len"]
        l_len = item["target_len"]

        padded_keypoints_raw[i, :t_len, :, :] = kp
        if l_len > 0:
            padded_targets[i, :l_len] = tgt

    # Permute to ST-GCN format: (N, T_max, V, C) -> (N, C, T_max, V)
    # (N, T, 543, 3) -> (N, 3, T, 543)
    padded_keypoints = padded_keypoints_raw.permute(0, 3, 1, 2).contiguous()

    return padded_keypoints, padded_targets, input_lengths, target_lengths
