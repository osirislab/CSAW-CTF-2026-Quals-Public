# TRUSTDINOIDC

Category: Web

# Description

TrustDinOIDC sells dinosaur posters to anyone who can prove they're logged in. The Flagosaurus print is for admins only.

# Deployment

        cd deployment
        docker compose up --build

        # custom port
        TRUSTDINOIDC_PORT=<port> docker compose up --build

        # public origin, when something in front terminates TLS
        PUBLIC_BASE_URL=https://example.com docker compose up --build

Runs on port 8990 by default. PaleoID and StrataID are separate
internal-only services with no exposed ports. The portal proxies their
`/authorize` pages so everything is reachable through the one public port.

The portal builds its own `redirect_uri` from the incoming request's
scheme/host, which only matches reality when nothing in front of it
terminates TLS. `PUBLIC_BASE_URL` overrides that with a fixed origin -
unset it and the portal falls back to the request itself.

## Production

Set `FLAG` and `PUBLIC_BASE_URL` (the real public `https://` origin)
in `deployment/.env`. Deploying is then the same command as above -
no flags, no overrides, just a rebuild:

        cd deployment
        docker compose up -d --build

# Flag

Set via `FLAG` in `deployment/.env`.

# Author
rollingcoconut

# Solution

<details>
    <summary> Spoiler warning </summary>

        Both paleoid.example.com and strataid.example.com are whitelisted
        issuers. Only paleoid's cert is pinned (fetched from its JWKS at
        boot). strataid isn't, so /oauth/callback trusts whatever key a
        strataid-claiming token brings in its own x5c header.

        Self-sign a cert, forge an id_token: iss=strataid.example.com,
        scope containing flagosaurus:redeem. POST as id_token to
        /oauth/callback, then GET /. Flag's on the Flagosaurus section.

        Same forgery against paleoid: rejected, certificate mismatch.

</details>
