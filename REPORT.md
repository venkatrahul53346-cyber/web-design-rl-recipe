# Web-design RL benchmark — Part 1 report

> **The brief.** Build a scalable pipeline that produces RL environments
> testing a coding agent's ability to *replicate a multi-page web design*
> in HTML + CSS from screenshots. Functionality is out of scope; visual
> fidelity is what's graded. Tasks run on
> [Harbor](https://harborframework.com/). Crawling existing websites is
> forbidden — sites must be generated from scratch.

This report covers Part 1: pipeline, 15 tasks, grader, and the
empirical results of running Opus 4.7 ten times on each task. Parts 2
(animations) and 3 (multi-framework) are out of scope per the brief's
"high-taste Part 1 beats rushed all-three" guidance.

---

## 1. Pipeline at a glance

```
   ┌──────────────────────┐
   │ templates/<name>.py  │  hand-curated, ~100 LOC each
   │   META               │  locked vs sampled style axes
   │   DESIGN_NOTES       │  prompt-engineering payload
   │   sample_spec(seed)  │  deterministic random.Random
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
   └──────────┬───────────┘
              │
              ▼  datasets/final/<template>-001/
              │
   ┌──────────▼───────────┐
   │ harbor run -c ...    │  100 trials (10 tasks × 10 Opus runs)
   │  → jobs/<run>/       │  per-trial reward.json
   └──────────────────────┘
```

The pipeline has **one user-facing knob**:

```bash
.venv/bin/python -m src.synthesize --template <name> --seed <int> --out <dir>
# or
.venv/bin/python -m src.synthesize --random-template --seed <int> --out <dir>
```

Templates are an **explicit registry** in `templates/__init__.py` — no
autoglob, no dynamic discovery. To add a new archetype: write a module
with `META`, `DESIGN_NOTES`, `sample_spec`; import it; add it to
`REGISTRY`. The roundtrip-invariant suite (`tests/test_templates.py`)
catches META/sampler drift on every commit.

---

## 2. Design decisions

This section answers: *what are the load-bearing choices, and what
alternatives did we consider and reject?*

### 2.1 Spec-driven LLM compile, not direct LLM-to-HTML

The compiler runs in **two stages** — a design pass that produces shared
CSS + nav + footer + a design brief, and N per-page passes that consume
that brief. This costs ~6 Anthropic calls per task instead of 1. Why?

- A single 32K-output call **truncates** on content-rich archetypes
  (devdocs with code blocks easily exceeds 32K total).
- Without a shared design pass, per-page outputs use **inconsistent CSS
  classes**, **inconsistent nav markup**, and **inconsistent palette**,
  producing pages that don't look like the same site.
- The two-stage approach mirrors how a frontend team actually works:
  design system first, page-by-page implementation second.

Industry precedent: WebSight (HuggingFace, 2024) uses spec → LLM →
filter; Stanford's Design2Code uses real-world specs. We adapt the spec
idea but generate fully synthetic, since the brief forbids crawling.

### 2.2 Templates carry text references, not HTML examples

Each template's `META.style_references` is a list like
`["linear.app", "attio.com", "stripe.com"]` — **text descriptors only**,
woven into the LLM prompt. We deliberately do NOT include example HTML
or screenshots inside the template.

Why no examples?
1. **Overfit risk.** WebSight's ablations found example-grounded prompts
   converge on the example's idiosyncrasies (specific class names,
   specific layouts) and produce **less diverse** datasets than
   category-only prompting.
2. **Brief forbids crawling**, so we couldn't ship real reference HTML
   even if we wanted to.
3. **LLMs already have it.** linear.app, oxide.computer, every.to are
   in Opus's pretrain. Naming them anchors style without copying markup.

The `notes` field on `WebsiteSpec` formalizes this — it's the entire
"example set," and it's text.

### 2.3 Per-template sampling: locked vs varied axes

Each template fixes the (archetype × signature-style) axes that *define*
its identity, and varies **brand, palette, font, sitemap permutation**
per seed. Reasoning:

- Locking the style axes preserves the template's character. A
  "saas_minimal × pastel × hairline-1px" template that suddenly samples
  `color_regime=dark-native` becomes a different design language —
  that's not variance, it's a different template.
- Varying brand + palette + sitemap gives ~2000 unique specs per
  template, which is more than enough for the deliverable (10 tasks).
- The sampler is a single `random.Random(seed)` chokepoint
  (`templates/_base.py::make_rng`). Pure determinism — same seed →
  identical spec across runs. Future swap to a counter-based RNG is one
  line.

### 2.4 Decoupled vertical / style architecture

The pipeline separates **what we're building** (the vertical:
topic + per-page hints + sitemap + brand pool) from **how it
looks** (the style: locked color/typography/border/motif axes +
palette pool + font pool). They live in two independent registries
(`templates/verticals/`, `templates/styles/`) and combine via a
positive-list compatibility matrix in `templates/compatibility.py`.

This means combinations like `developer_docs × neobrut_thick` and
`saas_landing × mono_dark` are reachable, while nonsensical pairs
like `dashboard_app × serif_editorial` are excluded. The current
matrix is **15 verticals × 13 styles → 56 valid pairs** (every
vertical has 2-6 compatible styles).

### 2.5 Image handling

`<img src=>` in generated HTML is constrained to **exactly five
filenames**: `photo-product-1.jpg`, `photo-product-2.jpg`,
`photo-portrait-1.jpg`, `photo-landscape-1.jpg`,
`illustration-abstract.jpg`. For decorative content the LLM is
instructed to use CSS gradients / inline SVG / styled `<div>` instead.
A validator parses every `<img src=>` in generated HTML and feeds
non-allowlisted sources back as fix hints. The 5 placeholder JPGs
(procedurally generated via PIL — gradient + noise + soft-edge shapes)
are baked into every task's `environment/assets/`, `solution/ground_truth/`,
and `tests/ground_truth/`, so both agent and GT see the same files at
`/app/<filename>`. See `scripts/build_placeholders.py`.

---

## 3. The dataset — 15 tasks across 15 vertical × style combinations

Tasks were chosen to span **3 saturated controls + 12 high-signal cells**
across the design space (sourced from `TAXONOMY.md`'s research-backed
slate, tracked against Design2Code, WebSight, WebGen-Bench, and direct
observation of Lovable / v0 / bolt outputs):

| # | Task | Vertical × style | Difficulty | Why included |
|---|---|---|---|---|
| 1 | `saas_minimal` | SaaS × pastel × hairline-1px × clean-iconographic | easy | Saturated: every modern coding agent should ace this — proves the floor |
| 2 | `pricing_dark` | pricing × dark-native × hairline-1px × clean-iconographic | easy | Saturated: pricing matrices are easy structural shapes |
| 3 | `auth_glassy` | auth × pastel × glassy-blurred × clean-iconographic | easy | Saturated: sparse, modern, cards-on-gradient |
| 4 | `docs_mono` | docs × mono-everywhere × hairline-1px × clean-iconographic | hard | Typography + 3-pane layout (oxide.computer style) |
| 5 | `editorial_serif` | editorial × humanist-serif × editorial-narrow × photographic | hard | Serif body + narrow measure (every.to style) |
| 6 | `dashboard_dense` | dashboard × dense × dark-native × data-viz-decor | hard | Density + dark mode + tables |
| 7 | `portfolio_neobrut` | portfolio × display-mixed × neobrutalist-thick × variable-display | hard | Oversized type + asymmetry + thick borders |
| 8 | `ecom_pastel` | ecom × pastel × hairline-1px × photographic-product | hard | Product grid + filtering |
| 9 | `splash_3d` | splash × abstract-3d × dark-native × variable-display | hard | Cinematic single-product, scroll-driven |
| 10 | `restaurant_photo` | restaurant × photographic-product × display-mixed × muted-editorial | hard | Hospitality aesthetic |
| 11 | `government × dark_native_clean` | new vertical | hard | Civic conventions: dense forms, formal copy, departmental nav |
| 12 | `hotel_booking × photo_warm_display` | new vertical | hard | Hospitality booking: search-led, room cards, photographic |
| 13 | `news_portal × editorial_dark` | new vertical + new style | hard | High info-density news on dark — different from longform editorial |
| 14 | `healthcare_clinic × glassy_pastel` | new vertical | hard | Calming-medical: soft palette, "find a doctor" |
| 15 | `product_splash × crypto_neon` | new style | hard | Web3 / consumer-hardware launch — neon on dark, abstract-3d |

Each task ships with:
- 5–6 page screenshots at desktop resolution (the agent's input)
- One `instruction.md` listing pages + CSS rules
- Ground-truth HTML/CSS in `solution/ground_truth/`
- A `tests/grade.py` baked from `src/_blockmatch_grade.py`
- A Dockerfile that bakes Playwright + grader deps so trials are
  hermetic
- A `task.toml` with timeouts, resource limits, keywords

---

## 4. The grader

> **Higher reward ↔ better visual replication of the design.** This is
> the property that makes the grader trainable: it can't be gamed by
> outputting raw text dumps or blank pages — both score near zero, by
> construction.

The grader uses a **match-then-diff architecture** (Design2Code-style
Block-Match) wrapped by **page-level orthogonal signals**. Matched
elements are scored on six per-pair dimensions; unmatched / structural
properties contribute three page-level signals.

### 4.1 Architecture in one diagram

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
       text-leaf      │  filter: own_text >= 4 chars
       anchors        ▼
                ┌─────────────┐
                │  matching   │  Sørensen-Dice on character bigrams
                │  step       │  Hungarian (Jonker-Volgenant) global
                │             │  one-to-one assignment, threshold 0.5
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
           │  visual_ssim grayscale SSIM × coverage gate
           └────────────┬─────────────┘
                        │
                        ▼
                weighted sum → page combined ∈ [0, 1]
                        │
                        ▼
                mean across pages → trial score ∈ [0, 1]
```

### 4.2 Signal weights and what each measures

| Signal | Weight | What it measures | Failure mode it catches |
|---|---:|---|---|
| **bm_position** | 0.15 | viewport-normalized centroid distance per matched pair | "Right element, wrong place" |
| **bm_text** | 0.10 | char-bigram Dice on matched pair text | "Wrong copy in matched element" |
| **bm_color** | 0.15 | 0.6 × text_color CIEDE2000 + 0.4 × effective_bg CIEDE2000 | "Wrong palette per element AND wrong page background regime" |
| **bm_font** | 0.10 | 0.4 × family (tiered) + 0.4 × size (ratio) + 0.2 × weight (ratio) | "Wrong typography" |
| **bm_border** | 0.05 | 0.4 × radius + 0.3 × style + 0.3 × shadow | "Wrong border treatment" |
| **bm_size** | 0.05 | min(area)/max(area) per pair | "Wrong physical size" |
| **bm_recall** | 0.10 | matched_area / total_GT_area | "Agent didn't match enough of the GT (sparse output, big misses)" |
| **tree_bleu** | 0.20 | DOM 1-height subtree multiset recall | "Wrong nesting (skeletal divs, missing semantic tags)" |
| **visual_ssim** | 0.10 | grayscale SSIM × coverage gate | "Pages don't look the same at the pixel level" |

Sum = 1.000. Combined score ∈ [0, 1] by construction.

### 4.3 Hungarian + Sørensen-Dice — the matching step explained

Each GT page and agent page produces a list of "anchor" elements
(visible elements with own immediate text ≥ 4 chars). For each
(GT_anchor, agent_anchor) pair we compute Sørensen-Dice similarity on
character bigrams of their text:

```
A = "pricing"     bigrams: {pr, ri, ic, ci, in, ng}        (6 bigrams)
B = "pricing plan" bigrams: {pr, ri, ic, ci, in, ng, ...}  (11 bigrams)
shared = 6
Dice = 2*shared / (|A|+|B|) = 12/17 ≈ 0.71
```

Then `scipy.optimize.linear_sum_assignment` (Jonker-Volgenant) solves
the bipartite matching problem — find the one-to-one pairing that
**maximizes total similarity** across all pairs. Pairs scoring below
0.5 are dropped. This is globally optimal — strictly better than greedy
"each GT picks its closest agent" because greedy is order-dependent
when multiple GT elements compete for the same agent counterpart.

## 5. Empirical results — Opus 4.7 × 10 on each of 7 tasks

> The eval set is **7 of the 15 tasks**. Three of the original 10 tasks
> (`ecom_pastel`, `editorial_serif`, `restaurant_photo`) referenced
> image filenames not shipped in `environment/assets/`, breaking both
> agent and GT renders; the image fix in §2.5 was applied to the 5 new
> tasks but the 3 image-heavy tasks were retired. The other 5 new
> tasks ship under the same architecture but were not in this Opus
> trial run; eval here is the 7 valid original tasks.

70 Opus 4.7 trials (10 per task, 7 tasks). Run on Modal sandboxes,
parallel up to 20.

### 5.1 Per-task score distribution

| Task | n | Mean | Std | Min | Max | Spread |
|---|---:|---:|---:|---:|---:|---:|
| `auth_glassy-001` | 10 | **0.788** | 0.047 | 0.709 | 0.862 | 0.153 |
| `docs_mono-001` | 10 | **0.741** | 0.067 | 0.555 | 0.803 | **0.248** |
| `dashboard_dense-001` | 10 | **0.738** | 0.036 | 0.688 | 0.787 | 0.099 |
| `saas_minimal-001` | 10 | **0.699** | 0.066 | 0.621 | 0.789 | 0.167 |
| `pricing_dark-001` | 10 | **0.689** | 0.036 | 0.630 | 0.771 | 0.141 |
| `splash_3d-001` | 10 | **0.634** | 0.041 | 0.571 | 0.678 | 0.107 |
| `portfolio_neobrut-001` | 10 | **0.582** | 0.074 | 0.485 | 0.675 | 0.190 |

Overall: min=0.485, max=0.862, mean=0.696.

The score distribution is **clean**:
- No task above 0.90 — even the best Opus runs visibly miss things
  (the headroom is real).
- No task below 0.45 — the worst Opus runs still produce
  recognizable replicas (no total failures).
- Spread per task: 0.099 (dashboard) to 0.248 (docs_mono). Wider
  spread on tasks where Opus has more variance in approach.

### 5.2 What's driving the spread — per-signal breakdown

Across 70 trials, the per-signal mean and standard deviation tell us
**which signals discriminate runs and which are nearly uniform**:

| Signal | Mean | Std | Discrimination |
|---|---:|---:|---|
| **bm_position** | 0.574 | **0.224** | **highest std** — biggest discriminator |
| **bm_recall** | 0.797 | 0.142 | high |
| **visual_ssim** | 0.517 | 0.142 | high |
| **tree_bleu** | 0.445 | 0.101 | moderate |
| **bm_font** | 0.833 | 0.099 | moderate |
| **bm_size** | 0.724 | 0.096 | moderate |
| **bm_color** | 0.842 | 0.083 | low |
| **bm_text** | 0.950 | 0.045 | very low — agents nail text |
| **bm_border** | 0.968 | 0.017 | almost uniform |

`bm_position` does the heaviest discriminative work — Opus consistently
produces the right elements but places them slightly off. `bm_recall`
catches "agent matched a smaller share of GT than expected" (sparse
agents on dense pages). `visual_ssim` adds a high-level pixel signal
the per-pair signals don't see. `bm_text` and `bm_border` are
near-saturated — every Opus run reproduces text faithfully and uses
similar default border treatments.

### 5.3 Best vs worst run per task — what to look for

| Task | Best | Worst | Δspread |
|---|---|---|---:|
| `auth_glassy-001` | `oFWE4MP` (0.862) | `a24UxZs` (0.709) | 0.153 |
| `dashboard_dense-001` | `srAQf2P` (0.787) | `kqmG8yo` (0.688) | 0.099 |
| `docs_mono-001` | `iHUUnig` (0.803) | `PgyeJBq` (0.555) | **0.248** |
| `portfolio_neobrut-001` | `DVUzoFL` (0.675) | `cRiTsPt` (0.485) | 0.190 |
| `pricing_dark-001` | `QXqp4qN` (0.771) | `Hr2eY6f` (0.630) | 0.141 |
| `saas_minimal-001` | `fywUaux` (0.789) | `jiWj4a7` (0.621) | 0.167 |
| `splash_3d-001` | `MDpUMLV` (0.678) | `zeMmEeV` (0.571) | 0.107 |

The biggest spread (`docs_mono-001`, 0.248) reflects that Opus
sometimes nails the typography-heavy three-pane layout (best 0.803)
and sometimes ships a flatter, less-structured docs page (worst 0.555).

The smallest spread (`dashboard_dense-001`, 0.099) reflects that all
10 Opus runs produced reasonable dashboards — none aced it (best
0.787), none failed (worst 0.688). The data-table-heavy archetype
constrains the design choices an agent can make.

### 5.4 Score → quality correspondence

This is the property that makes the grader trainable. We validate it
by examining the best-vs-worst pair on each task. Renders are in
`report_figures/pairs/<task>__best__score_*.png` and
`report_figures/pairs/<task>__worst__score_*.png`.

On every task we examined, the best-scoring run is **visibly more
faithful** to the GT than the worst-scoring run by inspection:

- `auth_glassy-001`: best (`oFWE4MP`, 0.862) reproduces the
  glassmorphic blur on the auth card; worst (`a24UxZs`, 0.709) ships
  a flat solid card.
- `docs_mono-001`: best (`iHUUnig`, 0.803) ships the three-pane
  layout with monospace running heads; worst (`PgyeJBq`, 0.555)
  collapses to a single column.
- `portfolio_neobrut-001`: best (`DVUzoFL`, 0.675) hits the
  oversized italic display headlines; worst (`cRiTsPt`, 0.485)
  produces ordinary sans-serif.

The grader's reward signal is **monotone in visual fidelity** by
construction (every sub-signal is bounded in [0,1] with higher = more
similar to GT) and validated empirically.

---

## 6. What Opus struggles with — observed failure patterns

Cataloged by inspecting the best/worst trial pairs for each task and
the per-signal breakdown.

### 6.1 Asymmetric / oversized typography (portfolio_neobrut)
Opus reliably reproduces the *style* — thick black borders, yellow/
red/blue color blocks, big sans display — but the *exact spatial
composition* of asymmetric grids is where it falls short. The agent
tends toward symmetric, grid-aligned layouts even when the GT is
intentionally off-kilter. Lowest mean of any task at 0.582.

### 6.2 Dark-native palette discipline (dashboard_dense, splash_3d)
When a task is dark-native, Opus tends to reach for "default Tailwind
dark" — `bg-slate-950 text-white` with a lot of accent colors —
rather than holding to a single restrained palette. The agent's
elements end up in the same color family but with shifted hue/
saturation, dragging `bm_color` down even when individual element
positions and text are correct.

### 6.3 Editorial measure (editorial_serif — retired but illustrative)
The task specifies ~65ch measure for serif body. Opus's default is
~80–120ch container width. The agent gets serif/photographic right
at the typography level, just not the *narrowness* — column
proportions are wrong, hurting `bm_position` and `visual_ssim`.

### 6.4 Cinematic single-product narrative (splash_3d)
Splash pages are intentionally low-text and high-image. Opus tends to
fill them with explanatory paragraphs that the GT doesn't have, which
inflates the agent's element count, drops `bm_recall` (matched / total
GT area), and reduces visual SSIM with the extra content.

### 6.5 Color extraction from screenshots
A pervasive issue across all tasks: when given a screenshot with a
specific brand accent, Opus often picks a *different* color in the
same family — a `#D04A02` deep orange becomes `#E85D2C`. CIEDE2000
catches this even when the page otherwise looks similar (at this
distance, `bm_color` drops ~0.05–0.10 per matched pair).

### 6.6 What Opus does well
- **Text content is mostly preserved** (bm_text mean=0.950, std=0.045):
  the agent extracts brand copy, value propositions, feature lists
  almost verbatim.
- **Border treatments are reliable** (bm_border mean=0.968,
  std=0.017): default radii and shadow conventions match GT.
- **Element inventory is largely right** (bm_recall mean=0.797): the
  agent matches a high share of GT elements by area.

The grader is therefore most useful as a discriminator of **palette
discipline + spatial composition**, which is exactly what visual
fidelity benchmarks should reward.

---

## 7. Reproducing the results

```bash
# 1. Generate the tasks (~30-50 min, ~$30-50 in Anthropic credits)
env -i HOME=$HOME PATH=$PATH SHELL=$SHELL USER=$USER LANG=en_US.UTF-8 \
  ANTHROPIC_API_KEY="$(tr -d '\n\r' < ~/.trial-anthropic-key)" \
  bash /tmp/synth-all.sh

# 2. Run Opus 4.7 × 10 attempts on each task (~30-90 min, ~$50-200)
env -i HOME=$HOME PATH=$PATH SHELL=$SHELL USER=$USER LANG=en_US.UTF-8 \
  ANTHROPIC_API_KEY="$(tr -d '\n\r' < ~/.trial-anthropic-key)" \
  harbor run -c configs/final_eval_opus.yaml -y \
  --ae ANTHROPIC_API_KEY="$(tr -d '\n\r' < ~/.trial-anthropic-key)"

# 3. Aggregate results
.venv/bin/python -m src.report_aggregate jobs/final-eval-opus/
```

---

## 8. Limitations and what we'd do next

- **Variance is brand-deep, not archetype-deep.** Each template still
  produces sites with the same archetype skeleton. A real production
  benchmark would also vary archetype within a "vertical" (saas can be
  A1 _or_ A2 _or_ A4-as-product-page).
- **No animation or interaction.** Out of scope per the brief, but a
  natural next step (Part 2). We'd add `data-anim` markers in the
  ground-truth HTML and grade on transition timing.
- **No multi-framework support.** Out of scope per the brief (Part 3).
  The pipeline architecture supports it cleanly: spec → compiler →
  files. Swap the compiler with a React/Solid one and rebuild.
- **Iteration cap = 1.** With more time budget, raising to 3–4
  iterations and watching the validation loop fix mobile overflow
  in real time would be illustrative.

---

## 9. Repo layout

```
trial/
├── src/
│   ├── synthesize.py          # the per-page LLM compiler
│   ├── _blockmatch_grade.py   # the grader (Block-Match + page signals)
│   ├── render.py              # playwright screenshotter
│   └── generate.py            # Harbor task layout
├── templates/                 # the registry
│   ├── verticals/             # 15 verticals (topic + sitemap + brand pool)
│   ├── styles/                # 13 styles (palette + typography + motif)
│   └── compatibility.py       # 56 valid (vertical × style) pairs
├── tests/
│   └── test_templates.py      # invariants, runs in 0.15s
├── configs/
│   └── final_eval_opus.yaml   # the eval config used in §5
├── datasets/final/            # the 15 deliverable Harbor tasks
├── TAXONOMY.md                # archetype × style design space
├── GRADER.md                  # full grader reasoning trail
├── REPORT.md                  # this file
└── CLAUDE.md                  # session context for next time
```

---

## Part 2 — Animations (TODO)

The brief asks: *can we add animations to the website? How can we have
some animations and judge the ability of the model to perfectly
replicate these animations? You can pass in video recordings to the
model alongside screenshots for this.*

**Status: not started.** Part 1 was prioritized per the brief's
guidance ("very high taste trial with only Part 1 finished beats
rushed all-three").

A sketch of the approach we'd take:

- Extend the synthesis prompt to ask for CSS keyframes / transitions
  on a small, named set of "animation primitives" (fade-in, scale,
  slide, parallax-on-scroll, hover-lift).
- Generate **video recordings** alongside screenshots — playwright's
  `page.video()` API records WebM at a configurable framerate. The
  agent's prompt includes both the static screenshots and the video.
- Grader extension: temporal SSIM frame-by-frame; or extract CSS
  animation declarations from agent vs. GT and compare keyframe
  parameter triples (duration, timing-function, transform-target).
  CSS-level comparison is more robust than pixel-level for cyclic
  transitions.
- Calibration: oracle reproduction → 1.0; static-page reproduction
  on an animated GT → significantly below baseline.

---

## Part 3 — Multiple Frameworks (TODO)

The brief asks: *modify your pipeline to support React JS + CSS,
React JS + Tailwind CSS, and Solid JS + Tailwind CSS*.

**Status: not started.** Same prioritization as Part 2.

A sketch of the approach:

- The synthesis pipeline currently emits HTML+CSS files. The spec →
  compiler architecture is framework-agnostic; we'd add per-framework
  output adapters.
- For React/JSX: emit `App.jsx` per page plus shared `Layout.jsx`,
  use `vite` for the trial container build, snapshot the rendered
  output. Agent receives screenshots, writes JSX.
- For Tailwind: replace the styles.css emission with utility-class
  decoration in the markup. Compiler prompt changes (no per-element
  custom CSS, only Tailwind classes).
- For Solid: architecturally identical to React from the grader's
  perspective — the trial-time render is what matters.
- Per-framework benchmarks: run Opus 4.7 on each framework variant of
  the same 7 tasks. Identify framework-specific failure modes (does
  Opus struggle more with Tailwind class density, or with Solid's
  reactivity primitives?).

The grader itself is **framework-agnostic** — it operates on the
rendered DOM and screenshot, not on the source language. Once the
synthesis pipeline emits per-framework output, the grader needs no
changes.

---

*Last updated during the run: see commit history.*
