# CSAW Challenge Deployment — Clarifications

As we get ready for CSAW challenge deployments, we would appreciate the following clarifications from challenge authors for all applicable challenges.

* **Challenge Name:** Autobahn
* **Final flag (of format csaw{flag}):** `csaw{c0d3_th4t_rewr1t3s_1ts3lf_c4nt_b3_tru5t3d}`
* **Challenge description:** Reverse Engineering (Hard). A self-decrypting flag checker: the important routine ships encrypted in its own ELF section and is decrypted in place at runtime. The flag keystream is derived from the *decrypted* code bytes, so a static guess fails — you must reproduce the self-modification (or just run it). Usage: `./nitro <password>` (password: `n2o_boost`).
* **Files/folders — player vs deployment:**
  * **Player receives:** `README.md`, `files/nitro` (x86-64 binary, non-PIE).
  * **Exclude (deployment / private):** `solution/` (`build.py`, `nitro.c`, `solve.py`, `writeup.md`).
* **Accredited alias:** Striker_Eureka

OPTIONAL:

* **Release wave preference:** No preference (any wave).
* **Solve script / writeup:** `solution/solve.py`, `solution/writeup.md`.
