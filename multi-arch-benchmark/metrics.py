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
