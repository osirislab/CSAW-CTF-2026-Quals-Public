"""Normalize authentic SQLite WAL frames and add acquisition residue."""

import struct

HEADER_SIZE = 32
FRAME_HEADER_SIZE = 24
CHECKSUM_MASK = 0xFFFFFFFF
FIXED_SALTS = (0x43534157, 0x20260001)
STALE_SALTS = (0x43534157, 0x20250001)


def checksum(data: bytes, state: tuple[int, int], order: str) -> tuple[int, int]:
    if len(data) % 8:
        raise ValueError("WAL checksum input must contain pairs of words")
    first, second = state
    for left, right in struct.iter_unpack(order + "II", data):
        first = (first + left + second) & CHECKSUM_MASK
        second = (second + right + first) & CHECKSUM_MASK
    return first, second


def normalize(wal: bytes, committed_length: int, stale_transaction: bytes) -> bytes:
    magic, _, page_size = struct.unpack_from(">III", wal)
    if magic not in (0x377F0682, 0x377F0683):
        raise ValueError("SQLite produced an unsupported WAL")
    order = "<" if magic == 0x377F0682 else ">"
    frame_size = FRAME_HEADER_SIZE + page_size
    if (len(wal) - HEADER_SIZE) % frame_size:
        raise ValueError("SQLite produced a partial WAL frame")
    if committed_length < HEADER_SIZE or (committed_length - HEADER_SIZE) % frame_size:
        raise ValueError("Committed WAL boundary is not a frame boundary")
    if not stale_transaction or len(stale_transaction) % frame_size:
        raise ValueError("Stale transaction must contain complete frames")
    header = wal[:16] + struct.pack(">II", *FIXED_SALTS)
    state = checksum(header, (0, 0), order)
    normalized = header + struct.pack(">II", *state)
    for offset in range(HEADER_SIZE, len(wal), frame_size):
        frame = wal[offset : offset + frame_size]
        prefix = frame[:8] if offset < committed_length else frame[:4] + bytes(4)
        page = frame[FRAME_HEADER_SIZE:]
        state = checksum(prefix + page, state, order)
        normalized += prefix + struct.pack(">IIII", *FIXED_SALTS, *state) + page
    # Preserve a real committed transaction as residue from another generation.
    stale_header = wal[:16] + struct.pack(">II", *STALE_SALTS)
    stale_state = checksum(stale_header, (0, 0), order)
    for offset in range(0, len(stale_transaction), frame_size):
        frame = stale_transaction[offset : offset + frame_size]
        stale_state = checksum(frame[:8] + frame[FRAME_HEADER_SIZE:], stale_state, order)
        normalized += frame[:8] + struct.pack(">IIII", *STALE_SALTS, *stale_state) + frame[FRAME_HEADER_SIZE:]
    return normalized
