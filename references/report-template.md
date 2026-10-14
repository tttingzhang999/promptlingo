# Daily report template

The Markdown skeleton and hard rules for `$LEARNING_DIR/reports/<DATE> English Daily.md`
(step 6 of `SKILL.md`). Fill every `<placeholder>`; no H1 (Obsidian uses the filename).

## Skeleton

````markdown
---
date: <YYYY-MM-DD>
level: <B2>
topic: <topic_label>
sessions: <N>
turns_analyzed: <M>
vocab_count: <len(vocab)>
review_count: <len(review_words)>
tags: [english-daily, level/<B2>]
---

```table-of-contents

```

> [!info] 今日重點
> **Topic:** <topic_label>
> **Level:** <B2> · **Sessions:** <N> · **Turns:** <M>
> **Vocab covered:** <len(vocab)>/<len(vocab)> · **Review:** <len(review)>/5

## 0. i+1 Article (~150 words)

> [!example] Comprehensible Input — <topic_label>
> <article paragraph; preserve inline glosses (中文)>
>
> Coverage: vocab X/X · review Y/5

## 1. Sentence Rewrites (中→英)

| 中文原句 | <Level> 英文改寫 |
| -------- | ---------------- |
| ...      | ...              |

## 2. Sentence Improvement

> [!tip] 練習建議
> 今日英文輸入大多為短指令，文法層面沒有需要改寫的完整句子。練習把短指令改寫成完整句。

（若有完整句要改，改用一張 table；不要既給 callout 又給空 table。）

## 3. Today's Vocabulary

| 單字                         | 中文 | 詞性 | 例句 | 同義字     | 反義字    |
| ---------------------------- | ---- | ---- | ---- | ---------- | --------- |
| [[Glossary B2#drift\|drift]] | 偏移 | n.   | ...  | divergence | alignment |

> 點單字跳到該 CEFR 等級檔的對應段落，可看完整 SRS 狀態與所有出現過的例句。

## 3.5 Spaced Review (Leitner SRS)

> [!todo] 今日複習
> 5 個逾期單字，請在文章 / 對話中找它們的蹤跡。

| 單字                                 | 上次出現   | 間隔                | 例句 |
| ------------------------------------ | ---------- | ------------------- | ---- |
| [[Glossary B2#compliant\|compliant]] | 2026-04-27 | 1 天（已逾期 2 天） | ...  |

## 4. Grammar Focus

> [!note] 4.1 <grammar point>
>
> - 分類：[[<中文分類名>]]
> - 規則：...
> - 例句：...
> - 對比：...

## 4.5 Sophisticated English

| 原句                                   | 升級版                                                      | 技巧     | 為什麼更好                     |
| -------------------------------------- | ----------------------------------------------------------- | -------- | ------------------------------ |
| This problem is big, we need fix fast. | This issue is significant and warrants immediate attention. | 精準動詞 | warrant 比 need 更正式、更精準 |

## 5. Slang / Idioms

- **<idiom>** — <gloss>（例：...）

## Summary

<3–5 行總結。>

---

延伸：[[promptlingo]] · [[english-board]] · 上一份 [[<PREV_DATE> English Daily]]
````

## Hard rules

- **Vocab table 第一欄一律用 wikilink** `[[Glossary <CEFR>#<word>|<word>]]`，`<CEFR>` 取該字的等級。
  單字沒有獨立筆記了，連結指向等級檔內該字的 `###` 段落。
- **Spaced review 同樣用這個形式**連單字段落。
- 開頭 `> [!info]` callout 取代純 blockquote header。
- 若 sentence improvement 沒料，**用 callout 收尾，不要塞空 table**。
- 上一份 report 檔名 = `vocab.json` 中 `last_seen` 不等於今天的最大日期；找不到就省略「上一份」連結。
- Sophisticated English 只收「已正確但平淡」的句子，升級幅度最多高 `config.level` 一級；不自然或做作的說法不要收。
- Grammar point 一律用 `> [!note]` callout，並連到它的分類筆記 `[[<中文分類名>]]`（見 SKILL.md 的分類表）。
