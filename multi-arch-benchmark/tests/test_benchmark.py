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
