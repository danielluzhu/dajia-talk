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

The entire app is one file, [`dajia-talks.html`](dajia-talks.html) — no build
step, no server, no dependencies. It is deployed as a Claude Artifact with the
`artifact` runtime capability: the page embeds its state (members, answers,
reactions) as JSON and saves a new version of itself whenever someone answers,
so everyone who opens the shared link sees the same living record.

Live app: https://claude.ai/code/artifact/f7f71fac-1f33-4e54-806d-012c9b99c0e9

To update the deployed app, edit `dajia-talks.html` and republish it to that
artifact URL (e.g. ask Claude Code to publish the file with the artifact's URL).

## Local preview

```bash
python3 -m http.server 8123
```

Then open <http://localhost:8123/dajia-talks.html>. Outside the claude.ai
runtime the page runs in preview mode (changes stay on the device); use the
"explore a sample family" button on the setup screen to see every state —
sealed answers, the countdown, poll reveals, and free-form reveals — with
demo data.

## Structure of `dajia-talks.html`

- `<style>` — token-based theming (light + dark via `prefers-color-scheme`
  and explicit `data-theme` stamps)
- `<script type="application/json" id="state">` — the embedded shared state
- The main script:
  - `QBANK` — the 60-question bank; the day's question is picked
    deterministically from the date, then snapshotted into the day's record
  - `famParts()` / `isUnlocked()` — the family-clock timezone logic and the
    "everyone answered or 6 PM" reveal rule
  - `computeTrends()` — the shared-word analysis for free-form reveals
  - render functions per view (today, archive, family, setup) and a
    delegated click handler for all actions
