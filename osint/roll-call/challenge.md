# Challenge Name
Roll Call

# Final Flag
`csaw{halcyonleaks_still_water_77}`

# Challenge Description
You are an intelligence analyst on an executive-protection detail. Someone has made
a credible threat against the principal, a fictional biotech CEO. Before the team
can assess anyone, you have to scope the case: who is actually in it?

The detail keeps a watch list by hand, and it has fallen behind. You get a data dump
instead — forum posts, contact-form messages, an intake mailbox, a records note, a
watch list, and a database. The files do not agree with each other. The database is
the record of truth. The flat exports lag and leave things out. Two subjects were
escalated to the detail and never written down. Find them.

The case records note in `case_file/protocol.md` explains how this detail maintains
its files.

The flag names both missing handles: `csaw{handle_handle}`, lower case, alphabetical,
joined by an underscore. Keep any underscores already inside a handle.

# Player Files
Give players everything under `dist/`:

```
dist/
  comms/
    forum_dump.json
    dm_export.json
    email_intake.mbox
  case_file/
    watchlist.csv
    protocol.md
    intake.db
  timeline/
    posting_activity.csv
```

Exclude from the player download:
```
deployment/
  WU/solve.md        solution, spoils the flag
```

No generator ships to players. The files are generated once and frozen, and the
build scripts that produced them live outside this repo as internal notes.

# Accreditation
Vinayak Malik (name and handle both fine to use)

# Release Wave Preference
First wave but either wave works.

# Solve Script / Writeup
`WU/solve.md`, already in the repo.
