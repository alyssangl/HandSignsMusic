"""
melody_controller.py
Right hand -> melody.
  - The SIGN (1-7) chooses the note (do-ti)
  - The HAND HEIGHT chooses the octave: top = high, middle = normal, bottom = low
  - Holding a sign keeps the note sounding; "rest" or no hand stops it
  - A quick DOWNWARD flick plays the same note again (for repeated notes)
  - Hand closer to the camera = louder (config.VOLUME_BY_DISTANCE)
"""

import time

import config
from music_utils import sign_to_midi, note_name

# Zone borders as a fraction of screen height (0 = top, 1 = bottom)
ZONE_TOP = 1 / 3        # above this line   -> high octave
ZONE_BOTTOM = 2 / 3     # below this line   -> low octave
ZONE_MARGIN = 0.04      # buffer around the lines so the octave doesn't flicker

OCTAVE_NAMES = {1: "HIGH", 0: "MID", -1: "LOW"}


class MelodyController:
    def __init__(self, player):
        self.player = player
        self.transpose = config.TRANSPOSE
        self.octave = 0
        self.sign = None
        self._note_id = None
        self._midi = None

        # for tap (flick) detection
        self._prev_h = None
        self._prev_t = None
        self._vel = 0.0
        self._stable_octave = 0
        self._last_tap = -1.0
        self._freeze_until = 0.0
        self.last_tap = -1.0        # time of the last tap that replayed a note (for the display)

        self.volume = 1.0           # current melody volume 0..1
        self.hand_size = None       # last measured hand size (shown on screen for calibration)

        # every time a note STARTS (new note or flick), this counter goes up (used by song mode)
        self.note_events = 0
        self.last_event = None      # (sign, octave) of the last note that started

    def _octave_from_height(self, height):
        candidate = 1 if height < ZONE_TOP else (0 if height < ZONE_BOTTOM else -1)
        if candidate != self.octave:
            # Only switch when the hand is clearly past a line
            near_line = min(abs(height - ZONE_TOP), abs(height - ZONE_BOTTOM)) < ZONE_MARGIN
            if near_line:
                return self.octave
        return candidate

    def _detect_tap(self, height, now):
        """Return True when the hand moves quickly downward."""
        tapped = False
        if height is not None and self._prev_h is not None:
            dt = now - self._prev_t
            if 0 < dt < 0.2:
                v = (height - self._prev_h) / dt          # positive = moving down
                self._vel = 0.4 * self._vel + 0.6 * v     # smooth out tracking jitter
                if (config.TAP_ENABLED and self._vel > config.TAP_SPEED
                        and now - self._last_tap > config.TAP_COOLDOWN):
                    tapped = True
                    self._last_tap = now
        if height is None:
            self._prev_h, self._prev_t, self._vel = None, None, 0.0
        else:
            self._prev_h, self._prev_t = height, now
        return tapped

    def _update_volume(self, size):
        self.hand_size = size
        if not config.VOLUME_BY_DISTANCE:
            self.volume = 1.0
            return
        if size is None:
            return
        far, near = config.VOLUME_SIZE_FAR, config.VOLUME_SIZE_NEAR
        t = min(max((size - far) / (near - far), 0.0), 1.0)      # 0 = far, 1 = near
        target = config.VOLUME_MIN + t * (1.0 - config.VOLUME_MIN)
        a = config.VOLUME_SMOOTHING
        self.volume = (1 - a) * self.volume + a * target

    def update(self, sign, height, size=None):
        """
        sign:   stable sign from SignRecognizer ("1"-"7", "rest", or None)
        height: right-hand height 0..1, or None if no hand
        size:   right-hand palm size (bigger = closer), or None
        """
        now = time.monotonic()
        tapped = self._detect_tap(height, now)
        self._update_volume(size)

        if tapped:
            # Keep the octave from before the flick started, and hold it for a moment
            self.octave = self._stable_octave
            self._freeze_until = now + config.TAP_OCTAVE_FREEZE
        elif height is not None and now >= self._freeze_until:
            self.octave = self._octave_from_height(height)
            if abs(self._vel) < config.TAP_SPEED * 0.3:   # hand is calm -> remember this octave
                self._stable_octave = self.octave
        self.sign = sign

        midi = None
        if sign in config.SIGN_SEMITONES:
            midi = sign_to_midi(sign, octave_shift=self.octave, transpose=self.transpose)

        if tapped and midi is not None and midi == self._midi:
            # Same note again -> replay it
            self.player.note_off(self._note_id)
            self._note_id = self.player.note_on(midi, volume=self.volume, timbre=config.MELODY_TIMBRE)
            self.last_tap = now
            self.note_events += 1
            self.last_event = (sign, self.octave)
        elif midi != self._midi:
            if self._note_id is not None:
                self.player.note_off(self._note_id)
                self._note_id = None
            if midi is not None:
                self._note_id = self.player.note_on(midi, volume=self.volume, timbre=config.MELODY_TIMBRE)
                self.note_events += 1
                self.last_event = (sign, self.octave)
            self._midi = midi
        elif self._note_id is not None:
            self.player.set_volume(self._note_id, self.volume)   # held note follows the hand

    def set_transpose(self, semitones):
        """Change key. The current note is replayed in the new key on the next update."""
        self.transpose = max(-12, min(12, semitones))

    def stop(self):
        if self._note_id is not None:
            self.player.note_off(self._note_id)
        self._note_id, self._midi = None, None

    # ---------- for the display ----------
    @property
    def note_text(self):
        if self._midi is None:
            return "-"
        return f"{self.sign} ({config.SIGN_NAMES[self.sign]})  {note_name(self._midi)}"

    @property
    def octave_text(self):
        return OCTAVE_NAMES[self.octave]