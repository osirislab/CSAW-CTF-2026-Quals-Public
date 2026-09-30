"""Museum capsule recorder, retained with the acquisition for compatibility."""

import hashlib
from collections.abc import Iterable

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

DOMAIN = b"csaw-2026/schrodingers-backup/v1\x00"
SHARE_SIZE = 32


def token(north: bytes, south: bytes) -> bytes:
    if len(north) != SHARE_SIZE or len(south) != SHARE_SIZE:
        raise ValueError("Display shares must each contain 32 bytes")
    return bytes(left ^ right for left, right in zip(north, south))


def derive_key(tokens: Iterable[bytes]) -> bytes:
    history = tuple(tokens)
    if any(len(item) != SHARE_SIZE for item in history):
        raise ValueError("Every recorded token must contain 32 bytes")
    return hashlib.sha256(DOMAIN + b"".join(history)).digest()


def seal(message: bytes, tokens: Iterable[bytes], nonce: bytes) -> dict:
    if len(nonce) != 12:
        raise ValueError("Capsule nonce must contain 12 bytes")
    ciphertext = AESGCM(derive_key(tokens)).encrypt(nonce, message, DOMAIN)
    return {"version": 1, "nonce": nonce.hex(), "ciphertext": ciphertext.hex()}
