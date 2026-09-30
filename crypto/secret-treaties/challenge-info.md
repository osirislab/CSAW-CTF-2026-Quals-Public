# CSAW Challenge Deployment — Clarifications

As we get ready for CSAW challenge deployments, we would appreciate the following clarifications from challenge authors for all applicable challenges.

* **Challenge Name:** Secret Treaties
* **Final flag (of format csaw{flag}):** `csaw{LLL_turns_kn4ps4cks_1nt0_p4nc4k3s_wh3n_d3ns1ty_1s_l0w}`
* **Challenge description:** Crypto (Medium). A "quantum-resistant" public-key scheme built on subset-sum: the flag is encrypted nine bytes at a time as a subset sum over a 72-element public key. Players recover it with a low-density lattice (LLL) attack — no trapdoor needed.
* **Files/folders — player vs deployment:**
  * **Player receives:** `README.md`, `files/` (`pubkey.txt`, `ciphertext.txt`).
  * **Exclude (deployment / private):** `solution/` (`generate.py`, `solve.py`, `writeup.md`).
* **Accredited alias:** Icarus

OPTIONAL:

* **Release wave preference:** No preference (any wave).
* **Solve script / writeup:** `solution/solve.py`, `solution/writeup.md`.
