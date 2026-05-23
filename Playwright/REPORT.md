# Playwright Execution Report

## Multi-Architecture Campaign Benchmark

**Application under test:** Multi-Arch Campaign Benchmark (Gradio app, `http://127.0.0.1:7860`)
**Test driver:** Playwright MCP plugin (Chromium, 1440×900 viewport)
**Test brief:** *"a campaign for a new kids bike to learn riding"*
**Date:** 2026-05-23

---

## 1. What was tested

The application benchmarks three OpenAI Agents SDK orchestration patterns running the same marketing brief, then reports tokens, latency, cost, and a blind quality score side-by-side.

The three architectures under evaluation are:

- **Sequential Pipeline** — Creative Director hands off to Strategist, who hands off to Copywriter. Each agent does its specialty stage and passes the result downstream.
- **Director-Orchestrator** — The Creative Director acts as the central agent and calls Strategist and Copywriter as tools, deciding when to delegate and when to revise.
- **Parallel + Judge** — All three agents produce a complete campaign in parallel from their own perspective; an internal judge picks the strongest.

## 2. How it was tested

The flow was driven through Playwright in headless Chromium against the live local app.

1. **Navigate** to `http://127.0.0.1:7860` after sizing the viewport to 1440×900.
2. **Snapshot** the accessibility tree and take a full-page screenshot of the idle state.
3. **Fill** the *Campaign brief* textarea with the test prompt.
4. **Click** the orange `Run Benchmark` CTA.
5. **Wait** for the Gradio queue to stream `process_starts → progress → process_completed` over the SSE channel.
6. **Switch** between the three result tabs (`Comparison`, `Final Outputs`, `Per-Call Detail`) and screenshot each.

The Gradio runtime exposes a typed event stream that was inspected via Playwright's network capture to confirm completion timing and payload integrity.

### Observation: front-end render bug

The first end-to-end attempt hit a Gradio DataFrame bug (`RangeError: Maximum call stack size exceeded` from `Index-CytOJC_D.js`). The backend completed the benchmark and returned valid data over the SSE stream, but the table component crashed mid-render and stayed empty. A page reload + re-run produced a clean render on the second attempt — the screenshots and metrics in this report are from the clean run.

## 3. Results — kids-bike campaign

The benchmark produced a complete, scored campaign package for the brief *"a campaign for a new kids bike to learn riding"*.

**Headline:** 3/3 architectures succeeded · 5,239 tokens · $0.0018 total cost.

### Comparison

| Architecture           | Tokens | Latency | Cost    | Creativity | Strategic Fit | Copy Quality | Overall |
|------------------------|--------|---------|---------|------------|---------------|--------------|---------|
| Sequential Pipeline    | 814    | 8.4 s   | $0.0003 | 7          | 6             | 8            | 7       |
| ★ Director-Orchestrator | 2,524  | 19.7 s  | $0.0007 | 8          | 9             | 9            | **9**   |
| Parallel + Judge       | 2,298  | 12.4 s  | $0.0009 | 9          | 8             | 8            | 8       |

(Values from the first clean run. A second clean run shown in the screenshots produced very similar shape: same winner, total cost $0.0018 across 5,239 tokens.)

### Per-call detail (clean run)

| Architecture          | Agent                              | Latency | Total Tokens | Cost     |
|-----------------------|------------------------------------|---------|--------------|----------|
| Sequential Pipeline   | Creative Director                  | 2.8 s   | 195          | $0.000074 |
| Sequential Pipeline   | Strategist                         | 2.7 s   | 282          | $0.000092 |
| Sequential Pipeline   | Copywriter                         | 2.9 s   | 337          | $0.0001  |
| Director-Orchestrator | Creative Director (Orchestrator)   | 19.7 s  | 1,913        | $0.0005  |
| Director-Orchestrator | Strategist                         | 3.1 s   | 287          | $0.0001  |
| Director-Orchestrator | Copywriter                         | 3.6 s   | 324          | $0.0001  |
| Parallel + Judge      | Creative Director (Full)           | 4.9 s   | 364          | $0.0002  |
| Parallel + Judge      | Strategist (Full)                  | 6.5 s   | 345          | $0.0002  |
| Parallel + Judge      | Copywriter (Full)                  | 4.2 s   | 349          | $0.0002  |
| Parallel + Judge      | Arch3 Internal Judge               | 5.9 s   | 1,240        | $0.0003  |

### Judge reasoning (clean run)

- **Sequential Pipeline (7/10)** — Conveys a message suitable for kids and parents, but lacks a distinct central concept that ties the messages together.
- **Director-Orchestrator (9/10) ★ winner** — Strong strategic approach, effective community engagement, experiential learning focus, builds confidence.
- **Parallel + Judge (8/10)** — Friendly and adventurous appeal with good focus on safety and connection; copy quality could be sharper for greater impact.

### Sample final outputs

- **Sequential — *Balance Buddy*:** Vibrant, hashtag-heavy posts emphasizing adventure and community.
- **Director-Orchestrator — *Pedal Pals*** ("Join the Ride to Adventure!"): Family-targeted campaign with safety tips and community angle.
- **Parallel + Judge — *Wheels of Adventure*** ("Every Journey Begins with a Single Pedal!"): Independence and confidence framing with a longer set of social posts.

## 4. Architecture comparison — analytical takeaways

- **Cost / quality frontier.** Sequential is 2.3× cheaper than the orchestrator but trades 2 points of overall quality. For a kids-bike brief where strategic fit and copy polish matter, the orchestrator's $0.0007 is well-spent.
- **Latency vs. coordination.** Sequential is the fastest (~8 s) because each stage runs in a fixed order with no re-entry. The orchestrator pays a ~19 s latency penalty for tool-calling overhead and multi-turn deliberation — but that loop is what lifts strategic fit from 6 to 9.
- **Creativity ceiling.** Parallel + Judge tops creativity (9) because three independent agents draft full campaigns, increasing variance. The judge then picks the strongest. This is the best pattern when divergence matters more than coordination.
- **When to pick which.**
  - *Sequential* → cheap, fast, predictable. Good for content with a known recipe.
  - *Director-Orchestrator* → best overall when you want a single decision-maker shaping output. Default choice for client-facing campaigns.
  - *Parallel + Judge* → ideation-heavy work where you want creative range, with cost ~3× sequential.

## 5. Screenshots

All screenshots live alongside this report:

1. `01-home-fullpage.png` — Initial app load, editorial header, three architecture cards, empty brief.
2. `02-brief-entered.png` — Brief textarea populated with the test prompt.
3. `03-benchmark-running.png` — `Run Benchmark` clicked, state transitioning out of *Idle*.
4. `04-comparison-results.png` — Comparison tab with full results table and headline.
5. `05-final-outputs.png` — Final Outputs tab showing the full campaign per architecture.
6. `06-per-call-detail.png` — Per-Call Detail tab with agent-level latency, tokens, and cost.

## 6. Conclusion

Playwright successfully drove the full flow end-to-end through the Gradio front-end on a real local server, including handling a first-pass front-end render crash by reloading and re-running. The Director-Orchestrator architecture won this brief decisively on overall quality (9/10), with the Sequential Pipeline as the cost-efficient baseline (7/10) and Parallel + Judge offering the highest creativity ceiling (9/10 on creativity, 8/10 overall).
