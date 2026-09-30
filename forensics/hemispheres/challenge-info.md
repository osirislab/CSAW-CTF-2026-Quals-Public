# CSAW Challenge Deployment — Clarifications

As we get ready for CSAW challenge deployments, we would appreciate the following clarifications from challenge authors for all applicable challenges.

* **Challenge Name:** Hemispheres
* **Final flag (of format csaw{flag}):** `csaw{0n3_f1l3_tw0_truth5_p0lygl0t_m4g1c}`
* **Challenge description:** Forensics (Medium–Hard). One file that is simultaneously a valid PNG image and a password-protected ZIP archive (a polyglot read from opposite ends). The archive password is hidden in the least-significant bits of the image's blue channel; players must extract it from the pixels to decrypt `flag.txt`.
* **Files/folders — player vs deployment:**
  * **Player receives:** `README.md`, `files/the_signal.png`.
  * **Exclude (deployment / private):** `solution/` (`generate.py`, `solve.py`, `writeup.md`).
* **Accredited alias:** VnVk1n

OPTIONAL:

* **Release wave preference:** No preference (any wave).
* **Solve script / writeup:** `solution/solve.py`, `solution/writeup.md`.
