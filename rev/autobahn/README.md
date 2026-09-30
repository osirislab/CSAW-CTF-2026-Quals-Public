# Autobahn

**Category:** Reverse Engineering
**Difficulty:** Hard
**Flag format:** `csaw{...}`

---

Our engine only fires with the right password. We built it tough: pop it
open in a disassembler and the important part is pure noise. It only makes
sense once the engine is running.

```
./nitro <password>
```

## Files

- `nitro` — a Linux x86-64 binary (non-PIE).

## Hint

`objdump` shows you the code *at rest*. This engine rewrites itself the
moment it starts.

And the key that unlocks the flag isn't a constant you can read off — the
engine grinds it out of its own running code. Guessing the keystream won't
work; you have to let the rewrite happen first (or reproduce it exactly).
