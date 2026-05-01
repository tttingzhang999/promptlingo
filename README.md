# promptlingo

啟發自語言學家 Stephen Krashen 提出的 Comprehensible Input 理論，我認為要有效學習一門語言，有幾個關鍵方向：

- **i+1 原則** — 找到略高於目前程度的內容，既能理解又有挑戰
- **多模態輸入** — 結合聽覺、視覺甚至觸覺，加深語言與概念、想法之間的連結
- **Shadowing** — 跟讀模仿，內化語感並提升口說流暢度
- **環境** — 持續處在目標語言環境中，並嘗試用該語言思考

而我希望透過這個工具達成的目標：

1. 能用英文敘述軟體工程領域的內容
2. [最大程度發揮 Coding Agent 的能力](https://arxiv.org/abs/2305.07004)
3. 遇到 Coding Agent 無法解決的問題時，能為自己找到正確的 Context 與切入點

軟體工程領域中，我們經常需要處理抽象的單字與概念，例如 `iterate`、`robust`、`feasibility` 等。這個 Skill 會根據你日常的開發任務客製英文學習內容，讓學習素材貼近實際工作，提升語言學習與真實情境的連結性。

## 概念

你跟 Claude Code 的對話原本就完整存在 `~/.claude/projects/*.jsonl`。本專案提供一個 Agent Skill `promptlingo`,讀取 JSONL,過濾雜訊(code、路徑、tool I/O、系統訊息),依你設定的 CEFR 等級產出每日學習素材:

1. **句型改寫** — 你的中文 prompt → 多種英文表達
2. **句型改善** — 你的英文 prompt → 文法 / 用字修正
3. **單字** — 從對話內挑符合等級的字(含略高一級延伸)
4. **文法重點** — 整體歸納

## Demo

![Demo](assets/demo.png)


## 前置需求

- **Python 3.10+**
- **[Claude Code](https://docs.claude.com/en/docs/claude-code)** 已安裝且至少使用過一次,確認 `~/.claude/projects/` 內有 `.jsonl` 對話檔
- macOS

## 安裝

執行安裝腳本(會 seed 空的 `vocab.json` / `patterns.json`,並建立 symlink 到 `~/.claude/skills/promptlingo`):

```bash
./install.sh
```

> 已存在的執行期資料檔不會被覆寫。執行期 `vocab.json` / `patterns.json` 已被 gitignore,模板放在 `skills/promptlingo/data/templates/`。

編輯 `skills/promptlingo/config.json` 設定等級:

```json
{ "level": "B2", "native_lang": "zh-TW", "target_lang": "en" }
```

## 使用

在任何 Claude Code session 內:

- `/promptlingo` — 分析今天
- `/promptlingo 2026-04-25` — 指定日期

報告寫到 `skills/promptlingo/data/reports/<DATE>/summary.md`,
單字累積在 `data/vocab.json`,易錯句型在 `data/patterns.json`。

## Ref

- [Input hypothesis on wiki](https://en.wikipedia.org/wiki/Input_hypothesis)
- [Comprehensible English by Volka English](https://www.youtube.com/watch?v=bo47JoSxl1s)
- [Not All Languages Are Created Equal in LLMs: Improving Multilingual Capability by Cross-Lingual-Thought Prompting](https://arxiv.org/abs/2305.07004)