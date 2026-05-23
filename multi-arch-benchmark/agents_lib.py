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
