# Multi-Architecture Campaign Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Gradio web app that runs the same marketing campaign brief through three OpenAI Agents SDK architectures (sequential, orchestrator, parallel+judge), then displays each architecture's final output side-by-side with token, latency, cost, and LLM-judge quality scores.

**Architecture:** Three architectures share the same three agent personas (Creative Director, Strategist, Copywriter); only orchestration topology differs. A separate Benchmark Judge scores all three on creativity, strategic fit, and copy quality. Plain Python modules + Gradio UI. No persistence.

**Tech Stack:** Python 3.10+, `openai-agents` (Agents SDK), `gradio`, `pydantic` (structured judge output), `python-dotenv`, `nest_asyncio`, `pytest` for tests.

**Spec:** `Assignment3/docs/superpowers/specs/2026-05-22-multi-arch-campaign-benchmark-design.md`

---

## File Structure

```
Assignment3/multi-arch-benchmark/
├── app.py                 # Gradio UI entrypoint
├── agents_lib.py          # Agent factories (build_creative_director, build_strategist, build_copywriter, build_arch3_full_agent)
├── architectures.py       # run_sequential, run_orchestrator, run_parallel_judge
├── benchmark.py           # run_benchmark() orchestrator + metrics aggregation
├── judge.py               # Benchmark Judge agent + Arch-3 internal judge
├── metrics.py             # TokenUsage, AgentCall, RunMetrics, BenchmarkRun dataclasses + pricing
├── requirements.txt
├── .env.example
└── tests/
    ├── __init__.py
    ├── test_metrics.py
    ├── test_architectures.py
    ├── test_judge.py
    └── test_benchmark.py
```

Each module has one clear job. `agents_lib.py` is the only place agents get constructed. `architectures.py` only orchestrates; it doesn't build agents. `benchmark.py` only aggregates; it doesn't run agents.

---

## Task 1: Project Scaffold

**Files:**
- Create: `Assignment3/multi-arch-benchmark/requirements.txt`
- Create: `Assignment3/multi-arch-benchmark/.env.example`
- Create: `Assignment3/multi-arch-benchmark/tests/__init__.py`

- [ ] **Step 1: Create the directory and empty init**

```bash
mkdir -p Assignment3/multi-arch-benchmark/tests
touch Assignment3/multi-arch-benchmark/tests/__init__.py
```

- [ ] **Step 2: Write `requirements.txt`**

```
openai-agents
gradio
python-dotenv
nest_asyncio
pydantic
pytest
pytest-asyncio
```

- [ ] **Step 3: Write `.env.example`**

```
OPENAI_API_KEY=sk-your-key-here
```

- [ ] **Step 4: Install dependencies into a venv**

```bash
cd Assignment3/multi-arch-benchmark
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Expected: clean install, no errors. Note the venv path; later commands run inside it.

- [ ] **Step 5: Add the venv to `.gitignore`**

Append to `Assignment3/.gitignore` (create if missing):

```
multi-arch-benchmark/.venv/
multi-arch-benchmark/__pycache__/
multi-arch-benchmark/**/__pycache__/
multi-arch-benchmark/.pytest_cache/
multi-arch-benchmark/.env
```

- [ ] **Step 6: Commit**

```bash
git add Assignment3/multi-arch-benchmark/requirements.txt Assignment3/multi-arch-benchmark/.env.example Assignment3/multi-arch-benchmark/tests/__init__.py Assignment3/.gitignore
git commit -m "chore: scaffold multi-arch-benchmark project"
```

---

## Task 2: Metrics Dataclasses

**Files:**
- Create: `Assignment3/multi-arch-benchmark/metrics.py`
- Test: `Assignment3/multi-arch-benchmark/tests/test_metrics.py`

- [ ] **Step 1: Write the failing test**

`tests/test_metrics.py`:

```python
import pytest

from metrics import (
    TokenUsage,
    AgentCall,
    RunMetrics,
    JudgeScore,
    BenchmarkRun,
    estimate_cost,
    PRICING,
)


def test_pricing_has_required_models():
    for model in ("gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"):
        assert model in PRICING


def test_estimate_cost_gpt_4o_mini():
    # gpt-4o-mini pricing per 1k tokens (as of plan date):
    # input  $0.00015, output $0.0006
    cost = estimate_cost("gpt-4o-mini", prompt_tokens=1000, completion_tokens=1000)
    assert cost == pytest.approx(0.00015 + 0.0006, rel=1e-6)


def test_estimate_cost_unknown_model_returns_zero():
    assert estimate_cost("nonexistent-model", 1000, 1000) == 0.0


def test_token_usage_dataclass_round_trip():
    usage = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30, cost_usd=0.001)
    assert usage.total_tokens == 30


def test_run_metrics_aggregates_calls():
    calls = [
        AgentCall(
            agent_name="cd",
            latency_s=1.0,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20, cost_usd=0.0001),
        ),
        AgentCall(
            agent_name="strat",
            latency_s=2.0,
            usage=TokenUsage(prompt_tokens=20, completion_tokens=20, total_tokens=40, cost_usd=0.0002),
        ),
    ]
    run = RunMetrics(
        architecture="sequential",
        calls=calls,
        total_latency_s=3.0,
        total_tokens=60,
        total_cost_usd=0.0003,
        final_output="hello",
    )
    assert run.total_tokens == sum(c.usage.total_tokens for c in run.calls)
```

- [ ] **Step 2: Run test, expect ImportError**

```bash
cd Assignment3/multi-arch-benchmark
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_metrics.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'metrics'`.

- [ ] **Step 3: Implement `metrics.py`**

```python
"""Dataclasses and cost estimation for the multi-arch campaign benchmark."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# Per-1k-token pricing (USD). Conservative public values; adjust if needed.
PRICING: dict[str, tuple[float, float]] = {
    # model: (input_per_1k, output_per_1k)
    "gpt-4o-mini": (0.00015, 0.00060),
    "gpt-4o":      (0.00250, 0.01000),
    "gpt-4.1-mini": (0.00040, 0.00160),
    "gpt-4.1":     (0.00200, 0.00800),
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Return estimated USD cost for a single agent call."""
    if model not in PRICING:
        return 0.0
    in_rate, out_rate = PRICING[model]
    return (prompt_tokens / 1000.0) * in_rate + (completion_tokens / 1000.0) * out_rate


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
    error: Optional[str] = None


@dataclass
class JudgeScore:
    architecture: str
    creativity: int
    strategic_fit: int
    copy_quality: int
    overall: int
    reasoning: str


@dataclass
class BenchmarkRun:
    brief: str
    model_config: dict
    runs: list[RunMetrics] = field(default_factory=list)
    scores: list[JudgeScore] = field(default_factory=list)
```

- [ ] **Step 4: Run tests, expect pass**

```bash
PYTHONPATH=. pytest tests/test_metrics.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add Assignment3/multi-arch-benchmark/metrics.py Assignment3/multi-arch-benchmark/tests/test_metrics.py
git commit -m "feat: metrics dataclasses and cost estimation"
```

---

## Task 3: Agent Factories

**Files:**
- Create: `Assignment3/multi-arch-benchmark/agents_lib.py`

This module produces `agents.Agent` instances. No tests in this task — agents are thin wrappers around prompts; we'll test them indirectly through architectures.

- [ ] **Step 1: Implement `agents_lib.py`**

```python
"""Agent factories. The only place Agent() is constructed."""
from __future__ import annotations

from agents import Agent


_CREATIVE_DIRECTOR_INSTRUCTIONS = (
    "You are a Creative Director at a top advertising agency. "
    "Given a product launch brief, produce exactly ONE best campaign idea. "
    "Output format: a single block with **Name** (bold) on the first line, "
    "*Tagline* (italic) on the second line, and a 2-3 sentence description of "
    "the concept and target audience. Do not produce multiple options."
)

_STRATEGIST_INSTRUCTIONS = (
    "You are a Marketing Strategist. You receive ONE campaign idea. "
    "Produce a single strategic refinement explaining why it works and how it "
    "should be positioned. Output format: **Name** (bold), then 3-4 sentences "
    "covering market fit, audience, and the differentiating angle. "
    "Do not produce multiple options."
)

_COPYWRITER_INSTRUCTIONS = (
    "You are a social media Copywriter. You receive ONE refined campaign concept. "
    "Produce exactly ONE set of 3 tweets that best embody the campaign. "
    "Each tweet under 280 characters, with 2-3 relevant hashtags, native to the "
    "target audience and location. Do not produce alternative sets."
)

_ARCH3_FULL_CAMPAIGN_INSTRUCTIONS = (
    "You are a {role}. Given the brief, produce a COMPLETE campaign output "
    "from your professional perspective. Include: (1) one campaign idea with "
    "Name and Tagline, (2) a 2-3 sentence strategic rationale, (3) three short "
    "social posts (tweets). Output a single best version. Do not produce multiple options."
)


def build_creative_director(model: str) -> Agent:
    return Agent(name="Creative Director", model=model, instructions=_CREATIVE_DIRECTOR_INSTRUCTIONS)


def build_strategist(model: str) -> Agent:
    return Agent(name="Strategist", model=model, instructions=_STRATEGIST_INSTRUCTIONS)


def build_copywriter(model: str) -> Agent:
    return Agent(name="Copywriter", model=model, instructions=_COPYWRITER_INSTRUCTIONS)


def build_arch3_full_agent(role: str, model: str) -> Agent:
    """Used in Architecture 3: each agent produces a full campaign from its own perspective."""
    return Agent(
        name=f"{role} (Full)",
        model=model,
        instructions=_ARCH3_FULL_CAMPAIGN_INSTRUCTIONS.format(role=role),
    )
```

- [ ] **Step 2: Smoke import**

```bash
PYTHONPATH=. python -c "from agents_lib import build_creative_director, build_strategist, build_copywriter, build_arch3_full_agent; print('ok')"
```

Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add Assignment3/multi-arch-benchmark/agents_lib.py
git commit -m "feat: agent factories for the three personas + arch3 full agents"
```

---

## Task 4: Runner Helper (capture usage + latency)

**Files:**
- Modify: `Assignment3/multi-arch-benchmark/architectures.py` (create)
- Test: `Assignment3/multi-arch-benchmark/tests/test_architectures.py` (create)

This task creates one helper used by all three architecture functions: `run_agent_call(agent, input_text, model_for_cost)` returns `(text_output, AgentCall)`.

- [ ] **Step 1: Write the failing test**

`tests/test_architectures.py`:

```python
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from metrics import TokenUsage


class _FakeUsage:
    def __init__(self, p, c):
        self.input_tokens = p
        self.output_tokens = c
        self.total_tokens = p + c


class _FakeResult:
    def __init__(self, text, p_tokens, c_tokens):
        self.final_output = text
        # Mirror real Agents SDK shape we read from
        self.usage = _FakeUsage(p_tokens, c_tokens)


@pytest.mark.asyncio
async def test_run_agent_call_returns_text_and_metrics():
    from architectures import run_agent_call

    fake = _FakeResult("the output", 100, 50)
    fake_agent = MagicMock()
    fake_agent.name = "Test Agent"

    with patch("architectures.Runner.run", new=AsyncMock(return_value=fake)):
        text, call = await run_agent_call(fake_agent, "input", model="gpt-4o-mini")

    assert text == "the output"
    assert call.agent_name == "Test Agent"
    assert call.usage.prompt_tokens == 100
    assert call.usage.completion_tokens == 50
    assert call.usage.total_tokens == 150
    assert call.latency_s >= 0
    assert call.usage.cost_usd > 0
```

- [ ] **Step 2: Run test, expect ImportError**

```bash
PYTHONPATH=. pytest tests/test_architectures.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'architectures'`.

- [ ] **Step 3: Implement helper in `architectures.py`**

```python
"""Three orchestration topologies for the campaign benchmark."""
from __future__ import annotations

import time
from dataclasses import dataclass

from agents import Agent, Runner

from metrics import AgentCall, TokenUsage, estimate_cost


def _extract_usage(result, model: str) -> TokenUsage:
    """Read usage off a Runner.run result and compute cost."""
    raw = getattr(result, "usage", None)
    if raw is None:
        return TokenUsage(0, 0, 0, 0.0)
    p = int(getattr(raw, "input_tokens", getattr(raw, "prompt_tokens", 0)) or 0)
    c = int(getattr(raw, "output_tokens", getattr(raw, "completion_tokens", 0)) or 0)
    t = int(getattr(raw, "total_tokens", p + c) or (p + c))
    return TokenUsage(prompt_tokens=p, completion_tokens=c, total_tokens=t, cost_usd=estimate_cost(model, p, c))


async def run_agent_call(agent: Agent, input_text: str, model: str) -> tuple[str, AgentCall]:
    """Run an agent once; return (final_output, AgentCall) with usage + latency."""
    t0 = time.monotonic()
    result = await Runner.run(agent, input_text)
    latency = time.monotonic() - t0
    usage = _extract_usage(result, model)
    return result.final_output, AgentCall(agent_name=agent.name, latency_s=latency, usage=usage)
```

- [ ] **Step 4: Configure pytest for asyncio**

Create `Assignment3/multi-arch-benchmark/pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 5: Run test, expect pass**

```bash
PYTHONPATH=. pytest tests/test_architectures.py -v
```

Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add Assignment3/multi-arch-benchmark/architectures.py Assignment3/multi-arch-benchmark/tests/test_architectures.py Assignment3/multi-arch-benchmark/pytest.ini
git commit -m "feat: run_agent_call helper captures usage and latency"
```

---

## Task 5: Architecture 1 — Sequential

**Files:**
- Modify: `Assignment3/multi-arch-benchmark/architectures.py`
- Modify: `Assignment3/multi-arch-benchmark/tests/test_architectures.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_architectures.py`:

```python
from dataclasses import dataclass


@dataclass
class _Config:
    cd_model: str = "gpt-4o-mini"
    strat_model: str = "gpt-4o-mini"
    copy_model: str = "gpt-4o-mini"


@pytest.mark.asyncio
async def test_run_sequential_chains_three_agents():
    from architectures import run_sequential

    responses = iter([
        _FakeResult("idea text", 10, 10),
        _FakeResult("strategy text", 20, 20),
        _FakeResult("tweets text", 30, 30),
    ])

    async def fake_run(agent, input_text):
        return next(responses)

    with patch("architectures.Runner.run", new=fake_run):
        run = await run_sequential("eco water bottle in Bali", _Config())

    assert run.architecture == "sequential"
    assert run.final_output == "tweets text"
    assert len(run.calls) == 3
    assert [c.agent_name for c in run.calls] == ["Creative Director", "Strategist", "Copywriter"]
    assert run.total_tokens == 20 + 40 + 60
```

- [ ] **Step 2: Run test, expect fail (run_sequential undefined)**

```bash
PYTHONPATH=. pytest tests/test_architectures.py::test_run_sequential_chains_three_agents -v
```

Expected: FAIL with ImportError or AttributeError.

- [ ] **Step 3: Implement `run_sequential` in `architectures.py`**

Add to `architectures.py`:

```python
from agents_lib import build_creative_director, build_strategist, build_copywriter
from metrics import RunMetrics


async def run_sequential(brief: str, config) -> RunMetrics:
    """Architecture 1: CD → Strategist → Copywriter (linear chain)."""
    cd = build_creative_director(model=config.cd_model)
    strat = build_strategist(model=config.strat_model)
    copy = build_copywriter(model=config.copy_model)

    t0 = time.monotonic()
    idea, cd_call = await run_agent_call(cd, brief, model=config.cd_model)
    strategy, strat_call = await run_agent_call(strat, idea, model=config.strat_model)
    tweets, copy_call = await run_agent_call(copy, strategy, model=config.copy_model)
    total_latency = time.monotonic() - t0

    calls = [cd_call, strat_call, copy_call]
    return RunMetrics(
        architecture="sequential",
        calls=calls,
        total_latency_s=total_latency,
        total_tokens=sum(c.usage.total_tokens for c in calls),
        total_cost_usd=sum(c.usage.cost_usd for c in calls),
        final_output=tweets,
    )
```

- [ ] **Step 4: Run test, expect pass**

```bash
PYTHONPATH=. pytest tests/test_architectures.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add Assignment3/multi-arch-benchmark/architectures.py Assignment3/multi-arch-benchmark/tests/test_architectures.py
git commit -m "feat: architecture 1 (sequential pipeline)"
```

---

## Task 6: Benchmark Judge

**Files:**
- Create: `Assignment3/multi-arch-benchmark/judge.py`
- Test: `Assignment3/multi-arch-benchmark/tests/test_judge.py`

- [ ] **Step 1: Write the failing test**

`tests/test_judge.py`:

```python
import json
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from metrics import RunMetrics, AgentCall, TokenUsage, JudgeScore


class _FakeResult:
    def __init__(self, text):
        self.final_output = text
        self.usage = None


def _run(arch, text):
    return RunMetrics(
        architecture=arch,
        calls=[],
        total_latency_s=0,
        total_tokens=0,
        total_cost_usd=0,
        final_output=text,
    )


@pytest.mark.asyncio
async def test_score_architectures_parses_json():
    from judge import score_architectures

    fake_json = json.dumps([
        {"architecture": "sequential", "creativity": 7, "strategic_fit": 8,
         "copy_quality": 6, "overall": 7, "reasoning": "solid"},
        {"architecture": "orchestrator", "creativity": 9, "strategic_fit": 7,
         "copy_quality": 8, "overall": 8, "reasoning": "creative"},
        {"architecture": "parallel_judge", "creativity": 6, "strategic_fit": 9,
         "copy_quality": 7, "overall": 7, "reasoning": "balanced"},
    ])

    runs = [
        _run("sequential", "A"),
        _run("orchestrator", "B"),
        _run("parallel_judge", "C"),
    ]

    with patch("judge.Runner.run", new=AsyncMock(return_value=_FakeResult(fake_json))):
        scores = await score_architectures("brief", runs, model="gpt-4o-mini")

    assert len(scores) == 3
    by_arch = {s.architecture: s for s in scores}
    assert by_arch["orchestrator"].overall == 8
    assert by_arch["sequential"].creativity == 7
```

- [ ] **Step 2: Run test, expect ImportError**

```bash
PYTHONPATH=. pytest tests/test_judge.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'judge'`.

- [ ] **Step 3: Implement `judge.py`**

```python
"""Benchmark Judge: scores all architecture outputs on creativity/fit/copy."""
from __future__ import annotations

import json
from typing import Iterable

from agents import Agent, Runner

from metrics import JudgeScore, RunMetrics


_JUDGE_INSTRUCTIONS = (
    "You are an impartial Advertising Judge. You receive a campaign brief and a list of "
    "candidate campaigns produced by different agent architectures. For each candidate, "
    "score creativity, strategic_fit, copy_quality, and overall on a 1-10 integer scale. "
    "Output ONLY a valid JSON array (no markdown, no commentary) with one object per "
    "candidate: "
    '[{"architecture": "<name>", "creativity": <int>, "strategic_fit": <int>, '
    '"copy_quality": <int>, "overall": <int>, "reasoning": "<one short paragraph>"}]'
)


def _format_candidates(brief: str, runs: Iterable[RunMetrics]) -> str:
    parts = [f"BRIEF:\n{brief}\n", "CANDIDATES:"]
    for r in runs:
        parts.append(f"\n--- {r.architecture} ---\n{r.final_output}\n")
    return "\n".join(parts)


async def score_architectures(brief: str, runs: list[RunMetrics], model: str) -> list[JudgeScore]:
    judge = Agent(name="Benchmark Judge", model=model, instructions=_JUDGE_INSTRUCTIONS)
    prompt = _format_candidates(brief, runs)
    result = await Runner.run(judge, prompt)
    text = result.final_output.strip()
    # Tolerate ```json fences if the model adds them despite instructions
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    data = json.loads(text)
    return [JudgeScore(**row) for row in data]
```

- [ ] **Step 4: Run test, expect pass**

```bash
PYTHONPATH=. pytest tests/test_judge.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add Assignment3/multi-arch-benchmark/judge.py Assignment3/multi-arch-benchmark/tests/test_judge.py
git commit -m "feat: benchmark judge with JSON parsing"
```

---

## Task 7: Benchmark Orchestrator (sequential mode, Arch 1 only — first end-to-end runnable slice)

**Files:**
- Create: `Assignment3/multi-arch-benchmark/benchmark.py`
- Test: `Assignment3/multi-arch-benchmark/tests/test_benchmark.py`

Goal: at the end of this task, you can invoke `run_benchmark()` programmatically and get a `BenchmarkRun` back. UI comes later.

- [ ] **Step 1: Write the failing test**

`tests/test_benchmark.py`:

```python
from dataclasses import dataclass
from unittest.mock import patch, AsyncMock

import pytest

from metrics import RunMetrics, JudgeScore, AgentCall, TokenUsage


@dataclass
class _Cfg:
    cd_model: str = "gpt-4o-mini"
    strat_model: str = "gpt-4o-mini"
    copy_model: str = "gpt-4o-mini"
    judge_model: str = "gpt-4o-mini"
    execution: str = "sequential"
    enabled_architectures: tuple = ("sequential",)


def _fake_run(arch: str) -> RunMetrics:
    return RunMetrics(
        architecture=arch,
        calls=[AgentCall("Test", 1.0, TokenUsage(10, 10, 20, 0.0001))],
        total_latency_s=1.0,
        total_tokens=20,
        total_cost_usd=0.0001,
        final_output=f"output-{arch}",
    )


@pytest.mark.asyncio
async def test_run_benchmark_executes_enabled_architectures():
    from benchmark import run_benchmark

    fake_scores = [
        JudgeScore("sequential", 7, 7, 7, 7, "ok"),
    ]

    with patch("benchmark.run_sequential", new=AsyncMock(return_value=_fake_run("sequential"))), \
         patch("benchmark.score_architectures", new=AsyncMock(return_value=fake_scores)):
        bench = await run_benchmark("brief", _Cfg())

    assert bench.brief == "brief"
    assert len(bench.runs) == 1
    assert bench.runs[0].architecture == "sequential"
    assert len(bench.scores) == 1
```

- [ ] **Step 2: Run test, expect ImportError**

```bash
PYTHONPATH=. pytest tests/test_benchmark.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `benchmark.py`**

```python
"""Top-level benchmark runner."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from architectures import run_sequential
from judge import score_architectures
from metrics import BenchmarkRun, RunMetrics


@dataclass
class BenchmarkConfig:
    cd_model: str = "gpt-4o-mini"
    strat_model: str = "gpt-4o-mini"
    copy_model: str = "gpt-4o-mini"
    judge_model: str = "gpt-4o-mini"
    execution: str = "sequential"          # "sequential" | "parallel"
    enabled_architectures: tuple[str, ...] = ("sequential",)  # extended in later tasks


_ARCH_RUNNERS = {
    "sequential": run_sequential,
    # "orchestrator": run_orchestrator,     # added in Task 9
    # "parallel_judge": run_parallel_judge, # added in Task 10
}


async def _safe_run(arch: str, brief: str, config) -> RunMetrics:
    runner = _ARCH_RUNNERS[arch]
    try:
        return await runner(brief, config)
    except Exception as e:
        return RunMetrics(
            architecture=arch,
            calls=[],
            total_latency_s=0.0,
            total_tokens=0,
            total_cost_usd=0.0,
            final_output="",
            error=f"{type(e).__name__}: {e}",
        )


async def run_benchmark(brief: str, config) -> BenchmarkRun:
    """Execute enabled architectures and the benchmark judge."""
    enabled = [a for a in config.enabled_architectures if a in _ARCH_RUNNERS]

    if config.execution == "parallel":
        runs = list(await asyncio.gather(*(_safe_run(a, brief, config) for a in enabled)))
    else:
        runs = [await _safe_run(a, brief, config) for a in enabled]

    successful = [r for r in runs if r.error is None]
    scores = []
    if successful:
        try:
            scores = await score_architectures(brief, successful, model=config.judge_model)
        except Exception as e:
            scores = []  # UI will display N/A for judge cols

    return BenchmarkRun(
        brief=brief,
        model_config={
            "cd": config.cd_model,
            "strat": config.strat_model,
            "copy": config.copy_model,
            "judge": config.judge_model,
            "execution": config.execution,
        },
        runs=runs,
        scores=scores,
    )
```

- [ ] **Step 4: Run all tests, expect pass**

```bash
PYTHONPATH=. pytest -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add Assignment3/multi-arch-benchmark/benchmark.py Assignment3/multi-arch-benchmark/tests/test_benchmark.py
git commit -m "feat: benchmark orchestrator with Arch 1 + judge"
```

---

## Task 8: Minimal Gradio UI (Arch 1 end-to-end, "I want to see it running")

**Files:**
- Create: `Assignment3/multi-arch-benchmark/app.py`

Goal: launchable web app. User enters brief, clicks Run, sees Architecture 1's final output + token/latency/cost + judge score for that one architecture. Tabs/columns to be expanded in Task 11.

- [ ] **Step 1: Write `app.py`**

```python
"""Gradio entrypoint for the multi-architecture campaign benchmark."""
import asyncio
import os

import gradio as gr
import nest_asyncio
import pandas as pd
from dotenv import load_dotenv

from benchmark import BenchmarkConfig, run_benchmark

nest_asyncio.apply()
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found. Copy .env.example to .env and add your key.")


MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"]


def _bench_to_dataframe(bench) -> pd.DataFrame:
    by_arch = {s.architecture: s for s in bench.scores}
    rows = []
    for r in bench.runs:
        s = by_arch.get(r.architecture)
        rows.append({
            "Architecture": r.architecture,
            "Tokens": r.total_tokens,
            "Latency (s)": round(r.total_latency_s, 2),
            "Cost ($)": round(r.total_cost_usd, 6),
            "Creativity": s.creativity if s else "N/A",
            "Strategic Fit": s.strategic_fit if s else "N/A",
            "Copy Quality": s.copy_quality if s else "N/A",
            "Overall": s.overall if s else "N/A",
            "Error": r.error or "",
        })
    return pd.DataFrame(rows)


def run_ui(brief, cd_model, strat_model, copy_model, judge_model, execution):
    if not brief or not brief.strip():
        return pd.DataFrame(), "Please enter a brief.", ""

    config = BenchmarkConfig(
        cd_model=cd_model,
        strat_model=strat_model,
        copy_model=copy_model,
        judge_model=judge_model,
        execution=execution,
        enabled_architectures=("sequential",),  # extended in Task 11
    )

    bench = asyncio.run(run_benchmark(brief, config))
    df = _bench_to_dataframe(bench)

    seq = next((r for r in bench.runs if r.architecture == "sequential"), None)
    seq_text = seq.final_output if seq else ""
    reasoning = "\n\n".join(
        f"**{s.architecture}**\n{s.reasoning}" for s in bench.scores
    )
    return df, seq_text, reasoning


with gr.Blocks(title="Multi-Arch Campaign Benchmark") as demo:
    gr.Markdown(
        "# 🎯 Multi-Arch Campaign Benchmark\n"
        "*Compare OpenAI Agents SDK architectures on the same marketing brief.*"
    )

    brief = gr.Textbox(
        label="Campaign Brief",
        placeholder='e.g. "Launch a campaign for a new eco-friendly water bottle in Bali."',
        lines=3,
    )

    with gr.Accordion("Configuration", open=False):
        with gr.Row():
            cd_model = gr.Dropdown(MODELS, value="gpt-4o-mini", label="Creative Director model")
            strat_model = gr.Dropdown(MODELS, value="gpt-4o-mini", label="Strategist model")
            copy_model = gr.Dropdown(MODELS, value="gpt-4o-mini", label="Copywriter model")
            judge_model = gr.Dropdown(MODELS, value="gpt-4o-mini", label="Judge model")
        execution = gr.Radio(["sequential", "parallel"], value="sequential", label="Execution mode")

    btn = gr.Button("▶ Run Benchmark", variant="primary")

    metrics_df = gr.Dataframe(label="Comparison")
    seq_out = gr.Textbox(label="Sequential — Final Output", lines=10, interactive=False)
    judge_md = gr.Markdown(label="Judge Reasoning")

    btn.click(
        run_ui,
        inputs=[brief, cd_model, strat_model, copy_model, judge_model, execution],
        outputs=[metrics_df, seq_out, judge_md],
    )

if __name__ == "__main__":
    demo.launch()
```

- [ ] **Step 2: Run locally (requires `OPENAI_API_KEY`)**

```bash
cp .env.example .env   # then edit .env and put your key in
python app.py
```

Expected: Gradio opens at `http://127.0.0.1:7860`. Enter a brief, click Run, see the sequential output + metrics row + judge reasoning. This is the first runnable milestone.

- [ ] **Step 3: Commit**

```bash
git add Assignment3/multi-arch-benchmark/app.py
git commit -m "feat: minimal Gradio UI running Arch 1 end-to-end"
```

---

## Task 9: Architecture 2 — Orchestrator

**Files:**
- Modify: `Assignment3/multi-arch-benchmark/architectures.py`
- Modify: `Assignment3/multi-arch-benchmark/tests/test_architectures.py`
- Modify: `Assignment3/multi-arch-benchmark/benchmark.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_architectures.py`:

```python
@pytest.mark.asyncio
async def test_run_orchestrator_uses_director_with_tools():
    """The orchestrator should produce a single RunMetrics with at least one director call."""
    from architectures import run_orchestrator

    fake = _FakeResult("final campaign", 80, 40)

    with patch("architectures.Runner.run", new=AsyncMock(return_value=fake)):
        run = await run_orchestrator("brief", _Config())

    assert run.architecture == "orchestrator"
    assert run.final_output == "final campaign"
    assert len(run.calls) >= 1
    assert run.calls[0].agent_name == "Creative Director (Orchestrator)"
```

- [ ] **Step 2: Run test, expect fail**

```bash
PYTHONPATH=. pytest tests/test_architectures.py::test_run_orchestrator_uses_director_with_tools -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `run_orchestrator` in `architectures.py`**

Add to `architectures.py`:

```python
from agents import function_tool


_ORCHESTRATOR_INSTRUCTIONS = (
    "You are a Creative Director and the orchestrator of a campaign team. "
    "Process: "
    "(1) Generate ONE best campaign idea (name + tagline + concept). "
    "(2) Call the `consult_strategist` tool with that idea to get a strategic refinement. "
    "(3) Evaluate the strategist's response; if weak, you may re-call once with revisions. "
    "(4) Call the `consult_copywriter` tool with the refined strategy to get tweets. "
    "(5) Produce the final campaign output: the chosen idea, the strategy, and the tweets, "
    "consolidated into one clean campaign package. "
    "Output the final campaign only; do not show intermediate deliberations."
)


async def run_orchestrator(brief: str, config) -> RunMetrics:
    """Architecture 2: Creative Director orchestrates Strategist and Copywriter as tools."""
    strategist = build_strategist(model=config.strat_model)
    copywriter = build_copywriter(model=config.copy_model)

    # Track sub-agent costs as nested AgentCall entries
    sub_calls: list[AgentCall] = []

    @function_tool
    async def consult_strategist(idea: str) -> str:
        text, call = await run_agent_call(strategist, idea, model=config.strat_model)
        sub_calls.append(call)
        return text

    @function_tool
    async def consult_copywriter(strategy: str) -> str:
        text, call = await run_agent_call(copywriter, strategy, model=config.copy_model)
        sub_calls.append(call)
        return text

    director = Agent(
        name="Creative Director (Orchestrator)",
        model=config.cd_model,
        instructions=_ORCHESTRATOR_INSTRUCTIONS,
        tools=[consult_strategist, consult_copywriter],
    )

    t0 = time.monotonic()
    final, dir_call = await run_agent_call(director, brief, model=config.cd_model)
    total_latency = time.monotonic() - t0

    calls = [dir_call] + sub_calls
    return RunMetrics(
        architecture="orchestrator",
        calls=calls,
        total_latency_s=total_latency,
        total_tokens=sum(c.usage.total_tokens for c in calls),
        total_cost_usd=sum(c.usage.cost_usd for c in calls),
        final_output=final,
    )
```

- [ ] **Step 4: Register the runner in `benchmark.py`**

Edit `_ARCH_RUNNERS` in `benchmark.py`:

```python
from architectures import run_sequential, run_orchestrator

_ARCH_RUNNERS = {
    "sequential": run_sequential,
    "orchestrator": run_orchestrator,
    # "parallel_judge": run_parallel_judge,  # added in Task 10
}
```

- [ ] **Step 5: Run all tests, expect pass**

```bash
PYTHONPATH=. pytest -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add Assignment3/multi-arch-benchmark/architectures.py Assignment3/multi-arch-benchmark/benchmark.py Assignment3/multi-arch-benchmark/tests/test_architectures.py
git commit -m "feat: architecture 2 (director-orchestrator with tools)"
```

---

## Task 10: Architecture 3 — Parallel + Judge

**Files:**
- Modify: `Assignment3/multi-arch-benchmark/architectures.py`
- Modify: `Assignment3/multi-arch-benchmark/tests/test_architectures.py`
- Modify: `Assignment3/multi-arch-benchmark/benchmark.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_architectures.py`:

```python
@pytest.mark.asyncio
async def test_run_parallel_judge_aggregates_three_full_outputs():
    from architectures import run_parallel_judge

    responses = iter([
        _FakeResult("cd full output", 30, 30),       # CD full campaign
        _FakeResult("strat full output", 30, 30),    # Strat full campaign
        _FakeResult("copy full output", 30, 30),     # Copy full campaign
        _FakeResult("the chosen campaign", 20, 20),  # internal judge picks
    ])

    async def fake_run(agent, input_text):
        return next(responses)

    with patch("architectures.Runner.run", new=fake_run):
        run = await run_parallel_judge("brief", _Config())

    assert run.architecture == "parallel_judge"
    assert run.final_output == "the chosen campaign"
    assert len(run.calls) == 4
```

- [ ] **Step 2: Run test, expect fail**

```bash
PYTHONPATH=. pytest tests/test_architectures.py::test_run_parallel_judge_aggregates_three_full_outputs -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `run_parallel_judge` in `architectures.py`**

Add to `architectures.py`:

```python
import asyncio

from agents_lib import build_arch3_full_agent


_ARCH3_INTERNAL_JUDGE_INSTRUCTIONS = (
    "You are an impartial campaign editor. You receive three candidate complete "
    "campaigns produced from different professional perspectives (Creative, Strategy, Copy). "
    "Pick the strongest single candidate OR synthesize the best elements into one final "
    "complete campaign. Output ONLY the final campaign, no commentary."
)


async def run_parallel_judge(brief: str, config) -> RunMetrics:
    """Architecture 3: three agents produce full campaigns in parallel; internal judge picks/merges."""
    cd_full = build_arch3_full_agent("Creative Director", model=config.cd_model)
    strat_full = build_arch3_full_agent("Strategist", model=config.strat_model)
    copy_full = build_arch3_full_agent("Copywriter", model=config.copy_model)

    t0 = time.monotonic()
    cd_pair, strat_pair, copy_pair = await asyncio.gather(
        run_agent_call(cd_full, brief, model=config.cd_model),
        run_agent_call(strat_full, brief, model=config.strat_model),
        run_agent_call(copy_full, brief, model=config.copy_model),
    )
    (cd_text, cd_call), (strat_text, strat_call), (copy_text, copy_call) = cd_pair, strat_pair, copy_pair

    aggregated = (
        f"CANDIDATE A (Creative perspective):\n{cd_text}\n\n"
        f"CANDIDATE B (Strategy perspective):\n{strat_text}\n\n"
        f"CANDIDATE C (Copy perspective):\n{copy_text}\n"
    )

    internal_judge = Agent(
        name="Arch3 Internal Judge",
        model=config.cd_model,  # reuse CD model for consistency; could be its own knob later
        instructions=_ARCH3_INTERNAL_JUDGE_INSTRUCTIONS,
    )
    final, judge_call = await run_agent_call(internal_judge, aggregated, model=config.cd_model)
    total_latency = time.monotonic() - t0

    calls = [cd_call, strat_call, copy_call, judge_call]
    return RunMetrics(
        architecture="parallel_judge",
        calls=calls,
        total_latency_s=total_latency,
        total_tokens=sum(c.usage.total_tokens for c in calls),
        total_cost_usd=sum(c.usage.cost_usd for c in calls),
        final_output=final,
    )
```

- [ ] **Step 4: Register in `benchmark.py`**

```python
from architectures import run_sequential, run_orchestrator, run_parallel_judge

_ARCH_RUNNERS = {
    "sequential": run_sequential,
    "orchestrator": run_orchestrator,
    "parallel_judge": run_parallel_judge,
}
```

- [ ] **Step 5: Run all tests, expect pass**

```bash
PYTHONPATH=. pytest -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add Assignment3/multi-arch-benchmark/architectures.py Assignment3/multi-arch-benchmark/benchmark.py Assignment3/multi-arch-benchmark/tests/test_architectures.py
git commit -m "feat: architecture 3 (parallel + judge)"
```

---

## Task 11: Full UI — three architectures, tabs, per-call detail

**Files:**
- Modify: `Assignment3/multi-arch-benchmark/app.py`

- [ ] **Step 1: Replace `app.py` with the full version**

```python
"""Gradio entrypoint for the multi-architecture campaign benchmark."""
import asyncio
import os

import gradio as gr
import nest_asyncio
import pandas as pd
from dotenv import load_dotenv

from benchmark import BenchmarkConfig, run_benchmark

nest_asyncio.apply()
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found. Copy .env.example to .env and add your key.")


MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"]
ARCHS = ("sequential", "orchestrator", "parallel_judge")


def _comparison_df(bench) -> pd.DataFrame:
    by_arch = {s.architecture: s for s in bench.scores}
    rows = []
    for r in bench.runs:
        s = by_arch.get(r.architecture)
        rows.append({
            "Architecture": r.architecture,
            "Tokens": r.total_tokens,
            "Latency (s)": round(r.total_latency_s, 2),
            "Cost ($)": round(r.total_cost_usd, 6),
            "Creativity": s.creativity if s else "N/A",
            "Strategic Fit": s.strategic_fit if s else "N/A",
            "Copy Quality": s.copy_quality if s else "N/A",
            "Overall": s.overall if s else "N/A",
            "Error": r.error or "",
        })
    return pd.DataFrame(rows)


def _per_call_df(bench) -> pd.DataFrame:
    rows = []
    for r in bench.runs:
        for c in r.calls:
            rows.append({
                "Architecture": r.architecture,
                "Agent": c.agent_name,
                "Latency (s)": round(c.latency_s, 2),
                "Prompt Tokens": c.usage.prompt_tokens,
                "Completion Tokens": c.usage.completion_tokens,
                "Total Tokens": c.usage.total_tokens,
                "Cost ($)": round(c.usage.cost_usd, 6),
            })
    return pd.DataFrame(rows)


def _final_for(bench, arch: str) -> str:
    run = next((r for r in bench.runs if r.architecture == arch), None)
    if run is None:
        return "(not run)"
    if run.error:
        return f"ERROR: {run.error}"
    return run.final_output


def _judge_markdown(bench) -> str:
    if not bench.scores:
        return "*Judge produced no scores.*"
    blocks = []
    for s in bench.scores:
        blocks.append(
            f"### {s.architecture}\n"
            f"- Creativity: {s.creativity}/10\n"
            f"- Strategic Fit: {s.strategic_fit}/10\n"
            f"- Copy Quality: {s.copy_quality}/10\n"
            f"- **Overall: {s.overall}/10**\n\n"
            f"{s.reasoning}"
        )
    return "\n\n---\n\n".join(blocks)


def run_ui(brief, cd_model, strat_model, copy_model, judge_model, execution):
    if not brief or not brief.strip():
        empty = pd.DataFrame()
        return empty, empty, "Please enter a brief.", "", "", "", ""

    config = BenchmarkConfig(
        cd_model=cd_model,
        strat_model=strat_model,
        copy_model=copy_model,
        judge_model=judge_model,
        execution=execution,
        enabled_architectures=ARCHS,
    )

    bench = asyncio.run(run_benchmark(brief, config))

    return (
        _comparison_df(bench),
        _per_call_df(bench),
        _judge_markdown(bench),
        _final_for(bench, "sequential"),
        _final_for(bench, "orchestrator"),
        _final_for(bench, "parallel_judge"),
        f"Done. Architectures run: {len(bench.runs)} | Judge scored: {len(bench.scores)}.",
    )


with gr.Blocks(title="Multi-Arch Campaign Benchmark") as demo:
    gr.Markdown(
        "# 🎯 Multi-Arch Campaign Benchmark\n"
        "*Compare OpenAI Agents SDK architectures on the same marketing brief.*"
    )

    brief = gr.Textbox(
        label="Campaign Brief",
        placeholder='e.g. "Launch a campaign for a new eco-friendly water bottle in Bali."',
        lines=3,
    )

    with gr.Accordion("Configuration", open=False):
        with gr.Row():
            cd_model = gr.Dropdown(MODELS, value="gpt-4o-mini", label="Creative Director model")
            strat_model = gr.Dropdown(MODELS, value="gpt-4o-mini", label="Strategist model")
            copy_model = gr.Dropdown(MODELS, value="gpt-4o-mini", label="Copywriter model")
            judge_model = gr.Dropdown(MODELS, value="gpt-4o-mini", label="Judge model")
        execution = gr.Radio(["sequential", "parallel"], value="sequential", label="Execution mode")

    btn = gr.Button("▶ Run Benchmark", variant="primary")
    status = gr.Textbox(label="Status", value="idle", interactive=False)

    with gr.Tabs():
        with gr.Tab("📊 Comparison"):
            metrics_df = gr.Dataframe(label="Architectures")
            judge_md = gr.Markdown()
        with gr.Tab("📄 Final Outputs"):
            with gr.Row():
                seq_out = gr.Textbox(label="Sequential", lines=14, interactive=False)
                orch_out = gr.Textbox(label="Orchestrator", lines=14, interactive=False)
                par_out = gr.Textbox(label="Parallel + Judge", lines=14, interactive=False)
        with gr.Tab("🔍 Per-Call Detail"):
            calls_df = gr.Dataframe(label="Agent calls")

    btn.click(
        run_ui,
        inputs=[brief, cd_model, strat_model, copy_model, judge_model, execution],
        outputs=[metrics_df, calls_df, judge_md, seq_out, orch_out, par_out, status],
    )

if __name__ == "__main__":
    demo.launch()
```

- [ ] **Step 2: Manual smoke test**

```bash
python app.py
```

Expected: Gradio opens. Enter a short brief, click Run, see the Comparison tab populate with 3 rows, Final Outputs tab with three side-by-side columns, Per-Call Detail tab with rows for each agent call across architectures. Try execution=parallel and confirm wall-clock latency drops while per-architecture latency is similar.

- [ ] **Step 3: Commit**

```bash
git add Assignment3/multi-arch-benchmark/app.py
git commit -m "feat: full Gradio UI with tabs and all three architectures"
```

---

## Task 12: README and Final Polish

**Files:**
- Create: `Assignment3/multi-arch-benchmark/README.md`

- [ ] **Step 1: Write a short README**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add Assignment3/multi-arch-benchmark/README.md
git commit -m "docs: README for multi-arch-benchmark"
```

- [ ] **Step 3: Final test sweep**

```bash
PYTHONPATH=. pytest -v
```

Expected: all tests pass. Manual smoke test of the app: enter a brief, confirm all three architectures produce final outputs and metrics, judge scores appear in the Comparison tab.

---

## Notes for the Implementer

- **`Runner.run` usage shape**: the SDK exposes token usage on the result. The helper `_extract_usage` reads `input_tokens`/`output_tokens` first and falls back to `prompt_tokens`/`completion_tokens`. If the SDK version diverges, adjust there only.
- **Cost is an estimate**: pricing in `metrics.py` is a hardcoded snapshot. Don't surprise yourself by trusting it as billable.
- **Orchestrator can be expensive**: max-turns is governed by the SDK default. If runs balloon in cost, cap turns by passing a `max_turns` arg to `Runner.run` (consult `agents` SDK docs in your installed version for the exact kwarg).
- **JSON parsing for judge**: tolerated code-fence stripping in `judge.py`. If models still produce non-JSON, swap to `pydantic` structured output via the SDK's response-format support.
- **`PYTHONPATH=.`** is needed when running `pytest` because the modules live at the project root and aren't installed as a package. Set it in your shell or via `conftest.py` later if it gets annoying.
