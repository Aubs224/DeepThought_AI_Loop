#!/usr/bin/env python3
"""Generate candidate DeepThought questions.

This script asks an LLM to propose high-leverage unknowns. If no API key is
configured, it falls back to deterministic seed questions so the project still
runs out of the box.
"""
from __future__ import annotations

import argparse
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DOMAINS = [
    "artificial intelligence",
    "technology infrastructure",
    "state of the world",
    "civilization and governance",
    "economics and labor",
    "science and health",
    "climate and energy",
    "culture and media",
]

SYSTEM_PROMPT = """You are DeepThought's Question-Builder.
Your job is to discover questions that matter because they reveal unknown unknowns.
Return only valid JSON matching this shape:
{
  "questions": [
    {
      "domain": "short domain",
      "question": "one precise, high-leverage question",
      "why_it_matters": "brief reason",
      "time_horizon": "near|medium|long",
      "signals_to_watch": ["observable signal", "observable signal"]
    }
  ]
}
"""

USER_PROMPT_TEMPLATE = """Generate {count} unusually strong questions about major unknowns.

Current date: {current_date}
Domains to consider: {domains}

{archive_guidance}

Criteria:
- Important enough that the answer would change decisions.
- Actually uncertain, not a disguised essay topic.
- Somewhat falsifiable through future signals.
- Specific enough to analyze deeply.
- Avoid vague cosmic pudding.
- Do not make predictions for dates before the current date.
"""

FALLBACK_QUESTIONS = [
    {
        "domain": "artificial intelligence",
        "question": "Which bottleneck will most constrain useful AI deployment over the next five years: model capability, reliable evaluation, energy, regulation, distribution, or trust?",
        "why_it_matters": "The limiting factor determines where builders, investors, and institutions should focus.",
        "time_horizon": "medium",
        "signals_to_watch": ["enterprise deployment failure modes", "AI energy procurement", "regulatory enforcement patterns"],
    },
    {
        "domain": "economics and labor",
        "question": "Which forms of work will become more valuable because AI exists, rather than less valuable?",
        "why_it_matters": "It helps forecast labor adaptation instead of only labor displacement.",
        "time_horizon": "medium",
        "signals_to_watch": ["wage premiums for AI-complementary roles", "new job titles", "workflow software adoption"],
    },
    {
        "domain": "technology infrastructure",
        "question": "Will the next decade's decisive infrastructure layer be compute, data provenance, identity, robotics, chips, energy, or agent orchestration?",
        "why_it_matters": "Infrastructure choices shape competitive advantage and public policy.",
        "time_horizon": "long",
        "signals_to_watch": ["capex concentration", "standards adoption", "supply chain chokepoints"],
    },
    {
        "domain": "civilization and governance",
        "question": "Can democratic institutions adapt decision cycles quickly enough for AI-accelerated economic and information systems?",
        "why_it_matters": "Governance speed and legitimacy may become a central constraint.",
        "time_horizon": "long",
        "signals_to_watch": ["AI-related legal precedent", "public trust surveys", "emergency regulatory mechanisms"],
    },
    {
        "domain": "culture and media",
        "question": "What happens to shared reality when synthetic media becomes abundant, cheap, personalized, and emotionally convincing?",
        "why_it_matters": "Media trust affects politics, education, relationships, and markets.",
        "time_horizon": "medium",
        "signals_to_watch": ["authentication standards", "platform labeling norms", "synthetic media scandals"],
    },
]


def now_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def call_openai_json(model: str, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.9,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:  # pragma: no cover - helpful CLI behavior
        print(f"[generate_questions] LLM call failed, using fallback: {exc}")
        return None


def generate_questions(count: int, domains: list[str], model: str, archive_guidance: str | None = None) -> dict[str, Any]:
    prompt = USER_PROMPT_TEMPLATE.format(
        count=count,
        domains=", ".join(domains),
        current_date=datetime.now(timezone.utc).date().isoformat(),
        archive_guidance=archive_guidance or "No archive guidance provided.",
    )
    data = call_openai_json(model, SYSTEM_PROMPT, prompt)
    if not data or "questions" not in data:
        pool = FALLBACK_QUESTIONS.copy()
        random.shuffle(pool)
        data = {"questions": pool[:count]}
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    data["generator_model"] = model if os.getenv("OPENAI_API_KEY") else "fallback-seed"
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate DeepThought candidate questions.")
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--domains", nargs="*", default=DEFAULT_DOMAINS)
    parser.add_argument("--model", default=os.getenv("DEEPTHOUGHT_QUESTION_MODEL", "gpt-4.1-mini"))
    parser.add_argument("--guidance-file", default=None, help="Optional JSON file from score_archive.py used to diversify questions.")
    parser.add_argument("--out", default=f"runs/{now_id()}_questions.json")
    args = parser.parse_args()

    archive_guidance = None
    if args.guidance_file:
        guidance_data = json.loads(Path(args.guidance_file).read_text(encoding="utf-8"))
        archive_guidance = guidance_data.get("guidance_text")
    result = generate_questions(args.count, args.domains, args.model, archive_guidance)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
