"""
Training Script for Continuous ISL Sentence Recognition Model.
Trains ST-GCN + Transformer + CTC with Mixed Precision and Checkpoint Saving.

Note:
Sentence annotations represent English transcript token sequences used as targets
for CTC training.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Optional

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from tqdm import tqdm

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import (
    BATCH_SIZE,
    BLANK_TOKEN_ID,
    CHECKPOINT_DIR,
    CSV_TEXT_COLUMN,
    CSV_UID_COLUMN,
    DEBUG_MODE,
    DEBUG_NUM_SAMPLES,
    KEYPOINT_FILENAME_PATTERN,
    LEARNING_RATE,
    MIN_TOKEN_FREQ,
    NUM_EPOCHS,
    NUM_WORKERS,
    OUTPUT_DIR,
    SEED,
    STGCN_HIDDEN_CHANNELS,
    STGCN_NUM_LAYERS,
    TRANSFORMER_D_MODEL,
    TRANSFORMER_DIM_FEEDFORWARD,
    TRANSFORMER_DROPOUT,
    TRANSFORMER_NHEAD,
    TRANSFORMER_NUM_LAYERS,
    USE_AMP,
    VALIDATION_SPLIT,
    VOCABULARY_FILE,
    WEIGHT_DECAY,
)
from src.ctc_decoder import GreedyCTCDecoder
from src.dataset import SentenceISLDataset, collate_variable_length
from src.model import SentenceISLModel
from src.vocabulary import GlossVocabulary, WordVocabulary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("TrainSentenceModel")


def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.CTCLoss,
    optimizer: torch.optim.Optimizer,
    scaler: Optional[torch.cuda.amp.GradScaler],
    device: torch.device,
    grad_accum_steps: int = 1,
) -> float:
    """Run one epoch of training."""
    model.train()
    total_loss = 0.0
    num_batches = 0

    optimizer.zero_grad()

    for batch_idx, (keypoints, targets, input_lengths, target_lengths) in enumerate(dataloader):
        keypoints = keypoints.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)
        input_lengths = input_lengths.to(device, non_blocking=True)
        target_lengths = target_lengths.to(device, non_blocking=True)

        if scaler is not None and device.type == "cuda":
            with torch.cuda.amp.autocast():
                log_probs, _ = model(keypoints, input_lengths=input_lengths)
                loss = criterion(log_probs, targets, input_lengths, target_lengths)
                loss = loss / grad_accum_steps
            scaler.scale(loss).backward()

            if (batch_idx + 1) % grad_accum_steps == 0 or (batch_idx + 1) == len(dataloader):
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()
        else:
            log_probs, _ = model(keypoints, input_lengths=input_lengths)
            loss = criterion(log_probs, targets, input_lengths, target_lengths)
            loss = loss / grad_accum_steps
            loss.backward()

            if (batch_idx + 1) % grad_accum_steps == 0 or (batch_idx + 1) == len(dataloader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()
                optimizer.zero_grad()

        total_loss += loss.item() * grad_accum_steps
        num_batches += 1

    return total_loss / max(1, num_batches)


def validate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.CTCLoss,
    device: torch.device,
) -> float:
    """Run validation loop."""
    model.eval()
    total_loss = 0.0
    num_batches = 0

    with torch.no_grad():
        for keypoints, targets, input_lengths, target_lengths in dataloader:
            keypoints = keypoints.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)
            input_lengths = input_lengths.to(device, non_blocking=True)
            target_lengths = target_lengths.to(device, non_blocking=True)

            log_probs, _ = model(keypoints, input_lengths=input_lengths)
            loss = criterion(log_probs, targets, input_lengths, target_lengths)

            total_loss += loss.item()
            num_batches += 1

    return total_loss / max(1, num_batches)


def run_training(
    dataset_path: Optional[str] = None,
    annotations_path: Optional[str] = None,
    checkpoint_dir: str = str(CHECKPOINT_DIR),
    vocab_path: Optional[str] = None,
    uid_col: str = CSV_UID_COLUMN,
    text_col: str = CSV_TEXT_COLUMN,
    min_token_freq: int = MIN_TOKEN_FREQ,
    pattern: str = KEYPOINT_FILENAME_PATTERN,
    num_epochs: int = NUM_EPOCHS,
    batch_size: int = BATCH_SIZE,
    learning_rate: float = LEARNING_RATE,
    debug: bool = DEBUG_MODE,
    resume_checkpoint: Optional[str] = None,
) -> None:
    """Main training execution entrypoint."""
    torch.manual_seed(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device} (CUDA available: {torch.cuda.is_available()})")

    # 1. Initialize Vocabulary
    vocab = GlossVocabulary()
    if vocab_path and Path(vocab_path).exists():
        logger.info(f"Loading prebuilt vocabulary from: {vocab_path}")
        vocab = GlossVocabulary.load_from_json(vocab_path)
    elif annotations_path and Path(annotations_path).exists():
        ann_path = Path(annotations_path)
        logger.info(f"Building vocabulary from annotations: {ann_path}")
        if ann_path.suffix.lower() == ".csv":
            vocab.build_from_csv(ann_path, text_col=text_col, min_freq=min_token_freq)
        else:
            with open(ann_path, "r", encoding="utf-8") as f:
                import json
                items = json.load(f)
            vocab.build_from_annotations(items)
        vocab.save_to_json(VOCABULARY_FILE)

    # 2. Build Dataset
    if debug or dataset_path is None:
        logger.info("Running in DEBUG / Demo mode with synthetic data.")
        dataset = SentenceISLDataset(vocab=vocab, debug_mode=True, debug_num_samples=DEBUG_NUM_SAMPLES)
    else:
        logger.info(f"Loading dataset from: {dataset_path}")
        dataset = SentenceISLDataset(
            keypoints_dir=dataset_path,
            annotations_file=annotations_path,
            vocab=vocab,
            uid_col=uid_col,
            text_col=text_col,
            keypoint_filename_pattern=pattern,
            debug_mode=False,
        )

    # Validate CTC targets before training
    if not debug:
        dataset.validate_ctc_targets()

    # Split into train / val
    val_size = max(1, int(len(dataset) * VALIDATION_SPLIT))
    train_size = len(dataset) - val_size
    train_ds, val_ds = random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=collate_variable_length,
        num_workers=NUM_WORKERS if not debug else 0,
        pin_memory=(device.type == "cuda"),
    )

    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=collate_variable_length,
        num_workers=NUM_WORKERS if not debug else 0,
        pin_memory=(device.type == "cuda"),
    )

    vocab_size = len(vocab)
    logger.info(f"Dataset summary: Train samples={len(train_ds)}, Val samples={len(val_ds)}, Vocab size={vocab_size}")

    # 3. Build Model
    model = SentenceISLModel(
        vocab_size=vocab_size,
        in_channels=3,
        stgcn_hidden=STGCN_HIDDEN_CHANNELS,
        stgcn_layers=STGCN_NUM_LAYERS,
        d_model=TRANSFORMER_D_MODEL,
        nhead=TRANSFORMER_NHEAD,
        transformer_layers=TRANSFORMER_NUM_LAYERS,
        dim_feedforward=TRANSFORMER_DIM_FEEDFORWARD,
        dropout=TRANSFORMER_DROPOUT,
    ).to(device)

    # 4. Loss & Optimizer
    criterion = nn.CTCLoss(blank=BLANK_TOKEN_ID, reduction="mean", zero_infinity=True)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs, eta_min=1e-6)
    scaler = torch.cuda.amp.GradScaler() if (USE_AMP and device.type == "cuda") else None

    # Resume if requested
    start_epoch = 0
    best_val_loss = float("inf")

    if resume_checkpoint and Path(resume_checkpoint).exists():
        logger.info(f"Resuming from checkpoint: {resume_checkpoint}")
        ckpt = torch.load(resume_checkpoint, map_location=device, weights_only=False)
        model.load_state_dict(ckpt["model_state_dict"])
        if "optimizer_state_dict" in ckpt and ckpt["optimizer_state_dict"]:
            optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        start_epoch = ckpt.get("epoch", 0) + 1
        best_val_loss = ckpt.get("val_loss", float("inf"))

    # 5. Training Loop
    save_dir = Path(checkpoint_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    best_ckpt_path = save_dir / "best.pt"
    latest_ckpt_path = save_dir / "latest.pt"

    logger.info(f"Starting training for {num_epochs} epochs...")

    for epoch in range(start_epoch, num_epochs):
        train_loss = train_one_epoch(
            model=model,
            dataloader=train_loader,
            criterion=criterion,
            optimizer=optimizer,
            scaler=scaler,
            device=device,
        )
        val_loss = validate(model=model, dataloader=val_loader, criterion=criterion, device=device)
        scheduler.step()

        logger.info(
            f"Epoch [{epoch + 1}/{num_epochs}] | Train CTC Loss: {train_loss:.4f} | Val CTC Loss: {val_loss:.4f} | LR: {scheduler.get_last_lr()[0]:.6f}"
        )

        # Save latest checkpoint
        model.save_checkpoint(
            filepath=latest_ckpt_path,
            vocab=vocab,
            epoch=epoch,
            optimizer=optimizer,
            val_loss=val_loss,
        )

        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            model.save_checkpoint(
                filepath=best_ckpt_path,
                vocab=vocab,
                epoch=epoch,
                optimizer=optimizer,
                val_loss=val_loss,
            )
            logger.info(f"⭐ New best model saved to: {best_ckpt_path} (Val Loss: {best_val_loss:.4f})")

    logger.info(f"Training completed successfully! Best checkpoint at: {best_ckpt_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Continuous ISL Sentence Recognition Model")
    parser.add_argument("--data_dir", type=str, default=None, help="Directory containing preprocessed keypoints (.npy/.npz)")
    parser.add_argument("--annotations", type=str, default=None, help="Path to annotations.csv / annotations.json")
    parser.add_argument("--vocab_path", type=str, default=None, help="Path to prebuilt vocabulary JSON")
    parser.add_argument("--uid_col", type=str, default=CSV_UID_COLUMN, help="UID column name in CSV")
    parser.add_argument("--text_col", type=str, default=CSV_TEXT_COLUMN, help="English transcript text column name in CSV")
    parser.add_argument("--min_freq", type=int, default=MIN_TOKEN_FREQ, help="Minimum token frequency for vocabulary")
    parser.add_argument("--pattern", type=str, default=KEYPOINT_FILENAME_PATTERN, help="Keypoint filename pattern")
    parser.add_argument("--checkpoint_dir", type=str, default=str(CHECKPOINT_DIR), help="Output checkpoint directory")
    parser.add_argument("--epochs", type=int, default=NUM_EPOCHS, help="Number of epochs")
    parser.add_argument("--batch_size", type=int, default=BATCH_SIZE, help="Batch size")
    parser.add_argument("--lr", type=float, default=LEARNING_RATE, help="Learning rate")
    parser.add_argument("--debug", action="store_true", default=DEBUG_MODE, help="Run on synthetic smoke-test dataset")
    parser.add_argument("--resume", type=str, default=None, help="Path to checkpoint to resume from")

    args = parser.parse_args()

    run_training(
        dataset_path=args.data_dir,
        annotations_path=args.annotations,
        checkpoint_dir=args.checkpoint_dir,
        vocab_path=args.vocab_path,
        uid_col=args.uid_col,
        text_col=args.text_col,
        min_token_freq=args.min_freq,
        pattern=args.pattern,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        debug=args.debug,
        resume_checkpoint=args.resume,
    )
