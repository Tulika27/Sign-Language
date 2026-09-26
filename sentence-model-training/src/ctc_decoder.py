"""
CTC Classification Head and Greedy Decoder.
Projects sequence embeddings to vocabulary logits and performs alignment-free CTC decoding.
"""

from typing import List, Optional, Tuple, Union
import torch
import torch.nn as nn
import torch.nn.functional as F

from .vocabulary import GlossVocabulary


class CTCHead(nn.Module):
    """
    Linear classification head projecting Transformer sequence representations to vocabulary logits.
    """

    def __init__(self, in_features: int, vocab_size: int, hidden_dim: Optional[int] = None, dropout: float = 0.1):
        super().__init__()
        if hidden_dim is not None and hidden_dim > 0:
            self.projection = nn.Sequential(
                nn.Linear(in_features, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim, vocab_size),
            )
        else:
            self.projection = nn.Linear(in_features, vocab_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Sequence features of shape (N, T, in_features)
        Returns:
            logits: (N, T, vocab_size)
        """
        return self.projection(x)


class GreedyCTCDecoder:
    """
    Greedy Best-Path CTC Decoder:
        1. Takes argmax over class probabilities at each timestep
        2. Removes repeated adjacent identical tokens
        3. Removes blank tokens (ID 0)
        4. Maps remaining token IDs to gloss strings using vocabulary
    """

    def __init__(self, vocab: GlossVocabulary, blank_id: int = 0):
        self.vocab = vocab
        self.blank_id = blank_id

    def decode_indices(self, raw_ids: List[int]) -> List[int]:
        """Collapse consecutive duplicates and strip blank tokens from an integer sequence."""
        collapsed = []
        prev = None
        for token_id in raw_ids:
            if token_id != prev:
                if token_id != self.blank_id:
                    collapsed.append(token_id)
                prev = token_id
        return collapsed

    def decode_logits(
        self,
        logits: torch.Tensor,
        sequence_lengths: Optional[torch.Tensor] = None,
    ) -> List[List[str]]:
        """
        Decode batch of logits into gloss token sequences.
        
        Args:
            logits: Tensor of shape (N, T, vocab_size) or (T, N, vocab_size)
            sequence_lengths: Optional Tensor of shape (N,) containing valid frames per sample
        Returns:
            List of decoded gloss sequences per batch sample.
        """
        if logits.dim() == 3 and logits.size(0) != len(sequence_lengths if sequence_lengths is not None else [1]):
            # If (T, N, vocab_size), permute to (N, T, vocab_size)
            logits = logits.permute(1, 0, 2)

        # Argmax per timestep
        predictions = torch.argmax(logits, dim=-1)  # (N, T)
        batch_size = predictions.size(0)

        decoded_batch = []
        for i in range(batch_size):
            valid_len = int(sequence_lengths[i].item()) if sequence_lengths is not None else predictions.size(1)
            raw_seq = predictions[i, :valid_len].tolist()
            collapsed_ids = self.decode_indices(raw_seq)
            glosses = self.vocab.decode_sequence(collapsed_ids, remove_special=True)
            decoded_batch.append(glosses)

        return decoded_batch
