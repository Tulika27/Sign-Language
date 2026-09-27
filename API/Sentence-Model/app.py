import json
import os
import sys
import tempfile

import cv2
from flask import Flask, jsonify, request
from flask_cors import CORS
import mediapipe as mp
import numpy as np
import torch

TRAINING_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "sentence-model-training")
)
if TRAINING_DIR not in sys.path:
    sys.path.insert(0, TRAINING_DIR)

from src.model import SentenceISLModel
from src.vocabulary import GlossVocabulary
from src.ctc_decoder import GreedyCTCDecoder
from src.formatter import format_gloss_to_english

CHECKPOINT_PATH = os.path.join(TRAINING_DIR, "checkpoints", "final_epoch150.pt")
VOCAB_PATH = os.path.join(TRAINING_DIR, "outputs", "gloss_vocab.json")

# Device selection: MPS / CUDA / CPU fallback (following Word-Model pattern)
if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    device = torch.device("mps")
elif torch.cuda.is_available():
    device = torch.device("cuda")
else:
    device = torch.device("cpu")

vocab = GlossVocabulary.load_from_json(VOCAB_PATH)
model = SentenceISLModel(vocab_size=len(vocab))
checkpoint = torch.load(CHECKPOINT_PATH, map_location=device, weights_only=False)
model.load_state_dict(checkpoint["model_state_dict"])
model.to(device)
model.eval()

decoder = GreedyCTCDecoder(vocab=vocab, blank_id=vocab.blank_id)

app = Flask(__name__)
CORS(app)


def extract_keypoints_from_video(video_path):
    """
    Extract 543 3D landmarks per frame using MediaPipe Holistic:
    - 33 Pose landmarks
    - 468 Face landmarks
    - 21 Left Hand landmarks
    - 21 Right Hand landmarks
    Returns a numpy float32 array of shape (T, 543, 3).
    """
    mp_holistic = mp.solutions.holistic
    holistic = mp_holistic.Holistic(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    cap = cv2.VideoCapture(video_path)
    frames_keypoints = []

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = holistic.process(frame_rgb)

            keypoints = np.zeros((543, 3), dtype=np.float32)
            idx = 0

            # 1. Pose landmarks (33)
            if results.pose_landmarks:
                for lm in results.pose_landmarks.landmark:
                    keypoints[idx] = [lm.x, lm.y, lm.z]
                    idx += 1
            else:
                idx += 33

            # 2. Face landmarks (468)
            if results.face_landmarks:
                for lm in results.face_landmarks.landmark:
                    keypoints[idx] = [lm.x, lm.y, lm.z]
                    idx += 1
            else:
                idx += 468

            # 3. Left Hand landmarks (21)
            if results.left_hand_landmarks:
                for lm in results.left_hand_landmarks.landmark:
                    keypoints[idx] = [lm.x, lm.y, lm.z]
                    idx += 1
            else:
                idx += 21

            # 4. Right Hand landmarks (21)
            if results.right_hand_landmarks:
                for lm in results.right_hand_landmarks.landmark:
                    keypoints[idx] = [lm.x, lm.y, lm.z]
                    idx += 1
            else:
                idx += 21

            frames_keypoints.append(keypoints)
    finally:
        cap.release()
        holistic.close()

    if len(frames_keypoints) == 0:
        return np.zeros((1, 543, 3), dtype=np.float32)

    return np.stack(frames_keypoints, axis=0).astype(np.float32)


@app.post("/predict/sentence")
def predict_sentence():
    temporary_video_path = None
    try:
        if "video" not in request.files:
            return jsonify({"error": "No video file provided under field name 'video'."}), 400

        uploaded_video = request.files["video"]
        if uploaded_video.filename == "":
            return jsonify({"error": "No video selected."}), 400

        original_filename = uploaded_video.filename or "upload.mp4"
        _, ext = os.path.splitext(original_filename)
        if not ext:
            ext = ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            uploaded_video.save(temp_file.name)
            temporary_video_path = temp_file.name

        keypoints = extract_keypoints_from_video(temporary_video_path)  # Shape: (T, 543, 3)
        t_len = keypoints.shape[0]

        # Convert to torch tensor of shape (1, 3, T, 543)
        # permute (T, 543, 3) -> (3, T, 543) and add batch dimension
        keypoints_tensor = (
            torch.from_numpy(keypoints)
            .permute(2, 0, 1)
            .unsqueeze(0)
            .float()
            .to(device)
        )
        input_lengths = torch.tensor([t_len], dtype=torch.long, device=device)

        with torch.no_grad():
            _, logits = model(keypoints_tensor, input_lengths=input_lengths)
            decoded_sequences = decoder.decode_logits(logits, sequence_lengths=input_lengths)

        pred_tokens = decoded_sequences[0] if decoded_sequences else []
        gloss_text = " ".join(pred_tokens)
        english_text = format_gloss_to_english(gloss_text)

        return jsonify({
            "gloss": gloss_text,
            "english": english_text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if temporary_video_path and os.path.exists(temporary_video_path):
            try:
                os.remove(temporary_video_path)
            except OSError:
                pass


if __name__ == "__main__":
    app.run(port=5002, debug=True)
