from flask import Flask, request, jsonify
from flask_cors import CORS
from ultralytics import YOLO
import cv2
import numpy as np
import math
import io

app = Flask(__name__)
CORS(app) 

model = YOLO("americanAlphabest.pt")  # Load trained YOLO model

@app.route('/predict/americanSignLanguage', methods=['POST'])
def translate():
    try:
        # Check if the request contains a file
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Convert file to OpenCV format
        img_bytes = file.read()
        img_np = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"error": "Invalid image format"}), 400

        # Run YOLO inference
        results = model(img)

        detections = []
        for r in results:
            for box in r.boxes:
                class_id = int(box.cls)
                confidence = float(box.conf)
                x1, y1, x2, y2 = map(int, box.xyxy[0])  # Bounding box coordinates
                
                detections.append({
    "label": model.names[class_id],  # Keep label as just the class name
    "confidence": math.floor(confidence* 100),  # Send confidence as a separate numeric value
    "x1": x1,
    "y1": y1,
    "x2": x2,
    "y2": y2
})


        return jsonify({"detections": detections})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=4999)
