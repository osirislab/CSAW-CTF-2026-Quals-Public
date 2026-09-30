# Midnight Vault

One integrated heist challenge with multiple locked artifacts and a final vault.
The intended solve path is to recover each fragment from the supplied files, carry the recovered state forward, and then open the vault with the completed set.

The landing page should stay thin; the real work happens in the artifacts.

## Solve Notes

Each stage expects the recovered fragment submission or the exact marker string for that stage. The markers are hyphenated values like `GRANITE-71`, `CRYO-29`, and `FERRUM-83`; they are not hash symbols and should be submitted exactly as written.

For a full walkthrough, use `solver/solve.py`. It prints the recovered plaintext for each artifact, the stage marker to submit, and the final vault flag.

## Playtesting

1. Start the Flask app from `app/` and confirm the Granite, Frost, Iron, and Vault routes load in order.
2. Use `solver/solve.py` once to confirm the artifact pipeline still resolves cleanly and prints the expected stage markers.
3. Play through the web UI with a fresh session cookie and verify each gate accepts either the recovered plaintext fragment or the exact hyphenated marker string.
4. Confirm the final vault still accepts the submitted flag and that the success state persists in the inventory view.
5. Reset the browser session and repeat the run to make sure the challenge is deterministic across playtests.

For competition deployment, do NOT ship `solver/`. Change the Flask secret, disable debug, run behind a reverse proxy, and preferably generate a unique artifact set per team.
