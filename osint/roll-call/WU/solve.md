# Roll Call — writeup

**Flag:** `csaw{halcyonleaks_still_water_77}`

## The task

You get a case file. You must name the two subjects that nobody logged. The watch
list holds 8 names. Two facts make this more than a list comparison. The watch list
is not the authoritative record. And one person can use more than one handle.

You do not need a query language. You solve this with a SQLite viewer and a
spreadsheet. You open files, sort a column, and compare.

## Step 0 — read the protocol and list the files

Read the published challenge description (maintained in `challenge.md`) first.

`dist/case_file/protocol.md` states three facts that matter:

- `intake.db` is the authoritative escalation record. The exports are convenience
  copies, and they can be incomplete.
- One person can use more than one handle. The `identities` record maps each
  escalated handle to a person. Reconcile by person, not by handle.
- The watch list has never been reconciled against that record.

## Step 1 — get the escalated subjects from the database

Open `dist/case_file/intake.db` in a SQLite viewer (DB Browser for SQLite, free and
cross-platform). Open the `escalations` table. It holds 58 rows. Sort by the `handle`
column. Twelve distinct handles have an escalation.

## Step 2 — compare to the watch list

Open `dist/case_file/watchlist.csv` in a spreadsheet. It holds eight names. Four
escalated handles are not on the watch list:

```
HALCYONLEAKS
still_water_77
ash_over_halcyon
trial7_mom
```

The prompt says two subjects are missing. Four candidate handles therefore need
identity reconciliation: two of these are not new people.

## Step 3 — resolve identities

Open the `identities` table. Sort by `person_id`. Two of the four candidates share a
person with a handle that is already on the watch list:

```
person_id  handle                 is_primary
P01        BURN_HALCYON_DOWN      1     <- on the watch list
P01        ash_over_halcyon       0     <- same person, an alias
P04        PatriciaK_Trial7       1     <- on the watch list
P04        trial7_mom             0     <- same person, an alias
```

`ash_over_halcyon` is `BURN_HALCYON_DOWN`. `trial7_mom` is `PatriciaK_Trial7`. Both
people are already logged, under their main handle. They are not missing. Drop them.

The alias posts say so as well, if you read them. `ash_over_halcyon` writes "They
banned BURN_HALCYON_DOWN so here I am again." `trial7_mom` writes "as PatriciaK." The
`identities` table is the authoritative confirmation.

Two candidates remain, and neither has an alias:

```
HALCYONLEAKS
still_water_77
```

## The trap — stopping at the export

The forum export is the big, obvious file. If you work only from it, two things go
wrong. First, `still_water_77` never shows an escalation there. It was escalated one
time only, as `INT-2026-0091`, and that record survives only in `intake.db`. Its
forum post carries no flag, and the mailbox has no notice for it. Second, the export
still shows the two aliases, so a naive count off the export gives three candidates,
an incomplete set that includes two already-listed people. Go to the authoritative
record, and resolve by person.

The database-only escalation reproduces "No update from my end." The protocol
explains that the reproduced message may not contain the full reason for an intake
decision. The task is to reconcile recorded escalations, not reassess message content.

## Optional — the same result with a query

You can get the same answer with SQL, if you prefer it:

```bash
sqlite3 dist/case_file/intake.db \
  "SELECT DISTINCT lower(p.handle) AS handle FROM escalations e
   JOIN identities i ON e.handle = i.handle
   JOIN identities p ON p.person_id = i.person_id AND p.is_primary = 1
   WHERE i.person_id NOT IN (
     SELECT person_id FROM identities WHERE handle IN (SELECT handle FROM watchlist))
   ORDER BY lower(p.handle);"
```

This returns the two primary handles in lowercase alphabetical order. The database
watch list contains the same handles as the CSV, so the whole comparison can also
be completed in a SQLite viewer.

A naive `SELECT DISTINCT handle FROM escalations EXCEPT SELECT handle FROM watchlist`
returns four handles — it does not resolve identities, so it is wrong. This is a
convenience, not the intended path.

## The flag

Write both handles in lower case. Sort them alphabetically. Join them with an
underscore, preserving underscores already inside each handle:

```
csaw{halcyonleaks_still_water_77}
```

## The lesson

This challenge teaches three beginner habits: read the records instructions, choose
the authoritative source, and resolve identity before comparing people. It is an
OSINT/data-triage exercise; SQL, jq, and reading the communications are optional.

## Common pitfalls

- Stopping at the forum export. You miss `still_water_77`, and you keep the aliases.
  The prompt's stated count of two missing subjects signals that your candidate
  set needs more work.
- Counting handles, not people. The naive diff returns four handles. Two are aliases
  of logged people. Resolve identity and the count falls to two.
- Diffing the `handles` table instead of `escalations`. That gives more than 40 minus
  8, which is far too many. Participation is not the same as an escalation.
- Trusting the watch list. It lags on purpose, and the protocol says so.
- Ordering the flag by post count or by date. The flag format is alphabetical.
- Rabbit holes, by design. `dm_export.json` holds 290 messages from loud non-answer
  handles. `posting_activity.csv` invites you to plot who went quiet, but several
  noise handles (`SaltmarshHydro`, `downstream_dan`, `seraph_index`) also trail off,
  so the timeline points nowhere. Neither file marks a subject. Only `intake.db` does.

## Notes

Difficulty: Easy. The identity step is an explicit table lookup, supported by alias
posts. A guided artifact review verified the intended result; blind beginner
playtesting is still needed to calibrate solve time and navigation difficulty.

Distribute only `dist/` to players. Keep `WU/solve.md` with the reviewer materials.

Every subject, message, and organization in this challenge is invented. No real
person or company is represented.
