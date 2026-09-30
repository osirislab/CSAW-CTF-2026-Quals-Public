"""Independent synthetic fixtures; no private generator or shipped flag imports."""

import hashlib
import json
import sqlite3
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

sys.path = [str(Path(__file__).resolve().parents[1] / "solution"), *sys.path]
from solve import DOMAIN, decrypt_capsule, read_evidence, snapshot_token, solve
from wal_reader import MAX_DATABASE_BYTES, checksum, committed_snapshots, database_page_size

PAGE_SIZE = 512


def fixture_checksum(payload, endian, previous=(0, 0)):
    words = struct.unpack(("<" if endian == "little" else ">") + "I" * (len(payload) // 4), payload)
    a, b = previous
    for index in range(0, len(words), 2):
        a, b = (a + b + words[index]) % 2**32, (a + 2 * b + words[index] + words[index + 1]) % 2**32
    return a, b


def fixture_database(size=PAGE_SIZE, pages=2):
    prefix = b"SQLite format 3\0" + (1 if size == 65536 else size).to_bytes(2, "big")
    return prefix + bytes(size * pages - len(prefix))


def fixture_wal(frames=(), endian="little", size=PAGE_SIZE, version=3007000):
    magic = 0x377F0682 if endian == "little" else 0x377F0683
    header = struct.pack(">6I", magic, version, size, 0, 0x13579BDF, 0x2468ACE0)
    current = fixture_checksum(header, endian)
    result = header + struct.pack(">2I", *current)
    for number, commit, image in frames:
        prefix = struct.pack(">2I", number, commit)
        current = fixture_checksum(prefix + image, endian, current)
        result = result + prefix + header[16:24] + struct.pack(">2I", *current) + image
    return result


def queryable_snapshot(armed=1, north=bytes(range(32)), south=bytes([0xAA]) * 32):
    connection = sqlite3.connect(":memory:")
    try:
        connection.executescript(
            "CREATE TABLE control(id INTEGER PRIMARY KEY, armed INTEGER, label TEXT);"
            "CREATE TABLE north(id INTEGER PRIMARY KEY, share BLOB);"
            "CREATE TABLE south(id INTEGER PRIMARY KEY, share BLOB);"
        )
        connection.execute("INSERT INTO control VALUES (1, ?, 'test')", (armed,))
        connection.execute("INSERT INTO north VALUES (1, ?)", (north,))
        connection.execute("INSERT INTO south VALUES (1, ?)", (south,))
        connection.commit()
        return connection.serialize()
    finally:
        connection.close()


def fixture_capsule(tokens, plaintext=b"test{independent_fixture}"):
    key = hashlib.sha256(DOMAIN + b"".join(tokens)).digest()
    nonce = bytes(range(12))
    return json.dumps({"version": 1, "nonce": nonce.hex(), "ciphertext": AESGCM(key).encrypt(nonce, plaintext, DOMAIN).hex()}).encode()


class WalReaderTests(unittest.TestCase):
    def test_both_endians_multi_page_commit_and_repeated_updates(self):
        database = fixture_database()
        a, b, c = (bytes([value]) * PAGE_SIZE for value in (1, 2, 3))
        for endian in ("little", "big"):
            with self.subTest(endian=endian):
                wal = fixture_wal(((1, 0, a), (2, 2, b), (2, 0, c), (2, 2, b)), endian)
                self.assertEqual(list(committed_snapshots(database, wal)), [a + b, a + b])
                self.assertEqual(database, fixture_database())
                self.assertEqual(wal, fixture_wal(((1, 0, a), (2, 2, b), (2, 0, c), (2, 2, b)), endian))

    def test_ignores_uncommitted_tail_and_partial_frame(self):
        base = fixture_database()
        committed = bytes([7]) * PAGE_SIZE
        wal = fixture_wal(((2, 2, committed), (2, 0, bytes(PAGE_SIZE))))
        expected = [base[:PAGE_SIZE] + committed]
        self.assertEqual(list(committed_snapshots(base, wal)), expected)
        self.assertEqual(list(committed_snapshots(base, wal[:-17])), expected)
        self.assertEqual(list(committed_snapshots(base, fixture_wal() + b"short")), [])

    def test_stops_at_first_bad_checksum_or_salt_without_resynchronizing(self):
        base = fixture_database()
        wal = fixture_wal(((2, 2, bytes([1]) * PAGE_SIZE), (2, 2, bytes([2]) * PAGE_SIZE), (2, 2, bytes([3]) * PAGE_SIZE)))
        expected = [base[:PAGE_SIZE] + bytes([1]) * PAGE_SIZE]
        for local_offset in (8, 16, 24):
            offset = 32 + 24 + PAGE_SIZE + local_offset
            bad = wal[:offset] + bytes([wal[offset] ^ 1]) + wal[offset + 1:]
            self.assertEqual(list(committed_snapshots(base, bad)), expected)

    def test_rejects_bad_headers(self):
        valid = fixture_wal()
        invalid = (b"", valid[:31], b"bad!" + valid[4:], fixture_wal(version=1), fixture_wal(size=1024), valid[:31] + bytes([valid[31] ^ 1]))
        for wal in invalid:
            with self.subTest(wal=wal), self.assertRaises(ValueError):
                list(committed_snapshots(fixture_database(), wal))

    def test_database_page_validation(self):
        for database in (b"", bytes(512), fixture_database()[:-1], b"SQLite format 3\0\x00\x03" + bytes(1006)):
            with self.assertRaises(ValueError):
                database_page_size(database)
        self.assertEqual(database_page_size(fixture_database(65536, 1)), 65536)
        self.assertEqual(list(committed_snapshots(fixture_database(65536, 1), fixture_wal(size=65536))), [])

    def test_growth_truncation_and_missing_pages(self):
        base = fixture_database()
        added = bytes([4]) * PAGE_SIZE
        wal = fixture_wal(((3, 3, added), (1, 1, base[:PAGE_SIZE])))
        self.assertEqual(list(committed_snapshots(base, wal)), [base + added, base[:PAGE_SIZE]])
        with self.assertRaisesRegex(ValueError, "missing"):
            list(committed_snapshots(base, fixture_wal(((4, 4, added),))))

    def test_page_and_commit_allocation_bounds(self):
        limit = MAX_DATABASE_BYTES // PAGE_SIZE
        for page, commit in ((0, 2), (limit + 1, 2), (2, limit + 1)):
            with self.assertRaisesRegex(ValueError, "bounds"):
                list(committed_snapshots(fixture_database(), fixture_wal(((page, commit, bytes(PAGE_SIZE)),))))

    def test_checksum_inputs(self):
        for endian in ("little", "big"):
            data = bytes(range(32))
            self.assertEqual(checksum(data, endian, (42, 99)), fixture_checksum(data, endian, (42, 99)))
        for data, endian in ((b"short", "little"), (b"", "invalid")):
            with self.assertRaises(ValueError):
                checksum(data, endian)

    def test_cumulative_snapshot_work_is_bounded(self):
        base = fixture_database()
        wal = fixture_wal(((2, 2, bytes(PAGE_SIZE)),) * 2)
        with patch("wal_reader.MAX_REPLAY_BYTES", PAGE_SIZE * 3, create=True):
            snapshots = committed_snapshots(base, wal)
            self.assertEqual(next(snapshots), base)
            with self.assertRaisesRegex(ValueError, "replay budget"):
                next(snapshots)


class SolverTests(unittest.TestCase):
    def test_snapshot_share_xor_and_disarmed_state(self):
        original = queryable_snapshot()
        self.assertEqual(snapshot_token(original), bytes(value ^ 0xAA for value in range(32)))
        self.assertEqual(original, queryable_snapshot())
        self.assertIsNone(snapshot_token(queryable_snapshot(armed=0)))
        self.assertEqual(snapshot_token(original[:18] + b"\x02\x02" + original[20:]), snapshot_token(original))

    def test_invalid_snapshot_values(self):
        for image in (queryable_snapshot(armed=3), queryable_snapshot(north=b"short"), queryable_snapshot(south="text"), fixture_database()):
            with self.assertRaises(ValueError):
                snapshot_token(image)

    def test_capsule_authentication_requires_order_and_duplicates(self):
        tokens = (bytes([1]) * 32, bytes([2]) * 32, bytes([1]) * 32)
        capsule = fixture_capsule(tokens)
        self.assertEqual(decrypt_capsule(capsule, tokens), "test{independent_fixture}")
        for wrong in (tokens[:2], (tokens[1], tokens[0], tokens[2]), ()):
            with self.assertRaisesRegex(ValueError, "authentication"):
                decrypt_capsule(capsule, wrong)

    def test_malformed_capsule(self):
        cases = (b"{}", b"[]", b"not json", b' {"version":true,"nonce":"00","ciphertext":"00"}', b'{"version":1,"nonce":4,"ciphertext":"00"}')
        for capsule in cases:
            with self.assertRaisesRegex(ValueError, "Malformed"):
                decrypt_capsule(capsule, ())

    def test_independent_archive_solution_without_executing_recorder(self):
        database = queryable_snapshot()
        page_size = database_page_size(database)
        pages = tuple(database[i:i + page_size] for i in range(0, len(database), page_size))
        frames = tuple((index, len(pages) if index == len(pages) else 0, image) for index, image in enumerate(pages, 1))
        wal = fixture_wal(frames + frames, size=page_size)
        token = snapshot_token(database)
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "evidence.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("catalog.db", database)
                output.writestr("catalog.db-wal", wal)
                output.writestr("capsule.json", fixture_capsule((token, token)))
                output.writestr("recorder.py", "raise RuntimeError('Do not execute archived source')")
                output.writestr("OPERATIONS.md", "Independent fixture")
            before = archive.read_bytes()
            self.assertEqual(solve(archive), "test{independent_fixture}")
            self.assertEqual(before, archive.read_bytes())
            self.assertEqual(tuple(Path(directory).iterdir()), (archive,))

    def test_unexpected_archive_members_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "bad.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("../catalog.db", b"not a database")
            with self.assertRaisesRegex(ValueError, "members"):
                read_evidence(archive)


if __name__ == "__main__":
    unittest.main()
