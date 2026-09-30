#!/usr/bin/env python3
"""
Ghost in the Machine - reference solver (hardened challenge).

The naive "threshold every inter-packet gap" attack now fails, because the
capture is salted with decoy packets and the timing bits are XOR-keyed. The
honest path:

  1. Parse the pcap. For every packet pull three things: arrival time, the
     IP TTL, and the UDP source port.
  2. Filter to the REAL packets (TTL == 64); the decoys (TTL == 113) are
     interleaved noise and must be dropped before measuring gaps.
  3. Gaps between consecutive real packets -> bits (threshold at the midpoint
     of the two clusters), MSB-first per byte -> ciphertext bytes.
  4. Recover the XOR key: for flag byte j, the key byte is (src_port - 40000)
     of the packets in that byte's group. XOR it out.

Pure standard library: parses classic libpcap directly, no scapy/dpkt.

Run:  python3 solve.py [path-to-capture.pcap]
"""
import os
import struct
import sys

REAL_TTL = 64


def read_pcap(path):
    """Return a list of (timestamp, ttl, udp_src_port) for UDP/IPv4 frames."""
    with open(path, "rb") as f:
        data = f.read()
    magic = struct.unpack("<I", data[:4])[0]
    if magic in (0xA1B2C3C4, 0xA1B23C4D):
        endian, nano = "<", magic == 0xA1B23C4D
    elif magic in (0xD4C3B2A1, 0x4D3CB2A1):
        endian, nano = ">", magic == 0x4D3CB2A1
    else:
        raise ValueError("not a pcap file")

    off = 24
    out = []
    while off + 16 <= len(data):
        ts_sec, ts_frac, incl_len, orig_len = struct.unpack(
            endian + "IIII", data[off:off + 16])
        off += 16
        frame = data[off:off + incl_len]
        off += incl_len
        frac = ts_frac / 1e9 if nano else ts_frac / 1e6
        ts = ts_sec + frac
        # Ethernet(14) + IPv4(20) + UDP; TTL at IP+8, UDP src port at IP+20
        if len(frame) >= 36:
            ttl = frame[14 + 8]
            sport = struct.unpack("!H", frame[34:36])[0]
            out.append((ts, ttl, sport))
    return out


def main():
    here = os.path.dirname(__file__)
    default = os.path.abspath(os.path.join(here, "..", "files", "capture.pcap"))
    path = sys.argv[1] if len(sys.argv) > 1 else default

    pkts = read_pcap(path)
    real = sorted((p for p in pkts if p[1] == REAL_TTL), key=lambda p: p[0])
    print(f"[+] {len(pkts)} packets; {len(real)} real (TTL {REAL_TTL}), "
          f"{len(pkts) - len(real)} decoys dropped")

    times = [p[0] for p in real]
    sports = [p[2] for p in real]
    gaps = [b - a for a, b in zip(times, times[1:])]

    lo, hi = min(gaps), max(gaps)
    thresh = (lo + hi) / 2
    print(f"[+] {len(gaps)} gaps; min={lo*1000:.1f}ms max={hi*1000:.1f}ms "
          f"thresh={thresh*1000:.1f}ms")
    bits = [1 if g > thresh else 0 for g in gaps]

    # bits -> ciphertext bytes (MSB-first)
    cipher = bytearray()
    for i in range(0, len(bits) - len(bits) % 8, 8):
        byte = 0
        for b in bits[i:i + 8]:
            byte = (byte << 1) | b
        cipher.append(byte)

    # key byte for ciphertext byte j comes from the src port of a packet in
    # that byte's group (packets j*8 .. j*8+7). src_port = 40000 + key_byte.
    flag = bytearray()
    for j, c in enumerate(cipher):
        sp = sports[j * 8 + 1] if j * 8 + 1 < len(sports) else sports[j * 8]
        key_byte = (sp - 40000) & 0xFF
        flag.append(c ^ key_byte)

    print("FLAG:", flag.decode(errors="replace"))


if __name__ == "__main__":
    main()
