"""Three orchestration topologies for the campaign benchmark."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from agents import Agent, Runner, function_tool

from agents_lib import build_creative_director, build_strategist, build_copywriter, build_arch3_full_agent
from metrics import AgentCall, RunMetrics, TokenUsage, estimate_cost


def _extract_usage(result, model: str) -> TokenUsage:
    """Read usage off a Runner.run result and compute cost.

    Real openai-agents SDK exposes usage at result.context_wrapper.usage;
    the helper also tolerates result.usage for ease of testing with mocks.
    """
    raw = getattr(result, "usage", None) or getattr(getattr(result, "context_wrapper", None), "usage", None)
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
