#!/usr/bin/env python3
"""Recover the capsule from committed database history, using only player files."""

import argparse
import hashlib
import json
import sqlite3
import sys
import zipfile
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from wal_reader import MAX_DATABASE_BYTES, MAX_WAL_BYTES, committed_snapshots

DOMAIN = b"csaw-2026/schrodingers-backup/v1\0"
ARCHIVE_LIMIT = 40 * 1024 * 1024
MEMBER_LIMITS = {
    "catalog.db": MAX_DATABASE_BYTES,
    "catalog.db-wal": MAX_WAL_BYTES,
    "capsule.json": 16384,
    "recorder.py": 65536,
    "OPERATIONS.md": 65536,
}
DEFAULT_ARCHIVE = Path(__file__).resolve().parents[1] / "files" / "evidence.zip"


def read_evidence(archive: Path) -> tuple[bytes, bytes, bytes]:
    if archive.stat().st_size > ARCHIVE_LIMIT:
        raise ValueError("Evidence archive exceeds the supported size")
    with zipfile.ZipFile(archive) as evidence:
        members = evidence.infolist()
        if len(members) != len(MEMBER_LIMITS) or {item.filename for item in members} != set(MEMBER_LIMITS):
            raise ValueError("Evidence archive has missing, duplicate, or unexpected members")
        if any(item.file_size > MEMBER_LIMITS[item.filename] for item in members):
            raise ValueError("Evidence archive member exceeds the supported size")
        if sum(item.file_size for item in members) > ARCHIVE_LIMIT:
            raise ValueError("Expanded evidence exceeds the supported size")
        return tuple(evidence.read(name) for name in ("catalog.db", "catalog.db-wal", "capsule.json"))


def snapshot_token(snapshot: bytes) -> bytes | None:
    # A private copy in rollback mode avoids SQLite seeking an external WAL.
    standalone = snapshot[:18] + b"\x01\x01" + snapshot[20:]
    connection = sqlite3.connect(":memory:")
    try:
        connection.deserialize(standalone)
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA query_only=ON")
        connection.set_progress_handler(lambda: 1, 100000)
        connection.set_authorizer(
            lambda action, *_: sqlite3.SQLITE_OK
            if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ) else sqlite3.SQLITE_DENY
        )
        objects = connection.execute(
            "SELECT name, type FROM sqlite_schema WHERE name IN ('control', 'north', 'south')"
        ).fetchall()
        if set(objects) != {("control", "table"), ("north", "table"), ("south", "table")}:
            raise ValueError("Snapshot is missing the expected controller tables")
        controls = connection.execute("SELECT id, armed, label FROM control LIMIT 2").fetchall()
        north = connection.execute("SELECT id, share FROM north LIMIT 2").fetchall()
        south = connection.execute("SELECT id, share FROM south LIMIT 2").fetchall()
        if len(controls) != 1 or controls[0][0] != 1 or type(controls[0][1]) is not int or controls[0][1] not in (0, 1):
            raise ValueError("Invalid controller state")
        if not isinstance(controls[0][2], str):
            raise ValueError("Invalid controller label")
        for rows in (north, south):
            if len(rows) != 1 or rows[0][0] != 1 or not isinstance(rows[0][1], bytes) or len(rows[0][1]) != 32:
                raise ValueError("Invalid display share")
        if controls[0][1] == 0:
            return None
        return bytes(left ^ right for left, right in zip(north[0][1], south[0][1], strict=True))
    except sqlite3.Error as error:
        raise ValueError(f"Cannot read committed SQLite snapshot: {error}") from error
    finally:
        connection.close()


def decrypt_capsule(capsule: bytes, tokens: tuple[bytes, ...]) -> str:
    try:
        document = json.loads(capsule)
        if not isinstance(document, dict) or set(document) != {"version", "nonce", "ciphertext"}:
            raise ValueError("Invalid capsule fields")
        if type(document["version"]) is not int or document["version"] != 1:
            raise ValueError("Unsupported capsule version")
        nonce = bytes.fromhex(document["nonce"])
        ciphertext = bytes.fromhex(document["ciphertext"])
        if len(nonce) != 12 or not 16 <= len(ciphertext) <= 4096:
            raise ValueError("Invalid capsule nonce or ciphertext size")
    except (ValueError, TypeError, UnicodeDecodeError) as error:
        raise ValueError(f"Malformed capsule: {error}") from error
    key = hashlib.sha256(DOMAIN + b"".join(tokens)).digest()
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, DOMAIN).decode("utf-8")
    except InvalidTag as error:
        raise ValueError("Capsule authentication failed; the committed history is incomplete or incorrect") from error
    except UnicodeDecodeError as error:
        raise ValueError("Capsule plaintext is not UTF-8") from error


def solve(archive: Path) -> str:
    database, wal, capsule = read_evidence(archive)
    tokens = tuple(
        token for snapshot in committed_snapshots(database, wal)
        if (token := snapshot_token(snapshot)) is not None
    )
    if not tokens:
        raise ValueError("No armed committed snapshots were recovered")
    return decrypt_capsule(capsule, tokens)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", nargs="?", type=Path, default=DEFAULT_ARCHIVE)
    arguments = parser.parse_args()
    try:
        print(solve(arguments.archive))
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as error:
        print(f"solve: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
