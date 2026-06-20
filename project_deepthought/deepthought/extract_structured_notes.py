#!/usr/bin/env python3
"""Extract structured predictions, assumptions, and signals from an answer."""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SYSTEM_PROMPT = """You are DeepThought's Auditor.
Extract structured notes from a deep analysis. Return only valid JSON:
{
  "summary": "compact summary",
  "key_predictions": [{"prediction": "...", "time_horizon": "near|medium|long|unknown", "confidence": 0.0}],
  "assumptions": ["..."],
  "uncertainties": ["..."],
  "signals_to_monitor": ["..."],
  "next_questions": ["..."]
}
"""


def call_openai_json(model: str, answer: str) -> dict[str, Any] | None:
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
                {"role": "user", "content": answer},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:
        print(f"[extract_structured_notes] LLM extraction failed, using regex fallback: {exc}")
        return None


def bullet_lines(text: str, section_hint: str, limit: int = 8) -> list[str]:
    pattern = re.compile(rf"## .*{re.escape(section_hint)}.*?(?=\n## |\Z)", re.I | re.S)
    match = pattern.search(text)
    scope = match.group(0) if match else text
    items = []
    for line in scope.splitlines():
        stripped = line.strip(" -•\t")
        if line.strip().startswith(("-", "•")) and stripped:
            items.append(stripped)
    return items[:limit]


def fallback_extract(answer: str) -> dict[str, Any]:
    text = answer.strip()
    summary = re.sub(r"\s+", " ", text[:700]).strip()
    prediction_lines = bullet_lines(text, "Prediction") or bullet_lines(text, "Plausible")
    signals = bullet_lines(text, "Signals")
    assumptions = bullet_lines(text, "Assumptions")
    next_questions = [line.strip("- •\t") for line in text.splitlines() if line.strip().endswith("?")][:8]
    return {
        "summary": summary,
        "key_predictions": [
            {"prediction": p, "time_horizon": "unknown", "confidence": 0.45} for p in prediction_lines[:6]
        ],
        "assumptions": assumptions[:8],
        "uncertainties": ["Fallback extraction could not reliably identify all uncertainties."],
        "signals_to_monitor": signals[:10],
        "next_questions": next_questions[:8],
    }


def extract(answer_payload: dict[str, Any], model: str) -> dict[str, Any]:
    answer = answer_payload.get("answer_markdown", "")
    notes = call_openai_json(model, answer) or fallback_extract(answer)
    notes["extracted_at"] = datetime.now(timezone.utc).isoformat()
    notes["extractor_model"] = model if os.getenv("OPENAI_API_KEY") else "regex-fallback"
    notes["source_question"] = answer_payload.get("selected", {}).get("selected_question", {})
    return notes


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract DeepThought structured notes.")
    parser.add_argument("answer_file")
    parser.add_argument("--model", default=os.getenv("DEEPTHOUGHT_EXTRACT_MODEL", "gpt-4.1-mini"))
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    in_path = Path(args.answer_file)
    result = extract(json.loads(in_path.read_text(encoding="utf-8")), args.model)
    out_path = Path(args.out or str(in_path).replace("_answer.json", "_notes.json"))
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
