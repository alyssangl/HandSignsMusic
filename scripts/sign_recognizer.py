"""
sign_recognizer.py
Loads the trained model and recognizes the right-hand sign in every frame.
Smooths the result so the sign doesn't flicker between frames.
"""

from collections import deque, Counter
from pathlib import Path

import joblib
import numpy as np

import config
from hand_tracker import normalize_landmarks

MODEL_PATH = Path(config.MODEL_DIR) / "sign_model.joblib"

HISTORY_SIZE = 5        # look at the last 5 frames
MIN_AGREE = 4           # at least 4 of them must agree to change the sign
MIN_CONFIDENCE = 0.6    # ignore predictions the model is unsure about


class SignRecognizer:
    def __init__(self):
        if not MODEL_PATH.exists():
            raise SystemExit(f"No model found at {MODEL_PATH}. Run train_model.py first.")
        saved = joblib.load(MODEL_PATH)
        self.model = saved["model"]
        self.model_name = saved.get("name", "model")
        self._history = deque(maxlen=HISTORY_SIZE)
        self.stable = None          # the accepted (smoothed) sign, None = no hand / rest
        self.confidence = 0.0

    def update(self, hand):
        """
        hand: the right-hand dict from HandTracker.process(), or None if not visible.
        Returns the stable sign ("1"-"7", "rest") or None if no hand.
        """
        if hand is None:
            raw, conf = None, 0.0
        else:
            feats = normalize_landmarks(hand["points"]).reshape(1, -1)
            probs = self.model.predict_proba(feats)[0]
            best = int(np.argmax(probs))
            raw, conf = self.model.classes_[best], float(probs[best])
            if conf < MIN_CONFIDENCE:
                raw = "rest"        # unsure -> treat as rest (no note)

        self._history.append(raw)
        self.confidence = conf

        # Only change the stable sign when most recent frames agree
        label, count = Counter(self._history).most_common(1)[0]
        if count >= MIN_AGREE:
            self.stable = label
        return self.stable