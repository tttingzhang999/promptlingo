"""Render the aggregate Obsidian notes from vocab.json / patterns.json.

One note per CEFR level (glossary) and one note per grammar category (grammar).
Every note is rebuilt in full from JSON on each run, so the JSON stays the single
source of truth and the notes can never drift.
"""
from __future__ import annotations

from pathlib import Path

from paths import (
    CATEGORY_LABEL,
    CATEGORY_ORDER,
    GLOSSARY_INDEX_PATH,
    ensure_dirs,
    glossary_note_path,
    grammar_note_path,
    word_link,
)

FOOTER = "延伸：[[promptlingo]] · [[Glossary Index]] · [[index]]"


def _cell(text: str, limit: int = 0) -> str:
    """Make a string safe inside a Markdown table cell; `limit` clips long originals."""
    s = (text or "").replace("|", "\\|")
    s = " ".join(s.split())
    if limit and len(s) > limit:
        s = s[:limit].rstrip() + "…"
    return s or "—"


# --------------------------------------------------------------------------- glossary


def render_glossary_level(level: str, entries: list[dict]) -> str:
    """One note per CEFR level. `### <word>` gives each word a linkable anchor."""
    words = sorted(entries, key=lambda e: e["word"].lower())
    fm = [
        "---",
        "type: glossary",
        f"level: {level}",
        f"word_count: {len(words)}",
        f"tags: [vocab, cefr/{level or 'unknown'}]",
        "---",
        "",
        f"> [!info] {level} 單字（{len(words)} 字）",
        "> 由 promptlingo 從 `data/vocab.json` 生成。不要手改這個檔案。",
        "> 改完 JSON 請跑 `uv run .claude/skills/promptlingo/scripts/store.py --rebuild-notes`。",
        "> 找單字用 Ctrl+F 或右側 outline；全部等級的總表在 [[Glossary Index]]。",
        "",
    ]
    body: list[str] = []
    for e in words:
        meta = [
            f"`{e.get('pos') or '—'}`",
            e.get("zh") or "—",
            f"出現 {e.get('count', 1)} 次",
            f"上次 {e.get('last_seen') or '—'}",
        ]
        if e.get("synonyms"):
            meta.append("同義 " + ", ".join(e["synonyms"]))
        if e.get("antonyms"):
            meta.append("反義 " + ", ".join(e["antonyms"]))
        body.append(f"### {e['word']}")
        body.append("")
        body.append(" · ".join(meta))
        body.append("")
        examples = e.get("examples") or []
        if examples:
            body.append("> [!example]")
            body.extend(f"> - {ex}" for ex in examples)
            body.append("")
    return "\n".join(fm + body + ["---", FOOTER, ""])


def render_glossary_index(vocab: list[dict]) -> str:
    """One table over every word, sorted by how often it has come up."""
    rows = sorted(vocab, key=lambda e: (-e.get("count", 1), e["word"].lower()))
    fm = [
        "---",
        "type: glossary-index",
        f"word_count: {len(rows)}",
        "tags: [vocab, glossary]",
        "---",
        "",
        f"> [!info] 單字總表（{len(rows)} 字）",
        "> 依出現次數排序。點單字跳到該等級檔的對應段落。",
        "> 由 promptlingo 生成，不要手改。",
        "",
        "| 單字 | CEFR | 中文 | 詞性 | 次數 | 上次 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    body = [
        "| {} | {} | {} | {} | {} | {} |".format(
            word_link(e["word"], e.get("cefr") or ""),
            _cell(e.get("cefr") or ""),
            _cell(e.get("zh") or ""),
            _cell(e.get("pos") or ""),
            e.get("count", 1),
            _cell(e.get("last_seen") or ""),
        )
        for e in rows
    ]
    return "\n".join(fm + body + ["", "---", FOOTER, ""])


def project_glossary(vocab: list[dict]) -> list[Path]:
    ensure_dirs()
    by_level: dict[str, list[dict]] = {}
    for e in vocab:
        by_level.setdefault(e.get("cefr") or "Other", []).append(e)
    written = []
    for level, entries in sorted(by_level.items()):
        path = glossary_note_path(level)
        path.write_text(render_glossary_level(level, entries), encoding="utf-8")
        written.append(path)
    GLOSSARY_INDEX_PATH.write_text(render_glossary_index(vocab), encoding="utf-8")
    written.append(GLOSSARY_INDEX_PATH)
    return written


# ---------------------------------------------------------------------------- grammar


# The Chinese/spoken original is context only — clip it so the table stays scannable.
# The full text stays in patterns.json and in that day's report.
CELL_LIMIT = {"user_wrote": 44}


def _grammar_table(points: list[dict], headers: list[str], fields: list[str]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for p in sorted(points, key=lambda x: (-x.get("count", 1), x.get("last_seen") or "")):
        cells = []
        for f in fields:
            val = p.get(f)
            cells.append(str(val) if f == "count" else _cell(val or "", CELL_LIMIT.get(f, 0)))
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def render_grammar_note(cat: dict) -> str:
    label = CATEGORY_LABEL.get(cat["category"], CATEGORY_LABEL["other"])
    points = cat.get("points") or []
    errors = [p for p in points if p.get("kind") == "error"]
    phrases = [p for p in points if p.get("kind") != "error"]
    fm = [
        "---",
        "type: grammar",
        f"category: {cat['category']}",
        f"label: {label}",
        f"error_count: {len(errors)}",
        f"phrase_count: {len(phrases)}",
        f"occurrences: {cat.get('occurrences', len(points))}",
        f"first_seen: {cat.get('first_seen') or ''}",
        f"last_seen: {cat.get('last_seen') or ''}",
        f"tags: [grammar, grammar/{cat['category']}]",
        "---",
        "",
        "```table-of-contents",
        "```",
        "",
        f"> [!bug] {label}",
        f"> **常犯錯誤：** {len(errors)} 條 · **值得學的說法：** {len(phrases)} 條",
        f"> **累計出現：** {cat.get('occurrences', len(points))} 次 · **上次：** {cat.get('last_seen') or '—'}",
        "",
    ]
    body: list[str] = ["## 常犯錯誤", ""]
    if errors:
        body += _grammar_table(
            errors,
            ["語法點", "你寫的", "修正", "次數", "上次"],
            ["point", "user_wrote", "correction", "count", "last_seen"],
        )
    else:
        body.append("> [!tip] 這個分類目前沒有錯誤紀錄。")
    body += ["", "## 值得學的說法", ""]
    if phrases:
        body += _grammar_table(
            phrases,
            ["說法", "情境原句", "英文範句", "次數", "上次"],
            ["point", "user_wrote", "correction", "count", "last_seen"],
        )
    else:
        body.append("> [!tip] 這個分類目前沒有收錄說法。")
    return "\n".join(fm + body + ["", "---", FOOTER, ""])


def project_grammar(categories: list[dict]) -> list[Path]:
    ensure_dirs()
    written = []
    for cat in sorted(categories, key=lambda c: CATEGORY_ORDER.get(c["category"], 99)):
        if not (cat.get("points") or []):
            continue
        path = grammar_note_path(cat["category"])
        path.write_text(render_grammar_note(cat), encoding="utf-8")
        written.append(path)
    return written
