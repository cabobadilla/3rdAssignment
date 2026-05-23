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
