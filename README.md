# Web-design RL benchmark

A scalable pipeline that produces RL environments for evaluating coding
agents at **multi-page web-design replication**: the agent is shown
screenshots of a 5–6 page website and must reproduce the design in HTML
+ CSS. Tasks run on the [Harbor framework](https://harborframework.com/);
visual fidelity (not functionality) is graded.

This repo is a deliverable for Anthropic's recipe-design trial.

## Start here

- **[REPORT.md](REPORT.md)** — the full report: pipeline architecture,
  design decisions with research backing, the 10 final tasks, the
  grader, and empirical results. Read this first.
- **[GRADER.md](GRADER.md)** — the v3.4 grader's reasoning trail (every
  signal, every weight, every alternative considered + rejected, plus
  the 4-step calibration on 10 Design2Code tasks).
- **[TAXONOMY.md](TAXONOMY.md)** — the design space we sample: 12
  archetypes × 5 style axes, the 10-task slate, exclusions, AI tells.
- **[CLAUDE.md](CLAUDE.md)** — operating context for the Claude Code
  session that built this. Useful as a session resume.

## Quick run

```bash
# Generate a task
ANTHROPIC_API_KEY="$(tr -d '\n\r' < ~/.trial-anthropic-key)" \
  .venv/bin/python -m src.synthesize --template saas_minimal --seed 0 \
    --out datasets/final/saas_minimal-001 --force

# Or pick at random
ANTHROPIC_API_KEY=... .venv/bin/python -m src.synthesize \
  --random-template --seed 42 --out datasets/final/random-042 --force

# Run an oracle trial (sanity)
harbor trial start -p datasets/final/saas_minimal-001 -a oracle
```

## Repo map

```
src/
  synthesize.py          per-page LLM compiler (the recipe)
  _container_grade.py    grader v3.4 (template baked into every task)
  render.py              host-side playwright screenshotter
  generate.py            Harbor task layout
  report_aggregate.py    reads jobs/<run>/ → markdown table
  report_plots.py        score box plots + signal breakdown bars
  report_pairs.py        side-by-side GT vs agent screenshots

templates/
  _base.py               TemplateMeta dataclass + sampling helpers
  _brands.py             26 brand personas across 8 verticals
  _palettes.py           palettes grouped by color regime
  _fonts.py              font pairs grouped by typography axis
  saas_minimal.py        A1 SaaS × pastel × hairline-1px (saturated)
  pricing_dark.py        A8 pricing × dark-native (saturated)
  auth_glassy.py         A12 auth × glassy-blurred (saturated)
  docs_mono.py           A3 docs × mono-everywhere (high-signal)
  editorial_serif.py     A6 editorial × serif × narrow (high-signal)
  dashboard_dense.py     A4 dashboard × dense × dark (high-signal)
  portfolio_neobrut.py   A7 portfolio × thick-borders (high-signal)
  ecom_pastel.py         A5 ecom × pastel × photographic (high-signal)
  splash_3d.py           A9 splash × abstract-3d × cinematic (high-signal)
  restaurant_photo.py    A11 hospitality × photographic (high-signal)

tests/
  test_templates.py      330 invariants (META vs sampler consistency)

configs/
  final_eval_opus.yaml   Opus 4.7 × 10 trials per task on Modal
  calibration_*.yaml     historical (4-step grader calibration)

datasets/
  final/                 the 10 final tasks (the deliverable)
  calibration/           10 D2C tasks used for grader calibration only
```

## What's deliberately out of scope

- **Crawling existing sites.** Forbidden by the brief. All websites
  are generated from scratch.
- **Animations and interaction.** Out of scope per brief Part 1.
  Architecture supports adding it later.
- **React / Tailwind / Solid frameworks.** Out of scope per brief Part 1.
  The pipeline is framework-agnostic at the spec level; a different
  compiler stage could target React or Solid instead of plain HTML/CSS.

## Reproducibility

Every artifact is keyed by `(template, seed)` and is bit-for-bit
deterministic given the same `random.Random(seed)` (the LLM compile
itself is non-deterministic, so the final task is per-run unique;
the *spec* feeding the compile is reproducible).
