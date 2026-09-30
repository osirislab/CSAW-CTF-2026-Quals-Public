from flask import Flask, render_template_string, request, session, send_from_directory
from pathlib import Path
import json, re, hashlib, base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE=Path(__file__).resolve().parent.parent
DATA=BASE/"data"
app=Flask(__name__)
app.secret_key="CHANGE-ME-IN-PRODUCTION"

STONE_ACCEPTED={
    "c0de0651fc9f26617a3fa12d5641694b3dfbafb2ceeacb9a539f00e187789836",
    "b4684df7f44898957292f9ca049ecf4d48e14f4dad6f980d63ebf55612546c6e",
}
FROST_ACCEPTED={
    "c07e88cfbeecf7f072759553b0290397db12a5d34ade2bd631ba150d5c5880ad",
    "d198bdfe03622da4a194cda2a648b02c46aba3eff45dae99e0bfc86606f4b3bd",
}
IRON_ACCEPTED={
    "910fefdeb32cf2795ad662ba03b8bd3d7ce12589e75b722fd479b818cfe68ab3",
    "4882ea62a3cc494c961011d1cc50deb4f882717ba6b02aa3617092c4f628f91a",
}
VAULT_ACCEPTED={
    "e26e33ab384e820e4c946bc68dfbf2daae6db1546dd67ae1f035ec2d376a449f",
}

def verify(text, marker):
    return marker.upper() in re.sub(r"\s+"," ",text.strip()).upper()

def normalized_answer(text):
    return re.sub(r"\s+"," ",text.strip()).upper()

def answer_digest(text):
    return hashlib.sha256(normalized_answer(text).encode()).hexdigest()

def flag_digest(text):
    # The final flag is case-sensitive; strip surrounding whitespace only.
    return hashlib.sha256(text.strip().encode()).hexdigest()

def answer_matches(text, accepted):
    return answer_digest(text) in accepted

HTML="""<!doctype html><html><head><title>Midnight Vault</title>
<style>
body{font-family:monospace;background:#101418;color:#d9e2ea;max-width:1000px;margin:30px auto;padding:0 20px}
pre,textarea,input{background:#171d23;color:#d9e2ea;border:1px solid #52616b;padding:12px}
pre{white-space:pre-wrap}textarea{width:100%;height:160px}input{width:70%}
a,button{color:#101418;background:#b9d6e8;border:0;padding:8px 12px;text-decoration:none;font-weight:bold}
nav{display:flex;gap:8px;flex-wrap:wrap;margin:15px 0}.ok{color:#9be29b}.bad{color:#ff9d9d}
</style></head><body><h1>THE MIDNIGHT VAULT</h1>
<nav><a href="/">Crew Brief</a><a href="/stone">Granite</a><a href="/frost">Frost</a>
<a href="/iron">Iron</a><a href="/altar">Vault Map</a><a href="/inventory">Crew Kit</a></nav>
{% if msg %}<p class="{{cls}}">{{msg}}</p>{% endif %}{{body|safe}}</body></html>"""

def page(body,msg="",cls=""):
    return render_template_string(HTML,body=body,msg=msg,cls=cls)

def artifact_unlocked(name):
    if name == "stone.json":
        return True
    if name in {"frost.txt","frost.bin"}:
        return session.get("k1") is True
    if name == "iron.json":
        return session.get("k1") is True and session.get("k2") is True
    if name == "vault.json":
        return all(session.get(k) is True for k in ("k1","k2","k3"))
    return False

@app.route("/")
def index():
    return page("""<pre>
The crew hit the wrong safehouse and found a ghost ledger hidden in the snow.

Three lockboxes were built to protect a vault on the black market circuit.
Each hides a fragment of the final key.
None of them alone will open the job.

The first remembers.
The second preserves.
The third endures.

A final note on the stolen page reads:

    ⠁ ⠅⠑⠽ ⠙⠊⠧⠊⠙⠑⠙
    ⠃⠗⠁⠊⠇⠇⠑ ⠕⠏⠑⠝⠎ ⠞⠓⠑ ⠕⠇⠙ ⠗⠑⠛⠊⠎

The rest of the plan is missing.

Recover the three fragments, rebuild the key, and wake the old registry before the getaway van leaves.

The score goes to whoever gets in, gets out, and keeps their hands clean.
</pre>
<p>Hard mode: algorithm names are intentionally absent. Inspect the supplied artifacts.</p>""")

@app.route("/stone",methods=["GET","POST"])
def stone():
    d=json.loads((DATA/"stone.json").read_text()); msg=""
    if request.method=="POST":
        answer=request.form.get("answer","")
        if answer_matches(answer,STONE_ACCEPTED):
            session["k1"]=True
            return page("<pre>FRAGMENT ONE RECOVERED</pre>","The first lockbox clicks open.","ok")
        msg="The lockbox stays cold and shut."
    body=f"""<pre>GRANITE SAFE

Braille: {d["braille"]}  ⠗⠑⠍⠑⠍⠃⠑⠗ ⠞⠓⠑ ⠇⠕⠉⠅
Inscription: {d["inscription"]}

Ciphertext:
{d["ciphertext"]}

Other markings:
- {d["decoys"][0]}
- {d["decoys"][1]}
- {d["decoys"][2]}

The vault team needs the recovered plaintext fragment to wake the old registry and crack the first seal.
Submit the recovered plaintext fragment.</pre>
<form method="post"><textarea name="answer" placeholder="Recovered plaintext"></textarea><br><button>Submit</button></form>"""
    return page(body,msg,"bad" if msg else "")

@app.route("/frost",methods=["GET","POST"])
def frost():
    if session.get("k1") is not True:
        return page("<pre>FROST VAULT\n\nThe chamber remains sealed. The granite fragment must be recovered before the frost archive unlocks.</pre>")
    msg=""
    if request.method=="POST":
        if answer_matches(request.form.get("answer",""),FROST_ACCEPTED):
            session["k2"]=True
            return page("<pre>FRAGMENT TWO RECOVERED</pre>","The frozen lock yields and the chamber fogs over.","ok")
        msg="The cold vault ignores you."
    body="""<pre>FROST VAULT

Braille: ⠊⠉⠑ ⠏⠗⠑⠎⠑⠗⠧⠑ ⠞⠓⠑ ⠗⠑⠛⠊⠎
Inscription: WHAT IS PRESERVED REMEMBERS WHERE IT CAME FROM.

The copper plate points to two artifacts.
The binary payload is not stored in a straight line.
The cold metal hums with one sentence: the wardens copied the trail before sealing it.

<a href="/artifact/frost.txt">frost.txt</a>
<a href="/artifact/frost.bin">frost.bin</a></pre>
<form method="post"><textarea name="answer" placeholder="Recovered plaintext"></textarea><br><button>Submit</button></form>"""
    return page(body,msg,"bad" if msg else "")

@app.route("/iron",methods=["GET","POST"])
def iron():
    if session.get("k1") is not True or session.get("k2") is not True:
        return page("<pre>IRON SAFEGUARD\n\nThe steel plate remains dormant. The frost archive must be opened before the final lock reveals itself.</pre>")
    msg=""
    if request.method=="POST":
        if answer_matches(request.form.get("answer",""),IRON_ACCEPTED):
            session["k3"]=True
            return page("<pre>FRAGMENT THREE RECOVERED</pre>","The steel vault shudders and the final lockbox rolls open.","ok")
        msg="The steel plate rejects the fragment."
    body="""<pre>IRON SAFEGUARD

Braille: ⠊⠗⠕⠝ ⠎⠞⠑⠑⠇ ⠞⠓⠑ ⠗⠑⠛⠊⠎
Inscription: THE SHAPE OF THE ANSWER IS NOT THE ANSWER.

The tablet contains four digest columns and a binary payload.
Only when the old registry stirs does the chain become honest, but the payload was recopied before burial.

<a href="/artifact/iron.json">iron.json</a>

The crew needs the recovered plaintext fragment to finish the set.</pre>
<form method="post"><textarea name="answer" placeholder="Recovered plaintext"></textarea><br><button>Submit</button></form>"""
    return page(body,msg,"bad" if msg else "")

@app.route("/altar")
def altar():
    if not all(session.get(k) is True for k in ("k1","k2","k3")):
        return page("<pre>Three lock segments are still missing. The vault map refuses to align.</pre>")
    return page("""<pre>THE VAULT MAP

Three fragments were stashed beneath the frost,
Each guarding the piece the others lost.
Stone keeps memory, frost keeps time,
Iron joins the broken line.
Set all three where old locks meet;
The hidden cache will yield its seat.

The order is not decorative.

<a href="/vault">Proceed to the vault</a></pre>""")

@app.route("/vault",methods=["GET","POST"])
def vault():
    if not all(session.get(k) is True for k in ("k1","k2","k3")):
        return page("<pre>The vault remains sealed until the team finishes the lock set.</pre>")
    msg=""
    if request.method=="POST":
        if flag_digest(request.form.get("flag","")) in VAULT_ACCEPTED:
            session["won"]=True
            return page("""<pre>The coffer clicks.
Once. Twice. Then the locks release.

Inside is a collection of objects wrapped in ancient cloth,
untouched for generations.

Something enormous shifts beneath the city.

The crew gets away clean.</pre>""","THE VAULT IS OPEN.","ok")
        msg="The final lock rejects the key."
    return page("""<pre>THE VAULT

Three pieces. One key. No second attempt.

The vault map supplied the ordering rule.
vault.json contains the final artifact, but the wardens copied the seal in pieces before locking it away.

<a href="/artifact/vault.json">vault.json</a>

Decrypt the payload and submit the loot flag.</pre>
<form method="post"><input name="flag" placeholder="csaw{...}"><button>Open</button></form>""",msg,"bad" if msg else "")

@app.route("/inventory")
def inventory():
    rows=[f"{n}: {'[recovered]' if session.get(k) is True else '[unrecovered]'}" for k,n in
          [("k1","Stone"),("k2","Frost"),("k3","Iron")]]
    rows.append("Vault: "+("OPEN" if session.get("won") else "SEALED"))
    return page("<pre>CREW KIT\n\n"+"\n".join(rows)+"</pre>")

@app.route("/artifact/<path:name>")
def artifact(name):
    if name not in {"frost.txt","frost.bin","iron.json","vault.json","stone.json"}:
        return "Not found",404
    if not artifact_unlocked(name):
        return "Artifact remains sealed until the prior stage is solved.",403
    return send_from_directory(DATA,name,as_attachment=True)

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000)
