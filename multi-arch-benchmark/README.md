# Multi-Arch Campaign Benchmark

A Gradio app that runs the same marketing campaign brief through three OpenAI Agents SDK
architectures and reports token usage, latency, cost, and LLM-judge quality scores.

## Architectures

1. **Sequential** — Creative Director → Strategist → Copywriter (linear).
2. **Orchestrator** — Creative Director delegates to Strategist and Copywriter as SDK tools.
3. **Parallel + Judge** — three agents each produce a full campaign from their perspective; an internal judge picks/merges the best.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your OPENAI_API_KEY
python app.py
```

Open http://127.0.0.1:7860 and run a brief.

## Tests

```bash
PYTHONPATH=. pytest -v
```
