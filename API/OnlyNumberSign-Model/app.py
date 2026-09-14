from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
from ultralytics import YOLO  # or your own model import
from PIL import Image
import io

app = Flask(__name__)
CORS(app)

# Load your trained YOLO model
model = YOLO("best.pt")  # or your .pt path

@app.route("/predict/number", methods=["POST"])
def predict_digit():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    try:
        # Read image from request and convert to OpenCV format
        image_file = request.files["image"]
        image_bytes = image_file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("L")  # Convert to grayscale (L mode)
        image_np = np.array(image)

        # If model expects 3-channel input (like YOLO), convert grayscale to BGR
        image_bgr = cv2.cvtColor(image_np, cv2.COLOR_GRAY2BGR)

        # Run prediction
        results = model.predict(image_bgr, conf=0.25)[0]

        detections = []
        if results.boxes is not None:
            for box in results.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = round(float(box.conf[0]) * 100, 2)
                label_index = int(box.cls[0])
                label = model.names[label_index]
                detections.append({
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "confidence": confidence,
                    "label": label
                })

        return jsonify({"detections": detections})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=4998)
