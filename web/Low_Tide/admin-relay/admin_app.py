#!/usr/bin/env python3
"""
Admin-relay service - the hidden SCADA control panel.

Never exposed on a host port. Only reachable from station-4's internal
network, and only via station-4's own /checkin/relay proxy - this
service never talks to a player directly.

Tracks water level per session (keyed by the sid station-4 forwards),
starting at 70, clamped 0-100. Hitting exactly 20 reveals the flag.
"""
import os
import re

from flask import Flask, request, jsonify

app = Flask(__name__)

FLAG = os.environ.get("FLAG", "CSAW{time_sensitive_scada_proxy_chain}")
START_LEVEL = 70
TARGET_LEVEL = 20

# in-memory per-session water level state
LEVELS = {}

CMD_PATTERN = re.compile(r"^CMD:WATER:(RAISE|LOWER):(\d+)$")


@app.route("/control", methods=["POST"])
def control():
    sid = request.headers.get("X-Session-Id", "")
    cmd = request.values.get("cmd", "")

    if not sid:
        return jsonify({"status": "error", "reason": "missing_session"}), 400

    match = CMD_PATTERN.match(cmd)
    if not match:
        return jsonify({"status": "error", "reason": "invalid_command"}), 400

    direction, amount = match.group(1), int(match.group(2))

    level = LEVELS.get(sid, START_LEVEL)
    if direction == "RAISE":
        level += amount
    else:
        level -= amount
    level = max(0, min(100, level))
    LEVELS[sid] = level

    body = {"status": "ok", "water_level": level}

    if level == TARGET_LEVEL:
        body["status"] = "critical"
        body["alarm"] = "LOW LEVEL"
        body["flag"] = FLAG
    elif level <= 5 or level >= 95:
        body["status"] = "critical"
        body["alarm"] = "LOW LEVEL" if level <= 5 else "HIGH LEVEL"

    return jsonify(body)


@app.route("/health")
def health():
    return jsonify({"admin": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
