import base64
import hashlib
import json
from pathlib import Path

from Crypto.Cipher import AES


ROOT = Path(__file__).resolve().parent.parent


def autokey_decrypt(ciphertext: str, primer: str) -> str:
    plaintext = []
    key = "".join(ch for ch in primer.upper() if ch.isalpha())
    for index, ch in enumerate(ciphertext):
        if index < len(key):
            shift = ord(key[index]) - 65
        else:
            shift = ord(plaintext[index - len(key)]) - 65
        plaintext.append(chr((ord(ch) - 65 - shift) % 26 + 65))
    return "".join(plaintext)


def undo_mirrored_trios(text: str) -> str:
    return "".join(text[index : index + 3][::-1] for index in range(0, len(text), 3))


def undo_mirrored_blocks(data: bytes, block_size: int) -> bytes:
    return b"".join(data[index : index + block_size][::-1] for index in range(0, len(data), block_size))


def undo_mirrored_quartets(text: str) -> str:
    return "".join(text[index : index + 4][::-1] for index in range(0, len(text), 4))


def xor_stream(data: bytes, material: bytes) -> bytes:
    output = bytearray()
    position = 0
    counter = 0
    while position < len(data):
        block = hashlib.sha256(material + counter.to_bytes(8, "big")).digest()
        chunk_size = min(32, len(data) - position)
        output.extend(x ^ y for x, y in zip(data[position : position + chunk_size], block[:chunk_size]))
        position += chunk_size
        counter += 1
    return bytes(output)


def main() -> None:
    stone = json.loads((ROOT / "data" / "stone.json").read_text())
    frost_blob = (ROOT / "data" / "frost.bin").read_bytes()
    iron = json.loads((ROOT / "data" / "iron.json").read_text())
    vault = json.loads((ROOT / "data" / "vault.json").read_text())

    # Stage 1: Granite
    stone_ciphertext = undo_mirrored_trios(stone["ciphertext"])
    stone_plaintext = autokey_decrypt(stone_ciphertext, "STONE")
    k1 = "GRANITE-71"
    print("[1] Granite plaintext:")
    print(stone_plaintext)
    print("[1] Granite submission marker:")
    print(k1)
    print()

    # Stage 2: Frost
    k1_bytes = k1.encode()
    frost_ciphertext = undo_mirrored_blocks(frost_blob, 8)
    frost_plaintext = xor_stream(frost_ciphertext, hashlib.sha256(k1_bytes).digest()).decode()
    k2 = "CRYO-29"
    print("[2] Frost plaintext:")
    print(frost_plaintext)
    print("[2] Frost submission marker:")
    print(k2)
    print()

    # Stage 3: Iron
    h0 = hashlib.sha256(k2.encode()).digest()
    h1 = hashlib.sha256(h0 + k1_bytes).digest()
    h2 = hashlib.sha256(h1[::-1] + k2.encode()).digest()
    iron_payload = base64.b64decode(undo_mirrored_quartets(iron["payload_b64"]))
    iron_plaintext = xor_stream(iron_payload, h2).decode()
    k3 = "FERRUM-83"
    print("[3] Iron plaintext:")
    print(iron_plaintext)
    print("[3] Iron submission marker:")
    print(k3)
    print()

    # Stage 4: Vault
    vault_key = hashlib.sha256(k1_bytes + b"|" + k2.encode() + b"|" + k3.encode()).digest()
    nonce = base64.b64decode(undo_mirrored_quartets(vault["nonce_b64"]))
    ciphertext_and_tag = base64.b64decode(undo_mirrored_quartets(vault["ciphertext_b64"]))
    ciphertext, tag = ciphertext_and_tag[:-16], ciphertext_and_tag[-16:]
    cipher = AES.new(vault_key, AES.MODE_GCM, nonce=nonce)
    cipher.update(vault["aad"].encode())
    vault_plaintext = cipher.decrypt_and_verify(ciphertext, tag).decode()
    print("[4] Vault flag:")
    print(vault_plaintext)


if __name__ == "__main__":
    main()