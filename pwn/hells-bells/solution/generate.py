#!/usr/bin/env python3
"""
Hells Bells - challenge generator.

Compiles the heap note manager, pins the exact glibc 2.31 runtime that the
challenge is exploited against, and lays down the player handout in
../files.

Why glibc 2.31 specifically:
  * tcache is present, but there is NO safe-linking (added in 2.32), so a
    poisoned tcache `fd` is a raw pointer -- the intended primitive.
  * the tcache double-free `key` check IS present (2.29+), which is why the
    challenge feeds you an *edit-after-free* to overwrite a freed chunk's
    fd, rather than a lazy double-free.
  * __free_hook still exists (removed in 2.34), giving a clean one-shot win
    target: overwrite it with `system` and free a chunk holding "/bin/sh".

The player only receives what lands in ../files (binary + pinned loader +
libc + Dockerfile). Run inside the glibc-2.31 toolchain image, e.g.:

    docker run --rm -v "$PWD/../../..":/work -w \
        /work/pwn/thermite-charge/solution csaw-pwn-build python3 generate.py
"""
import os
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))          # challenge root
FILES = os.path.join(ROOT, "files")                       # player handout
SRC = os.path.join(HERE, "thermite-charge.c")
BIN = os.path.join(FILES, "thermite-charge")

# Real flag lives at the challenge ROOT (deploy asset). The handout in files/
# ships only a PLACEHOLDER so the whole files/ folder is safe to distribute.
FLAG = "csaw{wh3n_y0u_r34ch_th3_cr0ssr04ds_d0nt_turn_l3ft}"
PLACEHOLDER = "csaw{local_test_flag_not_the_real_one}"

LIBC_SRC = "/lib/x86_64-linux-gnu/libc-2.31.so"
LD_SRC = "/lib/x86_64-linux-gnu/ld-2.31.so"

# Player-local image (lives in files/, ships with the placeholder flag so
# players can reproduce the environment end-to-end).
HANDOUT_DOCKERFILE = """\
# Hells Bells - local reproduction image (glibc 2.31)
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y --no-install-recommends socat && \\
    rm -rf /var/lib/apt/lists/* && \\
    useradd -m ctf
WORKDIR /home/ctf
COPY thermite-charge libc-2.31.so ld-2.31.so flag.txt ./
RUN chmod +x ./thermite-charge ./ld-2.31.so && \\
    chown -R root:root /home/ctf && chmod 0644 flag.txt
USER ctf
EXPOSE 1024
CMD ["socat", "-T60", "TCP-LISTEN:1024,reuseaddr,fork", "EXEC:./thermite-charge,stderr"]
"""

# Deploy image (lives at challenge ROOT; build context is the root so it can
# pull the binary from files/ and the REAL flag from the root).
DEPLOY_DOCKERFILE = """\
# Hells Bells - DEPLOY image (glibc 2.31). Build from the challenge root:
#   docker build -f Dockerfile -t thermite-charge .
# Do NOT ship this file or ../flag.txt to players.
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y --no-install-recommends socat && \\
    rm -rf /var/lib/apt/lists/* && \\
    useradd -m ctf
WORKDIR /home/ctf
COPY files/thermite-charge files/libc-2.31.so files/ld-2.31.so ./
COPY flag.txt ./
RUN chmod +x ./thermite-charge ./ld-2.31.so && \\
    chown -R root:root /home/ctf && chmod 0644 flag.txt
USER ctf
EXPOSE 1024
CMD ["socat", "-T60", "TCP-LISTEN:1024,reuseaddr,fork", "EXEC:./thermite-charge,stderr"]
"""


def run(cmd):
    print("[*]", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    os.makedirs(FILES, exist_ok=True)

    # 1) compile (PIE + NX + full RELRO defaults; no stack protector needed)
    run(["gcc", "-O1", "-fno-stack-protector", "-o", BIN, SRC])

    # 2) pin the runtime: ship this exact loader + libc and bind to them
    shutil.copy(LIBC_SRC, os.path.join(FILES, "libc-2.31.so"))
    shutil.copy(LD_SRC, os.path.join(FILES, "ld-2.31.so"))
    run(["patchelf", "--set-interpreter", "./ld-2.31.so",
         "--set-rpath", ".", BIN])

    # 3) flags + service definitions
    with open(os.path.join(FILES, "flag.txt"), "w") as f:      # placeholder (handout)
        f.write(PLACEHOLDER + "\n")
    with open(os.path.join(FILES, "Dockerfile"), "w") as f:    # player-local image
        f.write(HANDOUT_DOCKERFILE)
    with open(os.path.join(ROOT, "flag.txt"), "w") as f:       # REAL flag (deploy)
        f.write(FLAG + "\n")
    with open(os.path.join(ROOT, "Dockerfile"), "w") as f:     # deploy image
        f.write(DEPLOY_DOCKERFILE)

    print("[+] handout written to", FILES, "(placeholder flag)")
    print("[+] deploy flag + Dockerfile at", ROOT)
    print("[+] real flag:", FLAG)


if __name__ == "__main__":
    main()
