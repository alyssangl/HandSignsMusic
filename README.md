# Hand Signs Music

Play music with your hands in front of a webcam. Your **right hand** plays the melody using number hand signs (1–7, like numbered notation 簡譜), and your **left hand** plays chords. No physical instrument needed.

The core of the project is a **custom-trained hand sign recognition model**: MediaPipe finds the hand and its 21 key points, and a neural network trained on our own recorded dataset recognizes which number sign is being shown.

Final project for the course *Introduction to Image Recognition AI and Robotics Lab*, created by **Alyssa**.

---

## Features

- **Melody with number signs:** signs 1–7 play do, re, mi, fa, sol, la, ti
- **3 octaves by hand height:** hand high = high octave, middle = normal, low = low octave
- **Chords with the left hand:** move your left hand into one of 6 boxes on screen (I, ii, iii, IV, V, vi)
- **Transpose:** play in any key; everything is designed with 1 = C and shifted automatically
- **Flick to repeat a note:** a quick downward flick of the hand replays the same note
- **Volume by distance:** hand closer to the camera = louder
- **Piano sound generated in code:** no sound files needed
- **Song mode (sight reading):** read numbered notation and chords on screen and play along, like a Guitar Hero practice mode. The song only moves on when you play the right note and chord

## How it works

```
Webcam → MediaPipe hand tracking (21 landmarks per hand)
       ├── Right hand → normalize landmarks → neural network → sign (1–7 / rest)
       │                 + hand height → octave, hand size → volume
       │                 → melody note
       └── Left hand  → position in chord grid → chord
                                    ↓
                         Sound engine (piano synthesis) → speakers
```

1. **Hand tracking:** MediaPipe Hand Landmarker detects both hands and returns 21 points per hand.
2. **Normalization:** the points are moved so the wrist is at the origin and scaled by hand size, so the model learns the hand *shape*, not its position or distance from the camera.
3. **Classification:** a neural network (MLP) trained on our own dataset predicts the sign. Predictions are smoothed over several frames to avoid flickering.
4. **Music logic:** the sign, hand height, and hand size become a note, octave, and volume. The left hand's position selects a chord.
5. **Sound:** notes are synthesized in real time with a simple piano model and mixed together.

## Hand signs (right hand)

| Sign | Hand shape | Note |
|------|------------|------|
| rest | closed fist | no sound |
| 1 | index finger | do |
| 2 | index + middle | re |
| 3 | middle + ring + pinky | mi |
| 4 | four fingers (no thumb) | fa |
| 5 | open hand (fingers spread or together) | sol |
| 6 | thumb only | la |
| 7 | thumb + index | ti |

## Chord grid (left hand)

| | |
|---|---|
| **IV** (F) | **V** (G) |
| **I** (C) | **vi** (Am) |
| **ii** (Dm) | **iii** (Em) |

Chord names shown are for the key of C; they change automatically when you transpose.

---

## Installation

Requires **Python 3.9+**, a webcam, and speakers or headphones.

```bash
git clone <this-repository-url>
cd HandSignsMusic

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac / Linux

pip install -r requirements.txt
```

The MediaPipe hand model (`hand_landmarker.task`) downloads automatically the first time you run the program.

## Usage

All commands are run from the `HandSignsMusic` folder.

### 1. Test your setup

```bash
python scripts/test_tracking.py   # webcam + hand tracking, check Left/Right labels
python scripts/test_sound.py      # sound engine, scale + chord
```

### 2. Collect training data

```bash
python scripts/collect_data.py --person yourname
```

| Key | Action |
|-----|--------|
| `0` | select rest |
| `1`–`7` | select a sign |
| `SPACE` | record a burst of 60 samples |
| `U` | undo the last burst |
| `Q` | quit |

Tip: slowly move and tilt your hand while a burst records, so the model sees many variations.

### 3. Train the model

```bash
python scripts/train_model.py
python scripts/train_model.py --test-person amy   # test on a person not used for training
```

Compares Random Forest, Neural Network (MLP), and SVM, prints a per-sign report, saves a confusion matrix to `models/confusion_matrix.png`, and saves the final model to `models/sign_model.joblib`.

To inspect or clean up recorded data:

```bash
python scripts/manage_data.py list --sign 5
python scripts/manage_data.py delete <burst_id>
```

### 4. Play

```bash
python scripts/main.py
```

| Key | Action |
|-----|--------|
| `[` / `]` | transpose down / up |
| `C` | chords on / off |
| `S` | song mode on / off |
| `N` | next song (in song mode) |
| `R` | restart song (in song mode) |
| `Q` | quit |

Try *Twinkle Twinkle Little Star*: hold chord **I** with your left hand and play `1 · 1 · 5 · 5 · 6 · 6 · 5` with your right hand (flick to repeat a note).

### 5. Song mode (sight reading)

Press `S` while playing. A panel at the top of the screen shows the song in numbered notation:

- The **orange** box is the note to play now. Chord names (blue) appear above the notes where the chord changes.
- Play the right note (and hold the right chord with your left hand): the box flashes **green** and the song moves on.
- A wrong note flashes **red** and shows why: *wrong note*, *wrong octave*, or *wrong chord*. The song waits until you get it right.
- **"flick!"** appears when the same note repeats.
- A **dot above** a number means the high octave, a **dot below** means the low octave (like 簡譜).
- At the end you get your **time, number of mistakes, and accuracy**.

Included songs (all traditional / public domain):

| Level | Songs |
|-------|-------|
| Easy (middle octave only) | Little Bee (小蜜蜂), Mary Had a Little Lamb, Twinkle Twinkle Little Star, London Bridge, Ode to Joy, Jingle Bells |
| Medium (uses low / high octave) | Two Tigers (兩隻老虎), Row Row Row Your Boat, Old MacDonald, Happy Birthday |

#### Adding your own songs

Open `scripts/songs.py` and add a song to the `SONGS` list:

```python
{
    "title": "My Song",
    "notes": "1/I 2 3 1 3/IV 1 3",
},
```

- Separate notes with spaces: `1 2 3`
- Change chord by adding `/CHORD` after a note: `1/I`, `5/V`, `6/vi` (the chord stays until a new one is written)
- High octave: add `'` (for example `1'`). Low octave: add `,` (for example `5,`)
- Titles must use English letters (OpenCV cannot draw Chinese characters)

## Configuration

Settings are in `scripts/config.py`, for example:

| Setting | What it does |
|---------|--------------|
| `TRANSPOSE` | starting key in semitones (0 = C, 2 = D, ...) |
| `MASTER_VOLUME` | overall volume |
| `MELODY_TIMBRE`, `CHORD_TIMBRE` | `"piano"`, `"melody"` (soft organ), or `"pad"` |
| `TAP_SPEED` | how fast a flick must be to repeat a note |
| `VOLUME_SIZE_FAR`, `VOLUME_SIZE_NEAR` | hand sizes for quietest / loudest volume (shown on screen) |
| `CHORD_GRID` | which chord is in which box |
| `SONG_CHECK_OCTAVE` | song mode: `False` = octave isn't checked (easier for beginners) |
| `SONG_CHECK_CHORD` | song mode: `False` = chord isn't checked, focus on the melody |

---

## Project structure

```
HandSignsMusic/
├── data/
│   └── landmarks.csv          # recorded dataset (normalized hand landmarks)
├── models/
│   ├── sign_model.joblib      # trained sign classifier
│   └── confusion_matrix.png
├── scripts/
│   ├── config.py              # all settings
│   ├── hand_tracker.py        # MediaPipe hand tracking + landmark normalization
│   ├── music_utils.py         # note math (signs → notes, transpose)
│   ├── sound_player.py        # real-time sound synthesis and mixing
│   ├── sign_recognizer.py     # loads the model, predicts + smooths signs
│   ├── melody_controller.py   # right hand → melody (octaves, flick, volume)
│   ├── chord_controller.py    # left hand → chords
│   ├── song_mode.py           # sight-reading song mode
│   ├── songs.py               # song list (add your own songs here)
│   ├── collect_data.py        # record training data
│   ├── train_model.py         # train and evaluate models
│   ├── manage_data.py         # list / delete recorded bursts
│   ├── main.py                # the live instrument
│   ├── test_tracking.py
│   └── test_sound.py
├── requirements.txt
└── README.md
```

## Results

| Test | Accuracy |
|------|----------|
| Trained and tested on the same person (held-out bursts) | ~100% |
| Trained on one person, tested on a new person | 80.6% (SVM) |

Testing on a new person showed that most errors come from **thumb position** (rest vs. 6, and 1 vs. 7), since different people hold their thumbs differently. Training on data from multiple people and recording natural variations of each sign (for example, sign 5 with fingers spread *and* together) improved recognition.

## Author

**Alyssa**: concept, data collection, model training, and development.

## Acknowledgments

- [MediaPipe](https://developers.google.com/mediapipe) by Google for hand landmark detection
- Inspired by [Gesture Synth](https://gesture-synth-weld.vercel.app) by Eric Wei
- Thanks to everyone who contributed hand sign data