"""
chord_controller.py
Left hand -> chords.
The left side of the screen is divided into a grid of boxes (config.CHORD_GRID).
The box the left hand is in chooses WHICH chord.

Playing the chord (strike mode, default):
    - hold a FIST or an OPEN hand in a box  -> that chord plays
    - move to another box (fist or open)    -> the new chord plays right away
    - same chord again? change fist <-> open in the same box -> it plays again
  Taking the hand out of the grid (or out of the camera) stops the chord.

Set CHORD_STRIKE_MODE = False in config.py for the old behaviour
(the chord plays as soon as the hand enters a box).
"""

from collections import deque

import numpy as np

import config
from music_utils import NOTE_NAMES

STRIKE_MODE = getattr(config, "CHORD_STRIKE_MODE", True)
SHAPE_STABLE_FRAMES = getattr(config, "CHORD_SHAPE_FRAMES", 3)   # frames a shape must hold before it counts

# Finger tips and the middle joint (PIP) of each finger, MediaPipe numbering
FINGER_TIPS = (8, 12, 16, 20)
FINGER_PIPS = (6, 10, 14, 18)


def hand_shape(points):
    """
    Very simple rule-based shape check for the left hand:
      'fist' = at most 1 finger stretched out, 'open' = 4 fingers stretched out,
      None   = something in between (ignored).
    A finger counts as stretched when its tip is clearly farther from the wrist than its middle joint.
    """
    wrist = points[0, :2]
    extended = 0
    for tip, pip in zip(FINGER_TIPS, FINGER_PIPS):
        if np.linalg.norm(points[tip, :2] - wrist) > 1.15 * np.linalg.norm(points[pip, :2] - wrist):
            extended += 1
    if extended <= 1:
        return "fist"
    if extended >= 4:
        return "open"
    return None

ROMAN_TO_DEGREE = {"i": 0, "ii": 1, "iii": 2, "iv": 3, "v": 4, "vi": 5, "vii": 6}
SCALE = [0, 2, 4, 5, 7, 9, 11]      # major scale in semitones
EDGE_MARGIN = 0.03                  # buffer near box edges so chords don't flicker

# Chord types: suffix -> (intervals in semitones above the root, name suffix)
# For "7" and "6" the result depends on upper/lower case (major or minor).
CHORD_TYPES = {
    "":      None,                          # plain major / minor (from case)
    "7":     None,                          # V7 = dominant 7th, ii7 = minor 7th
    "6":     None,
    "maj7":  ((0, 4, 7, 11), "maj7"),
    "dim":   ((0, 3, 6), "dim"),
    "°":     ((0, 3, 6), "dim"),
    "dim7":  ((0, 3, 6, 9), "dim7"),
    "m7b5":  ((0, 3, 6, 10), "m7b5"),
    "aug":   ((0, 4, 8), "aug"),
    "+":     ((0, 4, 8), "aug"),
    "sus4":  ((0, 5, 7), "sus4"),
    "sus2":  ((0, 2, 7), "sus2"),
    "add9":  ((0, 4, 7, 14), "add9"),
}


def parse_chord(roman):
    """
    'V7' -> (root semitones above 1, intervals, name suffix)

    Roman numeral rules:
      UPPER case = major (I, IV, V, II, III ...), lower case = minor (ii, iii, vi, iv ...)
      b / # before the numeral = one semitone lower / higher (bVII = Bb in C)
      suffix after the numeral = chord type: 7, maj7, 6, dim (or °), dim7, m7b5, aug (or +), sus4, sus2, add9
    """
    text = roman.strip()
    shift = 0
    while text and text[0] in "b#":
        shift += -1 if text[0] == "b" else 1
        text = text[1:]
    for numeral in ("VII", "VI", "IV", "V", "III", "II", "I"):
        if text.upper().startswith(numeral):
            num_text, suffix = text[:len(numeral)], text[len(numeral):]
            break
    else:
        raise ValueError(f"Unknown chord '{roman}'. Use roman numerals like I, ii, V7, bVII.")
    if suffix not in CHORD_TYPES:
        raise ValueError(f"Unknown chord type '{suffix}' in '{roman}'. Options: {', '.join(k for k in CHORD_TYPES if k)}")

    major = num_text.isupper()
    root = SCALE[ROMAN_TO_DEGREE[num_text.lower()]] + shift

    if suffix == "":
        intervals, name = ((0, 4, 7), "") if major else ((0, 3, 7), "m")
    elif suffix == "7":
        intervals, name = ((0, 4, 7, 10), "7") if major else ((0, 3, 7, 10), "m7")
    elif suffix == "6":
        intervals, name = ((0, 4, 7, 9), "6") if major else ((0, 3, 7, 9), "m6")
    else:
        intervals, name = CHORD_TYPES[suffix]
    return root, intervals, name


def chord_notes(roman, transpose):
    """Chord notes in root position, e.g. 'IV' in C -> F A C, 'V7' -> G B D F."""
    root, intervals, _ = parse_chord(roman)
    base = config.CHORD_BASE_MIDI + transpose + root
    return [base + i for i in intervals]


def voice_chord(notes):
    """
    Move each chord note into one comfortable octave range (config.CHORD_LOW_MIDI .. +11).
    This avoids muddy low notes and makes chord changes smooth (notes move only a little).
    """
    low = config.CHORD_LOW_MIDI
    voiced = []
    for n in notes:
        while n < low:
            n += 12
        while n >= low + 12:
            n -= 12
        voiced.append(n)
    return sorted(set(voiced))


def chord_name(roman, transpose):
    """'V7' in C -> 'G7', 'bVII' in C -> 'Bb', 'ii' in D -> 'Em'"""
    root, _, suffix = parse_chord(roman)
    return NOTE_NAMES[(root + transpose) % 12] + suffix


class ChordController:
    def __init__(self, player):
        for row in config.CHORD_GRID:          # check the grid for typos right away
            for roman in row:
                parse_chord(roman)
        self.player = player
        self.transpose = config.TRANSPOSE
        self.enabled = config.CHORDS_ENABLED
        self.cell = None            # (row, col) of the active box, or None
        self.area = config.CHORD_AREA   # grid position on screen (song mode moves it down a bit)
        self._notes = None
        self._ids = []
        # strike mode
        self.shape = None                 # stable shape of the left hand: "fist", "open" or None
        self._shape_history = deque(maxlen=SHAPE_STABLE_FRAMES)
        self.strikes = 0                  # how many times a chord was played (for display)
        self._played_cell = None          # box of the chord that was played last

    # ---------- grid geometry ----------
    @staticmethod
    def grid_size():
        return len(config.CHORD_GRID), len(config.CHORD_GRID[0])

    def cell_rect(self, row, col):
        """Box position as fractions: (left, top, right, bottom)."""
        x1, y1, x2, y2 = self.area
        rows, cols = self.grid_size()
        cw, ch = (x2 - x1) / cols, (y2 - y1) / rows
        return x1 + col * cw, y1 + row * ch, x1 + (col + 1) * cw, y1 + (row + 1) * ch

    def _cell_at(self, x, y):
        x1, y1, x2, y2 = self.area
        if not (x1 <= x < x2 and y1 <= y < y2):
            return None
        rows, cols = self.grid_size()
        col = min(int((x - x1) / (x2 - x1) * cols), cols - 1)
        row = min(int((y - y1) / (y2 - y1) * rows), rows - 1)
        return row, col

    def _inside_with_margin(self, cell, x, y):
        l, t, r, b = self.cell_rect(*cell)
        return (l + EDGE_MARGIN) <= x <= (r - EDGE_MARGIN) and (t + EDGE_MARGIN) <= y <= (b - EDGE_MARGIN)

    # ---------- main update ----------
    def _update_cell(self, hand):
        if not self.enabled or hand is None:
            self.cell = None
            return
        x, y = hand["x"], hand["height"]
        candidate = self._cell_at(x, y)
        if candidate is None:
            self.cell = None
        elif candidate != self.cell:
            # Switch only when the hand is clearly inside the new box
            if self.cell is None or self._inside_with_margin(candidate, x, y):
                self.cell = candidate

    def _current_notes(self):
        if self.cell is None:
            return None
        roman = config.CHORD_GRID[self.cell[0]][self.cell[1]]
        return chord_notes(roman, self.transpose)

    def _play(self, notes):
        """Stop what is sounding and play these chord notes (None = silence)."""
        for nid in self._ids:
            self.player.note_off(nid)
        self._ids = [
            self.player.note_on(m, volume=config.CHORD_VOLUME, timbre=config.CHORD_TIMBRE)
            for m in voice_chord(notes)
        ] if notes else []
        self._notes = notes

    def update(self, hand):
        """hand: the left-hand dict from HandTracker.process(), or None."""
        self._update_cell(hand)

        if not STRIKE_MODE:
            notes = self._current_notes()
            if notes != self._notes:
                self._play(notes)
            return

        # ----- strike mode -----
        #   * moving to ANOTHER box plays that chord right away (fist or open, doesn't matter)
        #   * in the SAME box, changing fist <-> open plays the chord again
        if self.cell is None:
            if self._notes is not None:
                self._play(None)            # hand left the grid -> stop
            self._shape_history.clear()
            self.shape = None
            self._played_cell = None
            return

        self._shape_history.append(hand_shape(hand["points"]))
        h = self._shape_history
        stable = len(h) == h.maxlen and h[0] is not None and all(x == h[0] for x in h)

        if stable and h[0] != self.shape:
            # fist <-> open change (or the first clear shape after entering the grid)
            self.shape = h[0]
            self._strike()
        elif self.shape is not None and self.cell != self._played_cell:
            # hand moved to another box while holding a fist or open hand
            self._strike()

    def _strike(self):
        self._play(self._current_notes())
        self._played_cell = self.cell
        self.strikes += 1

    def set_transpose(self, semitones):
        self.transpose = max(-12, min(12, semitones))

    def toggle(self):
        self.enabled = not self.enabled

    def stop(self):
        for nid in self._ids:
            self.player.note_off(nid)
        self._ids, self._notes, self.cell = [], None, None
        self.shape = None
        self._played_cell = None
        self._shape_history.clear()

    # ---------- for the display ----------
    def label(self, row, col):
        roman = config.CHORD_GRID[row][col]
        return roman, chord_name(roman, self.transpose)

    @property
    def current_roman(self):
        """Roman numeral of the chord being played, or None."""
        if not self.enabled or self.cell is None:
            return None
        return config.CHORD_GRID[self.cell[0]][self.cell[1]]

    @property
    def chord_text(self):
        if not self.enabled:
            return "chords off"
        if self.cell is None:
            return "-"
        roman, name = self.label(*self.cell)
        if STRIKE_MODE:
            return f"{roman} ({name})  [{self.shape or '...'}]"
        return f"{roman} ({name})"