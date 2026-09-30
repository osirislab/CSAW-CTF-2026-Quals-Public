# /fingerprint bot — setup

This is the whole Discord piece of The Vantage Job: a single slash command,
`/fingerprint`, DM-enabled, deployed as a Vercel serverless function. No
persistent process, no Gateway connection, no reactions — Discord calls this
function once per command use, over plain HTTP.

## 1. Create the Discord application
1. Go to https://discord.com/developers/applications → **New Application**
2. Name it whatever the bot's public username should be — this name/username
   **is the Instagram-handle clue**, so pick it to match your Instagram
   account exactly (e.g. `ferryman_vt`).
3. Under **Bot**, click **Reset Token**, copy it → `DISCORD_BOT_TOKEN`
4. Under **General Information**, copy the **Public Key** →
   `DISCORD_PUBLIC_KEY`, and the **Application ID** →
   `DISCORD_APPLICATION_ID`
5. Under **Bot**, make sure the bot is **not** requiring the server members
   or message content intents — this bot doesn't need them, it only
   responds to slash-command interactions.
6. Generate an invite/OAuth2 URL with the `applications.commands` scope so
   it can be added anywhere needed (or just rely on DMs — the command has
   `dm_permission: true`, so any user who can find the bot can DM it
   directly without it needing to be in a server at all).

## 2. Install dependencies
```bash
cd 02_discord_bot
npm install
```

## 3. Set up environment variables
```bash
cp .env.example .env
# fill in DISCORD_PUBLIC_KEY, DISCORD_BOT_TOKEN, DISCORD_APPLICATION_ID
```

## 4. Register the slash command
```bash
npm run register
```
Global registration can take up to ~1 hour to show up everywhere. For
instant testing, set `GUILD_ID` in `.env` and swap to the guild-scoped URL
commented in `register-commands.js`.

## 5. Deploy

The bot is a plain HTTP service: Discord POSTs each command to one URL. It
runs as a Vercel serverless function — `server.js` is the entrypoint, and
the interaction logic lives in `lib/interactions.js`.

Run it locally first:
```bash
npm start
```
Check it is alive:
```bash
curl localhost:3000/health   # -> {"status":"ok"}
```
`/health` is unauthenticated and exists as a plain liveness check. The real
endpoint, `/api/interactions`, rejects anything without a valid Discord
Ed25519 signature.

Only `DISCORD_PUBLIC_KEY` is needed at runtime — the bot token and
application ID are used solely by `register-commands.js`, which you run once
from your laptop.

Then deploy:
```bash
vercel
```
Add the same three environment variables in the Vercel project settings
(Project → Settings → Environment Variables) so the deployed function can
read them — `.env` is local-only and won't carry over automatically.

Discord will not accept a plain-HTTP endpoint, so TLS is mandatory; Vercel
gives you an HTTPS URL directly.

## 6. Point Discord at your deployment
In the Discord Developer Portal, under **General Information**, set
**Interactions Endpoint URL** to your deployment's URL plus the path:
```
https://<your-vercel-project>.vercel.app/api/interactions
```
Discord will immediately send a PING to verify it — if the service is
reachable over HTTPS with the right public key, this should succeed
automatically. If it fails, double check `DISCORD_PUBLIC_KEY` is set
correctly wherever the bot is actually running (not just locally).

## 7. Test it
DM the bot (or use it in a server it's been added to) with `/fingerprint`.
You should get an ephemeral reply — visible only to you — with the poem
from `interactions.js`. Nothing else is needed on the Discord side; there
are no channels, roles, or reactions involved in this version.

## What this bot intentionally does NOT do
- No reaction watching (dropped in favor of the slash command — simpler,
  and works serverless on Vercel)
- No channel permissions or role grants (dropped — the reply itself is the
  full hint, delivered ephemerally)
- No file attachments (the hint is the bot's own identity, not a file)
