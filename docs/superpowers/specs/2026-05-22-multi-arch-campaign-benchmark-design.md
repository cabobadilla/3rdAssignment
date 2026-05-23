# Multi-Architecture Campaign Benchmark — Design Spec

**Date:** 2026-05-22
**Project:** `Assignment3/multi-arch-benchmark/`
**Status:** Approved

## Purpose

Build a Gradio web app that runs the same marketing-campaign brief through three different OpenAI Agents SDK architectures (sequential, orchestrator, parallel+judge), then displays each architecture's final output side-by-side along with token usage, latency, cost, and LLM-judge quality scores. Goal: quantify the tradeoffs between agent orchestration patterns.

## Constraints

- **Use the OpenAI Agents SDK** (`agents.Agent`, `agents.Runner`) — the same SDK used by the existing `campaign-web-app/`.
- **Same agent personas across architectures**: Creative Director, Strategist, Copywriter. Only the topology changes.
- **Each agent emits exactly one best output** — no menus of options, no human selection between stages.
- **Fully autonomous run** — user provides only the brief; no human-in-the-loop.

## Architectures

All three architectures share the same three agent personas. Differences are only in orchestration.

### Architecture 1 — Sequential Pipeline

```
brief → Creative Director → idea → Strategist → strategy → Copywriter → tweets (final)
```

Three sequential `Runner.run` calls. Each agent's output is the input to the next. Equivalent to the existing app minus human-in-the-loop selection.

### Architecture 2 — Orchestrator (Director-led)

Creative Director is the central agent. The Strategist and Copywriter are exposed to it as **SDK function tools**:

```python
@function_tool
async def consult_strategist(idea: str) -> str: ...

@function_tool
async def consult_copywriter(strategy: str) -> str: ...
```

The Director generates a single best campaign idea, delegates to the Strategist via tool call, evaluates the response, delegates to the Copywriter, evaluates, and produces the final campaign. Capped at a max-turns limit (e.g., 8) to bound cost.

### Architecture 3 — Parallel + Judge

All 3 agents receive the **same brief** and produce a **complete campaign from their own perspective** (idea + strategy + tweets), in parallel via `asyncio.gather`. A 4th internal **Arch-3 Judge** picks (or merges) the best complete campaign.

This is intentionally distinct from Architecture 1: in Arch 1 each agent does *its specialty stage*; in Arch 3 each agent does the *full job* through its own lens.

### Benchmark Judge (separate from Arch 3's internal judge)

After all three architectures finish, a single **Benchmark Judge** receives all three final outputs and the original brief, then returns structured scores for each architecture:

```python
class JudgeScore(BaseModel):
    architecture: str
    creativity: int        # 1-10
    strategic_fit: int     # 1-10
    copy_quality: int      # 1-10
    overall: int           # 1-10
    reasoning: str
```

Same judge for all three architectures → consistent scoring.

## File Layout

```
multi-arch-benchmark/
├── app.py                 # Gradio UI entrypoint
├── agents_lib.py          # Agent factories (build_creative_director, etc.)
├── architectures.py       # run_sequential, run_orchestrator, run_parallel_judge
├── benchmark.py           # run_benchmark() orchestrator + metrics collection
├── judge.py               # Benchmark Judge agent + Arch-3 internal judge
├── metrics.py             # Dataclasses for metrics
├── requirements.txt
└── .env.example
```

## Data Model (`metrics.py`)

```python
@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float

@dataclass
class AgentCall:
    agent_name: str
    latency_s: float
    usage: TokenUsage

@dataclass
class RunMetrics:
    architecture: str          # "sequential" | "orchestrator" | "parallel_judge"
    calls: list[AgentCall]
    total_latency_s: float
    total_tokens: int
    total_cost_usd: float
    final_output: str
    error: str | None = None

@dataclass
class BenchmarkRun:
    brief: str
    model_config: dict
    runs: list[RunMetrics]
    scores: list[JudgeScore]
```

## Data Flow

1. User fills the brief textbox, picks per-agent models (4 dropdowns: CD, Strat, Copy, Judge), and selects execution mode (sequential / parallel) → clicks **Run Benchmark**.
2. `benchmark.run_benchmark(brief, config)` invokes the three architecture functions (parallel via `asyncio.gather` or sequentially per the toggle).
3. Each architecture function wraps every `Runner.run` call to capture `result.usage` and latency (`time.monotonic()`), accumulating into `RunMetrics`.
4. After all three complete, the Benchmark Judge reads all three final outputs + brief and returns three `JudgeScore` objects via structured output.
5. The UI renders the comparison view.

## Pricing Table

A small static dict in `metrics.py` mapping model → `(input_price_per_1k, output_price_per_1k)` for cost estimation. Hardcoded for the curated model list: `gpt-4o-mini`, `gpt-4o`, `gpt-4.1-mini`, `gpt-4.1`.

## UI Layout (Gradio)

- **Header**: title + one-line description
- **Brief**: 3-line textbox
- **Configuration** (collapsible accordion):
  - 4 model dropdowns (CD, Strategist, Copywriter, Judge)
  - Execution mode radio: Sequential / Parallel
- **Run Benchmark** button + status text
- **Tabs**:
  - **📊 Comparison**: dataframe with columns `Architecture | Tokens | Latency (s) | Cost ($) | Creativity | Strategic Fit | Copy Quality | Overall`. Below: collapsible Judge reasoning per architecture.
  - **📄 Final Outputs**: 3 columns side-by-side, each showing one architecture's final campaign.
  - **🔍 Per-Call Detail**: per-architecture breakdown of each agent call (name, tokens, latency).

Model dropdowns are curated (no free text). No export, no persistence — display only.

## Error Handling

| Scenario | Behavior |
| --- | --- |
| Missing `OPENAI_API_KEY` | Raise on startup (parity with existing app). |
| Empty brief | Validation message in status; no API call. |
| One architecture fails | Mark its row as `ERROR: <msg>`, continue with the others. |
| Benchmark Judge fails | Show outputs + metrics; mark judge columns `N/A`. |
| Arch 2 hits max-turns | Record the fact in metrics; use last produced output. |
| Rate limits / transient errors | Rely on SDK's built-in retry; surface message if still failing. |

A single failed architecture does not sink the benchmark.

## Testing

- **`test_metrics.py`** — pure-function tests for cost math and dataclass serialization.
- **`test_architectures.py`** — patch `Runner.run` with stub returning canned outputs + fake usage; verify each architecture wires inputs/outputs correctly and accumulates metrics.
- **`test_judge.py`** — patch judge `Runner.run` with canned `JudgeScore` JSON; verify parsing.
- **`test_benchmark_smoke.py`** — optional live end-to-end run, gated on `OPENAI_API_KEY`, skipped in CI.

No UI/Gradio tests — manual verification on first run.

## Dependencies

```
openai-agents
gradio
python-dotenv
nest_asyncio
pydantic
```

## Success Criteria

1. One click runs all three architectures end-to-end on `gpt-4o-mini` for under $0.05 per benchmark.
2. UI shows: three final outputs side-by-side, a metrics dataframe (tokens / latency / cost / judge scores), and per-architecture judge reasoning.
3. Token counts come from real `Runner.run` usage data, not estimates.
4. A failed architecture does not crash the benchmark — the remaining two still produce results.

## Out of Scope (v1)

- Persistence / history of past benchmark runs
- Streaming token-by-token output display
- Authentication or multi-user support
- Cross-run prompt or result caching
- Per-architecture prompt customization in the UI
- CSV / JSON export
