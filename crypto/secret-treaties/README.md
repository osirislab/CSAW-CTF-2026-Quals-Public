# Secret Treaties

**Category:** Crypto
**Difficulty:** Medium
**Flag format:** `csaw{...}`

---

We built a "quantum-resistant" public-key scheme from the good old
subset-sum problem. Subset-sum is NP-complete, so surely nobody can read
our messages without the private key... right?

We encrypted the flag nine bytes at a time. Each 72-bit block became a
single number: the sum of the public-key entries selected by that block's
bits.

Recover the flag.

## Files

- `pubkey.txt` — the 72-element public key (one integer per line).
- `ciphertext.txt` — one ciphertext per 9-byte block.

## Notes

- Bits are taken **MSB-first within each byte**: for public-key index `i`,
  bit `i` is set iff it contributes `pubkey[i]` to that block's ciphertext.
- Brute force is out (2⁷² per block), and so is meet-in-the-middle
  (≈2³⁶ time *and* memory). The intended path is much prettier.
