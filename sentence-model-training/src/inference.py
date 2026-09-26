"""
Inference Pipeline for Continuous ISL Sentence Model.
Accepts raw video or pre-extracted keypoint arrays and returns decoded glosses and formatted English sentences.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union
import numpy as np
import torch

from .ctc_decoder import GreedyCTCDecoder
from .formatter import format_gloss_to_sentence
from .model import SentenceISLModel
from .preprocessing import MediaPipeHolisticExtractor
from .vocabulary import GlossVocabulary


class SentenceInferencePipeline:
    """
    End-to-end inference pipeline:
        Video (.mp4/.avi) / Keypoint Array (T, 543, 3)
        -> MediaPipe Holistic Extractor
        -> ST-GCN (1, 3, T, 543)
        -> Temporal Transformer
        -> Greedy CTC Decoding
        -> English Sentence Formatter
    """

    def __init__(
        self,
        checkpoint_path: Union[str, Path],
        device: Optional[str] = None,
    ):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.model, self.vocab, self.ckpt = SentenceISLModel.load_checkpoint(
            filepath=checkpoint_path,
            device=self.device,
        )
        self.decoder = GreedyCTCDecoder(vocab=self.vocab, blank_id=0)
        self.extractor = None

    def _get_extractor(self) -> MediaPipeHolisticExtractor:
        if self.extractor is None:
            self.extractor = MediaPipeHolisticExtractor()
        return self.extractor

    def predict_keypoints(self, keypoints: np.ndarray) -> Dict[str, Union[List[str], str, int]]:
        """
        Run inference on pre-extracted keypoints array of shape (T, 543, 3).
        """
        # Ensure shape (T, 543, 3)
        if keypoints.ndim != 3 or keypoints.shape[1] != 543 or keypoints.shape[2] != 3:
            raise ValueError(f"Expected keypoints array of shape (T, 543, 3), got {keypoints.shape}")

        t_len = keypoints.shape[0]
        # Reshape to (1, 3, T, 543)
        tensor_kp = torch.from_numpy(keypoints).float().permute(2, 0, 1).unsqueeze(0).to(self.device)
        input_lengths = torch.tensor([t_len], dtype=torch.long, device=self.device)

        with torch.no_grad():
            _, logits = self.model(tensor_kp, input_lengths=input_lengths)
            pred_glosses = self.decoder.decode_logits(logits, sequence_lengths=input_lengths)[0]

        formatted_sentence = format_gloss_to_sentence(pred_glosses)

        return {
            "glosses": pred_glosses,
            "sentence": formatted_sentence,
            "frame_count": t_len,
        }

    def predict_video(self, video_path: Union[str, Path]) -> Dict[str, Union[List[str], str, int]]:
        """
        Run inference directly from a video file.
        """
        extractor = self._get_extractor()
        keypoints, frame_count = extractor.extract_video(video_path)
        return self.predict_keypoints(keypoints)

    def close(self):
        if self.extractor is not None:
            self.extractor.close()
