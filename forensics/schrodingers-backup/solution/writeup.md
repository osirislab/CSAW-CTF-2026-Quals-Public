# Schrodinger's Backup - Writeup

**Flag:** `csaw{th3_c4t_c0mm1tt3d_but_th3_j0urn4l_r3m3mb3r5}`
**Difficulty:** Easy-Medium, provisional pending human playtesting.

## Deployment

Distribute only `README.md` and the frozen `files/evidence.zip`. No hosting,
accounts, or network services are required. Keep `challenge-info.md`, `solution/`,
and `tests/` private. The generator contains the flag and private fixture seed.
The ZIP contains exactly `catalog.db`, `catalog.db-wal`, `capsule.json`,
`recorder.py`, and `OPERATIONS.md`. Its notes originate in `solution/OPERATIONS.md`.

SHA-256 of the frozen attachment:

```text
ad0c49b04c9d72b5892a0d392fdc0fe3b73c41c316ffac258a7ad745ec949dfe
```

## Build and solve

Use Python 3.11 or later with SQLite and `cryptography==50.0.1`.
Run from the challenge directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r solution/requirements.txt
.venv/bin/python solution/generate.py
.venv/bin/python solution/solve.py
.venv/bin/python -m unittest discover -s tests -v
```

The solver prints the flag above. The attachment was generated with Python
3.12.8 / SQLite 3.47.1. Same-runtime regeneration is byte-identical, including
ZIP metadata, WAL salts, and nonce. SQLite releases may serialize pages
differently; semantic correctness across runtimes does not imply identical
bytes. Deploy the committed attachment rather than rebuilding it on a server.

## Recovering the history

The final database retains only the latest display shares. The useful evidence
is the ordered sequence of committed snapshots in its write-ahead log (WAL).
The public recorder and notes specify the cryptography and sampling rule:

1. After each committed transaction, read `control.armed`. If it is 1, XOR the
   32-byte shares from the `id = 1` rows in `north` and `south` and append that
   token. A repeated token is another visit, including maintenance-only commits.
   The disarmed acquisition baseline is not a visit.
2. Recover complete transaction states, carrying unchanged pages forward from
   the baseline. North-only and south-only updates, control-only rearming, and
   maintenance-only commits prevent sampling one panel's writes as a shortcut.
3. Hash `b"csaw-2026/schrodingers-backup/v1\0"` followed by the concatenated
   tokens with SHA-256. The domain ends in one actual NUL byte.
4. Use the digest as an AES-256-GCM key, the domain as associated data, and the
   nonce and ciphertext-with-tag from `capsule.json`. Authentication reveals
   the flag; no key search or cryptographic guessing is intended.

The fixture has 28 committed snapshots and 20 armed visits, including four
maintenance-only visits. Both its baseline and final committed state are disarmed.
Deduplicating XOR tokens loses valid visits, even when different share pairs
produce the same display.

## Accepted recovery approaches

A native SQLite approach can materialize history without implementing WAL salts
or checksums manually. For each complete frame prefix, put a fresh copy of the
baseline and that WAL prefix together in a separate temporary directory, then
query `control`, `north`, `south`, and `maintenance` through SQLite. Always use
fresh copies: opening a database can checkpoint or remove its journal. SQLite
handles valid commits and rejects unfinished or older-generation residue.
Frame size is 24 plus the page size stored at WAL header bytes 8 through 11;
the first frame follows the 32-byte header. No manual checksum or salt logic
is needed for this route.

Compare successive **full table states**, including `maintenance`, and retain
changes in order, excluding the baseline. In this fixture, consecutive duplicate
states arise from prefixes without a newly visible commit. Do not deduplicate
XOR tokens, panel rows alone, or nonconsecutive states. This approach is
fixture-specific: a different fixture with commits that leave every queried
value unchanged would require explicit commit enumeration to preserve visits.

The reference solver instead implements WAL replay. It reads the 32-byte header,
uses its page size and checksum byte order, validates cumulative checksums and
both salts, and stops at the first invalid frame. A nonzero database-size field
marks a commit; all preceding page replacements in that transaction become
visible together. Valid frames without a following commit contribute nothing.
The stale-generation suffix contains a plausible commit marker, so replaying
all physical commits produces a wrong transcript. Trying candidate history
prefixes against GCM authentication is also an accepted alternative.

The reference solver reads archive members in memory and never executes the
recorder or opens the original evidence through SQLite. It adjusts read/write
format bytes only on snapshot copies before deserializing them. Its archive,
query, and replay limits remain useful defensive checks for organizer tooling.

## Hints

Release progressively if needed:

1. A database can have more history than its SQL tables expose.
2. A journal frame is a page. A transaction can change more than one page.
3. A page written before a crash is not proof of a commit. SQLite can interpret
   the journal for you, or its header and frame checksums identify valid history.

Tool-specific support hint, only if a player is blocked: some WAL tools reject
unfinished or older-generation trailing frames. Work on copies and retain the
prefix ending at the last valid commit, or let native SQLite recover each prefix.

Verified with `sqlite-dissect 1.0.0`: the original WAL fails at physical frame 38
with `WalParsingError`; removing only the stale suffix still raises
`NotImplementedError` for uncommitted frames 35-37. Its `-k` option does not avoid
either failure. The 35,664-byte prefix ending at frame 34 succeeds and preserves
all 28 commits. The tool is optional, not a required player dependency.

## Validation and limitations

Recorded validation passed all 35 tests on Python 3.12.8 / SQLite 3.47.1 and
Python 3.11.15 / SQLite 3.53.1. All four tables matched native SQLite recovery
at all 28 commit prefixes; recovered snapshots passed integrity checks. Tests
reject final-only, reversed, deduplicated, incomplete, changed-only, south-page
carved, and indiscriminate histories. The archive contains neither the plaintext
flag nor private seed, and solving leaves it unchanged.
The native SQLite prefix solve is covered by a separate regression test.

The generator uses real SQLite page images, then normalizes salts/checksums,
creates an uncommitted tail, and appends older-generation framing. This is a
synthetic teaching fixture, not an acquisition from a naturally occurring crash.
Deterministic private randomness and the GCM nonce support reproducibility;
they are not a production encryption design. Regenerate the complete attachment
and update metadata together if the flag or history changes.

Human difficulty and enjoyment remain untested. Arrange two independent human
solves before merge and use their feedback to finalize difficulty and hints.
Automated correctness does not establish solve time or player enjoyment.

## Inspiration and references

[CSAW 2024 ZipZipZip](https://github.com/osirislab/CSAW-CTF-2024-Quals/blob/main/forensics/ZipZipZip/README.md)
inspired evidence reconstruction;
[CSAW 2024 is_there_an_echo](https://github.com/osirislab/CSAW-CTF-2024-Quals/blob/main/forensics/is_there_an_echo/README.md)
inspired recovering hidden history from its representation. Neither is cited as
a WAL precedent. The nearest identified precedent is the
[NPST 2020 SQLite task](https://blog.roysolberg.com/2021/01/pst-challenge-5), whose
firsthand writeup compares database views with and without a WAL. This challenge
combines an ordered committed transcript with repeated observations; no global
novelty is claimed. [SQLite's WAL format](https://www.sqlite.org/fileformat2.html#wal_file_format)
is the primary reference for frames, commit markers, salts, and checksums.
