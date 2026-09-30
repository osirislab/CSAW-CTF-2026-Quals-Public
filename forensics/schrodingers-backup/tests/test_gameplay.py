"""Ensure the evidence requires recovering observations, not pairing carved shares."""

from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path = [str(ROOT / "solution"), *sys.path]

from generate import FLAG, build
from solve import decrypt_capsule


@dataclass(frozen=True)
class Observation:
    pages: frozenset[int]
    armed: bool
    north: bytes
    south: bytes

    @property
    def token(self):
        return bytes(left ^ right for left, right in zip(self.north, self.south, strict=True))


@contextmanager
def database_connection(database):
    connection = sqlite3.connect(":memory:")
    try:
        connection.deserialize(database[:18] + b"\x01\x01" + database[20:])
        yield connection
    finally:
        connection.close()


def observe(database, changed=frozenset()):
    with database_connection(database) as connection:
        return Observation(
            changed,
            bool(connection.execute("SELECT armed FROM control WHERE id=1").fetchone()[0]),
            connection.execute("SELECT share FROM north WHERE id=1").fetchone()[0],
            connection.execute("SELECT share FROM south WHERE id=1").fetchone()[0],
        )


def frames(wal):
    page_size = struct.unpack_from(">I", wal, 8)[0]
    for offset in range(32, len(wal), page_size + 24):
        header = wal[offset:offset + 24]
        number, commit_size = struct.unpack_from(">II", header)
        yield number, commit_size, header[8:16], wal[offset + 24:offset + 24 + page_size]


def snapshots(database, wal, check_salts=True):
    """Independent page replay; deliberately omit checksums to test the shortcut."""
    page_size = struct.unpack_from(">I", wal, 8)[0]
    pages = tuple(database[offset:offset + page_size] for offset in range(0, len(database), page_size))
    changed = frozenset()
    observations = ()
    for number, commit_size, salts, image in frames(wal):
        if check_salts and salts != wal[16:24]:
            break
        pages = pages[:number - 1] + (image,) + pages[number:]
        changed = changed | {number}
        if commit_size:
            pages = pages[:commit_size]
            observations = observations + ((changed, b"".join(pages)),)
            changed = frozenset()
    return observations


def replay(database, wal, check_salts=True):
    return tuple(observe(image, changed) for changed, image in snapshots(database, wal, check_salts))


class GameplayTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        with zipfile.ZipFile(build(Path(temporary.name))) as archive:
            self.database = archive.read("catalog.db")
            self.wal = archive.read("catalog.db-wal")
            self.capsule = archive.read("capsule.json")
        with database_connection(self.database) as connection:
            self.roots = dict(connection.execute("SELECT name, rootpage FROM sqlite_schema WHERE type='table'"))
        self.initial = observe(self.database)
        self.observations = replay(self.database, self.wal)
        self.history = tuple(item.token for item in self.observations if item.armed)

    def assert_rejected(self, history):
        with self.assertRaisesRegex(ValueError, "authentication failed"):
            decrypt_capsule(self.capsule, tuple(history))

    def test_sparse_commits_and_first_observation_need_baseline(self):
        self.assertEqual(len(self.observations), 28)
        self.assertEqual(len(self.history), 20)
        self.assertEqual(decrypt_capsule(self.capsule, self.history), FLAG.decode())
        for table in ("north", "south"):
            self.assertTrue(any(
                item.armed and item.pages == {self.roots[table]}
                for item in self.observations
            ), f"No armed {table}-only commit")
        first_armed = next(index for index, item in enumerate(self.observations) if item.armed)
        changed = frozenset().union(*(item.pages for item in self.observations[:first_armed + 1]))
        untouched = {self.roots["north"], self.roots["south"]} - changed
        self.assertEqual(len(untouched), 1, "First observation must depend on one untouched baseline share")
        first = self.observations[first_armed]
        if self.roots["north"] in untouched:
            self.assertEqual(first.north, self.initial.north)
        else:
            self.assertEqual(first.south, self.initial.south)

    def test_silent_maintenance_visits_are_required(self):
        self.assertIn("maintenance", self.roots)
        maintenance = self.roots["maintenance"]
        previous = (self.initial,) + self.observations[:-1]
        silent = tuple(
            current for before, current in zip(previous, self.observations, strict=True)
            if current.armed and current.pages == {maintenance}
            and (current.north, current.south, current.armed) == (before.north, before.south, before.armed)
        )
        self.assertEqual(len(silent), 4)
        self.assert_rejected(item.token for item in self.observations if item.armed and item.pages != {maintenance})

    def test_same_token_rerandomization_and_control_only_rearm(self):
        pairs = tuple(zip((self.initial,) + self.observations[:-1], self.observations, strict=True))
        share_pages = {self.roots["north"], self.roots["south"]}
        self.assertTrue(any(
            before.armed and after.armed and before.token == after.token
            and before.north != after.north and before.south != after.south
            and share_pages <= after.pages
            for before, after in pairs
        ), "No armed same-token share rerandomization")
        self.assertTrue(any(
            not before.armed and after.armed and after.pages == {self.roots["control"]}
            and (before.north, before.south) == (after.north, after.south)
            for before, after in pairs
        ), "No control-only rearm of unchanged display")

    def test_every_prefix_of_south_page_carver_fails(self):
        armed = False
        north = self.initial.north
        candidates = ()
        for number, _, _, image in frames(self.wal):
            if number == self.roots["control"]:
                armed = b"recording" in image
            if number == self.roots["north"]:
                north = image[-32:]
            if number == self.roots["south"] and armed:
                candidates = candidates + (bytes(left ^ right for left, right in zip(north, image[-32:], strict=True)),)
        for length in range(len(candidates) + 1):
            with self.subTest(prefix_length=length):
                self.assert_rejected(candidates[:length])

    def test_every_commit_matches_native_sqlite_for_all_tables(self):
        page_size = struct.unpack_from(">I", self.wal, 8)[0]
        boundaries = ()
        for index, (_, commit_size, salts, _) in enumerate(frames(self.wal)):
            if salts != self.wal[16:24]:
                break
            if commit_size:
                boundaries = boundaries + (32 + (index + 1) * (24 + page_size),)
        expected = snapshots(self.database, self.wal)
        self.assertEqual(len(boundaries), 28)
        tables = ("control", "north", "south", "maintenance")
        self.assertEqual(set(self.roots), set(tables))
        with tempfile.TemporaryDirectory() as temporary:
            for index, (boundary, (_, snapshot)) in enumerate(zip(boundaries, expected, strict=True)):
                with self.subTest(commit=index):
                    database = Path(temporary) / f"commit-{index}.db"
                    database.write_bytes(self.database)
                    database.with_name(database.name + "-wal").write_bytes(self.wal[:boundary])
                    with closing(sqlite3.connect(database)) as native, database_connection(snapshot) as reconstructed:
                        for table in tables:
                            statement = f"SELECT * FROM {table} ORDER BY id"
                            self.assertEqual(native.execute(statement).fetchall(), reconstructed.execute(statement).fetchall())

    def test_changed_display_only_history_fails(self):
        changed_only = tuple(
            token for index, token in enumerate(self.history)
            if index == 0 or token != self.history[index - 1]
        )
        self.assertLess(len(changed_only), len(self.history))
        self.assert_rejected(changed_only)

    def test_stale_commits_change_unvalidated_replay(self):
        stale = tuple(frame for frame in frames(self.wal) if frame[2] != self.wal[16:24])
        self.assertTrue(any(commit_size for _, commit_size, _, _ in stale), "Old-generation residue has no commit")
        unsafe = replay(self.database, self.wal, check_salts=False)
        self.assertGreater(len(unsafe), len(self.observations))
        self.assertTrue(any(item.armed for item in unsafe[len(self.observations):]))
        self.assert_rejected(item.token for item in unsafe if item.armed)


if __name__ == "__main__":
    unittest.main()
