"""Top-level benchmark runner."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from architectures import run_sequential, run_orchestrator, run_parallel_judge
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


def _arch_runners() -> dict:
    """Build the architecture-name -> runner map at call time.

    Resolving via module globals (not a module-level dict literal) lets
    tests patch ``benchmark.run_sequential`` and friends with mocks.
    """
    import sys
    mod = sys.modules[__name__]
    return {
        "sequential": mod.run_sequential,
        "orchestrator": mod.run_orchestrator,
        "parallel_judge": mod.run_parallel_judge,
    }


async def _safe_run(arch: str, brief: str, config) -> RunMetrics:
    runner = _arch_runners()[arch]
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
    runners = _arch_runners()
    enabled = [a for a in config.enabled_architectures if a in runners]

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
