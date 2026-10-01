"""
hand_tracker.py
Finds hands with MediaPipe (Tasks API) and returns their landmarks.
Used by BOTH the data collection script and the live app,
so the data is always processed exactly the same way.

The first time it runs, it downloads the hand model file (about 8 MB)
into the models/ folder. After that it works offline.
"""

import time
import urllib.request
from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

import config

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
)

# Which points connect to draw the hand skeleton (MediaPipe's 21-point layout)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),           # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),           # index
    (5, 9), (9, 10), (10, 11), (11, 12),      # middle
    (9, 13), (13, 14), (14, 15), (15, 16),    # ring
    (13, 17), (17, 18), (18, 19), (19, 20),   # pinky
    (0, 17),                                  # palm edge
]


def _get_model_path():
    """Download the hand model once, then reuse it."""
    model_dir = Path(config.MODEL_DIR)
    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / "hand_landmarker.task"
    if not path.exists():
        print("Downloading MediaPipe hand model (first run only)...")
        try:
            urllib.request.urlretrieve(MODEL_URL, path)
        except Exception as e:
            raise RuntimeError(
                f"Could not download the model: {e}\n"
                f"Download it manually from:\n{MODEL_URL}\n"
                f"and save it as: {path}"
            )
        print("Done.")
    return str(path)


class HandTracker:
    def __init__(self):
        options = vision.HandLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=_get_model_path()),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=config.MAX_NUM_HANDS,
            min_hand_detection_confidence=config.MIN_DETECTION_CONF,
            min_hand_presence_confidence=config.MIN_TRACKING_CONF,
            min_tracking_confidence=config.MIN_TRACKING_CONF,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._start = time.monotonic()
        self._last_ts = -1

    def process(self, frame_bgr):
        """
        Find hands in a frame.

        Returns a dict like:
          {"Right": {"points": (21,3) array in pixels, "score": 0.98,
                     "height": 0.0-1.0 (0 = top of screen),
                     "x": 0.0-1.0 (0 = left of screen),
                     "size": palm size, bigger = closer to camera},
           "Left":  {...}}
        A hand that isn't visible is simply missing from the dict.

        Note: MediaPipe assumes a mirrored (selfie) image when it decides Left/Right,
        so keep config.MIRROR_VIEW = True for correct labels.
        """
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # VIDEO mode needs a timestamp (ms) that always increases
        ts = int((time.monotonic() - self._start) * 1000)
        if ts <= self._last_ts:
            ts = self._last_ts + 1
        self._last_ts = ts

        result = self._landmarker.detect_for_video(image, ts)

        hands = {}
        for lm_list, handed in zip(result.hand_landmarks, result.handedness):
            label = handed[0].category_name   # "Left" or "Right"
            if config.SWAP_HANDEDNESS:
                label = "Left" if label == "Right" else "Right"
            score = handed[0].score

            # Convert to pixel units so x and y use the same scale
            points = np.array(
                [[p.x * w, p.y * h, p.z * w] for p in lm_list], dtype=np.float32
            )

            # If two hands get the same label, keep the more confident one
            if label in hands and hands[label]["score"] >= score:
                continue

            hands[label] = {
                "points": points,
                "score": score,
                "height": float(points[:, 1].mean() / h),
                "x": float(points[:, 0].mean() / w),
                # palm size (wrist -> middle knuckle) relative to screen height:
                # bigger = hand is closer to the camera
                "size": float(np.linalg.norm(points[9, :2] - points[0, :2]) / h),
            }
        return hands

    def draw(self, frame_bgr, hands):
        """Draw hand skeletons and labels on the frame."""
        for label, hand in hands.items():
            color = (0, 200, 255) if label == config.MELODY_HAND else (255, 150, 0)
            pts = hand["points"][:, :2].astype(int)
            for a, b in HAND_CONNECTIONS:
                cv2.line(frame_bgr, tuple(pts[a]), tuple(pts[b]), color, 2)
            for x, y in pts:
                cv2.circle(frame_bgr, (int(x), int(y)), 4, (255, 255, 255), -1)
            wx, wy = pts[0]
            cv2.putText(frame_bgr, f"{label} ({hand['score']:.2f})", (int(wx) - 40, int(wy) + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    def close(self):
        self._landmarker.close()


def normalize_landmarks(points):
    """
    Turn 21 hand points into 63 numbers that describe the hand SHAPE only:
      1. Move the wrist to (0, 0, 0)  -> position on screen doesn't matter
      2. Divide by hand size          -> distance from camera doesn't matter
    This is the input for the sign classifier.
    """
    pts = points - points[0]                       # wrist (point 0) at origin
    size = np.linalg.norm(pts[9, :2])              # wrist -> middle finger knuckle
    if size < 1e-6:
        size = 1.0
    return (pts / size).flatten()


def crop_hand(frame_bgr, points, margin=0.25, out_size=224):
    """
    Cut a square image around the hand (for the optional image-based CNN later).
    Returns None if the crop would be empty.
    """
    h, w = frame_bgr.shape[:2]
    x_min, y_min = points[:, 0].min(), points[:, 1].min()
    x_max, y_max = points[:, 0].max(), points[:, 1].max()

    side = max(x_max - x_min, y_max - y_min) * (1 + 2 * margin)
    cx, cy = (x_min + x_max) / 2, (y_min + y_max) / 2

    x1, y1 = int(max(cx - side / 2, 0)), int(max(cy - side / 2, 0))
    x2, y2 = int(min(cx + side / 2, w)), int(min(cy + side / 2, h))
    if x2 <= x1 or y2 <= y1:
        return None

    crop = frame_bgr[y1:y2, x1:x2]
    return cv2.resize(crop, (out_size, out_size))