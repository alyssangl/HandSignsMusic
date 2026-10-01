"""
music_utils.py
Pure music math. No camera, no sound.
"""

import config

NOTE_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def midi_to_freq(midi):
    """MIDI note number -> frequency in Hz. 69 = A4 = 440 Hz, 60 = C4 (middle C)."""
    return 440.0 * 2 ** ((midi - 69) / 12)


def note_name(midi):
    """60 -> 'C4', 62 -> 'D4', etc."""
    return f"{NOTE_NAMES[midi % 12]}{midi // 12 - 1}"


def sign_to_midi(sign, octave_shift=0, transpose=None):
    """
    Convert a number sign to a MIDI note.
      sign:          "1" (do) ... "7" (ti)
      octave_shift:  -1 = lower octave, 0 = middle, 1 = higher octave
      transpose:     semitones (defaults to config.TRANSPOSE)
    Returns None for "rest" or unknown signs.
    """
    if sign not in config.SIGN_SEMITONES:
        return None
    if transpose is None:
        transpose = config.TRANSPOSE
    return config.BASE_MIDI + transpose + config.SIGN_SEMITONES[sign] + 12 * octave_shift