"""Gradio entrypoint for the multi-architecture campaign benchmark."""
import asyncio
import os

import gradio as gr
import nest_asyncio
import pandas as pd
from dotenv import load_dotenv

from benchmark import BenchmarkConfig, run_benchmark

nest_asyncio.apply()
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found. Copy .env.example to .env and add your key.")


MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"]

ARCH_META = [
    ("sequential",     "Sequential Pipeline",     "Creative Director hands off to Strategist, who hands off to Copywriter. A linear chain."),
    ("orchestrator",   "Director-Orchestrator",   "The Creative Director calls Strategist and Copywriter as tools, deciding when to delegate and when to revise."),
    ("parallel_judge", "Parallel + Judge",        "Three agents each produce a complete campaign in parallel from their own perspective; an internal judge picks the best."),
]
ARCH_IDS = tuple(m[0] for m in ARCH_META)
ARCH_DISPLAY = {m[0]: m[1] for m in ARCH_META}

EXAMPLE_BRIEFS = [
    "Launch a campaign for a new eco-friendly water bottle in Bali.",
    "Promote a premium electric bicycle for urban commuters in Amsterdam.",
    "Introduce a plant-based protein bar to gym-goers in São Paulo.",
]


def _fmt_cost(v: float) -> str:
    if v is None:
        return "—"
    return f"${v:.4f}" if v >= 0.0001 else f"${v:.6f}"


def _comparison_df(bench) -> pd.DataFrame:
    by_arch = {s.architecture: s for s in bench.scores}
    rows = []
    overall_scores = {s.architecture: s.overall for s in bench.scores}
    best_arch = max(overall_scores, key=overall_scores.get) if overall_scores else None

    for r in bench.runs:
        s = by_arch.get(r.architecture)
        display = ARCH_DISPLAY.get(r.architecture, r.architecture)
        if best_arch and r.architecture == best_arch:
            display = f"★  {display}"
        rows.append({
            "Architecture": display,
            "Tokens": f"{r.total_tokens:,}",
            "Latency": f"{r.total_latency_s:.1f}s",
            "Cost": _fmt_cost(r.total_cost_usd),
            "Creativity": s.creativity if s else "—",
            "Strategic Fit": s.strategic_fit if s else "—",
            "Copy Quality": s.copy_quality if s else "—",
            "Overall": s.overall if s else "—",
            "Notes": r.error or "",
        })
    return pd.DataFrame(rows)


def _per_call_df(bench) -> pd.DataFrame:
    rows = []
    for r in bench.runs:
        arch_display = ARCH_DISPLAY.get(r.architecture, r.architecture)
        for c in r.calls:
            rows.append({
                "Architecture": arch_display,
                "Agent": c.agent_name,
                "Latency": f"{c.latency_s:.1f}s",
                "Prompt Tokens": f"{c.usage.prompt_tokens:,}",
                "Completion Tokens": f"{c.usage.completion_tokens:,}",
                "Total Tokens": f"{c.usage.total_tokens:,}",
                "Cost": _fmt_cost(c.usage.cost_usd),
            })
    return pd.DataFrame(rows)


def _final_for(bench, arch_id: str) -> str:
    run = next((r for r in bench.runs if r.architecture == arch_id), None)
    if run is None:
        return "(not run)"
    if run.error:
        return f"This architecture failed:\n\n{run.error}"
    return run.final_output


def _judge_markdown(bench) -> str:
    if not bench.scores:
        return "_The Benchmark Judge produced no scores. This usually means none of the architectures succeeded._"
    overall = {s.architecture: s.overall for s in bench.scores}
    best = max(overall, key=overall.get)
    blocks = []
    for s in bench.scores:
        display = ARCH_DISPLAY.get(s.architecture, s.architecture)
        crown = "  ★ winner" if s.architecture == best else ""
        blocks.append(
            f"### {display}{crown}\n"
            f"| Creativity | Strategic Fit | Copy Quality | **Overall** |\n"
            f"|---|---|---|---|\n"
            f"| {s.creativity}/10 | {s.strategic_fit}/10 | {s.copy_quality}/10 | **{s.overall}/10** |\n\n"
            f"{s.reasoning}"
        )
    return "\n\n".join(blocks)


def _empty_dataframe(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


_EMPTY_COMPARISON = _empty_dataframe(
    ["Architecture", "Tokens", "Latency", "Cost", "Creativity", "Strategic Fit", "Copy Quality", "Overall", "Notes"]
)
_EMPTY_CALLS = _empty_dataframe(
    ["Architecture", "Agent", "Latency", "Prompt Tokens", "Completion Tokens", "Total Tokens", "Cost"]
)
_EMPTY_JUDGE_MD = (
    "_Run a benchmark to see how each architecture scores on creativity, strategic fit, and copy quality._"
)


def run_ui(brief, cd_model, strat_model, copy_model, judge_model, execution, progress=gr.Progress(track_tqdm=False)):
    if not brief or not brief.strip():
        return (
            _EMPTY_COMPARISON,
            _EMPTY_CALLS,
            _EMPTY_JUDGE_MD,
            "",
            "",
            "",
            "**Please enter a campaign brief before running.**",
        )

    progress(0.05, desc="Building agent configuration…")
    config = BenchmarkConfig(
        cd_model=cd_model,
        strat_model=strat_model,
        copy_model=copy_model,
        judge_model=judge_model,
        execution=execution,
        enabled_architectures=ARCH_IDS,
    )

    progress(0.15, desc=f"Running {len(ARCH_IDS)} architectures ({execution})…")
    bench = asyncio.run(run_benchmark(brief, config))

    progress(0.9, desc="Scoring with the Benchmark Judge…")
    ok = sum(1 for r in bench.runs if r.error is None)
    total_tokens = sum(r.total_tokens for r in bench.runs)
    total_cost = sum(r.total_cost_usd for r in bench.runs)
    status_msg = (
        f"**Benchmark complete.** {ok}/{len(bench.runs)} architectures succeeded · "
        f"{total_tokens:,} tokens · {_fmt_cost(total_cost)} total."
    )
    progress(1.0, desc="Done")

    return (
        _comparison_df(bench),
        _per_call_df(bench),
        _judge_markdown(bench),
        _final_for(bench, "sequential"),
        _final_for(bench, "orchestrator"),
        _final_for(bench, "parallel_judge"),
        status_msg,
    )


_CUSTOM_CSS = """
:root {
    --paper:        #F8F4ED;
    --paper-deep:   #F1EAD9;
    --ink:          #1C1B1A;
    --ink-soft:     #4A4742;
    --ink-mute:     #8A857C;
    --rule:         #1C1B1A;
    --accent:       #C24F1A;
    --accent-soft:  #FBE6D6;
}

/* Base canvas */
body, .gradio-container {
    background: var(--paper) !important;
    color: var(--ink) !important;
    font-family: "Manrope", -apple-system, "Segoe UI", sans-serif !important;
    font-feature-settings: "ss01", "cv11";
}
.gradio-container {
    max-width: 1180px !important;
    margin: 0 auto !important;
    padding: 28px 28px 64px !important;
}

/* Subtle paper grain — SVG data URI noise overlay */
body::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    opacity: 0.06;
    mix-blend-mode: multiply;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");
}

/* Headings — display serif */
h1, h2, h3, h4, .display-serif {
    font-family: "Fraunces", "Georgia", serif !important;
    color: var(--ink) !important;
    font-weight: 500 !important;
    letter-spacing: -0.012em !important;
    font-feature-settings: "ss01", "ss02";
}

/* Masthead */
#masthead {
    border-top: 4px solid var(--ink);
    border-bottom: 1px solid var(--ink);
    padding: 18px 0 22px 0;
    margin-bottom: 24px;
    animation: fadeUp 0.55s ease both 0s;
}
#masthead .kicker {
    font-family: "JetBrains Mono", "SF Mono", monospace;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: var(--ink-mute);
    margin-bottom: 6px;
}
#masthead h1 {
    font-size: clamp(34px, 5vw, 58px) !important;
    line-height: 1.02;
    margin: 0 0 8px 0 !important;
    font-weight: 400 !important;
    font-variation-settings: "opsz" 144;
}
#masthead h1 em {
    font-style: italic;
    color: var(--accent);
    font-variation-settings: "SOFT" 100, "opsz" 144;
}
#masthead .lede {
    font-size: 16px;
    max-width: 62ch;
    color: var(--ink-soft);
    line-height: 1.55;
}

/* Section dividers */
.section-rule {
    border-top: 1px solid var(--ink);
    margin: 28px 0 16px 0;
    padding-top: 12px;
}
.section-rule .label {
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    color: var(--ink-mute);
}

/* Architecture cards */
#arch-cards {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0;
    margin: 6px 0 4px 0;
    border-top: 1px solid var(--ink);
    border-bottom: 1px solid var(--ink);
    animation: fadeUp 0.65s ease both 0.08s;
}
.arch-card {
    padding: 18px 20px 20px;
    border-right: 1px solid var(--ink);
    position: relative;
    background: transparent;
    transition: background 0.18s ease;
}
.arch-card:last-child { border-right: none; }
.arch-card:hover { background: var(--paper-deep); }
.arch-card .index {
    font-family: "Fraunces", serif;
    font-size: 14px;
    font-weight: 400;
    color: var(--accent);
    letter-spacing: 0.05em;
    margin-bottom: 8px;
}
.arch-card .name {
    font-family: "Fraunces", serif;
    font-size: 20px;
    font-weight: 500;
    line-height: 1.15;
    margin-bottom: 8px;
    color: var(--ink);
    font-variation-settings: "opsz" 18;
}
.arch-card .desc {
    font-size: 13.5px;
    color: var(--ink-soft);
    line-height: 1.5;
}
@media (max-width: 760px) {
    #arch-cards { grid-template-columns: 1fr; }
    .arch-card { border-right: none; border-bottom: 1px solid var(--ink); }
    .arch-card:last-child { border-bottom: none; }
}

/* Textbox + dropdowns */
textarea, input, .gradio-container .form, .block {
    background: var(--paper) !important;
    color: var(--ink) !important;
}
textarea, input[type="text"], .scroll-hide {
    border: 1px solid var(--ink) !important;
    border-radius: 0 !important;
    background: var(--paper) !important;
    font-family: "Manrope", sans-serif !important;
    font-size: 15px !important;
}
label, .gr-label, span[data-testid="block-label"] {
    font-family: "JetBrains Mono", monospace !important;
    font-size: 10px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.18em !important;
    color: var(--ink-mute) !important;
}

/* Big primary button */
#run-button {
    background: var(--ink) !important;
    color: var(--paper) !important;
    border: none !important;
    border-radius: 0 !important;
    font-family: "Manrope", sans-serif !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    min-height: 54px !important;
    transition: background 0.18s ease, transform 0.08s ease !important;
    animation: fadeUp 0.65s ease both 0.16s;
}
#run-button:hover { background: var(--accent) !important; }
#run-button:active { transform: translateY(1px); }

/* Status strip */
#status-bar {
    border-top: 1px solid var(--ink);
    border-bottom: 1px solid var(--ink);
    padding: 14px 0 !important;
    margin: 18px 0 !important;
    background: transparent !important;
    font-family: "JetBrains Mono", monospace !important;
    font-size: 13px !important;
    color: var(--ink-soft) !important;
}
#status-bar strong { color: var(--ink); }
#status-bar p { margin: 0 !important; }

/* Tabs */
.tab-nav, [role="tablist"] {
    border-bottom: 1px solid var(--ink) !important;
    gap: 4px !important;
    margin-bottom: 14px !important;
}
.tab-nav button, [role="tab"] {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    color: var(--ink-mute) !important;
    font-family: "JetBrains Mono", monospace !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.16em !important;
    padding: 12px 14px !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -1px !important;
}
.tab-nav button.selected, [role="tab"][aria-selected="true"] {
    color: var(--ink) !important;
    border-bottom: 2px solid var(--accent) !important;
}

/* Examples chips */
.examples-row button, [data-testid="example"] {
    background: var(--paper) !important;
    border: 1px solid var(--ink) !important;
    border-radius: 0 !important;
    color: var(--ink) !important;
    font-family: "Manrope", sans-serif !important;
    font-size: 12px !important;
    padding: 6px 10px !important;
    transition: background 0.15s ease;
}
.examples-row button:hover, [data-testid="example"]:hover {
    background: var(--accent-soft) !important;
}

/* Dataframe — monospace numerals, ruled rows */
table {
    font-family: "JetBrains Mono", "SF Mono", monospace !important;
    font-size: 12.5px !important;
    border-collapse: collapse !important;
}
table thead th {
    background: var(--paper-deep) !important;
    color: var(--ink) !important;
    font-family: "JetBrains Mono", monospace !important;
    font-size: 10px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.14em !important;
    border-bottom: 1px solid var(--ink) !important;
    padding: 10px 12px !important;
    text-align: left !important;
}
table tbody td {
    border-bottom: 1px solid var(--paper-deep) !important;
    padding: 10px 12px !important;
    color: var(--ink) !important;
    font-feature-settings: "tnum";
}

/* Output textboxes (final campaigns) */
.gradio-container textarea[readonly] {
    background: var(--paper-deep) !important;
    border: 1px solid var(--ink) !important;
    font-family: "Manrope", sans-serif !important;
    font-size: 14px !important;
    line-height: 1.55 !important;
    color: var(--ink) !important;
}

/* Accordion */
[data-testid="accordion"], .gr-accordion {
    border: 1px solid var(--ink) !important;
    border-radius: 0 !important;
    background: transparent !important;
}
[data-testid="accordion"] > button, .gr-accordion > button {
    font-family: "JetBrains Mono", monospace !important;
    text-transform: uppercase !important;
    letter-spacing: 0.18em !important;
    font-size: 11px !important;
    color: var(--ink) !important;
}

/* Judge reasoning blocks */
.judge-reasoning h3 { margin-top: 18px; }
.judge-reasoning table { margin: 6px 0 10px 0; }

/* Running indicator — visible during long benchmark runs */
#run-button[disabled], #run-button.processing {
    background: var(--accent) !important;
    color: var(--paper) !important;
    cursor: progress !important;
    position: relative;
}
#run-button[disabled]::after {
    content: "";
    position: absolute;
    left: 0; right: 0; bottom: 0;
    height: 3px;
    background: linear-gradient(90deg, transparent, var(--paper) 50%, transparent);
    animation: marquee 1.4s linear infinite;
}
@keyframes marquee {
    from { transform: translateX(-100%); }
    to   { transform: translateX(100%); }
}

/* Subtle stagger animations */
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
.fade-1 { animation: fadeUp 0.6s ease both 0.20s; }
.fade-2 { animation: fadeUp 0.6s ease both 0.28s; }
.fade-3 { animation: fadeUp 0.6s ease both 0.36s; }

/* Responsive: stack brief/config and tighten paddings on narrow screens */
@media (max-width: 760px) {
    .gradio-container { padding: 18px 16px 48px !important; }
    #masthead h1 { font-size: 34px !important; }
    .gradio-container > .form > .gr-form,
    .gradio-container .gr-form > .form { flex-direction: column !important; }
    /* Force the brief+config Row to stack */
    .gradio-container .gr-form .gr-form,
    .gradio-container [class*="row"] [class*="column"] { width: 100% !important; }
    /* Final outputs row stacks too */
    .gradio-container [class*="row"] textarea { width: 100% !important; }
}
@media (max-width: 540px) {
    #masthead .lede { font-size: 14px; }
    table { font-size: 11.5px !important; }
    table thead th, table tbody td { padding: 8px 8px !important; }
}

/* Reduced motion preference */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition: none !important; }
}

/* Footer mark */
#colophon {
    margin-top: 36px;
    padding-top: 14px;
    border-top: 1px solid var(--ink);
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: var(--ink-mute);
    display: flex;
    justify-content: space-between;
}
"""


_MASTHEAD_HTML = """
<div id="masthead">
  <div class="kicker">Vol. 01 · Multi-Architecture Agent Benchmark · OpenAI Agents SDK</div>
  <h1>Three architectures. One brief. <em>One winner.</em></h1>
  <p class="lede">A side-by-side benchmark of three agent orchestration patterns — sequential, director-led, and parallel-with-judge — on the same marketing brief. Token usage, latency, cost, and a blind quality score, reported together.</p>
</div>
"""


_ARCH_CARDS_HTML = """
<div id="arch-cards">
  <div class="arch-card">
    <div class="index">01 / Linear</div>
    <div class="name">Sequential Pipeline</div>
    <div class="desc">Creative Director hands off to Strategist, who hands off to Copywriter. Each agent does its specialty stage and passes the result downstream.</div>
  </div>
  <div class="arch-card">
    <div class="index">02 / Hub</div>
    <div class="name">Director-Orchestrator</div>
    <div class="desc">The Creative Director acts as the central agent and calls the Strategist and Copywriter as tools, deciding when to delegate and when to revise.</div>
  </div>
  <div class="arch-card">
    <div class="index">03 / Parallel</div>
    <div class="name">Parallel + Judge</div>
    <div class="desc">All three agents produce a complete campaign in parallel from their own professional perspective; an internal judge picks the strongest.</div>
  </div>
</div>
"""


_THEME = gr.themes.Soft(
    primary_hue="orange",
    neutral_hue="stone",
    font=[gr.themes.GoogleFont("Manrope"), "system-ui", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"],
)

# Display font (Fraunces) loaded via @import inside CSS so it doesn't conflict with theme fonts
_FONTS_PRELUDE = (
    "@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght,SOFT@0,9..144,300..700,30..100;1,9..144,300..700,30..100&display=swap');"
)


with gr.Blocks(title="Multi-Arch Campaign Benchmark") as demo:
    gr.HTML(_MASTHEAD_HTML)

    gr.HTML('<div class="section-rule"><span class="label">§ 01 — Architectures under test</span></div>')
    gr.HTML(_ARCH_CARDS_HTML)

    gr.HTML('<div class="section-rule"><span class="label">§ 02 — Brief & configuration</span></div>')

    with gr.Row(elem_classes="fade-1"):
        with gr.Column(scale=3):
            brief = gr.Textbox(
                label="Campaign brief",
                placeholder="Describe the product, audience, and any constraints — e.g. \"Launch a new eco-friendly water bottle in Bali targeting eco-conscious travellers.\"",
                lines=4,
            )
            with gr.Row(elem_classes="examples-row"):
                gr.Examples(
                    examples=[[b] for b in EXAMPLE_BRIEFS],
                    inputs=brief,
                    label="Try an example brief",
                )

        with gr.Column(scale=2):
            with gr.Accordion("Configuration — models & execution", open=False):
                gr.Markdown("Same model across every role makes the comparison fair. Mix them to test how much the model matters.")
                cd_model = gr.Dropdown(MODELS, value="gpt-4o-mini", label="Creative Director")
                strat_model = gr.Dropdown(MODELS, value="gpt-4o-mini", label="Strategist")
                copy_model = gr.Dropdown(MODELS, value="gpt-4o-mini", label="Copywriter")
                judge_model = gr.Dropdown(MODELS, value="gpt-4o-mini", label="Benchmark Judge")
                execution = gr.Radio(
                    [("Sequential — one architecture at a time", "sequential"),
                     ("Parallel — run all three concurrently", "parallel")],
                    value="sequential",
                    label="Execution",
                )

    btn = gr.Button("Run Benchmark", variant="primary", elem_id="run-button")
    status = gr.Markdown(
        "_Idle._  Enter a brief above and run the benchmark. Expect about 30–60 seconds on `gpt-4o-mini`.",
        elem_id="status-bar",
    )

    gr.HTML('<div class="section-rule"><span class="label">§ 03 — Findings</span></div>')

    with gr.Tabs():
        with gr.Tab("Comparison"):
            metrics_df = gr.Dataframe(
                value=_EMPTY_COMPARISON,
                label="",
                headers=list(_EMPTY_COMPARISON.columns),
                interactive=False,
                wrap=True,
            )
            with gr.Accordion("Judge reasoning", open=True):
                judge_md = gr.Markdown(_EMPTY_JUDGE_MD, elem_classes="judge-reasoning")

        with gr.Tab("Final Outputs"):
            gr.Markdown("_Each column is the final campaign produced by one architecture, exactly as written by its last agent._")
            with gr.Row():
                seq_out = gr.Textbox(label="01 · Sequential Pipeline", lines=18, interactive=False)
                orch_out = gr.Textbox(label="02 · Director-Orchestrator", lines=18, interactive=False)
                par_out = gr.Textbox(label="03 · Parallel + Judge", lines=18, interactive=False)

        with gr.Tab("Per-Call Detail"):
            gr.Markdown("_Every individual agent call — what ran inside each architecture, with its own latency and token usage._")
            calls_df = gr.Dataframe(
                value=_EMPTY_CALLS,
                label="",
                headers=list(_EMPTY_CALLS.columns),
                interactive=False,
                wrap=True,
            )

    gr.HTML(
        '<div id="colophon">'
        '<span>Built with the OpenAI Agents SDK · Gradio</span>'
        '<span>Multi-Arch Benchmark · Vol. 01</span>'
        '</div>'
    )

    def _starting():
        return "**Running benchmark…** The button below the brief stays orange until all three architectures and the judge have finished."

    btn.click(
        fn=_starting,
        inputs=None,
        outputs=status,
    ).then(
        run_ui,
        inputs=[brief, cd_model, strat_model, copy_model, judge_model, execution],
        outputs=[metrics_df, calls_df, judge_md, seq_out, orch_out, par_out, status],
    )

if __name__ == "__main__":
    demo.launch(theme=_THEME, css=_FONTS_PRELUDE + _CUSTOM_CSS)
