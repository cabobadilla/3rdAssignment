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
