# Secret Treaties — Writeup

**Flag:** `csaw{LLL_turns_kn4ps4cks_1nt0_p4nc4k3s_wh3n_d3ns1ty_1s_l0w}`

## What it is

This is a **Merkle–Hellman knapsack** cryptosystem. The public key is a set
of 72 integers `a[0..71]`. Each 9-byte (72-bit) flag block is encoded as a
bit vector `x ∈ {0,1}⁷²` and encrypted as the subset sum

```
c = Σ a[i]·x[i]
```

The private trapdoor (a superincreasing sequence `w`, a modulus `q`, and a
multiplier `r` with `a[i] = w[i]·r mod q`) is **not** given. You don't need
it.

## Why the obvious attacks fail

- **Brute force:** 2⁷² subsets per block. No.
- **Meet-in-the-middle:** the standard subset-sum MITM runs in ≈2^(n/2) =
  2³⁶ time *and* 2³⁶ memory. That's why the block size is 72 bits and not
  64 — MITM is deliberately out of reach.

## The intended attack: low-density subset-sum via LLL

The **density** of the knapsack is

```
d = n / log2(max a[i]) = 72 / 96 ≈ 0.75
```

When `d < 0.9408`, the Lagarias–Odlyzko attack — with the Coster–Joux–
LaMacchia–Odlyzko–Schnorr ("CJLOSS") centring improvement — recovers the
0/1 solution from a **single lattice reduction**. This instance sits
comfortably under that threshold, so it's designed to fall.

### The lattice

For each ciphertext `c`, build this `(n+1) × (n+1)` basis (shown already
scaled by 2 so every entry is an integer; `W` is a large weight):

```
row i  (0 ≤ i < n):   [ 0 … 2 … 0 | 2·W·a[i] ]      (the 2 is at column i)
row n            :    [ 1  1 …  1 | 2·W·c    ]
```

Consider the integer combination `row_n − Σ_{x[i]=1} row_i`:

- **Last coordinate:** `2·W·(c − Σ a[i]·x[i]) = 0` exactly when `x` is the
  right subset. The large weight `W` makes any vector that *doesn't* zero
  this coordinate long, so LLL avoids them.
- **First n coordinates:** `1 − 2·x[i] ∈ {+1, −1}`. So the whole vector has
  norm `√n` — very short.

LLL surfaces this short vector. Read it back: coordinate `+1 → bit 0`,
coordinate `−1 → bit 1` (also check the negation of each row).

### Reading the bits back

```
x[i] = 0  if coord == +1
x[i] = 1  if coord == -1
```

Reassemble bits MSB-first into bytes, drop the trailing NUL padding of the
last block, and you have the flag.

## Running it

```
python3 solve.py       # reads ../files/pubkey.txt and ../files/ciphertext.txt
```

`solve.py` ships a self-contained **exact integer LLL** (Cohen, *A Course
in Computational Algebraic Number Theory*, Alg. 2.6.3) at δ=0.99, so it
needs only the Python standard library — no `sage`, no `fpylll`. All 7
blocks fall in ~1.5 s.

> Real-world solvers would just do `from fpylll import LLL` or use Sage's
> `Matrix(ZZ, ...).LLL()`. The hand-rolled version is here so the writeup is
> reproducible on a bare Python install.

### A note on robustness (re-reduction)

LLL returns a *reduced* basis, but it does not guarantee the shortest
vector is one of the basis rows for a given input ordering — occasionally
the CJLOSS target ends up split across rows and the direct read-back
misses it. The reduction itself is correct (the bundled integer LLL was
verified to produce properly size-reduced, Lovász-satisfying,
unimodular-equivalent bases at both δ=0.75 and δ=0.99). The fix is the
standard one: if the first reduction doesn't surface the answer, re-reduce
a **randomly shuffled copy** of the same lattice and try again. At density
0.75 the answer appears within a handful of tries, so the solver recovers
**any** instance — no cherry-picked parameters required.

## Regenerating the challenge

```
python3 generate.py            # default seed 0xC0FFEE; rewrites ../files/*.txt
python3 generate.py <seed>     # any seed works; the solver is seed-agnostic
```

The instance is *not* hand-picked to be easy — the solver's randomized
re-reduction solves arbitrary seeds at δ=0.99 (verified across many).
