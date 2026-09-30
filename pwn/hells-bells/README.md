# Hells Bells

**Category:** Pwn
**Difficulty:** Hard
**Flag format:** `csaw{...}`

---

Our breaching team keeps its charges in a little inventory manager. Plant a
charge, rewire it, inspect it, defuse it when you're done. Standard issue.

The quartermaster swears the thing is safe — "you can't touch a charge once
it's defused." He's wrong about that, and about a few other things. Get a
shell on the box.

```
nc <host> 1024
```

## Files

- `thermite-charge` — the service binary (x86-64, dynamically linked).
- `libc-2.31.so`, `ld-2.31.so` — the exact runtime the remote uses. Run the
  binary against these so your offsets match.
- `Dockerfile` — how the service is deployed (glibc 2.31).

## Hint

A defused charge is still sitting right where you left it — the inventory
just stops admitting it exists. But it will still let you *rewire* and
*inspect* that slot. One of those leaks where the library lives; the other
lets you rewrite a pointer the allocator is about to trust.

Read the message before you write the address. There's a hook that runs
every time a charge is defused.
