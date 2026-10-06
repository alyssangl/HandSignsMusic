"""
chord_controller.py
Left hand -> chords.
The left side of the screen is divided into a grid of boxes (config.CHORD_GRID).
Whichever box the left hand is in, that chord plays. Move the hand away
(or out of the grid / out of the camera) to stop the chord.
"""

import config
from music_utils import NOTE_NAMES

ROMAN_TO_DEGREE = {"i": 0, "ii": 1, "iii": 2, "iv": 3, "v": 4, "vi": 5, "vii": 6}
SCALE = [0, 2, 4, 5, 7, 9, 11]      # major scale in semitones
EDGE_MARGIN = 0.03                  # buffer near box edges so chords don't flicker


def chord_notes(roman, transpose):
    """Build a 3-note chord (triad) on a scale degree, e.g. 'IV' in C -> F A C."""
    degree = ROMAN_TO_DEGREE[roman.lower()]
    notes = []
    for step in (0, 2, 4):                      # root, third, fifth
        idx = degree + step
        semis = SCALE[idx % 7] + 12 * (idx // 7)
        notes.append(config.CHORD_BASE_MIDI + transpose + semis)
    return notes


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
    return sorted(voiced)


def chord_name(notes):
    """[53, 57, 60] -> 'F', [50, 53, 57] -> 'Dm', [59, 62, 65] -> 'Bdim'"""
    root = NOTE_NAMES[notes[0] % 12]
    third, fifth = notes[1] - notes[0], notes[2] - notes[0]
    if fifth == 6:
        return root + "dim"
    return root + ("m" if third == 3 else "")


class ChordController:
    def __init__(self, player):
        self.player = player
        self.transpose = config.TRANSPOSE
        self.enabled = config.CHORDS_ENABLED
        self.cell = None            # (row, col) of the active box, or None
        self.area = config.CHORD_AREA   # grid position on screen (song mode moves it down a bit)
        self._notes = None
        self._ids = []

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
    def update(self, hand):
        """hand: the left-hand dict from HandTracker.process(), or None."""
        if not self.enabled or hand is None:
            self.cell = None
        else:
            x, y = hand["x"], hand["height"]
            candidate = self._cell_at(x, y)
            if candidate is None:
                self.cell = None
            elif candidate != self.cell:
                # Switch only when the hand is clearly inside the new box
                if self.cell is None or self._inside_with_margin(candidate, x, y):
                    self.cell = candidate

        notes = None
        if self.cell is not None:
            roman = config.CHORD_GRID[self.cell[0]][self.cell[1]]
            notes = chord_notes(roman, self.transpose)

        if notes != self._notes:
            for nid in self._ids:
                self.player.note_off(nid)
            self._ids = [
                self.player.note_on(m, volume=config.CHORD_VOLUME, timbre=config.CHORD_TIMBRE)
                for m in voice_chord(notes)
            ] if notes else []
            self._notes = notes

    def set_transpose(self, semitones):
        self.transpose = max(-12, min(12, semitones))

    def toggle(self):
        self.enabled = not self.enabled

    def stop(self):
        for nid in self._ids:
            self.player.note_off(nid)
        self._ids, self._notes, self.cell = [], None, None

    # ---------- for the display ----------
    def label(self, row, col):
        roman = config.CHORD_GRID[row][col]
        return roman, chord_name(chord_notes(roman, self.transpose))

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
        return f"{roman} ({name})"