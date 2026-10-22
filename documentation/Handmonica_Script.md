# Handmonica: Checkpoint Presentation Script

Total time: about 10 minutes (about 9 minutes of speaking at a calm pace, plus playing time in the demo and switching speakers).
Timing per slide is in brackets, measured at a calm speaking pace (about 130 words per minute).
The professor's suggested split is Motivation 2 min, Problem 3 min, Solutions 5 min. This script is a bit shorter on Motivation and Problem, which leaves room for the demo. If you finish early, slow down on slides 2 and 3: those are the parts the template gives the most time.

---

## Slide 1: Cover [~20 sec]

Hi everyone. We are Alyssa, Guy, Hider and Armin, and our project is called **Handmonica**.
It's like a harmonica, but you play it with your hands instead of your mouth. It's a webcam instrument for melody, harmony and guided practice, built on an image recognition model that we trained ourselves.

---

## Slide 2: The Core Motivation [~1 min 15 sec]

Our ultimate goal is to make playing and learning music as easy as raising your hand. With just a laptop and a webcam, your hands become the instrument, and the computer becomes your practice tutor.

This isn't just a technical exercise. It matters for three groups of people:

- **Beginners and kids**, who can play a real melody within minutes, instead of practicing for weeks before anything sounds like music.
- **People without an instrument**, because the only thing you need is a webcam.
- **Music learners**, because the hand signs follow numbered notation, 簡譜, which many people here already know. So while you play, you are also practicing reading music.

Why does it matter? It lowers the first barrier to music: no money for an instrument, no finger technique, and it teaches notation while you play.

If we succeed, we are positioning Handmonica to let a first-time user sit in front of a laptop and play a full song with melody and chords on their very first day.

---

## Slide 3: The Problem [~2 min]

To reach that goal, we first had to face a real problem, and it has two sides.

**For learners**, the first steps of music are hard:

- Instruments cost money, and they're not always available.
- Finger technique takes weeks before anything sounds like music, and this is where many beginners give up.
- Reading notation is usually learned separately, so it feels abstract and disconnected from actually playing.
- And when you practice alone, nobody tells you what you did wrong.

**For the technology**, a hand-sign instrument is only useful if recognition is fast and reliable:

- Signs must be recognized in real time. If the note comes late, it doesn't feel like an instrument anymore.
- Every person forms the same sign a little differently, and the thumb is the biggest difference.
- Here is a concrete number from our own training: even with data from three people, sign 7, which is the thumb and index finger, is recognized only 78% of the time. The rest of the time it's read as 6, which is the thumb only. So a small difference in how someone holds their thumb decides which note is played.
- And simple rules like "count the raised fingers" break as soon as the hand is tilted or turned.

For a beginner, this means hearing a wrong note even though they made the right sign. That's frustrating, and it makes them think *they* are the problem.

**In short:** if learning is hard and recognition is unreliable, the instrument can't do its job of making music easy for beginners. That's what our three pillars are designed to solve.

---

## Slide 4: The Solution [~30 sec]

Our solution is one real-time pipeline. The webcam captures a frame, MediaPipe finds the hand and gives us 21 landmarks, our classifier recognizes the sign, the music logic turns it into a note, octave and chord, and a piano synthesizer plays it, all in real time.

We organized the work into three pillars: the **recognition model** as the foundation, the **instrument** as the impact driver, and the **user experience** for guidance and sharing.

---

## Slide 5: Pillar 1 · Recognition Model [~50 sec]

Pillar 1 is the foundation.

**What it does:** MediaPipe finds 21 hand landmarks. We normalize them, putting the wrist at the origin and scaling by hand size, so the model learns the *shape* of the sign, not where the hand is or how far it is from the camera. Then a classifier predicts 8 classes: rest, plus signs 1 to 7.

**Progress:** we built our own dataset of 6,300 samples from three people, compared three models, and added natural variations of the signs to reduce thumb errors.

**Next step:** a leave-one-person-out test to measure accuracy on new users, fixing the 7 versus 6 confusion, and comparing our model with simple rule-based finger counting and with an image CNN.

---

## Slide 6: Training Results [~50 sec]

Here are our results. We trained three models on the same data and tested them on recordings they had never seen: one held-out burst per sign, 480 samples in total.

Random Forest got 96.0%, the MLP neural network 93.3%, and **SVM 96.2%**, so we chose SVM for the instrument.

The confusion matrix shows that 6 of the 8 classes are perfect. The remaining errors are 7 read as 6, 13 out of 60, and 6 read as rest, 5 out of 60. It's still the thumb.

One honest note: all three people are in the training data, so 96.2% measures **known users**. Measuring accuracy on completely **new users** is our next step.

---

## Slide 7: Pillar 2 · The Instrument [~1 min]

Pillar 2 is the impact driver. This is the part that solves the core problem: it turns hand signs into real music, so a beginner can play melody and chords without owning an instrument.

The **right hand** plays the melody: the sign chooses the note, the height of the hand chooses one of three octaves, and the palm size, meaning how close the hand is to the camera, controls the volume.
The **left hand** plays the harmony: its position in the grid chooses one of six chords, C, Dm, Em, F, G and Am. Making a fist plays the chord, and opening and closing the hand plays it again.

**Progress:** it's a working real-time prototype that can already play a full song. A quick downward flick repeats the same note, and you can transpose to any key.

**Next step:** measure the latency, the time from making a sign to hearing the sound.

---

## Slide 8: Pillar 3 · User Experience [~55 sec]

Pillar 3 is the user experience: how the player understands what's happening, and how other people can get the project.

**What it does:** the screen always shows what the model sees: the chord boxes, the octave zones, the current note, and bars for the model's confidence and the volume. This instant feedback is important for beginners, because they can see right away why a note did or didn't play. And anyone can install it from GitHub.

**Progress:** the on-screen display works, the code and a step-by-step README are on GitHub, and three people have tested it.

**Next step:** a **learning mode** that teaches each sign step by step with pictures, a **song mode** that shows the notation and chords on screen so you can play along, and a **user test with beginners by October 29**.

---

## Slide 9: Live Demo [~1 min, including playing]

Now a short live demo. We'll play **Mary Had a Little Lamb**.

The right hand plays the melody, 3, 2, 1, 2, 3, 3, 3, with a quick flick for the repeated notes. The left hand holds chord **I**, C, and moves to chord **V**, G, when the melody goes to 2, 2, 2.

We'll also show expression: moving the hand closer makes it louder, and raising it plays a higher octave.

*(Backup: if the camera or sound doesn't work, play the recorded demo video.)*

---

## Slide 10: What's Next [~45 sec]

To conclude: we're on track.

- **Now**, we have a working real-time instrument with melody and chords.
- **Next**, we'll collect more people's data, run the leave-one-person-out test, and compare our model with rule-based and CNN approaches.
- **Then**, we'll build the learning mode and song mode, measure latency, and run a beginner user test by **October 29**.
- And for the **final** presentation, we'll show the evaluated model and the user-test results.

Our goal for the final is not just an instrument that works, but evidence that it works for new people and actually helps beginners learn.

---

## Slide 11: Thank You [~10 sec]

Thank you! We'd love to hear your questions, and if you have ideas for features we could add, please let us know.
