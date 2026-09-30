"""Verify the public recorder contract and reject incomplete display inputs."""

import hashlib
from pathlib import Path
import sys
import unittest

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

sys.path = [str(Path(__file__).resolve().parents[1] / "solution"), *sys.path]
from recorder import DOMAIN, derive_key, seal, token


class RecorderTests(unittest.TestCase):
    def test_display_is_bytewise_xor_and_requires_complete_shares(self):
        north = bytes(range(32))
        south = bytes([255]) * 32
        self.assertEqual(token(north, south), bytes(range(255, 223, -1)))
        for pair in ((b"", south), (north, b""), (north + b"x", south)):
            with self.assertRaises(ValueError):
                token(*pair)

    def test_key_preserves_order_and_duplicates_from_iterable(self):
        first, second = bytes(range(32)), bytes(reversed(range(32)))
        expected = hashlib.sha256(DOMAIN + first + second + first).digest()
        self.assertEqual(derive_key(iter((first, second, first))), expected)
        self.assertNotEqual(derive_key((first, second)), expected)
        self.assertNotEqual(derive_key((second, first, first)), expected)
        with self.assertRaises(ValueError):
            derive_key((first, b"short"))

    def test_sealed_message_authenticates_with_the_public_contract(self):
        tokens = (bytes(range(32)),)
        nonce = bytes(range(12))
        envelope = seal(b"a message", tokens, nonce)
        self.assertEqual(set(envelope), {"version", "nonce", "ciphertext"})
        self.assertEqual(envelope["version"], 1)
        recovered = AESGCM(derive_key(tokens)).decrypt(
            bytes.fromhex(envelope["nonce"]),
            bytes.fromhex(envelope["ciphertext"]),
            DOMAIN,
        )
        self.assertEqual(recovered, b"a message")
        for invalid in (b"", bytes(11), bytes(13)):
            with self.assertRaises(ValueError):
                seal(b"a message", tokens, invalid)


if __name__ == "__main__":
    unittest.main()
