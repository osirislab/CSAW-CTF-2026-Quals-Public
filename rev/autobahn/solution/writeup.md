# Autobahn — Writeup

**Flag:** `csaw{c0d3_th4t_rewr1t3s_1ts3lf_c4nt_b3_tru5t3d}`
**Password:** `n2o_boost`

## The trap

Disassemble `secret_check` and you get garbage — invalid/nonsensical
instructions:

```
40130d <secret_check>:
  40130d: e0 38            loopne ...
  40130f: de 24 ef         fisubs ...
  ...
```

`strings` shows no flag and no password. That's because `secret_check`
lives in its own ELF section, **`enccode`**, which is stored **encrypted on
disk**. This is self-modifying code (SMC): the bytes you disassemble are
*not* the bytes that execute.

## Understanding `main`

`main` is normal, readable code. It does three things before calling
`secret_check`:

1. `mprotect()` the page(s) covering `[__start_enccode, __stop_enccode)` as
   `RWX`.
2. XOR every byte of that region with the repeating 8-byte key
   `13 37 c0 de ba ad f0 0d`. **This is the self-modification** — the
   process rewrites its own `.text` in place.
3. `call secret_check`.

So the real code appears only at runtime.

## Two ways to solve

### A. Dynamic — just let it decrypt itself

Run it under a debugger, break *after* the XOR loop in `main` (or on entry
to `secret_check`), and dump/disassemble the now-decrypted region. You'll
see the true function, including the password check and the flag decrypt.
Or, once you know the password, simply:

```
$ ./nitro n2o_boost
NITRO ENGAGED: csaw{c0d3_th4t_rewr1t3s_1ts3lf_c4nt_b3_tru5t3d}
```

### B. Static — reproduce the decryption yourself

No execution needed. Read the `enccode` section out of the ELF and XOR it
with the same key. Now it disassembles cleanly:

```
40130d <secret_check>:
  40130d: f3 0f 1e fa   endbr64
  40131d: c6 45 ed 6e   movb $0x6e,-0x13(%rbp)   ; 'n'
  401321: c6 45 ee 32   movb $0x32,-0x12(%rbp)   ; '2'
  401325: c6 45 ef 6f   movb $0x6f,-0x11(%rbp)   ; 'o'
  ...                                            ; -> "n2o_boost"
```

The password is assembled byte-by-byte from `movb` immediates (so it never
appears as a contiguous string). Reading them off gives `n2o_boost`.

The flag itself is decrypted *mid-run* from a ciphertext `enc_flag` sitting
in `.rodata`. **This is where the challenge bites.** The keystream is *not* a
tidy `0x6b + 7*i` you can guess against `.rodata` — it is derived from the
**decrypted bytes of `enccode` itself**:

```
L    = __stop_enccode - __start_enccode          ; size of the code section
k[i] = (code[(i*7 + 3) % L] + i*5 + 0x6b) & 0xff ; code = DECRYPTED enccode
flag[i] = enc_flag[i] ^ k[i]
```

So the naive attack — "scan `.rodata`, try `key = 0x6b + 7*i`, look for
`csaw{`" — fails: it never finds the flag, because the true key depends on
machine-code bytes that don't exist on disk. You must first reproduce the
SMC decrypt, *then* build the keystream from those bytes (or just run the
binary and let it do both).

## Solver

`solve.py` does the static route with no execution: decrypts `enccode`,
reads the password out of the `movb` immediates, derives the keystream from
the decrypted code bytes, and decrypts the flag ciphertext from `.rodata`:

```
$ python3 solve.py
[+] password recovered from decrypted enccode: n2o_boost
FLAG: csaw{c0d3_th4t_rewr1t3s_1ts3lf_c4nt_b3_tru5t3d}
```

## Regenerating

```
python3 build.py    # emits nitro.c, compiles, encrypts the enccode section,
                    # writes ../files/nitro, and self-checks the shipped binary
```

`nitro.c` (the plaintext source) is here for reference. Note the plaintext
compile output must never be run directly — `main` always XORs the section,
so it only yields valid code after the section is encrypted on disk.
