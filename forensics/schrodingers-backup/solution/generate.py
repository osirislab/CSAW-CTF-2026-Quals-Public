#!/usr/bin/env python3
"""Build the private, deterministic Schrodinger's Backup training evidence."""

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import zipfile

from recorder import seal, token
from wal_writer import normalize

ROOT = Path(__file__).resolve().parents[1]
FLAG = b"csaw{th3_c4t_c0mm1tt3d_but_th3_j0urn4l_r3m3mb3r5}"
PRIVATE_SEED = b"museum-generator-v1-frozen-2026"
TRANSACTIONS = 28
FIXED_TIME = (2026, 1, 1, 0, 0, 0)
ACTIONS = (
    "north", "north", "maintenance", "south", "rerandomize", "north", "control",
    "south", "control", "maintenance", "north", "south", "rerandomize", "control",
    "north", "control", "south", "maintenance", "rerandomize", "north", "control",
    "south", "control", "north", "maintenance", "rerandomize", "south", "north",
)


def material(label: str) -> bytes:
    return hashlib.sha256(PRIVATE_SEED + b"\x00" + label.encode("ascii")).digest()


def initialize(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA page_size=1024")
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA wal_autocheckpoint=0")
    connection.executescript(
        "CREATE TABLE control(id INTEGER PRIMARY KEY, armed INTEGER NOT NULL, label TEXT NOT NULL);"
        "CREATE TABLE north(id INTEGER PRIMARY KEY, share BLOB NOT NULL);"
        "CREATE TABLE south(id INTEGER PRIMARY KEY, share BLOB NOT NULL);"
        "CREATE TABLE maintenance(id INTEGER PRIMARY KEY, pulse INTEGER NOT NULL);"
    )
    with connection:
        connection.execute("INSERT INTO control VALUES(1, 0, 'standby')")
        connection.execute("INSERT INTO north VALUES(1, ?)", (material("initial-north"),))
        connection.execute("INSERT INTO south VALUES(1, ?)", (material("initial-south"),))
        connection.execute("INSERT INTO maintenance VALUES(1, 0)")
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def read_display(connection: sqlite3.Connection) -> tuple[bool, bytes]:
    armed, north, south = connection.execute(
        "SELECT armed, north.share, south.share FROM control, north, south"
    ).fetchone()
    return bool(armed), token(north, south)


def write_state(connection: sqlite3.Connection, index: int, armed: bool) -> None:
    action = ACTIONS[index] if index < TRANSACTIONS else "both"
    previous_armed, display = read_display(connection)
    north = material(f"north-{index}")
    south = token(north, display) if action == "rerandomize" else material(f"south-{index}")
    with connection:
        if action in ("north", "both", "rerandomize"):
            connection.execute("UPDATE north SET share=? WHERE id=1", (north,))
        if action in ("south", "both", "rerandomize"):
            connection.execute("UPDATE south SET share=? WHERE id=1", (south,))
        if action == "maintenance":
            connection.execute("UPDATE maintenance SET pulse=? WHERE id=1", (index + 1,))
        if previous_armed != armed:
            connection.execute(
                "UPDATE control SET armed=?, label=? WHERE id=1",
                (int(armed), "recording" if armed else "standby"),
            )


def evidence(database: Path) -> tuple[bytes, bytes, tuple[bytes, ...]]:
    connection = sqlite3.connect(database)
    try:
        initialize(connection)
        baseline = database.read_bytes()
        wal_path = database.with_name(database.name + "-wal")
        history = ()
        stale_transaction = b""
        for index in range(TRANSACTIONS):
            previous_length = len(wal_path.read_bytes())
            write_state(connection, index, index % 7 not in (0, 6))
            armed, display = read_display(connection)
            history = history + (display,) if armed else history
            if index == 1:
                stale_transaction = wal_path.read_bytes()[previous_length:]
        committed_length = len(wal_path.read_bytes())
        write_state(connection, TRANSACTIONS, True)
        wal = normalize(wal_path.read_bytes(), committed_length, stale_transaction)
        return baseline, wal, history
    finally:
        connection.close()


def build(destination: Path) -> Path:
    with tempfile.TemporaryDirectory(prefix="schrodingers-backup-") as directory:
        baseline, wal, history = evidence(Path(directory) / "catalog.db")
    capsule = seal(FLAG, history, material("capsule-nonce")[:12])
    entries = (
        ("catalog.db", baseline),
        ("catalog.db-wal", wal),
        ("capsule.json", (json.dumps(capsule, sort_keys=True, indent=2) + "\n").encode()),
        ("recorder.py", Path(__file__).with_name("recorder.py").read_bytes()),
        ("OPERATIONS.md", Path(__file__).with_name("OPERATIONS.md").read_bytes()),
    )
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / "evidence.zip"
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, content in entries:
            entry = zipfile.ZipInfo(name, FIXED_TIME)
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, content)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", nargs="?", type=Path, default=ROOT / "files")
    print(build(parser.parse_args().destination))


if __name__ == "__main__":
    main()
