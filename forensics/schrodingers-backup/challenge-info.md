# CSAW Challenge Deployment - Clarifications

As we get ready for CSAW challenge deployments, we would appreciate the following clarifications from challenge authors for all applicable challenges.

- **Challenge Name:** Schrodinger's Backup
- **Final flag (of format csaw{flag}):** `csaw{th3_c4t_c0mm1tt3d_but_th3_j0urn4l_r3m3mb3r5}`
- **Challenge description:** Forensics (Easy-Medium, provisional pending human playtesting). Recover an ordered history of committed SQLite WAL snapshots, XOR the two display shares at each armed commit, and derive the key to a sealed capsule. Repeated displays and maintenance-only commits count as separate visits. Use `README.md` for the player-facing description.
- **Files/folders - player vs deployment:**
  - **Player receives:** `README.md`, `files/evidence.zip`.
  - **Exclude (deployment / private):** `challenge-info.md`, `solution/`, `tests/`. The generator embeds the flag and private fixture seed; do not distribute the challenge folder recursively.
- **Accredited alias:** ChinmayShringi

OPTIONAL:

- **Release wave preference:** No preference (any wave).
- **Solve script / writeup:** `solution/solve.py`, `solution/writeup.md`.
- **Hosting:** None. Upload the frozen ZIP as a downloadable attachment. All evidence is synthetic and self-contained.
