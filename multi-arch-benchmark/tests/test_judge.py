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
