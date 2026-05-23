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
