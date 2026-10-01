"""
config.py
All project settings in one place. Change values here instead of inside other files.
"""

# ---------- Camera ----------
CAMERA_INDEX = 0          # 0 = built-in webcam. Try 1 if you use an external camera.
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
MIRROR_VIEW = True        # Flip the image like a mirror (also makes Left/Right labels correct)

# ---------- Hand tracking (MediaPipe) ----------
MAX_NUM_HANDS = 2         # Track both hands from the start (left hand used later for chords)
MIN_DETECTION_CONF = 0.6
MIN_TRACKING_CONF = 0.5
SWAP_HANDEDNESS = True    # New MediaPipe reports Left/Right reversed on a mirrored image

MELODY_HAND = "Right"     # Right hand plays the melody
CHORD_HAND = "Left"       # Left hand will play chords (added later)

# ---------- Signs ----------
# Number signs like numbered notation (簡譜): 1 = do ... 7 = ti.
# Octave comes from hand height (low / middle / high zone), not from the sign.
# "rest" = no note. The order here is also the label order (key 0 = rest, 1-7 = numbers).
SIGNS = ["rest", "1", "2", "3", "4", "5", "6", "7"]

# Semitones above "1" (do) for each sign (major scale)
SIGN_SEMITONES = {
    "1": 0, "2": 2, "3": 4, "4": 5, "5": 7, "6": 9, "7": 11,
}

# Names shown on screen
SIGN_NAMES = {
    "rest": "rest", "1": "do", "2": "re", "3": "mi", "4": "fa",
    "5": "sol", "6": "la", "7": "ti",
}

# ---------- Music ----------
BASE_MIDI = 60            # 60 = middle C. Fixed do = C.
TRANSPOSE = 0             # Semitones: 0 = C, 2 = D, -3 = A, etc.

# ---------- Repeated notes (tap) ----------
# Flick the right hand quickly DOWNWARD to play the same note again (e.g. "1 1" in Twinkle Twinkle).
TAP_ENABLED = True
TAP_SPEED = 0.9           # how fast the flick must be (screen heights per second). Lower = easier to trigger
TAP_COOLDOWN = 0.2        # seconds before another tap can trigger (prevents double notes)
TAP_OCTAVE_FREEZE = 0.35  # seconds the octave stays fixed after a tap (the flick won't change octave)

# ---------- Volume by distance (right hand) ----------
# Hand closer to the camera = louder. The "hand size" number is shown on screen;
# use it to set these two values for your camera and seating position.
VOLUME_BY_DISTANCE = True
VOLUME_SIZE_FAR = 0.10    # hand size when your hand is far  -> quietest
VOLUME_SIZE_NEAR = 0.25   # hand size when your hand is near -> loudest
VOLUME_MIN = 0.2          # quietest volume (0 = silent, 1 = full)
VOLUME_SMOOTHING = 0.3    # 0.1 = very smooth/slow changes, 1.0 = instant (can be jumpy)

# ---------- Chords (left hand) ----------
CHORDS_ENABLED = True     # press C in the app to turn chords on/off
CHORD_BASE_MIDI = 48      # reference C for building chords (don't change)
CHORD_LOW_MIDI = 53       # chord notes are placed between F3 and E4 (not too low, not muddy)
CHORD_VOLUME = 0.3        # softer than the melody so the melody stays clear

# The chord grid on the LEFT side of the screen (rows top -> bottom, columns left -> right).
# Roman numerals = chord on that scale degree: I = 1-3-5, IV = 4-6-1, V = 5-7-2, vi = 6-1-3 ...
# Upper case = major, lower case = minor (chosen automatically from the scale).
CHORD_GRID = [
    ["IV", "V"],
    ["I", "vi"],
    ["ii", "iii"],
]
# Area of the screen used by the grid: (left, top, right, bottom) as fractions
CHORD_AREA = (0.03, 0.12, 0.45, 0.85)

# ---------- Sound ----------
# Instrument sound: "piano", "melody" (soft organ/flute) or "pad" (very soft, sustained)
MELODY_TIMBRE = "piano"
CHORD_TIMBRE = "pad"    # try "pad" for a soft sustained background instead

SAMPLE_RATE = 44100
MASTER_VOLUME = 0.4       # Overall volume. For louder sound, turn up your laptop volume first.
ATTACK_TIME = 0.02        # Seconds for a note to fade in (avoids clicks)
RELEASE_TIME = 0.15       # Seconds for a note to fade out

# ---------- Paths ----------
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent   # the HandSignsMusic folder
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "models"