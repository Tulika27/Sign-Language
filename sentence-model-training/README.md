# Continuous ISL Sentence Model Training

This directory contains the Kaggle-ready and local training, evaluation, and inference pipeline for the **Continuous Indian Sign Language (ISL) Sentence Recognition Model**.

> [!IMPORTANT]
> **Dataset & Terminology Clarification:**
> The currently available sentence annotations are English transcript tokens. They are used as sequence targets for this experimental CTC training setup. They should not be interpreted as manually annotated ISL glosses.
> 
> The pipeline maps:
> $$\text{Continuous ISL Video} \longrightarrow \text{MediaPipe (543 3D landmarks)} \longrightarrow \text{ST-GCN + Transformer} \longrightarrow \text{CTC} \longrightarrow \text{English Word Tokens} \longrightarrow \text{Formatted Sentence}$$

---

## 🏗️ Architecture Overview

The system processes continuous sign language video sequences without requiring isolated-word segmentation:

```
Continuous ISL Video (.mp4 / .avi)
  │
  ▼
[MediaPipe Holistic] ──────────► Extracts 543 3D Landmarks/Frame (33 Pose + 468 Face + 42 Hands)
  │                              Tensor Shape: (N, 3, T, 543)
  ▼
[ST-GCN Encoder] ──────────────► Spatial Graph Convolutions + 1D Temporal Convolutions
  │                              Tensor Shape: (N, T, d_model=256)
  ▼
[Temporal Transformer] ────────► Multi-Head Self-Attention across frames
  │                              Tensor Shape: (N, T, d_model=256)
  ▼
[CTC Projection Head] ─────────► Linear Classification Layer -> Log-Softmax Logits
  │                              Tensor Shape: (T, N, vocab_size)
  ▼
[PyTorch CTCLoss] ─────────────► Alignment-free training (Blank token at ID 0)
  │
  ▼
[Greedy CTC Decoder] ──────────► Argmax -> Collapse duplicates -> Remove blanks -> Word-token sequence
  │                              e.g., ["good", "morning"]
  ▼
[Sentence Formatter] ──────────► Formatted Punctuated English Sentence
                                 e.g., "Good morning."
```

---

## 📁 Directory Structure

```
sentence-model-training/
├── README.md                      # Complete execution and dataset guide
├── requirements.txt               # Dependencies
├── config.py                      # Configurable paths, CSV columns, & hyperparameters
├── notebooks/
│   ├── 01_extract_keypoints.ipynb # Step 1: Batch keypoint extraction (MediaPipe Holistic)
│   ├── 02_prepare_dataset.ipynb   # Step 2: Vocabulary generation & CSV dataset preparation
│   ├── 03_train_sentence_model.ipynb # Step 3: ST-GCN + Transformer + CTC training
│   └── 04_evaluate_sentence_model.ipynb # Step 4: WER evaluation & inference demo
├── src/
│   ├── __init__.py                # Package exports
│   ├── graph.py                   # 543-node skeletal graph & adjacency matrix
│   ├── preprocessing.py           # MediaPipe Holistic keypoint extraction
│   ├── vocabulary.py              # English word-token vocabulary & tokenization (Blank ID 0)
│   ├── dataset.py                 # PyTorch Dataset, CSV loader, keypoint resolver & CTC checks
│   ├── stgcn.py                   # ST-GCN spatial-temporal convolutional network
│   ├── transformer.py             # Temporal Transformer sequence encoder
│   ├── ctc_decoder.py             # CTC Head & Greedy CTC Decoder
│   ├── formatter.py               # Token-to-English sentence formatter
│   ├── model.py                   # Complete SentenceISLModel architecture
│   ├── train.py                   # Training loop with mixed precision & checkpointing
│   ├── evaluate.py                # Word Error Rate (WER) and metrics calculation
│   ├── inference.py               # End-to-end inference pipeline
│   └── smoke_test.py              # 13-point verification & smoke testing suite
├── checkpoints/                   # Saved model weights (e.g., best.pt, latest.pt)
│   └── .gitkeep
└── outputs/                       # Generated vocabulary (gloss_vocab.json) & logs
    └── .gitkeep
```

---

## 📊 CSV Annotation Format

The dataset pipeline accepts standard CSV files mapping sample identifiers (UID) to English sentence transcripts:

| uid | english | split (optional) |
| :--- | :--- | :--- |
| `sample_001` | `GOOD MORNING` | `train` |
| `sample_002` | `HOW ARE YOU?` | `train` |
| `sample_003` | `THANK YOU!` | `val` |

### Keypoint File Resolution
The sample `uid` resolves to pre-extracted landmark files using `KEYPOINT_FILENAME_PATTERN`:
- `sample_001` $\to$ `keypoints/sample_001.npy` (or `.npz`)
- If a referenced file is missing, the loader raises a clear `FileNotFoundError` identifying the missing UID and expected path.

### Tokenization & Vocabulary
- **Text Normalization:** Lowercases text, removes punctuation, and splits into clean word tokens.
  - `"How are you?"` $\to$ `["how", "are", "you"]`
  - `"THANK YOU!"` $\to$ `["thank", "you"]`
- **Reserved Special Tokens:**
  - `<blank>` at ID `0` (Reserved for CTC decoding)
  - `<unk>` at ID `1` (Out-of-vocabulary unknown token)
- **Minimum Frequency (`min_freq`):** Tokens with count $< \text{min\_freq}$ are filtered out and map to `<unk>` during training.

### CTC Sequence Length Safety Checks
For every sample, the loader verifies the fundamental CTC mathematical constraint:
$$\text{input sequence length } (T) \ge \text{target sequence length } (L)$$
Violating samples are flagged and logged to prevent dataset corruption or training failures.

---

## 🚀 Quick Smoke Test

Verify all 13 pipeline components locally using the built-in smoke test:

```bash
python sentence-model-training/src/smoke_test.py
```

This verifies:
1. LandmarkGraph adjacency matrix $(3, 543, 543)$
2. English transcript tokenization and punctuation stripping
3. Vocabulary generation from CSV with `min_freq` filtering and JSON serialization
4. Vocabulary token-to-ID conversion with reserved blank ID 0
5. CSV dataset loading and keypoint file resolution
6. CTC sequence length validation ($T \ge L$)
7. Dynamic variable-length dataset batch collation
8. ST-GCN forward pass $(N, 3, T, 543) \to (N, T, d\_model)$
9. Temporal Transformer forward pass $(N, T, d\_model) \to (N, T, d\_model)$
10. Complete model CTC output shape $(T, N, \text{vocab\_size})$
11. PyTorch `CTCLoss` forward and backward passes
12. Greedy CTC decoding of duplicate/blank tokens $\to$ formatted English sentence
13. Model checkpoint saving and loading

---

## ⚡ Kaggle Step-by-Step Training Guide

### Step 1: Create a Kaggle Notebook
1. Go to [Kaggle](https://www.kaggle.com/) and click **New Notebook**.
2. Under **Notebook Options**:
   * **Accelerator**: Select **GPU T4 x2** or **GPU P100**.
   * **Internet**: Turn **ON**.

### Step 2: Add Dataset to Kaggle
* Click **+ Add Input** in the top-right corner.
* Attach your continuous ISL dataset (e.g. **ISLTranslate** or **iSign**).

### Step 3: Copy Code into `/kaggle/working`
```bash
!git clone <YOUR_REPOSITORY_URL> /kaggle/working/repo
!cp -r /kaggle/working/repo/sentence-model-training /kaggle/working/
%cd /kaggle/working/sentence-model-training
!pip install -r requirements.txt
```

### Step 4: Extract Keypoints & Prepare Vocabulary
Run `notebooks/01_extract_keypoints.ipynb` to extract 543 landmarks per frame into `.npy` / `.npz`.
Run `notebooks/02_prepare_dataset.ipynb` to build the word vocabulary from the annotations CSV.

### Step 5: Start Training
Run `notebooks/03_train_sentence_model.ipynb` or execute via CLI:
```bash
python src/train.py \
    --data_dir /kaggle/working/keypoints_cache \
    --annotations /kaggle/input/isltranslate/annotations.csv \
    --uid_col uid \
    --text_col english \
    --checkpoint_dir /kaggle/working/checkpoints \
    --epochs 35 \
    --batch_size 8 \
    --lr 1e-4
```

### Step 6: Download Checkpoint
Download `best.pt` from `/kaggle/working/checkpoints/best.pt`.

---

## 🔒 Safety & Word Model Isolation
* This training module is completely self-contained in `sentence-model-training/`.
* No files under `API/Word-Model/` or `word-model-test/INCLUDE/` are modified.
* The existing isolated Word detection backend continues to operate independently on its 134-feature input format.
