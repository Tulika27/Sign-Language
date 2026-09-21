import json
import os
import sys
import tempfile

import cv2
import mediapipe as mp
import numpy as np
import torch
from flask import Flask, jsonify, request
from flask_cors import CORS


INCLUDE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "word-model-test", "INCLUDE")
)
sys.path.insert(0, INCLUDE_DIR)

from configs import TransformerConfig
from models import Transformer


app = Flask(__name__)
CORS(app)

LABEL_MAP_PATH = os.path.join(INCLUDE_DIR, "label_maps", "label_map_include.json")
MODEL_PATH = os.path.join(INCLUDE_DIR, "include_no_cnn_transformer_large.pth")
MAX_FRAME_LEN = 169
FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080
MIN_FRAME_COUNT = 8

with open(LABEL_MAP_PATH, "r") as label_file:
    label_map = json.load(label_file)
id_to_label = {class_id: label for label, class_id in label_map.items()}

if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")

config = TransformerConfig(size="large", max_position_embeddings=256)
model = Transformer(config=config, n_classes=len(label_map)).to(device)
checkpoint = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
model.load_state_dict(checkpoint["model"])
model.eval()

mp_hands = mp.solutions.hands
mp_pose = mp.solutions.pose


def landmark_xy(landmarks, limit=None):
    if landmarks is None:
        return [], []
    points = landmarks.landmark[:limit] if limit else landmarks.landmark
    return (
        [landmark.x for landmark in points],
        [landmark.y for landmark in points],
    )


def assign_hands(hand_results, pose_x, pose_y):
    hands = [landmark_xy(hand) for hand in (hand_results.multi_hand_landmarks or [])]
    hand_slots = [([], []), ([], [])]

    if len(hands) == 2 and len(pose_x) > 16:
        left_wrist = (pose_x[15], pose_y[15])
        right_wrist = (pose_x[16], pose_y[16])
        distances = []
        for hand_x, hand_y in hands:
            wrist = (hand_x[0], hand_y[0])
            left_distance = (left_wrist[0] - wrist[0]) ** 2 + (left_wrist[1] - wrist[1]) ** 2
            right_distance = (right_wrist[0] - wrist[0]) ** 2 + (right_wrist[1] - wrist[1]) ** 2
            distances.append((left_distance, right_distance))
        left_index = 0 if distances[0][0] <= distances[1][0] else 1
        right_index = 1 - left_index
        hand_slots = [hands[left_index], hands[right_index]]
    elif hands:
        if len(pose_x) > 16:
            hand_x, hand_y = hands[0]
            hand_wrist = (hand_x[0], hand_y[0])
            left_distance = (pose_x[15] - hand_wrist[0]) ** 2 + (pose_y[15] - hand_wrist[1]) ** 2
            right_distance = (pose_x[16] - hand_wrist[0]) ** 2 + (pose_y[16] - hand_wrist[1]) ** 2
            hand_slots[0 if left_distance <= right_distance else 1] = hands[0]
        else:
            hand_slots[0] = hands[0]
        if len(hands) > 1:
            hand_slots[1] = hands[1]

    return hand_slots


def collect_frame_keypoints(image, hands, pose):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    hand_results = hands.process(image_rgb)
    pose_results = pose.process(image_rgb)

    pose_x, pose_y = landmark_xy(pose_results.pose_landmarks, limit=25)
    hand_slots = assign_hands(hand_results, pose_x, pose_y)

    pose_x = pose_x if len(pose_x) == 25 else [np.nan] * 25
    pose_y = pose_y if len(pose_y) == 25 else [np.nan] * 25
    frame = []
    for x_values, y_values, expected_count in [
        (pose_x, pose_y, 25),
        (hand_slots[0][0], hand_slots[0][1], 21),
        (hand_slots[1][0], hand_slots[1][1], 21),
    ]:
        if len(x_values) != expected_count:
            x_values = [np.nan] * expected_count
            y_values = [np.nan] * expected_count
        for x_value, y_value in zip(x_values, y_values):
            frame.extend((x_value, y_value))
    return frame


def interpolate_and_prepare(frames):
    values = np.asarray(frames, dtype=np.float32).reshape(-1, 67, 2)
    for landmark_index in range(values.shape[1]):
        for coordinate_index in range(2):
            track = values[:, landmark_index, coordinate_index]
            valid = ~np.isnan(track)
            if valid.any():
                valid_indices = np.flatnonzero(valid)
                values[:, landmark_index, coordinate_index] = np.interp(
                    np.arange(len(track)), valid_indices, track[valid]
                )
            else:
                values[:, landmark_index, coordinate_index] = 0

    values[:, :, 0] *= FRAME_WIDTH
    values[:, :, 1] *= FRAME_HEIGHT
    sequence = values.reshape(values.shape[0], 134)
    if len(sequence) > MAX_FRAME_LEN:
        sequence = sequence[-MAX_FRAME_LEN:]
    padded = np.zeros((MAX_FRAME_LEN, 134), dtype=np.float32)
    padded[: len(sequence)] = sequence
    return torch.from_numpy(padded).unsqueeze(0)


@app.get("/labels")
def labels():
    return jsonify({"labels": sorted(label_map.keys())})


def predict_from_frames(frames):
    input_tensor = interpolate_and_prepare(frames).to(device)
    with torch.no_grad():
        logits = model(input_tensor)
        probabilities = torch.softmax(logits, dim=-1)
        confidence, predicted_id = torch.max(probabilities, dim=-1)

    class_id = int(predicted_id.item())
    return {
        "class_id": class_id,
        "label": id_to_label[class_id],
        "confidence": round(float(confidence.item()), 4),
        "frame_count": len(frames),
    }


@app.post("/predict/word")
def predict_word():
    uploaded_frames = request.files.getlist("frames")
    uploaded_video = request.files.get("video")
    if not uploaded_frames and not uploaded_video:
        return jsonify({"error": "Provide webcam frames or a video file."}), 400
    if uploaded_frames and len(uploaded_frames) < MIN_FRAME_COUNT:
        return jsonify({"error": f"Capture at least {MIN_FRAME_COUNT} frames."}), 400

    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    temporary_video_path = None
    try:
        frames = []
        if uploaded_video:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".video") as temporary_video:
                uploaded_video.save(temporary_video.name)
                temporary_video_path = temporary_video.name
            capture = cv2.VideoCapture(temporary_video_path)
            while len(frames) < MAX_FRAME_LEN:
                success, image = capture.read()
                if not success:
                    break
                frames.append(collect_frame_keypoints(image, hands, pose))
            capture.release()
        else:
            for uploaded_frame in uploaded_frames[:MAX_FRAME_LEN]:
                image = cv2.imdecode(
                    np.frombuffer(uploaded_frame.read(), np.uint8), cv2.IMREAD_COLOR
                )
                if image is None:
                    continue
                frames.append(collect_frame_keypoints(image, hands, pose))
        if len(frames) < MIN_FRAME_COUNT:
            if uploaded_video:
                return jsonify({"error": "Video is too short. Please upload a longer video."}), 400
            return jsonify({"error": "The captured frames could not be decoded."}), 400
        return jsonify(predict_from_frames(frames))
    except Exception as error:
        return jsonify({"error": str(error)}), 500
    finally:
        hands.close()
        pose.close()
        if temporary_video_path and os.path.exists(temporary_video_path):
            os.remove(temporary_video_path)


if __name__ == "__main__":
    app.run(port=4996)