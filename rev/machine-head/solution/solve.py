#!/usr/bin/env python3
"""
Machine Head - reference solver (hardened challenge).

The old shortcut -- "each byte is an independent invertible transform, so
invert all 53 of them in any order" -- is gone. A running-state register
(r1) is folded from every accepted byte and XORed into each comparison, so
the i-th target depends on bytes 0..i. There is exactly one consistent
left-to-right assignment, and to find it you must model the VM.

This solver does the honest thing:
  1. carve the embedded bytecode out of the binary,
  2. build a faithful emulator of the (scrambled) opcode set, including the
     register-register ops that move the state around,
  3. recover the flag one byte at a time, greedily: fix the prefix already
     found, try each value for the next byte, and keep the one whose VCMP
     passes -- the emulator carries the state forward automatically.

Run:  python3 solve.py [path-to-masterkey]
"""
import sys
import os

# scrambled opcode table (recovered by reversing the interpreter loop)
OP_VLD, OP_VXORI, OP_VADDI, OP_VMULI, OP_VROL, OP_VXORR, OP_VADDR, OP_VCMP, OP_VHLT = (
    0x91, 0x7A, 0x24, 0x1D, 0xB2, 0x4E, 0x6D, 0xA7, 0xE0
)
VALID = {OP_VLD, OP_VXORI, OP_VADDI, OP_VMULI, OP_VROL,
         OP_VXORR, OP_VADDR, OP_VCMP, OP_VHLT}


def rol8(v, n):
    n &= 7
    return ((v << n) | (v >> (8 - n))) & 0xFF


def extract_bytecode(blob):
    """Longest run of valid 3-byte instructions terminating in VHLT."""
    best = None
    n = len(blob)
    for i in range(n - 2):
        if blob[i] not in VALID:
            continue
        j = i
        ok = True
        while j < n - 2:
            op = blob[j]
            if op == OP_VHLT:
                j += 3
                break
            if op not in VALID:
                ok = False
                break
            j += 3
        else:
            ok = False
        if ok and j - 3 >= i and blob[j - 3] == OP_VHLT:
            run = blob[i:j]
            if best is None or len(run) > len(best):
                best = run
    if best is None:
        raise RuntimeError("could not locate bytecode")
    return best


def emulate(code, inp):
    """Run the VM. Returns the list of per-VCMP results (True/False)."""
    reg = [0] * 8
    cmps = []
    pc = 0
    while pc + 2 < len(code):
        op, a, b = code[pc], code[pc + 1], code[pc + 2]
        pc += 3
        if op == OP_VLD:
            reg[a] = inp[b] if b < len(inp) else 0
        elif op == OP_VXORI:
            reg[a] ^= b
        elif op == OP_VADDI:
            reg[a] = (reg[a] + b) & 0xFF
        elif op == OP_VMULI:
            reg[a] = (reg[a] * b) & 0xFF
        elif op == OP_VROL:
            reg[a] = rol8(reg[a], b)
        elif op == OP_VXORR:
            reg[a] ^= reg[b]
        elif op == OP_VADDR:
            reg[a] = (reg[a] + reg[b]) & 0xFF
        elif op == OP_VCMP:
            cmps.append(reg[a] == b)
        elif op == OP_VHLT:
            break
    return cmps


def main():
    here = os.path.dirname(__file__)
    default = os.path.abspath(os.path.join(here, "..", "files", "masterkey"))
    path = sys.argv[1] if len(sys.argv) > 1 else default
    with open(path, "rb") as f:
        blob = f.read()

    code = extract_bytecode(blob)
    ncmp = sum(1 for k in range(0, len(code), 3) if code[k] == OP_VCMP)
    print(f"[+] recovered {len(code)} bytes of bytecode "
          f"({len(code)//3} instructions, {ncmp} comparisons)")

    flag = bytearray()
    for i in range(ncmp):
        found = None
        for cand in range(256):
            trial = bytes(flag) + bytes([cand]) + b"\x00" * (ncmp - i - 1)
            cmps = emulate(code, trial)
            if len(cmps) > i and cmps[i]:
                # prefer printable, but accept the unique match
                found = cand
                if 32 <= cand < 127:
                    break
        if found is None:
            print(f"[!] byte {i} not recovered")
            return
        flag.append(found)

    print("FLAG:", flag.decode(errors="replace"))


if __name__ == "__main__":
    main()
