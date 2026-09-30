/* Autobahn - self-decrypting flag checker (hardened). */
#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <sys/mman.h>

/* The flag ciphertext (visible, but useless without the runtime keystream). */
static const unsigned char enc_flag[] = {
    0x06, 0x2f, 0xdb, 0x37, 0xa5, 0x06, 0xfe, 0x30, 0xa7, 0xc7, 0x96, 0x8f,
    0x83, 0x16, 0xe5, 0xc4, 0x5b, 0x4a, 0x78, 0xb1, 0x60, 0x62, 0xad, 0xfa,
    0xa1, 0x46, 0xae, 0xc1, 0x9a, 0x82, 0xa2, 0xf2, 0x3a, 0xc6, 0x78, 0x3d,
    0x06, 0x37, 0x80, 0x60, 0xb2, 0x9b, 0xca, 0xe2, 0xf9, 0xf5, 0xe4,
};
#define ENC_LEN 47

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
        unsigned char k = (unsigned char)(code[(i * 7 + 3) % L]
                                          + (unsigned char)(i * 5)
                                          + base);
        out[i] = (char)(enc_flag[i] ^ k);
    }
    out[ENC_LEN] = 0;

    printf("NITRO ENGAGED: %s\n", out);
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: %s <password>\n", argv[0]);
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
        __start_enccode[i] ^= smc_key[i % 8];

    secret_check(argv[1]);
    return 0;
}
