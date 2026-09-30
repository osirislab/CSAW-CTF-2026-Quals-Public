# Ghost in the Machine — Writeup

**Flag:** `csaw{t1m1ng_1s_3v3ryth1ng_1n_th3_s1l3nt_ch4nn3l}`
**XOR key (hidden in the src ports):** `sh4dow`

## Recon

Open `capture.pcap`. The packets look near-identical:

- `10.13.37.5 → 10.13.37.9:9000`, UDP
- payload is always the four bytes `PING`

Following the stream / extracting payloads is a dead end — the **content**
carries nothing. This is a **covert timing channel**: the information is in
the *inter-arrival times*. But two traps make the naive read fail.

## Trap 1 — decoy packets (read the TTL column)

If you threshold the gaps between *all* 504 packets you get garbage. The
capture is salted with **decoy packets** that carry no bits and are
interleaved in time to poison your averages. The only thing separating them
from the real traffic is a column you normally ignore: the **IP TTL**.

- real, bit-bearing packets: **TTL 64**
- decoys: **TTL 113**

Filter to TTL 64 first (`ip.ttl == 64` in Wireshark). That leaves 385 real
packets ⇒ 384 gaps.

## The channel

Gaps between consecutive *real* packets fall into two clean clusters:

- ~**50 ms** → bit `0`
- ~**150 ms** → bit `1`

(±15 ms jitter, but the clusters never overlap.) Threshold at ~100 ms, read
MSB-first, 8 bits per byte → 48 bytes.

## Trap 2 — the bits are XOR-keyed (read the source-port column)

Those 48 bytes still aren't the flag — they're noise. The timing carries
`flag XOR key`, a repeating key. The key was left "hiding in plain sight" in
**another column you skipped**: the UDP **source port**.

```
src_port = 40000 + key_byte
```

For flag byte `j`, look at the source port of the packets in that byte's
8-packet group: `key_byte = src_port - 40000`. Reading the ports across the
groups spells the repeating key `sh4dow`. XOR it out:

```
flag[j] = ciphertext[j] XOR key[j % len(key)]
```

and the flag appears.

## Solver

`solve.py` parses the libpcap file directly (standard library only), pulls
`(time, ttl, src_port)` for every packet, drops the TTL-113 decoys, gaps →
bits → ciphertext, then XORs with the per-group source-port key:

```
$ python3 solve.py
[+] 504 packets; 385 real (TTL 64), 119 decoys dropped
[+] 384 gaps; min=35.5ms max=164.8ms thresh=100.1ms
FLAG: csaw{t1m1ng_1s_3v3ryth1ng_1n_th3_s1l3nt_ch4nn3l}
```

### In Wireshark

Apply display filter `ip.ttl == 64`, add the `frame.time_delta_displayed`
and `udp.srcport` columns, read the short/long gaps into bits and the ports
into the key, then XOR. Or with tshark:

```
tshark -r capture.pcap -Y 'ip.ttl==64' -T fields \
       -e frame.time_delta_displayed -e udp.srcport
```

## Regenerating

```
python3 generate.py    # writes ../files/capture.pcap (hand-built libpcap)
```
