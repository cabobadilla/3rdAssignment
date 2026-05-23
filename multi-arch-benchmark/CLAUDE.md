# CLAUDE.md — Multi-Arch Campaign Benchmark

A Gradio app that runs the same marketing-campaign brief through three OpenAI Agents SDK orchestration patterns, then reports token usage, latency, cost, and LLM-judge quality scores. Built to make the tradeoffs between agent architectures legible.

## Stack

- Python 3.10+ (developed on 3.13)
- `openai-agents` (Agents SDK) — `Agent`, `Runner`, `function_tool`
- `gradio` — UI
- `pydantic` (used implicitly by the judge JSON contract)
- `pytest`, `pytest-asyncio` — tests

## Module map

| File | Responsibility |
| --- | --- |
| `app.py` | Gradio entrypoint. Theme, CSS, layout, event wiring. The only place that touches the UI. |
| `agents_lib.py` | Agent factories. The only place `Agent(...)` is constructed. |
| `architectures.py` | The three orchestration topologies plus `run_agent_call` helper that captures usage and latency. |
| `benchmark.py` | `BenchmarkConfig` and `run_benchmark` — runs the enabled architectures (sequential or parallel) and the Benchmark Judge. |
| `judge.py` | Benchmark Judge agent and JSON parsing. |
| `metrics.py` | Dataclasses (`TokenUsage`, `AgentCall`, `RunMetrics`, `JudgeScore`, `BenchmarkRun`) and the `PRICING` table. |

## The three architectures

1. **Sequential Pipeline** — Creative Director → Strategist → Copywriter. Linear chain of three `Runner.run` calls.
2. **Director-Orchestrator** — The Creative Director is built with `function_tool` wrappers around the other two agents; it decides when to delegate and when to revise.
3. **Parallel + Judge** — All three agents produce a complete campaign in parallel via `asyncio.gather`; an internal judge merges/picks the best.

A separate **Benchmark Judge** (always the same) scores the three architectures' final outputs on creativity, strategic fit, copy quality, and overall — returning structured JSON.

## How to run

```bash
cd Assignment3/multi-arch-benchmark
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add OPENAI_API_KEY
python app.py
```

Open `http://127.0.0.1:7860`.

## How to test

```bash
PYTHONPATH=. pytest -v
```

All tests are unit-level with `Runner.run` mocked. There are no live API tests in CI.

## Key conventions

- **Every agent emits exactly one best output.** No menus, no filtering, no human-in-the-loop. Prompts in `agents_lib.py` enforce this.
- **Usage is read from `result.context_wrapper.usage`** (real SDK path), with a fallback to `result.usage` for mock testing. See `_extract_usage` in `architectures.py`.
- **`benchmark.py` uses `_arch_runners()` (a function, not a literal dict)** so tests can patch `benchmark.run_sequential` and friends.
- **The UI's CSS uses `!important` liberally** to override Gradio defaults. Theme + CSS are applied at `demo.launch(...)`, not in the `Blocks` constructor (Gradio 6 moved them).
- **Fonts**: Fraunces (display serif) + Manrope (body sans) + JetBrains Mono (data). Avoid Inter — explicitly flagged as a generic AI choice.

## Pricing table

Static dict in `metrics.py`. Estimates only — not billable, not authoritative. Update when prices change.

## Error handling

- One failing architecture does not sink the benchmark. `_safe_run` wraps each runner in try/except and records the error on the `RunMetrics`.
- A failed judge is caught separately; the UI shows the architectures' outputs and marks judge columns as `—`.
- Missing `OPENAI_API_KEY` raises on startup.

## Out of scope

History/persistence, streaming, auth, caching, prompt customisation in the UI, exports. Documented in `PLAN.md → Future Roadmap`.
