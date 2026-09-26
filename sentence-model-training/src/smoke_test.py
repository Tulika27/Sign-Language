"""
Comprehensive Smoke Test for Continuous ISL Sentence Model Training Pipeline.
Verifies all core requirements including CSV dataset loading, English tokenization,
vocabulary building, ST-GCN, Transformer, CTC, decoding, formatting, and checkpointing.
"""

import csv
import logging
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ctc_decoder import CTCHead, GreedyCTCDecoder
from src.dataset import SentenceISLDataset, collate_variable_length, check_ctc_validity, resolve_keypoint_path
from src.formatter import format_gloss_to_sentence
from src.graph import LandmarkGraph
from src.model import SentenceISLModel
from src.stgcn import STGCNEncoder
from src.transformer import TemporalTransformerEncoder
from src.vocabulary import GlossVocabulary, WordVocabulary, tokenize_english_transcript

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("SmokeTest")


def run_smoke_test():
    logger.info("==================================================")
    logger.info("  STARTING STEP 4B SENTENCE MODEL SMOKE TEST      ")
    logger.info("==================================================")

    # 1. Landmark Graph & Adjacency Matrix
    logger.info("[Test 1/13] Verifying Landmark Graph & Adjacency Matrix...")
    graph = LandmarkGraph()
    A = graph.get_torch_adjacency()
    assert A.shape == (3, 543, 543), f"Unexpected adjacency shape: {A.shape}"
    logger.info("  -> Passed: LandmarkGraph created with shape (3, 543, 543)")

    # 2. English Transcript Tokenization
    logger.info("[Test 2/13] Verifying English transcript tokenization...")
    sample_text_1 = "How are you?"
    sample_text_2 = "THANK YOU!"
    sample_text_3 = "Good morning, everyone."
    tokens_1 = tokenize_english_transcript(sample_text_1)
    tokens_2 = tokenize_english_transcript(sample_text_2)
    tokens_3 = tokenize_english_transcript(sample_text_3)

    assert tokens_1 == ["how", "are", "you"], f"Unexpected tokens for '{sample_text_1}': {tokens_1}"
    assert tokens_2 == ["thank", "you"], f"Unexpected tokens for '{sample_text_2}': {tokens_2}"
    assert tokens_3 == ["good", "morning", "everyone"], f"Unexpected tokens for '{sample_text_3}': {tokens_3}"
    logger.info(f"  -> Passed: Tokenization working correctly (e.g., '{sample_text_1}' -> {tokens_1})")

    # 3. Vocabulary generation from CSV & min_freq filtering
    logger.info("[Test 3/13] Verifying Vocabulary building from CSV...")
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "annotations_sample.csv"
        rows = [
            {"uid": "sample_001", "english": "GOOD MORNING"},
            {"uid": "sample_002", "english": "HOW ARE YOU"},
            {"uid": "sample_003", "english": "THANK YOU"},
            {"uid": "sample_004", "english": "GOOD NIGHT"},
            {"uid": "sample_005", "english": "RARE_WORD_XYZ"},
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["uid", "english"])
            writer.writeheader()
            writer.writerows(rows)

        # Build with min_freq=2 (RARE_WORD_XYZ should be filtered out)
        vocab_csv = GlossVocabulary()
        vocab_csv.build_from_csv(csv_path, text_col="english", min_freq=2)
        assert vocab_csv.blank_id == 0, f"Blank ID must be 0, got {vocab_csv.blank_id}"
        assert vocab_csv.unk_id == 1, f"Unk ID must be 1, got {vocab_csv.unk_id}"
        assert "good" in vocab_csv.token_to_id, "'good' (freq=2) should be in vocabulary"
        assert "you" in vocab_csv.token_to_id, "'you' (freq=2) should be in vocabulary"
        assert "rare_word_xyz" not in vocab_csv.token_to_id, "'rare_word_xyz' (freq=1) should be filtered by min_freq=2"

        # Check JSON save & load
        vocab_json_path = Path(tmpdir) / "vocab.json"
        vocab_csv.save_to_json(vocab_json_path)
        loaded_vocab = GlossVocabulary.load_from_json(vocab_json_path)
        assert len(loaded_vocab) == len(vocab_csv), "Loaded vocabulary size mismatch"
    logger.info(f"  -> Passed: CSV vocabulary building and min_freq filtering verified (Vocab size={len(vocab_csv)})")

    # 4. Vocabulary encode/decode & token-to-ID conversion
    logger.info("[Test 4/13] Verifying Vocabulary token-to-ID conversion...")
    vocab = GlossVocabulary()
    sample_phrases = ["good morning", "thank you", "how are you"]
    vocab.build_from_texts(sample_phrases)
    encoded = vocab.encode_tokens(["good", "morning"])
    decoded = vocab.decode_tokens(encoded)
    assert decoded == ["good", "morning"], f"Vocabulary decode mismatch: {decoded}"
    assert vocab.blank_id == 0, f"Blank ID must be 0, got {vocab.blank_id}"
    logger.info(f"  -> Passed: Vocabulary has {len(vocab)} tokens (Blank token ID={vocab.blank_id})")

    # 5. CSV Dataset Loading & Keypoint File Resolution
    logger.info("[Test 5/13] Verifying CSV Dataset loading and keypoint file resolution...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        kp_dir = tmp_path / "keypoints"
        kp_dir.mkdir(parents=True, exist_ok=True)
        csv_file = tmp_path / "train.csv"

        # Create dummy keypoint files for sample_001, sample_002
        kp_1 = np.random.randn(30, 543, 3).astype(np.float32)
        kp_2 = np.random.randn(45, 543, 3).astype(np.float32)
        np.save(kp_dir / "sample_001.npy", kp_1)
        np.savez_compressed(kp_dir / "sample_002.npz", keypoints=kp_2)

        csv_rows = [
            {"uid": "sample_001", "english": "GOOD MORNING", "split": "train"},
            {"uid": "sample_002", "english": "HOW ARE YOU", "split": "train"},
        ]
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["uid", "english", "split"])
            writer.writeheader()
            writer.writerows(csv_rows)

        csv_dataset = SentenceISLDataset(
            csv_path=csv_file,
            keypoints_dir=kp_dir,
            vocab=vocab,
            uid_col="uid",
            text_col="english",
            split_col="split",
            split_val="train",
        )
        assert len(csv_dataset) == 2, f"Expected 2 samples, got {len(csv_dataset)}"
        s0 = csv_dataset[0]
        assert s0["keypoints"].shape == (30, 543, 3), f"Sample 0 shape mismatch: {s0['keypoints'].shape}"
        assert s0["sample_id"] == "sample_001", f"Sample ID mismatch: {s0['sample_id']}"
        assert s0["target_len"] == 2, f"Target length mismatch: {s0['target_len']}"
        s1 = csv_dataset[1]
        assert s1["keypoints"].shape == (45, 543, 3), f"Sample 1 shape mismatch: {s1['keypoints'].shape}"
        assert s1["target_len"] == 3, f"Target length mismatch: {s1['target_len']}"
    logger.info("  -> Passed: CSV dataset loading and keypoint resolution verified.")

    # 6. CTC Safety Check & Length Validation
    logger.info("[Test 6/13] Verifying CTC Sequence Length Validation...")
    assert check_ctc_validity(input_length=30, target_length=3) is True
    assert check_ctc_validity(input_length=2, target_length=5) is False
    # Validate on dataset instance
    val_report = csv_dataset.validate_ctc_targets()
    assert val_report["invalid_count"] == 0, f"Expected 0 invalid samples, got {val_report['invalid_count']}"
    logger.info("  -> Passed: CTC sequence length constraints verified.")

    # 7. Dataset & Variable-Length Collation
    logger.info("[Test 7/13] Verifying Dataset & Dynamic Collation...")
    dataset = SentenceISLDataset(vocab=vocab, debug_mode=True, debug_num_samples=4)
    sample_0 = dataset[0]
    assert sample_0["keypoints"].shape[1:] == (543, 3), f"Expected (T, 543, 3), got {sample_0['keypoints'].shape}"

    batch = [dataset[i] for i in range(4)]
    keypoints, targets, input_lengths, target_lengths = collate_variable_length(batch)
    assert keypoints.shape[0] == 4 and keypoints.shape[1] == 3 and keypoints.shape[3] == 543, (
        f"Unexpected collated keypoints shape: {keypoints.shape}"
    )
    logger.info(f"  -> Passed: Collated batch keypoints shape={tuple(keypoints.shape)} (N, 3, T_max, 543)")

    # 8. ST-GCN Forward Pass
    logger.info("[Test 8/13] Verifying ST-GCN Encoder forward pass...")
    stgcn = STGCNEncoder(in_channels=3, hidden_channels=32, out_channels=128, num_layers=2)
    stgcn_out = stgcn(keypoints)
    assert stgcn_out.shape == (4, keypoints.shape[2], 128), f"Unexpected STGCN output shape: {stgcn_out.shape}"
    logger.info(f"  -> Passed: ST-GCN output shape={tuple(stgcn_out.shape)} (N, T_max, d_model)")

    # 9. Temporal Transformer Forward Pass
    logger.info("[Test 9/13] Verifying Temporal Transformer forward pass...")
    transformer = TemporalTransformerEncoder(d_model=128, nhead=4, num_layers=2, dim_feedforward=256)
    trans_out = transformer(stgcn_out)
    assert trans_out.shape == (4, keypoints.shape[2], 128), f"Unexpected Transformer output shape: {trans_out.shape}"
    logger.info(f"  -> Passed: Transformer output shape={tuple(trans_out.shape)} (N, T_max, d_model)")

    # 10. Full Model & CTC Output Shape
    logger.info("[Test 10/13] Verifying Complete SentenceISLModel...")
    vocab_size = len(vocab)
    model = SentenceISLModel(
        vocab_size=vocab_size,
        in_channels=3,
        stgcn_hidden=32,
        stgcn_layers=2,
        d_model=128,
        nhead=4,
        transformer_layers=2,
        dim_feedforward=256,
    )
    log_probs, logits = model(keypoints, input_lengths=input_lengths)
    T_max = keypoints.shape[2]
    assert log_probs.shape == (T_max, 4, vocab_size), f"Unexpected log_probs shape: {log_probs.shape}"
    assert logits.shape == (4, T_max, vocab_size), f"Unexpected logits shape: {logits.shape}"
    logger.info(f"  -> Passed: CTC log_probs shape={tuple(log_probs.shape)} (T_max, N, vocab_size)")

    # 11. PyTorch CTCLoss Computation
    logger.info("[Test 11/13] Verifying PyTorch CTCLoss calculation...")
    ctc_loss_fn = nn.CTCLoss(blank=0, reduction="mean", zero_infinity=True)
    loss = ctc_loss_fn(log_probs, targets, input_lengths, target_lengths)
    assert torch.isfinite(loss), f"CTC Loss is non-finite: {loss.item()}"
    loss.backward()
    logger.info(f"  -> Passed: CTC Loss computed and backward passed successfully (Loss={loss.item():.4f})")

    # 12. Greedy CTC Decoder & Sentence Formatter
    logger.info("[Test 12/13] Verifying Greedy CTC Decoder & Sentence Formatter...")
    decoder = GreedyCTCDecoder(vocab=vocab, blank_id=0)
    good_id = vocab.token_to_id_lookup("good")
    morn_id = vocab.token_to_id_lookup("morning")
    raw_test_tokens = [0, good_id, good_id, 0, morn_id, morn_id, 0]
    collapsed_ids = decoder.decode_indices(raw_test_tokens)
    assert collapsed_ids == [good_id, morn_id], f"Expected {[good_id, morn_id]}, got {collapsed_ids}"

    decoded_tokens = vocab.decode_tokens(collapsed_ids)
    formatted_sentence = format_gloss_to_sentence(decoded_tokens)
    assert formatted_sentence == "Good morning.", f"Unexpected formatted sentence: {formatted_sentence}"
    logger.info(f"  -> Passed: Greedy decoder decoded {decoded_tokens} -> \"{formatted_sentence}\"")

    # 13. Checkpoint Save and Load
    logger.info("[Test 13/13] Verifying Checkpoint save and load...")
    with tempfile.TemporaryDirectory() as tmpdir:
        ckpt_path = Path(tmpdir) / "test_best.pt"
        model.save_checkpoint(filepath=ckpt_path, vocab=vocab, epoch=1, val_loss=0.42)
        loaded_model, loaded_vocab, meta = SentenceISLModel.load_checkpoint(ckpt_path)
        assert len(loaded_vocab) == len(vocab), "Loaded vocab size mismatch"
        assert meta["val_loss"] == 0.42, "Loaded checkpoint metadata mismatch"
    logger.info("  -> Passed: Checkpoint saved and loaded correctly.")

    logger.info("==================================================")
    logger.info("  ALL 13 SMOKE TEST CHECKS PASSED SUCCESSFULLY!   ")
    logger.info("==================================================")


if __name__ == "__main__":
    run_smoke_test()
