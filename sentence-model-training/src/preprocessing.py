"""
MediaPipe Holistic Keypoint Extractor for Continuous ISL Sentence Recognition.
Extracts 543 3D landmarks (x, y, z) per frame preserving temporal ordering.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

logger = logging.getLogger(__name__)


class MediaPipeHolisticExtractor:
    """
    Extracts 543 landmarks per frame using MediaPipe Holistic:
        - 33 Pose landmarks (0..32)
        - 468 Face landmarks (33..500)
        - 21 Left Hand landmarks (501..521)
        - 21 Right Hand landmarks (522..542)
    Total: 543 landmarks x 3 channels (x, y, z) = 1629 values per frame.
    """

    NUM_POSE = 33
    NUM_FACE = 468
    NUM_LEFT_HAND = 21
    NUM_RIGHT_HAND = 21
    TOTAL_LANDMARKS = 543
    NUM_CHANNELS = 3

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        model_complexity: int = 2,
    ):
        if not MEDIAPIPE_AVAILABLE:
            logger.warning("MediaPipe is not installed. Extractor will raise errors on video processing.")
            self.holistic = None
            return

        self.mp_holistic = mp.solutions.holistic
        self.holistic = self.mp_holistic.Holistic(
            static_image_mode=False,
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def extract_frame(self, frame_bgr: np.ndarray) -> np.ndarray:
        """
        Extract keypoints from a single BGR video frame.
        
        Returns:
            np.ndarray of shape (543, 3) with (x, y, z) normalized coordinates.
        """
        if self.holistic is None:
            raise RuntimeError("MediaPipe Holistic model is not initialized.")

        # Convert to RGB for MediaPipe
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.holistic.process(frame_rgb)

        keypoints = np.zeros((self.TOTAL_LANDMARKS, self.NUM_CHANNELS), dtype=np.float32)
        idx = 0

        # 1. Pose landmarks (33)
        if results.pose_landmarks:
            for lm in results.pose_landmarks.landmark:
                keypoints[idx] = [lm.x, lm.y, lm.z]
                idx += 1
        else:
            idx += self.NUM_POSE

        # 2. Face landmarks (468)
        if results.face_landmarks:
            for lm in results.face_landmarks.landmark:
                keypoints[idx] = [lm.x, lm.y, lm.z]
                idx += 1
        else:
            idx += self.NUM_FACE

        # 3. Left Hand landmarks (21)
        if results.left_hand_landmarks:
            for lm in results.left_hand_landmarks.landmark:
                keypoints[idx] = [lm.x, lm.y, lm.z]
                idx += 1
        else:
            idx += self.NUM_LEFT_HAND

        # 4. Right Hand landmarks (21)
        if results.right_hand_landmarks:
            for lm in results.right_hand_landmarks.landmark:
                keypoints[idx] = [lm.x, lm.y, lm.z]
                idx += 1
        else:
            idx += self.NUM_RIGHT_HAND

        return keypoints

    def extract_video(
        self,
        video_path: Union[str, Path],
        max_frames: Optional[int] = None,
    ) -> Tuple[np.ndarray, int]:
        """
        Extract keypoint sequence from a video file.
        
        Returns:
            keypoint_sequence: np.ndarray of shape (T, 543, 3)
            num_frames: Total processed frames (T)
        """
        video_path = str(video_path)
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Failed to open video file: {video_path}")

        frames_keypoints = []
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            kp = self.extract_frame(frame)
            frames_keypoints.append(kp)
            frame_count += 1

            if max_frames and frame_count >= max_frames:
                break

        cap.release()

        if len(frames_keypoints) == 0:
            # Fallback for empty/unreadable video: 1 zero frame
            keypoint_array = np.zeros((1, self.TOTAL_LANDMARKS, self.NUM_CHANNELS), dtype=np.float32)
        else:
            keypoint_array = np.stack(frames_keypoints, axis=0)  # Shape: (T, 543, 3)

        return keypoint_array, frame_count

    def close(self):
        """Release MediaPipe resources."""
        if self.holistic:
            self.holistic.close()
