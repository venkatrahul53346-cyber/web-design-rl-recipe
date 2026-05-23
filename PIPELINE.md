# PIPELINE.md — how websites get generated

> Read this if you want to understand the synthesis pipeline, the
> rules we hardcode for the LLM, or how to add a new vertical / style.

This document is the deepest reference for the pipeline. For the
trial deliverable summary, see [REPORT.md](REPORT.md). For the
grader's reasoning, see [GRADER.md](GRADER.md). For the design space
itself (the 12 archetypes × 5 style axes that informed our
selections), see [TAXONOMY.md](TAXONOMY.md).

---

## 1. What this pipeline does

Given a `(vertical, style)` pair and a seed, it produces a Harbor
task: a directory containing screenshots, ground-truth HTML/CSS, a
grader, and a Dockerfile. The agent (Claude Code) sees the
screenshots, recreates the design in HTML+CSS, and is graded on
visual fidelity. Functionality is out of scope.

```
(vertical, style, seed)
    │
    ▼
WebsiteSpec  ──→  Stage 1: design pass (CSS + nav + footer + brief)
                     │
                     ▼
                 Stage 2: per-page passes (one Anthropic call per page,
                          with a render-time validation loop)
                     │
                     ▼
                 {styles.css, page1.html, page2.html, …}
                     │
                     ▼
                 Playwright screenshots at desktop+mobile
                     │
                     ▼
                 Harbor task directory
```

## 2. End-to-end flow

The entry point is `python -m src.synthesize`:

```
src.synthesize.main()
   ├── parses CLI: --vertical X --style Y --seed N --out DIR
   │                OR --random --seed N
   │                OR --spec path/to/spec.json
   ├── calls templates.sample_spec(v, s, seed) → WebsiteSpec
   └── calls synthesize_task(spec, out)
         ├── call_compiler(spec) — LLM compile loop
         │     ├── design_pass(spec) — Anthropic call #1
         │     │     returns {styles_css, nav_html, footer_html, design_brief}
         │     └── for each page in sitemap:
         │           page_pass_iterative(spec, design, page_name)
         │             ├── attempt 1: Anthropic call → page.html
         │             ├── validate (format + render-time at desktop+mobile)
         │             ├── if issues: append assistant + user turn, retry once
         │             └── if exhausted: log + accept best-effort (don't abort)
         ├── render_site(scratch_dir, screens_dir) — host-side Playwright
         └── build_task_dir(out_dir, files=…, screenshots=…, assets=PLACEHOLDERS)
```

`build_task_dir` is shared with the (archived) earlier ingester paths
and is responsible for the Harbor on-disk layout — `task.toml`,
`instruction.md`, `environment/Dockerfile`, `solution/`, `tests/`.

## 3. Anatomy of a vertical

A vertical describes **what we're building** — independent of how it
looks.

```python
# templates/verticals/_base.py

@dataclass
class VerticalMeta:
    name: str                    # e.g. "developer_docs"
    archetype: str               # "A1".."A12" — for grouping/reporting
    difficulty: str              # "easy" | "medium" | "hard"
    topic_description: str       # ~250 words: who, what, why
    page_hints: dict[str, str]   # per-page guidance
    sitemap_pool: list[str]      # candidate pages
    sitemap_min, sitemap_max: int
    sitemap_first: str           # the page that always leads (default "index")
    brand_verticals: list[str]   # which brand pools to draw from
    references: list[str]        # text-only ("oxide.computer/docs", ...)
    density_override: str | None # forces a density regardless of style
```

Why these fields:
- `topic_description` is the LLM's grounding. It's prose, not a
  schema. ~250 words because that's enough to describe a website type
  without bloating the prompt.
- `page_hints` are per-page nudges — what should be on the pricing
  page, what should be on the FAQ page. Keeps the design coherent
  across pages.
- `brand_verticals` ties verticals to compatible brand persona pools.
  A government vertical doesn't pull a SaaS persona.
- `density_override` is needed because a `dashboard_app` vertical is
  always dense regardless of which style it pairs with — that's a
  property of the topic, not the visual language.

## 4. Anatomy of a style

A style describes **how it looks** — independent of topic.

```python
# templates/styles/_base.py

@dataclass
class StyleMeta:
    name: str                    # e.g. "mono_warm"
    color_regime: str            # locked
    typography: str              # locked
    border_language: str         # locked
    motif: str                   # locked
    density_default: str         # default; vertical can override
    palette_pool: list[str]      # hex anchors
    font_pool: list[tuple]       # (display, body, mono?) options
    font_pair_locked: tuple|None # None = sample
    style_notes: str             # ~200 words visual language
    style_references: list[str]  # text-only
```

The four locked axes (`color_regime × typography × border_language ×
motif`) are the **identity** of a style. You can't sample
`typography=mono` with `border=glassy-blurred` and get something
coherent. So those are bundled.

Within those locked axes, palette anchor and font pair ARE sampled
per seed. So `mono_warm` always has a warm-neutral background and
mono everywhere, but the specific accent colour and the specific mono
font (JetBrains / Geist / IBM Plex) varies per task.

## 5. The compatibility matrix

`templates/compatibility.py` holds a **positive list** per vertical:
which styles are visually plausible for each topic.

```python
COMPATIBLE_STYLES = {
    "saas_landing":      {"saas_clean", "dark_native_clean", "mono_warm",
                          "mono_dark", "glassy_pastel", "neobrut_thick"},
    "developer_docs":    {"saas_clean", "dark_native_clean", "mono_warm",
                          "mono_dark", "neobrut_thick"},
    "editorial_pub":     {"serif_editorial", "photo_warm_display",
                          "editorial_dark"},
    # …
}
```

We use a positive list (rather than an exclusion list) because the
natural human question is "what styles fit this topic?", not "what
combinations are bad?". Adding a new vertical means specifying its
compatible styles, full stop.

Today the matrix has 15 verticals × 13 styles → **56 valid pairs**.
Some verticals are flexible (saas_landing fits 6 styles), some
constrained (restaurant fits only 2). That's the empirical truth —
restaurant websites simply don't look like terminal-aesthetic devtool
sites, and we don't pretend otherwise.

## 6. Brand personas

Hand-curated, partitioned by vertical, in `templates/_brands.py`:

```python
BRANDS_BY_VERTICAL = {
    "saas":          [<5 personas>],
    "devtools":      [<5 personas>],
    "fintech":       [<3 personas>],
    "ecom-fashion":  [<3 personas>],
    "media":         [<2 personas>],
    "agency":        [<2 personas>],
    "hospitality":   [<3 personas>],
    "ai-product":    [<3 personas>],
    "government":    [<3 personas>],
    "healthcare":    [<3 personas>],
    "marketplace":   [<2 personas>],
}
```

Each persona has a name, tagline, value-prop, product category, and
target audience. They're plausible-sounding fictional brands — not
real companies, not generic ("CompanyA"), not lorem ipsum.

Why hand-curated and not LLM-generated at synth time:
- **Determinism.** Same seed → same brand, every time.
- **Cost.** Generating 100 personas at synth time would cost real
  money for marginal variance.
- **Quality.** Curated personas are crisp and unique; LLM-generated
  personas drift toward generic SaaS-speak.

## 7. Image policy — the no-broken-images rule

This is a hard constraint enforced at three layers:

### Layer 1: prompt-side (LLM is told)
The system prompt and per-page DESIGN_NOTES include:

> **For purely decorative content** (hero illustrations, abstract
> section dividers, decorative blobs): use NO `<img>` tags. Use CSS
> gradients, inline SVG, or styled `<div>` blocks.
>
> **For content-essential photography** (product photos, dish
> photos, hotel rooms, portrait avatars, editorial leads): use
> `<img src="X">` where X is EXCLUSIVELY one of:
>
> - `photo-product-1.jpg` (generic product / object)
> - `photo-product-2.jpg` (cooler product variant — for grids)
> - `photo-portrait-1.jpg` (generic person)
> - `photo-landscape-1.jpg` (generic scene)
> - `illustration-abstract.jpg` (mesh-gradient — for splash hero)

### Layer 2: validation-side (synth-time check)
`src/synthesize.py::_validate_page_format` parses every `<img src=>`
in generated HTML; non-allow-listed sources become a validation issue
that's fed back to the LLM with concrete fix hints.

### Layer 3: shipping-side (assets are real)
`synthesize_task` always passes the 5 placeholder JPGs to
`build_task_dir(assets=…)`. They land in:
- `environment/assets/` (Dockerfile bakes into `/app/`)
- `solution/ground_truth/`
- `tests/ground_truth/`

So at trial time, both the agent's HTML and the GT have access to
the files at `/app/<filename>`. No more broken-image icons.

Placeholder images are procedurally generated via PIL (gradient +
noise + soft-edge shapes) — see `scripts/build_placeholders.py`. They
look intentional (mesh-gradient, sky-with-horizon, etc.), not
"missing image". No third-party photography licensing involved.

## 8. The compiler

Two stages, both via Anthropic Opus 4.7.

### Stage 1: design pass
Single call, 12-16K output token budget. Produces:
```json
{
  "styles_css": "...",
  "nav_html": "<header>…</header>",
  "footer_html": "<footer>…</footer>",
  "design_brief": "..."
}
```
The design brief is plain-text (200-400 words) describing the
visual conventions; it's fed to every per-page pass to keep them
consistent.

### Stage 2: per-page passes (one call per page)
For each page in the sitemap:
1. Build the per-page user prompt (vertical's topic_description +
   page_hints[page] + style's style_notes + brand interpolation +
   image rules)
2. Stream call to Opus with the design pass output as shared context
3. Validate format (DOCTYPE, `<link rel="stylesheet">`, image src
   allow-list)
4. Validate render-time at desktop (1280×800) and mobile (390×844):
   - mobile horizontal overflow check (scrollWidth > viewport + 20px)
   - mobile `<meta name="viewport">` tag presence
   - desktop page height ≥ 200px
   - desktop content coverage ≥ 3% non-white pixels
5. If issues, append assistant + user turn, retry up to 1 more time
6. If still failing after 2 iters: log + accept best-effort

### Token budgets
- Design pass: `DESIGN_MAX_TOKENS = 16000` (heavy data-viz themes
  exceeded 12K)
- Per page: `PAGE_MAX_TOKENS = 20000` (rich pages with code blocks
  need ~10-15K)

### Iteration cap
- `PAGE_MAX_ITERATIONS = 2` — initial attempt + up to 1 correction
- Trade-off: 1 lets cost stay bounded; 4 (the original) sometimes
  took 4× longer for marginal gains. 2 is the sweet spot.

### Transient retries
A separate retry wrapper handles `httpx.RemoteProtocolError`,
`anthropic.APIConnectionError`, etc. — up to 2 retries with 1s/4s
backoff. **These do not consume an iteration slot** — they're
transparent to validation.

## 9. The validation loop

For each page, after the LLM returns HTML:

| Check | Domain | Action on fail |
|---|---|---|
| Starts with `<!DOCTYPE html>` | format | flag + retry |
| Has `<link rel="stylesheet" href="styles.css">` | format | flag + retry |
| `<img src=>` in allow-list | format | flag + retry |
| Mobile `scrollWidth ≤ viewport+20` | render | flag + retry |
| Mobile has `<meta name="viewport">` | render | flag + retry |
| Desktop `scrollHeight ≥ 200` | render | flag + retry |
| Desktop content coverage ≥ 3% | render | flag + retry |

Failure feedback is **specific and actionable**, not generic:

> [mobile 390×844] Horizontal overflow: page width is 461px but
> viewport is only 390px. Common causes: (1) hardcoded
> `width: <some-large-px>` in CSS — replace with `max-width:` and
> percentage / `1fr` / `auto`; (2) flex containers without
> `flex-wrap: wrap`; (3) images without `max-width: 100%; height: auto`.
> Add `@media (max-width: 768px) { ... }` queries to switch to a
> stacked / single-column layout.

## 10. The "AI tells" we forbid (verbatim from synthesize.py)

Every system prompt to the LLM includes:

```
CRITICAL — AVOID THESE "AI-GENERATED TELLS":

1. Uniform vertical rhythm. Do NOT use the same `padding: 96px` /
   `py-16` on every section. Vary section padding for hierarchy.
2. Single font family at four weights. If the spec asks for
   display-mixed or two distinct typefaces, ACTUALLY use two.
3. Snap-to-12-col grid for everything. Use asymmetric grids,
   overlapping elements, edge-bleeds when the design calls for it.
4. `border-radius: 12px` and `box-shadow: 0 1px 2px rgba(0,0,0,0.05)`
   on every card regardless of brand. Match the spec's
   border_language.
5. Default 3-stop linear gradient hero. If motif is clean-iconographic,
   NO gradient blobs.
6. Always-centered headlines. Edge-aligned, oversized-display
   headlines are valid and often better.
7. Default Tailwind grays when a brand palette is specified.
8. The "shadcn template": hero → 3-feature-grid → testimonials → CTA.
   Vary section types, order, and layout per archetype.
9. Pastel-on-white regardless of color_regime. Match the regime.
10. Lorem ipsum / "Feature one — Description". Write real copy.
```

Plus the image policy from §7.

These came from observed failure modes of Lovable / v0 / bolt-style
AI website builders. By calling them out explicitly the LLM is much
more likely to avoid them.

## 11. The grader (cross-reference)

The grader is shipped inside every task as `tests/grade.py`, baked
from `src/_container_grade.py` v3.4. Five signals:

| Signal | Weight | Asks |
|---|---:|---|
| Layout | 0.30 | Are elements in the right places? |
| Visual SSIM | 0.25 | Do screenshots look the same? |
| Component recall | 0.20 | Are the right elements present? |
| Text | 0.15 | Did meaningful copy survive? |
| Style HSV | 0.10 | Are the brand colors right? |

Each signal computed at desktop AND mobile, weighted 0.7/0.3.
Adversarial gates (content-coverage, weight-aware text intersection)
prevent blank-page exploits.

For the full reasoning trail (4-step calibration on 10 D2C tasks,
why each weight), read [GRADER.md](GRADER.md).

## 12. Adding a new vertical

```bash
# 1. Create the module
cat > templates/verticals/my_vertical.py <<EOF
from templates.verticals._base import VerticalMeta

META = VerticalMeta(
    name="my_vertical",
    archetype="A2",
    difficulty="medium",
    topic_description="...250 words...",
    page_hints={
        "index": "...",
        "page_a": "...",
    },
    sitemap_pool=["index", "page_a", "page_b", "page_c", "page_d", "page_e"],
    sitemap_min=5, sitemap_max=6,
    brand_verticals=["saas"],
    references=["example.com"],
)
EOF

# 2. Register in templates/verticals/__init__.py
# Add `from templates.verticals import my_vertical` and add to VERTICALS dict.

# 3. Add to compatibility matrix in templates/compatibility.py
# COMPATIBLE_STYLES["my_vertical"] = {"saas_clean", "dark_native_clean", ...}

# 4. Add brand personas to _brands.py if introducing a new brand_vertical key

# 5. Run pytest
.venv/bin/python -m pytest tests/
```

The roundtrip-and-invariant tests will fail loudly if you forget any
step: missing brand vertical, page_hints referencing nonexistent
pages, sitemap bounds out of range, etc.

## 13. Adding a new style

```bash
# 1. Create the module
cat > templates/styles/my_style.py <<EOF
from templates import _fonts, _palettes
from templates.styles._base import StyleMeta

META = StyleMeta(
    name="my_style",
    color_regime="pastel",          # one of VALID_COLOR_REGIMES
    typography="geometric-sans",    # one of VALID_TYPOGRAPHIES
    border_language="hairline-1px", # one of VALID_BORDERS
    motif="clean-iconographic",     # one of VALID_MOTIFS
    density_default="balanced",     # one of VALID_DENSITIES
    palette_pool=_palettes.PASTEL_PURPLES_AND_BLUES,
    font_pool=_fonts.GEOMETRIC_SANS,
    style_notes="...200 words...",
    style_references=["site.com", "another.com"],
)
EOF

# 2. Register in templates/styles/__init__.py

# 3. Add to compatibility — for which verticals does it fit?
# Append "my_style" to the sets in COMPATIBLE_STYLES.

# 4. If using a new color regime or typography axis, expand
#    templates/_palettes.py / _fonts.py first.

# 5. pytest (will catch any inconsistencies)
```

## 14. CLI reference

```bash
# Explicit pair
python -m src.synthesize \
  --vertical developer_docs --style mono_warm \
  --seed 0 --out datasets/final/devdocs-001 --force

# Random compatible pair
python -m src.synthesize \
  --random --seed 42 \
  --out datasets/final/random-042 --force

# From a JSON spec (bypass registry)
python -m src.synthesize \
  --spec /path/to/spec.json \
  --out datasets/final/from-spec --force

# All synth runs need ANTHROPIC_API_KEY — and run via env -i to
# isolate from any Vertex env on the host (see CLAUDE.md).
env -i HOME=$HOME PATH=$PATH SHELL=$SHELL USER=$USER LANG=en_US.UTF-8 \
  ANTHROPIC_API_KEY="$(tr -d '\n\r' < ~/.trial-anthropic-key)" \
  python -m src.synthesize --random --seed 0 --out datasets/final/x
```

## 15. Diversity selection — picking N tasks for a deliverable

When building a benchmark of N tasks, pick (vertical, style) pairs
that maximise coverage of both axes. Constraints to apply:

- Every (vertical, style) pair is unique.
- Every vertical appears at most once.
- Every style appears at most once.
- Mix of difficulty: keep some easy controls so you can see what the
  saturation floor looks like; keep many high-signal cells so you
  can see what the model struggles with.
- Cover the new (vertical, style) cells the architecture unlocked,
  not just easy carries from the old slate.

This is a set-cover problem, but small enough to solve by hand. The
[REPORT.md](REPORT.md) §3 documents the selection rationale for the
current 10 final tasks.
