"""
sound_player.py
Generates notes with code (no sound files needed) and mixes several notes at once,
so melody notes and chord notes can play together.

Timbres (sounds):
    "piano"  - piano-like: sharp strike, then a natural fade, brighter at the start
    "melody" - soft organ/flute-like tone that sustains while held
    "pad"    - very soft, round, sustained tone (good for background chords)

Usage:
    player = SoundPlayer()
    player.start()
    note_id = player.note_on(60, timbre="piano")
    player.note_off(note_id)
    player.stop()
"""

import itertools
import threading

import numpy as np
import sounddevice as sd

import config
from music_utils import midi_to_freq

# Sustained timbres: (harmonic number, loudness)
TIMBRES = {
    "melody": [(1, 1.0), (2, 0.35), (3, 0.15), (4, 0.05)],
    "pad":    [(1, 1.0), (2, 0.12)],
}

# ---------- Piano model ----------
# A struck string: many overtones, the high ones fade much faster than the low ones,
# real strings are slightly "stretched" (inharmonic), and each note has 2 strings
# tuned a tiny bit apart, which gives the warm, shimmering piano character.
PIANO_PARTIALS = 8
PIANO_INHARMONICITY = 0.0004    # string stiffness (stretches higher overtones)
PIANO_DETUNE = 0.0008           # tuning difference between the 2 strings (~1.4 cents)
PIANO_ATTACK = 0.003            # seconds: a piano hammer strike is very fast
PIANO_RELEASE = 0.25            # seconds: damper falling on the string

LIMIT_KNEE = 0.8   # below this the sound is untouched; only loud peaks get softened


class _Voice:
    """One sounding note."""

    def __init__(self, midi, volume, timbre):
        self.freq = midi_to_freq(midi)
        self.volume = volume
        self.target_volume = volume
        self.timbre = timbre
        self.phase = 0.0
        self.samples = 0          # samples played since the note started
        self.env = 0.0            # attack / release envelope, 0..1
        self.releasing = False

        if timbre == "piano":
            self._setup_piano(midi)
        else:
            self.harmonics = TIMBRES[timbre]
            self.harm_sum = sum(a for _, a in self.harmonics)

    def _setup_piano(self, midi):
        ks = np.arange(1, PIANO_PARTIALS + 1, dtype=np.float64)
        # stretched overtone frequencies
        self.p_freqs = self.freq * ks * np.sqrt(1 + PIANO_INHARMONICITY * ks ** 2)
        # keep overtones below the audible/aliasing limit
        valid = self.p_freqs < config.SAMPLE_RATE / 2.2
        # brighter for low notes, softer overtones for high notes
        brightness = 1.6 + max(0, midi - 60) / 24
        amps = 1.0 / ks ** brightness
        amps[1] *= 1.3                         # piano's strong 2nd overtone
        self.p_amps = np.where(valid, amps, 0.0)
        self.p_amps /= self.p_amps.sum()
        # fade time: low notes ring longer than high notes, overtones fade faster
        base_decay = 2.5 * 2 ** (-(midi - 60) / 24)
        self.p_decay = base_decay / (1 + 0.6 * (ks - 1))


class SoundPlayer:
    def __init__(self):
        self.sr = config.SAMPLE_RATE
        self._voices = {}
        self._lock = threading.Lock()
        self._ids = itertools.count()
        self._stream = sd.OutputStream(
            samplerate=self.sr, channels=1, dtype="float32",
            callback=self._callback, blocksize=256,   # small block = low delay
        )

    # ---------- public ----------
    def start(self):
        self._stream.start()

    def stop(self):
        self._stream.stop()
        self._stream.close()

    def note_on(self, midi, volume=1.0, timbre="piano"):
        """Start a note. Returns an id to use with note_off()."""
        note_id = next(self._ids)
        with self._lock:
            self._voices[note_id] = _Voice(midi, volume, timbre)
        return note_id

    def set_volume(self, note_id, volume):
        """Change the volume of a note that is already playing (changes smoothly)."""
        with self._lock:
            if note_id in self._voices:
                self._voices[note_id].target_volume = volume

    def note_off(self, note_id):
        """Fade out a note."""
        with self._lock:
            if note_id in self._voices:
                self._voices[note_id].releasing = True

    def all_off(self):
        with self._lock:
            for v in self._voices.values():
                v.releasing = True

    # ---------- audio thread ----------
    def _piano_wave(self, v, frames):
        t = (v.samples + np.arange(frames, dtype=np.float64)) / self.sr
        tt = t[:, None]                                          # (frames, 1)
        decay = np.exp(-tt / v.p_decay[None, :])                 # each overtone fades
        f1 = v.p_freqs[None, :]
        f2 = f1 * (1 + PIANO_DETUNE)                             # second string
        strings = np.sin(2 * np.pi * f1 * tt) + np.sin(2 * np.pi * f2 * tt)
        return (0.5 * strings * decay * v.p_amps[None, :]).sum(axis=1).astype(np.float32)

    def _sustained_wave(self, v, frames, n):
        phase_inc = 2 * np.pi * v.freq / self.sr
        phases = v.phase + phase_inc * n
        wave = sum(a * np.sin(k * phases) for k, a in v.harmonics) / v.harm_sum
        v.phase = float((phases[-1] + phase_inc) % (2 * np.pi))
        return wave

    def _callback(self, outdata, frames, time_info, status):
        mix = np.zeros(frames, dtype=np.float32)
        n = np.arange(frames, dtype=np.float32)

        with self._lock:
            finished = []
            for note_id, v in self._voices.items():
                piano = v.timbre == "piano"
                wave = self._piano_wave(v, frames) if piano else self._sustained_wave(v, frames, n)

                # Attack / release envelope (no clicks)
                attack = PIANO_ATTACK if piano else config.ATTACK_TIME
                release = PIANO_RELEASE if piano else config.RELEASE_TIME
                if v.releasing:
                    env = np.clip(v.env - (n + 1) / (release * self.sr), 0.0, 1.0)
                else:
                    env = np.clip(v.env + (n + 1) / (attack * self.sr), 0.0, 1.0)
                v.env = float(env[-1])

                # Volume glides smoothly to its new value
                vol = np.linspace(v.volume, v.target_volume, frames, dtype=np.float32)
                v.volume = v.target_volume

                mix += wave * env * vol
                v.samples += frames

                done = v.releasing and v.env <= 0.0
                if piano and v.samples / self.sr > 4 * v.p_decay[0]:
                    done = True                      # piano note has faded away naturally
                if done:
                    finished.append(note_id)

            for note_id in finished:
                del self._voices[note_id]

        # Clean volume: untouched below the knee, only loud peaks are gently limited
        x = mix * config.MASTER_VOLUME
        mag = np.abs(x)
        over = mag > LIMIT_KNEE
        if over.any():
            room = 1.0 - LIMIT_KNEE
            x[over] = np.sign(x[over]) * (LIMIT_KNEE + room * np.tanh((mag[over] - LIMIT_KNEE) / room))
        outdata[:, 0] = x