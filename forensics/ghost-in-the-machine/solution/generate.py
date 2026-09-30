#!/usr/bin/env python3
"""
Ghost in the Machine - challenge generator (hardened).

The message is still hidden in packet *timing* (the gap between consecutive
packets encodes one bit), but two extra layers defeat the push-button solve:

  1. DECOY PACKETS. The capture is salted with decoy packets that carry no
     bits. They are interleaved in time, so a solver that naively thresholds
     the gaps between *all* packets reads pure garbage. The decoys are
     distinguishable only by a field you normally ignore: their IP TTL.
     Real (bit-bearing) packets use TTL 64; decoys use TTL 113. You must
     filter to the real packets *first*, then read the gaps between them.

  2. XOR KEYSTREAM. Even after you recover the timing bits, they are the flag
     XORed with a repeating key -- so they still look like noise. The key
     byte for flag byte j is transmitted in the UDP *source port* of that
     byte's packets:  src_port = 40000 + key_byte. Another "column you
     usually ignore."

    short gap (~50 ms)  -> bit 0
    long  gap (~150 ms) -> bit 1        (MSB-first per byte)
    ciphertext[j] = flag[j] XOR key[j % len(key)]
    real packet TTL = 64, decoy TTL = 113
    real packet src port = 40000 + key[(pkt_index // 8) % len(key)]

The pcap is written by hand (classic libpcap format), no third-party deps.

Run:  python3 generate.py    (writes ../files/capture.pcap)
"""
import os
import random
import struct

FLAG = b"csaw{t1m1ng_1s_3v3ryth1ng_1n_th3_s1l3nt_ch4nn3l}"
KEY = b"sh4dow"                 # repeating XOR key, carried in the src ports

SHORT = 0.050     # seconds, bit 0
LONG = 0.150      # seconds, bit 1
JITTER = 0.015    # +/- uniform jitter (clusters stay separated by ~50ms)

REAL_TTL = 64
DECOY_TTL = 113
NDECOY = 119

rng = random.Random(1337)


def ip_checksum(header):
    s = 0
    for i in range(0, len(header), 2):
        s += (header[i] << 8) + header[i + 1]
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    return (~s) & 0xFFFF


def build_frame(ttl, src_port, payload=b"PING"):
    """One Ethernet/IPv4/UDP frame with the given TTL and UDP source port."""
    udp_len = 8 + len(payload)
    udp = struct.pack("!HHHH", src_port, 9000, udp_len, 0) + payload

    total_len = 20 + udp_len
    ihl_ver = 0x45
    tos = 0
    ident = 0x1337
    flags_frag = 0x4000            # DF
    proto = 17                     # UDP
    src = bytes([10, 13, 37, 5])
    dst = bytes([10, 13, 37, 9])
    ip_no_csum = struct.pack("!BBHHHBBH", ihl_ver, tos, total_len, ident,
                             flags_frag, ttl, proto, 0) + src + dst
    csum = ip_checksum(ip_no_csum)
    ip = struct.pack("!BBHHHBBH", ihl_ver, tos, total_len, ident,
                     flags_frag, ttl, proto, csum) + src + dst

    eth = (bytes.fromhex("deadbeef0002") + bytes.fromhex("deadbeef0001") +
           struct.pack("!H", 0x0800))
    return eth + ip + udp


def bits_of(data):
    for byte in data:
        for k in range(7, -1, -1):
            yield (byte >> k) & 1


def main():
    here = os.path.dirname(__file__)
    files = os.path.abspath(os.path.join(here, "..", "files"))
    os.makedirs(files, exist_ok=True)

    # ciphertext = flag XOR repeating key
    cipher = bytes(c ^ KEY[i % len(KEY)] for i, c in enumerate(FLAG))
    bits = list(bits_of(cipher))

    # --- real (bit-bearing) packets -------------------------------------
    t = 1700000000.0
    real = []   # (time, ttl, src_port)
    # first real packet (starts the stream; index 0)
    real.append((t, REAL_TTL, 40000 + KEY[0]))
    for i, bit in enumerate(bits):
        gap = (LONG if bit else SHORT) + rng.uniform(-JITTER, JITTER)
        t += gap
        pkt_index = i + 1                     # this packet closes bit i
        key_byte = KEY[(pkt_index // 8) % len(KEY)]
        real.append((t, REAL_TTL, 40000 + key_byte))

    real_times = [r[0] for r in real]

    # --- decoy packets: interleaved in time, TTL 113 --------------------
    decoys = []
    for _ in range(NDECOY):
        m = rng.randrange(len(real_times) - 1)
        lo, hi = real_times[m], real_times[m + 1]
        dt = lo + rng.uniform(0.30, 0.70) * (hi - lo)
        decoys.append((dt, DECOY_TTL, rng.randrange(50000, 51000)))

    packets = sorted(real + decoys, key=lambda p: p[0])

    out = os.path.join(files, "capture.pcap")
    with open(out, "wb") as f:
        f.write(struct.pack("<IHHiIII", 0xA1B2C3C4, 2, 4, 0, 0, 65535, 1))
        for ts, ttl, sport in packets:
            frame = build_frame(ttl, sport)
            sec = int(ts)
            usec = int(round((ts - sec) * 1_000_000))
            if usec >= 1_000_000:
                sec += 1
                usec -= 1_000_000
            f.write(struct.pack("<IIII", sec, usec, len(frame), len(frame)))
            f.write(frame)

    print(f"{len(packets)} packets total "
          f"({len(real)} real TTL64, {len(decoys)} decoy TTL113)")
    print(f"{len(FLAG)} flag bytes, {len(bits)} bits, key={KEY.decode()!r}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
