# Challenge Name
The Vantage Job

# Final Flag
`csaw{cr0ss_pl4tf0rm_carel3ssness}`

# Challenge Description
Three nights ago, Solenne & Vane, a private auction house in Geneva, was robbed of a hardware wallet holding the keys to a dormant 340 BTC wallet, once seized in a fraud case and quietly re-listed for a closed-bid sale. No forced entry. No alarms. Interpol's cybercrime liaison is out of leads through official channels, which is why you've been brought in.

One thing is certain: the person behind this can't resist bragging.

The thief goes by **"Ferryman."**

**Attached is a file left by the thief on the company's server and a poem he left along with it.**

# Player Files
Give players one attachment on the CTFd page:

```
dist/
  evidence_01.pdf
  evidence_02.txt
```

Everything else in this challenge is live infrastructure, not a download — the
Discord bot, the Instagram account, the two X accounts, the TinyURL, and the
Pastebin paste all have to be stood up before launch.

Exclude from the player download:
```
discord_bot/           bot source and deploy notes
receipt.b64
```

No generator ships to players. `case_file.pdf`, and `receipt.b64` are generated once and frozen; the build scripts are kept as internal notes so any hidden text, the flag, or the images can be regenerated if needed.

# Handles to register
| Platform | Handle |
|---|---|
| Discord bot username | `ferryman_vt` |
| Instagram | `ferryman_vt` |
| X (primary) | `tockferr` |
| X (decoy, for the Likes mechanic) | `timepieces_ferr` |
| TinyURL alias | `<3wm4tty4>` → `tinyurl.com+ id found on timepieces_ferr` |

# Full Chain/writeup

| # | Stage | Mechanism | Leads to |
|---|-------|-----------|----------|
| 1 | CTFd `case_file.pdf` | Zero-text-layer PDF; poem riddle drawn as near-invisible pixels (`RGB 252,252,252` on white), recoverable by rendering the page and boosting contrast around  | `/fingerprint` slash command |
| 2 | Discord bot (DM, Vercel serverless) | Rhymed ephemeral reply; the bot's own **username** is the clue | Instagram handle `ferryman_vt` |
| 3 | Instagram | Acrostic poem caption — first letters spell the X handle | X handle `tockferr` |
| 4 | X — tweets | Mostly rhyming noise plus one soft red herring | Nothing decisive on its own |
| 5 | X — Comments tab | A reply posted by `timepieces_ferr` leads to another post on his account carrying a TinyURL | tinyurl.com/vantage-job |
| 6 | TinyURL | Redirects back to `@tockferr`'s own profile | Prompts a closer re-read |
| 7 | X — bio | Spaced-out Pastebin link, visible the whole time but easy to skim past | Pastebin URL |
| 8 | Pastebin | Base64 blob → decode | `receipt.jpg` |
| 9 | EXIF | `exiftool receipt.jpg` | **Flag** |


# Accreditation
Yash Chandna

# Release Wave Preference
second wave

