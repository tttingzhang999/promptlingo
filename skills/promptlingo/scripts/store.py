#!/usr/bin/env python3
"""Merge analyzer output into vocab.json and patterns.json (idempotent).

Stdin:  JSON {"vocab": [...], "patterns": [...], "date": "YYYY-MM-DD"}
Stdout: summary {"vocab_added", "vocab_updated", "patterns_added", "patterns_updated", ...}
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
VOCAB_PATH = DATA_DIR / "vocab.json"
PATTERNS_PATH = DATA_DIR / "patterns.json"


def load_json(path: Path) -> list:
    if not path.exists():
        return []
    with path.open() as f:
        return json.load(f)


def save_json(path: Path, data: list) -> None:
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
            cur["count"] = cur.get("count", 0) + 1
            cur["last_seen"] = today
            existing_examples = cur.get("examples") or []
            for ex in examples:
                if ex not in existing_examples:
                    existing_examples.append(ex)
            cur["examples"] = existing_examples[-5:]
            if raw.get("zh") and not cur.get("zh"):
                cur["zh"] = raw["zh"]
            if raw.get("cefr") and not cur.get("cefr"):
                cur["cefr"] = raw["cefr"]
            updated += 1
        else:
            index[key] = {
                "word": word,
                "cefr": raw.get("cefr") or "",
                "zh": raw.get("zh") or "",
                "count": 1,
                "first_seen": today,
                "last_seen": today,
                "examples": examples[:5],
            }
            added += 1
    existing.clear()
    existing.extend(sorted(index.values(), key=lambda x: x["word"].lower()))
    return added, updated


def merge_patterns(existing: list, incoming: list, today: str) -> tuple[int, int]:
    index = {(item["pattern"], item.get("user_wrote", "")): item for item in existing}
    added = updated = 0
    for raw in incoming:
        pat = (raw.get("pattern") or "").strip()
        if not pat:
            continue
        key = (pat, raw.get("user_wrote", ""))
        if key in index:
            cur = index[key]
            cur["occurrences"] = cur.get("occurrences", 0) + 1
            cur["last_seen"] = today
            if raw.get("correction") and not cur.get("correction"):
                cur["correction"] = raw["correction"]
            updated += 1
        else:
            index[key] = {
                "pattern": pat,
                "user_wrote": raw.get("user_wrote", ""),
                "correction": raw.get("correction", ""),
                "occurrences": 1,
                "last_seen": today,
            }
            added += 1
    existing.clear()
    existing.extend(index.values())
    return added, updated


def main() -> int:
    payload = json.load(sys.stdin)
    today = payload.get("date") or date.today().isoformat()

    vocab = load_json(VOCAB_PATH)
    patterns = load_json(PATTERNS_PATH)

    v_add, v_upd = merge_vocab(vocab, payload.get("vocab", []), today)
    p_add, p_upd = merge_patterns(patterns, payload.get("patterns", []), today)

    save_json(VOCAB_PATH, vocab)
    save_json(PATTERNS_PATH, patterns)

    json.dump({
        "vocab_added": v_add, "vocab_updated": v_upd,
        "patterns_added": p_add, "patterns_updated": p_upd,
        "vocab_total": len(vocab), "patterns_total": len(patterns),
    }, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
