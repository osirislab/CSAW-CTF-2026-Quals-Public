#!/usr/bin/env python3
"""
Secret Treaties - challenge generator.

A textbook Merkle-Hellman knapsack cryptosystem. The flag is split into
9-byte (72-bit) blocks; each block is encrypted as a subset sum over a
72-element public key. The blocks are large enough that brute force
(2**72 per block) is hopeless, but the knapsack density is low enough
(~0.75) that the Lagarias-Odlyzko / low-density lattice attack recovers
each subset with a single LLL reduction. No trapdoor needed.

Run:  python3 generate.py
Emits ../files/pubkey.txt and ../files/ciphertext.txt
"""
import random
import os
import sys

FLAG = b"csaw{LLL_turns_kn4ps4cks_1nt0_p4nc4k3s_wh3n_d3ns1ty_1s_l0w}"
# 9-byte (72-bit) blocks: too wide for brute force AND for a 2**(n/2)
# meet-in-the-middle (2**36 * storage), so recovery really does need LLL.
BLOCK = 9          # bytes per block  -> n = 72 bit positions
N = BLOCK * 8      # 72 knapsack elements

# Deterministic instance so the shipped files are reproducible.
SEED = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0xC0FFEE
rng = random.Random(SEED)


def gen_superincreasing(n):
    """Superincreasing sequence: each term exceeds the sum of all previous."""
    seq = []
    total = 0
    cur = rng.randrange(2 ** 9, 2 ** 10)      # start near 2**9
    for _ in range(n):
        seq.append(cur)
        total += cur
        # next term strictly greater than running sum, with a little slack
        cur = total + rng.randrange(2 ** 8, 2 ** 9) + 1
    return seq, total


def egcd(a, b):
    if b == 0:
        return (a, 1, 0)
    g, x, y = egcd(b, a % b)
    return (g, y, x - (a // b) * y)


def inv(a, m):
    g, x, _ = egcd(a % m, m)
    assert g == 1
    return x % m


def main():
    w, total = gen_superincreasing(N)

    # Modulus q > sum(w), but chosen much larger to keep the density low:
    #   density = N / log2(max(b_i)) ~= 72 / 96 ~= 0.75  (< 0.9408 threshold)
    q = (1 << 96) + rng.randrange(1 << 70)
    while True:
        r = rng.randrange(2, q)
        if egcd(r, q)[0] == 1:
            break

    # Public key: b_i = w_i * r mod q
    b = [(wi * r) % q for wi in w]

    # pad to a whole number of blocks with NUL (solver strips trailing NULs)
    flag = FLAG
    if len(flag) % BLOCK:
        flag = flag + b"\x00" * (BLOCK - len(flag) % BLOCK)

    ciphertexts = []
    for off in range(0, len(flag), BLOCK):
        block = flag[off:off + BLOCK]
        # bit vector, MSB-first per byte
        bits = []
        for byte in block:
            for k in range(7, -1, -1):
                bits.append((byte >> k) & 1)
        c = sum(bi * bit for bi, bit in zip(b, bits))
        ciphertexts.append(c)

    here = os.path.dirname(__file__)
    files = os.path.abspath(os.path.join(here, "..", "files"))
    os.makedirs(files, exist_ok=True)

    with open(os.path.join(files, "pubkey.txt"), "w") as f:
        f.write("# Merkle-Hellman public key (72 elements)\n")
        f.write("# Each flag block is 9 bytes = 72 bits (MSB-first per byte).\n")
        f.write("# ciphertext = sum of pubkey[i] for every set bit i.\n")
        for bi in b:
            f.write(f"{bi}\n")

    with open(os.path.join(files, "ciphertext.txt"), "w") as f:
        f.write("# one ciphertext per 9-byte block\n")
        for c in ciphertexts:
            f.write(f"{c}\n")

    # density report (for our own sanity, not shipped)
    import math
    density = N / math.log2(max(b))
    print(f"N={N}  q~2^{q.bit_length()}  density={density:.4f}")
    print(f"blocks={len(ciphertexts)}")
    print("wrote pubkey.txt, ciphertext.txt")


if __name__ == "__main__":
    main()
