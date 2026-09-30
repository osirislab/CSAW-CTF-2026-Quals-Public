# Diamond Dogs

**Category:** Pwn
**Difficulty:** Medium–Hard
**Flag format:** `csaw{...}`

---

The K-9 unit runs a little manager: adopt a dog, give it a name, and issue a
command to make it bark. When a dog retires you release it back to the wild.
There's also a scratchpad for filing notes.

Trouble is, a released dog doesn't always stay gone. Get a shell.

```
nc <host> 1025
```

## Files

- `guard-dog` — the service binary (x86-64, non-PIE).
- `libc-2.31.so`, `ld-2.31.so` — the exact runtime the remote uses.
- `Dockerfile` — how the service is deployed (glibc 2.31).

## Hint

Every dog carries its own instructions for how to bark. Release one and the
kennel forgets it — but you can still *command* it. If you can get something
your own size back into that same spot before you give the order, you decide
what "bark" means.

The commander hands the dog a pointer to itself. Look closely at what sits at
the front of a dog. And you'll need to know where the library lives first — a
note that's too big to pocket has to be stored somewhere it can point back
home.
