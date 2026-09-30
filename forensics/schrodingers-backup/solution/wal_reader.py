"""Read transaction-consistent SQLite WAL snapshots without modifying evidence."""

import struct
from collections.abc import Iterator

MAX_DATABASE_BYTES = 8 * 1024 * 1024
MAX_WAL_BYTES = 32 * 1024 * 1024
MAX_REPLAY_BYTES = 256 * 1024 * 1024
WAL_VERSION = 3007000
WAL_HEADER_BYTES = 32
FRAME_HEADER_BYTES = 24


def checksum(data: bytes, byteorder: str, seed: tuple[int, int] = (0, 0)) -> tuple[int, int]:
    """SQLite rolling checksum; stored checksums themselves are always big endian."""
    if byteorder not in ("little", "big") or len(data) % 8:
        raise ValueError("Invalid checksum input")
    first, second = seed
    for offset in range(0, len(data), 8):
        left = int.from_bytes(data[offset:offset + 4], byteorder)
        right = int.from_bytes(data[offset + 4:offset + 8], byteorder)
        first = (first + left + second) & 0xFFFFFFFF
        second = (second + right + first) & 0xFFFFFFFF
    return first, second


def database_page_size(database: bytes) -> int:
    if not 100 <= len(database) <= MAX_DATABASE_BYTES:
        raise ValueError("Database size is outside the supported bounds")
    if database[:16] != b"SQLite format 3\0":
        raise ValueError("Invalid SQLite database header")
    encoded = int.from_bytes(database[16:18], "big")
    size = 65536 if encoded == 1 else encoded
    if size < 512 or size > 65536 or size & (size - 1):
        raise ValueError("Invalid SQLite page size")
    if len(database) % size:
        raise ValueError("Truncated SQLite database page")
    return size


def _wal_header(wal: bytes, page_size: int) -> tuple[str, bytes, tuple[int, int]]:
    if not WAL_HEADER_BYTES <= len(wal) <= MAX_WAL_BYTES:
        raise ValueError("WAL size is outside the supported bounds")
    magic, version, size = struct.unpack(">III", wal[:12])
    if magic not in (0x377F0682, 0x377F0683):
        raise ValueError("Invalid WAL magic")
    if version != WAL_VERSION:
        raise ValueError("Unsupported WAL format version")
    if size != page_size:
        raise ValueError("WAL and database page sizes differ")
    byteorder = "little" if magic == 0x377F0682 else "big"
    seed = checksum(wal[:24], byteorder)
    if seed != struct.unpack(">II", wal[24:32]):
        raise ValueError("Invalid WAL header checksum")
    return byteorder, wal[16:24], seed


def committed_snapshots(database: bytes, wal: bytes) -> Iterator[bytes]:
    """Yield every commit in order; stop at the first invalid or incomplete frame."""
    page_size = database_page_size(database)
    byteorder, salts, seed = _wal_header(wal, page_size)
    pages = tuple(database[i:i + page_size] for i in range(0, len(database), page_size))
    pending: dict[int, bytes] = {}
    replay_bytes = 0
    frame_size = FRAME_HEADER_BYTES + page_size
    for offset in range(WAL_HEADER_BYTES, len(wal) - frame_size + 1, frame_size):
        header = wal[offset:offset + FRAME_HEADER_BYTES]
        page_number, commit_size = struct.unpack(">II", header[:8])
        image = wal[offset + FRAME_HEADER_BYTES:offset + frame_size]
        if header[8:16] != salts:
            break
        computed = checksum(header[:8] + image, byteorder, seed)
        if computed != struct.unpack(">II", header[16:24]):
            break
        if not 1 <= page_number <= MAX_DATABASE_BYTES // page_size:
            raise ValueError("WAL page number is outside the supported bounds")
        if commit_size > MAX_DATABASE_BYTES // page_size:
            raise ValueError("WAL commit size is outside the supported bounds")
        seed = computed
        pending = {**pending, page_number: image}
        if commit_size:
            replay_bytes = replay_bytes + commit_size * page_size
            if replay_bytes > MAX_REPLAY_BYTES:
                raise ValueError("WAL history exceeds the supported replay budget")
            available = {**dict(enumerate(pages, 1)), **pending}
            if any(number not in available for number in range(1, commit_size + 1)):
                raise ValueError("WAL commit contains missing database pages")
            pages = tuple(available[number] for number in range(1, commit_size + 1))
            pending = {}
            yield b"".join(pages)
