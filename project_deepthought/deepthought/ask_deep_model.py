#!/usr/bin/env python3
"""Ask the selected DeepThought question to a deeper model."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

SYSTEM_PROMPT = """You are DeepThought's Deep Analysis model.
Think rigorously and write an analysis that distinguishes evidence, assumptions,
uncertainties, plausible scenarios, and testable predictions. Avoid theatrical certainty.
Use clear sections and concrete signals to monitor.
"""

DEEP_PROMPT_TEMPLATE = """Question:
{question}

Context:
Current date: {current_date}
Domain: {domain}
Why it matters: {why}
Initial signals to watch: {signals}

Produce a deep analysis with these sections:
1. Executive synthesis
2. Why this question is hard
3. Current forces and constraints
4. Three to five plausible futures
5. Key assumptions
6. Predictions with time horizons and resolution criteria
7. Signals that would change the forecast
8. What a builder, policymaker, investor, and citizen should watch
9. Best next questions

Important date discipline:
- Do not present dates before the current date as future predictions.
- For every prediction, include a deadline or time window and what would count as evidence it came true or false.
"""


def fallback_answer(selected: dict) -> str:
    q = selected["selected_question"]
    signals = ", ".join(q.get("signals_to_watch", [])) or "none listed"
    return f"""# DeepThought Analysis: {q.get('question')}

## Executive synthesis
This fallback analysis is generated without an API key. The question appears important because: {q.get('why_it_matters', 'not specified')}.

## Why this question is hard
The answer depends on interacting technical, economic, political, and cultural systems. Each system moves at a different tempo, which makes linear forecasting brittle.

## Current forces and constraints
- Domain: {q.get('domain', 'unknown')}
- Time horizon: {q.get('time_horizon', 'unknown')}
- Early signals: {signals}

## Plausible futures
1. **Acceleration path:** adoption compounds quickly because incentives align.
2. **Bottleneck path:** deployment slows because reliability, regulation, infrastructure, or trust fails to keep pace.
3. **Fragmentation path:** different regions and sectors develop incompatible norms and stacks.

## Key assumptions
- The observable signals are relevant proxies.
- The domain remains strategically important.
- Adjacent systems do not radically change the baseline first.

## Predictions with time horizons and resolution criteria
- Near term: public narratives will over-index on the most visible failures and successes.
- Medium term: infrastructure and trust will matter as much as raw capability.
- Long term: the winning path will be shaped by institutions that can learn quickly without losing legitimacy.

## Signals that would change the forecast
- Clear evidence that one bottleneck dominates all others.
- Major policy, infrastructure, or market shifts.
- Repeated failures that alter public trust.

## Best next questions
- What evidence would distinguish the plausible futures fastest?
- Which actor has the strongest incentive to resolve the bottleneck?
- What would be visible six months before the consensus notices?
"""


def call_openai_text(model: str, prompt: str, max_tokens: int) -> str | None:
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
                {"role": "user", "content": prompt},
            ],
            temperature=0.45,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        print(f"[ask_deep_model] LLM call failed, using fallback: {exc}")
        return None


def ask(selected: dict, model: str, max_tokens: int) -> dict:
    q = selected["selected_question"]
    prompt = DEEP_PROMPT_TEMPLATE.format(
        question=q.get("question", ""),
        current_date=datetime.now(timezone.utc).date().isoformat(),
        domain=q.get("domain", ""),
        why=q.get("why_it_matters", ""),
        signals=", ".join(q.get("signals_to_watch", [])),
    )
    answer = call_openai_text(model, prompt, max_tokens) or fallback_answer(selected)
    return {
        "answered_at": datetime.now(timezone.utc).isoformat(),
        "deep_model": model if os.getenv("OPENAI_API_KEY") else "fallback-analysis",
        "prompt": prompt,
        "answer_markdown": answer,
        "selected": selected,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask deep model to answer selected question.")
    parser.add_argument("selected_file")
    parser.add_argument("--model", default=os.getenv("DEEPTHOUGHT_DEEP_MODEL", "gpt-4.1"))
    parser.add_argument("--max-tokens", type=int, default=int(os.getenv("DEEPTHOUGHT_MAX_TOKENS", "6000")))
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    in_path = Path(args.selected_file)
    result = ask(json.loads(in_path.read_text(encoding="utf-8")), args.model, args.max_tokens)
    out_path = Path(args.out or str(in_path).replace("_selected.json", "_answer.json"))
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    md_path = Path(str(out_path).replace("_answer.json", "_answer.md"))
    md_path.write_text(result["answer_markdown"], encoding="utf-8")
    print(out_path)
    print(md_path)


if __name__ == "__main__":
    main()
