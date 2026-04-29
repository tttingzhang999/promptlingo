#!/usr/bin/env python3
"""Load and filter Claude Code JSONL transcripts for English-learning analysis.

Usage:
    python3 transcript_loader.py [YYYY-MM-DD]   # default: today

Stdout: JSON {date, sources, stats, turns: [{role, lang, text, ts, sessionId}]}
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
PROJECTS_ROOT = Path.home() / ".claude" / "projects"

DROP_TAGS = ("<system-reminder>", "<command-name>", "<local-command-stdout>",
             "<command-message>", "<command-args>", "<user-prompt-submit-hook>")
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
PATH_RE = re.compile(r"(?:(?:~|\.{0,2})/[\w./\-]+|[A-Za-z]:\\[\w.\\\-]+)")
URL_RE = re.compile(r"https?://\S+")
SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
SHELL_PREFIX_RE = re.compile(r"^[\$>]\s+", re.MULTILINE)
SLASH_CMD_RE = re.compile(r"^/[a-z][\w-]*", re.MULTILINE)
WS_RE = re.compile(r"\s+")
CJK_RE = re.compile(r"[一-鿿㐀-䶿]")


def load_config() -> dict:
    with CONFIG_PATH.open() as f:
        return json.load(f)


def detect_lang(text: str) -> str:
    if not text:
        return "unknown"
    cjk = len(CJK_RE.findall(text))
    return "zh" if cjk / max(len(text), 1) > 0.3 else "en"


def clean_text(raw: str) -> str:
    s = FENCE_RE.sub(" ", raw)
    s = INLINE_CODE_RE.sub(" ", s)
    s = URL_RE.sub(" ", s)
    s = PATH_RE.sub(" ", s)
    s = SHA_RE.sub(" ", s)
    s = SHELL_PREFIX_RE.sub("", s)
    s = SLASH_CMD_RE.sub("", s)
    return WS_RE.sub(" ", s).strip()


def extract_text(message: dict) -> str | None:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [seg.get("text", "") for seg in content
                 if isinstance(seg, dict) and seg.get("type") == "text"]
        return "\n".join(p for p in parts if p) or None
    return None


def is_noise(record: dict, text: str) -> bool:
    if record.get("isMeta") or record.get("isSidechain"):
        return True
    if any(tag in text for tag in DROP_TAGS):
        return True
    return False


def project_tag(jsonl_path: Path) -> str:
    try:
        rel = jsonl_path.relative_to(PROJECTS_ROOT)
        return rel.parts[0] if rel.parts else jsonl_path.stem
    except ValueError:
        return jsonl_path.stem


def stage1_structural(jsonl_path: Path) -> list[dict]:
    out: list[dict] = []
    sid_fallback = jsonl_path.stem
    project = project_tag(jsonl_path)
    with jsonl_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") not in ("user", "assistant"):
                continue
            msg = rec.get("message") or {}
            if msg.get("role") not in ("user", "assistant"):
                continue
            text = extract_text(msg)
            if not text or not isinstance(text, str):
                continue
            if is_noise(rec, text):
                continue
            out.append({
                "role": msg["role"],
                "raw": text,
                "ts": rec.get("timestamp"),
                "sessionId": rec.get("sessionId", sid_fallback),
                "project": project,
                "cwd": rec.get("cwd") or "",
            })
    return out


def stage2_clean(turns: list[dict], min_chars: int) -> list[dict]:
    cleaned = []
    for t in turns:
        text = clean_text(t["raw"])
        if len(text) < min_chars:
            continue
        cleaned.append({
            "role": t["role"],
            "text": text,
            "lang": detect_lang(text),
            "ts": t["ts"],
            "sessionId": t["sessionId"],
            "project": t.get("project", ""),
            "cwd": t.get("cwd", ""),
        })
    return cleaned


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = int(limit * 0.6)
    tail = limit - head
    return text[:head] + " […] " + text[-tail:]


def stage3_sample(turns: list[dict], cfg: dict) -> list[dict]:
    p = cfg["parser"]
    seen: set[str] = set()
    deduped = []
    for t in turns:
        h = hashlib.sha1(t["text"].encode()).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        limit = (p["user_turn_max_chars"] if t["role"] == "user"
                 else p["assistant_turn_max_chars"])
        deduped.append({**t, "text": truncate(t["text"], limit)})

    cap = p["max_turns_per_day"]
    if len(deduped) <= cap:
        return deduped
    users = [t for t in deduped if t["role"] == "user"]
    assistants = [t for t in deduped if t["role"] == "assistant"]
    if len(users) >= cap:
        return users[:cap]
    budget = cap - len(users)
    rng = random.Random(42)
    sampled = rng.sample(assistants, k=min(budget, len(assistants)))
    kept = users + sampled
    kept.sort(key=lambda x: x.get("ts") or "")
    return kept


def jsonl_for_date(target: date) -> list[Path]:
    if not PROJECTS_ROOT.exists():
        return []
    out = []
    start = datetime.combine(target, datetime.min.time(), tzinfo=timezone.utc).timestamp()
    end = start + 86400
    for jsonl in PROJECTS_ROOT.rglob("*.jsonl"):
        try:
            mtime = jsonl.stat().st_mtime
        except OSError:
            continue
        if start <= mtime < end:
            out.append(jsonl)
    return out


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    target = date.fromisoformat(arg) if arg else date.today()
    cfg = load_config()
    sources = jsonl_for_date(target)

    raw_turns: list[dict] = []
    for path in sources:
        raw_turns.extend(stage1_structural(path))

    stage1_count = len(raw_turns)
    cleaned = stage2_clean(raw_turns, cfg["parser"]["min_turn_chars"])
    cleaned.sort(key=lambda x: x.get("ts") or "")
    sampled = stage3_sample(cleaned, cfg)

    payload = {
        "date": target.isoformat(),
        "sources": [str(p) for p in sources],
        "stats": {
            "session_files": len(sources),
            "stage1_turns": stage1_count,
            "stage2_turns": len(cleaned),
            "stage3_turns": len(sampled),
            "total_chars": sum(len(t["text"]) for t in sampled),
        },
        "turns": sampled,
    }
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
