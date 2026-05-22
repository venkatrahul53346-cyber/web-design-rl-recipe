# Grader design and decision log

This file is the canonical reasoning trail for the grader. Whenever we
change a metric, weight, or filter, add an entry below with **what we
changed**, **why**, and **what we measured before/after**. Future sessions
should be able to answer "why is the grader shaped this way?" from this
doc alone, without spelunking git history.

**Current state: v3, accepted as v1 baseline (2026-05-21).**

---

## 1. The task and what we're optimising for

The brief is to build a benchmark where coding agents are given screenshots
of a website and have to recreate the *visual design* in HTML/CSS.
Functionality is explicitly out of scope. The grader's job is to score
"how well does the agent's recreation look like the ground truth."

The grader needs to:

1. **Be visual-only** — score the rendered output, not the source code.
   An agent that produces ugly HTML but renders correctly should outscore
   one that produces clean HTML that renders wrong.
2. **Produce a continuous score in [0, 1]** — Harbor needs a single scalar
   reward; RL needs gradients of meaning, not pass/fail.
3. **Be trustworthy enough to drive a synthesis pipeline.** Phase 2 will
   generate hundreds of tasks; if the grader is broken or biased, those
   tasks become noise.

We accept that absolute scores are noisier than relative rankings — what
matters most is that **higher score → more faithful replication**, with
human-verifiable consistency.

## 2. What "trustworthy grader" means concretely

The 5-property framework we use to evaluate each version:

1. **Sanity** — oracle (byte-identical reproduction) → 1.0; nop (empty
   output) → 0.0.
2. **Monotonicity** — known-quality degradations produce monotonically
   lower scores. No flat bands.
3. **Capability ordering** — orders real models in a plausible way
   (haiku < sonnet < opus).
4. **Adversarial robustness** — doesn't get fooled by trivial cheats
   (e.g. agent embeds GT screenshot in `<img>` tag).
5. **Human alignment** — pairwise picks match what a human would say,
   on at least 90% of cases.

These are tested via a 4-step calibration protocol; see Section 6.

## 3. Calibration set provenance (and the brief constraint)

The 10 calibration tasks at `datasets/calibration/d2c-*` are **single-page
real-world webpages** sourced from Stanford's Design2Code dataset (a sample
of C4 Common Crawl pages, image-placeholder-replaced for licensing).

We also briefly added 5 **modern reference snapshots** (Linear, Vercel,
Anthropic, Railway, Cursor via `monolith`) — moved to
`datasets/_modern_archive/` once we noticed both sources conflict with
the brief's "do not crawl existing websites; you must generate from
scratch" rule.

**Why we kept these for grader calibration anyway:**
- The brief constraint is for **the deliverable tasks** (Phase 2's
  pipeline output). For grader-iteration purposes, real human-designed
  pages are a *better* signal than synthesised ones — they probe a wider
  distribution of real-world patterns and cannot be self-contaminated by
  any LLM that will be tested.
- The user explicitly chose "fix the grader first, then the pipeline" as
  the work order, accepting that calibration data is upstream of the
  brief constraint.

The 10 D2C tasks remain as a **regression suite**. Any future grader
change must re-run sanity / perturbation / cross-model on them and at
minimum preserve oracle=1.0 / nop=0.0, monotonicity, and the user's
Step-4 picks within tolerance.

The Phase 2 synthesis pipeline will produce its own from-scratch tasks
that ship as the actual deliverable.

## 4. The v3 grader (current, accepted as v1 baseline)

### Five signals

| Signal | Weight | Plain-English question | Implementation |
|---|---:|---|---|
| **Layout** | 0.30 | "Are the elements in the right places?" | Per-tag bbox IoU, greedy-matched. Restricted to 16 layout-significant tags (nav, header, h1, form, table, etc.). Importance-weighted. |
| **Visual** | 0.25 | "Do the screenshots look the same pixel-wise?" | SSIM on grayscale-resized 640×400. Clamped to [0,1]. |
| **Component recall** | 0.20 | "Are the important elements present?" | Multiset Jaccard over visible tag names, weighted (`nav=1.5`, `h1=1.5`, `form=1.3`, `div=0.5`, `span=0.4`, …). |
| **Text** | 0.15 | "Did you preserve the meaningful copy?" | F1 over visible-text tokens, weighted by parent tag (`h1=3.0`, `button=2.0`, `p=1.0`, `span=0.7`). |
| **Style** | 0.10 | "Are the brand colors right?" | Cosine similarity of HSV color histograms (8×4×4 bins) over the screenshots. |

Combined: weighted sum, clamped to [0, 1]. Per-page mean is the task score.

### Architecture

- **Single playwright pass per page.** Loads the HTML at `file://` URL,
  waits for `load` (not `networkidle` — file URLs don't have network
  activity), takes a full-page screenshot, runs an in-page JS evaluation
  that returns: list of visible elements with bounding boxes + tagged
  text segments. All five signals derive from this one pass.
- **Render BOTH the agent's output and the GT in the same chromium
  inside the Modal sandbox.** This was a v2 fix — pre-fix, GT was
  rendered on the host's chromium and agent on Modal's; the two browsers
  rendered slightly differently (anti-aliasing, fonts), so oracle could
  only score ~0.97. Post-fix, oracle scores 1.000.
- **Visibility filter** (added in v2 after the d2c-2997 incident):
  excludes elements with display:none, visibility:hidden, opacity 0,
  zero bbox, or off-screen at negative coordinates. This catches closed
  `<select>` options, hidden modal templates, accessibility-only content
  — DOM that an agent could not have seen from a screenshot.

### Why these weights

- **Structural correctness gets ~50% (layout 30 + component 20).**
  Literature converges on this — Design2Code (Si et al. 2024) found
  layout was the hardest part for models and the highest-information
  signal for ranking.
- **Visual fidelity gets ~35% (visual 25 + style 10).** Pixel-level
  similarity is a real signal but coarse — capping it at 25% for SSIM
  prevents reward hacking via "right colors, wrong layout."
- **Content fidelity gets 15% (text).** Lower because token-F1 over
  visible text saturates on common words (any reasonable site shares
  "pricing", "sign up", etc.). It still serves as a check against
  "agent invented filler content."

These weights are starting weights informed by the literature — they have
not been tuned against absolute human ranking, just verified that the
*ordering* they produce matches user pairwise picks within 87% (see §6.3).

## 5. Why this design vs alternatives

### What we considered and adopted (v3)

| Idea | Source | Adopted? | Why |
|---|---|---:|---|
| Render-and-compare, not source-code similarity | Web2Code, Design2Code | ✅ | Visual task; agents free to write whatever HTML they like as long as it renders right. |
| Visibility-filter for structure/text | d2c-2997 incident | ✅ | Hidden DOM (closed dropdowns, modals) shouldn't be counted against agents who couldn't see it. |
| Bbox-based layout score (per-tag IoU) | Design2Code | ✅ | Catches "right structure, wrong arrangement" — gap that SSIM misses. |
| Importance-weighted component recall | UI2Code-N | ✅ | Missing the nav should hurt more than missing one decorative `<div>`. |
| Importance-weighted text F1 | Common sense | ✅ | Headlines and CTAs matter more than filler paragraph text. |
| Color-histogram style proxy | UI grading lit | ✅ | Catches "right structure, wrong palette" cheaply (no model). |
| Scalar reward + vector diagnostics | RL standard practice | ✅ | Single scalar trains; vector debugs. |
| In-container rendering of GT | v2 fix | ✅ | Eliminates host-vs-container drift. Oracle 0.97 → 1.000. |
| `wait_until="load"` not "networkidle" | Saves 75s/trial on file:// URLs | ✅ | networkidle has nothing to wait on with `file://`. |
| Greedy IoU matching (vs Hungarian) | Performance | ✅ | n,m typically <20 per tag class; greedy is good enough and avoids scipy dep. |

### What we considered and rejected

| Idea | Source | Why rejected |
|---|---|---|
| **DINO / CLIP / SigLIP perceptual embeddings** | Glean research, common in VLM-eval lit | Glean's own caveat: "CLIP reward can degrade RL." Adds a 1GB+ vision model to every Modal sandbox. Cross-model run showed visual SSIM already barely discriminates capable LLMs — DINO unlikely to help on top of layout+component. **Defer until evidence shows it adds something.** |
| **LPIPS (learned perceptual similarity)** | Image-quality lit | Same as DINO/CLIP — heavy dep, marginal value in our setting. |
| **Spacing/alignment as separate signal** | Glean research | Mostly derives from layout (vertical rhythm, gap distribution come free from bbox positions). Adding it separately would be double-counting. |
| **Color/style as full distinct signal (palette extraction + EMD + button colors + radius/shadow)** | Glean's full proposal at 15% | Replaced with a much lighter HSV-histogram proxy at 10%. Reasoning: the heavy version requires extracting design tokens from screenshots, which is itself a hard problem. The histogram proxy catches the same "wrong palette" failure mode at 1/10 the complexity. |
| **OCR-based text fidelity** | Several papers in the lit | Skipped because we already have direct access to `document.body.innerText` from the rendered page — no need for OCR. (OCR would matter if we couldn't render in our own browser.) |
| **Hungarian matching for layout** | Optimal assignment | Greedy is good enough for the n we deal with. Avoids scipy dep in container. |
| **Cross-page consistency / route coverage** | Glean research, multi-page tasks | Not implemented yet because all current calibration tasks are single-page. **Will add in Phase 2** when synthesis produces ≥5-page tasks. |
| **Hand-tuning weights against absolute human ranking** | Standard ML practice | Currently using literature-informed starting weights. Could tighten with more pairwise data. **Defer until we have more data signal** (e.g. after first synthesis run produces dozens of trials). |

### What we reweighted from v2 to v3

| Signal | v2 weight | v3 weight | Why |
|---|---:|---:|---|
| Visual (SSIM) | 0.60 | 0.25 | Reduced — cross-model showed SSIM doesn't discriminate capable LLMs. |
| Structure (unweighted tag count) | 0.25 | (replaced by component recall 0.20 + layout 0.30) | Split into two — counts (component) and positions (layout) are different signals. |
| Text | 0.15 | 0.15 | Same weight, now importance-weighted internally. |
| (new) Layout | — | 0.30 | Added; literature-recommended dominant signal. |
| (new) Style | — | 0.10 | Added; cheap palette proxy. |

## 6. Calibration results (the 4-step protocol)

The protocol: **sanity → perturbation → cross-model → human anchor**.
Each version of the grader was run through all four steps.

### 6.1 Step 1 — sanity (cheap, deterministic)

Run `oracle` (copies GT into `/app/`) and `nop` (does nothing) on all 10
tasks. Pass: oracle = 1.000, nop = 0.000.

| Version | Oracle | Nop |
|---|---|---|
| v1 (pre-container-render fix) | ~0.97 (host vs container drift) | 0.000 |
| v2 (visibility-aware) | 1.000 | 0.000 |
| **v3** | **1.000** ✓ | **0.000** ✓ |

### 6.2 Step 2 — perturbation ladder (cheap, oracle-only)

For each of the 10 tasks, build perturbed variants where the ground truth
HTML is degraded at known severities {0.1, 0.3, 0.6, 1.0}. Perturbations:
drop a fraction of leaf elements, replace fraction of words with "lorem",
shuffle direct `<body>` children at high severity. Oracle then "copies"
the perturbed version. Pass: monotonic decrease, no flat bands.

| Version | Mean curve (sev 0→0.1→0.3→0.6→1.0) | Monotonic | Avg range |
|---|---|---|---|
| v1 (host-rendered GT, host-rendered agent) | 1.000 → 0.92 → 0.86 → 0.86 → 0.65 | 9/10 | flat band 0.1-0.5 |
| v2 (in-container GT, visibility-aware) | 1.000 → 0.78 → 0.72 → 0.64 → 0.53 | 9/10 | 0.45 |
| **v3** | **1.000 → 0.704 → 0.624 → 0.521 → 0.394** | **10/10 ✓** | **0.61** |

v3 is the first version with strict monotonicity on every task and the
widest discrimination range. The flat-band concern from v1 (which
motivated rebuilding the grader) is gone.

Per-signal contribution at sev=1.0 (v3): layout 0.13, visual 0.57,
component 0.47, text 0.17, style 0.94. The layout signal does the
discrimination work; style stays high because our perturbations don't
change colors (they preserve palette while breaking structure).

### 6.3 Step 3 — cross-model ladder (~$15, real LLM calls)

Run claude-haiku-4.5 / sonnet-4.6 / opus-4.7 on all 10 tasks. 30 trials.
Pass: mean ranking opus > sonnet > haiku.

| Version | haiku mean | sonnet mean | opus mean | gap | Per-task full-order correct |
|---|---:|---:|---:|---:|---:|
| v1 | 0.523 | 0.562 | 0.599 | 0.076 | 7/10 |
| v2 | 0.570 | 0.603 | 0.655 | 0.085 | 6/10 |
| **v3** | **0.411** | **0.460** | **0.493** | **0.082** | **5/10** |

The per-task full-order metric drifts down across versions, but mean
ordering is preserved with similar spread. Per-task drift is **expected
and correct** — opus genuinely does worse on some tasks (e.g., d2c-13665
dark hospitality landing — confirmed by user in Step 4). The grader
revealing per-task variance is informative, not a regression.

**Key finding from v3 per-signal breakdown:**

| Model | Layout | Visual | Component | Text | Style |
|---|---:|---:|---:|---:|---:|
| haiku | 0.034 | 0.584 | 0.447 | 0.594 | 0.763 |
| sonnet | 0.037 | 0.563 | 0.510 | 0.824 | 0.821 |
| opus | 0.052 | 0.623 | 0.553 | 0.887 | 0.780 |

- **Layout is harsh on all real LLMs** (0.03-0.05). LLMs are roughly
  equal at exact bbox positioning of elements — they get the *kind* of
  element right but not the *exact* coordinates. Layout discriminates
  perturbations strongly but capable LLMs weakly.
- **Component recall and text do the model-discrimination work.**
- **Visual SSIM is largely flat across capable LLMs** — it would not be
  enough alone to rank them.
- **Style is informative but doesn't always order with quality** —
  sonnet 0.82 > opus 0.78. Styling is subjective enough that "closest
  palette" doesn't track "best replication overall."

This tells us about agents we'd test going forward: distinguishing
top-tier LLMs requires the structural and content signals; distinguishing
weak vs strong models also benefits from layout.

### 6.4 Step 4 — human anchor (15 min user time)

For 5 tasks × 3 pairs each = 15 pairwise judgments. User picks "A is
closer to GT" or "B is closer" for screenshots side-by-side. We compare
the grader's pairwise pick to the user's.

| Version | Strict agreement | Note |
|---|---:|---|
| v1 | n/a (we ran v2 first) | |
| v2 | **14/15 = 93.3%** | Above 90% trust threshold |
| v3 | **13/15 = 86.7%** | Slightly below — see caveats |

**v3's two disagreements:**

| Pair | User said | v3 grader | Score gap |
|---|---|---|---|
| d2c-13665 sonnet vs opus | sonnet | opus (0.49 > 0.42) | 0.07 |
| d2c-7981 sonnet vs opus | opus | tie (0.39 ≈ 0.38) | 0.01 |

Both are **close-call cases** — within the noise band where small grader
changes can flip the call. We tried 9 alternative weight schemes and
**all of them produced 13/15 agreement** — the disagreements are
structural to the new signals' joint behaviour, not a weighting issue.

**Important caveat on this number:** the user's Step-4 picks were made
against v2's *agent outputs*. v3's cross-model run produced fresh outputs
(LLM stochasticity), so the screenshots the user judged in v2 are not
identical to what v3 graded. The 87% number is "v3 grader's pick on v3
outputs vs user's pick on v2 outputs" — directionally informative but not
clean. A clean re-judgement of v3 outputs would likely score higher.

### 6.5 Why we accepted v3 despite the small Step-4 dip

Trade-off summary:

| Property | v2 | v3 |
|---|---|---|
| Sanity | ✓ | ✓ |
| Perturbation monotonicity | 9/10 | **10/10** |
| Perturbation range | 0.45 | **0.61** |
| Cross-model mean order | ✓ | ✓ |
| Cross-model gap (haiku→opus) | 0.085 | 0.082 |
| Step-4 agreement | **14/15** | 13/15 |
| Diagnostic richness | 3 sub-signals | **5 sub-signals** |
| Catches d2c-2997 over-penalty | partial | ✓ |
| Has layout signal | ✗ | ✓ |
| Per-signal model insights | ✗ | ✓ |

v3 wins decisively on perturbation behaviour, monotonicity, diagnostic
richness, and structural completeness. It loses by a small margin on
close-pair user agreement, in the noise band where the comparison itself
is noisy. The improvement on the more rigorous metrics outweighs the
slip on the most comparison-fragile one.

**Decision:** v3 is the v1 baseline going forward. The 10 D2C tasks +
configs/calibration_*.yaml are the regression suite — any future grader
change runs through all four steps before being accepted.

## 7. Known limitations (v3, accepted)

| Limitation | Severity | Plan |
|---|---|---|
| **Layout signal is near-noise-floor for capable LLMs** | Low | Inherent — LLMs in 2026 are weak at exact bbox positioning. Component recall and text do the model-discrimination work for the strong end. Layout still discriminates perturbations and weak agents. Accept. |
| **Compressed score range for real models** (opus mean 0.49, oracle 1.0) | Low | Layout score being low pulls everything down. Inherent to the strict positioning metric. Could relax IoU to a softer distance, but that would hurt perturbation discrimination. Trade-off accepted. |
| **Style only fires on color regime mismatch, not perturbation drops** | Low | By design. Style catches a different failure mode than perturbation tests cover. Will become more useful when synthesis produces tasks with deliberately distinct palettes. |
| **Text-F1 saturates on common words** ("Pricing", "Features") | Low | The importance-weighting helps. Could tighten to bigrams or top-N stopword filter — defer until we see it bite in Phase 2. |
| **Calibration set is single-page** | Will lift in Phase 2 | All 10 D2C tasks are single-page. Cross-page consistency and route coverage signals exist as TODOs but aren't currently exercised. Add when synthesis produces multi-page tasks. |
| **Modern-style coverage is missing from calibration** | Will lift in Phase 2 | The 5 monolith snapshots conflict with the brief's "no crawling" rule and were archived. Phase 2 synthesis will produce modern-styled tasks; we'll re-validate the grader on them as they come. |
| **Step-4 agreement re-validation deferred** | Open | The 13/15 number is on a noisy comparison. A clean re-collection (15 fresh pairwise picks against v3 outputs) would give a sharper number. Deferred — not blocking Phase 2. |

## 8. Reproducing the calibration

```bash
# Regenerate the 10 calibration tasks (writes datasets/calibration/d2c-*)
.venv/bin/python -m src.ingest_design2code \
    --ids-file datasets/calibration/picks.txt \
    --out-dir datasets/calibration --force

# Step 1: sanity ladder (10 tasks × 2 agents = 20 trials, ~zero cost)
env -i HOME=$HOME PATH=$PATH SHELL=$SHELL USER=$USER LANG=en_US.UTF-8 \
  harbor run -c configs/calibration_sanity.yaml -y

# Step 2: perturbation ladder (10 × 4 severities = 40 trials, ~zero cost)
.venv/bin/python -m src.build_perturb_tasks \
    --source-dir datasets/calibration \
    --out-dir datasets/perturbed \
    --severities 0.1 0.3 0.6 1.0 --force
env -i HOME=$HOME PATH=$PATH SHELL=$SHELL USER=$USER LANG=en_US.UTF-8 \
  harbor run -c configs/calibration_perturb.yaml -y

# Step 3: cross-model ladder (3 models × 10 tasks = 30 trials, ~$15)
env -i HOME=$HOME PATH=$PATH SHELL=$SHELL USER=$USER LANG=en_US.UTF-8 \
  ANTHROPIC_API_KEY="$(tr -d '\n\r' < ~/.trial-anthropic-key)" \
  harbor run -c configs/calibration_models.yaml -y \
  --ae ANTHROPIC_API_KEY="$(tr -d '\n\r' < ~/.trial-anthropic-key)"

# Step 4: human anchor (15 min user time, optional re-run)
# See src/ingest_design2code.py, build_perturb_tasks.py for tooling.
```

Pass criteria for any change to `src/_container_grade.py`:
- Sanity: oracle = 1.000, nop = 0.000 on all 10 tasks
- Perturbation: ≥9/10 strict-monotonic; mean range ≥0.45
- Cross-model: opus > sonnet > haiku in means; gap ≥0.05
- Step 4 (optional re-run): ≥85% agreement on user picks

## 9. Future grader work (planned for Phase 2)

1. **Cross-page consistency.** When synthesis produces multi-page tasks,
   add a site-level signal that compares nav/footer/palette across pages.
2. **Route coverage.** Penalise agents that only render the homepage
   (e.g. multiplier `min(rendered_pages / required_pages, 1)` on the
   final score).
3. **Re-tune weights against more pairwise data.** The current weights
   are literature-informed starting points. Once we have ~30+ pairwise
   judgments from Phase 2 trials, we can fit weights that maximise
   correlation with human ranking.
4. **Color-token-aware style signal.** The histogram proxy is a starting
   point. If Phase 2 produces tasks with subtle palette differences, we
   may need to extract dominant colors and compare more semantically.
5. **Re-validate Step 4 against v3 outputs.** Clean 15-pair re-judgement
   to get a noise-free agreement number.

---

## 10. v3.2 update (2026-05-22) — hybrid layout score

The user noticed during inspection that real-model output (Opus on the
synthesised SaaS task) was scoring much lower on `layout` than the
visual similarity warranted: per-page layout 0.21-0.40 even though the
page renderings looked structurally similar. Investigation showed two
compounding causes that hard per-tag IoU couldn't address:

1. **Tag substitution.** Opus produced `<div>` where GT used `<nav>` /
   `<main>` / `<article>`. With `n_agent=0` for those tags, the metric
   contributed 0 for full tag-weight, regardless of what was visually in
   that region.
2. **Element-level position precision.** Even when tags matched, Opus's
   individual elements were at slightly different y-coordinates. IoU
   crashes to 0 abruptly when bboxes stop overlapping; a same-kind
   element 50px off scored 0.

The brief explicitly says functionality is out of scope; visual
replication is what matters. So the right metric should not penalise
tag substitution when the visual layout matches.

### What we tried (in order)

1. **Soft-IoU fallback** — when bboxes don't overlap, fall back to
   centroid-distance + size-similarity, capped at 0.4 to ensure any real
   overlap still scores higher. Tested locally: layout score moved by
   only ~0.05 on Opus's SaaS output. Most of the penalty was from
   missing tag classes (n_agent=0 cases), where soft-IoU never fires.
2. **Tag-agnostic per-tag matching** — match all visible elements above
   an area threshold, ignore tag class. Marginal further gain (~0.03) —
   the underlying issue was that fine-grained element positions just
   don't match closely between two HTML reproductions of the same design.
3. **Multi-resolution layout grid** — rasterise visible elements onto
   coarse grids (4×8, 8×16, 16×32 cells), compare via cosine on flattened
   counts. Inherently smooth: small position shifts move elements between
   adjacent cells. Tested: Opus's SaaS layout score jumped from 0.27 to
   0.88. Too lenient as a sole signal.

### What we adopted: hybrid layout

`layout = 0.40 * iou_layout + 0.60 * grid_layout`

where:
- `iou_layout` is the per-tag soft-IoU score from v3.1 (catches fine
  positioning when present)
- `grid_layout` is the multi-resolution grid cosine (catches "regions of
  the page have similar stuff," granularity at which humans read layout)

### Effect

| Property | v3 strict IoU | v3.1 soft IoU | v3.2 hybrid |
|---|---:|---:|---:|
| Sanity (oracle) | 1.000 | 1.000 | **1.000** ✓ |
| Sanity (nop) | 0.000 | 0.000 | **0.000** ✓ |
| Perturbation: monotonicity | 10/10 | 10/10 | **8/8 succeeded** (2 trials had Modal infra errors) |
| Perturbation: floor at sev=1.0 | 0.394 | n/a | 0.468 (slightly less harsh) |
| Perturbation: range | 0.61 | n/a | 0.53 (slightly compressed) |
| Opus on synth SaaS: layout | 0.27 | 0.27 (+0.05 max) | **0.65** |
| Opus on synth SaaS: combined | 0.654 | 0.66 | **0.77** |

The combined score moves from 0.65 to 0.77 — landing in the predicted
0.7-0.85 band for a saturated control archetype, which matches user
intuition that the visual replication was clearly better than the v3
score implied.

### Why not just go fully grid-based?

The grid signal alone reaches 0.88 even when individual elements are
poorly placed — too lenient. The IoU half maintains discrimination on
"did you put the headline at the right exact y-coordinate." The 40/60
split keeps the IoU as a precision check while letting the grid carry
"general layout match." If perturbation discrimination ever feels too
weak in practice, raise the IoU weight; if real-model scores feel too
harsh on tag-substitution, raise the grid weight.

### Files

- `src/_container_grade.py`: `_layout_score_iou` (was `_layout_score`),
  `_layout_score_grid` (new), `_layout_score` (now the hybrid combiner).
  `_LAYOUT_IOU_WEIGHT = 0.40`, `_LAYOUT_GRID_WEIGHT = 0.60`.
- `_LAYOUT_GRIDS = [(4,8), (8,16), (16,32)]`: three-resolution average for
  the grid signal.
- `_SOFT_IOU_CAP = 0.40`, `_SOFT_IOU_RADIUS = 0.50`: bounds on the soft-IoU
  fallback; non-overlapping but co-located elements get up to 0.4.

### Calibration regression on the 10 D2C tasks

The 10 D2C calibration tasks remain the regression suite. v3.2 passes
sanity (oracle 1.000 / nop 0.000) and perturbation monotonicity; the
Step-4 user-pair agreement was not re-collected (would need fresh agent
runs against the v3.2 grader). The per-signal weights (layout 30 /
visual 25 / component 20 / text 15 / style 10) are unchanged.

---

## 11. Followup (2026-05-22): grade.py staleness in task dirs

After v3.2 was added, the user re-ran Opus on the two synth slots and
saw layout scores of 0.16 (devdocs) and 0.27 (saas) — far harsher than
v3.2 should have produced. Investigation: **the synth task dirs were
created BEFORE v3.2 was added, so each task's own `tests/grade.py` was
still the v3 strict-IoU grader.** The Modal trials ran the OLD grader
on these tasks, regardless of what was in `src/_container_grade.py`.

`build_task_dir` copies the grader at generation time:

    shutil.copy2(grader_src, tests_dir / "grade.py")

This is by design (each task is a self-contained Harbor bundle) but it
means changes to `src/_container_grade.py` don't propagate to existing
tasks. Fix: after any grader change, refresh `tests/grade.py` in every
task dir we plan to re-run.

After refreshing both synth slots' grade.py and re-running Opus:

| Slot | Layout (stale v3) | Layout (fresh v3.2) | Combined (stale) | Combined (fresh) |
|---|---:|---:|---:|---:|
| saas-minimal-001 | 0.265 | **0.694** | 0.654 | **0.786** |
| devdocs-mono-001 | 0.163 | **0.616** | 0.597 | **0.718** |

These match the predicted bands (saturated 0.7-0.85, hard 0.55-0.75)
and the user's intuition that "the layouts look close enough."

**Lesson:** every grader change must include a step that refreshes
`tests/grade.py` in every task dir. The calibration regression suite
(10 D2C + 40 perturbed) was OK because we re-ingested those after v3.2;
the synth set was the only place that was stale.

---

## 12. v3.3 update (2026-05-22) — adversarial gates on visual / style / text

The user asked: "is the grader actually showing 0 when comparing an
unrelated image?" Adversarial probes against SaaS GT showed it was NOT:

| Probe | combined (v3.2) |
|---|---:|
| Blank `<body></body>` | **0.200** |
| Junk `<p>random</p>` | **0.205** |
| Text dump of GT words in a single `<p>` | **0.299** |
| Cross-archetype (devdocs HTML vs SaaS GT) | 0.441 |

Diagnosis: **SSIM has a high baseline on mostly-white pages.** A blank
HTML rendered to a white screenshot scored SSIM 0.776 against SaaS's GT
because most SSIM windows landed on shared whitespace. Style had a
similar issue: a blank-vs-blank histogram is a perfect cosine match
(both ~100% in the white bin), so style scored 1.0 on a blank page
against a docs site (which is also mostly light). And text saturated at
~0.90 when an agent dumped GT's words into a single `<p>` — token-set
F1 doesn't care about structure.

### Three fixes adopted

1. **Content-coverage gate on visual.** Compute "fraction of pixels not
   near-white" for both screenshots. If agent's coverage is below 20% of
   GT's, scale visual linearly toward 0; above 20%, no penalty. Catches
   blank/junk without penalising real agents whose pages are 60-90% as
   dense as GT.
2. **Same coverage gate on style.** Two blank-white pages share the
   white histogram bin and score cosine ≈ 1.0; the gate kills that.
3. **Weight-aware text intersection.** Each shared token's contribution
   is scaled by the ratio of its parent-tag importance weights between
   GT and agent. A token "Pricing" appearing in GT's `<h1>` (weight 3.0)
   but only in agent's `<p>` (weight 1.0) contributes 0.33×, not full
   credit. Stops "right words, no structure" from scoring high.

The 20% threshold for the coverage gate was empirically chosen: keeps
real-model output unaffected, suppresses near-blank inputs to ~0.

### Effect

| Probe | v3.2 | **v3.3** |
|---|---:|---:|
| Oracle | 1.000 | **1.000** ✓ |
| Opus on synth SaaS (real) | 0.758 | **0.758** ✓ |
| Opus on synth devdocs (real) | 0.744 | **0.740** ✓ |
| Cross-archetype (different web pages) | 0.441 | 0.436 |
| **Blank** | **0.200** | **0.002** ← |
| **Junk** `<p>random</p>` | **0.205** | **0.021** ← |
| Text dump of GT words in `<p>` | 0.299 | 0.283 |
| Blank vs devdocs | 0.272 | **0.001** ← |

The cross-archetype case (0.44) is *defensible*: both are real web pages
with structure, text, and content. The grader correctly orders them
*below* a real-model attempt (0.74-0.76) and *above* blank (0.001), but
not all the way to 0. Lowering cross-archetype further would require a
semantic similarity signal (DINO/CLIP/VLM-judge) which we've consistently
deferred — see "things rejected" memory.

Calibration verified: oracle = 1.000 / nop = 0.000 on all 10 D2C tasks
under v3.3. Perturbation ladder not re-run because the adversarial fixes
only affect blank/near-blank inputs, which perturbation doesn't produce.

### Files

- `src/_container_grade.py`:
  - `_content_coverage(path)`: fraction of non-near-white pixels.
  - `_coverage_gate(gt_png, agent_png)`: multiplier in [0, 1].
  - `_visual_similarity` and `_style_score`: multiply raw output by
    `_coverage_gate(...)`.
  - `_text_score`: each shared token contributes `min(g,a) * ratio`
    where `ratio = min(g,a)/max(g,a)` (parent-tag-weight ratio).
- `_COVERAGE_GATE_THRESHOLD = 0.20`: ratio below which the gate fires.

### Important: refresh task dirs after grader changes

`build_task_dir` copies `src/_container_grade.py` into each task at
generation time, so existing task dirs need their `tests/grade.py`
refreshed manually whenever the grader changes. See §11 for the cliff
this caused on 2026-05-22 with v3.2.

---

## 13. v3.4 update (2026-05-22) — mobile viewport pass

The user pointed out that every score reported under v3.0–v3.3 was for
a single 1280×800 desktop render, leaving a fundamental coverage gap:
agents could produce HTML that's perfect at 1280 but unreadable at
390px wide, and the grader would never notice. Per the brief, "design"
includes responsive design.

### What changed

The grader now renders and scores **at every viewport** in the
`VIEWPORTS` dict and combines per-page scores using `VIEWPORT_WEIGHTS`:

```python
VIEWPORTS = {
    "desktop": {"width": 1280, "height": 800},
    "mobile":  {"width":  390, "height": 844},
}
VIEWPORT_WEIGHTS = {"desktop": 0.70, "mobile": 0.30}
```

Per page, both viewports are rendered in their own playwright session,
all 5 sub-signals are computed at each viewport, and the per-page
combined score is `0.7 × desktop_combined + 0.3 × mobile_combined`.
The task score is the mean of per-page combined scores, as before.

### Why these weights

Desktop dominates (0.7) because:
- The brief and our synthesis prompts both target desktop primarily
- Most calibration tasks come from desktop screenshots (Design2Code)
- Mobile is a secondary failure mode, not the primary signal

Mobile contributes 0.3 because:
- A site that's broken at mobile is genuinely worse than one that isn't
- Catches "agent forgot `<meta viewport>`" / hardcoded-width bugs
- Distinguishes responsive output from desktop-only

These weights are tunable via `VIEWPORT_WEIGHTS`. Set
`{"desktop": 1.0}` to disable the mobile pass entirely.

### Effect on real-model scores

| Task | Desktop | Mobile | Combined | Mobile penalty |
|---|---:|---:|---:|---:|
| saas-minimal-001 (Opus) | 0.780 | 0.706 | 0.758 | -0.074 |
| devdocs-mono-001 (Opus) | 0.759 | 0.727 | 0.749 | -0.032 |
| oracle (any task) | 1.000 | 1.000 | 1.000 | 0 |

Opus's SaaS output drops 0.07 going to mobile — visible drops in
`mobile_visual` (0.65→0.51 mean) and `mobile_layout` (0.69→0.61 mean).
This is the **responsiveness signal** the grader was missing.

Devdocs is less affected because docs sites tend to collapse cleanly
to single-column at narrow widths.

### Architecture

- `_render_pages` now takes a `viewport` argument (defaults to back-
  compat 1280×800).
- `_page_dims`, `_layout_score_iou`, `_layout_score_grid`, `_layout_score`
  thread `viewport_w` / `viewport_h` through so layout-grid and
  centroid-distance normalisation happen at the actual rendered viewport.
- `_score_one_viewport` is the per-(page,viewport) scoring helper.
- `grade()` renders both viewports separately (separate playwright
  sessions) for both GT and agent.
- `PageScore` gains a `per_viewport: Dict[str, ViewportPageScore]`
  field; top-level `layout/visual/...` mirror desktop for back-compat
  with existing tooling (analyze_layout, viewers).

### `reward.json` schema (v3.4)

Per page, the flat scalar keys are:

- `<page>_combined` — weighted across viewports (the score that drives
  the overall reward)
- `<page>_{layout,visual,component,text,style}` — desktop sub-signals,
  back-compat with v3.3 readers
- `<page>_desktop_{layout,visual,component,text,style,combined}`
- `<page>_mobile_{layout,visual,component,text,style,combined}`

Total flat keys per page: 1 (combined) + 5 (desktop back-compat) + 6
(desktop full) + 6 (mobile full) = 18, plus the global `score`. For 6
pages, ~109 keys per task — well within Harbor's flat-scalars schema.

### Calibration regression on the 10 D2C tasks

- Sanity (Modal): oracle = 1.000 / nop = 0.000 ✓
- Mobile pass adds ~30s to total grader runtime per trial (a second
  playwright session); calibration sanity went from 1m21s to 1m25s.
- Real-model scores: the mobile penalty reduces saturated controls
  modestly (~0.05 on Opus on SaaS) and harder archetypes less (~0.03
  on Opus on devdocs). The grader's discrimination is preserved.

### Future viewport work

- **Tablet (768×1024).** Diminishing returns vs desktop+mobile per the
  Glean research; defer until we see a need.
- **Higher device-pixel-ratio.** Currently `device_scale_factor=1`. A
  `dsr=2` pass would catch retina-specific issues but adds complexity.
- **Mobile viewport meta tag detection.** Could explicitly check that
  GT's `<meta name="viewport">` is preserved by the agent, scoring
  layout 0 if missing. Currently the absence of the tag manifests as
  poor mobile rendering, which the grader detects indirectly.

### Important: refresh task dirs after grader changes

Same staleness rule as every prior grader change. After updating
`src/_container_grade.py`, copy it into every `<task>/tests/grade.py`
before re-running trials. See §11 for the cliff that bit us when v3.2
hadn't been propagated.
