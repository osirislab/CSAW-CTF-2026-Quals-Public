import os, json, random, base64
from typing import Optional
from fastapi import FastAPI, Request, Response, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

app = FastAPI(
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

FLAG   = r"csaw{el3gant_sw1ng_n3ver_c4ught}"
PHRASE = ["fairway", "putt", "knock"]

ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
W = {"I":"EKMFLGDQVZNTOWYHXUSPAIBRCJ","II":"AJDKSIRUXBLHWTMCQGZNPYFVOE",
     "III":"BDFHJLCPRTXVZNYEIWGAKMUSQO","REF":"YRUHQSLDPXNGOKMIEBFZCWVJAT"}

WORDS = {
    "A":["albatross","approach","ace"],   "B":["birdie","bogey","bunker"],
    "C":["caddy","chip","course"],        "D":["divot","dogleg","driver"],
    "E":["eagle","embed","escrow"],       "F":["fairway","flop","flag"],
    "G":["green","grip","gimme"],         "H":["handicap","hazard","hole"],
    "I":["iron","inside","index"],        "J":["jigger","juniper","joint"],
    "K":["knock","knoll","keeper"],       "L":["links","lie","loft"],
    "M":["mashie","mulligan","marker"],   "N":["niblick","net","nap"],
    "O":["open","out","oath"],            "P":["par","putt","pin"],
    "Q":["qualify","quest","quad"],       "R":["rough","round","ridge"],
    "S":["stroke","scratch","slope"],     "T":["tee","tap","triple"],
    "U":["under","uphill","uneven"],      "V":["vault","vantage","vector"],
    "W":["wedge","water","waggle"],       "X":["xeric","xerox","xenon"],
    "Y":["yardage","yips","yield"],       "Z":["zone","zenith","zero"],
}

MEMBERS = [
    {"id":1,"name":"Reginald Ashworth","handicap":4, "membership":"Platinum","since":2018,"status":"Active"},
    {"id":2,"name":"Caroline Vance",   "handicap":12,"membership":"Gold",    "since":2020,"status":"Active"},
    {"id":3,"name":"Desmond Okafor",   "handicap":7, "membership":"Platinum","since":2016,"status":"Active"},
    {"id":4,"name":"Harriet Bloom",    "handicap":18,"membership":"Silver",  "since":2022,"status":"On Hold"},
    {"id":5,"name":"Theodore Marsh",   "handicap":2, "membership":"Platinum","since":2014,"status":"Active"},
    {"id":6,"name":"Sylvia Renner",    "handicap":9, "membership":"Gold",    "since":2019,"status":"Active"},
    {"id":7,"name":"Edmund Fitch",     "handicap":22,"membership":"Silver",  "since":2023,"status":"Active"},
]

def enigma(r1, r2, r3):
    def f(c, w, o): return w[(ALPHA.index(c)+o)%26]
    out = []
    for s in ["G","O","L"]:
        c=s; c=f(c,W["I"],r1%26); c=f(c,W["II"],r2%26); c=f(c,W["III"],r3%26)
        c=W["REF"][ALPHA.index(c)]; c=f(c,W["III"],(26-r3%26)%26)
        out.append(c)
    return out

def hint(v): return base64.b64encode(f"{v:06d}".encode()).decode()

import secrets as _sec
R1 = _sec.randbelow(26)
R2 = _sec.randbelow(26)
R3 = _sec.randbelow(26)
_letters = enigma(R1, R2, R3)
PHRASE = [WORDS[_letters[0]][0], WORDS[_letters[1]][1], WORDS[_letters[2]][0]]

# ── Pydantic models ──────────────────────────────────────────────────────────

class EnigmaRequest(BaseModel):
    r1: int = 0
    r2: int = 0
    r3: int = 0

class VaultPhraseRequest(BaseModel):
    phrase: str

class MemberCreate(BaseModel):
    name: str
    handicap: int
    membership: str
    since: int
    status: str

class MemberUpdate(BaseModel):
    name: Optional[str] = None
    handicap: Optional[int] = None
    membership: Optional[str] = None
    since: Optional[int] = None
    status: Optional[str] = None

# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/pro-shop/inventory/clubs")
async def clubs(req: Request):
    return Response("I'm a teapot.", status_code=418,
        headers={"X-Golf-Hint": hint(R1), "X-Caddy-Note": "Rotor I"})

@app.get("/pro-shop/inventory/balls")
async def balls(req: Request):
    return Response("I'm a teapot.", status_code=418,
        headers={"X-Golf-Hint": hint(R2), "X-Caddy-Note": "Rotor II"})

@app.get("/pro-shop/inventory/bags")
async def bags(req: Request):
    return Response("I'm a teapot.", status_code=418,
        headers={"X-Golf-Hint": hint(R3), "X-Caddy-Note": "Rotor III"})

@app.post("/api/enigma/encode")
async def enigma_api(body: EnigmaRequest):
    return {"output": enigma(body.r1, body.r2, body.r3)}

@app.get("/api/word-table")
async def word_table(): return {"table": WORDS}

@app.post("/api/vault/enter")
async def vault_enter(body: VaultPhraseRequest):
    phrase = body.phrase.strip().lower().split()
    if phrase == PHRASE:
        return {"success": True, "tier": "privileged",
            "message": "Welcome, privileged user. You are in. But the special item is reserved for admin only.",
            "special_item": {"locked": True},
            "hint": "The caddy has a known vulnerability. Check GHSA-7r4p-vjf4-gxv4. API Docs available to webmasters."}
    return JSONResponse({"error": "Access denied."}, status_code=403)

@app.post("/api/vault/admin-item")
async def vault_admin(body: VaultPhraseRequest, req: Request):
    phrase = body.phrase.strip().lower().split()
    if phrase != PHRASE:
        return JSONResponse({"error": "Wrong phrase."}, status_code=403)
    role = req.headers.get("X-User-Role", "")
    uid  = req.headers.get("X-User-Id", "guest")
    if role.lower() == "admin":
        return {"success": True, "tier": "admin",
            "message": f"Welcome, {uid}. Identity header trusted. The caddy looked the other way.",
            "special_item": {"locked": False, "name": "The Golden Putter",
                "description": "Forged from a single billet of 18k gold. No grip. No mercy. One of one.",
                "provenance": "Taken from the Avispa vault, March 2025. The caddy never saw it leave."},
            "flag": FLAG, "cve": "GHSA-7r4p-vjf4-gxv4",
            "exploit": "Caddy forward_auth copy_headers does not strip client-supplied headers. X-User-Role: admin was injected and trusted by the backend."}
    return JSONResponse({"error": "Insufficient role.", "your_role": role or "(none)",
        "hint": "The caddy doesn't strip what the auth service doesn't set."}, status_code=403)

@app.get("/api/engineer/caddyfile")
async def caddyfile():
    content = """{
    admin off
    auto_https off
}

:8000 {
    forward_auth 127.0.0.1:9091 {
        uri /auth
        copy_headers X-User-Id X-User-Role
    }
    reverse_proxy 127.0.0.1:9092
}
"""
    return Response(content, media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=Caddyfile"})

@app.get("/api/engineer/status")
async def eng_status(): return {"daemon": "WATCHING", "vault_sealed": False, "burn_count": 0}

@app.post("/api/engineer/reset")
async def eng_reset(): return {"success": True}

@app.get("/api/members")
async def get_members(): return {"members": MEMBERS}

@app.put("/api/members/{mid}")
async def upd_member(mid: int, body: MemberUpdate):
    return {"success": True, "member_id": mid, "updated": body.model_dump(exclude_none=True)}

@app.delete("/api/members/{mid}")
async def del_member(mid: int): return {"success": True}

@app.post("/api/members")
async def new_member(body: MemberCreate):
    return {"success": True, "member": {**body.model_dump(), "id": random.randint(100,999)}}

@app.get("/", response_class=HTMLResponse)
async def index(req: Request):
    return templates.TemplateResponse("index.html", {"request": req})

@app.get("/collection", response_class=HTMLResponse)
async def collection(req: Request):
    return templates.TemplateResponse("collection.html", {"request": req})

@app.get("/vault", response_class=HTMLResponse)
async def vault_page(req: Request):
    return templates.TemplateResponse("vault.html", {"request": req})

@app.get("/engineer", response_class=HTMLResponse)
async def engineer_page(req: Request):
    return templates.TemplateResponse("engineer.html", {"request": req})

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
