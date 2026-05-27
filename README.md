# Web-design RL benchmark

A scalable pipeline that produces RL environments for evaluating coding
agents at **multi-page web-design replication**: the agent is shown
screenshots of a 5–7 page website and must reproduce the design in HTML
+ CSS. Tasks run on the [Harbor framework](https://harborframework.com/);
visual fidelity (not functionality) is graded.

This repo is a deliverable for Anthropic's recipe-design trial.

## Read this first

**→ [REPORT.md](REPORT.md)** — the full Part 1 report.

The report covers, in order:

1. **The grader** — Block-Match architecture, 9 signals, weights, anti-gaming.
2. **The pipeline** — spec-driven LLM compile, decoupled vertical/style architecture.
3. **The 11 final tasks** — distribution across (vertical × style).
4. **Empirical results** — 106 of 110 trials, per-task / per-signal distributions.
5. **Grader shortcomings** — what we know we can't catch, including §5.7 sparse / image-heavy pages.
6. **What we learned about Opus 4.7** — observed failure patterns.
7. **Reproducing the results.**
8. **Out of scope (Parts 2 and 3)** — proposed approach for animations and multi-framework support.
9. **Grader evolution: v5.2 candidate** — area-weighted aggregation + 39-trial empirical comparison.

## Visual deliverables (open in a browser)

| File | What it shows |
|---|---|
| **`report_figures/slides/index.html`** | **9-slide deck** with keyboard nav, lightbox, narration alongside each panel. The headline visual report. |
| `report_figures/v51_pairs.html` | GT-vs-agent gallery (22 best/worst pairs across 11 tasks) — anchors §4.2's correlation evidence. |
| `report_figures/slides/A_per_task_spread.png` … `F_v51_vs_v52.png` | The 6 individual slide panels as standalone PNGs. |

```bash
# from the repo root
open report_figures/slides/index.html        # the slide deck
open report_figures/v51_pairs.html           # the GT-vs-agent gallery
ls datasets/final/                           # the 11 deliverable Harbor tasks
```

## Other docs

| File | Purpose |
|---|---|
| [PIPELINE.md](PIPELINE.md) | Deeper architecture reference for the synthesis pipeline |
| [GRADER.md](GRADER.md) | Grader reasoning trail — why these signals, why these weights |
| [TAXONOMY.md](TAXONOMY.md) | The design space: 12 archetypes × 5 style axes |

## Quick run

Generate one task:

```bash
ANTHROPIC_API_KEY="$(tr -d '\n\r' < ~/.trial-anthropic-key)" \
  .venv/bin/python -m src.synthesize \
    --vertical saas_landing --style mono_warm --seed 0 \
    --out datasets/final/saas-001 --force
```

Or sample a random valid (vertical × style) pair:

```bash
.venv/bin/python -m src.synthesize --random --seed 42 \
  --out datasets/final/random-042 --force
```

Run the full Opus eval on all 11 tasks (Modal-backed, ~$80–300 / ~45-90 min):

```bash
env -i HOME=$HOME PATH=$PATH SHELL=$SHELL USER=$USER LANG=en_US.UTF-8 \
  ANTHROPIC_API_KEY="$(tr -d '\n\r' < ~/.trial-anthropic-key)" \
  harbor run -c configs/final_eval_opus.yaml -y \
  --ae ANTHROPIC_API_KEY="$(tr -d '\n\r' < ~/.trial-anthropic-key)"
```

## Repo layout

```
src/
  synthesize.py              per-page LLM compiler (the recipe)
  _blockmatch_grade.py       v5.1 grader; v5.2 mode via weighting="sqrt_area" (§9)
  _container_grade.py        helpers (CIE-Lab + tree-BLEU); shipped beside grade.py
  render.py                  host-side playwright screenshotter
  generate.py                Harbor task layout (bakes the grader)

templates/
  verticals/                 15 verticals (topic + sitemap + brand pool)
  styles/                    13 styles (palette + typography + motif)
  compatibility.py           56 valid (vertical × style) pairs

datasets/
  final/                     the 11 deliverable Harbor tasks

configs/
  final_eval_opus.yaml       Opus 4.7 × 10 trials per task on Modal

report_figures/
  v51_results.csv            106 graded trials (the data behind §4)
  v51_pairs.html             GT-vs-agent visual gallery
  v51_contact_sheet.png      single-image overview of all best/worst pairs
  pairs_v51/                 22 individual best/worst stitched PNGs
  v52_compare.csv            39-trial v5.1 vs v5.2 comparison (§9)
  adversarial_results.csv    empty + screenshot-embed cheat anchors (§1.5)
  slides/                    9-slide deck (index.html + 6 panel PNGs)
```

## What's deliberately out of scope

- **Crawling existing sites.** Forbidden by the brief.
- **Animations** (Part 2). Proposed approach + DOM-based grader extension in [REPORT §8](REPORT.md).
- **React / Tailwind / Solid** (Part 3). Proposed approach in [REPORT §8](REPORT.md); v5.1 grader is framework-agnostic by construction.
