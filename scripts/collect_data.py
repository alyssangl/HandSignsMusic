"""
collect_data.py
Record training data for the number sign classifier (RIGHT hand only).

Run from the HandSignsMusic folder:
    python scripts/collect_data.py --person yourname

Controls:
    0        select "rest" (relaxed hand / random non-sign poses)
    1 - 7    select number sign 1-7 (1 = do ... 7 = ti)
    SPACE    start recording a burst (stops automatically after BURST_SIZE samples)
    U        undo the last burst (if you made a mistake)
    Q        quit

Tip: while a burst records, slowly move/tilt your hand and change distance a bit,
so the model sees many variations of the same sign.

Saves:
    data/landmarks.csv                   -> 63 normalized numbers per sample (for training)
    data/images/<sign>/<person>_*.jpg    -> cropped hand images (for the optional CNN)
"""

import argparse
import csv
import time
from pathlib import Path

import cv2

import config
from hand_tracker import HandTracker, normalize_landmarks, crop_hand

BURST_SIZE = 60          # samples per burst
SAMPLE_EVERY = 2         # save every 2nd frame (less duplicate data)

CSV_PATH = Path(config.DATA_DIR) / "landmarks.csv"
IMG_DIR = Path(config.DATA_DIR) / "images"
HEADER = ["person", "label", "burst_id", "height"] + [f"f{i}" for i in range(63)]


def load_counts():
    """Count existing samples per sign in the CSV."""
    counts = {s: 0 for s in config.SIGNS}
    if CSV_PATH.exists():
        with open(CSV_PATH, newline="") as f:
            for row in csv.DictReader(f):
                if row["label"] in counts:
                    counts[row["label"]] += 1
    return counts


def append_rows(rows):
    new_file = not CSV_PATH.exists()
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(HEADER)
        writer.writerows(rows)


def undo_burst(burst_id, image_paths):
    """Remove one burst from the CSV and delete its images."""
    if not CSV_PATH.exists():
        return 0
    with open(CSV_PATH, newline="") as f:
        rows = list(csv.reader(f))
    header, body = rows[0], rows[1:]
    keep = [r for r in body if r[2] != burst_id]
    removed = len(body) - len(keep)
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(keep)
    for p in image_paths:
        Path(p).unlink(missing_ok=True)
    return removed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--person", default="me", help="Name of the person recording")
    parser.add_argument("--no-images", action="store_true", help="Only save landmarks")
    args = parser.parse_args()

    Path(config.DATA_DIR).mkdir(parents=True, exist_ok=True)
    for s in config.SIGNS:
        (IMG_DIR / s).mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    if not cap.isOpened():
        print("Could not open camera. Try changing CAMERA_INDEX in config.py.")
        return

    tracker = HandTracker()
    counts = load_counts()

    selected = "1"
    recording = False
    burst_rows, burst_imgs = [], []
    burst_id = None
    last_burst = None          # (burst_id, label, image_paths) for undo
    frame_i = 0
    message, message_until = "", 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if config.MIRROR_VIEW:
            frame = cv2.flip(frame, 1)

        clean = frame.copy()                 # crop from the frame BEFORE drawing on it
        hands = tracker.process(frame)
        right = hands.get(config.MELODY_HAND)
        frame_i += 1

        # ---------- Recording ----------
        if recording and right is not None and frame_i % SAMPLE_EVERY == 0:
            feats = normalize_landmarks(right["points"])
            burst_rows.append(
                [args.person, selected, burst_id, f"{right['height']:.4f}"]
                + [f"{v:.5f}" for v in feats]
            )
            if not args.no_images:
                crop = crop_hand(clean, right["points"])
                if crop is not None:
                    path = IMG_DIR / selected / f"{args.person}_{burst_id}_{len(burst_rows):03d}.jpg"
                    cv2.imwrite(str(path), crop)
                    burst_imgs.append(str(path))

            if len(burst_rows) >= BURST_SIZE:
                append_rows(burst_rows)
                counts[selected] += len(burst_rows)
                last_burst = (burst_id, selected, burst_imgs)
                message, message_until = f"Saved {len(burst_rows)} samples of '{selected}'", time.time() + 2
                recording = False
                burst_rows, burst_imgs = [], []

        # ---------- Drawing ----------
        tracker.draw(frame, hands)
        h, w = frame.shape[:2]

        cv2.rectangle(frame, (0, 0), (w, 70), (30, 30, 30), -1)
        cv2.putText(frame, f"Sign: {selected} ({config.SIGN_NAMES[selected]})", (20, 48),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 200, 255), 3)
        cv2.putText(frame, f"Person: {args.person}", (420, 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        if recording:
            cv2.circle(frame, (w - 40, 35), 15, (0, 0, 255), -1)
            cv2.putText(frame, f"REC {len(burst_rows)}/{BURST_SIZE}", (w - 230, 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        if right is None:
            cv2.putText(frame, "Show your RIGHT hand", (20, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

        # Sample counts per sign
        for i, s in enumerate(config.SIGNS):
            color = (0, 200, 255) if s == selected else (220, 220, 220)
            cv2.putText(frame, f"{i}: {config.SIGN_NAMES[s]:<8} {counts[s]}", (20, 160 + i * 32),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        if time.time() < message_until:
            cv2.putText(frame, message, (20, h - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, "0-7 select | SPACE record | U undo | Q quit", (w - 560, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        cv2.imshow("Collect data", frame)

        # ---------- Keys ----------
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif ord("0") <= key <= ord("7") and not recording:
            selected = config.SIGNS[key - ord("0")]
        elif key == ord(" ") and not recording:
            recording = True
            burst_id = f"{args.person}_{int(time.time() * 1000)}"
            burst_rows, burst_imgs = [], []
        elif key == ord("u") and not recording and last_burst:
            b_id, label, imgs = last_burst
            removed = undo_burst(b_id, imgs)
            counts[label] -= removed
            message, message_until = f"Undid last burst of '{label}' ({removed} samples)", time.time() + 2
            last_burst = None

    if recording and burst_rows:
        print("Quit during recording: unfinished burst was not saved.")
        for p in burst_imgs:
            Path(p).unlink(missing_ok=True)

    cap.release()
    cv2.destroyAllWindows()
    tracker.close()
    print("Samples per sign:", counts)


if __name__ == "__main__":
    main()