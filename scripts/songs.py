"""
songs.py
Songs for song mode, written in numbered notation (jianpu).
Note: titles must use English letters (OpenCV cannot draw Chinese characters).

How to write a song:
    - Notes are separated by spaces:          1 2 3
    - Chord: add /CHORD after a note:         1/I  5/V  6/vi
      The chord stays until a new one is written.
    - High octave: add '  (apostrophe):       1'
    - Low octave:  add ,  (comma):            5,

Add your own songs to the list below!
"""

SONGS = [
    {
        "title": "Little Bee (Xiao Mi Feng)",   # OpenCV can't draw Chinese characters
        "notes": "5/I 3 3 4/V 2 2 1/I 2 3 4 5 5 5",
    },
    {
        "title": "Twinkle Twinkle Little Star",
        "notes": "1/I 1 5 5 6/IV 6 5/I 4/IV 4 3/I 3 2/V 2 1/I",
    },
    {
        "title": "Mary Had a Little Lamb",
        "notes": "3/I 2 1 2 3 3 3 2/V 2 2 3/I 5 5 3 2 1 2 3 3 3 3 2/V 2 3 2 1/I",
    },
    {
        "title": "Ode to Joy",
        "notes": "3/I 3 4 5 5/V 4 3 2 1/I 1 2 3 3/V 2 2",
    },
]


def parse_song(text):
    """'1/I 1 5'' -> [{'sign': '1', 'octave': 0, 'chord': 'I'}, ...]"""
    steps = []
    chord = None
    for token in text.split():
        if "/" in token:
            token, chord = token.split("/", 1)
        octave = 0
        while token.endswith("'"):
            octave += 1
            token = token[:-1]
        while token.endswith(","):
            octave -= 1
            token = token[:-1]
        steps.append({"sign": token, "octave": octave, "chord": chord})
    return steps