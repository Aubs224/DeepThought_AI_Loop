#!/usr/bin/env python3
"""Score and select the strongest DeepThought question."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WEIGHTS = {
    "importance": 0.28,
    "uncertainty": 0.20,
    "actionability": 0.16,
    "novelty": 0.18,
    "falsifiability": 0.18,
}

SYSTEM_PROMPT = """You are DeepThought's Question Judge.
Score each candidate question from 1 to 10 on:
importance, uncertainty, actionability, novelty, falsifiability.
Return only valid JSON:
{
  "scores": [
    {"index": 0, "importance": 8, "uncertainty": 7, "actionability": 6, "novelty": 8, "falsifiability": 5, "rationale": "brief"}
  ]
}
"""


def weighted_total(score: dict[str, Any]) -> float:
    return round(sum(float(score.get(k, 0)) * w for k, w in WEIGHTS.items()), 3)


def heuristic_score(question: dict[str, Any], index: int) -> dict[str, Any]:
    text = (question.get("question", "") + " " + question.get("why_it_matters", "")).lower()
    importance = 8 if any(w in text for w in ["governance", "labor", "infrastructure", "ai", "climate", "energy"]) else 6
    uncertainty = 8 if "will" in text or "which" in text or "can" in text else 6
    actionability = 7 if any(w in text for w in ["bottleneck", "constraint", "signals", "deployment", "adapt"]) else 5
    novelty = 7 if len(text) > 160 else 6
    falsifiability = 8 if question.get("signals_to_watch") else 5
    return {
        "index": index,
        "importance": importance,
        "uncertainty": uncertainty,
        "actionability": actionability,
        "novelty": novelty,
        "falsifiability": falsifiability,
        "rationale": "Heuristic fallback score based on specificity, signals, and decision relevance.",
    }


def call_openai_json(model: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:
        print(f"[select_best_question] LLM scoring failed, using heuristic: {exc}")
        return None


def select_best(input_data: dict[str, Any], model: str) -> dict[str, Any]:
    questions = input_data.get("questions", [])
    if not questions:
        raise ValueError("No questions found in input JSON.")

    judged = call_openai_json(model, {"questions": questions})
    scores = judged.get("scores", []) if judged else []
    if len(scores) != len(questions):
        scores = [heuristic_score(q, i) for i, q in enumerate(questions)]

    for s in scores:
        s["total"] = weighted_total(s)

    best_score = max(scores, key=lambda s: s["total"])
    best_index = int(best_score["index"])
    return {
        "selected_at": datetime.now(timezone.utc).isoformat(),
        "judge_model": model if os.getenv("OPENAI_API_KEY") else "heuristic-fallback",
        "weights": WEIGHTS,
        "selected_index": best_index,
        "selected_question": questions[best_index],
        "selected_score": best_score,
        "all_scores": scores,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Select best DeepThought question.")
    parser.add_argument("questions_file")
    parser.add_argument("--model", default=os.getenv("DEEPTHOUGHT_JUDGE_MODEL", "gpt-4.1-mini"))
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    in_path = Path(args.questions_file)
    result = select_best(json.loads(in_path.read_text(encoding="utf-8")), args.model)
    out_path = Path(args.out or str(in_path).replace("_questions.json", "_selected.json"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
