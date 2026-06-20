#!/usr/bin/env python3
"""Save a DeepThought run into a durable archive folder."""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def slugify(text: str, max_len: int = 64) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in text)
    safe = "-".join(part for part in safe.split("-") if part)
    return (safe[:max_len].strip("-") or "deepthought-run")


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def save_archive(answer_file: Path, notes_file: Path, archive_dir: Path) -> dict[str, Any]:
    answer_payload = json.loads(answer_file.read_text(encoding="utf-8"))
    notes = json.loads(notes_file.read_text(encoding="utf-8"))
    q = answer_payload.get("selected", {}).get("selected_question", {})
    question = q.get("question", "DeepThought run")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + slugify(question, 40)

    run_dir = archive_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "question.json").write_text(json.dumps(q, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "answer.md").write_text(answer_payload.get("answer_markdown", ""), encoding="utf-8")
    (run_dir / "answer.json").write_text(json.dumps(answer_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "notes.json").write_text(json.dumps(notes, indent=2, ensure_ascii=False), encoding="utf-8")

    if answer_file.exists():
        shutil.copy2(answer_file, run_dir / "raw_answer_payload.json")
    if notes_file.exists():
        shutil.copy2(notes_file, run_dir / "raw_notes_payload.json")

    index_record = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "domain": q.get("domain"),
        "question": question,
        "summary": notes.get("summary"),
        "archive_path": str(run_dir),
        "signals_to_monitor": notes.get("signals_to_monitor", []),
        "prediction_count": len(notes.get("key_predictions", [])),
    }
    append_jsonl(archive_dir / "index.jsonl", index_record)

    signal_record = {
        "run_id": run_id,
        "question": question,
        "signals_to_monitor": notes.get("signals_to_monitor", []),
        "created_at": index_record["created_at"],
    }
    append_jsonl(archive_dir / "signal_watchlist.jsonl", signal_record)

    return index_record


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive a DeepThought run.")
    parser.add_argument("answer_file")
    parser.add_argument("notes_file")
    parser.add_argument("--archive-dir", default="archive")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    result = save_archive(Path(args.answer_file), Path(args.notes_file), Path(args.archive_dir))
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
