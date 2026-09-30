# CSAW Challenge Deployment — Clarifications

As we get ready for CSAW challenge deployments, we would appreciate the following clarifications from challenge authors for all applicable challenges.

* **Challenge Name:** Diamond Dogs
* **Final flag (of format csaw{flag}):** `csaw{w3dd1ngs_4r3_b4s1c4lly_fun3r4ls_w1th_c4k3}`
* **Challenge description:** Pwn (Medium–Hard, glibc 2.31). A K-9 unit manager: adopt a dog, name it, command it to bark, release it. A released dog leaves a dangling pointer (use-after-free); reclaim the freed object with attacker bytes to hijack its bark handler and pop a shell. Served over `nc` on port **1025**.
* **Files/folders — player vs deployment:**
  * **Player receives:** `README.md`, `files/` (`guard-dog` binary, `libc-2.31.so`, `ld-2.31.so`, `files/Dockerfile` local-repro, and `files/flag.txt` which is a **placeholder**).
  * **Exclude (deployment / private):** the challenge-root `Dockerfile` (deploy image), the challenge-root `flag.txt` (**the real flag**), and `solution/` (`build.py`, `guard-dog.c`, `solve.py`, `writeup.md`).
* **Accredited alias:** Noisyboy

OPTIONAL:

* **Release wave preference:** No preference (any wave).
* **Solve script / writeup:** `solution/solve.py`, `solution/writeup.md`.
