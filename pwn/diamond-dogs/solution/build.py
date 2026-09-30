#!/usr/bin/env python3
"""
Diamond Dogs - challenge builder.

Compiles the K-9 manager as a **non-PIE** binary (fixed load address, so the
object layout and default handler are legible in a disassembler), pins the
exact glibc 2.31 runtime it is exploited against, and lays down the handout
in ../files.

glibc 2.31 rationale is the same as thermite-charge: tcache present, no
safe-linking, and __free_hook still exists -- but this challenge does not
need __free_hook. The win is a use-after-free that reclaims a released `dog`
object and overwrites its `bark` handler with `system`, so `command` calls
`system("/bin/sh")`.

Run inside the glibc-2.31 toolchain image:

    docker run --rm -v "$PWD/../../..":/work -w \
        /work/pwn/guard-dog/solution csaw-pwn-build python3 build.py
"""
import os
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))          # challenge root
FILES = os.path.join(ROOT, "files")                       # player handout
SRC = os.path.join(HERE, "guard-dog.c")
BIN = os.path.join(FILES, "guard-dog")

# Real flag lives at the challenge ROOT (deploy asset). files/ ships only a
# PLACEHOLDER so the whole handout folder is safe to distribute.
FLAG = "csaw{w3dd1ngs_4r3_b4s1c4lly_fun3r4ls_w1th_c4k3}"
PLACEHOLDER = "csaw{local_test_flag_not_the_real_one}"

LIBC_SRC = "/lib/x86_64-linux-gnu/libc-2.31.so"
LD_SRC = "/lib/x86_64-linux-gnu/ld-2.31.so"

HANDOUT_DOCKERFILE = """\
# Diamond Dogs - local reproduction image (glibc 2.31)
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y --no-install-recommends socat && \\
    rm -rf /var/lib/apt/lists/* && \\
    useradd -m ctf
WORKDIR /home/ctf
COPY guard-dog libc-2.31.so ld-2.31.so flag.txt ./
RUN chmod +x ./guard-dog ./ld-2.31.so && \\
    chown -R root:root /home/ctf && chmod 0644 flag.txt
USER ctf
EXPOSE 1025
CMD ["socat", "-T60", "TCP-LISTEN:1025,reuseaddr,fork", "EXEC:./guard-dog,stderr"]
"""

DEPLOY_DOCKERFILE = """\
# Diamond Dogs - DEPLOY image (glibc 2.31). Build from the challenge root:
#   docker build -f Dockerfile -t guard-dog .
# Do NOT ship this file or ../flag.txt to players.
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y --no-install-recommends socat && \\
    rm -rf /var/lib/apt/lists/* && \\
    useradd -m ctf
WORKDIR /home/ctf
COPY files/guard-dog files/libc-2.31.so files/ld-2.31.so ./
COPY flag.txt ./
RUN chmod +x ./guard-dog ./ld-2.31.so && \\
    chown -R root:root /home/ctf && chmod 0644 flag.txt
USER ctf
EXPOSE 1025
CMD ["socat", "-T60", "TCP-LISTEN:1025,reuseaddr,fork", "EXEC:./guard-dog,stderr"]
"""


def run(cmd):
    print("[*]", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    os.makedirs(FILES, exist_ok=True)

    # non-PIE so the binary's own addresses (object layout, default handler)
    # are fixed; libc is still ASLR'd, hence the leak step.
    run(["gcc", "-O1", "-fno-stack-protector", "-no-pie", "-fno-pie",
         "-o", BIN, SRC])

    shutil.copy(LIBC_SRC, os.path.join(FILES, "libc-2.31.so"))
    shutil.copy(LD_SRC, os.path.join(FILES, "ld-2.31.so"))
    run(["patchelf", "--set-interpreter", "./ld-2.31.so",
         "--set-rpath", ".", BIN])

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
