# CSAW Challenge Deployment — Clarifications

As we get ready for CSAW challenge deployments, we would appreciate the following clarifications from challenge authors for all applicable challenges.

* **Challenge Name:** Hells Bells
* **Final flag (of format csaw{flag}):** `csaw{wh3n_y0u_r34ch_th3_cr0ssr04ds_d0nt_turn_l3ft}`
* **Challenge description:** Pwn (Hard, glibc 2.31). A demolition "charge" inventory manager. A defused charge is left dangling; the manager still lets you rewire (write) and inspect (read) that freed slot — a use-after-free that leaks libc and poisons the tcache / `__free_hook` to run `system("/bin/sh")`. Served over `nc` on port **1024**.
* **Files/folders — player vs deployment:**
  * **Player receives:** `README.md`, `files/` (`thermite-charge` binary, `libc-2.31.so`, `ld-2.31.so`, `files/Dockerfile` local-repro, and `files/flag.txt` which is a **placeholder**).
  * **Exclude (deployment / private):** the challenge-root `Dockerfile` (deploy image), the challenge-root `flag.txt` (**the real flag**), and `solution/` (`generate.py`, `thermite-charge.c`, `solve.py`, `writeup.md`).
* **Accredited alias:** DirtyHarry

OPTIONAL:

* **Release wave preference:** No preference (any wave).
* **Solve script / writeup:** `solution/solve.py`, `solution/writeup.md`.
