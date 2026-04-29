#!/usr/bin/env python3
"""Output vocab due for spaced review today.

Usage:
    python3 due.py [YYYY-MM-DD]              # default: today
    python3 due.py [YYYY-MM-DD] --limit=N

Stdout: JSON {"today": "<DATE>", "due": [{word, cefr, zh, last_seen, count, interval, days_overdue, examples}]}
Intervals (Leitner-style, by count): 1->1d, 2->3d, 3->7d, 4->14d, >=5->30d.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

VOCAB_PATH = Path(__file__).resolve().parent.parent / "data" / "vocab.json"

INTERVALS = {1: 1, 2: 3, 3: 7, 4: 14}
INTERVAL_DEFAULT = 30


def interval_for(count: int) -> int:
    return INTERVALS.get(count, INTERVAL_DEFAULT)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    today = date.fromisoformat(args[0]) if args else date.today()
    limit = None
    for f in flags:
        if f.startswith("--limit"):
            _, _, val = f.partition("=")
            try:
                limit = int(val)
            except (TypeError, ValueError):
                limit = None

    if not VOCAB_PATH.exists():
        json.dump({"today": today.isoformat(), "due": []}, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    with VOCAB_PATH.open() as f:
        vocab = json.load(f)

    due = []
    for item in vocab:
        last_seen = item.get("last_seen") or item.get("first_seen")
        if not last_seen:
            continue
        try:
            last = date.fromisoformat(last_seen)
        except ValueError:
            continue
        if last >= today:
            continue
        count = max(1, int(item.get("count", 1)))
        interval = interval_for(count)
        gap = (today - last).days
        if gap < interval:
            continue
        due.append({
            "word": item["word"],
            "cefr": item.get("cefr", ""),
            "zh": item.get("zh", ""),
            "last_seen": last_seen,
            "count": count,
            "interval": interval,
            "days_overdue": gap - interval,
            "examples": (item.get("examples") or [])[-1:],
        })

    due.sort(key=lambda x: (-x["days_overdue"], -x["count"]))
    if limit:
        due = due[:limit]

    json.dump({"today": today.isoformat(), "due": due}, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
