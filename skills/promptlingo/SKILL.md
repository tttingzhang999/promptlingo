---
name: promptlingo
description: Analyze the user's daily Claude Code conversations and produce an English-learning report (vocabulary, grammar focus, sentence improvement, sentence rewrites). Triggered when the user runs /promptlingo or /promptlingo YYYY-MM-DD.
argument-hint: "[YYYY-MM-DD]"
disable-model-invocation: true
allowed-tools: Bash(python3 *) Bash(cat *) Read Write
---

# promptlingo

Read JSONL transcripts from `~/.claude/projects/`, filter noise, and generate study material calibrated to the user's CEFR level.

## Invocation

- `/promptlingo` — analyze today
- `/promptlingo 2026-04-25` — analyze a specific ISO-8601 date

## Steps

Let `SKILL_DIR` be the directory of this file. Let `DATE_ARG` be the user's second token (empty if none).

### 1. Read config

```bash
cat "$SKILL_DIR/config.json"
```
Hold onto `level` (CEFR) and `native_lang` (default `zh-TW`). Use `native_lang` for explanations to the user.

### 2. Load and clean turns

```bash
python3 "$SKILL_DIR/scripts/transcript_loader.py" $DATE_ARG
```

Returns `{date, sources, stats, turns}`. Each turn carries `project` (the `~/.claude/projects/<dir>` tag — encodes cwd) and `cwd` (raw cwd if the JSONL recorded it). If `stats.stage3_turns == 0`, tell the user there's nothing to analyze and stop.

### 2.5 Narrow bundle (Krashen narrow input)

Group `turns` by `project`. Pick the project with the **most user turns** as today's `topic_project`; collect those turns as `topic_turns`. They form the "narrow input" used by the i+1 article in step 4. Other projects still feed steps 3a–3d but won't drive the article. Tie-break by most-recent turn.

Infer a short `topic_label` from the dominant subject of `topic_turns` (e.g. "Sinopac connection resilience"). Don't invent topics that aren't in the turns.

### 2.6 Spaced review query

```bash
python3 "$SKILL_DIR/scripts/due.py" $DATE_ARG --limit=5
```

Returns `{today, due: [{word, cefr, zh, last_seen, count, interval, days_overdue, examples}]}`. Hold this list as `review_words` — vocab from prior days that have hit their spaced-repetition interval (Leitner: 1/3/7/14/30 days). Weave them into the article (step 4) and surface them in the report (step 6).

### 3. Per-language analysis

Use `config.level` as the baseline; `native_lang` for all glosses and explanations.

**3a. Sentence rewrites (Chinese → English)**
Filter `lang == "zh"` and `role == "user"`. Pick up to 5 sentences with the highest learning value. For each, give **one** English rewrite at exactly `config.level` (not multiple levels). The CEFR-level filter applies only to vocabulary (3c), not to sentence rewrites.

**3b. Sentence improvement (English user prompts)**
Filter `lang == "en"` and `role == "user"`. **First drop fragments and quick imperatives** that are not real sentences — e.g. "ok", "commit it", "fix it for me", "go", "do it", "thanks". Rule of thumb: skip if the line is under ~5 words OR is a one-clause imperative with no detail worth correcting (the agent will understand it; that's enough). Only critique full sentences where grammar / word choice / naturalness actually matter. For each kept sentence give the corrected version plus a brief explanation in `native_lang`.

**3c. Vocabulary extraction (assistant first, user second)**
Pull 8–15 words worth learning.
- **Hard filter: only include words at or above `config.level`.** Drop anything easier (e.g. for B2: skip A1/A2/B1 words). Mix of on-level and one-level-up words is good.
- Drop programming jargon, variable names, file paths, brand names, proper nouns.
- Each entry: `{word, cefr, zh, examples: [real sentence(s) from the conversation]}`. If a worthy word never appeared verbatim, you may invent an example — but tag CEFR honestly.

**3d. Grammar focus (overall)**
Pick 1–3 grammar points worth remembering (inversion, subjunctive, present perfect vs past simple, etc.). For each: one example pulled from the day's conversation plus one contrast example.

### 4. Generate the i+1 short article (Krashen comprehensible input)

Write **one short article, ~150 words**, at `config.level` (e.g. B2). Hard rules:

- **Topic = `topic_label`** from step 2.5. Stay narrowly inside that domain so vocab recycles naturally.
- **Comprehension target ≥ 95%**: at most 5% of words may be above `config.level`. Counted by tokens, not types.
- **Massed repetition**: every word from `vocab` (step 3c) must appear at least **once** in the article. High-priority words (CEFR == `config.level`) should appear **twice** in different sentences.
- **Spaced repetition**: weave in 3–5 of `review_words` from step 2.6, naturally — don't list them.
- **Style**: third-person narrative recap of what the developer did, not instructions. Past or present perfect tense for completed work.
- **Glossing**: any word above `config.level` (≤ 5% allowed) gets an inline `(中文)` parenthetical the first time it appears.

Output: a single paragraph plus a 2-line `> Coverage: vocab X/X · review Y/5` footer you compute yourself.

### 5. Persist

Build:

```json
{ "date": "<YYYY-MM-DD>", "vocab": [...from 3c], "patterns": [...from 3a+3b] }
```

Then:

```bash
echo '<the json above>' | python3 "$SKILL_DIR/scripts/store.py"
```

`store.py` is idempotent — re-running the same day bumps counts and refreshes `last_seen`.

### 6. Write the daily report

Write Markdown to `$SKILL_DIR/data/reports/<DATE>/summary.md`:

```markdown
# English daily — <DATE>

> Level: B2 · sessions: N · turns analyzed: M · topic: <topic_label>

## 0. Today's i+1 article (~150 words)
<the article from step 4, then its Coverage footer>

## 1. Sentence rewrites (中→英)         ← B2 only, single column
## 2. Sentence improvement              ← skip if no full sentences worth correcting
## 3. Today's vocabulary                ← table: 單字 / 中文 / 詞性 / 例句 / 同義字 / 反義字 (no CEFR column)
## 3.5 Spaced review (from prior days)  ← table from review_words: 單字 / 上次出現 / 間隔 / 例句
## 4. Grammar focus
## 5. Slang / idioms
## Summary
```

Section bodies in `native_lang`; English examples preserved.

### 7. Echo a short summary in chat

Output: today's `topic_label`, the top 3 takeaways, and the report path. Do not paste the full report or the article.

---

## Install

Clone this repo, then symlink the skill into your Claude config:

```bash
git clone https://github.com/<your-username>/promptlingo.git
cd promptlingo
ln -s "$(pwd)/skills/promptlingo" ~/.claude/skills/promptlingo
```

## Adjust level

Edit `config.json` `level` to one of A1 / A2 / B1 / B2 / C1 / C2.
