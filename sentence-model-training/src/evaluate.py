"""
Evaluation and Metrics Calculation for Sentence ISL Model.
Loads checkpoint, runs greedy CTC decoding, and calculates Word Error Rate (WER) & sentence accuracy.
"""

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import torch
from torch.utils.data import DataLoader

from src.ctc_decoder import GreedyCTCDecoder
from src.dataset import SentenceISLDataset, collate_variable_length
from src.formatter import format_gloss_to_sentence
from src.model import SentenceISLModel
from src.vocabulary import GlossVocabulary

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EvaluateSentenceModel")


def calculate_levenshtein_distance(seq1: List[str], seq2: List[str]) -> int:
    """Calculate token-level edit distance between two sequences."""
    n, m = len(seq1), len(seq2)
    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if seq1[i - 1] == seq2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

    return dp[n][m]


def evaluate_model(
    checkpoint_path: str,
    dataset: SentenceISLDataset,
    batch_size: int = 8,
    device: Optional[torch.device] = None,
) -> Dict[str, float]:
    """
    Run evaluation on a dataset using the specified checkpoint.
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    logger.info(f"Loading checkpoint from: {checkpoint_path}")
    model, vocab, ckpt = SentenceISLModel.load_checkpoint(checkpoint_path, device=device)
    decoder = GreedyCTCDecoder(vocab=vocab, blank_id=0)

    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=collate_variable_length,
    )

    total_edit_distance = 0
    total_ref_words = 0
    exact_match_count = 0
    total_samples = 0

    results = []

    model.eval()
    with torch.no_grad():
        for keypoints, targets, input_lengths, target_lengths in loader:
            keypoints = keypoints.to(device)
            input_lengths = input_lengths.to(device)

            _, logits = model(keypoints, input_lengths=input_lengths)
            pred_glosses_batch = decoder.decode_logits(logits, sequence_lengths=input_lengths)

            for i in range(len(pred_glosses_batch)):
                pred_glosses = pred_glosses_batch[i]
                t_len = target_lengths[i].item()
                ref_ids = targets[i, :t_len].tolist()
                ref_glosses = vocab.decode_sequence(ref_ids, remove_special=True)

                dist = calculate_levenshtein_distance(ref_glosses, pred_glosses)
                total_edit_distance += dist
                total_ref_words += len(ref_glosses)

                if ref_glosses == pred_glosses:
                    exact_match_count += 1
                total_samples += 1

                formatted_sentence = format_gloss_to_sentence(pred_glosses)
                results.append({
                    "ref_glosses": ref_glosses,
                    "pred_glosses": pred_glosses,
                    "formatted_sentence": formatted_sentence,
                })

    wer = (total_edit_distance / max(1, total_ref_words)) * 100.0
    accuracy = (exact_match_count / max(1, total_samples)) * 100.0

    logger.info(f"--- Evaluation Results ---")
    logger.info(f"Total Samples: {total_samples}")
    logger.info(f"Word Error Rate (WER): {wer:.2f}%")
    logger.info(f"Exact Sequence Accuracy: {accuracy:.2f}%")

    # Display sample predictions
    logger.info("Sample Predictions:")
    for sample in results[:5]:
        logger.info(f"  Reference: {' '.join(sample['ref_glosses'])}")
        logger.info(f"  Predicted: {' '.join(sample['pred_glosses'])} -> \"{sample['formatted_sentence']}\"")

    return {
        "wer": wer,
        "accuracy": accuracy,
        "total_samples": total_samples,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Continuous ISL Sentence Model")
    parser.add_argument("--checkpoint", type=str, required=True, help="Path to checkpoint best.pt")
    parser.add_argument("--debug", action="store_true", help="Evaluate on synthetic debug dataset")

    args = parser.parse_args()

    vocab = GlossVocabulary()
    dataset = SentenceISLDataset(vocab=vocab, debug_mode=True, debug_num_samples=16)

    evaluate_model(checkpoint_path=args.checkpoint, dataset=dataset)
