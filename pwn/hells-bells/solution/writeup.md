# Hells Bells — writeup

**Flag:** `csaw{wh3n_y0u_r34ch_th3_cr0ssr04ds_d0nt_turn_l3ft}`

## Vulnerabilities

A menu-driven heap manager (`plant / defuse / rewire / inspect`) over an
array of `charges[16]` with parallel `sizes[16]`. Three deliberate flaws:

- **`defuse` (free) never nulls the slot pointer** — the reference stays live.
- **`rewire` (edit)** writes `sizes[idx]` bytes into `charges[idx]` with no
  check that the slot is still allocated → **edit-after-free**.
- **`inspect` (view)** `write(1, charges[idx], sizes[idx])` with the same
  missing check → **read-after-free**.

## Runtime

glibc **2.31** (shipped `libc-2.31.so` / `ld-2.31.so`, binary `patchelf`ed to
use them). This version is the crux:

- tcache is present, but **safe-linking does not exist yet** (added in 2.32),
  so a tcache `fd` is a raw pointer you can set directly.
- the tcache **double-free `key` check is present** (2.29+), so the intended
  primitive is an *edit-after-free fd overwrite*, not a lazy double-free.
- **`__free_hook` still exists** (removed in 2.34): overwrite it with `system`
  and `free` a chunk whose data is `"/bin/sh"`.

## Intended path

1. **libc leak.** Plant a chunk larger than the tcache ceiling (`0x500`,
   chunk size `0x510 > 0x410`) and a small guard chunk after it. `defuse`
   the big one — with the guard blocking consolidation into the top chunk it
   lands in the **unsorted bin**, so its `fd`/`bk` now point at
   `main_arena + 0x60`. `inspect` it → leak → libc base. (Offset derived from
   the exported `__malloc_hook` symbol: `main_arena + 0x60 == __malloc_hook + 0x70`.)
2. **tcache poison.** Plant two same-size chunks (`0x18`), `defuse` both →
   `tcache[0x20]: A → B`. `rewire` A, overwriting its `fd` with
   `&__free_hook`.
3. **Arbitrary write + fire.** Allocate twice from that bin: the first hands
   back A (fill it with `"/bin/sh"`), the second is returned **inside libc at
   `__free_hook`** — write `system` there. `defuse` the `"/bin/sh"` chunk →
   `__free_hook("/bin/sh") == system("/bin/sh")`. Shell → `cat flag.txt`.

## Why this resists automated solving

There is no signature to match — the win is an ordered, stateful heap groom.
A solver has to (a) recognise the three-way UAF, (b) get a libc leak *before*
the write and compute offsets against this specific libc, (c) size the tcache
bins correctly, and (d) sequence free → poison → alloc → alloc → free in
exactly the right order. Each step depends on live runtime feedback, and a
wrong ordering silently corrupts the heap rather than failing loudly — the
many-round interactive loop that agentic solvers struggle to close.

## Reproduce

Build the handout (inside the glibc-2.31 toolchain image):

```
docker run --rm -v "$REPO":/work -w /work/pwn/thermite-charge/solution \
    csaw-pwn-build python3 generate.py
```

Solve locally, or against the deployed service:

```
python3 solve.py                       # local process
REMOTE=host:1024 python3 solve.py      # remote service
```

## Deploy note (authors)

`generate.py` writes two flags: a **placeholder** in `files/flag.txt` (so the
whole `files/` handout is safe to distribute and players can reproduce
locally) and the **real** flag at the challenge root `flag.txt`. Deploy with
the root Dockerfile, whose build context is the challenge root:

```
docker build -f Dockerfile -t thermite-charge .   # from pwn/thermite-charge/
```

Do **not** ship the root `Dockerfile` or root `flag.txt` to players — only the
`files/` folder.
