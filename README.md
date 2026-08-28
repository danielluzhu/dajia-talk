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

On the open web the app stores each family room in a Firebase Realtime
Database, spoken to over plain REST — no SDK, no build step. Every room has an
unguessable id; the invite link (`…/#r=<id>`) is the only key, like a
"anyone with the link" document. Members join by opening the link and typing
their name — no accounts. Answers sync live (server-sent events, with polling
as fallback), and saves merge onto the freshest copy so simultaneous answers
never overwrite each other.

One-time setup (~5 minutes, free):

1. Go to https://console.firebase.google.com and add a project (Analytics not
   needed).
2. In the project: **Build → Realtime Database → Create database**, any
   location, **locked mode**.
3. In the database's **Rules** tab, replace the rules with:

   ```json
   { "rules": { "rooms": { "$room": { ".read": true, ".write": true } } } }
   ```

   This makes individual rooms readable/writable only by whoever knows the
   room id (the invite link), and nothing else.
4. Copy the database URL shown at the top of the data view (it looks like
   `https://<project>-default-rtdb.firebaseio.com`).
5. In `index.html`, set it on the `var DB_URL = ""` line, commit, push.

Privacy: anyone who has a room's invite link can read and write that room —
that is the sharing model. Treat invite links like you'd treat a private group
chat link, and don't post them publicly.

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
