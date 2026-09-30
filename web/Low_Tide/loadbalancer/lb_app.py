#!/usr/bin/env python3
"""
Load balancer - single public entrypoint. Enforces UA allowlist and
lap/pacing defense, routes sessions to one of N internal station backends,
proxies transparently.
"""
import os
import secrets
import time
from datetime import datetime

import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

REQUIRED_UA = os.environ.get("REQUIRED_UA", "StationSync-Agent/2.1")

# comma-separated internal station URLs, in order (last one must be the relay station)
STATION_URLS = os.environ.get(
    "STATION_URLS",
    "http://127.0.0.1:5001,http://127.0.0.1:5002,http://127.0.0.1:5003,http://127.0.0.1:5004"
).split(",")

BURST_LIMIT = 5
BURST_WINDOW = 5
LAP_SIZE = 4              # attempts allowed per station before rotation
MINI_COOLDOWN = 15        # after rotating to a new station
BIG_COOLDOWN = 16         # after a full cycle (all 4 stations exhausted, 16 total attempts)
RELAY_MIN_INTERVAL = 10
RELAY_MAX_WRONG = 3

# in-memory session store: sid -> state dict
SESSIONS = {}


def new_session():
    return {
        "station_index": secrets.randbelow(len(STATION_URLS)),
        "burst_times": [],
        "lap_count": 0,           # attempts on the CURRENT station
        "tried_stations": set(),  # stations already exhausted this cycle
        "cooldown_until": None,
        "relay_last_attempt": 0,
        "relay_wrong_count": 0,
    }


def get_sid_from_cookie(cookie_header: str):
    """Extract just the sid value (up to first space) for LB bookkeeping.
    The full raw cookie is still forwarded untouched to the backend."""
    if not cookie_header:
        return None
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith("sid="):
            from urllib.parse import unquote
            raw_value = unquote(part[len("sid="):])
            return raw_value.split(" ", 1)[0]
    return None


def decoy_response():
    return jsonify({
        "result": "rejected",
        "reason": "code_mismatch: expected token derived from current sync time",
        "sync_time": "2019-01-02T03:14:07Z"
    })


def proxy_to_station(session, path, raw_body, is_relay=False):
    station_url = STATION_URLS[session["station_index"]]
    if is_relay:
        target = f"{station_url}/checkin/relay"
    else:
        target = f"{station_url}/checkin"
        if path:
            target += f"/{path}"

    query_string = request.query_string.decode()
    if query_string:
        target += f"?{query_string}"

    headers = {
        "Cookie": request.headers.get("Cookie", ""),
        "Content-Type": request.headers.get("Content-Type", "application/x-www-form-urlencoded"),
    }
    for h in ("X-Relay-Target", "X-Relay-Key", "Authorization"):
        if h in request.headers:
            headers[h] = request.headers[h]

    try:
        r = requests.request(
            method=request.method,
            url=target,
            headers=headers,
            data=raw_body,
            timeout=5,
        )
    except requests.RequestException:
        # must return a real Response, not a bare tuple - checkin() unconditionally
        # accesses resp.headers below, which a tuple doesn't have
        resp = jsonify({"result": "error", "reason": "upstream_unavailable"})
        resp.status_code = 502
        return resp

    return Response(r.content, status=r.status_code, content_type="application/json")


def handle_lap_accounting(session):
    """Call after a failed (rejected) token attempt. Returns an override
    response if rotation/cooldown should intercept, else None.

    Model: 4 attempts per station. On the 4th failure, mark this station
    tried and either rotate to an untried station (+15s mini cooldown),
    or - if all 4 stations have now been exhausted (16 total attempts) -
    apply a 16s big cooldown and reset the cycle entirely.
    """
    session["lap_count"] += 1
    if session["lap_count"] < LAP_SIZE:
        return None

    session["tried_stations"].add(session["station_index"])
    session["lap_count"] = 0

    if len(session["tried_stations"]) >= len(STATION_URLS):
        # full cycle exhausted - big cooldown, then start a fresh cycle
        session["cooldown_until"] = time.time() + BIG_COOLDOWN
        session["tried_stations"] = set()
        session["station_index"] = secrets.randbelow(len(STATION_URLS))
        return jsonify({"result": "rejected", "reason": "cycle_exhausted", "cooldown": BIG_COOLDOWN}), 200

    # rotate to a station not yet tried this cycle
    choices = [i for i in range(len(STATION_URLS)) if i not in session["tried_stations"]]
    session["station_index"] = secrets.choice(choices)
    session["cooldown_until"] = time.time() + MINI_COOLDOWN
    return jsonify({"result": "rejected", "reason": "station_exhausted", "cooldown": MINI_COOLDOWN}), 200


@app.route("/station/checkin", defaults={"subpath": ""}, methods=["GET", "POST"])
@app.route("/station/checkin/<path:subpath>", methods=["GET", "POST"])
def checkin(subpath):
    # capture the raw body FIRST - accessing request.values/.form before this
    # consumes the stream and leaves get_data() empty for the proxy forward
    raw_body = request.get_data()

    ua = request.headers.get("User-Agent", "")
    if ua != REQUIRED_UA:
        return decoy_response()

    is_relay = subpath == "relay"

    sid = get_sid_from_cookie(request.headers.get("Cookie", ""))
    set_cookie = False
    if sid is None or sid not in SESSIONS:
        sid = secrets.token_hex(8)  # 64-bit - cheap to raise from the previous 32-bit
        SESSIONS[sid] = new_session()
        set_cookie = True
    session = SESSIONS[sid]

    now = time.time()

    if session["cooldown_until"] and now < session["cooldown_until"]:
        retry_after = int(session["cooldown_until"] - now)
        return jsonify({"result": "throttled", "reason": "cooldown", "retry_after": retry_after}), 429, {"Retry-After": str(retry_after)}
    elif session["cooldown_until"] and now >= session["cooldown_until"]:
        session["cooldown_until"] = None

    if is_relay:
        if now - session["relay_last_attempt"] < RELAY_MIN_INTERVAL:
            retry_after = int(RELAY_MIN_INTERVAL - (now - session["relay_last_attempt"]))
            return jsonify({"result": "throttled", "reason": "slow down", "retry_after": retry_after}), 429, {"Retry-After": str(retry_after)}
        session["relay_last_attempt"] = now
    else:
        session["burst_times"] = [t for t in session["burst_times"] if now - t < BURST_WINDOW]
        if len(session["burst_times"]) >= BURST_LIMIT:
            return jsonify({"result": "throttled", "reason": "slow down", "retry_after": BURST_WINDOW}), 429, {"Retry-After": str(BURST_WINDOW)}
        session["burst_times"].append(now)

    from urllib.parse import parse_qs
    form = parse_qs(raw_body.decode(errors="ignore"))
    has_token = bool(form.get("token", [None])[0])

    resp = proxy_to_station(session, subpath, raw_body, is_relay=is_relay)

    if set_cookie:
        resp.headers["Set-Cookie"] = f"sid={sid}; Path=/; HttpOnly; SameSite=Lax"

    try:
        body = resp.get_json(silent=True) or {}
    except Exception:
        body = {}

    if is_relay:
        if body.get("reason") == "relay_auth_failed":
            session["relay_wrong_count"] += 1
            if session["relay_wrong_count"] >= RELAY_MAX_WRONG:
                del SESSIONS[sid]
                return jsonify({"result": "rejected", "reason": "session_invalidated"}), 200
        return resp

    if has_token and body.get("result") == "rejected":
        override = handle_lap_accounting(session)
        if override:
            return override
    elif has_token and body.get("result") == "accepted":
        session["lap_count"] = 0
        session["tried_stations"] = set()

    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
