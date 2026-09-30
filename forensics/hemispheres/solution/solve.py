#!/usr/bin/env python3
"""
Hemispheres - reference solver (hardened challenge).

The file is a PNG with a ZIP glued on the end, but the archive is
password-protected, and the password is hidden in the image's pixel LSBs.

Steps:
  1. It's a polyglot: `zipfile` scans from EOF and finds the archive inside
     the .png. But `flag.txt` is encrypted -- dumping it is not enough.
  2. Recover the password from the least-significant bit of the blue channel:
     a 16-bit big-endian length header followed by that many bytes.
  3. Decrypt `flag.txt` with the recovered password.

Run:  python3 solve.py [path-to-the_signal.png]
"""
import os
import struct
import sys
import zipfile

from PIL import Image


def extract_lsb_password(path):
    img = Image.open(path).convert("RGB")
    W, H = img.size
    px = img.load()
    bits = []
    n_bytes = None
    for y in range(H):
        for x in range(W):
            bits.append(px[x, y][2] & 1)
            if n_bytes is None and len(bits) == 16:
                n_bytes = struct.unpack(">H", _bits_to_bytes(bits[:16]))[0]
            if n_bytes is not None and len(bits) >= 16 + 8 * n_bytes:
                return _bits_to_bytes(bits[16:16 + 8 * n_bytes])
    raise RuntimeError("could not read LSB payload")


def _bits_to_bytes(bits):
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for b in bits[i:i + 8]:
            byte = (byte << 1) | b
        out.append(byte)
    return bytes(out)


def main():
    here = os.path.dirname(__file__)
    default = os.path.abspath(os.path.join(here, "..", "files", "the_signal.png"))
    path = sys.argv[1] if len(sys.argv) > 1 else default

    with open(path, "rb") as f:
        head = f.read(8)
    print("[+] PNG signature present:", head == b"\x89PNG\r\n\x1a\n")

    pw = extract_lsb_password(path)
    print("[+] LSB password recovered:", pw.decode(errors="replace"))

    with zipfile.ZipFile(path) as z:
        print("[+] archive entries:", z.namelist())
        flag = z.read("flag.txt", pwd=pw).decode().strip()
    print("FLAG:", flag)


if __name__ == "__main__":
    main()
