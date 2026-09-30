"""Validate the frozen handout and recovery with an independent SQLite reader."""

from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path = [str(ROOT / "solution"), *sys.path]

from generate import FLAG, PRIVATE_SEED, TRANSACTIONS, build, evidence, material


class GeneratorTests(unittest.TestCase):
    def test_reproducible_archive_and_distribution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = build(root / "first")
            second = build(root / "second")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(set(archive.namelist()), {
                    "catalog.db", "catalog.db-wal", "capsule.json",
                    "recorder.py", "OPERATIONS.md",
                })
                for entry in archive.infolist():
                    content = archive.read(entry)
                    self.assertNotIn(FLAG, content)
                    self.assertNotIn(PRIVATE_SEED, content)
                    self.assertEqual(entry.date_time, (2026, 1, 1, 0, 0, 0))
                    self.assertEqual(entry.external_attr >> 16, 0o100644)

    def test_sqlite_recovers_last_committed_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = build(root / "archive")
            database = root / "catalog.db"
            with zipfile.ZipFile(archive_path) as archive:
                database.write_bytes(archive.read("catalog.db"))
                database.with_name("catalog.db-wal").write_bytes(archive.read("catalog.db-wal"))
            with sqlite3.connect(database) as connection:
                self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone(), ("ok",))
                self.assertEqual(connection.execute("SELECT armed, label FROM control").fetchone(), (0, "standby"))
                self.assertEqual(connection.execute("SELECT share FROM north").fetchone(), (material(f"north-{TRANSACTIONS - 1}"),))

    def test_baseline_is_disarmed_and_tables_have_separate_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, _, _ = evidence(root / "source.db")
            database = root / "baseline.db"
            database.write_bytes(baseline)
            with sqlite3.connect(database) as connection:
                self.assertEqual(connection.execute("SELECT armed FROM control").fetchone(), (0,))
                pages = connection.execute("SELECT rootpage FROM sqlite_schema WHERE type='table'").fetchall()
                self.assertEqual(len(set(pages)), 4)
                self.assertEqual(connection.execute("SELECT share FROM north").fetchone(), (material("initial-north"),))

    def test_wal_has_commits_then_uncommitted_and_stale_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            _, wal, history = evidence(Path(directory) / "catalog.db")
        page_size = struct.unpack_from(">I", wal, 8)[0]
        frames = tuple(wal[offset:offset + 24 + page_size] for offset in range(32, len(wal), 24 + page_size))
        current = tuple(frame for frame in frames if frame[8:16] == wal[16:24])
        stale = frames[len(current):]
        self.assertEqual(sum(struct.unpack_from(">I", frame, 4)[0] > 0 for frame in current), TRANSACTIONS)
        self.assertTrue(all(frame[4:8] == bytes(4) for frame in current[-3:]))
        self.assertEqual(len(stale), 2)
        self.assertTrue(all(frame[8:16] != wal[16:24] for frame in stale))
        self.assertNotEqual(stale[-1][4:8], bytes(4))
        self.assertEqual(len(history), 20)
        self.assertLess(len(set(history)), len(history))


if __name__ == "__main__":
    unittest.main()
