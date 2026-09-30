#!/usr/bin/env python3
"""
Secret Treaties - reference solver.

Breaks the Merkle-Hellman knapsack WITHOUT the private key using the
low-density subset-sum attack (Lagarias-Odlyzko with the Coster et al.
"CJLOSS" centring, which lifts the workable density up to ~0.9408).

For each ciphertext c and public key a[0..n-1] build the lattice (already
scaled x2 so every entry is an integer; W is a large weight that pins the
last coordinate to zero):

    row i  (0<=i<n) :  [ 0 .. 2 .. 0 | 2*W*a_i ]     (the 2 sits at column i)
    row n           :  [ 1  1 ..  1  | 2*W*c   ]

The target short vector is  row_n - sum_{bit_i=1} row_i : its last coord is
2*W*(c - sum a_i*bit_i) = 0 and its first n coords are 1-2*bit_i in {+1,-1}.
LLL surfaces it. Reading it back: coord +1 -> bit 0, coord -1 -> bit 1.

Exact integer LLL (Cohen, "A Course in Computational Algebraic Number
Theory", Alg. 2.6.3) -- all-integer, so no float precision limit and no
Fraction blow-up. Pure standard library; no sage / fpylll.

Run:  python3 solve.py
"""
import os
import random
from fractions import Fraction


# --------------------------- exact integer LLL ---------------------------
YNUM, YDEN = 99, 100   # LLL delta = 0.99

def lll_int(basis):
    """LLL-reduce a list of integer row-vectors in place-ish; returns rows."""
    b = [list(map(int, row)) for row in basis]
    n = len(b)

    def dot(u, v):
        return sum(x * y for x, y in zip(u, v))

    d = [0] * (n + 1)          # d[0..n]; d[i] = Gram determinant of b[0..i-1]
    d[0] = 1
    lam = [[0] * n for _ in range(n)]

    def RED(k, l):
        if 2 * abs(lam[k][l]) <= d[l + 1]:
            return
        q = round(Fraction(lam[k][l], d[l + 1]))
        b[k] = [x - q * y for x, y in zip(b[k], b[l])]
        lam[k][l] -= q * d[l + 1]
        for i in range(l):
            lam[k][i] -= q * lam[l][i]

    def SWAP(k):
        b[k], b[k - 1] = b[k - 1], b[k]
        for j in range(k - 1):
            lam[k][j], lam[k - 1][j] = lam[k - 1][j], lam[k][j]
        lm = lam[k][k - 1]
        B = (d[k - 1] * d[k + 1] + lm * lm) // d[k]
        for i in range(k + 1, kmax + 1):
            t = lam[i][k]
            lam[i][k] = (d[k + 1] * lam[i][k - 1] - lm * t) // d[k]
            lam[i][k - 1] = (B * t + lm * lam[i][k]) // d[k + 1]
        d[k] = B

    # init
    kmax = 0
    d[1] = dot(b[0], b[0])
    k = 1
    while k < n:
        # incremental Gram-Schmidt for row k
        if k > kmax:
            kmax = k
            for j in range(k + 1):
                u = dot(b[k], b[j])
                for i in range(j):
                    u = (d[i + 1] * u - lam[k][i] * lam[j][i]) // d[i]
                if j < k:
                    lam[k][j] = u
                else:
                    d[k + 1] = u
        # Lovasz test, integer form with y = YNUM/YDEN (0.99 -> stronger reduction)
        RED(k, k - 1)
        if YDEN * d[k + 1] * d[k - 1] < YNUM * d[k] * d[k] - YDEN * lam[k][k - 1] ** 2:
            SWAP(k)
            k = max(k - 1, 1)
        else:
            for l in range(k - 2, -1, -1):
                RED(k, l)
            k += 1
    return b


# ------------------------------ the attack ------------------------------
def build_lattice(pub, c, W=1 << 20):
    """CJLOSS lattice (already x2-scaled), W pins the last coordinate to 0."""
    n = len(pub)
    rows = []
    for i in range(n):
        row = [0] * (n + 1)
        row[i] = 2
        row[n] = 2 * W * pub[i]
        rows.append(row)
    rows.append([1] * n + [2 * W * c])
    return rows


def recover_from_basis(pub, c, reduced):
    """A reduced row is the answer iff its last coord is 0 and its first n
    coords are all +/-1 (map +1 -> bit 0, -1 -> bit 1) and the subset sum
    checks out.  Try each row and its negation."""
    n = len(pub)
    for row in reduced:
        for sign in (1, -1):
            if sign * row[n] != 0:
                continue
            bits = []
            ok = True
            for i in range(n):
                v = sign * row[i]
                if v == 1:
                    bits.append(0)
                elif v == -1:
                    bits.append(1)
                else:
                    ok = False
                    break
            if ok and sum(bit * a for bit, a in zip(bits, pub)) == c:
                return bits
    return None


def solve_block(pub, c, retries=40):
    """LLL doesn't always leave the target as a basis vector on the first
    ordering, so if the direct reduction misses it we re-reduce randomly
    shuffled copies of the same lattice (deterministic seeds -> reproducible)
    until the answer surfaces.  Density 0.75 makes success essentially
    certain within a handful of tries."""
    rows = build_lattice(pub, c)

    reduced = lll_int([r[:] for r in rows])
    got = recover_from_basis(pub, c, reduced)
    if got:
        return got

    for t in range(retries):
        rng = random.Random(t * 7 + 1)
        shuffled = [r[:] for r in rows]
        rng.shuffle(shuffled)
        reduced = lll_int(shuffled)
        got = recover_from_basis(pub, c, reduced)
        if got:
            return got
    return None


def bits_to_bytes(bits):
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for bit in bits[i:i + 8]:
            byte = (byte << 1) | bit
        out.append(byte)
    return bytes(out)


def read_ints(path):
    vals = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                vals.append(int(line))
    return vals


def main():
    here = os.path.dirname(__file__)
    files = os.path.abspath(os.path.join(here, "..", "files"))
    pub = read_ints(os.path.join(files, "pubkey.txt"))
    cts = read_ints(os.path.join(files, "ciphertext.txt"))

    flag = bytearray()
    for idx, c in enumerate(cts):
        bits = solve_block(pub, c)
        if bits is None:
            print(f"[!] block {idx} not recovered")
            return
        chunk = bits_to_bytes(bits)
        flag += chunk
        print(f"[+] block {idx}: {chunk!r}")

    print("\nFLAG:", flag.rstrip(b"\x00").decode())


if __name__ == "__main__":
    main()
