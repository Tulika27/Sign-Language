"""
Continuous ISL Sentence Model (ST-GCN + Temporal Transformer + CTC Head).
Full end-to-end neural network architecture for continuous sign language recognition.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import torch
import torch.nn as nn
import torch.nn.functional as F

from .stgcn import STGCNEncoder
from .transformer import TemporalTransformerEncoder
from .ctc_decoder import CTCHead, GreedyCTCDecoder
from .vocabulary import GlossVocabulary


class SentenceISLModel(nn.Module):
    """
    End-to-end continuous sign language recognition model:
        Input: (N, C=3, T, V=543)
        1. ST-GCN Spatial-Temporal Feature Extractor -> (N, T, d_model)
        2. Temporal Transformer Encoder -> (N, T, d_model)
        3. CTC Classification Head -> (T, N, vocab_size) Log-Softmax Logits
    """

    def __init__(
        self,
        vocab_size: int,
        in_channels: int = 3,
        stgcn_hidden: int = 64,
        stgcn_layers: int = 2,
        d_model: int = 256,
        nhead: int = 8,
        transformer_layers: int = 4,
        dim_feedforward: int = 1024,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.vocab_size = vocab_size
        self.in_channels = in_channels
        self.stgcn_hidden = stgcn_hidden
        self.stgcn_layers = stgcn_layers
        self.d_model = d_model
        self.nhead = nhead
        self.transformer_layers = transformer_layers
        self.dim_feedforward = dim_feedforward
        self.dropout = dropout

        # 1. ST-GCN Spatial-Temporal Encoder
        self.stgcn = STGCNEncoder(
            in_channels=in_channels,
            hidden_channels=stgcn_hidden,
            out_channels=d_model,
            num_layers=stgcn_layers,
            dropout=dropout,
        )

        # 2. Temporal Transformer
        self.transformer = TemporalTransformerEncoder(
            d_model=d_model,
            nhead=nhead,
            num_layers=transformer_layers,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
        )

        # 3. CTC Projection Head
        self.ctc_head = CTCHead(
            in_features=d_model,
            vocab_size=vocab_size,
            hidden_dim=dim_feedforward // 2,
            dropout=dropout,
        )

    def forward(
        self,
        x: torch.Tensor,
        input_lengths: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass for training and evaluation.
        
        Args:
            x: Landmark tensor of shape (N, C=3, T, V=543)
            input_lengths: Optional sequence length per sample (N,)
        Returns:
            log_probs: Tensor of shape (T, N, vocab_size) for nn.CTCLoss
            logits:    Tensor of shape (N, T, vocab_size) for evaluation/decoding
        """
        N, C, T, V = x.size()

        # Build key padding mask for Transformer if lengths provided
        key_padding_mask = None
        if input_lengths is not None:
            max_t = T
            mask = torch.arange(max_t, device=x.device).unsqueeze(0) >= input_lengths.unsqueeze(1)
            key_padding_mask = mask  # (N, T) with True at padding

        # 1. ST-GCN Feature Extraction: (N, 3, T, 543) -> (N, T, d_model)
        stgcn_feats = self.stgcn(x)

        # 2. Temporal Transformer Modeling: (N, T, d_model) -> (N, T, d_model)
        trans_feats = self.transformer(stgcn_feats, key_padding_mask=key_padding_mask)

        # 3. CTC Output Logits: (N, T, d_model) -> (N, T, vocab_size)
        logits = self.ctc_head(trans_feats)

        # Compute log-probabilities for PyTorch CTCLoss: (T, N, vocab_size)
        log_probs = F.log_softmax(logits, dim=-1).permute(1, 0, 2)

        return log_probs, logits

    def save_checkpoint(
        self,
        filepath: Union[str, Path],
        vocab: GlossVocabulary,
        epoch: int = 0,
        optimizer: Optional[torch.optim.Optimizer] = None,
        val_loss: float = float("inf"),
        extra_info: Optional[Dict] = None,
    ) -> None:
        """Save full model checkpoint including weights, vocabulary, and config."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        checkpoint_data = {
            "model_state_dict": self.state_dict(),
            "vocab_token_to_id": vocab.token_to_id,
            "vocab_size": self.vocab_size,
            "in_channels": self.in_channels,
            "stgcn_hidden": self.stgcn_hidden,
            "stgcn_layers": self.stgcn_layers,
            "d_model": self.d_model,
            "nhead": self.nhead,
            "transformer_layers": self.transformer_layers,
            "dim_feedforward": self.dim_feedforward,
            "dropout": self.dropout,
            "epoch": epoch,
            "val_loss": val_loss,
            "optimizer_state_dict": optimizer.state_dict() if optimizer else None,
            "extra_info": extra_info or {},
        }
        torch.save(checkpoint_data, filepath)

    @classmethod
    def load_checkpoint(
        cls,
        filepath: Union[str, Path],
        device: torch.device = torch.device("cpu"),
    ) -> Tuple["SentenceISLModel", GlossVocabulary, Dict]:
        """Load model and vocabulary from a saved checkpoint."""
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Checkpoint not found at: {filepath}")

        ckpt = torch.load(filepath, map_location=device, weights_only=False)

        vocab = GlossVocabulary(token_to_id=ckpt["vocab_token_to_id"])
        model = cls(
            vocab_size=ckpt["vocab_size"],
            in_channels=ckpt.get("in_channels", 3),
            stgcn_hidden=ckpt.get("stgcn_hidden", 64),
            stgcn_layers=ckpt.get("stgcn_layers", 2),
            d_model=ckpt.get("d_model", 256),
            nhead=ckpt.get("nhead", 8),
            transformer_layers=ckpt.get("transformer_layers", 4),
            dim_feedforward=ckpt.get("dim_feedforward", 1024),
            dropout=ckpt.get("dropout", 0.1),
        )
        model.load_state_dict(ckpt["model_state_dict"])
        model.to(device)
        model.eval()

        return model, vocab, ckpt
