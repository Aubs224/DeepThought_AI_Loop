# Project DeepThought

> A recursive AI inquiry engine for discovering high-leverage unknowns, asking stronger models to analyze them, and archiving the resulting forecasts, assumptions, signals, and next questions.

Project DeepThought is a small Python prototype that turns a simple loop into a research machine:

1. Generate candidate questions about big unknowns.
2. Score and select the strongest question.
3. Ask a deeper model for a long-form analysis.
4. Extract structured notes, predictions, assumptions, and signals.
5. Save everything into a durable archive.
6. Repeat.

It can run with the OpenAI API, but it also includes deterministic fallback behavior so you can test the entire pipeline without an API key.

---

## Table of Contents

- [What This Is](#what-this-is)
- [Repository Structure](#repository-structure)
- [How the Loop Works](#how-the-loop-works)
- [Requirements](#requirements)
- [Platform Notes](#platform-notes)
- [Quick Start](#quick-start)
- [Using an OpenAI API Key](#using-an-openai-api-key)
- [Running DeepThought](#running-deepthought)
- [Running Individual Scripts](#running-individual-scripts)
- [Output Files](#output-files)
- [Configuration Reference](#configuration-reference)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Safety and Practical Notes](#safety-and-practical-notes)
- [Development Ideas](#development-ideas)
- [License](#license)

---

## What This Is

Project DeepThought is a lightweight framework for recursive exploratory forecasting.

It is not a magic oracle. It is better understood as an **epistemic telescope**: a tool for repeatedly generating useful questions, producing structured analyses, and preserving the trail of reasoning so future runs can be compared, audited, or extended.

The project is especially useful for questions like:

- What major bottleneck will constrain AI deployment?
- Which technology layer becomes strategically important next?
- What signals should we monitor before a consensus forms?
- Which assumptions would flip our view of the future?
- What are we not asking yet?

DeepThought’s best use case is not “predict the future perfectly.” It is **discover better questions and track what would change your mind**.

---

## Repository Structure

```text
deepthought_project/
├── deepthought/
│   ├── generate_questions.py
│   ├── select_best_question.py
│   ├── ask_deep_model.py
│   ├── extract_structured_notes.py
│   ├── save_to_archive.py
│   ├── score_archive.py
│   └── loop.py
├── .env.example
├── requirements.txt
└── README.md
```

### Script Summary

| Script | Purpose |
|---|---|
| `generate_questions.py` | Generates candidate questions about major unknowns. |
| `select_best_question.py` | Scores candidate questions and selects the strongest one. |
| `ask_deep_model.py` | Sends the selected question to the deeper analysis model. |
| `extract_structured_notes.py` | Extracts structured predictions, assumptions, uncertainties, signals, and next questions. |
| `save_to_archive.py` | Copies the run artifacts into a durable archive and appends index records. |
| `score_archive.py` | Audits prior runs, detects repeated domains/themes, and creates diversity guidance for the next loop. |
| `loop.py` | Runs the whole pipeline for one or more iterations, with archive-aware diversity enabled by default. |

---

## How the Loop Works

A single DeepThought iteration looks like this:

```text
Candidate questions
        ↓
Question scoring and selection
        ↓
Deep model analysis
        ↓
Structured extraction
        ↓
Archive write
        ↓
Optional next iteration
```

More concretely:

1. `score_archive.py` reads previous runs and creates diversity guidance: underexplored domains, overrepresented domains, repeated themes, and recent questions to avoid.
2. `generate_questions.py` creates several candidate questions across the active domain set. By default, `loop.py` feeds it underexplored domains from the archive instead of always using the full list.
3. `select_best_question.py` scores each candidate using weighted criteria:
   - importance
   - uncertainty
   - actionability
   - novelty
   - falsifiability
4. `ask_deep_model.py` asks the selected question to a stronger model and requests a detailed analysis with current-date discipline and resolution criteria.
5. `extract_structured_notes.py` converts that analysis into machine-readable notes.
6. `save_to_archive.py` saves the artifacts into an archive directory and updates JSONL indexes.
7. `loop.py` orchestrates the whole flow.


### Archive-Aware Diversity

The updated loop includes a small self-auditor: `score_archive.py`. Before each iteration, it scans prior `runs/` and `archive/` artifacts and produces guidance like:

```text
Prefer underexplored domains this run: civilization and governance, culture and media, technology infrastructure
Penalize overrepresented domains unless the question is exceptionally new: artificial intelligence, climate and energy
Do not repeat or closely paraphrase these recent questions: ...
```

`loop.py` uses this guidance in two places:

1. **Question generation:** by default, it feeds the generator a rotating set of underexplored domains.
2. **Question selection:** it applies deterministic diversity adjustments after the judge scores each candidate. Repeated domains and close paraphrases get penalized; underexplored domains get a small bonus.

This is designed to prevent the system from falling into one giant topic gravity well, such as asking about AGI twenty-five times in a row while climate, labor, infrastructure, health, governance, and culture sit outside the observatory eating cold soup. 🥣

Disable this behavior with:

```bash
python loop.py --iterations 5 --no-diversity
```

Change how aggressively the loop narrows toward underexplored domains:

```bash
python loop.py --iterations 10 --domain-strategy underexplored --domain-window 4
```

Use all domains but still apply selection penalties:

```bash
python loop.py --iterations 10 --domain-strategy all
```

---

## Requirements

- Python 3.10 or newer recommended
- `pip`
- An OpenAI API key for model-backed runs
- Linux recommended for the smoothest experience

Python dependencies are listed in `requirements.txt`:

```text
openai>=1.30.0
python-dotenv>=1.0.1
```

The prototype can run without an API key. In that mode, it uses built-in fallback questions, heuristic scoring, fallback analysis, and regex-based extraction.

---

## Platform Notes

DeepThought works best on Linux because the setup and examples assume a Unix-style shell:

- `python3`
- `venv`
- `source`
- environment variables with `export`
- standard paths like `runs/` and `archive/`

It should also work on macOS with minimal changes.

Windows users can run it through:

- WSL, recommended
- Git Bash
- PowerShell with adjusted activation and environment-variable commands

Recommended Windows path: use WSL and follow the Linux instructions.

---

## Quick Start

Clone or unzip the project, then enter the repo:

```bash
git clone <your-repo-url>
cd deepthought_project
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run one fallback iteration without an API key:

```bash
cd deepthought
python loop.py --iterations 1
```

You should see output showing an archive record and a manifest path.

Generated files will appear in:

```text
deepthought/runs/
deepthought/archive/
```

---

## Using an OpenAI API Key

The scripts read your API key from the `OPENAI_API_KEY` environment variable.

### Option 1: Export the key directly

From your shell:

```bash
export OPENAI_API_KEY="sk-your-key-here"
```

Then run DeepThought:

```bash
cd deepthought
python loop.py --iterations 1
```

### Option 2: Use a `.env` file

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
OPENAI_API_KEY=sk-your-key-here
DEEPTHOUGHT_QUESTION_MODEL=gpt-4.1-mini
DEEPTHOUGHT_JUDGE_MODEL=gpt-4.1-mini
DEEPTHOUGHT_DEEP_MODEL=gpt-4.1
DEEPTHOUGHT_EXTRACT_MODEL=gpt-4.1-mini
DEEPTHOUGHT_MAX_TOKENS=6000
```

Then load it into your current shell:

```bash
set -a
source .env
set +a
```

Now run:

```bash
cd deepthought
python loop.py --iterations 1
```

> Note: the current scripts read environment variables through `os.getenv`. They do not automatically load `.env` by themselves unless you add `load_dotenv()` to the scripts or export the variables with `source .env` as shown above.

### Confirm your key is visible

```bash
python -c "import os; print(bool(os.getenv('OPENAI_API_KEY')))"
```

Expected output:

```text
True
```

Do not commit your `.env` file to GitHub. Add it to `.gitignore` if it is not already ignored.

---

## Running DeepThought

The main entry point is:

```bash
cd deepthought
python loop.py
```

### Basic run

```bash
python loop.py --iterations 1
```

### Multiple iterations

```bash
python loop.py --iterations 5
```

### Add delay between iterations

```bash
python loop.py --iterations 5 --sleep-seconds 10
```

### Generate more candidate questions per iteration

```bash
python loop.py --iterations 1 --count 12
```

### Restrict domains

```bash
python loop.py \
  --iterations 1 \
  --domains "artificial intelligence" "energy" "governance"
```

### Choose models

```bash
python loop.py \
  --iterations 1 \
  --question-model gpt-4.1-mini \
  --judge-model gpt-4.1-mini \
  --deep-model gpt-4.1 \
  --extract-model gpt-4.1-mini \
  --max-tokens 6000
```

The most important model flag is `--deep-model`. That is the model used for the long-form analysis.

---

## Running Individual Scripts

You can run each stage manually if you want to inspect or modify the pipeline.

All examples assume you are inside the `deepthought/` directory.

### 1. Generate candidate questions

```bash
python generate_questions.py --count 8 --out runs/test_questions.json
```

Output:

```text
runs/test_questions.json
```

### 2. Select the best question

```bash
python select_best_question.py runs/test_questions.json --out runs/test_selected.json
```

Output:

```text
runs/test_selected.json
```

### 3. Ask the deep model

```bash
python ask_deep_model.py runs/test_selected.json --out runs/test_answer.json
```

Outputs:

```text
runs/test_answer.json
runs/test_answer.md
```

### 4. Extract structured notes

```bash
python extract_structured_notes.py runs/test_answer.json --out runs/test_notes.json
```

Output:

```text
runs/test_notes.json
```

### 5. Save to archive

```bash
python save_to_archive.py runs/test_answer.json runs/test_notes.json --archive-dir archive
```

Outputs:

```text
archive/<run_id>/
archive/index.jsonl
archive/signal_watchlist.jsonl
```

### Score the Archive

Run the archive auditor by itself:

```bash
python score_archive.py --runs-dir runs --archive-dir archive
```

Print only the human-readable steering memo:

```bash
python score_archive.py --runs-dir runs --archive-dir archive --print-guidance
```

Save the score report for inspection or manual use:

```bash
python score_archive.py --runs-dir runs --archive-dir archive --out runs/archive_score.json
```

Then pass that guidance into the individual question scripts:

```bash
python generate_questions.py --count 8 --guidance-file runs/archive_score.json --out runs/test_questions.json
python select_best_question.py runs/test_questions.json --guidance-file runs/archive_score.json --out runs/test_selected.json
```

---

## Output Files

DeepThought writes two main groups of files.

### `runs/`

The `runs/` directory contains raw per-iteration files.

Example:

```text
runs/
├── 20260620T030307Z_iter001_archive_score.json
├── 20260620T030307Z_iter001_questions.json
├── 20260620T030307Z_iter001_selected.json
├── 20260620T030307Z_iter001_answer.json
├── 20260620T030307Z_iter001_answer.md
├── 20260620T030307Z_iter001_notes.json
└── 20260620T030310Z_manifest.json
```

These are useful for debugging, replaying, or inspecting each stage.

### `archive/`

The `archive/` directory contains durable, organized run records.

Example:

```text
archive/
├── index.jsonl
├── signal_watchlist.jsonl
└── 20260620T030307Z_which-bottleneck-will-most-constrain-useful/
    ├── question.json
    ├── answer.md
    ├── answer.json
    ├── notes.json
    ├── raw_answer_payload.json
    └── raw_notes_payload.json
```

### `archive/index.jsonl`

Each line is a JSON record summarizing one archived run:

```json
{
  "run_id": "20260620T030307Z_example-run",
  "created_at": "2026-06-20T03:03:07+00:00",
  "domain": "artificial intelligence",
  "question": "Which bottleneck will most constrain useful AI deployment...?",
  "summary": "Compact summary of the analysis...",
  "archive_path": "archive/20260620T030307Z_example-run",
  "signals_to_monitor": ["signal one", "signal two"],
  "prediction_count": 4
}
```

### `archive/signal_watchlist.jsonl`

Each line records the signals the system thinks are worth monitoring later.

This is one of the most useful long-term artifacts. Over time, it can become a forecast dashboard, trend monitor, or retrieval source for future runs.

---

## Configuration Reference

### `loop.py` arguments

| Argument | Default | Description |
|---|---:|---|
| `--iterations` | `1` | Number of DeepThought loops to run. |
| `--sleep-seconds` | `0.0` | Delay between iterations. |
| `--count` | `8` | Number of candidate questions to generate. |
| `--domains` | built-in list | Domains available to the generator. |
| `--no-diversity` | disabled | Turns off archive scoring and diversity steering. |
| `--recent-window` | `8` | Recent questions used for repetition penalties. |
| `--domain-strategy` | `underexplored` | `underexplored` narrows generation to low-count domains; `all` uses every provided domain. |
| `--domain-window` | `5` | Number of underexplored domains passed to the generator. |
| `--runs-dir` | `runs` | Directory for raw run files. |
| `--archive-dir` | `archive` | Directory for durable archived outputs. |
| `--question-model` | `gpt-4.1-mini` | Model used to generate candidate questions. |
| `--judge-model` | `gpt-4.1-mini` | Model used to score/select questions. |
| `--deep-model` | `gpt-4.1` | Model used for the main deep analysis. |
| `--extract-model` | `gpt-4.1-mini` | Model used to extract structured notes. |
| `--max-tokens` | `6000` | Maximum output tokens for the deep model response. |

### Environment variables

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Enables model-backed runs. Without it, fallback mode is used. |
| `DEEPTHOUGHT_QUESTION_MODEL` | Default model for `generate_questions.py`. |
| `DEEPTHOUGHT_JUDGE_MODEL` | Default model for `select_best_question.py`. |
| `DEEPTHOUGHT_DEEP_MODEL` | Default model for `ask_deep_model.py`. |
| `DEEPTHOUGHT_EXTRACT_MODEL` | Default model for `extract_structured_notes.py`. |
| `DEEPTHOUGHT_MAX_TOKENS` | Default max token count for `ask_deep_model.py`. |

Important nuance: `loop.py` currently uses its own CLI defaults for models unless you pass flags. The individual scripts read their model defaults from environment variables.

---

## Examples

### Run a cheap exploratory pass

```bash
python loop.py \
  --iterations 3 \
  --count 6 \
  --deep-model gpt-4.1-mini \
  --max-tokens 2500
```

Good for testing the archive flow without generating huge responses.

### Run a heavier analysis pass

```bash
python loop.py \
  --iterations 1 \
  --count 12 \
  --question-model gpt-4.1-mini \
  --judge-model gpt-4.1-mini \
  --deep-model gpt-4.1 \
  --extract-model gpt-4.1-mini \
  --max-tokens 8000
```

Good for a serious single run.

### Focus on AI and infrastructure

```bash
python loop.py \
  --iterations 2 \
  --domains "artificial intelligence" "technology infrastructure" "energy" "chips" "data centers"
```

### Store outputs somewhere else

```bash
python loop.py \
  --iterations 1 \
  --runs-dir ../deepthought_runs \
  --archive-dir ../deepthought_archive
```

---

## Troubleshooting

### The scripts use fallback mode even though I have a key

Check whether the key is visible to Python:

```bash
python -c "import os; print(os.getenv('OPENAI_API_KEY'))"
```

If it prints `None`, export the key again or source your `.env` file:

```bash
set -a
source .env
set +a
```

### `ModuleNotFoundError: No module named 'openai'`

Install dependencies inside your virtual environment:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### `python: command not found`

Try:

```bash
python3 loop.py --iterations 1
```

or create the environment with:

```bash
python3 -m venv .venv
```

### Windows activation looks different

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Command Prompt:

```bat
.venv\Scripts\activate.bat
```

WSL is recommended if you want to use the Linux commands exactly.

### The model call fails

The scripts catch OpenAI call failures and fall back rather than crashing. Check:

- API key validity
- account/project access
- model name availability
- network connectivity
- rate limits
- token limits

If a call fails, the script prints a message like:

```text
[ask_deep_model] LLM call failed, using fallback: ...
```

### I got JSON parsing errors from a model response

The scripts ask the model for JSON and use `response_format={"type": "json_object"}` where appropriate. If the model or API behavior changes, malformed JSON may still happen. The current code catches failures and uses fallback logic.

### The outputs feel repetitive

Archive-aware diversity is enabled by default:

```bash
python loop.py --iterations 10
```

For a stronger diversity push, reduce the underexplored domain window:

```bash
python loop.py --iterations 10 --domain-strategy underexplored --domain-window 3
```

To inspect what the system thinks is overused:

```bash
python score_archive.py --runs-dir runs --archive-dir archive --print-guidance
```

To keep all domains in the generator but still penalize repeated selections:

```bash
python loop.py --iterations 10 --domain-strategy all
```

---

## Safety and Practical Notes

DeepThought produces speculative analysis. Treat it as a structured thinking aid, not a source of truth.

Recommended habits:

- Do not treat outputs as financial, legal, medical, or safety-critical advice.
- Review predictions manually before acting on them.
- Track confidence and assumptions.
- Prefer falsifiable signals over vibes.
- Compare old predictions against later evidence.
- Keep API keys private.
- Do not commit `.env`, raw secrets, or sensitive archives.

The system is strongest when it is used as a question engine and archive, not as an authority machine.

---

## Development Ideas

DeepThought is intentionally small. Good next upgrades include:

### 1. Automatic `.env` loading

Add this near the top of each script that reads environment variables:

```python
from dotenv import load_dotenv

load_dotenv()
```

### 2. Retrieval over past runs

Before generating new questions, retrieve summaries from `archive/index.jsonl` and unresolved questions from prior `notes.json` files.

### 3. Prediction tracking

Create a script that reads `archive/index.jsonl` and `notes.json`, extracts dated predictions, and lets you mark them as:

- pending
- supported
- contradicted
- ambiguous

### 4. Signal monitor

Use `archive/signal_watchlist.jsonl` as the basis for a scheduled monitoring system.

Example future script:

```text
monitor_signals.py
```

It could search news, papers, market data, policy updates, or internal documents and compare new evidence against stored signals.

### 5. Better judging

Expand `select_best_question.py` with multiple judges:

- skeptic
- historian
- builder
- investor
- policy analyst
- scientist

Then aggregate their scores.

### 6. Web-grounded research mode

Add a research step before the deep analysis:

```text
research_context.py
```

This could gather current facts, recent papers, official statistics, and news before asking the deep model to reason.

### 7. Dashboard

Build a small dashboard for:

- archived questions
- predictions by horizon
- signals to monitor
- confidence trends
- recurring themes
- contradicted assumptions

### 8. Agent council mode

Split the analysis into roles:

- Oracle: question generator
- Judge: prompt selector
- Skeptic: assumption attacker
- Historian: precedent finder
- Builder: practical implications
- Auditor: structured extraction
- Archivist: durable storage

Tiny pantheon, big notebook. 🧠📚

---

## Suggested `.gitignore`

Consider adding:

```gitignore
.venv/
.env
__pycache__/
*.pyc
runs/
archive/
.DS_Store
```

Whether to ignore `runs/` and `archive/` depends on your workflow. If you want to version example outputs, commit a small curated sample instead of your full archive.

---

## License

*SEE LICENSE FILE*

---

## One-Sentence Summary

Project DeepThought is a recursive AI question-discovery and forecasting archive: generate important unknowns, select the strongest question, produce deep analysis, extract structured notes, save the artifacts, and repeat.
