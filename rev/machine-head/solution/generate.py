#!/usr/bin/env python3
"""
Machine Head - challenge generator (hardened).

Builds a small register-based virtual machine (in C), hand-assembles a
bytecode program that validates the flag, embeds the per-byte target
constants, and compiles the whole thing into the shipped binary
`../files/masterkey`.

Hardening over the naive version:
  * The checker is NO LONGER a set of independent per-byte equations.
    A dedicated "state" register (r1) carries a running value that is
    updated from every accepted plaintext byte, and that state is mixed
    into each byte's comparison. So the i-th target depends on bytes
    0..i, not just byte i.
  * That kills the offline "invert 53 independent transforms in any
    order" shortcut. The solver must actually *emulate* the VM and carry
    the state forward, recovering the flag strictly left-to-right.
  * The register-to-register opcodes (VXORR / VADDR) force the reverser
    to model inter-register data flow, not just immediate arithmetic.

The player only receives the compiled, stripped binary.

Run (needs gcc, i.e. Linux/WSL):  python3 generate.py
"""
import os
import subprocess

FLAG = b"csaw{cl1mb1ng_th3_v1rtu4l_st4ck_0n3_0pc0d3_4t_4_t1m3}"

# --- opcode table (scrambled byte values so they don't map to anything obvious)
OP = {
    "VLD":   0x91,   # reg[a] = input[b]
    "VXORI": 0x7A,   # reg[a] ^= imm
    "VADDI": 0x24,   # reg[a] = (reg[a] + imm) & 0xff
    "VMULI": 0x1D,   # reg[a] = (reg[a] * imm) & 0xff
    "VROL":  0xB2,   # reg[a] = rol8(reg[a], imm & 7)
    "VXORR": 0x4E,   # reg[a] ^= reg[b]           (NEW: register-register)
    "VADDR": 0x6D,   # reg[a] = (reg[a] + reg[b]) & 0xff  (NEW)
    "VCMP":  0xA7,   # if reg[a] != imm: ok = 0
    "VHLT":  0xE0,   # stop
}

MUL = 0x1B          # 27, odd -> invertible mod 256 (inverse is 19)
XORC = 0xC3         # constant xored into every byte transform
STATE0 = 0x3C       # initial value of the running-state register r1
STATE_ROT = 3       # rotate applied when folding a byte into the state
STATE_XOR = 0x9E    # constant xored into the state each round

R_WORK = 0          # working register
R_STATE = 1         # running-state register (the chain)
R_TMP = 2           # scratch register for reloading the raw byte


def rol8(v, n):
    n &= 7
    return ((v << n) | (v >> (8 - n))) & 0xFF


def k1(i):
    return (0x5A + 0x27 * i) & 0xFF


def k2(i):
    return (0x11 + 7 * i) & 0xFF


def rot(i):
    return (i % 7) + 1


def byte_transform(c, i):
    """Per-byte transform BEFORE the running state is mixed in."""
    t = c
    t ^= k1(i)
    t = (t + k2(i)) & 0xFF
    t = rol8(t, rot(i))
    t ^= XORC
    t = (t * MUL) & 0xFF
    return t


def state_update(state, c):
    """How an accepted plaintext byte folds into the running state."""
    return rol8((state + c) & 0xFF, STATE_ROT) ^ STATE_XOR


def assemble():
    code = bytearray()
    # initialise the running state:  r1 = 0 ^ STATE0
    code += bytes([OP["VXORI"], R_STATE, STATE0])

    state = STATE0
    for i, c in enumerate(FLAG):
        # target = transform(byte) XOR current_state
        tgt = byte_transform(c, i) ^ state

        code += bytes([OP["VLD"],   R_WORK, i])          # r0 = input[i]
        code += bytes([OP["VXORI"], R_WORK, k1(i)])
        code += bytes([OP["VADDI"], R_WORK, k2(i)])
        code += bytes([OP["VROL"],  R_WORK, rot(i)])
        code += bytes([OP["VXORI"], R_WORK, XORC])
        code += bytes([OP["VMULI"], R_WORK, MUL])
        code += bytes([OP["VXORR"], R_WORK, R_STATE])    # mix in the chain
        code += bytes([OP["VCMP"],  R_WORK, tgt])

        # fold this byte into the running state for the next round
        code += bytes([OP["VLD"],   R_TMP, i])           # r2 = input[i]
        code += bytes([OP["VADDR"], R_STATE, R_TMP])     # r1 += r2
        code += bytes([OP["VROL"],  R_STATE, STATE_ROT])
        code += bytes([OP["VXORI"], R_STATE, STATE_XOR])

        state = state_update(state, c)

    code += bytes([OP["VHLT"], 0, 0])
    return bytes(code)


C_TEMPLATE = r"""/* Machine Head - custom bytecode VM. Ships as a stripped binary. */
#include <stdio.h>
#include <string.h>
#include <stdint.h>

static const unsigned char program[] = {
%s
};

#define FLAGLEN %d

static uint8_t rol8(uint8_t v, uint8_t n) {
    n &= 7;
    return (uint8_t)((v << n) | (v >> (8 - n)));
}

/* register VM: 8 one-byte registers, byte-addressed program, 3 bytes/insn.
 * Instruction layout:  [ op | a | b ]
 *   a is always a register index; b is an immediate, an input index, or
 *   (for the register-register ops) a second register index. */
static int run(const unsigned char *in) {
    uint8_t reg[8] = {0};
    int ok = 1;
    size_t pc = 0;
    for (;;) {
        unsigned char op = program[pc];
        unsigned char a  = program[pc + 1];
        unsigned char b  = program[pc + 2];
        pc += 3;
        switch (op) {
            case 0x91: reg[a] = in[b]; break;                     /* VLD   */
            case 0x7A: reg[a] ^= b; break;                        /* VXORI */
            case 0x24: reg[a] = (uint8_t)(reg[a] + b); break;     /* VADDI */
            case 0x1D: reg[a] = (uint8_t)(reg[a] * b); break;     /* VMULI */
            case 0xB2: reg[a] = rol8(reg[a], b); break;           /* VROL  */
            case 0x4E: reg[a] ^= reg[b]; break;                   /* VXORR */
            case 0x6D: reg[a] = (uint8_t)(reg[a] + reg[b]); break;/* VADDR */
            case 0xA7: if (reg[a] != b) ok = 0; break;            /* VCMP  */
            case 0xE0: return ok;                                 /* VHLT  */
            default:   return 0;
        }
    }
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %%s <flag>\n", argv[0]);
        return 2;
    }
    if (strlen(argv[1]) != FLAGLEN) {
        puts("Wrong.");
        return 1;
    }
    if (run((const unsigned char *)argv[1])) {
        puts("Correct! That's the master key.");
        return 0;
    }
    puts("Wrong.");
    return 1;
}
"""


def format_bytes(data):
    lines = []
    for i in range(0, len(data), 12):
        chunk = data[i:i + 12]
        lines.append("    " + ", ".join("0x%02x" % b for b in chunk) + ",")
    return "\n".join(lines)


def main():
    here = os.path.dirname(__file__)
    files = os.path.abspath(os.path.join(here, "..", "files"))
    os.makedirs(files, exist_ok=True)

    code = assemble()
    src = C_TEMPLATE % (format_bytes(code), len(FLAG))

    src_path = os.path.join(here, "vm_source.c")
    with open(src_path, "w") as f:
        f.write(src)

    binpath = os.path.join(files, "masterkey")
    subprocess.run(
        ["gcc", "-O2", "-s", "-o", binpath, src_path],
        check=True,
    )
    print(f"bytecode: {len(code)} bytes, flag len {len(FLAG)}")
    print(f"wrote {src_path}")
    print(f"wrote {binpath}")

    # self-check: the real flag must be accepted, a tampered one rejected
    r = subprocess.run([binpath, FLAG.decode()], capture_output=True, text=True)
    print("self-check (real):", r.stdout.strip())
    assert "Correct" in r.stdout, "generated binary rejects the real flag!"

    bad = FLAG[:-2] + b"X}"
    r2 = subprocess.run([binpath, bad.decode()], capture_output=True, text=True)
    assert "Correct" not in r2.stdout, "binary accepts a wrong flag!"
    print("self-check (wrong):", r2.stdout.strip())


if __name__ == "__main__":
    main()
