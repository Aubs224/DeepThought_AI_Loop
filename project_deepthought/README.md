# Project DeepThought 🧠⚙️

A tiny recursive inquiry engine.

One loop does this:

1. Generate candidate questions about major unknowns.
2. Score and select the strongest question.
3. Send it to a deeper model for long-form analysis.
4. Extract structured predictions, assumptions, uncertainties, signals, and next questions.
5. Save everything into an archive.

The scripts run without an API key using fallback logic, so you can test the gears before connecting the oracle-cloud.

## Install

```bash
cd deepthought_project
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional:

```bash
cp .env.example .env
export OPENAI_API_KEY="sk-your-key-here"
```

Or just set the environment variable in your shell.

## Run the full loop

```bash
cd deepthought
python loop.py --iterations 1
```

Run three iterations with a pause:

```bash
python loop.py --iterations 3 --sleep-seconds 10
```

## Run scripts individually

```bash
python generate_questions.py --count 8 --out runs/demo_questions.json
python select_best_question.py runs/demo_questions.json
python ask_deep_model.py runs/demo_selected.json
python extract_structured_notes.py runs/demo_answer.json
python save_to_archive.py runs/demo_answer.json runs/demo_notes.json --archive-dir archive
```

## Output structure

```text
deepthought/
  runs/
    *_questions.json
    *_selected.json
    *_answer.json
    *_answer.md
    *_notes.json
  archive/
    index.jsonl
    signal_watchlist.jsonl
    <run_id>/
      question.json
      answer.md
      answer.json
      notes.json
```

## The six scripts

| Script | Purpose |
| --- | --- |
| `generate_questions.py` | Creates candidate high-leverage unknowns. |
| `select_best_question.py` | Scores candidates and selects the strongest one. |
| `ask_deep_model.py` | Sends the selected prompt to the deep model. |
| `extract_structured_notes.py` | Extracts predictions, assumptions, uncertainties, signals, and next questions. |
| `save_to_archive.py` | Saves the run and appends archive indexes. |
| `loop.py` | Runs the whole pipeline repeatedly. |

## Notes

- Uses OpenAI if `OPENAI_API_KEY` is present.
- Falls back to deterministic local behavior if no key is present.
- The archive is designed to become a retrieval substrate later.
- The `signal_watchlist.jsonl` file is the seed of an epistemic weather station. 🌦️
