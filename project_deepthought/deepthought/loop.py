#!/usr/bin/env python3
"""Run the full DeepThought loop.

One iteration:
1. generate candidate questions
2. select the best one
3. ask a deep model
4. extract structured notes
5. save everything to the archive
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from ask_deep_model import ask
from extract_structured_notes import extract
from generate_questions import DEFAULT_DOMAINS, generate_questions
from save_to_archive import save_archive
from select_best_question import select_best
from score_archive import analyze_archive


def now_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def run_once(args: argparse.Namespace, iteration: int) -> dict:
    run_label = f"{now_id()}_iter{iteration:03d}"
    runs_dir = Path(args.runs_dir)

    archive_guidance = None
    guidance_file = None
    active_domains = list(args.domains)
    if args.diversity:
        archive_guidance = analyze_archive(args.runs_dir, args.archive_dir, args.recent_window)
        guidance_file = write_json(runs_dir / f"{run_label}_archive_score.json", archive_guidance)
        underexplored = archive_guidance.get("underexplored_domains") or []
        if args.domain_strategy == "underexplored" and underexplored:
            active_domains = underexplored[: max(3, min(len(underexplored), args.domain_window))]
        print("[DeepThought] diversity guidance:")
        print(archive_guidance.get("guidance_text", ""))

    questions = generate_questions(args.count, active_domains, args.question_model, archive_guidance.get("guidance_text") if archive_guidance else None)
    questions["active_domains"] = active_domains
    questions_file = write_json(runs_dir / f"{run_label}_questions.json", questions)

    selected = select_best(questions, args.judge_model, archive_guidance)
    selected_file = write_json(runs_dir / f"{run_label}_selected.json", selected)

    answer = ask(selected, args.deep_model, args.max_tokens)
    answer_file = write_json(runs_dir / f"{run_label}_answer.json", answer)
    (runs_dir / f"{run_label}_answer.md").write_text(answer["answer_markdown"], encoding="utf-8")

    notes = extract(answer, args.extract_model)
    notes_file = write_json(runs_dir / f"{run_label}_notes.json", notes)

    archive_record = save_archive(answer_file, notes_file, Path(args.archive_dir))
    return {
        "iteration": iteration,
        "questions_file": str(questions_file),
        "selected_file": str(selected_file),
        "archive_score_file": str(guidance_file) if guidance_file else None,
        "answer_file": str(answer_file),
        "notes_file": str(notes_file),
        "archive_record": archive_record,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DeepThought recursively.")
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--domains", nargs="*", default=DEFAULT_DOMAINS)
    parser.add_argument("--no-diversity", dest="diversity", action="store_false", help="Disable archive scoring and diversity guidance.")
    parser.set_defaults(diversity=True)
    parser.add_argument("--recent-window", type=int, default=8, help="How many recent questions to penalize for repetition.")
    parser.add_argument("--domain-strategy", choices=["all", "underexplored"], default="underexplored", help="Which domains the next question batch should consider.")
    parser.add_argument("--domain-window", type=int, default=5, help="Number of underexplored domains to feed into the generator.")
    parser.add_argument("--runs-dir", default="runs")
    parser.add_argument("--archive-dir", default="archive")
    parser.add_argument("--question-model", default="gpt-4.1-mini")
    parser.add_argument("--judge-model", default="gpt-4.1-mini")
    parser.add_argument("--deep-model", default="gpt-4.1")
    parser.add_argument("--extract-model", default="gpt-4.1-mini")
    parser.add_argument("--max-tokens", type=int, default=6000)
    args = parser.parse_args()

    if args.iterations < 1:
        raise ValueError("--iterations must be at least 1")

    manifest = []
    for i in range(1, args.iterations + 1):
        print(f"[DeepThought] iteration {i}/{args.iterations}")
        record = run_once(args, i)
        manifest.append(record)
        print(json.dumps(record["archive_record"], indent=2, ensure_ascii=False))
        if i < args.iterations and args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    manifest_path = Path(args.runs_dir) / f"{now_id()}_manifest.json"
    write_json(manifest_path, {"runs": manifest})
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
