# PLAN.md — Multi-Arch Campaign Benchmark

## What We Built

A Gradio web app that runs the **same marketing-campaign brief** through three different OpenAI Agents SDK orchestration patterns and reports the result side-by-side.

**Three architectures, same agent personas (Creative Director, Strategist, Copywriter):**

1. **Sequential Pipeline** — linear chain: CD → Strategist → Copywriter.
2. **Director-Orchestrator** — Creative Director acts as central agent with `function_tool` wrappers around Strategist and Copywriter.
3. **Parallel + Judge** — all three agents produce a complete campaign in parallel; an internal judge merges/picks the best.

**Measurement layer:**

- Per-agent-call token usage and latency are captured from the SDK's `result.context_wrapper.usage`.
- Per-architecture totals (tokens, latency, cost in USD) are aggregated in `RunMetrics`.
- A **Benchmark Judge** (separate from architecture 3's internal judge) scores all three final campaigns on creativity, strategic fit, copy quality, and overall — returning structured JSON.

**UI:**

- Editorial "Benchmark Report" aesthetic — Fraunces / Manrope / JetBrains Mono on warm paper-cream + ink-black + saffron-orange.
- Masthead, numbered architecture cards, section dividers (§ 01 / 02 / 03), tabs (Comparison · Final Outputs · Per-Call Detail).
- Example-brief chips, configuration panel (per-agent model dropdowns + sequential/parallel toggle).
- Responsive down to 540px; honors `prefers-reduced-motion`.

**Quality:**

- 11/11 unit tests passing (mocked `Runner.run`).
- A single failing architecture does not break the benchmark — others still produce results, and judge columns degrade to `—`.
- Configurable model per agent role; cost estimated from a static pricing table.

## What We Improved

Documented in detail in `docs/2026-05-22-ralph-retrospective.md`. Headline list:

### Iteration 1 — Functional polish
- Human-readable architecture names.
- Empty states with helpful copy across every tab.
- Example-brief chips for one-click first use.
- Progress reporting during runs.
- Adaptive cost formatting and friendlier status messages.
- Trophy on the winning architecture.

### Iteration 2 — Editorial aesthetic
- Replaced Inter (rubric-flagged generic) with Fraunces + Manrope + JetBrains Mono.
- Replaced indigo-on-white cliche with paper/ink/saffron.
- Magazine masthead, numbered architecture cards with hairline rules.
- Section dividers, uppercase tracked-out tab labels, black-to-saffron button.
- SVG paper-grain texture, no rounded corners (intentional brutalism).
- Staggered entrance motion + hover micro-interactions.

### Iteration 3 — Responsive + prominent running state
- Brief/config row stacks under 760px; tables shrink under 540px.
- Status flips to "Running benchmark…" *before* the long call starts (via `.click().then(...)`).
- Animated marquee under the disabled run button.
- `prefers-reduced-motion` respected.

### Repo hygiene
- Accidentally tracked `Assignment3/campaign-web-app/.venv` (≈23k files) removed from the repo.
- `.gitignore` broadened to `**/.venv/`, `**/__pycache__/`, `**/.pytest_cache/`, `**/.env` to prevent recurrence.
- Remote (`github.com/cabobadilla/3rdAssignment`) cleaned to contain only `Assignment3/`.

## Future Roadmap

In order of (rough) value-to-effort:

### Near term
1. **Streamed outputs** — render tokens as the model produces them, instead of waiting for the whole campaign. Highest impact on perceived speed.
2. **Brief history** — local-only list of recent briefs; click to re-run.
3. **Export benchmark run** — single JSON button with the full `BenchmarkRun` (brief, config, runs, scores) for later analysis or sharing.
4. **Compare two briefs** — side-by-side mode that runs the same architecture on two briefs to isolate brief sensitivity.
5. **Cost-budget cap** — hard ceiling that aborts a run if estimated cost exceeds a threshold.

### Medium term
6. **Prompt customisation in the UI** — let the user edit the persona prompts before a run, to test prompt sensitivity per architecture.
7. **Architecture variants** — additional topologies (handoffs, debate, hierarchical) toggled in the configuration panel.
8. **Per-agent model dropdowns in `architectures.py`** for the Arch 3 internal judge — currently shares the CD model.
9. **Richer winner attribution** — break down *why* a given architecture won (e.g. judge weighting per criterion).
10. **Charts** — small inline charts (tokens vs cost, latency vs overall) instead of just tables.

### Quality / infra
11. **Live SDK smoke test in CI** — gated on `OPENAI_API_KEY`, runs one tiny brief end-to-end on every PR to catch SDK shape drift.
12. **Pricing table auto-fetch** — pull current model prices from a known source instead of hardcoding.
13. **Auth / multi-user** — only relevant if this leaves a single-user demo context.
14. **History persistence** (file or SQLite) — only relevant once people care to look back at runs.

### Deferred / explicit non-goals
- Authentication or organisation accounts.
- Anything that turns this from a comparison tool into a campaign generator (e.g. "run the orchestrator only and save the campaign"). The benchmark *is* the product.
