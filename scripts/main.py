"""
main.py
The live instrument:
    RIGHT hand -> melody (signs 1-7, hand height = octave)
    LEFT hand  -> chords (position in the grid on the left side)

Run from the HandSignsMusic folder:
    python scripts/main.py

Controls:
    [  /  ]   transpose down / up (change key)
    C         chords on / off
    Q         quit
"""

import time

import cv2

import config
from hand_tracker import HandTracker
from sign_recognizer import SignRecognizer
from sound_player import SoundPlayer
from melody_controller import MelodyController, ZONE_TOP, ZONE_BOTTOM
from chord_controller import ChordController
from music_utils import NOTE_NAMES

ORANGE = (0, 200, 255)
BLUE = (255, 150, 0)
WHITE = (255, 255, 255)
GRAY = (150, 150, 150)
DARK = (30, 30, 30)


def draw_zones(frame, active_octave):
    """Melody octave zones (right half of the screen)."""
    h, w = frame.shape[:2]
    for y_frac in (ZONE_TOP, ZONE_BOTTOM):
        y = int(y_frac * h)
        cv2.line(frame, (w // 2, y), (w, y), GRAY, 1, cv2.LINE_AA)

    zones = [(1, "HIGH", 0, ZONE_TOP), (0, "MID", ZONE_TOP, ZONE_BOTTOM), (-1, "LOW", ZONE_BOTTOM, 1)]
    for octave, name, top, bottom in zones:
        y = int((top + bottom) / 2 * h)
        color = ORANGE if octave == active_octave else GRAY
        cv2.putText(frame, name, (w - 110, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)


def draw_chord_grid(frame, chords):
    """Chord boxes (left side of the screen)."""
    if not chords.enabled:
        return
    h, w = frame.shape[:2]
    rows, cols = chords.grid_size()
    overlay = frame.copy()
    for r in range(rows):
        for c in range(cols):
            l, t, rr, b = chords.cell_rect(r, c)
            p1, p2 = (int(l * w), int(t * h)), (int(rr * w), int(b * h))
            if chords.cell == (r, c):
                cv2.rectangle(overlay, p1, p2, BLUE, -1)
            cv2.rectangle(frame, p1, p2, BLUE if chords.cell == (r, c) else GRAY, 2)
    cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)

    for r in range(rows):
        for c in range(cols):
            l, t, rr, b = chords.cell_rect(r, c)
            roman, name = chords.label(r, c)
            cx, cy = int((l + rr) / 2 * w), int((t + b) / 2 * h)
            color = WHITE if chords.cell == (r, c) else GRAY
            cv2.putText(frame, roman, (cx - 25, cy - 5), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
            cv2.putText(frame, name, (cx - 25, cy + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)


def draw_info(frame, melody, chords, recognizer, fps):
    h, w = frame.shape[:2]

    # Top bar
    cv2.rectangle(frame, (0, 0), (w, 60), DARK, -1)
    key = NOTE_NAMES[melody.transpose % 12]
    cv2.putText(frame, f"Key: {key}  (1 = {key})", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, WHITE, 2)
    cv2.putText(frame, f"FPS {fps:.0f}", (w - 130, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, GRAY, 2)

    # Bottom bar: chord (left) and melody note (middle)
    cv2.rectangle(frame, (0, h - 90), (w, h), DARK, -1)
    if time.monotonic() - melody.last_tap < 0.2:          # flash when a tap replays the note
        cv2.rectangle(frame, (int(w * 0.40), h - 88), (int(w * 0.72), h - 2), ORANGE, 3)
    cv2.putText(frame, f"Chord: {chords.chord_text}", (20, h - 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, BLUE, 2)
    cv2.putText(frame, melody.note_text, (int(w * 0.42), h - 30), cv2.FONT_HERSHEY_SIMPLEX, 1.6, ORANGE, 3)

    # Confidence bar
    conf = recognizer.confidence
    bar_w = 160
    x0, y0 = w - bar_w - 30, h - 55
    cv2.rectangle(frame, (x0, y0), (x0 + bar_w, y0 + 18), GRAY, 1)
    cv2.rectangle(frame, (x0, y0), (x0 + int(bar_w * conf), y0 + 18), ORANGE, -1)
    cv2.putText(frame, "confidence", (x0, y0 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, GRAY, 1)

    # Volume bar (right edge, vertical) + hand size number for calibration
    if config.VOLUME_BY_DISTANCE:
        bx, top, bottom = w - 25, 80, h - 110
        cv2.rectangle(frame, (bx, top), (bx + 12, bottom), GRAY, 1)
        fill = int((bottom - top) * melody.volume)
        cv2.rectangle(frame, (bx, bottom - fill), (bx + 12, bottom), ORANGE, -1)
        cv2.putText(frame, "vol", (bx - 8, top - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, GRAY, 1)
        size_txt = "-" if melody.hand_size is None else f"{melody.hand_size:.2f}"
        cv2.putText(frame, f"hand size {size_txt}", (w - 330, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.55, GRAY, 1)

    cv2.putText(frame, "[ ] change key | C chords on/off | Q quit", (20, h - 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 1)


def main():
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    if not cap.isOpened():
        print("Could not open camera. Try changing CAMERA_INDEX in config.py.")
        return

    tracker = HandTracker()
    recognizer = SignRecognizer()
    player = SoundPlayer()
    player.start()
    melody = MelodyController(player)
    chords = ChordController(player)
    print(f"Loaded model: {recognizer.model_name}")

    prev = time.time()
    fps = 0.0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if config.MIRROR_VIEW:
                frame = cv2.flip(frame, 1)

            hands = tracker.process(frame)
            right = hands.get(config.MELODY_HAND)
            left = hands.get(config.CHORD_HAND)

            sign = recognizer.update(right)
            melody.update(sign, right["height"] if right else None, right["size"] if right else None)
            chords.update(left)

            # Drawing
            draw_chord_grid(frame, chords)
            draw_zones(frame, melody.octave)
            tracker.draw(frame, hands)
            now = time.time()
            fps = 0.9 * fps + 0.1 * (1 / max(now - prev, 1e-6))
            prev = now
            draw_info(frame, melody, chords, recognizer, fps)
            cv2.imshow("Hand Sign Music", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key in (ord("]"), ord("[")):
                t = melody.transpose + (1 if key == ord("]") else -1)
                melody.set_transpose(t)
                chords.set_transpose(t)
            elif key == ord("c"):
                chords.toggle()
    finally:
        melody.stop()
        chords.stop()
        time.sleep(0.2)          # let the last notes fade out
        player.stop()
        cap.release()
        cv2.destroyAllWindows()
        tracker.close()


if __name__ == "__main__":
    main()