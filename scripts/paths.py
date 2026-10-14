"""Resolve filesystem paths for promptlingo.

Learning artifacts (reports, glossary notes, grammar notes, SRS state) live in
LEARNING_DIR: PROMPTLINGO_LEARNING_DIR if set, else <skill>/learning.

Run as a script to print the obsidian:// link for a date's report:
    paths.py --open-url YYYY-MM-DD
It prints nothing when LEARNING_DIR is not inside an Obsidian vault.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote

SKILL_DIR = Path(__file__).resolve().parent.parent

_DEFAULT_LEARNING_DIR = SKILL_DIR / "learning"
LEARNING_DIR = Path(os.environ.get("PROMPTLINGO_LEARNING_DIR") or _DEFAULT_LEARNING_DIR)

DATA_DIR = LEARNING_DIR / "data"
REPORTS_DIR = LEARNING_DIR / "reports"
GLOSSARY_DIR = LEARNING_DIR / "glossary"
GRAMMAR_DIR = LEARNING_DIR / "grammar"

VOCAB_JSON = DATA_DIR / "vocab.json"
PATTERNS_JSON = DATA_DIR / "patterns.json"

TEMPLATE_DIR = SKILL_DIR / "data" / "templates"

# Grammar categories. Slug is the machine key (frontmatter + skill payload);
# label is the note filename and the human-facing title.
GRAMMAR_CATEGORIES: list[tuple[str, str]] = [
    ("articles-and-determiners", "冠詞與限定詞"),
    ("agreement-and-number", "主謂一致與單複數"),
    ("tense-and-aspect", "時態"),
    ("passive-voice", "被動語態"),
    ("questions", "疑問句與間接問句"),
    ("word-form", "詞性與構詞"),
    ("sentence-boundaries", "句子切分"),
    ("spelling-and-typography", "拼字與排版"),
    ("requests-and-instructions", "提出要求與下指令"),
    ("contrast-and-alternatives", "對比與取捨"),
    ("conditions-and-consequences", "條件、時間與後果"),
    ("inquiry-and-assessment", "探詢與評估"),
    ("other", "未分類"),
]
CATEGORY_LABEL = dict(GRAMMAR_CATEGORIES)
CATEGORY_ORDER = {slug: i for i, (slug, _) in enumerate(GRAMMAR_CATEGORIES)}

CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]


def ensure_dirs() -> None:
    for d in (DATA_DIR, REPORTS_DIR, GLOSSARY_DIR, GRAMMAR_DIR):
        d.mkdir(parents=True, exist_ok=True)


def report_path(date_str: str) -> Path:
    return REPORTS_DIR / f"{date_str} English Daily.md"


def glossary_note_name(level: str) -> str:
    """Note name (no extension) holding every word of one CEFR level."""
    return f"Glossary {level or 'Other'}"


def glossary_note_path(level: str) -> Path:
    return GLOSSARY_DIR / f"{glossary_note_name(level)}.md"


GLOSSARY_INDEX_PATH = GLOSSARY_DIR / "Glossary Index.md"


def word_link(word: str, level: str) -> str:
    """Wikilink to a word's heading inside its level note."""
    return f"[[{glossary_note_name(level)}#{word}|{word}]]"


def grammar_note_path(category: str) -> Path:
    label = CATEGORY_LABEL.get(category, CATEGORY_LABEL["other"])
    return GRAMMAR_DIR / f"{label}.md"


def obsidian_url(path: Path) -> str | None:
    """obsidian:// link to a file, or None when no ancestor holds a .obsidian folder."""
    path = path.resolve()
    vault = next((d for d in path.parents if (d / ".obsidian").is_dir()), None)
    if vault is None:
        return None
    rel = path.relative_to(vault).as_posix()
    return f"obsidian://open?vault={quote(vault.name, safe='')}&file={quote(rel, safe='')}"


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--open-url":
        sys.exit("usage: paths.py --open-url YYYY-MM-DD")
    url = obsidian_url(report_path(sys.argv[2]))
    if url:
        print(url)
