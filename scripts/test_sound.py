"""
test_sound.py
Step 2 test: Does the sound engine work, and can it play several notes at once?
  1. Plays 1 2 3 4 5 6 7 (do re mi fa sol la ti) in the middle octave, then 1 in low and high
  2. Plays a C chord (C-E-G) with a melody note on top, all together
"""

import time

from sound_player import SoundPlayer
from music_utils import sign_to_midi, note_name


def main():
    player = SoundPlayer()
    player.start()

    print("Part 1: scale")
    for sign in ["1", "2", "3", "4", "5", "6", "7"]:
        midi = sign_to_midi(sign)
        print(f"  {sign} -> {note_name(midi)}")
        nid = player.note_on(midi)
        time.sleep(0.4)
        player.note_off(nid)
        time.sleep(0.05)
    for shift, name in [(-1, "low"), (0, "middle"), (1, "high")]:
        midi = sign_to_midi("1", octave_shift=shift)
        print(f"  1 ({name}) -> {note_name(midi)}")
        nid = player.note_on(midi)
        time.sleep(0.4)
        player.note_off(nid)
        time.sleep(0.05)
    time.sleep(0.5)

    print("Part 2: chord + melody together")
    chord = [player.note_on(m, volume=0.5) for m in (48, 52, 55)]   # C3 E3 G3 (lower, softer)
    for sign in ["3", "2", "1"]:
        nid = player.note_on(sign_to_midi(sign))
        time.sleep(0.5)
        player.note_off(nid)
    for c in chord:
        player.note_off(c)
    time.sleep(0.5)

    player.stop()
    print("Done! If you heard everything clearly, the sound engine works.")


if __name__ == "__main__":
    main()