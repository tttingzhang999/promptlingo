#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Merge analyzer output into vocab.json + patterns.json and rebuild the aggregate notes.

Stdin:  JSON {"date": "YYYY-MM-DD", "vocab": [...], "patterns": [...], "reviewed": [...]}
Stdout: summary {"vocab_added", "patterns_added", "notes_written", ...}

A pattern item is {category, kind, point, user_wrote, correction}:
  category  one of paths.GRAMMAR_CATEGORIES slugs (unknown slugs land in "other")
  kind      "error" (the user wrote it wrong) or "phrase" (a wording worth acquiring)
  point     the language feature, e.g. "疑問句缺助動詞" — NEVER the task content

Flags:
    --rebuild-notes    Skip stdin merge; just rebuild every note from json.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import (  # noqa: E402
    CATEGORY_LABEL,
    CATEGORY_ORDER,
    PATTERNS_JSON,
    VOCAB_JSON,
    ensure_dirs,
)
from render import project_glossary, project_grammar  # noqa: E402


def load_json(path: Path) -> list:
    if not path.exists():
        return []
    with path.open() as f:
        return json.load(f)


def save_json(path: Path, data: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)


def merge_vocab(existing: list, incoming: list, today: str) -> tuple[int, int]:
    index = {item["word"].lower(): item for item in existing}
    added = updated = 0
    for raw in incoming:
        word = (raw.get("word") or "").strip()
        if not word:
            continue
        key = word.lower()
        examples = [e for e in (raw.get("examples") or []) if e]
        if key in index:
            cur = index[key]
            if cur.get("last_seen") != today:  # idempotent: same-day re-run must not inflate count
                cur["count"] = cur.get("count", 0) + 1
                cur["last_seen"] = today
            kept = cur.get("examples") or []
            for ex in examples:
                if ex not in kept:
                    kept.append(ex)
            cur["examples"] = kept[-5:]
            for field in ("zh", "cefr", "pos", "synonyms", "antonyms"):
                if raw.get(field) and not cur.get(field):
                    cur[field] = raw[field]
            updated += 1
        else:
            index[key] = {
                "word": word,
                "cefr": raw.get("cefr") or "",
                "zh": raw.get("zh") or "",
                "pos": raw.get("pos") or "",
                "synonyms": raw.get("synonyms") or [],
                "antonyms": raw.get("antonyms") or [],
                "count": 1,
                "first_seen": today,
                "last_seen": today,
                "examples": examples[:5],
            }
            added += 1
    existing.clear()
    existing.extend(sorted(index.values(), key=lambda x: x["word"].lower()))
    return added, updated


def _new_category(slug: str, today: str) -> dict:
    return {
        "category": slug,
        "label": CATEGORY_LABEL[slug],
        "occurrences": 0,
        "first_seen": today,
        "last_seen": today,
        "points": [],
    }


def merge_patterns(existing: list, incoming: list, today: str) -> tuple[int, int, int]:
    """Accumulate by (category, kind, point) so a repeated mistake raises one count.

    Returns (points_added, points_updated, unknown_categories).
    """
    cats = {c["category"]: c for c in existing}
    added = updated = unknown = 0
    for raw in incoming:
        point = (raw.get("point") or "").strip()
        if not point:
            continue
        slug = (raw.get("category") or "").strip()
        if slug not in CATEGORY_LABEL:
            unknown += 1
            slug = "other"
        kind = "error" if raw.get("kind") == "error" else "phrase"
        cat = cats.setdefault(slug, _new_category(slug, today))
        by_point = {(p["kind"], p["point"].strip().lower()): p for p in cat["points"]}
        key = (kind, point.lower())
        user_wrote = (raw.get("user_wrote") or "").strip()
        correction = (raw.get("correction") or "").strip()
        cur = by_point.get(key)
        if cur:
            if cur.get("last_seen") != today:  # idempotent per day
                cur["count"] = cur.get("count", 0) + 1
                cur["last_seen"] = today
                cat["occurrences"] = cat.get("occurrences", 0) + 1
            updated += 1
        else:
            cur = {
                "kind": kind,
                "point": point,
                "user_wrote": user_wrote,
                "correction": correction,
                "count": 1,
                "first_seen": today,
                "last_seen": today,
                "examples": [],
            }
            cat["points"].append(cur)
            cat["occurrences"] = cat.get("occurrences", 0) + 1
            added += 1
        if user_wrote or correction:
            instance = {"user_wrote": user_wrote, "correction": correction, "date": today}
            if instance not in cur["examples"]:
                cur["examples"].append(instance)
            cur["examples"] = cur["examples"][-5:]
            cur["user_wrote"] = user_wrote or cur.get("user_wrote", "")
            cur["correction"] = correction or cur.get("correction", "")
        cat["last_seen"] = max(cat.get("last_seen") or today, today)
    existing.clear()
    existing.extend(sorted(cats.values(), key=lambda c: CATEGORY_ORDER.get(c["category"], 99)))
    return added, updated, unknown


def advance_reviews(existing: list, reviewed: list, today: str) -> int:
    """Surfacing a word in the daily review counts as one spaced-repetition rep:
    promote its Leitner box (count += 1) and reset the clock (last_seen = today).
    Idempotent per day — a word already touched today is skipped."""
    index = {item["word"].lower(): item for item in existing}
    advanced = 0
    for raw in reviewed:
        cur = index.get((raw or "").strip().lower())
        if not cur or cur.get("last_seen") == today:
            continue
        cur["count"] = cur.get("count", 0) + 1
        cur["last_seen"] = today
        advanced += 1
    return advanced


def rebuild_notes(vocab: list, patterns: list) -> int:
    ensure_dirs()
    return len(project_glossary(vocab)) + len(project_grammar(patterns))


def main() -> int:
    ensure_dirs()
    vocab = load_json(VOCAB_JSON)
    patterns = load_json(PATTERNS_JSON)

    if "--rebuild-notes" in sys.argv[1:]:
        result = {"notes_written": rebuild_notes(vocab, patterns)}
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    payload = json.load(sys.stdin)
    today = payload.get("date") or date.today().isoformat()

    v_add, v_upd = merge_vocab(vocab, payload.get("vocab", []), today)
    p_add, p_upd, p_unknown = merge_patterns(patterns, payload.get("patterns", []), today)
    r_adv = advance_reviews(vocab, payload.get("reviewed", []), today)

    save_json(VOCAB_JSON, vocab)
    save_json(PATTERNS_JSON, patterns)
    notes = rebuild_notes(vocab, patterns)

    summary = {
        "vocab_added": v_add, "vocab_updated": v_upd,
        "pattern_points_added": p_add, "pattern_points_updated": p_upd,
        "reviews_advanced": r_adv,
        "vocab_total": len(vocab),
        "grammar_categories": len(patterns),
        "notes_written": notes,
    }
    if p_unknown:
        summary["warning"] = (
            f"{p_unknown} 個 pattern 的 category 不在清單內，已歸到 other。"
            "請改用 SKILL.md 列出的 category slug。"
        )
    json.dump(summary, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
