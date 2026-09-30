# CSAW Challenge Deployment — Clarifications

As we get ready for CSAW challenge deployments, we would appreciate the following clarifications from challenge authors for all applicable challenges.

* **Challenge Name:** Ghost in the Machine
* **Final flag (of format csaw{flag}):** `csaw{t1m1ng_1s_3v3ryth1ng_1n_th3_s1l3nt_ch4nn3l}`
* **Challenge description:** Forensics / Networking (Hard). A host quietly beacons out of a locked-down network with identical `PING` packets. The message is hidden in packet timing, salted with decoy packets (told apart only by IP TTL), and XOR-keyed with a key carried in the UDP source ports. Filter the real packets, read the gaps, then un-XOR.
* **Files/folders — player vs deployment:**
  * **Player receives:** `README.md`, `files/capture.pcap`.
  * **Exclude (deployment / private):** `solution/` (`generate.py`, `solve.py`, `writeup.md`).
* **Accredited alias:** Lazarus

OPTIONAL:

* **Release wave preference:** No preference (any wave).
* **Solve script / writeup:** `solution/solve.py`, `solution/writeup.md`.
