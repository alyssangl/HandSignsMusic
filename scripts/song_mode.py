"""
song_mode.py
Sight-reading practice, like Guitar Hero's practice mode:
the screen shows the song in numbered notation (with chords),
and it only moves on when you play the correct note (and chord).

Keys (in main.py):  S = song mode on/off,  N = next song,  R = restart
"""

import time

import cv2

import config
from songs import SONGS, parse_song

ORANGE = (0, 200, 255)
GREEN = (80, 200, 80)
RED = (60, 60, 230)
WHITE = (255, 255, 255)
GRAY = (130, 130, 130)
DARK = (30, 30, 30)

PANEL_TOP = 0.09                          # song panel starts here (fraction of screen height)
GRID_TOP_IN_SONG_MODE = 0.36              # chord grid moves down so the panel fits


class SongMode:
    def __init__(self):
        self.active = False
        self.song_i = 0
        self._load()

    # ---------- control ----------
    def _load(self):
        song = SONGS[self.song_i]
        self.title = song["title"]
        self.steps = parse_song(song["notes"])
        self.pos = 0
        self.mistakes = 0
        self.start_time = None
        self.end_time = None
        self._seen_events = None
        self._flash_until = 0.0
        self._flash_color = GREEN
        self.wrong_reason = ""

    def toggle(self, chords):
        self.active = not self.active
        self._load()
        x1, y1, x2, y2 = config.CHORD_AREA
        chords.area = (x1, max(y1, GRID_TOP_IN_SONG_MODE), x2, y2) if self.active else config.CHORD_AREA

    def next_song(self):
        self.song_i = (self.song_i + 1) % len(SONGS)
        self._load()

    def restart(self):
        self._load()

    @property
    def finished(self):
        return self.end_time is not None

    # ---------- checking ----------
    def update(self, melody, chords):
        if not self.active or self.finished:
            return
        if self._seen_events is None:                 # ignore notes played before the song started
            self._seen_events = melody.note_events
            return
        if melody.note_events == self._seen_events:
            return                                    # no new note
        self._seen_events = melody.note_events

        now = time.monotonic()
        if self.start_time is None:
            self.start_time = now

        sign, octave = melody.last_event
        target = self.steps[self.pos]
        note_ok = sign == target["sign"] and (not config.SONG_CHECK_OCTAVE or octave == target["octave"])
        chord_ok = (not config.SONG_CHECK_CHORD or not chords.enabled
                    or target["chord"] is None or chords.current_roman == target["chord"])

        if note_ok and chord_ok:
            self.pos += 1
            self._flash_color, self._flash_until = GREEN, now + 0.25
            if self.pos >= len(self.steps):
                self.end_time = now
        else:
            self.mistakes += 1
            self._flash_color, self._flash_until = RED, now + 0.4
            if not note_ok and sign == target["sign"]:
                self.wrong_reason = "wrong octave"
            elif not note_ok:
                self.wrong_reason = "wrong note"
            else:
                self.wrong_reason = "wrong chord"

    # ---------- drawing ----------
    def draw(self, frame):
        if not self.active:
            return
        h, w = frame.shape[:2]
        top = int(PANEL_TOP * h)
        box = max(40, min(64, int(h * 0.09)))       # size of one note box
        y_box = top + 68                            # title row, then chord row, then boxes
        bottom = y_box + box + 26                   # room for the "flick!" hint

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, top), (w, bottom), DARK, -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        # Title + progress
        cv2.putText(frame, f"SONG: {self.title}", (20, top + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, WHITE, 2)
        cv2.putText(frame, f"{min(self.pos, len(self.steps))}/{len(self.steps)}   mistakes: {self.mistakes}",
                    (w - 330, top + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, GRAY, 2)

        # Note boxes: a few done notes on the left, current in the middle, next ones on the right
        gap = int(box * 0.35)
        visible = max(5, (w - 40) // (box + gap))
        start = max(0, self.pos - visible // 3)
        x = 20
        prev_chord = self.steps[start - 1]["chord"] if start > 0 else None
        now = time.monotonic()

        for i in range(start, min(len(self.steps), start + visible)):
            step = self.steps[i]
            if i < self.pos:
                color, thick = GRAY, 1
            elif i == self.pos:
                color = self._flash_color if now < self._flash_until else ORANGE
                thick = 3
            else:
                color, thick = WHITE, 1
            cv2.rectangle(frame, (x, y_box), (x + box, y_box + box), color, thick)

            # number
            text_color = GRAY if i < self.pos else color
            (tw, th), _ = cv2.getTextSize(step["sign"], cv2.FONT_HERSHEY_SIMPLEX, 1.3, 3)
            tx, ty = x + (box - tw) // 2, y_box + (box + th) // 2
            cv2.putText(frame, step["sign"], (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 1.3, text_color, 3)
            # octave dots (like numbered notation): dot above = high, dot below = low
            for k in range(abs(step["octave"])):
                dy = (ty - th - 8 - k * 8) if step["octave"] > 0 else (ty + 9 + k * 8)
                cv2.circle(frame, (x + box // 2, dy), 3, text_color, -1)

            # chord name above the box when it changes
            if step["chord"] and step["chord"] != prev_chord:
                cv2.putText(frame, step["chord"], (x, y_box - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                            GRAY if i < self.pos else (255, 150, 0), 2)
            prev_chord = step["chord"]

            # hint for repeated notes on the current box
            if i == self.pos and i > 0 and self.steps[i - 1]["sign"] == step["sign"] \
                    and self.steps[i - 1]["octave"] == step["octave"]:
                cv2.putText(frame, "flick!", (x, y_box + box + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, ORANGE, 1)
            x += box + gap

        # Wrong-note message
        if now < self._flash_until and self._flash_color == RED:
            cv2.putText(frame, self.wrong_reason, (w // 2 - 80, top + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, RED, 2)

        if self.finished:
            self._draw_results(frame)

    def _draw_results(self, frame):
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = w // 2 - 230, h // 2 - 120, w // 2 + 230, h // 2 + 120
        cv2.rectangle(frame, (x1, y1), (x2, y2), DARK, -1)
        cv2.rectangle(frame, (x1, y1), (x2, y2), ORANGE, 2)
        total = len(self.steps)
        accuracy = 100 * total / (total + self.mistakes)
        seconds = self.end_time - (self.start_time or self.end_time)
        lines = [
            ("Finished!", 1.2, ORANGE),
            (f"Time: {seconds:.1f} s", 0.8, WHITE),
            (f"Mistakes: {self.mistakes}", 0.8, WHITE),
            (f"Accuracy: {accuracy:.0f}%", 0.8, WHITE),
            ("R = play again   N = next song", 0.6, GRAY),
        ]
        y = y1 + 50
        for text, scale, color in lines:
            cv2.putText(frame, text, (x1 + 30, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2)
            y += 45