import os, base64, datetime as dt
from flask import Flask, request, render_template_string
import jwt as pyjwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID

ISSUER = os.environ["ISSUER"]
PORT = int(os.environ.get("PORT", 8991))
ACCENT = os.environ.get("ACCENT", "#4a9")
GRANTABLE = {"openid", "profile", "freeosaurus:redeem"}

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
NAME = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, ISSUER)])
CERT = (x509.CertificateBuilder()
        .subject_name(NAME).issuer_name(NAME)
        .public_key(KEY.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(dt.datetime.now(dt.timezone.utc))
        .not_valid_after(dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=365))
        .sign(KEY, hashes.SHA256()))
DER = CERT.public_bytes(serialization.Encoding.DER)

app = Flask(__name__)


def b64url_uint(n):
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


@app.get("/.well-known/openid-configuration")
def discovery():
    base = request.host_url.rstrip("/")
    return {"issuer": ISSUER, "authorization_endpoint": f"{base}/authorize", "jwks_uri": f"{base}/jwks.json"}


@app.get("/jwks.json")
def jwks():
    nums = KEY.public_key().public_numbers()
    return {"keys": [{"kty": "RSA", "use": "sig", "alg": "RS256", "kid": ISSUER,
                       "n": b64url_uint(nums.n), "e": b64url_uint(nums.e),
                       "x5c": [base64.b64encode(DER).decode()]}]}


CONSENT = """<!doctype html><title>{{ issuer }}</title>
<body style="background:#111;color:#eee;font-family:sans-serif;display:flex;
align-items:center;justify-content:center;height:100vh;margin:0">
<div style="background:#1c1c24;padding:2rem;border-radius:8px;text-align:center;max-width:22rem">
<h1 style="color:{{ accent }}">{{ issuer }}</h1>
<p>{{ client_id }} is requesting: {{ scope }}</p>
<form method="post" action="{{ redirect_uri }}">
<input type="hidden" name="id_token" value="{{ token }}">
<input type="hidden" name="state" value="{{ state }}">
<button style="padding:0.6rem 1.4rem;border:none;border-radius:4px;background:{{ accent }};color:#fff;font-size:1rem">Allow</button>
</form>
</div></body>"""


@app.get("/authorize")
def authorize():
    redirect_uri = request.args["redirect_uri"]
    client_id = request.args.get("client_id", "")
    scope = request.args.get("scope", "openid profile")
    state = request.args.get("state", "")
    granted = " ".join(s for s in scope.split() if s in GRANTABLE)
    payload = {"iss": ISSUER, "sub": "guest", "aud": client_id, "scope": granted,
               "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)}
    token = pyjwt.encode(payload, KEY, algorithm="RS256", headers={"x5c": [base64.b64encode(DER).decode()]})
    return render_template_string(CONSENT, issuer=ISSUER, client_id=client_id, scope=scope,
                                   redirect_uri=redirect_uri, token=token, state=state, accent=ACCENT)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
