import os, base64, json, time, secrets
from urllib.parse import urlencode
import urllib.request
from flask import Flask, request, redirect, make_response, render_template, abort
import jwt as pyjwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes

CLIENT_ID = "trustdinoidc-portal"
ADMIN_SCOPE = "flagosaurus:redeem"
HERO_ANON = "https://upload.wikimedia.org/wikipedia/commons/8/85/Tyrannosaurus_rex.jpg"
HERO_MEMBER = "https://upload.wikimedia.org/wikipedia/commons/4/4a/Triceratops.jpg"
HERO_ADMIN = "https://upload.wikimedia.org/wikipedia/commons/c/cd/Velociraptor_dinoguy2.jpg"
FLAG = os.environ["FLAG"]
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL")
ISSUERS = {"paleoid": ("paleoid.example.com", 8991), "strataid": ("strataid.example.com", 8992)}
ALLOWED_ISSUERS = {iss for iss, _ in ISSUERS.values()}


def fetch_pin(slug):
    _, port = ISSUERS[slug]
    url = f"http://{slug}:{port}/jwks.json"
    for _ in range(30):
        try:
            jwks = json.load(urllib.request.urlopen(url, timeout=2))
            der = base64.b64decode(jwks["keys"][0]["x5c"][0])
            return x509.load_der_x509_certificate(der).fingerprint(hashes.SHA256())
        except Exception:
            time.sleep(1)
    raise RuntimeError(f"could not fetch jwks for {slug}")


PINNED_CERTS = {"paleoid.example.com": fetch_pin("paleoid")}

app = Flask(__name__)


def verify(token):
    header = pyjwt.get_unverified_header(token)
    if "x5c" not in header:
        raise ValueError("missing x5c")
    claims = pyjwt.decode(token, options={"verify_signature": False})
    iss = claims.get("iss")
    if iss not in ALLOWED_ISSUERS:
        raise ValueError("unknown issuer")
    cert = x509.load_der_x509_certificate(base64.b64decode(header["x5c"][0]))
    pin = PINNED_CERTS.get(iss)
    if pin and cert.fingerprint(hashes.SHA256()) != pin:
        raise ValueError("certificate mismatch")
    return pyjwt.decode(token, key=cert.public_key(), algorithms=["RS256"], audience=CLIENT_ID)


def auth_urls(base, scope, return_to):
    redirect_uri = f"{base}/oauth/callback"
    urls = {}
    for slug in ISSUERS:
        state = f"{return_to}:{secrets.token_urlsafe(6)}"
        qs = urlencode({"client_id": CLIENT_ID, "redirect_uri": redirect_uri, "scope": scope, "state": state})
        urls[slug] = f"{base}/idp/{slug}/authorize?{qs}"
    return urls


@app.get("/")
def index():
    claims = None
    token = request.cookies.get("session")
    if token:
        try:
            claims = verify(token)
        except Exception:
            pass
    scope = claims.get("scope", "").split() if claims else []
    admin = ADMIN_SCOPE in scope
    member = admin or "freeosaurus:redeem" in scope
    hero = HERO_ADMIN if admin else HERO_MEMBER if claims else HERO_ANON
    base = (PUBLIC_BASE_URL or request.host_url).rstrip("/")
    idp_urls = auth_urls(base, "openid profile freeosaurus:redeem", "")
    freeosaurus_urls = auth_urls(base, "openid profile freeosaurus:redeem", "freeosaurus")
    return render_template("index.html", admin=admin, member=member, flag=FLAG if admin else None,
                            claims=claims, idp_urls=idp_urls, freeosaurus_urls=freeosaurus_urls, hero=hero)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


@app.get("/idp/<slug>/authorize")
def idp_authorize_proxy(slug):
    if slug not in ISSUERS:
        abort(404)
    _, port = ISSUERS[slug]
    url = f"http://{slug}:{port}/authorize?{request.query_string.decode()}"
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        return opener.open(url).read()
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303):
            return redirect(e.headers["Location"])
        raise


@app.get("/logout")
def logout():
    resp = make_response(redirect("/"))
    resp.delete_cookie("session")
    return resp


@app.get("/oauth/callback")
def callback_error():
    return request.args.get("error", "unknown_error"), 400


@app.post("/oauth/callback")
def callback():
    token = request.form.get("id_token", "")
    try:
        verify(token)
    except Exception as e:
        return str(e), 401
    return_to = request.form.get("state", "").split(":")[0]
    resp = make_response(redirect(f"/#{return_to}" if return_to else "/"))
    resp.set_cookie("session", token, httponly=True)
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8990)
