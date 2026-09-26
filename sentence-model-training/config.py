# =============================================================================
# Configuration for Continuous ISL Sentence Model Training
# =============================================================================

import os
from pathlib import Path

# -----------------------------------------------------------------------------
# Environment Detection (Kaggle vs Local)
# -----------------------------------------------------------------------------
IS_KAGGLE = os.path.exists("/kaggle")

if IS_KAGGLE:
    # Kaggle directory structure
    BASE_DIR = Path("/kaggle/working/sentence-model-training")
    DATASET_ROOT = Path("/kaggle/input")
    OUTPUT_DIR = Path("/kaggle/working/outputs")
    CHECKPOINT_DIR = Path("/kaggle/working/checkpoints")
    KEYPOINTS_CACHE_DIR = Path("/kaggle/working/keypoints_cache")
    KEYPOINT_ROOT = KEYPOINTS_CACHE_DIR
    ANNOTATION_ROOT = DATASET_ROOT
else:
    # Local workspace structure
    BASE_DIR = Path(__file__).resolve().parent
    DATASET_ROOT = BASE_DIR / "data"
    OUTPUT_DIR = BASE_DIR / "outputs"
    CHECKPOINT_DIR = BASE_DIR / "checkpoints"
    KEYPOINTS_CACHE_DIR = BASE_DIR / "keypoints_cache"
    KEYPOINT_ROOT = KEYPOINTS_CACHE_DIR
    ANNOTATION_ROOT = DATASET_ROOT

# Ensure output directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)
os.makedirs(KEYPOINTS_CACHE_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# Dataset & Annotation Paths (Configurable for ISLTranslate, iSign, etc.)
# -----------------------------------------------------------------------------
VIDEO_DATA_DIR = DATASET_ROOT / "isl_videos"
ANNOTATIONS_FILE = DATASET_ROOT / "annotations.csv"  # Default CSV annotation mapping
VOCABULARY_FILE = OUTPUT_DIR / "gloss_vocab.json"

GLOSS_CSV_PATH = DATASET_ROOT / "datasets" / "drblack00" / "isl-csltr-indian-sign-language-dataset" / \
    "ISL_CSLRT_Corpus" / "ISL_CSLRT_Corpus" / "corpus_csv_files" / "ISL Corpus sign glosses.csv"

CSV_GLOSS_COLUMN = "SIGN GLOSSES"
CSV_ENGLISH_COLUMN = "Sentence"

# CSV Annotation Column Config
CSV_UID_COLUMN = "uid"           # Column containing video/sample identifier
CSV_TEXT_COLUMN = "english"      # Column containing English sentence transcript
CSV_SPLIT_COLUMN = "split"       # Optional column indicating 'train', 'val', or 'test'

# Split CSV Paths (if provided as separate files)
TRAIN_CSV = None
VAL_CSV = None
TEST_CSV = None

# Keypoint File Resolution Config
# Configurable filename template for resolving sample UID to keypoint file
KEYPOINT_FILENAME_PATTERN = "{uid}.npy"  # Alternative: "{uid}.npz" or "{uid}_keypoints.npy"

# Minimum frequency for vocabulary token retention
MIN_TOKEN_FREQ = 1

# -----------------------------------------------------------------------------
# Keypoint Extraction Config (MediaPipe Holistic)
# -----------------------------------------------------------------------------
NUM_POSE_LANDMARKS = 33
NUM_FACE_LANDMARKS = 468
NUM_LEFT_HAND_LANDMARKS = 21
NUM_RIGHT_HAND_LANDMARKS = 21

TOTAL_LANDMARKS = (
    NUM_POSE_LANDMARKS
    + NUM_FACE_LANDMARKS
    + NUM_LEFT_HAND_LANDMARKS
    + NUM_RIGHT_HAND_LANDMARKS
)  # 543 landmarks

NUM_CHANNELS = 3  # (x, y, z)

# MediaPipe confidence settings
MP_DETECTION_CONFIDENCE = 0.5
MP_TRACKING_CONFIDENCE = 0.5
MP_MODEL_COMPLEXITY = 2

# -----------------------------------------------------------------------------
# Sequence Length Config & CTC Constraints
# -----------------------------------------------------------------------------
MIN_SEQ_LENGTH = 8      # Minimum frames required to consider a sample valid
MAX_SEQ_LENGTH = 512    # Maximum frames to pad/truncate

# -----------------------------------------------------------------------------
# Model Architecture Hyperparameters
# -----------------------------------------------------------------------------
# ST-GCN Spatial-Temporal Graph Convolution
STGCN_IN_CHANNELS = NUM_CHANNELS      # 3
STGCN_HIDDEN_CHANNELS = 64
STGCN_NUM_LAYERS = 2
STGCN_TEMPORAL_KERNEL_SIZE = 9
STGCN_DROPOUT = 0.1

# Temporal Transformer
TRANSFORMER_D_MODEL = 256
TRANSFORMER_NHEAD = 8
TRANSFORMER_NUM_LAYERS = 4
TRANSFORMER_DIM_FEEDFORWARD = 1024
TRANSFORMER_DROPOUT = 0.1
TRANSFORMER_MAX_POS = 1024

# CTC Decoder
BLANK_TOKEN_ID = 0      # Reserved CTC blank index
DEFAULT_VOCAB_SIZE = 1200  # Will be dynamically sized based on vocabulary.json

# -----------------------------------------------------------------------------
# Training Hyperparameters
# -----------------------------------------------------------------------------
BATCH_SIZE = 8          # Set to 8 or 16 depending on GPU VRAM (e.g. 16GB on T4)
NUM_EPOCHS = 40
LEARNING_RATE = 1e-4
WEIGHT_DECAY = 1e-4
GRADIENT_ACCUMULATION_STEPS = 2
USE_AMP = True          # Automatic Mixed Precision for faster GPU training
NUM_WORKERS = 2
VALIDATION_SPLIT = 0.1
TEST_SPLIT = 0.1
SEED = 42

# -----------------------------------------------------------------------------
# Debug & Smoke Test Mode
# -----------------------------------------------------------------------------
# When True, the training pipeline runs on a tiny synthetic / subset dataset
DEBUG_MODE = False
DEBUG_NUM_SAMPLES = 16
