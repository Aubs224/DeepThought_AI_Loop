#!/usr/bin/env python3
"""Score the DeepThought archive and produce diversity guidance.

This script reads prior run artifacts and summarizes what the loop has already
been thinking about. The output can be used by loop.py to steer future question
generation away from over-represented domains and recently repeated themes.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DOMAIN_TARGETS = {
    "artificial intelligence": 1.0,
    "technology infrastructure": 1.0,
    "state of the world": 1.0,
    "civilization and governance": 1.0,
    "economics and labor": 1.0,
    "science and health": 1.0,
    "climate and energy": 1.0,
    "culture and media": 1.0,
}

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "by", "for", "in", "is", "of", "on", "or", "the", "to", "if", "not", "about", "above", "after", "again", "against", "also", "among", "because",
    "before", "being", "between", "could", "does", "during", "future", "have",
    "into", "major", "might", "more", "most", "next", "over", "question", "should",
    "than", "that", "their", "there", "these", "they", "this", "through", "under",
    "what", "when", "where", "which", "while", "will", "with", "within", "would",
    "years", "year", "world", "from", "into", "itself", "become", "becomes", "becoming",
}


@dataclass
class ArchiveItem:
    path: str
    kind: str
    domain: str
    question: str
    score: float | None
    created_at: str | None


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _normalize_domain(value: str | None) -> str:
    value = (value or "unknown").strip().lower()
    aliases = {
        "ai": "artificial intelligence",
        "agi": "artificial intelligence",
        "artificial intelligence and machine learning": "artificial intelligence",
        "climate": "climate and energy",
        "energy": "climate and energy",
        "economics": "economics and labor",
        "labor": "economics and labor",
        "governance": "civilization and governance",
        "health": "science and health",
        "science": "science and health",
        "media": "culture and media",
        "culture": "culture and media",
    }
    return aliases.get(value, value)


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", text.lower())
    return [w for w in words if w not in STOPWORDS and not w.isdigit()]


def _cosineish_overlap(a: str, b: str) -> float:
    ca = Counter(_tokenize(a))
    cb = Counter(_tokenize(b))
    if not ca or not cb:
        return 0.0
    shared = sum(min(ca[k], cb[k]) for k in ca.keys() & cb.keys())
    denom = math.sqrt(sum(v * v for v in ca.values())) * math.sqrt(sum(v * v for v in cb.values()))
    return round(shared / denom, 3) if denom else 0.0


def collect_items(runs_dir: Path, archive_dir: Path | None = None) -> list[ArchiveItem]:
    """Collect selected questions from prior runs.

    Priority is given to *_selected.json because it includes judge scores.
    *_notes.json is used as a fallback when selected files are not available.
    """
    items: list[ArchiveItem] = []
    seen_questions: set[str] = set()

    for path in sorted(runs_dir.glob("*_selected.json")):
        data = _read_json(path)
        if not data:
            continue
        q = data.get("selected_question", {}) or {}
        question = str(q.get("question", "")).strip()
        if not question:
            continue
        key = question.lower()
        if key in seen_questions:
            continue
        seen_questions.add(key)
        score = data.get("selected_score", {}).get("total")
        items.append(
            ArchiveItem(
                path=str(path),
                kind="selected",
                domain=_normalize_domain(q.get("domain")),
                question=question,
                score=float(score) if isinstance(score, (int, float)) else None,
                created_at=data.get("selected_at"),
            )
        )

    for path in sorted(runs_dir.glob("*_notes.json")):
        data = _read_json(path)
        if not data:
            continue
        q = data.get("source_question", {}) or {}
        question = str(q.get("question", "")).strip()
        if not question:
            continue
        key = question.lower()
        if key in seen_questions:
            continue
        seen_questions.add(key)
        items.append(
            ArchiveItem(
                path=str(path),
                kind="notes",
                domain=_normalize_domain(q.get("domain")),
                question=question,
                score=None,
                created_at=data.get("extracted_at"),
            )
        )

    # Optional archive scan for projects that move records outside runs/.
    if archive_dir and archive_dir.exists():
        for path in sorted(archive_dir.glob("**/*.json")):
            data = _read_json(path)
            if not data:
                continue
            q = data.get("source_question") or data.get("selected_question") or {}
            question = str(q.get("question", "")).strip() if isinstance(q, dict) else ""
            if not question or question.lower() in seen_questions:
                continue
            seen_questions.add(question.lower())
            items.append(
                ArchiveItem(
                    path=str(path),
                    kind="archive",
                    domain=_normalize_domain(q.get("domain") if isinstance(q, dict) else None),
                    question=question,
                    score=None,
                    created_at=data.get("extracted_at") or data.get("selected_at"),
                )
            )

    return items


def analyze_archive(
    runs_dir: str | Path = "runs",
    archive_dir: str | Path | None = "archive",
    recent_window: int = 8,
    target_domains: dict[str, float] | None = None,
) -> dict[str, Any]:
    runs = Path(runs_dir)
    archive = Path(archive_dir) if archive_dir else None
    targets = target_domains or DEFAULT_DOMAIN_TARGETS
    items = collect_items(runs, archive)
    recent = items[-recent_window:] if recent_window > 0 else items

    domain_counts = Counter(item.domain for item in items)
    recent_domain_counts = Counter(item.domain for item in recent)

    all_questions = "\n".join(item.question for item in items)
    recent_questions = [item.question for item in recent]
    keyword_counts = Counter(_tokenize(all_questions))

    total_target = sum(targets.values()) or 1.0
    total_items = len(items)
    domain_pressure: dict[str, float] = {}
    for domain, weight in targets.items():
        expected_share = weight / total_target
        actual_share = (domain_counts.get(domain, 0) / total_items) if total_items else 0.0
        pressure = round(actual_share - expected_share, 3)
        domain_pressure[domain] = pressure

    underexplored = sorted(
        targets.keys(),
        key=lambda d: (domain_counts.get(d, 0) / (targets[d] or 1.0), domain_counts.get(d, 0), d),
    )
    overrepresented = sorted(
        [d for d, pressure in domain_pressure.items() if pressure > 0.08],
        key=lambda d: domain_pressure[d],
        reverse=True,
    )

    repeated_themes = [word for word, count in keyword_counts.most_common(20) if count >= 2]

    guidance_text = build_guidance_text(
        total_items=total_items,
        underexplored=underexplored,
        overrepresented=overrepresented,
        recent_questions=recent_questions,
        repeated_themes=repeated_themes,
        recent_domain_counts=recent_domain_counts,
    )

    return {
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "runs_dir": str(runs),
        "archive_dir": str(archive) if archive else None,
        "total_items": total_items,
        "domain_counts": dict(domain_counts),
        "recent_domain_counts": dict(recent_domain_counts),
        "domain_pressure": domain_pressure,
        "underexplored_domains": underexplored,
        "overrepresented_domains": overrepresented,
        "repeated_themes": repeated_themes,
        "recent_questions": recent_questions,
        "items": [item.__dict__ for item in items],
        "guidance_text": guidance_text,
    }


def build_guidance_text(
    total_items: int,
    underexplored: list[str],
    overrepresented: list[str],
    recent_questions: list[str],
    repeated_themes: list[str],
    recent_domain_counts: Counter[str],
) -> str:
    if total_items == 0:
        return (
            "No prior archive items were found. Explore broadly across all domains, "
            "and avoid selecting multiple questions from the same domain in a single batch."
        )

    favored = ", ".join(underexplored[:4]) or "any non-repeated domain"
    avoid_domains = ", ".join(overrepresented[:4]) or "none"
    avoid_themes = ", ".join(repeated_themes[:12]) or "none"
    recent_block = "\n".join(f"- {q}" for q in recent_questions[-6:]) or "- none"
    recent_domains = ", ".join(f"{d}: {c}" for d, c in recent_domain_counts.most_common()) or "none"

    return f"""Archive diversity guidance:
- Prior items: {total_items}
- Prefer underexplored domains this run: {favored}
- Penalize overrepresented domains unless the question is exceptionally new: {avoid_domains}
- Recent domain mix: {recent_domains}
- Repeated themes/words to avoid unless framed in a new way: {avoid_themes}
- Do not repeat or closely paraphrase these recent questions:
{recent_block}
""".strip()


def score_candidate_penalty(question: dict[str, Any], guidance: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic diversity penalties for a candidate question."""
    domain = _normalize_domain(question.get("domain"))
    q_text = str(question.get("question", ""))
    pressure = float(guidance.get("domain_pressure", {}).get(domain, 0.0))
    overrepresented = set(guidance.get("overrepresented_domains", []))
    recent_questions = guidance.get("recent_questions", []) or []

    max_similarity = 0.0
    closest = None
    for prior in recent_questions:
        sim = _cosineish_overlap(q_text, str(prior))
        if sim > max_similarity:
            max_similarity = sim
            closest = prior

    domain_penalty = 0.0
    if domain in overrepresented:
        domain_penalty += min(1.2, max(0.4, pressure * 4.0))
    if guidance.get("recent_domain_counts", {}).get(domain, 0) >= 3:
        domain_penalty += 0.4

    similarity_penalty = 0.0
    if max_similarity >= 0.7:
        similarity_penalty = 1.2
    elif max_similarity >= 0.5:
        similarity_penalty = 0.7
    elif max_similarity >= 0.35:
        similarity_penalty = 0.35

    underexplored_bonus = 0.0
    if domain in (guidance.get("underexplored_domains", [])[:3]):
        underexplored_bonus = 0.25

    total_adjustment = round(-domain_penalty - similarity_penalty + underexplored_bonus, 3)
    return {
        "domain": domain,
        "domain_penalty": round(domain_penalty, 3),
        "similarity_penalty": round(similarity_penalty, 3),
        "underexplored_bonus": round(underexplored_bonus, 3),
        "max_recent_similarity": max_similarity,
        "closest_recent_question": closest,
        "total_adjustment": total_adjustment,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a DeepThought archive for diversity and repetition.")
    parser.add_argument("--runs-dir", default="runs")
    parser.add_argument("--archive-dir", default="archive")
    parser.add_argument("--recent-window", type=int, default=8)
    parser.add_argument("--out", default=None)
    parser.add_argument("--print-guidance", action="store_true")
    args = parser.parse_args()

    result = analyze_archive(args.runs_dir, args.archive_dir, args.recent_window)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(out_path)
    elif args.print_guidance:
        print(result["guidance_text"])
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
