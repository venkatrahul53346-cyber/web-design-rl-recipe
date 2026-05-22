# Web Design RL Environment Pipeline — session context

This repo builds RL environments where a coding agent is shown screenshots
of a website and must replicate the visual design in HTML/CSS. Tasks run
on **Harbor** (`harborframework.com`, installed via
`uv tool install harbor --with modal`). Functionality is out of scope —
only visual fidelity is graded.

> **Operator note:** an Anthropic API key was once pasted in plaintext in a
> prior session and is compromised. Rotate at
> `https://console.anthropic.com/settings/keys` if you haven't already.
> Read `ANTHROPIC_API_KEY` from environment only. Never accept inline keys.

## Where we are

**Phase 1 (grader confidence): DONE.** The grader at
`src/_container_grade.py` is at v3, accepted as the v1 baseline on
2026-05-21. See `GRADER.md` for the full reasoning trail — it documents
every signal, every weight, every alternative we considered and rejected,
and the 4-step calibration results across v0/v1/v2/v3.

**Phase 2 (synthesis pipeline): NEXT.** Build a from-scratch generator
that produces multi-page (≥5) website tasks. The 10 final deliverable
tasks come from this pipeline. The brief explicitly forbids crawling
existing websites.

The 10 D2C calibration tasks at `datasets/calibration/` were used for
grader iteration only and don't ship as deliverables — they're the
regression suite for any future grader change.

## v3 grader summary

Five signals, all from one playwright pass per page:

| Signal | Weight | What it asks |
|---|---:|---|
| Layout | 0.30 | "Are elements in the right places?" (per-tag bbox IoU) |
| Visual | 0.25 | "Do the screenshots look the same pixel-wise?" (SSIM) |
| Component recall | 0.20 | "Are the important elements present?" (weighted tag count) |
| Text | 0.15 | "Did you preserve the meaningful copy?" (weighted token F1) |
| Style | 0.10 | "Are the brand colors right?" (HSV histogram cosine) |

Validation results (10 D2C calibration tasks):
- Sanity: oracle=1.000, nop=0.000 ✓
- Perturbation: 10/10 monotonic, range 1.000→0.394 ✓
- Cross-model: opus(0.493) > sonnet(0.460) > haiku(0.411) ✓
- Step 4 user agreement: 13/15 (close-pair noise; see GRADER.md §6.5)

## Repo layout

```
trial/
├── src/
│   ├── generate.py             # writes Harbor task dirs (current entry point)
│   ├── render.py               # host-side playwright screenshotter
│   ├── _container_grade.py     # source-of-truth for tests/grade.py (v3)
│   ├── ingest_design2code.py   # HF Design2Code → Harbor task (calibration only)
│   ├── ingest_modern.py        # monolith snapshots → Harbor task (archived)
│   ├── perturb.py              # severity-parameterised HTML perturbation
│   └── build_perturb_tasks.py  # generates perturbed variants for Step 2
├── templates/
│   └── marketing.py            # v0 5-page marketing template (still works,
│                               # but conflicts with the brief — Phase 2 will
│                               # replace it)
├── configs/
│   ├── local.yaml              # Docker, single trial
│   ├── modal.yaml              # Modal, parallel trials
│   ├── calibration_sanity.yaml # Step 1 protocol (oracle + nop)
│   ├── calibration_perturb.yaml# Step 2 protocol (perturbed variants)
│   └── calibration_models.yaml # Step 3 protocol (haiku/sonnet/opus)
├── datasets/
│   ├── calibration/            # 10 D2C tasks + picks.txt — REGRESSION SUITE
│   ├── perturbed/              # 40 perturbed variants (Step 2 inputs)
│   ├── _modern_archive/        # 5 monolith snapshots (out-of-brief; kept private)
│   └── web-design/             # legacy v0 marketing tasks
├── trials/, jobs/              # Harbor outputs (auto-generated)
├── GRADER.md                   # canonical grader reasoning trail (READ ME)
├── DESIGN.md                   # broader design log (older)
├── README.md
└── requirements.txt            # offline (.venv) deps for generate-time only
```

## Phase 2 plan (sketch — to flesh out next)

The brief says: generate websites from scratch, ≥5 pages each, varied
distribution of types, modern-feeling. Glean research recommends a
"WebsiteSpec → design tokens → page specs → reference code → screenshots
→ QC → Harbor task" pipeline rather than direct LLM-to-HTML generation.

Open architecture questions for next session:
1. Spec format. JSON schema covering vertical/audience/brand/sitemap/
   design tokens/page specs/components.
2. Generation strategy. LLM produces the spec; deterministic compiler
   produces HTML/CSS from the spec. Avoids the "LLM directly writes HTML
   that's brittle and template-feeling" failure mode.
3. Diversity sampling. Cover archetypes (SaaS, e-commerce, docs, blog,
   editorial, dashboard, …) × style families × layout complexities.
4. Quality control gates. Build success, all routes render, screenshots
   stable, no blank regions, perceptual deduplication.
5. Validation. Generated tasks should pass the v3 grader's sanity check
   (oracle=1.000) — that's how we know synthesis didn't break anything.

When restarting Phase 2, read `GRADER.md` first, then this CLAUDE.md.

## Critical conventions (don't break these)

- **`reward.json` must be flat scalars only** (Harbor schema enforces it).
- **Render BOTH GT and agent in the same chromium in the container.**
- **`wait_until="load"`, NOT `"networkidle"`**, for `file://` URLs.
- **`mcr.microsoft.com/playwright/python:v1.50.0-noble`** ships chromium
  binaries but NOT the playwright Python package. Dockerfile must
  `pip install playwright==1.50.0` and set `PLAYWRIGHT_BROWSERS_PATH`.
- **`environment/assets/` must never be empty** — write a `.harbor-keep`
  placeholder so Modal's image builder doesn't fail. `build_task_dir`
  does this automatically.
- **`harbor` invocations must use `env -i` to isolate from parent shell**
  to avoid the Vertex AI env leak (see memory).

## Modal setup (one-time, already done on this machine)

```bash
uv tool install --force harbor --with modal
uv tool install modal
modal token new                    # browser auth → ~/.modal.toml
modal token info                   # verify
```

Workspace `venkatrahul53346`. Token at `~/.modal.toml`.

## Running with Claude (gotcha)

The host shell on this machine has Vertex AI vars set
(`ANTHROPIC_BASE_URL`, `CLAUDE_CODE_USE_VERTEX`). Harbor's `claude-code`
agent inherits them and forwards them into the sandbox — an `sk-ant-*`
key gets authenticated against Vertex and 401s. Always use `env -i`:

```bash
env -i HOME=$HOME PATH=$PATH SHELL=$SHELL USER=$USER LANG=en_US.UTF-8 \
  ANTHROPIC_API_KEY="$(tr -d '\n\r' < ~/.trial-anthropic-key)" \
  harbor run -c configs/<config>.yaml -y \
  --ae ANTHROPIC_API_KEY="$(tr -d '\n\r' < ~/.trial-anthropic-key)"
```

## Hard rules

- Never write secrets to disk. `ANTHROPIC_API_KEY` from env only.
- Never use `git clean -f`, `git reset --hard`, or destructive ops without
  asking. The user has uncommitted state.
- Don't run `bazel clean --expunge` (parent repo `scio` rule).

## Style notes (from prior sessions, repo-local)

- Heredoc `cat > file << 'EOF' ... EOF` is more reliable than the Write
  tool for large multi-line files in this environment. Some Write calls
  end up with a literal `[{"text": ...}]` JSON wrapper. Heredoc dodges that.
- Python venv at `.venv/`. Use `.venv/bin/python`. Modal-side deps are
  in the Dockerfile (in `src/generate.py`'s `DOCKERFILE` constant).
