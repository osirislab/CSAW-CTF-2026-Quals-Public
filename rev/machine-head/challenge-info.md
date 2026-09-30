# CSAW Challenge Deployment — Clarifications

As we get ready for CSAW challenge deployments, we would appreciate the following clarifications from challenge authors for all applicable challenges.

* **Challenge Name:** Machine Head
* **Final flag (of format csaw{flag}):** `csaw{cl1mb1ng_th3_v1rtu4l_st4ck_0n3_0pc0d3_4t_4_t1m3}`
* **Challenge description:** Reverse Engineering (Hard). The flag checker is a custom bytecode VM — the x86 you see is just the interpreter; the real program is data. A running-state register is mixed into every comparison, so each character depends on all the ones before it; the key must be recovered strictly left-to-right by emulating the VM. Usage: `./masterkey <flag>`.
* **Files/folders — player vs deployment:**
  * **Player receives:** `README.md`, `files/masterkey` (stripped x86-64 binary).
  * **Exclude (deployment / private):** `solution/` (`generate.py`, `vm_source.c`, `solve.py`, `writeup.md`).
* **Accredited alias:** HorahLoux

OPTIONAL:

* **Release wave preference:** No preference (any wave).
* **Solve script / writeup:** `solution/solve.py`, `solution/writeup.md`.
