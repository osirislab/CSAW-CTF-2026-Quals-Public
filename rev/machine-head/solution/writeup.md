# Machine Head — Writeup

**Flag:** `csaw{cl1mb1ng_th3_v1rtu4l_st4ck_0n3_0pc0d3_4t_4_t1m3}`

## Recon

`masterkey` reads `argv[1]`, checks its length, and prints
`Correct!`/`Wrong.`. In a disassembler `main` is tiny — it just calls a
`run()` function. `run()` is a single `switch` over bytes fetched from a
static array `program[]`. That's the tell: this is a **bytecode virtual
machine**. The x86 is only the interpreter; the real logic lives in
`program[]`.

## Step 1 — reverse the interpreter

The fetch–decode loop reads instructions of a **fixed 3-byte layout**:

```
[ opcode ][ operand a ][ operand b ]
```

`a` is always a register index (8 one-byte registers). `b` is an immediate,
an input index, or — for the two register-register ops — a second register
index. Recovering the `switch` cases gives the opcode semantics (the byte
values are scrambled so they mean nothing until you read the handlers):

| opcode | mnemonic        | effect                          |
|:------:|:----------------|:--------------------------------|
| `0x91` | `VLD  a, idx`   | `reg[a] = input[idx]`           |
| `0x7A` | `VXORI a, imm`  | `reg[a] ^= imm`                 |
| `0x24` | `VADDI a, imm`  | `reg[a] = (reg[a] + imm) & 0xff`|
| `0x1D` | `VMULI a, imm`  | `reg[a] = (reg[a] * imm) & 0xff`|
| `0xB2` | `VROL a, imm`   | `reg[a] = rol8(reg[a], imm & 7)`|
| `0x4E` | `VXORR a, b`    | `reg[a] ^= reg[b]`              |
| `0x6D` | `VADDR a, b`    | `reg[a] = (reg[a] + reg[b])`    |
| `0xA7` | `VCMP a, imm`   | `if reg[a] != imm: ok = 0`      |
| `0xE0` | `VHLT`          | return `ok`                     |

The two register-register ops (`VXORR`, `VADDR`) are the important addition:
they move data *between* registers, so the checker is no longer a pile of
independent immediate arithmetic.

## Step 2 — disassemble the bytecode

`program[]` opens with `VXORI r1, 0x3C` — that seeds a **running-state
register** `r1`. Then, per flag byte, twelve instructions:

```
; --- transform byte i into r0 ---
VLD   r0, i          ; load flag byte i
VXORI r0, K1         ; K1 = (0x5A + 0x27*i) & 0xff
VADDI r0, K2         ; K2 = (0x11 + 7*i)   & 0xff
VROL  r0, R          ; R  = (i % 7) + 1
VXORI r0, 0xC3
VMULI r0, 0x1B       ; 0x1B = 27
VXORR r0, r1         ; *** mix in the running state ***
VCMP  r0, T          ; T = embedded target for byte i
; --- fold byte i into the state for the next round ---
VLD   r2, i
VADDR r1, r2         ; r1 += input[i]
VROL  r1, 3
VXORI r1, 0x9E       ; r1 = rol8(r1 + input[i], 3) ^ 0x9E
```

`r1` is a hash of every byte accepted so far, and it is XORed into each
comparison. **This is what breaks the naive attack.** In the easy version
you could invert all 53 `VCMP` targets independently, in any order. Here the
target for byte `i` is `transform(byte_i) XOR state_i`, and `state_i`
depends on bytes `0..i-1`. You cannot solve byte 7 without first knowing
bytes 0–6.

## Step 3 — solve by emulating, left to right

Because the state chains forward, the clean approach is to emulate the VM and
recover the flag greedily:

1. Model all nine opcodes (including the register-register ones and the state
   fold).
2. Fix the prefix already recovered; for the next position try all 256
   byte values, run the VM, and keep the one whose `VCMP` for that position
   passes. The emulator carries `r1` forward for free.
3. Repeat to the end.

You *can* also do it analytically — invert the transform, but thread the
state through in order:

```
state = 0x3C
for i in range(n):
    t = T[i] ^ state
    t = (t * 19) & 0xff        # undo VMULI (19 = inverse of 27 mod 256)
    t ^= 0xC3
    t = ror8(t, (i % 7) + 1)   # undo VROL
    t = (t - ((0x11 + 7*i) & 0xff)) & 0xff   # undo VADDI
    t ^= (0x5A + 0x27*i) & 0xff              # undo VXORI (K1)
    c = t                       # recovered byte i
    state = rol8((state + c) & 0xff, 3) ^ 0x9e   # advance the chain
```

Either way, the order is forced.

## Solver

`solve.py` carves the bytecode out of the binary, builds a faithful emulator
of the scrambled opcode set, and recovers the flag one byte at a time:

```
$ python3 solve.py
[+] recovered 1914 bytes of bytecode (638 instructions, 53 comparisons)
FLAG: csaw{cl1mb1ng_th3_v1rtu4l_st4ck_0n3_0pc0d3_4t_4_t1m3}
```

## Regenerating

```
python3 generate.py    # emits vm_source.c and ../files/masterkey, self-checks
```

`vm_source.c` (the interpreter source) is included here for reference; only
the compiled, stripped `masterkey` binary is shipped to players. (Build needs
a Linux toolchain — `gcc` — e.g. native Linux or WSL.)
