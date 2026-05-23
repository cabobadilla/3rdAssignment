# Ralph-Style Iteration Retrospective — Multi-Arch Campaign Benchmark

**Date:** 2026-05-22
**Goal:** Lift the app from "works" to "feels like a real product" through iterative review + design verification.
**Method:** Three iteration cycles, each followed by a self-review against the `frontend-design` skill's rubric (typography, color, motion, composition, visual details, differentiation).

The formal Ralph Loop scaffolding needed an interactive permission grant that couldn't be requested in this session, so the same pattern (same goal, repeated rounds, prior work visible to each round) was applied manually. Code and tests were re-verified after every iteration.

---

## Iteration 1 — Functional polish

**Commit:** `c0776d59 ui: iter 1 - polished layout, theme, example briefs, progress feedback`

### What was found
- Default Gradio look with no visual personality.
- Architecture identifiers (`sequential`, `orchestrator`, `parallel_judge`) exposed to the user as labels.
- No loading state — clicking Run was silent for 30+ seconds.
- No empty state — first-time users saw blank tabs and no guidance.
- No example briefs.
- Cost values formatted as `$0.001234` (six decimals everywhere) regardless of magnitude.
- Status text was technical ("Architectures run: 3 | Judge scored: 3").
- No description of what each architecture does, just names.

### What was improved
- Soft theme + Inter font + custom CSS, ~1200px max width.
- Human-readable architecture display names (`Sequential Pipeline`, `Director-Orchestrator`, `Parallel + Judge`).
- Example-brief chips for one-click first use.
- Per-stage progress reporting via `gr.Progress`.
- Empty states across every tab with helpful copy.
- Trophy emoji on the highest-overall architecture in the comparison table.
- Friendlier status messages: success/failure count plus aggregate tokens and cost.
- Adaptive cost formatting (`$0.0012` if ≥ $0.0001, else 6-decimal scientific).

### `frontend-design` verification (iter 1)

| Criterion | Verdict |
| --- | --- |
| Typography | ❌ Uses Inter — explicitly flagged as a generic AI cliche by the rubric |
| Color | ❌ Indigo on white — the exact "purple gradients on white" anti-pattern |
| Motion | ❌ None |
| Composition | ⚠️ Decent grid, but conservative and symmetric |
| Visual details | ⚠️ Cards present but bland; no atmosphere |
| Differentiation | ❌ Looks like a generic Gradio app with cards |

**Decision:** Iter 1 fixed the UX issues but kept the generic AI aesthetic. Iter 2 needs a real point of view.

---

## Iteration 2 — Editorial "Benchmark Report" aesthetic

**Commit:** `f80aece6 ui: iter 2 - editorial benchmark report aesthetic`

### Direction chosen
Commit to a magazine/editorial metaphor. The product is a **benchmark report** — let the UI feel like one.

### What changed
- **Typography stack:** Fraunces (variable serif with optical sizing, italic axis) for display, Manrope for body, JetBrains Mono for numerals and labels. Inter is gone.
- **Palette:** warm paper cream (`#F8F4ED`), ink black (`#1C1B1A`), saffron-orange accent (`#C24F1A`). No indigo, no white background.
- **Masthead:** "Vol. 01" supra-label in monospace, large display headline with an italic accent on the last phrase ("One winner.").
- **Architecture cards:** numbered 01 / 02 / 03 with serif numerals in accent color, divided by hairline rules, no rounded corners.
- **Section dividers:** `§ 01 — Architectures under test`, `§ 02 — Brief & configuration`, `§ 03 — Findings` — uppercase tracked-out monospace labels.
- **Tabs:** uppercase tracked, underlined in accent when selected.
- **Button:** black with saffron hover, uppercase tracking — feels like a serious tool, not a chatbot.
- **Background:** subtle SVG-noise paper grain at 6% opacity.
- **Motion:** staggered `fadeUp` on masthead → cards → brief row → button. Hover transitions on cards/button/chips.
- **Colophon footer** for closure.

### `frontend-design` verification (iter 2)

| Criterion | Verdict |
| --- | --- |
| Typography | ✅ Fraunces + Manrope + JetBrains Mono — distinctive, none generic |
| Color | ✅ Paper/ink/saffron — cohesive, not the indigo-on-white cliche |
| Motion | ✅ Staggered entrance + hover micro-interactions |
| Composition | ✅ Magazine masthead, numbered cards, ruled section dividers |
| Visual details | ✅ Paper grain, hairline rules, no rounded corners (intentional) |
| Differentiation | ✅ Editorial metaphor is memorable and matches the domain |

**Remaining issues spotted:**
- Mobile layout: the 3:2 brief/config split doesn't stack on narrow screens.
- Loading state is still subtle (only the Gradio progress strip).
- Some Gradio internals may leak through despite `!important` rules.

---

## Iteration 3 — Responsive + prominent running state

**Commit:** `dde41544 ui: iter 3 - responsive, prominent running state, motion preferences`

### What changed
- **Responsive:** at ≤ 760px the gradio columns force-stack via CSS; paddings tighten; masthead headline shrinks. At ≤ 540px the tables reduce font size and padding.
- **Running state:** clicking the button immediately writes "**Running benchmark…**" to the status strip via a fast `.click().then(…)` chain — visible *before* the long API calls begin.
- **Animated marquee** under the disabled run button while a benchmark is in flight.
- **Reduced motion:** `prefers-reduced-motion: reduce` disables all animations and transitions globally.
- **Idle status copy** sets expectations: "Expect about 30-60 seconds on `gpt-4o-mini`."

### `frontend-design` verification (iter 3)

| Criterion | Verdict |
| --- | --- |
| First-time clarity | ✅ Idle status sets expectations; example briefs invite a first run |
| Loading affordance | ✅ Status flips to "Running…" instantly; button styling indicates activity |
| Mobile usability | ✅ Stacks under 760px; tables shrink under 540px |
| Accessibility | ✅ `prefers-reduced-motion` respected |
| Polish details | ✅ Hover states on cards/chips/button; consistent ruling lines; monospace numerals |

---

## Aggregate result

Three commits, ~340 lines of CSS, no functional regressions (11/11 tests pass after every iteration). The app moved from "Gradio app with cards" to "Vol. 01 benchmark report" — a clear, owned aesthetic that matches the product's purpose.

## Things deliberately *not* done
- No frontend framework swap (still Gradio). The brief was to polish, not rebuild.
- No streaming output (token-by-token) — out of scope; flagged in `PLAN.md → Future Roadmap`.
- No history persistence — same reason.

## What I'd do next
Listed in `PLAN.md → Future Roadmap`.
