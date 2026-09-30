# Museum time capsule: acquisition notes

The north and south display controllers store one 32-byte share each. Their
bitwise XOR is the token currently on display. The operator may update both
controllers and the armed switch in a single transaction. Intermediate page
writes do not represent a display visitors actually saw.

The capsule recorder samples once after **each committed transaction**. If the
controller is armed at that point, it appends the displayed token to its memory.
If it is disarmed, it appends nothing. Repeated tokens still count as separate
visits, including commits that only update the maintenance controller's pulse.
One controller may change while the others keep their previous values. The
recorder started with empty memory at this acquisition's baseline;
the baseline state itself is not a visit. No other transactions occurred between
that baseline and the acquisition. There is no stored audit-history table.

The included `recorder.py` specifies the token, key derivation, and capsule
envelope. It does not recover a recorder's lost memory. `capsule.json` is version
1: a 12-byte nonce and AES-256-GCM ciphertext with its appended authentication
tag, both represented as hexadecimal. Python's `cryptography==50.0.1` package
can read the envelope. The associated data is the domain string in `recorder.py`,
including its trailing NUL byte.

The controller was disarmed after the exhibit closed. The emergency acquisition
copied `catalog.db` and its uncheckpointed `catalog.db-wal` separately. The WAL
file can contain an unfinished transaction and residue from an older generation.
Preserve the original files before opening a working copy in SQLite: normal
database access can checkpoint or discard recovery evidence. No shared-memory
file is needed for an offline examination.

All evidence is synthetic and self-contained. No server, account, network
capture, or external lookup is required. The capsule plaintext uses `csaw{...}`.
