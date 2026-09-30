#!/usr/bin/env python3
"""
Station service - represents one field station on its own fixed, offset clock.
Trusts the load balancer for UA/pacing enforcement; only handles the token
check and (post-auth) the manager directory/notes and station-4 relay.
"""
import base64
import hashlib
import os
import time
from datetime import datetime
from urllib.parse import unquote

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ---- station identity / clock config (env-driven) ----
STATION_ID = os.environ.get("STATION_ID", "st-01")
TARGET_TIME = os.environ.get("TARGET_TIME", "2018-07-12T04:00:00-04:00")
WINDOW_SECONDS = int(os.environ.get("WINDOW_SECONDS", "5"))
IS_RELAY_STATION = os.environ.get("IS_RELAY_STATION", "false").lower() == "true"
ADMIN_RELAY_HOST = os.environ.get("ADMIN_RELAY_HOST", "10.10.14.31")
RELAY_KEY = os.environ.get("RELAY_KEY", "4f9a-77c2-e01d")
DEBUG_SEPARATOR = os.environ.get("DEBUG_SEPARATOR", " ")  # literal character, after URL-decoding

# IMPORTANT: we do NOT call time.time() again after startup to compute "now".
# Docker Desktop's VM clock is known to jump (not just drift by a fixed amount)
# during periodic host resync - if sync_epoch() called time.time() fresh on
# every request, two closely-spaced requests (a probe and the guess that
# follows moments later) could see a wall-clock jump between them large enough
# to fall outside the +-WINDOW_SECONDS tolerance, causing correct tokens to be
# rejected. Instead: anchor wall-clock time ONCE at boot, then advance using
# time.monotonic(), which the OS guarantees never jumps or gets adjusted by
# time sync - only wall-clock time is ever subject to that.
_target_epoch = datetime.fromisoformat(TARGET_TIME).timestamp()
_boot_wall_time = time.time()
_boot_monotonic = time.monotonic()
OFFSET_SECONDS = int(_target_epoch - _boot_wall_time)


def sync_epoch() -> int:
    elapsed_since_boot = time.monotonic() - _boot_monotonic
    return int(_boot_wall_time + OFFSET_SECONDS + elapsed_since_boot)


def sync_time_iso() -> str:
    return datetime.utcfromtimestamp(sync_epoch()).strftime("%Y-%m-%dT%H:%M:%SZ")


def valid_token(token: str, sid: str) -> bool:
    """Two valid identity sources, both non-secret and both legitimately
    known to the player at the point they'd use them:
      - sid: their own session cookie, known from the very first heartbeat,
             before station_id has ever been revealed (first auth)
      - STATION_ID: revealed in every successful auth response, used for
             every action after that point (ls/cat/v1 api/chat/relay)
    Checking both is safe since neither is a secret - the real boundary
    enforced here is TIME (the +-WINDOW_SECONDS live clock match), not
    the identity string's secrecy.
    """
    now = sync_epoch()
    identities = [STATION_ID]
    if sid:
        identities.append(sid)
    for t in range(now - WINDOW_SECONDS, now + WINDOW_SECONDS + 1):
        for identity in identities:
            candidate = hashlib.md5(f"{identity}{t}".encode()).hexdigest()
            if candidate == token:
                return True
    return False


# ---- virtual filesystem (post-auth only) ----
def xor_encrypt(plaintext: str, key: str) -> str:
    raw = plaintext.encode()
    kb = key.encode()
    out = bytes(b ^ kb[i % len(kb)] for i, b in enumerate(raw))
    return base64.b64encode(out).decode()


VFS = {
    "": ["station.log", "config/"],
    "config": ["sync.conf", "relay-bot.js", "relay_chat.js"],
    ".logs": ["err_3005.log"],  # deliberately NOT referenced from root listing above 
                                 # only reachable if you already know the exact path
}

FILES = {
    "station.log": (
        f"[{STATION_ID}] routine check-in ok\n"
        f"[{STATION_ID}] heartbeat nominal\n"
        f"[{STATION_ID}] disk usage 34%\n"
        f"[{STATION_ID}] cron: backup job completed\n"
        f"[{STATION_ID}] WARN: stale handler dump written to .logs/err_3005.log\n"
        f"[{STATION_ID}] heartbeat nominal\n"
    ),
    "config/sync.conf": (
        "chat bridge auth: Authorization: Bot <token>\n"
        "token=md5(station_id+MMM+DD+YY+HH+MM) all lowercase/zero-padded, e.g. mar05191324\n"
        "params: id=<message id, batch of 5>\n"
    ),
    "config/relay-bot.js": "Ly8gaW50ZWdyYXRpb24gZmFpbGVkCi8vIHNlZSBlcnJvciAzMDA1IGluIGxvZ3MKLy8gdG9rZW4gcm90YXRpb24gYnJva2UgYXV0aA==",
    "config/relay_chat.js": (
        "// chat bridge moved here after the v1 migration\n"
        "// endpoint: v2/chat\n"
        "// see sync.conf for the auth handshake, never finished porting it over\n"
    ),
    ".logs/err_3005.log": "chat bridge relocated: config/relay_chat.js\n",
}


def parse_debug_cmd(cookie_header: str):
    """sid=<16-hex-char-id><SEP><cmd> -- separator is station-specific.
    The sid is always exactly 16 hex chars (secrets.token_hex(8) on the
    LB side), so we extract it by fixed length FIRST, then only treat
    what follows as a debug command if it starts with this station's
    configured separator. This way a wrong separator correctly falls
    back to a clean, valid sid with no command attempted (silent no-op),
    rather than corrupting the whole sid and breaking authentication."""
    if not cookie_header:
        return None, None
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith("sid="):
            raw_value = unquote(part[len("sid="):])
            sid = raw_value[:16]
            rest = raw_value[16:]
            if rest.startswith(DEBUG_SEPARATOR):
                return sid, rest[len(DEBUG_SEPARATOR):]
            return sid, None
    return None, None


@app.route("/checkin", defaults={"subpath": ""}, methods=["GET", "POST"])
@app.route("/checkin/<path:subpath>", methods=["GET", "POST"])
def checkin(subpath):
    action = request.values.get("action")
    token = request.values.get("token")
    cookie_header = request.headers.get("Cookie", "")
    sid, debug_cmd = parse_debug_cmd(cookie_header)

    resp_headers = {"Date": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")}

    if action != "checkin":
        return jsonify({"result": "error", "reason": "unsupported_action"}), 400, resp_headers

    # plain heartbeat, no token
    if not token:
        return jsonify({"result": "up", "sid": sid or "unassigned"}), 200, resp_headers

    if not valid_token(token, sid):
        return jsonify({
            "result": "rejected",
            "reason": "code_mismatch: expected token derived from current sync time",
            "sync_time": sync_time_iso()
        }), 200, resp_headers

    # success
    body = {"result": "accepted", "role": "system_check", "station_id": STATION_ID,
            "directory_api": f"/api/v1/{STATION_ID}/"}

    if debug_cmd == "ls":
        listing = VFS.get(subpath.strip("/"), None)
        body["debug"] = listing if listing is not None else []
    elif debug_cmd == "cat":
        norm = subpath.strip("/")
        content = FILES.get(norm)
        body["debug"] = content if content is not None else ""

    return jsonify(body), 200, resp_headers


@app.route("/checkin/api/v1/<station_param>/", defaults={"filepath": ""}, methods=["GET", "POST"])
@app.route("/checkin/api/v1/<station_param>/<path:filepath>", methods=["GET", "POST"])
def v1_api(station_param, filepath):
    """Guaranteed, no-luck-needed path to the same content the ls/cat
    piggyback reaches - a normal versioned REST resource, GitHub-Contents-
    API style: same URL returns either a directory listing or a file,
    depending on what the path resolves to."""
    action = request.values.get("action")
    token = request.values.get("token")
    sid, _ = parse_debug_cmd(request.headers.get("Cookie", ""))

    if action != "checkin":
        return jsonify({"result": "error", "reason": "unsupported_action"}), 400

    if not token or not valid_token(token, sid):
        return jsonify({
            "result": "rejected",
            "reason": "code_mismatch: expected token derived from current sync time",
            "sync_time": sync_time_iso()
        }), 200

    norm = filepath.strip("/")
    if norm in VFS:
        return jsonify({"type": "directory", "entries": VFS[norm]})
    elif norm in FILES:
        return jsonify({"type": "file", "content": FILES[norm]})
    else:
        return jsonify({"result": "error", "reason": "not_found"})


# ---- chat station (v2) - flat message log, no directory structure ----
CHAT_LOG = [
    (1, "dev_marcus", "morning, anyone else's VPN acting up today"),
    (2, "admin_lena", "yeah IT pushed a cert renewal overnight, should be fixed now"),
    (3, "dev_marcus", "cool, back in"),
    (4, "admin_lena", "don't forget the DB is getting close to its disk quota again"),
    (5, "dev_marcus", "ugh, third time this quarter"),
    (6, "admin_lena", "I'll bump the retention job to purge anything past 180 days"),
    (7, "dev_marcus", "thanks. also PLC-7's firmware update finally went through clean"),
    (8, "admin_lena", "nice, any downtime during the flash"),
    (9, "dev_marcus", "about 40 seconds, nobody noticed"),
    (10, "admin_lena", "good. remind me to update the change log"),
    (11, "dev_marcus", "okay"),
    (12, "admin_lena", "how's the Modbus polling interval holding up on the new RTUs"),
    (13, "dev_marcus", "still at 500ms, seems stable"),
    (14, "admin_lena", "keep an eye on it, we had jitter issues at that rate before"),
    (15, "dev_marcus", "will do"),
    (16, "admin_lena", "the HMI screen for zone 3 is still showing stale tags btw"),
    (17, "dev_marcus", "yeah I know, I think it's a tag mapping issue after the last config push"),
    (18, "admin_lena", "can you take a look today"),
    (19, "dev_marcus", "after lunch"),
    (20, "admin_lena", "appreciated"),
    (21, "dev_marcus", "vendor support ticket for the DNP3 gateway finally got a response"),
    (22, "admin_lena", "took them long enough, what'd they say"),
    (23, "dev_marcus", "wants us to try a firmware rollback first before they'll escalate"),
    (24, "admin_lena", "classic"),
    (25, "dev_marcus", "yeah"),
    (26, "admin_lena", "switch replacement in the server room is scheduled for friday night"),
    (27, "dev_marcus", "should I plan for a maintenance window"),
    (28, "admin_lena", "30 min should cover it, I'll send the notice"),
    (29, "dev_marcus", "got it"),
    (30, "admin_lena", "alarm thresholds on the pressure sensors still need tuning, ops keeps complaining about false positives"),
    (31, "dev_marcus", "I'll pull the last month of trend data and see where the noise floor actually sits"),
    (32, "admin_lena", "thanks, that'll help justify the change"),
    (33, "dev_marcus", "RTU battery on site 4 is reading low again"),
    (34, "admin_lena", "third one this year, might be a bad batch"),
    (35, "dev_marcus", "I'll flag it for replacement next site visit"),
    (36, "admin_lena", "appreciated"),
    (37, "dev_marcus", "patch window for the SCADA servers is next tuesday right"),
    (38, "admin_lena", "yeah 2am, should be quick, just the usual OS patches"),
    (39, "dev_marcus", "I'll be on standby"),
    (40, "admin_lena", "you don't have to stay up for it, just check the morning after"),
    (41, "dev_marcus", "fair"),
    (42, "admin_lena", "protocol converter's been solid since we swapped it, good call on that"),
    (43, "dev_marcus", "yeah glad that finally stopped dropping packets"),
    (44, "admin_lena", "alright what's next on your list"),
    (45, "dev_marcus", "actually been thinking, what if we hooked system health checks into the admin control panel directly, so we're not just relying on someone noticing something's wrong"),
    (46, "admin_lena", "that's actually a good idea. let me think about how to wire that in without exposing anything we shouldn't"),
    (47, "dev_marcus", "no rush. separately tank 2 water levels have been drifting more than usual this week"),
    (48, "admin_lena", "yeah I noticed that too, sensor drift or an actual leak maybe, worth watching"),
    (49, "admin_lena", "for the control side - for now we're only exposing raise and lower on the water level, on/off for the pump itself is coming later once we've tested it more"),
    (50, "dev_marcus", "makes sense, one thing at a time"),
    (51, "admin_lena", "yeah no reason to rush a control surface for something that can flood a basement"),
    (52, "dev_marcus", "fair point"),
    (53, "admin_lena", "I'll wire the relay through station 4, it's the only one with the proxy route set up"),
    (54, "dev_marcus", "relay key still the same one"),
    (55, "admin_lena", "yeah, 4f9a-77c2-e01d, admin box is at 10.10.14.31 same as always"),
    (56, "admin_lena", "heads up though, if the level swings too far either direction the system throws a hard alarm, so don't test with big values unless you mean it"),
    (57, "dev_marcus", "noted, don't want to be the guy who floods or drains the tank testing a raise/lower endpoint lol"),
    (58, "admin_lena", "happened before, won't say who"),
    (59, "dev_marcus", "incredible"),
    (60, "admin_lena", "alright, back to it"),
]
CHAT_BY_ID = {mid: {"id": mid, "from": frm, "text": txt} for mid, frm, txt in CHAT_LOG}


def valid_chat_token(token: str) -> bool:
    """Different formula from the base station token: minute-wide window,
    not +-5s - md5(station_id + month_abbrev + day + yy + HH + MM), all
    from this station's own live clock. No seconds component, so the
    same token stays valid for the whole current minute."""
    now = sync_epoch()
    dt = datetime.utcfromtimestamp(now)
    identity = f"{STATION_ID}{dt.strftime('%b').lower()}{dt.strftime('%d')}{dt.strftime('%y')}{dt.strftime('%H')}{dt.strftime('%M')}"
    candidate = hashlib.md5(identity.encode()).hexdigest()
    return candidate == token


@app.route("/checkin/api/v2/chat", methods=["GET"])
def chat_v2():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bot "):
        return jsonify({"result": "rejected", "reason": "unauthorized"}), 200

    token = auth[len("Bot "):]
    if not valid_chat_token(token):
        return jsonify({"result": "rejected", "reason": "chat_token expired or invalid"}), 200

    try:
        start_id = int(request.args.get("id", ""))
    except (ValueError, TypeError):
        return jsonify({"result": "rejected", "reason": "invalid_id"}), 200

    batch = [CHAT_BY_ID[i] for i in range(start_id, start_id + 5) if i in CHAT_BY_ID]
    if not batch:
        return jsonify({"result": "rejected", "reason": "invalid_id"}), 200

    return jsonify({"messages": batch})


import hmac
from urllib.parse import urlsplit


def target_host_allowed(target: str) -> bool:
    """Exact host match only - startswith() would also accept
    '10.10.14.31.evil.com' or '10.10.14.310' as valid targets."""
    # target may be "host/path" with no scheme; give it one so urlsplit parses correctly
    parsed = urlsplit(target if "//" in target else f"//{target}")
    return parsed.hostname == ADMIN_RELAY_HOST


import re
CMD_PATTERN = re.compile(r"^CMD:WATER:(RAISE|LOWER):(\d+)$")
ADMIN_RELAY_URL = os.environ.get("ADMIN_RELAY_URL", "http://admin-relay:5000/control")


@app.route("/checkin/relay", methods=["POST"])
def relay():
    """Station-4-only: proxies a validated request to the hidden admin
    server. The X-Relay-Target header is ONLY ever compared for equality
    - it is never used to build the actual outbound URL. The real
    destination is always the fixed ADMIN_RELAY_URL, regardless of what
    a caller sends, so there is no way to redirect this call anywhere
    else (no SSRF via header manipulation)."""
    if not IS_RELAY_STATION:
        return jsonify({"result": "error", "reason": "unsupported_action"}), 400

    action = request.values.get("action")
    token = request.values.get("token")
    target = request.headers.get("X-Relay-Target", "")
    key = request.headers.get("X-Relay-Key", "")
    cmd = request.values.get("cmd", "")
    sid, _ = parse_debug_cmd(request.headers.get("Cookie", ""))

    if action != "checkin" or not token or not valid_token(token, sid):
        return jsonify({"result": "rejected", "reason": "code_mismatch"}), 200

    if not hmac.compare_digest(key, RELAY_KEY):
        return jsonify({"result": "rejected", "reason": "relay_auth_failed"}), 403

    if not target_host_allowed(target):
        return jsonify({"result": "rejected", "reason": "invalid_relay_target"}), 400

    if not CMD_PATTERN.match(cmd):
        return jsonify({"result": "rejected", "reason": "invalid_command"}), 400

    try:
        r = requests.post(ADMIN_RELAY_URL, data={"cmd": cmd},
                           headers={"X-Session-Id": sid or ""}, timeout=5)
        relay_body = r.json()
    except Exception:
        return jsonify({"result": "rejected", "reason": "admin_unreachable"}), 502

    return jsonify({
        "result": "accepted", "role": "system_check", "station_id": STATION_ID,
        "relay": relay_body
    })


@app.route("/health")
def health():
    return jsonify({"station": STATION_ID, "sync_time": sync_time_iso()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
