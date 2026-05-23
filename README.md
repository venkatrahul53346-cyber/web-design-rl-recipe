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

1. **The grader** — Block-Match architecture, 9 signals, weights,
   anti-gaming.
2. **The pipeline** — spec-driven LLM compile, decoupled vertical/style
   architecture.
3. **The 11 final tasks** — distribution across (vertical × style).
4. **Empirical results** — 106 of 110 trials, per-task / per-signal
   distributions.
5. **Grader shortcomings** — what we know we can't catch.
6. **What we learned about Opus 4.7** — observed failure patterns.

Open `report_figures/v51_pairs.html` in a browser for the visual
GT-vs-agent gallery that anchors the correlation evidence in §4.2.

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
  _blockmatch_grade.py       v5.1 Block-Match grader (primary)
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
```

## What's deliberately out of scope

- **Crawling existing sites.** Forbidden by the brief.
- **Animations** (Part 2 of the brief). Architecture supports it later.
- **React / Tailwind / Solid** (Part 3). The pipeline is framework-
  agnostic at the spec level.
