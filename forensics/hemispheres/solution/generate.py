#!/usr/bin/env python3
"""
Hemispheres - challenge generator (hardened).

Still one file that is simultaneously a valid PNG image and a valid ZIP
archive (the two formats parse from opposite ends). But now the archive is
**password-protected**, and the password is not written anywhere in text --
it is hidden in the **least-significant bits of the image pixels**.

  * PNG is read front-to-back: signature, chunks, IEND. Trailing bytes after
    IEND are ignored by viewers.
  * ZIP is read back-to-front: the parser scans from EOF for the End of
    Central Directory record.
  * The picture therefore renders normally AND `unzip`/`binwalk` still find
    an archive -- but the archive is encrypted, so dumping it is not enough.
  * The decryption password is steganographically embedded in the blue
    channel's LSBs. You must read the pixels to open the lock.

So the trivial `binwalk -e` / `unzip` one-liner no longer yields the flag:
it yields an encrypted `flag.txt`. The solver has to (1) notice the polyglot,
(2) extract the LSB password from the image, (3) decrypt with it.

Uses the traditional (ZipCrypto) scheme so the standard-library `zipfile`
can read it back with a password. Pure stdlib + Pillow; no other deps.

Run:  python3 generate.py    (writes ../files/the_signal.png)
"""
import binascii
import io
import os
import random
import struct
import zlib

from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

FLAG = b"csaw{0n3_f1l3_tw0_truth5_p0lygl0t_m4g1c}"
# The steg-hidden archive password (never stored as text on disk).
PASSWORD = b"r3ad_b3tw33n_th3_p1x3ls"

SEED = 0x51643   # deterministic instance


# --------------------------- LSB steganography ---------------------------
def embed_lsb(img, secret):
    """Embed a 16-bit length header + `secret` bytes into the LSBs of the
    blue channel, pixel by pixel in row-major order."""
    px = img.load()
    W, H = img.size
    payload = struct.pack(">H", len(secret)) + secret
    bits = [(byte >> (7 - k)) & 1 for byte in payload for k in range(8)]
    if len(bits) > W * H:
        raise ValueError("image too small for payload")
    i = 0
    for y in range(H):
        for x in range(W):
            if i >= len(bits):
                return
            r, g, b = px[x, y]
            b = (b & ~1) | bits[i]
            px[x, y] = (r, g, b)
            i += 1


# ------------------------- traditional ZipCrypto -------------------------
_CRC = []
for _n in range(256):
    _c = _n
    for _ in range(8):
        _c = (0xEDB88320 ^ (_c >> 1)) if (_c & 1) else (_c >> 1)
    _CRC.append(_c & 0xFFFFFFFF)


def _crc32_upd(crc, b):
    return ((crc >> 8) ^ _CRC[(crc ^ b) & 0xFF]) & 0xFFFFFFFF


class _ZipCrypto:
    def __init__(self, pw):
        self.k0, self.k1, self.k2 = 0x12345678, 0x23456789, 0x34567890
        for ch in pw:
            self._upd(ch)

    def _upd(self, c):
        self.k0 = _crc32_upd(self.k0, c)
        self.k1 = (self.k1 + (self.k0 & 0xFF)) & 0xFFFFFFFF
        self.k1 = (self.k1 * 134775813 + 1) & 0xFFFFFFFF
        self.k2 = _crc32_upd(self.k2, (self.k1 >> 24) & 0xFF)

    def _stream(self):
        t = (self.k2 | 2) & 0xFFFF
        return ((t * (t ^ 1)) >> 8) & 0xFF

    def enc(self, data):
        out = bytearray()
        for p in data:
            out.append(p ^ self._stream())
            self._upd(p)
        return bytes(out)


def make_encrypted_zip(entries, password, seed=SEED):
    rng = random.Random(seed)
    pw = password if isinstance(password, bytes) else password.encode()
    out = bytearray()
    central = bytearray()
    for name, data in entries:
        nb = name.encode()
        crc = binascii.crc32(data) & 0xFFFFFFFF
        comp = zlib.compressobj(9, zlib.DEFLATED, -15)
        cd = comp.compress(data) + comp.flush()
        hdr = bytes(rng.randrange(256) for _ in range(11)) + bytes([(crc >> 24) & 0xFF])
        zc = _ZipCrypto(pw)
        enc = zc.enc(hdr) + zc.enc(cd)
        comp_size = len(enc)
        flags = 0x0001  # bit 0: encrypted
        lho = len(out)
        out += struct.pack("<IHHHHHIIIHH", 0x04034B50, 20, flags, 8, 0, 0,
                           crc, comp_size, len(data), len(nb), 0)
        out += nb + enc
        central += struct.pack("<IHHHHHHIIIHHHHHII", 0x02014B50, 20, 20, flags, 8,
                               0, 0, crc, comp_size, len(data), len(nb),
                               0, 0, 0, 0, 0, lho)
        central += nb
    cd_off = len(out)
    out += central
    out += struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, len(entries), len(entries),
                       len(central), cd_off, 0)
    return bytes(out)


# ------------------------------ the image -------------------------------
def make_png():
    import math
    W, H = 720, 400
    img = Image.new("RGB", (W, H), (16, 18, 28))
    d = ImageDraw.Draw(img)

    prev = None
    for x in range(0, W, 2):
        y = int(H / 2 + 60 * math.sin(x / 28.0) * math.exp(-((x - W / 2) ** 2) / 90000.0))
        if prev:
            d.line([prev, (x, y)], fill=(40, 90, 120), width=2)
        prev = (x, y)

    try:
        font_big = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 20)
    except Exception:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

    d.text((40, 40), "THE SIGNAL", fill=(230, 235, 245), font=font_big)
    d.text((40, 300), "one file. two truths. one locked.", fill=(150, 160, 180), font=font_small)
    d.text((40, 330), "the picture holds a key; the tail holds a lock.",
           fill=(90, 100, 120), font=font_small)

    # hide the archive password in the pixel LSBs
    embed_lsb(img, PASSWORD)

    meta = PngInfo()
    meta.add_text("Comment", "Look past IEND for the lock. The key is in the pixels, not the words.")
    meta.add_text("Software", "signal-station v2.0")

    buf = io.BytesIO()
    img.save(buf, format="PNG", pnginfo=meta, compress_level=6)
    return buf.getvalue()


def main():
    here = os.path.dirname(__file__)
    files = os.path.abspath(os.path.join(here, "..", "files"))
    os.makedirs(files, exist_ok=True)

    png = make_png()
    zip_bytes = make_encrypted_zip(
        [("flag.txt", FLAG + b"\n"),
         ("README.txt",
          b"You found the second truth AND the key. Nicely done.\n")],
        PASSWORD,
    )
    blob = png + zip_bytes

    out = os.path.join(files, "the_signal.png")
    with open(out, "wb") as f:
        f.write(blob)

    print(f"png={len(png)}B zip={len(zip_bytes)}B total={len(blob)}B")
    print(f"wrote {out}")

    # --- verify ALL interpretations ---
    import zipfile
    img = Image.open(out)
    img.load()
    print(f"[+] valid PNG: {img.format} {img.size}")

    # LSB password round-trips
    px = img.convert("RGB").load()
    W, H = img.size
    bits = []
    need = 16
    done = False
    for y in range(H):
        for x in range(W):
            bits.append(px[x, y][2] & 1)
            if len(bits) == 16 and need == 16:
                need = 16 + 8 * int("".join(map(str, bits)), 2)
            if need != 16 and len(bits) >= need:
                done = True
                break
        if done:
            break
    n = int("".join(map(str, bits[:16])), 2)
    recovered = bytes(int("".join(map(str, bits[16 + 8 * i:24 + 8 * i])), 2) for i in range(n))
    assert recovered == PASSWORD, f"LSB password mismatch: {recovered!r}"
    print(f"[+] LSB password: {recovered.decode()}")

    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        try:
            z.read("flag.txt")
            raise AssertionError("flag.txt readable without password!")
        except RuntimeError:
            pass
        got = z.read("flag.txt", pwd=PASSWORD).strip()
    print(f"[+] valid ENCRYPTED ZIP: entries={names}")
    assert got == FLAG, "zip does not contain the expected flag"
    print(f"[+] flag (with LSB password): {got.decode()}")


if __name__ == "__main__":
    main()
