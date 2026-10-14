---
name: promptlingo
description: Analyzes the user's daily Claude Code and Codex conversations and produces an Obsidian-flavored English-learning report (vocabulary, grammar focus, sentence improvement, sentence rewrites, i+1 article, spaced review). Triggered when the user runs /promptlingo or /promptlingo YYYY-MM-DD.
argument-hint: "[YYYY-MM-DD]"
allowed-tools: Bash(uv *) Bash(cat *) Read Write
model: haiku
---

# promptlingo

Read JSONL transcripts from Claude Code (`~/.claude/projects/`) and Codex (`~/.codex/sessions/`), filter noise, and generate study material calibrated to the user's CEFR level. Output is Obsidian-flavored Markdown written to `LEARNING_DIR`; point it into an Obsidian vault so reports, vocab, and patterns are browsable, searchable, and linkable.

## Invocation

- `/promptlingo` — analyze today
- `/promptlingo 2026-04-25` — analyze a specific ISO-8601 date

## Paths

Let `SKILL_DIR` be the directory of this file. The scripts read paths from `scripts/paths.py`:

- `LEARNING_DIR` = `$PROMPTLINGO_LEARNING_DIR` if set, else `$SKILL_DIR/learning/`
- Reports → `$LEARNING_DIR/reports/<DATE> English Daily.md`
- Vocab JSON (SRS state) → `$LEARNING_DIR/data/vocab.json`
- Patterns JSON (grammar categories) → `$LEARNING_DIR/data/patterns.json`
- Glossary notes → `$LEARNING_DIR/glossary/Glossary <LEVEL>.md` + `Glossary Index.md`
- Grammar notes → `$LEARNING_DIR/grammar/<中文分類名>.md`

> [!important] Notes are aggregates, never one file per item
> There is **one note per CEFR level** and **one note per grammar category** — never a
> note per word or per sentence. `store.py` rebuilds every note from the JSON on each
> run, so the JSON is the single source of truth. Never write a note by hand.

## Steps

Let `DATE_ARG` be the user's second token (empty if none).

### 1. Read config

```bash
cat "$SKILL_DIR/config.json"
```

Hold onto `level` (CEFR) and `native_lang` (default `zh-TW`). Use `native_lang` for explanations.

### 2. Load and clean turns

```bash
uv run "$SKILL_DIR/scripts/transcript_loader.py" $DATE_ARG
```

Returns `{date, sources, stats, turns}`. Each turn carries `project` (cwd-encoded, shared by both agents), `cwd` and `agent` (`claude-code` or `codex`). If `stats.stage3_turns == 0`, tell the user there's nothing to analyze and stop.

### 2.5 Narrow bundle (Krashen narrow input)

Group `turns` by `project`. Pick the project with the most user turns as `topic_project`; collect those turns as `topic_turns`. Tie-break by most-recent turn. Infer a short `topic_label` from the dominant subject — don't invent topics not in the turns.

### 2.6 Spaced review query

```bash
uv run "$SKILL_DIR/scripts/due.py" $DATE_ARG --limit=5
```

Returns `{today, due: [{word, cefr, zh, last_seen, count, interval, days_overdue, examples}]}`. Hold this list as `review_words`. Weave them into the article (step 4) and surface in section 3.5.

### 3. Per-language analysis

Use `config.level` as baseline; `native_lang` for explanations.

**3a. Sentence rewrites (Chinese → English)**
Filter `lang == "zh"` and `role == "user"`. Pick up to 5 high-value sentences. Give one English rewrite at exactly `config.level` per sentence.

**3b. Sentence improvement (English user prompts)**
Filter `lang == "en"` and `role == "user"`. **Drop fragments and quick imperatives** (under ~5 words OR one-clause imperative with no detail worth correcting — `ok`, `commit it`, `fix it`, `go`, `do it`, `thanks`). Only critique full sentences where grammar / word choice / naturalness matter. If nothing qualifies, skip the section with a `> [!tip]` callout — don't emit an empty table.

**3c. Vocabulary extraction (assistant first, user second)**
Pull 8–15 words.

- **Hard filter: only at or above `config.level`.** Drop easier words.
- Drop programming jargon, variable names, file paths, brand names, proper nouns.
- Each entry: `{word, cefr, zh, pos, examples, synonyms, antonyms}`. `pos` is part-of-speech (`n.`, `v.`, `adj.`, etc.).

**3d. Grammar focus (overall)**
Pick 1–3 grammar points. For each: one example pulled from the day plus one contrast example.

**3e. Assign every pattern a category and a kind**

Each item from 3a + 3b becomes `{category, kind, point, user_wrote, correction}`.

`category` — pick exactly one slug:

| slug                          | 中文分類         | 收什麼                                      |
| ----------------------------- | ---------------- | ------------------------------------------- |
| `articles-and-determiners`    | 冠詞與限定詞     | a / an / the、all the same、漏冠詞          |
| `agreement-and-number`        | 主謂一致與單複數 | a lot of + 複數、these ... need             |
| `tense-and-aspect`            | 時態             | 現在完成式、過去式、resume 用的動詞形       |
| `passive-voice`               | 被動語態         | be + p.p.、needs to be done                 |
| `questions`                   | 疑問句與間接問句 | 助動詞、whether / if、選擇疑問句            |
| `word-form`                   | 詞性與構詞       | clean up / cleanup、connect / connection    |
| `sentence-boundaries`         | 句子切分         | run-on、逗號黏接、命令與疑問混在一句        |
| `spelling-and-typography`     | 拼字與排版       | typo、括號前空格                            |
| `requests-and-instructions`   | 提出要求與下指令 | 祈使句、授權、劃出禁區                      |
| `contrast-and-alternatives`   | 對比與取捨       | X rather than Y、instead of、why not        |
| `conditions-and-consequences` | 條件、時間與後果 | if / until / since / or we'll               |
| `inquiry-and-assessment`      | 探詢與評估       | assess whether、what risks does that expose |

If nothing fits, use `other` — do not invent a slug.

`kind` — `error` if the user wrote English wrongly; `phrase` if it is a wording worth
acquiring (this includes a Chinese sentence rewritten into model English).

`point` — **name the language feature, never the task.** This is the accumulator key:
the same `point` string seen again raises its count, which is the whole learning signal.

- Good: `疑問句缺助動詞` · `用 rather than 表達取捨` · `article before consonant sound: an -> a`
- Bad: `proxy_headers strips auth header on SSO redirect` · `three-layer model of software work`
  — those describe the work, not the language. Retitle them by their construction.
- Never put the raw sentence in `point`. The sentence goes in `user_wrote`.

`user_wrote` — the original (Chinese sentence, or the user's wrong English).
`correction` — the model English sentence.

**3f. Sophisticated English upgrades**
Pick 2–3 of the user's English sentences (or 3a rewrites) that are already correct but plain. For each, give one upgrade one notch above `config.level`: a more precise verb, a natural collocation, a hedged or diplomatic tone, or a tighter structure. Name the technique in a short label (e.g. `精準動詞`, `委婉語氣`, `名詞化`). Reject pretentious upgrades — if a native engineer would not say it in a PR or Slack thread, drop it. Report-only; do not add these to `patterns`.

### 4. Generate the i+1 short article

Write **one short article, ~150 words**, at `config.level`. Hard rules:

- **Topic = `topic_label`** from step 2.5.
- **Comprehension target ≥ 95%**: at most 5% of word tokens above `config.level`.
- **Massed repetition**: every word from step 3c appears at least once; on-level words twice in different sentences.
- **Spaced repetition**: weave 3–5 of `review_words` naturally — don't list them.
- **Style**: third-person narrative recap; past or present perfect tense.
- **Glossing**: any above-level word gets inline `(中文)` first occurrence.

Output: a single paragraph plus a 2-line `> Coverage: vocab X/X · review Y/5` footer.

### 5. Persist

Build:

```json
{
  "date": "<YYYY-MM-DD>",
  "vocab": [
    {
      "word": "...",
      "cefr": "...",
      "zh": "...",
      "pos": "...",
      "examples": [],
      "synonyms": [],
      "antonyms": []
    }
  ],
  "patterns": [
    {
      "category": "questions",
      "kind": "error",
      "point": "疑問句缺助動詞",
      "user_wrote": "ci failed?",
      "correction": "Did CI fail?"
    }
  ],
  "reviewed": ["...the review_words surfaced in 3.5"]
}
```

`reviewed` = the `word` of every `review_words` entry you surfaced in section 3.5.
Surfacing a word IS one spaced-repetition rep, so `store.py` promotes its Leitner box
(`count += 1`, `last_seen = today`) — this is what stops the same overdue words from
reappearing every day. Omit / leave empty only if section 3.5 had no words.

Then:

```bash
uv run "$SKILL_DIR/scripts/store.py" <<'PLJSON'
<the json above>
PLJSON
```

> [!warning] 用 heredoc,不要 `echo '...' |`
> payload 裡的英文縮寫(`don't`、`it's`)和使用者引號含單引號,用 `echo '...'` 會截斷 shell 字串、腐化 JSON。上面的 quoted heredoc(`<<'PLJSON'`)不做任何展開,單引號原樣送進 stdin。

`store.py` is idempotent (a word or a `point` already touched today is not advanced
twice, so re-running a date is safe). It updates `vocab.json` / `patterns.json`,
advances the reviewed words, then **rebuilds every glossary and grammar note in full**
from the JSON. `grammar.base` indexes the grammar notes; `Glossary Index.md` is the
all-levels word table.

Check the returned summary. A `warning` field means a `category` slug was not on the
list above and the items landed in `other` — fix the slug and re-run that date.

To regenerate every note from JSON without merging new data:

```bash
uv run "$SKILL_DIR/scripts/store.py" --rebuild-notes
```

### 6. Write the daily report

Write Markdown to `$LEARNING_DIR/reports/<DATE> English Daily.md`.

Read `references/report-template.md` (relative to `SKILL_DIR`) — it holds the exact
frontmatter, the Obsidian-flavored section skeleton (no H1), and the hard rules for
each section. Fill every `<placeholder>` and follow those rules.

### 7. Echo a short summary in chat

Output:

- `topic_label`
- top 3 takeaways
- report path
- the `obsidian://` link from `uv run "$SKILL_DIR/scripts/paths.py" --open-url <DATE>` — 一鍵打開. If it prints nothing, `LEARNING_DIR` is not inside an Obsidian vault; skip the link.

Don't paste the full report or the i+1 article.

---

## Adjust level

Edit `config.json` `level` to A1 / A2 / B1 / B2 / C1 / C2.
