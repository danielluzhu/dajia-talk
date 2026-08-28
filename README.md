# Dajia Talks

One question a day, answered by the whole family.

Dajia Talks is a daily-question app for a family spread across the world. Every
day, everyone gets the same question — a food debate, a fond memory, a
would-you-rather. Answers stay sealed until the whole family has answered, or
until 6:00 PM on the shared "family clock", whichever comes first. Then the
table opens:

- **Polls** reveal the global vote breakdown — counts, percentages, and who
  voted for what, by name.
- **Free-form questions** reveal everyone's answers as letters, plus a
  "Common threads" card highlighting words that came up across multiple
  people.
- After the reveal, anyone can react (❤️ 😂 🥹) to an answer, and every past
  day stays browsable in the archive.

## How it runs

The entire app is one file, [`index.html`](index.html) — no build step, no
framework, no dependencies. Hosted on the open web it uses **family rooms**
(below); inside the claude.ai artifact runtime it instead uses the `artifact`
capability to save new versions of itself, one family per artifact.

Live app (GitHub Pages): https://danielluzhu.github.io/dajia-talk/ — start a
family room, share the invite link, and family joins with just the link and
their own name. Requires the one-time database setup below; until then the
page offers the sample family.

There is also a claude.ai artifact deployment
(https://claude.ai/code/artifact/f7f71fac-1f33-4e54-806d-012c9b99c0e9) where
the page saves itself instead of using rooms — one family per artifact, shared
via claude.ai.

## Family rooms

On the open web the app stores each family room as a row in a ClickHouse Cloud
table (`dajia.rooms`, a ReplacingMergeTree keyed by room id — every save is a
new row, reads use `FINAL` for the latest). The page talks to the service's
HTTPS interface directly with CORS-simple requests — no SDK, no build step.
Every room has an unguessable id; the invite link (`…/#r=<id>`) is how family
finds it. Members join by opening the link and typing their name — no
accounts. Rooms sync by polling every 10 s (plus on tab focus), and saves
merge onto the freshest copy so simultaneous answers never overwrite each
other.

One-time setup, from this repo:

```bash
CH_URL="https://<service>.clickhouse.cloud:8443" \
CH_ADMIN_USER="default" \
CH_ADMIN_PASSWORD="..." \
./setup-clickhouse.sh
```

The script creates the database/table plus a sandboxed `dajia_app` user with a
random password, and prints the `BACKEND` line to paste into `index.html`.
Admin credentials are used only by the script and never appear in the page.

Security model, stated plainly: the `dajia_app` password ships inside the
public page — that is unavoidable for a serverless static app. The user is
correspondingly boxed in: it can only `SELECT` and `INSERT` on `dajia.rooms`
(no ALTER/DROP/TRUNCATE, no other tables), result rows and execution time are
capped, and a per-IP hourly quota limits abuse. Consequences to accept: anyone
who reads the page source could list rooms in the table or append junk rows.
Treat invite links like a private group-chat link, and don't use rooms for
secrets. If that tradeoff isn't acceptable, the `rest` adapter still supports
a Firebase Realtime Database (`BACKEND = {type:"rest", url:"https://<project>-
default-rtdb.firebaseio.com"}`) whose rules can hide the room list.

## Local development

```bash
python3 dev-server.py
```

serves the app at <http://localhost:8123> with an in-memory mock of the
database endpoints, so the whole create/join/answer flow works locally with no
Firebase project.

The "explore a sample family" button on the landing screen shows every state —
sealed answers, the countdown, poll reveals, free-form reveals — with demo
data, no database needed.

## Structure of `index.html`

- `<style>` — token-based theming (light + dark via `prefers-color-scheme`
  and explicit `data-theme` stamps)
- `<script type="application/json" id="state">` — the embedded shared state
- The main script:
  - `QBANK` — the 60-question bank; the day's question is picked
    deterministically from the date, then snapshotted into the day's record
  - `famParts()` / `isUnlocked()` — the family-clock timezone logic and the
    "everyone answered or 6 PM" reveal rule
  - `computeTrends()` — the shared-word analysis for free-form reveals
  - the rooms layer — `apiLoad`/`apiSave` (Firebase REST), `mergeRoom`
    (conflict-safe saves), `startSync` (live updates via EventSource, polling
    fallback), and the create/join screens
  - render functions per view (landing, join, today, archive, family, setup)
    and a delegated click handler for all actions
