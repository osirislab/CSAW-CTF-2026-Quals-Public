# The Challenge
 
## First draft
 
It all started with an attempt to set up a timing attack on Python's regular `==`.

When Python compares two strings with ==, it does not necessarily check all the characters in constant time. In a naive comparison, the check walks through both strings character by character and stops as soon as it finds a mismatch.

That means a comparison against a string that is wrong in the first character finishes slightly faster than one that gets the first character right and fails on the second, and so on. Each additional correct character means a few extra comparisons happen before the mismatch is found, which takes a tiny bit more time

Turns out that's *technically* possible, but the timing signal is so minuscule that you need a large number of samples, some statistics, and even then you can't be fully sure.
 
Still, the signal is there, so the plan became: loop a million times and amplify it. Bim bam boom, challenge done.
 
That worked fine for small-scale testing. But the moment it got hit with a real solve attempt, consistent requests cycling through a lot of different possible characters, the signal would just vanish.
 
To this day I'm not 100% sure why. My best guess is that some Python optimizer noticed *"hey, there's a loop running a million times that isn't actually doing anything, let's optimize that away"* but that's pure speculation on my part. The challenge would still be technically solvable you would just have to have done it **EXTREMELY SLOWLY** which I'm sure would have pissed a lot of people of.
 
So, in the end, I cheaped out: chucked a `sleep()` in there and called it a day.
 
## Making It Harder
 
I wanted to add a bit more difficulty, so I:
 
- Hid the amplification logic inside custom libraries uploaded to PyPI: **`reqmeta`** and **`inputval`**
- Played around with different ways of smuggling values into those libraries in a not-immediately-obvious way
- Tried to "camouflage" the libraries by asking AI to pad them with a bunch of random, unrelated libraries: pure slop, just red herrings
...and then, Mr. Genius Author over here wrote:
 
```python
from inputval import Flag
```
 
Which is basically a giant arrow saying **LOOK HERE, THIS IS RELATED TO THE FLAG.**
 
Not my smartest move in retrospect.

## Solution

I made the solver a lot more complicated than it needed to be, just so that infra or moderators could test that the challenge is still working even if the chal was under a lot of load and had a lot of latency because initially this was not meant to be instanced. Now its a bit overkill.

The solve, basically does 3 passes with the given charset, and chooses the "best" one (ie the one with more delay). It is also the product of me slowly losing my mind as to why the signal wasn't appearing when I was still doing the million loop strat. So yes there are some really unnecessary math stuff as I was thinking the issue was with my solve attempt.
 
## TL;DR
 
If you want to solve it:
 
1. Realize that presenting a **Chrome user-agent** causes 2 values from the user-agent to be fed into the timing amplification.
2. Use that timing attack to recover the letters of the flag **one at a time**.
