# Schrodinger's Backup

**Category:** Forensics

**Difficulty:** Easy-Medium (provisional)

**Flag format:** `csaw{...}`

The Museum of Unfinished Futures built a time capsule that remembers everything
its visitors saw. To save space, its controller keeps overwriting the same two
display panels. No screenshots. No audit table. Very forward-thinking.

Then the power failed.

The restored database says the exhibit is closed. The conservator says the
capsule can only be opened with the history that actually happened. The intern
says every page on disk is equally real.

One of them is wrong.

Recover the capsule's message from `files/evidence.zip`. The archive contains the
controller database, its companion journal, the sealed capsule, and the recorder's
source and operating notes. Everything needed is offline.

Keep the original evidence intact and work on copies. Opening a SQLite database
normally can change or remove its companion journal.
