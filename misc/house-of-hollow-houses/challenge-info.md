# CSAW Challenge Deployment — Clarifications

As we get ready for CSAW challenge deployments, we would appreciate the following clarifications from challenge authors for all applicable challenges.

* **Challenge Name:** House of Hollow Houses
* **Final flag (of format csaw{flag}):** `csaw{w4nd3r3r_0f_th3_h0ll0w_h0us3}`
* **Challenge description:** Misc / Web. A labyrinth of "hollow" rooms served as a static website — each room links to others, and the flag lies waiting in the sanctum. Players wander the interlinked rooms (and read what the pages are quietly telling them) to find the way in. Hosted service on port **8000**.
* **Files/folders — player vs deployment:**
  * **Player receives:** a URL to the hosted site (the served `chal/` rooms); no downloadable files needed.
  * **Deployment:** `Dockerfile`, `chal/` (the generated site).
  * **Exclude (private):** the generator/build internals (e.g. `chal/gen.py`) and any solve notes.
* **Accredited alias:** Star$cream

OPTIONAL:

* **Release wave preference:** No preference (any wave).
* **Solve script / writeup:** _(available on request)._
