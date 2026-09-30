"""Exercise the frozen player handout, independently of generator internals."""

import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

CHALLENGE = Path(__file__).resolve().parents[1]
sys.path = [str(CHALLENGE / "solution"), *sys.path]

from solve import solve
from wal_reader import committed_snapshots

ARCHIVE = CHALLENGE / "files" / "evidence.zip"
DOMAIN = b"csaw-2026/schrodingers-backup/v1\0"
FLAG = "csaw{th3_c4t_c0mm1tt3d_but_th3_j0urn4l_r3m3mb3r5}"


def read_state(snapshot):
    image = snapshot[:18] + b"\x01\x01" + snapshot[20:]
    connection = sqlite3.connect(":memory:")
    try:
        connection.deserialize(image)
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute("PRAGMA query_only = ON")
        if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise AssertionError("Recovered snapshot is not a valid SQLite database")
        armed = connection.execute("SELECT armed FROM control WHERE id = 1").fetchone()[0]
        north = connection.execute("SELECT share FROM north WHERE id = 1").fetchone()[0]
        south = connection.execute("SELECT share FROM south WHERE id = 1").fetchone()[0]
        return armed, bytes(a ^ b for a, b in zip(north, south, strict=True))
    finally:
        connection.close()


def open_capsule(tokens, capsule):
    key = hashlib.sha256(DOMAIN + b"".join(tokens)).digest()
    return AESGCM(key).decrypt(
        bytes.fromhex(capsule["nonce"]),
        bytes.fromhex(capsule["ciphertext"]),
        DOMAIN,
    )


def native_full_state(database, wal_prefix):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "catalog.db").write_bytes(database)
        (root / "catalog.db-wal").write_bytes(wal_prefix)
        connection = sqlite3.connect(root / "catalog.db")
        try:
            return tuple(
                tuple(connection.execute(f'SELECT * FROM "{table}" ORDER BY id'))
                for table in ("control", "north", "south", "maintenance")
            )
        finally:
            connection.close()


class HandoutIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(ARCHIVE) as archive:
            cls.database = archive.read("catalog.db")
            cls.wal = archive.read("catalog.db-wal")
            cls.capsule = json.loads(archive.read("capsule.json"))

    def test_shipped_archive_solves_without_changing_evidence(self):
        before = ARCHIVE.read_bytes()
        self.assertEqual(solve(ARCHIVE), FLAG)
        self.assertEqual(ARCHIVE.read_bytes(), before)

    def test_native_sqlite_prefix_solve_needs_no_custom_wal_validation(self):
        before = ARCHIVE.read_bytes()
        frame_size = 24 + int.from_bytes(self.wal[8:12], "big")
        previous = native_full_state(self.database, b"")
        tokens = ()
        commits = 0
        for end in range(32 + frame_size, len(self.wal) + 1, frame_size):
            state = native_full_state(self.database, self.wal[:end])
            if state == previous:
                continue
            previous = state
            commits = commits + 1
            if state[0][0][1] == 1:
                north, south = state[1][0][1], state[2][0][1]
                tokens = tokens + (bytes(a ^ b for a, b in zip(north, south, strict=True)),)
        self.assertEqual(commits, 28)
        self.assertEqual(len(tokens), 20)
        self.assertEqual(open_capsule(tokens, self.capsule), FLAG.encode())
        self.assertEqual(ARCHIVE.read_bytes(), before)

    def test_solver_is_portable_and_does_not_need_generator(self):
        with tempfile.TemporaryDirectory(prefix="capsule test ") as directory:
            root = Path(directory)
            for name in ("solve.py", "wal_reader.py"):
                shutil.copyfile(CHALLENGE / "solution" / name, root / name)
            shutil.copyfile(ARCHIVE, root / "player evidence.zip")
            result = subprocess.run(
                [sys.executable, str(root / "solve.py"), str(root / "player evidence.zip")],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), FLAG)
            self.assertEqual(result.stderr, "")

    def test_snapshots_are_valid_and_match_sqlite_final_recovery(self):
        snapshots = tuple(committed_snapshots(self.database, self.wal))
        self.assertGreater(len(snapshots), 20)
        states = tuple(read_state(snapshot) for snapshot in snapshots)
        self.assertEqual(read_state(self.database)[0], 0)
        self.assertEqual(states[-1][0], 0)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "catalog.db").write_bytes(self.database)
            (root / "catalog.db-wal").write_bytes(self.wal)
            connection = sqlite3.connect(root / "catalog.db")
            try:
                recovered = connection.serialize()
                self.assertEqual(read_state(recovered), states[-1])
            finally:
                connection.close()

    def test_only_ordered_full_committed_history_unlocks_capsule(self):
        states = tuple(
            read_state(snapshot)
            for snapshot in committed_snapshots(self.database, self.wal)
        )
        tokens = tuple(token for armed, token in states if armed == 1)
        self.assertGreater(len(tokens), len(set(tokens)), "Fixture must include a repeat")
        self.assertEqual(open_capsule(tokens, self.capsule), FLAG.encode())
        wrong_histories = (
            (),
            (states[-1][1],),
            tokens[:-1],
            tuple(reversed(tokens)),
            tuple(dict.fromkeys(tokens)),
            tuple(token for _, token in states),
        )
        for history in wrong_histories:
            with self.subTest(history_length=len(history)):
                with self.assertRaises(InvalidTag):
                    open_capsule(history, self.capsule)

    def test_frozen_archive_contains_only_public_files(self):
        expected = {"catalog.db", "catalog.db-wal", "capsule.json", "recorder.py", "OPERATIONS.md"}
        with zipfile.ZipFile(ARCHIVE) as archive:
            self.assertEqual(set(archive.namelist()), expected)
            self.assertEqual(len(archive.namelist()), len(expected))
            for name in expected:
                self.assertNotIn(FLAG.encode(), archive.read(name), name)
            compile(archive.read("recorder.py"), "recorder.py", "exec")


if __name__ == "__main__":
    unittest.main()
