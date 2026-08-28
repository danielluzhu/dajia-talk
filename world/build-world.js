#!/usr/bin/env node
// Builds the Dajia Talks "world panel": expands the authored answer corpus to
// 100 faux panelists per question, computes each question's digest (sentiment
// mix, themes, common words, representative quotes), and writes JSONEachRow
// files for ClickHouse (world_answers.jsonl, world.jsonl). Deterministic:
// fixed RNG seed, so rebuilding produces the same panel.
"use strict";
const fs = require("fs");
const path = require("path");

const DIR = __dirname;
const NAMES = JSON.parse(fs.readFileSync(path.join(DIR, "names.json"), "utf8"));
const POLLS = JSON.parse(fs.readFileSync(path.join(DIR, "polls.json"), "utf8"));

// QBANK poll option texts, needed for the world "line" per poll.
const html = fs.readFileSync(path.join(DIR, "..", "index.html"), "utf8");
const bankSrc = html.match(/var QBANK = \[([\s\S]*?)\n\];/)[1];
const QBANK = new Function("return [" + bankSrc + "]")();

const AUTHORED = {};
for (const f of ["authored-a.json", "authored-b.json", "authored-c.json"]) {
  Object.assign(AUTHORED, JSON.parse(fs.readFileSync(path.join(DIR, f), "utf8")));
}

// mulberry32 — small deterministic RNG
function rng(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const STOP = new Set(("the a an and or but if then than that this those these i you he she it we they them his her my your our their of in on at to for with from by about as is are was were be been being am do does did have has had not no yes so just very really too also there here when what who whom whose which why how all any some one two few more most other own same its im dont didnt cant wont isnt thats youre were theyre will would can could should shall may might must out up down over under again once because while during before after above below off only still ever never always sometimes lot bit thing things stuff way ways got get gets getting go goes going went come came like even much many back now new old good great little every each it's don't didn't can't won't isn't that's you're we're they're").split(" "));

function words(text) {
  const out = [];
  for (let w of (text.toLowerCase().match(/[a-zÀ-ɏ'-]{3,}/g) || [])) {
    w = w.replace(/^['-]+|['-]+$/g, "").replace(/'/g, "");
    if (w.length >= 3 && !STOP.has(w)) out.push(w);
  }
  return out;
}

const SENTIMENT_LINE = {
  warm: "Mostly warm answers out there",
  funny: "The world mostly joked its way through this one",
  wistful: "A wistful one, around the world",
  thoughtful: "The world got thoughtful on this one"
};

const answersRows = [];
const digestRows = [];
const rand = rng(20260828);

function shuffled(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// ---- free-form questions ----
for (const [qiStr, authored] of Object.entries(AUTHORED)) {
  const qi = +qiStr;
  const weights = authored.map(() => 1 + rand() * 2.2);
  const totalW = weights.reduce((a, b) => a + b, 0);
  const panelNames = shuffled(NAMES);
  const sample = []; // per panelist: authored index
  for (let p = 0; p < 100; p++) {
    let r = rand() * totalW, idx = 0;
    while (r > weights[idx]) { r -= weights[idx]; idx++; }
    sample.push(idx);
    answersRows.push({ q: qi, name: panelNames[p], kind: "free", choice: -1, text: authored[idx].text });
  }
  const s = { warm: 0, funny: 0, wistful: 0, thoughtful: 0 };
  const themeCount = {}, wordCount = {}, perAnswer = {};
  sample.forEach((idx, p) => {
    const a = authored[idx];
    s[a.s]++;
    (perAnswer[idx] = perAnswer[idx] || []).push(panelNames[p]);
    for (const t of a.t) themeCount[t] = (themeCount[t] || 0) + 1;
    for (const w of words(a.text)) wordCount[w] = (wordCount[w] || 0) + 1;
  });
  const themes = Object.entries(themeCount).sort((a, b) => b[1] - a[1]).slice(0, 5);
  const topWords = Object.fromEntries(Object.entries(wordCount).sort((a, b) => b[1] - a[1]).slice(0, 40));
  // quotes: the most-picked answer of three different sentiments
  const bySent = {};
  Object.entries(perAnswer).forEach(([idx, names]) => {
    const a = authored[+idx];
    if (!bySent[a.s] || bySent[a.s].names.length < names.length) bySent[a.s] = { idx: +idx, names };
  });
  const quotes = Object.values(bySent)
    .sort((a, b) => b.names.length - a.names.length).slice(0, 3)
    .map(({ idx, names }) => ({ name: names[0], text: authored[idx].text, s: authored[idx].s }));
  const topSent = Object.entries(s).sort((a, b) => b[1] - a[1])[0][0];
  const line = SENTIMENT_LINE[topSent] +
    (themes.length >= 2 ? ` — '${themes[0][0]}' and '${themes[1][0]}' came up again and again.` : ".");
  digestRows.push({ q: qi, digest: JSON.stringify({ type: "free", n: 100, s, themes, words: topWords, quotes, line }) });
}

// ---- poll questions ----
for (const [qiStr, votes] of Object.entries(POLLS)) {
  const qi = +qiStr;
  const opts = QBANK[qi].o;
  if (votes.length !== opts.length || votes.reduce((a, b) => a + b, 0) !== 100) {
    throw new Error(`poll ${qi}: bad distribution`);
  }
  const panelNames = shuffled(NAMES);
  let p = 0;
  votes.forEach((n, choice) => {
    for (let k = 0; k < n; k++) {
      answersRows.push({ q: qi, name: panelNames[p++], kind: "poll", choice, text: "" });
    }
  });
  const max = Math.max(...votes);
  const leaders = votes.map((v, i) => [v, i]).filter(([v]) => v === max).map(([, i]) => i);
  const line = leaders.length > 1 || max <= 52
    ? "The world is split almost down the middle on this one."
    : `The world leans '${opts[leaders[0]]}' — ${max} of 100.`;
  digestRows.push({ q: qi, digest: JSON.stringify({ type: "poll", n: 100, votes, line }) });
}

fs.writeFileSync(path.join(DIR, "world_answers.jsonl"), answersRows.map(r => JSON.stringify(r)).join("\n") + "\n");
fs.writeFileSync(path.join(DIR, "world.jsonl"), digestRows.map(r => JSON.stringify(r)).join("\n") + "\n");
console.log(`built: ${answersRows.length} panel answers, ${digestRows.length} digests`);
