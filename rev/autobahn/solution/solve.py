#!/usr/bin/env python3
"""
Autobahn - static (no-execution) reference solver (hardened challenge).

The easy shortcut is gone: the flag keystream is no longer a tidy linear
function you can guess against `.rodata`. It is derived from the *decrypted*
bytes of the `enccode` section, so you must first reproduce the runtime
self-decryption before you can build the keystream.

Intended static path (this script):
  1. read `enccode` from the ELF and XOR it back with the SMC key
     (13 37 c0 de ba ad f0 0d) -> the real machine code + the password.
  2. derive the flag keystream from those decrypted bytes, exactly the way
     secret_check does at runtime:
         k[i] = (code[(i*7 + 3) % len] + i*5 + 0x6b) & 0xff
  3. `enc_flag` sits in `.rodata`; decrypt it with that keystream.

(You could also just run `./nitro n2o_boost` -- but the point is that the
static recovery now requires understanding the self-modification.)

Run:  python3 solve.py [path-to-nitro]     (needs readelf, i.e. Linux/WSL)
"""
import os
import re
import subprocess
import sys

SMC_KEY = bytes([0x13, 0x37, 0xC0, 0xDE, 0xBA, 0xAD, 0xF0, 0x0D])
KS_BASE = 0x6B
KS_STEP = 5
KS_A = 7
KS_B = 3


def section(binpath, name):
    out = subprocess.check_output(["readelf", "-S", "-W", binpath], text=True)
    for line in out.splitlines():
        line2 = re.sub(r"\[\s*\d+\]", "", line)
        p = line2.split()
        if p and p[0] == name:
            return int(p[3], 16), int(p[4], 16)   # offset, size
    raise RuntimeError(name + " not found")


def read_bytes(binpath, off, size):
    with open(binpath, "rb") as f:
        f.seek(off)
        return f.read(size)


def flag_keystream(code, n):
    L = len(code)
    return bytes(((code[(i * KS_A + KS_B) % L] + i * KS_STEP + KS_BASE) & 0xFF)
                 for i in range(n))


def main():
    here = os.path.dirname(__file__)
    default = os.path.abspath(os.path.join(here, "..", "files", "nitro"))
    binpath = sys.argv[1] if len(sys.argv) > 1 else default

    # (1) decrypt the SMC section -> the real code bytes.
    off, size = section(binpath, "enccode")
    enc = read_bytes(binpath, off, size)
    code = bytes(enc[i] ^ SMC_KEY[i % 8] for i in range(size))

    # password lives in the decrypted code as a run of `movb $imm, disp(%rbp)`
    # instructions (C6 45 <disp> <imm>); collect the immediates until NUL.
    pw = bytearray()
    i = 0
    while i < len(code) - 3:
        if code[i] == 0xC6 and code[i + 1] == 0x45:
            imm = code[i + 3]
            if imm == 0x00:
                break
            if 32 <= imm < 127:
                pw.append(imm)
                i += 4
                continue
        i += 1
    print("[+] password recovered from decrypted enccode:",
          pw.decode(errors="replace") if pw else "(disassemble the section)")

    # (2) keystream is derived from the decrypted code bytes.
    ro_off, ro_size = section(binpath, ".rodata")
    rodata = read_bytes(binpath, ro_off, ro_size)
    ks = flag_keystream(code, 64)

    # locate enc_flag by decrypting .rodata at every offset and matching csaw{
    flag = None
    for start in range(0, len(rodata) - 5):
        if bytes(rodata[start + j] ^ ks[j] for j in range(5)) == b"csaw{":
            out = bytearray()
            j = 0
            while start + j < len(rodata):
                c = rodata[start + j] ^ ks[j]
                out.append(c)
                if c == ord("}"):
                    break
                j += 1
            flag = bytes(out)
            break

    print("FLAG:", flag.decode() if flag else "(not found)")


if __name__ == "__main__":
    main()
