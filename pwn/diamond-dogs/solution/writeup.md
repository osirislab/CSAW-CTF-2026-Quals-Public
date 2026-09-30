# Diamond Dogs — writeup

**Flag:** `csaw{w3dd1ngs_4r3_b4s1c4lly_fun3r4ls_w1th_c4k3}`

## The object

```c
struct dog { char name[0x18]; void (*bark)(struct dog *); };  /* 0x20 -> chunk 0x30 */
```

`command` does `dog->bark(dog)` — it calls the handler with a pointer to the
object as the first argument. Crucially the **name comes first**, so that
pointer points at the name bytes.

## Vulnerabilities

- **`release` frees the dog but leaves `dogs[i]` dangling** → use-after-free
  (the slot can still be `command`ed).
- A **same-size `note` allocation** (`file note`) reclaims a freed dog chunk
  with fully attacker-controlled bytes.
- **`read note` on a freed note** is a read-after-free, used for the libc leak.

## Runtime

glibc **2.31** (shipped, binary `patchelf`ed to it), built **non-PIE** so the
object layout and the default `woof` handler are at fixed, legible addresses.
libc is still ASLR'd, so a leak is required. `__free_hook` exists but is *not*
needed here — the win is the object's own function pointer.

## Intended path

1. **libc leak.** File a note larger than the tcache ceiling (`0x500`) plus a
   small guard note; `shred` the big one → unsorted bin. `read note` on it
   leaks `main_arena + 0x60` → libc base. (`main_arena + 0x60 == __malloc_hook + 0x70`.)
2. **Reclaim + hijack.** `adopt` a dog (one `0x30` chunk), then `release` it →
   `tcache[0x30]`, slot still dangling. `file note` of the same size class
   reclaims that exact chunk, writing `name = "/bin/sh\0…"` and
   `bark = system`.
3. **Fire.** `command` the released dog: `bark(dog) == system(dog)`, and `dog`
   points at `"/bin/sh"` (name is at offset 0). Shell → `cat flag.txt`.

## Why this resists automated solving

There's no attack signature — it's a use-after-free whose exploitation is a
stateful heap groom. The solver must recognise the dangling object, reason
about the struct layout (why *name-before-handler* is what makes `system`'s
argument land on `"/bin/sh"`), obtain a libc leak *before* the overwrite, size
the reclaim into the right tcache bin, and order release → reclaim → command
precisely. A wrong order silently corrupts the heap instead of erroring — the
multi-round interactive feedback loop that agents struggle to close.

## Reproduce

```
docker run --rm -v "$REPO":/work -w /work/pwn/guard-dog/solution \
    csaw-pwn-build python3 build.py
python3 solve.py                       # local
REMOTE=host:1025 python3 solve.py      # remote service
```

## Deploy note (authors)

`build.py` writes a **placeholder** flag into `files/flag.txt` (the handout is
safe to distribute wholesale) and the **real** flag at the challenge root
`flag.txt`. Deploy with the root Dockerfile (build context = challenge root):

```
docker build -f Dockerfile -t guard-dog .          # from pwn/guard-dog/
```

Do **not** ship the root `Dockerfile` or root `flag.txt` to players — only the
`files/` folder.
