# Machine Head

**Category:** Reverse Engineering
**Difficulty:** Hard
**Flag format:** `csaw{...}`

---

Every lock in the building answers to one key. We burned the checker into a
little machine of our own design — it speaks a language you won't find in
any disassembler's opcode table.

```
./masterkey <flag>
```

Give it the master key and it'll tell you.

## Files

- `masterkey` — a stripped Linux x86-64 binary.

## Hint

The x86 you see in your disassembler is just the *interpreter*. The program
it actually runs is data.

Each character isn't checked on its own — the machine keeps a running memory
of everything it has accepted so far, and mixes it into the next test. Read
the key from the front; there's only one order that works.
