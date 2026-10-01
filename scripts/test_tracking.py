"""
test_tracking.py
Step 1 test: Do both hands get tracked, and are Left/Right correct?
Raise your RIGHT hand -> it should say "Right" (orange text).
Press Q to quit.
"""

import time
import cv2

import config
from hand_tracker import HandTracker


def main():
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    if not cap.isOpened():
        print("Could not open camera. Try changing CAMERA_INDEX in config.py.")
        return

    tracker = HandTracker()
    prev = time.time()

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if config.MIRROR_VIEW:
            frame = cv2.flip(frame, 1)

        hands = tracker.process(frame)
        tracker.draw(frame, hands)

        # Show which hands are visible + right hand height
        info = f"Hands: {', '.join(hands.keys()) or 'none'}"
        if config.MELODY_HAND in hands:
            info += f" | Right hand height: {hands[config.MELODY_HAND]['height']:.2f}"
        now = time.time()
        fps = 1 / max(now - prev, 1e-6)
        prev = now

        cv2.putText(frame, info, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, f"FPS: {fps:.0f}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.imshow("Hand tracking test (Q to quit)", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
