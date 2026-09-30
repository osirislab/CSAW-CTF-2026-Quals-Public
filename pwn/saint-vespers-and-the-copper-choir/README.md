# Saint Vespers and the Copper Choir

**Category:** pwn
**Difficulty:** Hard

> A cathedral machine hums beneath the chapel floor, preserving "holy"
> recordings in copper coils and replaying them on command. The service keeps
> choir entries, archives transcripts, and renders hymns from stored fragments,
> but a bug in the restoration path leaves a dangling object behind.

A heap challenge for glibc 2.35 (Ubuntu 22.04) with **all mitigations on**:
PIE, Full RELRO, NX, stack canaries, and tcache safe-linking.

---

## Player-facing description

The Copper Choir keeps up to 8 choristers. Each chorister has a name, a hymn
style (a fixed callback), and a raw "transcript" buffer. You can recruit them,
retire them to the archive, restore them from the archive, rewrite their
transcript or name, print their transcript, view the ledger, and finally begin
the **Final Performance**, during which every active chorister sings via its
stored callback.

Connect with:

```
nc <host> <port>
```

Handout contains: `vespers` (the binary), `libc.so.6` + `ld-2.35.so` (the exact
runtime), and `vespers.c` (source).

---

## The bug

`op_retire()` frees both the chorister struct **and** its transcript buffer, but
never clears the slot pointer:

```c
if (c->transcript) free(c->transcript);
free(c);
c->active = 0;             /* slot pointer left dangling */
```

`op_restore()` then flips the slot back to `active = 1` **without reallocating
anything**. Every operation that follows on a restored seat — recite, rename,
inscribe, or the Final Performance — touches freed memory. That is a reusable
**use-after-free**, and (by retiring twice) a **double-free** as well.

## Intended solve path

1. **libc leak.** Recruit a chorister with a large transcript (`> 0x408` bytes)
   so freeing it lands in the unsorted bin. Retire + restore that seat, then
   *recite* it: the UAF read prints the unsorted-bin `fd`, which points into
   `main_arena` inside libc.

2. **heap leak.** Retire a small chorister and read its freed **struct** back
   through the ledger (`op_roster` prints archived seats too). Because `name`
   sits at offset 0 of the struct, the bytes you read are the tcache
   safe-linking value `mangled(NULL) == chunk_addr >> 12` — i.e. the heap base.

3. **tcache poison.** `op_rename` writes straight into offset 0 of a freed
   struct — exactly the freed chunk's `fd`. Overwrite it (safe-linking-aware)
   to point the `0x60` tcache bin at a still-live chorister struct. A second,
   never-poisoned struct is parked in the same bin first so the tcache **count**
   stays non-zero through the poisoned allocation.

4. **overwrite the callback.** Recruit once more. The struct allocation reclaims
   the parked chunk; the following transcript allocation (`0x49` request → same
   `0x60` bin) lands **on the live chorister's own memory**. Write
   `"/bin/sh\0"` over its `name` (offset 0) and `&system` over its `sing`
   pointer.

5. **fire.** Begin the Final Performance. The engine calls `sing(self)`, which is
   now `system(self)` and `self` still reads `"/bin/sh"` → shell.

See [`solve/solve.py`](solve/solve.py) for the full, commented chain.

## Why the mitigations matter

- **Full RELRO** rules out the usual GOT overwrite; you must hijack the heap
  `sing` callback instead.
- **PIE** means no static gadget/`win()` to jump to — nothing useful is baked in
  (`strings` shows no `/bin/sh`, `system`, or flag path), so the **libc leak is
  mandatory**.
- **Safe-linking** forces you to understand `ptr ^ (addr >> 12)`; the heap leak
  and the poison both go through it.
- **Canaries + NX** keep the intended primitive on the heap, not the stack.

---

## Building & running

Everything is driven from the `Makefile` and the `build/` directory.

```bash
make            # build dist/vespers (patched to the shipped ld/libc)
make handout    # produce the player archive (never includes the flag)
make docker     # build the container image
make run        # build + serve locally on :5000
make test       # run solve/solve.py against a fresh local instance
```

Or directly with Docker Compose:

```bash
cd build && docker compose up --build
```

The service is a `socat` TCP forwarder to the binary (see
[`build/Dockerfile`](build/Dockerfile)), running as an unprivileged user with the
flag readable only via the popped shell.

## Testing the solve

```bash
# local binary
python3 solve/solve.py

# remote instance
python3 solve/solve.py <host> <port>
```

The solve script leaks libc + heap, poisons tcache, hijacks the callback, and
drops to an interactive shell; `cat flag.txt` from there.

## Directory layout

```
saint-vespers-and-the-copper-choir/
├── Makefile
├── README.md
├── src/
│   └── vespers.c              # challenge source
├── dist/
│   ├── vespers                # release binary (stripped, patched to ld-2.35)
│   ├── libc.so.6              # Ubuntu 22.04 glibc 2.35
│   └── ld-2.35.so             # matching loader
├── solve/
│   └── solve.py               # reference exploit (local + remote)
└── build/
    ├── Dockerfile             # builds + serves the challenge
    ├── docker-compose.yml
    ├── build_and_run.sh
    └── flag.txt               # the real flag (do NOT ship to players)
```

## Notes for organizers / testers

- The offsets in `solve.py` (`UNSORTED_DELTA`, `system`) are tied to the shipped
  `dist/libc.so.6`. The Docker image compiles against the identical
  Ubuntu 22.04 glibc, so the same offsets hold on the remote.
- Reliability: the allocation sequence is deterministic; the reference exploit
  succeeded 15/15 locally and 10/10 over TCP across randomized ASLR.
- There is a single intended flag path (heap UAF → callback hijack). The
  double-free is an alternate route to the *same* tcache-poison primitive, not
  an easier bypass — it still requires both leaks and the safe-linking work.
```
