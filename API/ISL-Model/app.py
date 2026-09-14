from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import mediapipe as mp
import copy
import itertools
import numpy as np
import pandas as pd
import string
from tensorflow import keras

app = Flask(__name__)
CORS(app)

# Load the trained Keras model
model = keras.models.load_model("model.h5")

# Create the label list
alphabet = ['1', '2', '3', '4', '5', '6', '7', '8', '9'] + list(string.ascii_uppercase)

# Setup MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    model_complexity=0,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

def calc_landmark_list(image, landmarks):
    image_width, image_height = image.shape[1], image.shape[0]
    landmark_point = []
    for _, landmark in enumerate(landmarks.landmark):
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)
        landmark_point.append([landmark_x, landmark_y])
    return landmark_point

def pre_process_landmark(landmark_list):
    temp_landmark_list = copy.deepcopy(landmark_list)
    base_x, base_y = temp_landmark_list[0][0], temp_landmark_list[0][1]
    for point in temp_landmark_list:
        point[0] -= base_x
        point[1] -= base_y
    flat = list(itertools.chain.from_iterable(temp_landmark_list))
    max_val = max(map(abs, flat)) or 1
    normalized = [n / max_val for n in flat]
    return normalized
@app.route('/predict/isl', methods=['POST'])
def predict():
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Read image
        img_bytes = file.read()
        np_arr = np.frombuffer(img_bytes, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        image = cv2.flip(image, 1)

        if image is None:
            return jsonify({"error": "Invalid image format"}), 400

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = hands.process(image_rgb)

        if not results.multi_hand_landmarks:
            return jsonify({"error": "No hand detected"}), 400

        detections = []

        for hand_landmarks in results.multi_hand_landmarks:
            # Get landmarks
            landmark_list = calc_landmark_list(image, hand_landmarks)
            normalized_landmarks = pre_process_landmark(landmark_list)
            df = pd.DataFrame([normalized_landmarks])

            # Bounding box
            x_coords = [point[0] for point in landmark_list]
            y_coords = [point[1] for point in landmark_list]
            x_min, x_max = min(x_coords), max(x_coords)
            y_min, y_max = min(y_coords), max(y_coords)

            # Prediction
            predictions = model.predict(df, verbose=0)
            predicted_class = int(np.argmax(predictions))
            confidence = float(np.max(predictions))
            label = alphabet[predicted_class]

            detections.append({
                "label": label,
                "confidence": round(confidence * 100, 2),
                "x1": x_min,
                "y1": y_min,
                "x2": x_max,
                "y2": y_max
            })

        return jsonify({ "detections": detections })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=4997)
