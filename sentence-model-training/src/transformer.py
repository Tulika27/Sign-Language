"""
Temporal Transformer Encoder for Continuous Sign Sequence Modeling.
Processes frame features across time while preserving sequence representations for CTC.
"""

import math
from typing import Optional
import torch
import torch.nn as nn


class PositionalEncoding(nn.Module):
    """
    Sinusoidal positional encoding for sequence order representation.
    """

    def __init__(self, d_model: int, max_len: int = 1024, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)

        pe = pe.unsqueeze(0)  # Shape: (1, max_len, d_model)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input sequence tensor (N, T, d_model)
        Returns:
            Tensor with added positional encodings (N, T, d_model)
        """
        seq_len = x.size(1)
        x = x + self.pe[:, :seq_len, :]
        return self.dropout(x)


class TemporalTransformerEncoder(nn.Module):
    """
    Temporal Transformer sequence model.
    Receives temporal features (N, T, d_model) from ST-GCN and outputs enriched representations (N, T, d_model).
    """

    def __init__(
        self,
        d_model: int = 256,
        nhead: int = 8,
        num_layers: int = 4,
        dim_feedforward: int = 1024,
        dropout: float = 0.1,
        max_position: int = 1024,
    ):
        super().__init__()
        self.d_model = d_model
        self.pos_encoder = PositionalEncoding(d_model=d_model, max_len=max_position, dropout=dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            activation="gelu",
            batch_first=True,  # (N, T, d_model)
            norm_first=True,
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.norm = nn.LayerNorm(d_model)

    def forward(self, x: torch.Tensor, key_padding_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Args:
            x: Feature sequence tensor (N, T, d_model)
            key_padding_mask: BoolTensor of shape (N, T) where True indicates padded positions
        Returns:
            Sequence output (N, T, d_model)
        """
        x = self.pos_encoder(x)
        out = self.transformer_encoder(x, src_key_padding_mask=key_padding_mask)
        out = self.norm(out)
        return out
