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
    # ---------- Easy: middle octave only ----------
    {
        "title": "Little Bee (Xiao Mi Feng)",   # OpenCV can't draw Chinese characters
        "notes": "5/I 3 3 4/V 2 2 1/I 2 3 4 5 5 5",
    },
    {
        "title": "Mary Had a Little Lamb",
        "notes": "3/I 2 1 2 3 3 3 2/V 2 2 3/I 5 5 3 2 1 2 3 3 3 3 2/V 2 3 2 1/I",
    },
    {
        "title": "Twinkle Twinkle Little Star",
        "notes": "1/I 1 5 5 6/IV 6 5/I 4/IV 4 3/I 3 2/V 2 1/I",
    },
    {
        "title": "London Bridge",
        "notes": "5/I 6 5 4 3 4 5 2/V 3 4 3/I 4 5 5 6 5 4 3 4 5 2/V 5 3/I 1",
    },
    {
        "title": "Ode to Joy",
        "notes": "3/I 3 4 5 5/V 4 3 2 1/I 1 2 3 3/V 2 2 "
                 "3/I 3 4 5 5/V 4 3 2 1/I 1 2 3 2/V 1 1/I",
    },
    {
        "title": "Jingle Bells",
        "notes": "3/I 3 3 3 3 3 3 5 1 2 3 4/IV 4 4 4 4 3/I 3 3 3 2/V 2 3 2 5 "
                 "3/I 3 3 3 3 3 3 5 1 2 3 4/IV 4 4 4 4 3/I 3 3 5/V 5 4 2 1/I",
    },
    # ---------- Medium: uses the LOW or HIGH octave zone ----------
    {
        "title": "Two Tigers (Liang Zhi Lao Hu)",
        "notes": "1/I 2 3 1 1 2 3 1 3 4 5 3 4 5 5 6 5 4 3 1 5 6 5 4 3 1 "
                 "1 5,/V 1/I 1 5,/V 1/I",
    },
    {
        "title": "Row Row Row Your Boat",
        "notes": "1/I 1 1 2 3 3 2 3 4 5 1' 1' 1' 5 5 5 3 3 3 1 1 1 5 4 3 2/V 1/I",
    },
    {
        "title": "Old MacDonald",
        "notes": "1/I 1 1 5, 6,/IV 6, 5,/I 3 3 2/V 2 1/I "
                 "5, 1 1 1 5, 6,/IV 6, 5,/I 3 3 2/V 2 1/I",
    },
    {
        "title": "Happy Birthday",
        "notes": "5,/I 5, 6, 5, 1 7,/V 5, 5, 6, 5, 2 1/I "
                 "5, 5, 5 3 1 7,/IV 6, 4 4 3/I 1 2/V 1/I",
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