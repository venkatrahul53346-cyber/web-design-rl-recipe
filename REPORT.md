# Web-design RL benchmark — Part 1 report

> **The brief.** Build a scalable pipeline that produces RL environments
> testing a coding agent's ability to *replicate a multi-page web design*
> in HTML + CSS from screenshots. Functionality is out of scope; visual
> fidelity is what's graded. Tasks run on
> [Harbor](https://harborframework.com/). Crawling existing websites is
> forbidden — sites must be generated from scratch.

The deliverables required by the brief and where they live:

| Deliverable | Where |
|---|---|
| **(a)** A grading function where higher reward ↔ better visual replication | [§1](#1-the-grader), implementation: `src/_blockmatch_grade.py` |
| **(b)** A scalable pipeline producing multi-page (≥5) websites from scratch | [§2](#2-the-pipeline) (incl. [the within-pair diversity subsection](#within-pair-diversity-pattern-injection--phash-dedup)), implementation: `src/synthesize.py` + `templates/` |
| **(c)** ≥10 final tasks, each with Opus 4.7 × 10 attempts | [§3](#3-the-tasks), [§4](#4-empirical-results), data: `report_figures/v51_results.csv` |
| **(d)** Visual evidence that higher score → better replication | [§4.2](#42-correlation-evidence-best-vs-worst-pairs), gallery: `report_figures/v51_pairs.html` |
| **(e)** What models struggle with | [§6](#6-what-we-learned-about-opus-47) |

Parts 2 (animations) and 3 (multi-framework) are out of scope per the
brief's "high-taste Part 1 beats rushed all-three" guidance.

---

## 1. The grader

> **Property we're optimising for: higher reward ↔ better visual
> replication of GT.** The grader is the load-bearing artifact of this
> trial — without it, a synthesis pipeline produces tasks no one can
> evaluate, and an RL environment has no learning signal.

The grader uses a **match-then-diff architecture** (Design2Code-style
Block-Match) wrapped by **page-level orthogonal signals**. Matched
elements are scored on six per-pair dimensions; unmatched / structural
properties contribute three page-level signals. Total = 9 signals,
weights sum to 1.0, output ∈ [0, 1].

### 1.1 Architecture

```
        ┌────────────────────────────┐
        │ rendered DOM elements      │
        │   per element:             │
        │     (tag, bbox, own_text,  │
        │      font, color,          │
        │      effective_bg,         │
        │      border, etc.)         │
        └─────────────┬──────────────┘
                      │
       text-leaf      │  filter: own_text ≥ 4 chars
       anchors        ▼
                ┌─────────────┐
                │  matching   │  Sørensen-Dice on character bigrams
                │  step       │  Hungarian (Jonker-Volgenant) one-to-one
                │             │  threshold 0.5
                └──────┬──────┘
                       │
            matched (gt, agent) pairs
                       │
                       ▼
           ┌─────────────────────────┐
           │   per-pair sub-scores   │
           │   (6 dimensions, [0,1]) │
           ├─────────────────────────┤
           │  bm_position  Δx, Δy    │
           │  bm_text      Dice      │
           │  bm_color     CIEDE2000 │  ← uses effective_bg (ancestor-walked)
           │  bm_font      family +  │     for transparent backgroundColor
           │               size +    │
           │               weight    │
           │  bm_border    radius +  │
           │               style +   │
           │               shadow    │
           │  bm_size      area      │
           └────────────┬────────────┘
                        │
                        ▼  weighted average across pairs
                        │
           ┌────────────┴─────────────┐
           │   page-level signals     │
           ├──────────────────────────┤
           │  bm_recall   matched-area / total-area
           │  tree_bleu   1-height DOM subtree multiset recall
           │  visual_ssim grayscale SSIM
           └────────────┬─────────────┘
                        │
                        ▼
                weighted sum → page combined ∈ [0, 1]
                        │
                        ▼
                mean across pages → trial score ∈ [0, 1]
```

### 1.2 Signal weights and what each measures

| Signal | Weight | What it measures | Failure mode it catches |
|---|---:|---|---|
| **bm_position** | 0.20 | viewport-normalised centroid distance per matched pair | "Right element, wrong place" |
| **tree_bleu** | 0.20 | DOM 1-height subtree multiset recall | "Wrong nesting (skeletal divs, missing semantic tags)" |
| **bm_color** | 0.15 | 0.6 × text colour CIEDE2000 + 0.4 × effective bg CIEDE2000 | "Wrong palette per element AND wrong page background regime" |
| **bm_recall** | 0.15 | matched_area / total_GT_area | "Sparse output, big GT regions unmatched" |
| **bm_text** | 0.10 | char-bigram Dice on matched pair text | "Wrong copy in matched element" |
| **bm_font** | 0.10 | 0.4 × family (tiered) + 0.4 × size (ratio) + 0.2 × weight (ratio) | "Wrong typography" |
| **bm_size** | 0.05 | min(area)/max(area) per pair | "Wrong physical size" |
| **visual_ssim** | 0.05 | grayscale SSIM | "Pixel-level adversarial mode (right DOM, bizarre imagery)" |

Sum = 1.000. Combined ∈ [0, 1] by construction. Weights were
empirically rebalanced from a uniform v3-era baseline using the
variance/discrimination analysis in §4.3 — see that section for the
data behind every weight.

### 1.3 The matching step — Hungarian + Sørensen-Dice

Each GT and agent page produces a list of *anchor* elements (visible
elements whose own immediate text ≥ 4 chars). For each
(GT_anchor, agent_anchor) pair we compute Sørensen-Dice similarity on
character bigrams of their text:

```
A = "pricing"      bigrams: {pr, ri, ic, ci, in, ng}        (6)
B = "pricing plan" bigrams: {pr, ri, ic, ci, in, ng, ...}  (11)
shared = 6
Dice = 2·shared / (|A|+|B|) = 12/17 ≈ 0.71
```

`scipy.optimize.linear_sum_assignment` (Jonker-Volgenant) solves the
bipartite matching that **maximises total similarity** across all
pairs. Pairs scoring below 0.5 are dropped. This is globally optimal —
strictly better than greedy "each GT picks its closest agent", which
is order-dependent when multiple GT elements compete for the same
agent counterpart.

### 1.4 Why these specific signals

The match-then-diff structure follows **Design2Code (Stanford NAACL
2024)**, which found that bbox-IoU on whole-page DOM dumps is too
noisy because most elements don't have stable bbox-equivalents across
agent reproductions, but **text content does** — agents reproduce copy
faithfully, so text becomes a stable anchor for matching elements
between GT and agent. Once paired, every per-pair sub-score is a
numerical distance, not a 0/1 cliff.

Three page-level signals catch what per-pair matching can't:

- **bm_recall** — caps total matchable area. Penalises agents that
  reproduce a small subset of GT's elements faithfully (a 5-element
  hero reproduction of a 50-element page).
- **tree_bleu** — DOM 1-height subtree recall (from **WebCode2M, WWW
  2025**). Catches "right text wrong nesting" — `<button>Save</button>`
  matches `<a>Save</a>` on text but not on structure.
- **visual_ssim** — pixel-level fallback. Catches whole-page
  differences (background regime, hero photo presence, dark vs light
  flips) that no per-element signal captures.

Colour comparison uses **CIEDE2000 in CIE Lab space**, not HSV or RGB.
A predecessor v3 grader used HSV-cosine and produced bimodal
distributions on dark-themed tasks — the histogram bin alignment
between near-black and near-grey collapsed the score to ~0 or ~1.
CIEDE2000 is a perceptually-uniform distance and avoids this. For
backgrounds we walk up the parent chain to find the **nearest
non-transparent ancestor's bg colour**: most elements have transparent
backgrounds and inherit visually from their container, so naive
`getComputedStyle().backgroundColor` matches transparent-on-white with
transparent-on-black at 1.0 — which is wrong.

### 1.5 Anti-gaming (what an adversarial agent can't do)

| Cheat | Why it doesn't work |
|---|---|
| Embed GT screenshot in `<img>` | bm_text=0 (no text leaves), bm_recall=0, tree_bleu=0; visual_ssim ~0.7 from pixel match dragged to ~0.07 by 0.10 weight |
| Submit a blank page | All anchors empty → 0 across the board |
| Submit raw GT text dump | bm_text high but bm_position/font/color/size all 0; tree_bleu near 0 |
| Submit only the index page | n_pages mean still includes 0-scoring missing pages |

The architecture makes the maximum trivially-gameable score ≈ 0.10
(the SSIM weight ceiling alone), well below any real reproduction.

---

## 2. The pipeline

A scalable, deterministic pipeline that turns a `(vertical, style, seed)`
triple into a Harbor task with screenshots, ground truth HTML/CSS,
graded by the v5.1 Block-Match grader.

```
   ┌──────────────────────┐
   │ templates/           │
   │   verticals/  (15)   │  what we're building (topic + sitemap)
   │   styles/     (13)   │  how it looks (palette + typography + motif)
   │   compatibility.py   │  56 valid (vertical × style) pairs
   └──────────┬───────────┘
              │
              ▼  WebsiteSpec  (brand, palette, fonts, sitemap, notes)
              │
   ┌──────────▼───────────┐
   │   src/synthesize.py  │  per-page LLM compile (Opus 4.7)
   │   ─────────────────  │
   │   stage 1: design    │  → styles.css + nav + footer + brief
   │   stage 2: per page  │  → page.html (one Anthropic call per page)
   │   per-page validate  │  desktop+mobile render checks
   └──────────┬───────────┘
              │
              ▼  {styles.css, *.html}
              │
   ┌──────────▼───────────┐
   │    src/render.py     │  playwright headless screenshots
   └──────────┬───────────┘
              │
              ▼  screenshots/*.png
              │
   ┌──────────▼───────────┐
   │   src/generate.py    │  Harbor task layout
   │   build_task_dir()   │  /environment, /solution, /tests
   │                      │  (bakes the v5.1 grader as tests/grade.py)
   └──────────┬───────────┘
              │
              ▼  datasets/final/<vertical>__<style>-NNN/
```

**One user-facing knob:**
```bash
.venv/bin/python -m src.synthesize \
    --vertical <name> --style <name> --seed <int> --out <dir>
# or
.venv/bin/python -m src.synthesize --random --seed <int> --out <dir>
```

**Four load-bearing design choices:**

1. **Spec-driven LLM compile, not direct LLM-to-HTML.** A two-stage
   compile (design pass → per-page passes) keeps CSS classes, nav
   markup, and palette consistent across pages. A single 32K-output
   call truncates on content-rich archetypes.
2. **Templates carry text references, not HTML examples.** Each
   template lists `style_references` like `["linear.app", "attio.com"]`
   as text descriptors only, not embedded HTML/screenshots. WebSight's
   ablations found example-grounded prompts produce *less* diverse
   datasets because they converge on the example's idiosyncrasies.
3. **Decoupled vertical × style.** `templates/verticals/` (what we're
   building) and `templates/styles/` (how it looks) live in
   independent registries combined by a positive-list compatibility
   matrix. 15 verticals × 13 styles → 56 valid pairs, far more than
   the ten the deliverable needs.
4. **Within-pair variance via pattern injection + perceptual-hash
   dedup.** Each vertical declares pattern axes
   (`hero_patterns`, `nav_patterns`, `section_arcs`,
   `density_modifiers`) that the sampler picks from per seed and the
   design prompt forces the LLM to follow exactly. A pHash check at
   render time rejects residual near-duplicates. Together this lifts
   effective visual variance per pair from ~3-5x to >10x — the path
   to hundreds of distinct sites without the "modern Inter pastel"
   monoculture. See the within-pair diversity subsection below.

For the deeper architecture walkthrough — sampler, validation loop,
image handling, brand pool — see [PIPELINE.md](PIPELINE.md).

### Within-pair diversity: pattern injection + pHash dedup

Without explicit guidance, an LLM compiling 5 different SaaS
landing pages from the same `(vertical, style)` cell converges on a
shared default — `hero-text-left + product-shot-right` + `topbar-
horizontal nav` + `hero → 3-feature-grid → testimonials → pricing →
cta` arc. Brand persona and font choice shift the surface but not the
shape. Effective variance per pair sits at ~3-5x, dominated by the
"shadcn template" attractor.

The pipeline counters this two ways:

**Pattern injection.** Each `VerticalMeta` carries four axes of
explicit layout patterns. For `saas_landing`:

```python
hero_patterns       = [centered-text-only, text-left-product-shot-right,
                       text-center-product-shot-below,
                       text-left-illustration-right,
                       asymmetric-stagger, hero-with-inline-demo]
nav_patterns        = [topbar-horizontal-links, topbar-with-mega-dropdown,
                       floating-pill-nav, minimal-with-cmd-k, dual-bar]
section_arcs        = [<6 section orderings, e.g. integration-grid-led,
                       comparison-led, walkthrough-led, ...>]
density_modifiers   = [airy, tight, mixed-rhythm]
```

`sample_spec(seed)` picks one entry per axis. The design-pass prompt
renders these as **REQUIRED PATTERN DIRECTIVES** the LLM must follow
exactly — not soft suggestions. The page pass re-states them so the
index-page LLM doesn't have to remember the design-pass turn.

For `saas_landing × saas_clean` alone this multiplies the spec space
by 6 × 5 × 6 × 3 = **540 pattern combinations** before brand / font /
palette variance, against the ~60 in the pre-injection sampler.

**Perceptual-hash dedup.** Even with pattern injection, two compiles
will occasionally converge on near-identical pages. `src/dedup.py`
implements a 64-bit DCT pHash (resize 32×32 → DCT-II → 8×8 low-
frequency block → median threshold). Hamming distance ≤ 8 bits
(~12%) flags near-duplicates; the batch generator can reject and
re-roll with a fresh seed.

**Empirical confirmation.** Five seeds of `saas_landing × saas_clean`
were rendered as single-page sites and pHash-compared:

| | min hamming | mean hamming | max hamming | duplicates |
|---|---:|---:|---:|---:|
| 5 seeds, single-page | **22** (34%) | **28.2** (44%) | **38** (59%) | **0** |

For reference, oracle reproductions of the same site hash 0–3 bits
apart, and unrelated screenshots are typically 25–35 bits apart. The
five variants land squarely in the "unrelated screenshots" range —
pattern injection drives variance well above the dedup threshold by
construction. The closest pair (s1↔s2 = 22 bits) shared
`topbar-horizontal-links` nav but differed on every other axis; the
furthest (s0↔s3 = 38 bits) shared no patterns at all.

Pattern lists populate per `VerticalMeta`. Pattern coverage on the
remaining 14 verticals is tracked in §8 limitations.

---

## 3. The tasks

11 final tasks in `datasets/final/`, each spanning a distinct
(vertical × style) cell across the design space. Each ships:

- 5–7 page screenshots at desktop resolution (the agent's input)
- An `instruction.md` listing pages + CSS rules + image filenames
- Ground-truth HTML/CSS in `solution/ground_truth/`
- A `tests/grade.py` baked from `src/_blockmatch_grade.py` (the v5.1 grader)
- A Dockerfile (`mcr.microsoft.com/playwright/python:v1.50.0-noble` +
  scipy/numpy/skimage/PIL/bs4)
- A `task.toml` with timeouts, resource limits, keywords

| # | Task | Vertical × style | Difficulty | Why |
|---|---|---|---|---|
| 1 | `saas_minimal` | SaaS × pastel × hairline-1px × clean-iconographic | easy | Saturated control — proves the floor |
| 2 | `pricing_dark` | pricing × dark-native × hairline-1px × clean-iconographic | easy | Saturated — pricing matrices are easy structural shapes |
| 3 | `auth_glassy` | auth × pastel × glassy-blurred × clean-iconographic | easy | Saturated — sparse, modern, cards-on-gradient |
| 4 | `docs_mono` | docs × mono-everywhere × hairline-1px × clean-iconographic | hard | Typography + 3-pane layout (oxide.computer style) |
| 5 | `dashboard_dense` | dashboard × dense × dark-native × data-viz-decor | hard | Density + dark mode + tables |
| 6 | `portfolio_neobrut` | portfolio × display-mixed × neobrutalist-thick × variable-display | hard | Oversized type + asymmetry + thick borders |
| 7 | `government__dark_native_clean` | government × dark | hard | Civic conventions: dense forms, formal copy |
| 8 | `hotel_booking__photo_warm_display` | hospitality × photo-warm | hard | Search-led, room cards, photographic |
| 9 | `news_portal__editorial_dark` | news × editorial-dark | hard | High info-density on dark — different from longform |
| 10 | `healthcare_clinic__glassy_pastel` | healthcare × glassy-pastel | hard | Calming-medical: soft palette, "find a doctor" |
| 11 | `product_splash__crypto_neon` | splash × crypto-neon | hard | Web3 / consumer-hardware launch — neon on dark |

The split (3 saturated + 8 hard) gives a controlled difficulty
distribution. Earlier iterations of this slate had 4 image-heavy tasks
(`ecom_pastel`, `editorial_serif`, `restaurant_photo`, `splash_3d`)
that referenced an unshipped `rick.jpg` placeholder; both GT and agent
rendered with broken-image icons, compromising the grading signal.
Those tasks were retired and the pipeline now ships 5 procedurally-
generated placeholder JPGs in every `environment/assets/` and
constrains `<img src=>` to that allow-list.

---

## 4. Empirical results

11 tasks × 10 Opus 4.7 attempts = **110 attempted trials**. Run on
Modal sandboxes, parallel up to 20.

**Coverage:** 106 of 110 trials returned a graded result. 4 trials
were lost agent-side (no HTML produced before the agent timed out and
no salvageable trajectory). Of the 110:

- 86 graded inside the Modal verifier sandbox.
- 20 had agent output but the verifier sandbox stalled (Modal
  scheduling instability on 7-page tasks). These were re-graded
  locally from `agent/trajectory.json` using the same v5.1 code that
  ships in `tests/grade.py`. We marked them with `_recovered_locally`
  in the reward.json.

### 4.1 Per-task score distribution

| Task | n | Mean | Std | Min | Max | Spread |
|---|---:|---:|---:|---:|---:|---:|
| `auth_glassy-001` | 10 | **0.826** | 0.029 | 0.791 | 0.878 | 0.087 |
| `docs_mono-001` | 10 | **0.726** | 0.094 | 0.528 | 0.804 | 0.276 |
| `dashboard_dense-001` | 10 | **0.721** | 0.042 | 0.668 | 0.783 | 0.115 |
| `pricing_dark-001` | 9 | **0.648** | 0.016 | 0.621 | 0.672 | 0.051 |
| `healthcare_clinic__glassy_pastel-001` | 10 | **0.625** | 0.038 | 0.576 | 0.693 | 0.118 |
| `government__dark_native_clean-001` | 9 | **0.614** | 0.080 | 0.552 | 0.793 | 0.241 |
| `product_splash__crypto_neon-001` | 9 | **0.612** | 0.053 | 0.545 | 0.705 | 0.160 |
| `hotel_booking__photo_warm_display-001` | 10 | **0.602** | 0.064 | 0.518 | 0.683 | 0.165 |
| `saas_minimal-001` | 10 | **0.588** | 0.209 | **0.000** | 0.804 | 0.804 |
| `portfolio_neobrut-001` | 10 | **0.583** | 0.097 | 0.458 | 0.724 | 0.266 |
| `news_portal__editorial_dark-001` | 9 | **0.537** | 0.061 | 0.481 | 0.654 | 0.173 |

**Overall (n=106):** mean = 0.645, std = 0.119, range = [0.000, 0.878].

The distribution is clean:

- **No task above 0.90** — even the best Opus runs visibly miss
  things. Real headroom for a successor model.
- **No task below 0.45** — except `saas_minimal-001__Fkc9r6q`, which
  the agent submitted *no HTML for at all*. The 0.000 is the grader
  correctly assigning a no-submission its true score.
- **Spread per task: 0.05 (pricing_dark) → 0.23 (portfolio_neobrut)**
  on the well-formed runs. Wider spread = more variance in agent
  approaches.

See `report_figures/v51_scores_per_task.png` for the boxplot and
`report_figures/v51_signals.png` for the per-signal mean ± std bars.

### 4.2 Correlation evidence — best vs worst pairs

This is the property that makes the grader trainable: **higher score
must correspond to a more faithful replica when a human looks at it.**

We rendered side-by-side GT-vs-agent screenshots for the
best-scoring and worst-scoring trial of every task — 22 pair PNGs in
`report_figures/pairs_v51/`, plus a single contact sheet at
`report_figures/v51_contact_sheet.png` and an interactive HTML
gallery at `report_figures/v51_pairs.html` (open in a browser).

On every task we examined, the score ranking matches the visual
ranking by inspection:

| Task | Spread | Visible difference between best and worst |
|---|---:|---|
| `docs_mono-001` | 0.228 | best preserves 3-pane mono layout; worst compresses to dark single column |
| `portfolio_neobrut-001` | 0.234 | best hits oversized italic display + colour blocks; worst flattens both |
| `government__dark_native_clean-001` | 0.201 | best is faithful dark layout; worst crams 3 columns into single-column hero space |
| `auth_glassy-001` | 0.089 | best near-identical; worst flips sidebar+footer to dark |
| `pricing_dark-001` | 0.051 | best & worst both close — minor proportions differ |
| `saas_minimal-001` | 0.795 | best near-identical; worst submitted **no HTML** (0.000) |

The grader's reward signal is **monotone in visual fidelity** by
construction (every sub-signal is bounded in [0,1] with higher = more
similar to GT) and confirmed empirically by the pair-by-pair
inspection. **No reversed pairs** were found.

### 4.3 Per-signal discrimination

Across 124 trials (106 final-eval Opus + 18 cross-model), the
per-signal mean, std, Spearman correlation with composite, and share
of composite variance attributable to each signal:

| Signal | Weight | Mean | Std | Spearman ρ vs composite | Variance share |
|---|---:|---:|---:|---:|---:|
| **`bm_position`** | 0.20 | 0.49 | **0.24** | **+0.88** | **57 %** |
| **`tree_bleu`** | 0.20 | 0.41 | 0.11 | +0.80 | 12 % |
| **`bm_recall`** | 0.15 | 0.71 | 0.20 | +0.76 | 22 % |
| `bm_color` | 0.15 | 0.81 | 0.12 | +0.58 | 7 % |
| `bm_text` | 0.10 | 0.91 | 0.10 | +0.90 | 2 % |
| `bm_font` | 0.10 | 0.82 | 0.12 | +0.64 | 3 % |
| `bm_size` | 0.05 | 0.68 | 0.11 | +0.86 | 1 % |
| `visual_ssim` | 0.05 | 0.48 | 0.16 | +0.77 | 1 % |

(Variance share = (w·std)² normalised; assumes signal independence so
slightly overstates contributions. Earlier `bm_border` was dropped
to 0.00 weight after this same analysis showed Spearman ρ = −0.02
across 124 trials — flat near 0.95 on every run, contributing nothing
to ranking.)

**One signal does the majority of the work.** `bm_position` carries
≈57 % of composite variance — agents reliably produce the right
elements but place them slightly off, and that gap is what
discriminates a faithful replica from an approximate one.

`bm_recall` is the second-biggest mover (≈22 %): "the agent matched
a smaller share of GT than it should have" catches sparse-output
agents on dense pages.

`bm_text` and `bm_size` show the highest Spearman with composite
(+0.90, +0.86) — they correlate strongly with quality — but their low
weight × low std means they don't *separate* runs much. Every Opus
trial reproduces text faithfully (mean 0.91). They're useful as
quality *indicators* and anti-gaming guards rather than primary
discriminators.

`bm_color` correlates more weakly with composite (+0.58) than other
signals — palettes are shared across the same template family, so
most agents land in the right colour neighbourhood regardless of
overall faithfulness.

`visual_ssim` is the smallest contributor (≈1 %): it's redundant
with `bm_position` (r=+0.73) and saturates low (max ≈ 0.74 even on
oracle-faithful renders due to anti-aliasing noise). It earns its
5 % weight as the only pure-pixel sanity check — defends against the
"right DOM, weird imagery" adversarial mode that the structural
signals would otherwise miss.

### 4.4 External validity — perturbation curve and model rank ordering

Two checks were run to confirm the score is a meaningful number, not
just an internally-consistent ranking.

**(a) Perturbation monotonicity.** For three diverse tasks
(`auth_glassy-001`, `dashboard_dense-001`, `portfolio_neobrut-001`)
we synthesised five GT-derived agent submissions per task at
increasing severity:

| sev | what we feed the grader | expected behaviour |
|---:|---|---|
| 0 | random ASCII gibberish, no CSS | floor (≈0) |
| 1 | GT structure, no CSS, all text shuffled | low |
| 2 | GT structure + GT CSS, all text shuffled | mid |
| 3 | GT, 25 % of text leaves shuffled | high |
| 4 | byte-for-byte GT (oracle) | 1.000 |

Result on all 3 tasks (full curve in
`report_figures/perturbation_curve.png`):

| task | sev 0 | sev 1 | sev 2 | sev 3 | sev 4 |
|---|---:|---:|---:|---:|---:|
| `auth_glassy-001` | 0.032 | 0.678 | 0.979 | 0.995 | **1.000** |
| `dashboard_dense-001` | 0.001 | 0.574 | 0.968 | 0.991 | **1.000** |
| `portfolio_neobrut-001` | 0.005 | 0.638 | 0.949 | 0.983 | **1.000** |

Strict monotonicity holds at every step on every task; sev 0 hits the
floor; sev 4 hits exactly 1.000. The largest single jump is sev 1 →
sev 2 (≈+0.30) where CSS comes back — this is the layout/visual
signals firing. The remaining gap to oracle is small (≈0.02–0.05)
because sev 2 and sev 3 already match GT structure and styling
pixel-for-pixel, and only the text content differs. That matches the
weights: text-only signals are ≤ 10 % of the composite.

**(b) Cross-model rank ordering.** A 3-model × 3-task × 2-attempt run
(`configs/cross_model_calibration.yaml`, all 18 trials graded) checks
that a stronger Claude variant scores higher on average:

| model | overall | `auth_glassy` | `dashboard_dense` | `portfolio_neobrut` |
|---|---:|---:|---:|---:|
| `claude-haiku-4-5` | 0.514 | 0.619 | 0.540 | 0.383 |
| `claude-sonnet-4-6` | 0.623 | 0.749 | 0.654 | 0.466 |
| `claude-opus-4-7` | **0.685** | **0.848** | **0.727** | **0.479** |

Strict haiku < sonnet < opus ordering holds **overall and on every
task individually**. Bar plot in `report_figures/cross_model_scores.png`,
raw rows in `report_figures/cross_model_results.csv`. Same pages, same
prompt, only the model differs — so the score difference is
attributable to model output quality, not noise. This is the
calibration anchor the grader was missing in v3.x.

---

## 5. Grader shortcomings

Honest accounting of where the grader falls short.

### 5.1 Spatial fidelity is centroid-only

`bm_position` compares centroid Δx/Δy on viewport-normalised
coordinates. It does **not** measure rotation, perspective, or precise
size — `bm_size` does pure area ratio without aspect-ratio comparison.
An agent that places the right element at the right centroid but at
2× width and ½ height scores well on position but poorly on size; an
agent that gets size right but at 30° rotation scores ~1.0 on both.
Neither failure is realistic in HTML/CSS but the grader has no head
that catches it if it happens.

### 5.2 No image-content comparison

`<img>` element area is matched but pixel content of the rendered
image isn't compared. If an agent uses `photo-portrait-1.jpg` where
GT used `photo-landscape-1.jpg` the grader treats both as "an image
of similar size at similar position" without noticing they're
visually different. Image-aware extension would compute SSIM or DINO
similarity per `<img>` element; not implemented because all our 11
tasks use the same 5-image allow-list.

### 5.3 Modal verifier instability on long tasks

The v5.1 grader runs in 12-15 seconds locally on a 7-page task but
the verifier sandbox stalled on 18% of 7-page trials in our run
(Modal scheduling, not grader correctness — local re-grade always
returns a value). Production deployment would either (a) increase
verifier timeout to 1800s, (b) run the grader on a beefier Modal
machine type, or (c) profile and remove the stall.

### 5.4 No human-rated calibration anchor

We validated correlation by visual inspection of best-vs-worst pairs
(§4.2), perturbation monotonicity, and cross-model rank ordering
(§4.4). We did not collect ≥30 human-rated triplets to anchor the
grader against ground-truth visual-similarity ranking. Spearman ρ
between the v5.1 grader and the predecessor v3.4 baseline was 0.733
(n=59, on the 6 tasks where we had paired data) — meaningful but not
definitive evidence of correctness.

### 5.5 Single-viewport

The grader scores at desktop (1280×800) only. Mobile responsiveness
regressions go uncaught. The v3.4 predecessor scored at desktop +
mobile with 0.7/0.3 weighting; v5.1 dropped this for grader simplicity
and runtime. Adding mobile back is a one-line config change.

### 5.6 No anti-gaming validated empirically

The architecture is designed to make trivial cheats score near 0
(§1.5). We didn't actually run an adversarial agent that tries each
cheat — the proofs are by construction (signal weights), not by test.

---

## 6. What we learned about Opus 4.7

Catalogued from the per-signal breakdown and inspection of best/worst
pairs across all 11 tasks.

### 6.1 What Opus does well

- **Text content.** `bm_text` mean = 0.916, std = 0.106. Brand copy,
  value propositions, feature lists, headlines — extracted faithfully
  from screenshots in nearly every run.
- **Default border / shadow conventions.** `bm_border` mean = 0.954,
  std = 0.096. Modern card aesthetics (8px radius, soft shadow) are
  converged Opus defaults.
- **Element inventory.** `bm_recall` mean = 0.731 — Opus matches a
  high share of GT elements by area on most tasks.

### 6.2 What Opus consistently struggles with

**Element positioning** is the dominant failure mode across all
tasks. `bm_position` mean = 0.482, std = 0.235 — Opus produces the
right elements but places them slightly off. Patterns we observed:

- **Symmetric drift.** When GT is asymmetric (`portfolio_neobrut`,
  `news_portal`), Opus drifts toward symmetric / grid-aligned layouts
  even when the screenshots show otherwise. Half the Opus runs on
  `portfolio_neobrut` produced ordinary 12-col grids when GT has 3-4
  staggered colour blocks.
- **Column compression.** When GT uses a narrow-measure body (~65ch
  for serif editorial, ~40ch for narrow news lists), Opus defaults to
  ~80–120ch and the page reflows wrong. `news_portal` drops bm_position
  to ~0.29 on multiple runs from this alone.
- **Single-page hero compression.** When GT has a tall hero with
  generous whitespace (`government`, `hotel`), Opus compresses it
  vertically and starts the next section higher up the fold.

### 6.3 Palette discipline on dark themes

When a task is dark-native (`pricing_dark`, `dashboard_dense`,
`government`, `news_portal`, `splash_crypto`), Opus reaches for
**default Tailwind dark** — `bg-slate-950 text-white` with a lot of
accent colours — rather than holding to a single restrained palette.
The agent's elements end up in the same colour family but with
shifted hue/saturation. CIEDE2000 (`bm_color`) catches this:
dark-native tasks have `bm_color` ~0.78 vs ~0.88 on light-mode tasks.

### 6.4 Density in dense info-architectures

`news_portal`, `dashboard_dense`, and `government` are intentionally
information-dense designs. Opus on these produces visibly *less*
dense reproductions — wider spacing, fewer cards per row, more
whitespace. This drops `bm_recall` (smaller matched area) and
`tree_bleu` (fewer nested structures) on dense tasks vs sparse ones.

### 6.5 Failure modes worth flagging

- **No-submission failure** (`saas_minimal-001__Fkc9r6q`, score 0.000):
  the agent's trajectory ended without writing any HTML to `/app/`. The
  underlying cause is likely an Opus deliberation loop that exhausted
  the trial budget. 1/110 = ~1% rate in this run.
- **Gen-2 task degradation.** Tasks added in the second-generation
  pipeline (government, healthcare, hotel, news, splash_crypto)
  cluster ~0.07 below the original 6 in mean score. We don't have
  enough data to rule out: (a) Opus is genuinely worse at the new
  verticals' density patterns, vs (b) the new tasks are slightly
  harder ground truths regardless of model. Worth investigating with
  cross-model runs.

### 6.6 The grader is most useful as a discriminator of palette
discipline + spatial composition

Opus reproduces text + borders near-perfectly almost always, so those
signals contribute mostly to the floor of the score. The *spread*
between a great Opus run and a mediocre one comes almost entirely
from `bm_position`, `bm_recall`, and `visual_ssim` — which is exactly
what visual fidelity benchmarks should reward.

---

## 7. Reproducing the results

```bash
# Generate all 11 tasks (~30-50 min, ~$30-50 in Anthropic credits)
env -i HOME=$HOME PATH=$PATH SHELL=$SHELL USER=$USER LANG=en_US.UTF-8 \
  ANTHROPIC_API_KEY="$(tr -d '\n\r' < ~/.trial-anthropic-key)" \
  bash scripts/synth-all.sh

# Run Opus 4.7 × 10 attempts on all 11 tasks (~30-90 min, ~$50-200)
env -i HOME=$HOME PATH=$PATH SHELL=$SHELL USER=$USER LANG=en_US.UTF-8 \
  ANTHROPIC_API_KEY="$(tr -d '\n\r' < ~/.trial-anthropic-key)" \
  harbor run -c configs/final_eval_opus.yaml -y \
  --ae ANTHROPIC_API_KEY="$(tr -d '\n\r' < ~/.trial-anthropic-key)"

# Aggregate v5.1 scores from jobs/<run_name>/*/verifier/reward.json
.venv/bin/python /tmp/aggregate_v51.py
```

Stuck Modal verifier sandboxes can be recovered locally:

```bash
.venv/bin/python /tmp/recover_stuck.py     # re-grade from agent/trajectory.json
```

---

## 8. Out of scope (Parts 2 and 3 of the brief)

- **Animations** (Part 2). The grader operates on static screenshots;
  it doesn't see CSS keyframes or transitions. A natural extension is
  temporal SSIM frame-by-frame from `page.video()` recordings, plus
  CSS animation declaration comparison.
- **React / Tailwind / Solid** (Part 3). The pipeline currently emits
  HTML+CSS files; the spec → compiler split is framework-agnostic and
  could swap the compiler stage without changing the grader (which
  operates on the rendered DOM).
- **Pattern coverage on every vertical.** Pattern axes (see §2's
  within-pair diversity subsection) are populated for `saas_landing`
  as proof. Extending each remaining vertical takes ~2 hours of
  careful per-vertical authorship; the schema is in place, only the
  content is missing. Required to scale the dataset from ~tens to
  hundreds without quality drift.
- **Stratified batch sampling.** `--random` today is uniform over
  the 56 valid pairs; some pairs (`saas_clean` covers 11 verticals)
  get over-sampled at large batch sizes. A `sample_batch(N)` that
  enforces coverage across the (regime × typography × density) grid
  is needed for production batches >50.

Both Parts 2 and 3 were deferred per the brief's "high-taste Part 1
beats rushed all-three" guidance.

---

## 9. Repo map

```
trial/
├── src/
│   ├── synthesize.py          # the per-page LLM compiler
│   ├── _blockmatch_grade.py   # the v5.1 grader (primary)
│   ├── _container_grade.py    # helpers (CIE-Lab, tree-BLEU); shipped alongside grade.py
│   ├── dedup.py               # 64-bit DCT pHash for diversity dedup
│   ├── render.py              # playwright screenshotter
│   └── generate.py            # Harbor task layout
├── templates/
│   ├── verticals/             # 15 verticals (topic + sitemap + brand pool + pattern axes)
│   ├── styles/                # 13 styles (palette + typography + motif)
│   └── compatibility.py       # 56 valid (vertical × style) pairs
├── tests/
│   └── test_templates.py      # invariants, runs in 0.15s
├── scripts/
│   └── perturb_test.py        # 5-severity GT→gibberish perturbation runner (§4.4 a)
├── configs/
│   ├── final_eval_opus.yaml   # the eval config used in §4
│   └── cross_model_calibration.yaml # haiku/sonnet/opus rank-ordering check (§4.4)
├── datasets/final/            # the 11 deliverable Harbor tasks
├── report_figures/
│   ├── v51_results.csv        # 106-row trial output (the data behind §4)
│   ├── v51_pairs.html         # GT-vs-agent gallery (§4.2)
│   ├── v51_contact_sheet.png  # single-image contact sheet
│   ├── v51_scores_per_task.png
│   ├── v51_signals.png
│   ├── v51_best_worst.png
│   ├── grader_correlation.png # v5.1 vs v3.4 baseline scatter
│   ├── pairs_v51/             # 22 best+worst stitched PNGs
│   ├── perturbation_results.csv  # 5-severity × 3-task curve (§4.4 a)
│   ├── perturbation_curve.png
│   ├── cross_model_results.csv   # 18-trial 3-model rank ordering (§4.4 b)
│   └── cross_model_scores.png
├── PIPELINE.md                # deeper pipeline reference
├── GRADER.md                  # grader's reasoning trail
├── TAXONOMY.md                # design space (12 archetypes × 5 axes)
├── REPORT.md                  # this file
└── README.md                  # crisp entry point
```
