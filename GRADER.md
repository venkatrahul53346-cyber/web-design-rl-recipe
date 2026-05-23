# Grader design and reasoning trail

The canonical reasoning for the grader. Whenever a metric, weight, or
filter changes, add an entry to §7 with **what changed**, **why**, and
**what we measured before/after**.

**Current state: v5.1 Block-Match (accepted 2026-05-23).**

---

## 1. The task and what we're optimising for

The brief is to grade how well a coding agent recreates a website's
*visual design* in HTML/CSS, given screenshots. Functionality is out
of scope.

The grader needs to:

1. **Be visual-only** — score the rendered output, not the source
   code. An agent that produces ugly HTML but renders correctly should
   outscore one that produces clean HTML that renders wrong.
2. **Produce a continuous score in [0, 1]** — Harbor needs a single
   scalar reward; RL needs gradients of meaning, not pass/fail.
3. **Be monotone in visual fidelity** — higher score must correspond
   to a more faithful replica when a human looks at the pair.
4. **Resist trivial gaming** — embedding the GT screenshot in
   `<img>`, dumping raw text, blank submissions all score near 0.

We accept that absolute scores are noisier than relative rankings —
what matters most is **higher score → more faithful replication**, with
human-verifiable consistency.

---

## 2. The v5.1 Block-Match grader

> Implementation: `src/_blockmatch_grade.py`. Baked into every task as
> `tests/grade.py` by `src/generate.py::build_task_dir`. The companion
> `src/_container_grade.py` ships alongside as a sibling helper module
> (provides CIE-Lab conversion, CIEDE2000, TreeBLEU, coverage gate).

### 2.1 Architecture: match-then-diff

Every page-pair goes through:

```
1. Render — playwright at desktop (1280×800).
            Extract per-element records (tag, bbox, font, colour,
            effective_bg, border, ...) via in-page JS.

2. Anchor — keep elements with own immediate text ≥ 4 chars
            (text leaves with stable identity across reproductions).

3. Match  — Sørensen-Dice similarity on character bigrams of
            (gt_anchor.text, agent_anchor.text); Hungarian
            (Jonker-Volgenant) one-to-one assignment maximising
            total similarity; pairs below 0.5 dropped.

4. Diff   — six per-pair sub-scores on matched pairs, three
            page-level signals on the whole page.

5. Aggregate — weighted sum across pairs → page combined;
               mean across pages → trial score ∈ [0, 1].
```

### 2.2 Signal weights

```
WEIGHTS = {
    "bm_position":  0.15,   # Δx, Δy on viewport-normalised centroids
    "bm_text":      0.10,   # char-bigram Dice on matched-pair text
    "bm_color":     0.15,   # 0.6 × text-CIEDE2000 + 0.4 × bg-CIEDE2000
    "bm_font":      0.10,   # family (tiered) + size (ratio) + weight (ratio)
    "bm_border":    0.05,   # radius + style + shadow
    "bm_size":      0.05,   # min(area)/max(area)
    "bm_recall":    0.10,   # matched_area / total_GT_area
    "tree_bleu":    0.20,   # 1-height DOM subtree multiset recall
    "visual_ssim":  0.10,   # grayscale SSIM on screenshots
}
```

Sum = 1.000. Output ∈ [0, 1] by construction.

Weights were chosen by:

- Higher weight on signals with high std across trials (they
  discriminate runs). Empirically: `bm_position` std = 0.235 →
  largest weight slot at 0.15.
- High weight on `tree_bleu` (0.20) because it's the only signal
  that breaks ties on tasks where Opus produces near-identical
  copy — DOM nesting differences become the discriminator.
- Lowest weight on `bm_border` (0.05) and `bm_size` (0.05) because
  std is small (modern web borders converge; size is bounded by
  viewport).
- `bm_recall` and `visual_ssim` at 0.10 each — orthogonal to the
  per-pair signals (catch sparse output and pixel-level differences
  the per-pair scoring misses).

### 2.3 Effective background colour

Most elements have transparent backgrounds and inherit visually from
their container. Naive `getComputedStyle(el).backgroundColor` returns
`rgba(0,0,0,0)` for these, which would match transparent-on-white with
transparent-on-black at 1.0 — wrong.

The extractor walks the parent chain from each element to find the
**nearest non-transparent ancestor's bg colour**:

```javascript
function effectiveBg(el) {
  let cur = el;
  while (cur) {
    const s = getComputedStyle(cur);
    const bg = s.backgroundColor || '';
    const m = bg.match(/rgba?\(([^)]+)\)/);
    if (m) {
      const parts = m[1].split(',').map(x => parseFloat(x.trim()));
      const alpha = parts.length >= 4 ? parts[3] : 1.0;
      if (alpha > 0.05) return bg;
    }
    cur = cur.parentElement;
  }
  return 'rgb(255, 255, 255)';
}
```

Without this, dark-themed agent reproductions of light GTs (or vice
versa) would not be penalised on bg colour for any element that
inherits its background. With it, the page-bg flip drops `bm_color`
to ~0.4 across all matched pairs.

### 2.4 Colour distance: CIEDE2000 in CIE Lab

`bm_color` uses CIEDE2000 (perceptually-uniform colour distance) on
text colour and effective bg, weighted 0.6/0.4. A predecessor v3
grader used HSV-cosine on dominant-colour histograms; on dark-themed
tasks the histogram bin alignment between near-black and near-grey
collapsed the score bimodally to ~0 or ~1. CIEDE2000 in Lab space
avoids this — it's perceptually meaningful and continuous everywhere.

### 2.5 Page-level signals

Three signals don't fit the per-pair framework but catch real failure
modes:

- **bm_recall** — matched-area / total-GT-area. Catches "agent
  reproduced 5 of GT's 50 elements faithfully." Without this, a
  sparse reproduction of a dense page can score well on the per-pair
  signals (the matched ones look right) and miss the obvious gap.
- **tree_bleu** — multiset recall of (parent_tag, sorted_children) DOM
  subtrees. From WebCode2M (WWW 2025). Catches "right text wrong
  nesting" — `<button>Save</button>` matches `<a>Save</a>` on text
  but not on structure.
- **visual_ssim** — grayscale SSIM on the rendered screenshots. The
  high-level "looks similar" head — catches whole-page differences
  (background regime, hero photo presence, dark vs light flips) that
  no per-element signal sees.

---

## 3. Anti-gaming

Trivial cheats and why they don't work:

| Cheat | Why it fails |
|---|---|
| Embed GT screenshot in `<img>` | bm_text=0 (no text leaves), bm_recall≈0, tree_bleu≈0; visual_ssim ~0.7 from pixel match dragged to ~0.07 by 0.10 weight |
| Submit a blank page | Anchor list empty → 0 across the board |
| Submit raw GT text dump | bm_text high but bm_position/font/color/size all 0; tree_bleu near 0 |
| Submit only the index page | n_pages mean still includes 0-scoring missing pages |

The architecture caps trivially-gameable scores at ~0.10 (the SSIM
weight ceiling alone), well below any real reproduction.

---

## 4. Calibration approach

The v5.1 grader was validated empirically rather than via a formal
4-step protocol:

1. **Oracle check** — running the grader on `(GT, GT)` pairs scores
   ~0.996 (the small gap is sub-pixel playwright jitter on
   centroid positions and matched-pair font-size ratios).
2. **No-submission check** — empty agent output → 0.000 score
   (validated on `saas_minimal-001__Fkc9r6q` in the production run).
3. **Best-vs-worst inspection** — on every one of the 11 final tasks,
   the highest-scoring run was visibly more faithful to GT than the
   lowest-scoring run by inspection. See `report_figures/v51_pairs.html`
   for the full gallery; no reversed pairs were observed.
4. **Cross-grader correlation** — Spearman ρ vs the v3.4 predecessor
   was 0.733 on the 6 tasks where we had paired data
   (`report_figures/grader_correlation.png`). Strong correlation
   confirms the new grader hasn't gone off the rails on rank ordering;
   the difference (slope 0.91, +0.12 lift) reflects v5.1 being more
   generous on partial reproductions.

---

## 5. Known limitations

Detailed in [REPORT.md §5](REPORT.md#5-grader-shortcomings):

1. **Spatial fidelity is centroid-only** — no rotation, perspective, or
   aspect-ratio comparison.
2. **No image-content comparison** — `<img>` element area is matched
   but pixel content isn't.
3. **Modal verifier instability on long tasks** — 18% of 7-page trials
   stalled in the production eval (Modal scheduling, not grader
   correctness).
4. **No human-rated calibration anchor** — correlation evidence is
   from inspection, not ≥30 human triplets.
5. **Single viewport** — desktop only; mobile responsiveness regressions
   go uncaught.
6. **Anti-gaming is by construction, not empirical** — trivial cheats
   weren't run as live agents.

---

## 6. Why this design vs alternatives

### Bbox-IoU on whole-page DOM dumps (rejected)

The natural baseline. Doesn't work because most agent-produced elements
don't have stable bbox-equivalents in the GT — every element gets its
own random offset, and IoU averaged across all of them is ~0.2 even
on faithful reproductions. Design2Code (Stanford NAACL 2024)
documented this and proposed text-anchored matching, which we adopted.

### DINO / CLIP / LPIPS visual similarity (rejected)

Tempting but two failure modes:
1. **Black-box.** "Why did this trial score 0.4?" has no answer.
2. **Rewards style mimicry over structural fidelity.** A modern-
   looking site with no relation to GT can score similarly to a
   faithful reproduction.

### Hungarian matching on bbox positions (rejected)

Considered as a fallback for elements without text. Drops the global-
optimality guarantee Hungarian normally provides — bbox similarity is
non-monotone in the sense matters here (two elements at the same
centroid but different sizes are not "more matched" than two at
different centroids and same size). We dropped it; non-text elements
are caught by `tree_bleu` (which doesn't need positional alignment).

### Layout-as-grid rasterisation (rejected after trying)

A v3.2 predecessor scored a 32×32 grid mask of "does each cell
contain ≥1 visible element" between GT and agent. Worked but added
no signal beyond what `bm_recall` + `visual_ssim` already provided.
Removed in v4.

### OCR text comparison (rejected)

Initial v0 used OCR on screenshots to get text to compare. Replaced
with DOM `textContent` extraction in v1 — same signal, deterministic
(OCR misreads on rendered fonts are non-trivial and added noise).

---

## 7. Reasoning trail (chronological)

| Date | Version | Key change |
|---|---|---|
| 2026-05-21 | v3 | First trustworthy grader — 5 signals (layout/visual/component/text/style), accepted as v1 baseline after 4-step calibration on 10 D2C tasks |
| 2026-05-22 | v3.2 | Hybrid layout score (40% per-tag soft IoU + 60% multi-resolution grid) |
| 2026-05-22 | v3.3 | Adversarial gates on visual/style/text — blank/junk pages now near 0 |
| 2026-05-22 | v3.4 | Mobile viewport pass added (0.7 desktop / 0.3 mobile) |
| 2026-05-22 | v4 | HSV → CIEDE2000 (fixes bimodal style on dark themes); add TreeBLEU |
| 2026-05-23 | v5 | Block-Match architecture: text-anchored Hungarian matching + 6 per-pair sub-scores + 3 page-level signals. Total signals: 9 |
| 2026-05-23 | v5.1 (current) | Effective-background-colour ancestor walk (closes body-bg-flip gap) |

For the deeper version-by-version reasoning (each iteration's
motivating problem and what we measured), see git history of this
file before commit `90b24a9` and the deleted `_archive/` folder.

---

## 8. Future work

- **Image-content comparison.** SSIM or DINO per `<img>` element to
  catch wrong-image-but-right-size cases.
- **Aspect-ratio and rotation.** Add a sub-score on `bm_size` that
  compares (w/h) ratio, not just total area.
- **Multi-viewport.** Bring back desktop+mobile aggregation from v3.4.
- **Live adversarial validation.** Run the trivial-cheat agents (GT
  embed, blank, text dump) and confirm scores are in the expected
  bands.
- **Human-rated calibration anchor.** ≥30 triplet votes (A vs B vs
  GT, "which agent looks more like GT") for a quantitative
  human-agreement number.
