#!/usr/bin/env python3
"""
Autobahn - challenge builder (hardened).

Produces a binary whose flag-checking routine is *encrypted on disk*. The
routine `secret_check` is compiled into a dedicated ELF section `enccode`.
After compiling, this script XOR-encrypts exactly that section's bytes in
the file, so a static disassembler sees garbage instructions there.

At runtime `main()`:
  1. mprotect()s the page(s) holding `enccode` as RWX,
  2. XOR-decrypts the section back in place with the SMC key (this is the
     self-modification),
  3. only then calls `secret_check`.

Hardening over the naive version:
  * The flag is NOT recoverable by guessing a tidy linear keystream off
    `.rodata`. `secret_check` derives its keystream from the **bytes of the
    decrypted `enccode` section itself** — i.e. from the real machine code
    that only exists after the self-decryption has run.
  * So the shortcut "scan .rodata, try key = 0x6b + 7*i, look for csaw{" is
    dead. To recover the flag statically you must first reproduce the SMC
    decrypt, then reproduce the code-dependent keystream. Or just run it.

Run (needs gcc, i.e. Linux/WSL):  python3 build.py
"""
import os
import re
import struct
import subprocess

FLAG = b"csaw{c0d3_th4t_rewr1t3s_1ts3lf_c4nt_b3_tru5t3d}"
PASSWORD = b"n2o_boost"

# key used to XOR the whole `enccode` section on disk (the SMC key)
SMC_KEY = bytes([0x13, 0x37, 0xC0, 0xDE, 0xBA, 0xAD, 0xF0, 0x0D])

# flag keystream base constants (mixed with the decrypted code bytes)
KS_BASE = 0x6B
KS_STEP = 5
KS_A = 7
KS_B = 3


def flag_keystream(code, n):
    """Keystream derived from the *decrypted* enccode bytes `code`.
    Must match secret_check() byte-for-byte."""
    L = len(code)
    return bytes(((code[(i * KS_A + KS_B) % L] + i * KS_STEP + KS_BASE) & 0xFF)
                 for i in range(n))


C_SOURCE = r"""/* Autobahn - self-decrypting flag checker (hardened). */
#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <sys/mman.h>

/* The flag ciphertext (visible, but useless without the runtime keystream). */
static const unsigned char enc_flag[] = {
%(enc_flag)s
};
#define ENC_LEN %(enc_len)d

/* ld provides these for a section whose name is a C identifier. */
extern unsigned char __start_enccode[];
extern unsigned char __stop_enccode[];

/* --- lives in section `enccode`; shipped ENCRYPTED, decrypted at runtime --- */
__attribute__((noinline, used, section("enccode")))
void secret_check(const char *pw)
{
    /* expected password, assembled from code immediates */
    char exp[10];
    exp[0]='n'; exp[1]='2'; exp[2]='o'; exp[3]='_';
    exp[4]='b'; exp[5]='o'; exp[6]='o'; exp[7]='s'; exp[8]='t'; exp[9]=0;

    int i, ok = 1;
    for (i = 0; i < 9; i++)
        if (pw[i] != exp[i]) { ok = 0; break; }
    if (ok && pw[9] != 0) ok = 0;

    if (!ok) { puts("Access denied. The engine stays cold."); return; }

    /* Derive the keystream from the DECRYPTED code bytes of this very
     * section. By the time we run, __start_enccode..__stop_enccode holds
     * the real (decrypted) machine code, so `code` is exactly what the
     * builder hashed. A static guess of the keystream is impossible without
     * first decrypting this section. */
    const unsigned char *code = (const unsigned char *)__start_enccode;
    unsigned long L = (unsigned long)(__stop_enccode - __start_enccode);

    unsigned char base = 0x40 + 0x2B;   /* 0x6B, materialised in-code */
    char out[ENC_LEN + 1];
    for (i = 0; i < ENC_LEN; i++) {
        unsigned char k = (unsigned char)(code[(i * 7 + 3) %% L]
                                          + (unsigned char)(i * 5)
                                          + base);
        out[i] = (char)(enc_flag[i] ^ k);
    }
    out[ENC_LEN] = 0;

    printf("NITRO ENGAGED: %%s\n", out);
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: %%s <password>\n", argv[0]);
        return 2;
    }

    long ps = sysconf(_SC_PAGESIZE);
    uintptr_t start = (uintptr_t)__start_enccode;
    size_t len = (size_t)(__stop_enccode - __start_enccode);
    uintptr_t pbeg = start & ~((uintptr_t)ps - 1);
    size_t plen = (start + len) - pbeg;

    if (mprotect((void *)pbeg, plen,
                 PROT_READ | PROT_WRITE | PROT_EXEC) != 0) {
        perror("mprotect");
        return 3;
    }

    /* self-modification: decrypt the routine in place */
    static const unsigned char smc_key[8] =
        { 0x13, 0x37, 0xC0, 0xDE, 0xBA, 0xAD, 0xF0, 0x0D };
    for (size_t i = 0; i < len; i++)
        __start_enccode[i] ^= smc_key[i %% 8];

    secret_check(argv[1]);
    return 0;
}
"""


def fmt_bytes(data):
    lines = []
    for i in range(0, len(data), 12):
        lines.append("    " + ", ".join("0x%02x" % b for b in data[i:i + 12]) + ",")
    return "\n".join(lines)


def section_offset_size(binpath, name):
    out = subprocess.check_output(["readelf", "-S", "-W", binpath], text=True)
    for line in out.splitlines():
        line2 = re.sub(r"\[\s*\d+\]", "", line)
        parts = line2.split()
        if parts and parts[0] == name:
            addr = int(parts[2], 16)
            off = int(parts[3], 16)
            size = int(parts[4], 16)
            return off, size, addr
    raise RuntimeError(f"section {name} not found")


def read_section(binpath, off, size):
    with open(binpath, "rb") as f:
        f.seek(off)
        return f.read(size)


def compile_with(src_path, binpath, enc_flag):
    src = C_SOURCE % {"enc_flag": fmt_bytes(enc_flag), "enc_len": len(FLAG)}
    with open(src_path, "w") as f:
        f.write(src)
    subprocess.run(
        ["gcc", "-no-pie", "-O0", "-fno-stack-protector", "-o", binpath, src_path],
        check=True,
    )


def main():
    here = os.path.dirname(__file__)
    files = os.path.abspath(os.path.join(here, "..", "files"))
    os.makedirs(files, exist_ok=True)

    src_path = os.path.join(here, "nitro.c")
    binpath = os.path.join(files, "nitro")

    # Pass 1: compile with a placeholder ciphertext just to learn the compiled
    # (plaintext) bytes of `enccode`. Those bytes are what the runtime keystream
    # is derived from.
    compile_with(src_path, binpath, bytes(len(FLAG)))

    # Fixpoint: the keystream depends on enccode's plaintext bytes, and setting
    # enc_flag (which lives in .rodata, a different section) must not change
    # enccode. Iterate until stable -- in practice one extra compile.
    for _ in range(4):
        off, size, addr = section_offset_size(binpath, "enccode")
        code = read_section(binpath, off, size)
        ks = flag_keystream(code, len(FLAG))
        enc_flag = bytes(c ^ k for c, k in zip(FLAG, ks))
        compile_with(src_path, binpath, enc_flag)
        off2, size2, _ = section_offset_size(binpath, "enccode")
        code2 = read_section(binpath, off2, size2)
        if code2 == code:
            break
    else:
        raise RuntimeError("enccode bytes did not stabilise across recompiles")

    # NB: the freshly compiled binary is PLAINTEXT and must NOT be run --
    # main() always XORs the section, so it only produces valid code once the
    # section has been encrypted on disk (below).

    # now encrypt the `enccode` section in the file (the SMC payload)
    off, size, addr = section_offset_size(binpath, "enccode")
    with open(binpath, "rb") as f:
        data = bytearray(f.read())
    for i in range(size):
        data[off + i] ^= SMC_KEY[i % 8]
    with open(binpath, "wb") as f:
        f.write(data)
    os.chmod(binpath, 0o755)

    print(f"enccode: offset=0x{off:x} size={size} vaddr=0x{addr:x}")
    print(f"wrote {binpath}")

    # self-check on the SHIPPED (encrypted) binary
    good = subprocess.run([binpath, PASSWORD.decode()], capture_output=True, text=True)
    bad = subprocess.run([binpath, "wrongpass"], capture_output=True, text=True)
    print("correct-pw  :", good.stdout.strip())
    print("wrong-pw    :", bad.stdout.strip())
    assert FLAG.decode() in good.stdout, "shipped binary rejects correct password!"
    assert FLAG.decode() not in bad.stdout, "shipped binary leaks flag on wrong pw!"
    print("OK")


if __name__ == "__main__":
    main()
