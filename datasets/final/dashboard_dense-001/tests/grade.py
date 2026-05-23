"""In-container grader for the web-design RL task — v4 (6 signals).

Runs inside the Harbor verifier (default: shared with the agent's container).
Reads the agent's HTML/CSS from /app/, screenshots them with playwright in
the same chromium that screenshots the ground truth (so visual SSIM is
apples-to-apples). Five signals are computed from the **rendered page**;
TreeBLEU is computed from the raw HTML.

The six signals (weights):

  Layout         (0.25) — for each "structurally significant" tag (nav,
                          h1, form, …), greedy-match agent bboxes to GT
                          bboxes, average IoU, weighted by tag importance.
                          Catches "right elements, wrong arrangement."
  Visual         (0.20) — SSIM on grayscale-resized 640×400 screenshots.
                          Catches pixel-level placement, font, rendering.
  Component      (0.05) — weighted multiset Jaccard over visible tag
                          names (nav=1.5, div=0.5). Substantially
                          downweighted in v4 from v3's 0.20: Spearman
                          correlation analysis on the v3.4 90-trial set
                          showed component is 0.82-correlated with the
                          new tree_bleu and has the lowest within-set
                          std (0.049) of any signal. Kept at 0.05 for
                          diagnostic value (catches "agent omitted the
                          <nav> entirely") rather than 0.00.
  Text           (0.15) — weighted F1 over `innerText` tokens, where each
                          token is weighted by the importance of its
                          parent tag (h1=3.0, button=2.0, p=1.0). Catches
                          "wrong headline" without being dominated by
                          filler-word matches.
  Style          (0.10) — rank-aligned CIEDE2000 in CIE Lab on the top-5
                          dominant pixel colors of each screenshot, weighted
                          by min(GT_weight, agent_weight). Replaces v3's
                          HSV-cosine which had a bimodal-binning artifact
                          on near-monochrome (dark/light) regimes — see
                          GRADER.md §7. Field name kept "style" for
                          back-compat with reward.json consumers; the
                          semantic is "color-palette match."
  TreeBLEU       (0.25) — recall of 1-height DOM subtrees (parent_tag,
                          sorted_tuple_of_child_tags) between agent HTML
                          and GT HTML. Catches "agent built a thin DOM"
                          even when the rendered output looks plausible.
                          Inspired by WebCode2M (Gui et al., WWW 2025).
                          Highest weight among new signals because it is
                          the only signal that produces meaningful spread
                          on tasks where v3.4 had collapsed to ~0.05
                          variance across 10 agents (ecom_pastel,
                          pricing_dark, restaurant_photo).

Combined: weighted sum, [0, 1]. Oracle (byte-identical reproduction) → 1.0.
Empty/garbage agent → 0.0.

reward.json is flat scalars only (Harbor schema). Per-page subscores plus
the missing/extra page lists go to diagnostics.json.

See GRADER.md for the design history.
"""
from __future__ import annotations

import json
import re
import sys
import traceback
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from bs4 import BeautifulSoup
from PIL import Image
from playwright.sync_api import sync_playwright
from skimage.metrics import structural_similarity as ssim


APP_DIR = Path("/app")
TESTS_GT_DIR = Path("/tests/ground_truth")
REWARD_DIR = Path("/logs/verifier")
VIEWPORT = {"width": 1280, "height": 800}   # back-compat default

# Viewports we score at, and how much each contributes to the per-page
# score. Desktop dominates because the brief and the synthesis prompts
# both target desktop primarily, but mobile contribution catches
# responsiveness regressions (no `<meta viewport>`, hardcoded widths,
# missing media queries, etc.). Set to {"desktop": 1.0} to disable mobile.
VIEWPORTS: Dict[str, Dict[str, int]] = {
    "desktop": {"width": 1280, "height":  800},
    "mobile":  {"width":  390, "height":  844},
}
VIEWPORT_WEIGHTS: Dict[str, float] = {
    "desktop": 0.70,
    "mobile":  0.30,
}

WEIGHTS = {
    "layout":    0.25,   # was 0.30 in v3.4
    "visual":    0.20,   # was 0.25 in v3.4
    "component": 0.05,   # was 0.20 — Spearman 0.82 with tree_bleu on the v3.4 90-trial set;
                         #   lowest within-set std (0.049). Kept at 0.05 for diagnostics
                         #   (catches "agent omitted entire <nav>") rather than 0.00.
    "text":      0.15,   # unchanged — does real discriminative work (std 0.17, ρ=0.71 with baseline)
    "style":     0.10,   # weight unchanged; v3.4's HSV-cosine swapped for rank-aligned CIEDE2000
    "tree_bleu": 0.25,   # new — only signal that breaks ties on low-spread tasks
                         #   (ecom_pastel std 0.06 vs baseline 0.01 = 5.2× more spread).
}

# Importance weights used by component-recall and layout. Hand-authored from
# common web-page anatomy. Unlisted tags get a low default (0.5) so missing
# them doesn't dominate the score.
COMPONENT_WEIGHT: Dict[str, float] = {
    # Page chrome
    "nav": 1.5, "header": 1.5, "footer": 1.0, "main": 1.2,
    # Major content regions
    "section": 1.0, "article": 1.0, "aside": 0.8,
    # Headings
    "h1": 1.5, "h2": 1.2, "h3": 1.0, "h4": 0.8, "h5": 0.6, "h6": 0.6,
    # Interactive
    "button": 1.2, "form": 1.3,
    "input": 1.1, "select": 1.1, "textarea": 1.1,
    "label": 0.8, "a": 0.8,
    # Media
    "img": 1.0, "video": 1.2, "svg": 0.8, "canvas": 0.8,
    # Tabular / lists
    "table": 1.3, "thead": 0.6, "tbody": 0.6, "tr": 0.6,
    "td": 0.6, "th": 0.8,
    "ul": 1.0, "ol": 1.0, "li": 0.7,
    "dl": 0.8, "dt": 0.6, "dd": 0.6,
    # Generic / often noise
    "div": 0.5, "span": 0.4, "p": 0.8, "br": 0.2, "hr": 0.4,
    # Other text-flavor tags
    "strong": 0.6, "em": 0.6, "b": 0.5, "i": 0.5, "small": 0.4,
}

DEFAULT_COMPONENT_WEIGHT = 0.5

# Importance weights for text by parent tag. Headlines and CTA text matter
# more than body or filler text.
TEXT_WEIGHT: Dict[str, float] = {
    "h1": 3.0, "h2": 2.0, "h3": 1.5, "h4": 1.2, "h5": 1.0, "h6": 1.0,
    "button": 2.0,
    "label": 1.2,
    "th": 1.2, "td": 1.0,
    "a": 1.0, "li": 1.0, "p": 1.0, "blockquote": 1.0,
    "strong": 1.1, "em": 1.0,
    "span": 0.7, "div": 0.7, "small": 0.5,
}

DEFAULT_TEXT_WEIGHT = 1.0

# Tags worth comparing positions for. Filtered to reduce noise from huge
# counts of <span> and <div>. (component-recall already covers raw counts.)
LAYOUT_TAGS = {
    "nav", "header", "footer", "main", "section", "article", "aside",
    "h1", "h2", "h3",
    "form", "table", "ul", "ol",
    "img", "button",
}


# ---------------------------------------------------------------------------
# Per-page rendered artifact: screenshot + visible items (bboxes) +
# text segments tagged by parent element.
# ---------------------------------------------------------------------------


@dataclass
class RenderedPage:
    name: str
    png: Path
    visible_items: List[Dict]          # [{tag, x, y, w, h}, ...]
    text_segments: List[Dict]          # [{tag, text}, ...]
    html: str = ""                     # raw source HTML (for TreeBLEU)


# JS run in-page after load. Returns:
#   items:         visible elements with bounding boxes
#   text_segments: visible text nodes tagged with their parent element name
# "Visible" = rendered with non-zero bbox, not display:none, not
# visibility:hidden, opacity > 0, and overlapping the positive coordinate
# plane (catches off-screen tricks at -9999px).
_VISIBILITY_JS = """
() => {
  const items = [];
  const text_segments = [];

  // First pass: visible elements with bboxes (for layout + component-recall).
  const all = document.querySelectorAll('*');
  for (const el of all) {
    const rect = el.getBoundingClientRect();
    if (!(rect.width > 0 && rect.height > 0)) continue;
    if (!(rect.right > 0 && rect.bottom > 0)) continue;
    const s = getComputedStyle(el);
    if (s.display === 'none') continue;
    if (s.visibility === 'hidden') continue;
    const op = parseFloat(s.opacity || '1');
    if (!(op > 0)) continue;
    items.push({
      tag: el.tagName.toLowerCase(),
      x: rect.left, y: rect.top, w: rect.width, h: rect.height,
    });
  }

  // Second pass: visible text segmented by parent tag (for text score).
  function walk(node, parentTag) {
    if (node.nodeType === 3) {
      const t = (node.nodeValue || '').trim();
      if (t) text_segments.push({ tag: parentTag, text: t });
      return;
    }
    if (node.nodeType !== 1) return;
    const tag = node.tagName.toLowerCase();
    if (tag === 'script' || tag === 'style' || tag === 'noscript') return;
    const s = getComputedStyle(node);
    if (s.display === 'none') return;
    if (s.visibility === 'hidden') return;
    const op = parseFloat(s.opacity || '1');
    if (!(op > 0)) return;
    for (const child of node.childNodes) walk(child, tag);
  }
  if (document.body) walk(document.body, 'body');

  return { items: items, text_segments: text_segments };
}
"""


def _render_pages(html_dir: Path, screenshot_out_dir: Path,
                  viewport: Dict[str, int] = None) -> Dict[str, RenderedPage]:
    """Screenshot every .html in ``html_dir`` and collect visibility data
    via in-page JS. One playwright session, one page-load per file.

    ``viewport`` selects the rendering width/height (defaults to the
    1280×800 desktop viewport for back-compat).

    Uses ``wait_until="load"`` because pages are served as ``file://`` URLs
    with no network activity to settle on.
    """
    if viewport is None:
        viewport = VIEWPORT
    screenshot_out_dir.mkdir(parents=True, exist_ok=True)
    htmls = sorted(html_dir.glob("*.html"))
    out: Dict[str, RenderedPage] = {}
    if not htmls:
        return out
    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        try:
            context = browser.new_context(
                viewport=viewport, device_scale_factor=1
            )
            page = context.new_page()
            for html in htmls:
                page.goto(html.as_uri(), wait_until="load", timeout=15000)
                page.wait_for_timeout(200)
                visibility = page.evaluate(_VISIBILITY_JS)
                out_png = screenshot_out_dir / (html.stem + ".png")
                page.screenshot(path=str(out_png), full_page=True)
                out[html.stem] = RenderedPage(
                    name=html.stem,
                    png=out_png,
                    visible_items=visibility.get("items", []),
                    text_segments=visibility.get("text_segments", []),
                    html=html.read_text(errors="replace"),
                )
        finally:
            browser.close()
    return out


# ---------------------------------------------------------------------------
# Signal 1: Visual — SSIM on grayscale-resized screenshots.
# ---------------------------------------------------------------------------


def _resized(path: Path, size=(640, 400)) -> np.ndarray:
    return np.asarray(Image.open(path).convert("L").resize(size))


def _content_coverage(path: Path, near_white_threshold: int = 240) -> float:
    """Fraction of pixels that are NOT near-white in the rendered screenshot.

    Used to detect "the agent rendered an essentially blank page." A page
    that's 99% white pixels is content-empty even if its few dark pixels
    happen to align with GT (which is what SSIM gets fooled by).
    """
    img = np.asarray(Image.open(path).convert("L"))
    return float((img < near_white_threshold).mean())


# Below this fraction of GT's content coverage, visual/style scores are
# scaled linearly toward 0. Above the threshold, no penalty. Catches
# blank/junk pages without unfairly penalising real agents whose
# screenshots are 60-90% as dense as GT.
_COVERAGE_GATE_THRESHOLD = 0.20


def _coverage_gate(gt_png: Path, agent_png: Path) -> float:
    """Multiplier in [0, 1] applied to visual and style.

    Returns 1.0 when agent's content coverage is at least 20% of GT's
    (essentially: "the agent rendered SOMETHING"); scales linearly toward
    0 below that. Blank agent → near-zero multiplier; well-formed agent →
    multiplier 1.0 even if coverage is moderately lower than GT.
    """
    gt_cov = _content_coverage(gt_png)
    ag_cov = _content_coverage(agent_png)
    if gt_cov <= 0:
        return 1.0
    ratio = ag_cov / gt_cov
    return float(min(1.0, ratio / _COVERAGE_GATE_THRESHOLD))


def _visual_similarity(gt_png: Path, agent_png: Path) -> float:
    """SSIM with a content-coverage gate.

    Raw SSIM on grayscale-resized 640×400 has a known weakness: any two
    mostly-white pages score ~0.7-0.8 because SSIM windows mostly land
    on shared whitespace. The coverage gate caps SSIM whenever the agent
    has rendered significantly less content than GT, eliminating the
    "blank page farms 0.78 from background match" failure mode.
    """
    a = _resized(gt_png)
    b = _resized(agent_png)
    score = ssim(a, b, data_range=255)
    raw = float(max(0.0, min(1.0, score)))
    return float(raw * _coverage_gate(gt_png, agent_png))


# ---------------------------------------------------------------------------
# Signal 2: Layout — per-tag bbox IoU, greedy-matched, importance-weighted.
# ---------------------------------------------------------------------------


def _iou(a: Dict, b: Dict) -> float:
    ax2, ay2 = a["x"] + a["w"], a["y"] + a["h"]
    bx2, by2 = b["x"] + b["w"], b["y"] + b["h"]
    ix1, iy1 = max(a["x"], b["x"]), max(a["y"], b["y"])
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union > 0 else 0.0


# Soft-IoU fallback parameters. See GRADER.md §"Soft-IoU (v3.1)".
_SOFT_IOU_CAP = 0.40           # max score from proximity fallback alone
_SOFT_IOU_RADIUS = 0.50        # 0 score when centroid > this fraction of page diag


def _soft_iou(a: Dict, b: Dict, page_w: float, page_h: float) -> float:
    """IoU with a centroid-distance fallback when bboxes don't overlap.

    Industry observation: hard IoU is too strict for "same conceptual
    element, slightly different position" — it falls to 0 abruptly when
    bboxes stop overlapping, even if elements are clearly the same kind
    of section in the same general region of the page. We add a soft
    fallback bounded at 0.4 (always less than any positive overlap) so:

      - overlapping bboxes  → IoU directly (unchanged from v3)
      - non-overlapping but co-located, similar size → ~0.3
      - non-overlapping, far OR very different size  → 0

    This is closer to GIoU/DIoU semantics from object-detection lit but
    keeps it simple and bounded so the perturbation discrimination from
    v3 doesn't get washed out.
    """
    iou_val = _iou(a, b)
    if iou_val > 0:
        return iou_val
    # No overlap. Compute proximity-based fallback.
    if page_w <= 0 or page_h <= 0:
        return 0.0
    cx_a, cy_a = a["x"] + a["w"] / 2, a["y"] + a["h"] / 2
    cx_b, cy_b = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
    dx = abs(cx_a - cx_b) / page_w
    dy = abs(cy_a - cy_b) / page_h
    centroid_dist = (dx * dx + dy * dy) ** 0.5
    if centroid_dist >= _SOFT_IOU_RADIUS:
        return 0.0
    proximity = 1.0 - centroid_dist / _SOFT_IOU_RADIUS
    area_a = a["w"] * a["h"]
    area_b = b["w"] * b["h"]
    if max(area_a, area_b) <= 0:
        return 0.0
    size_ratio = min(area_a, area_b) / max(area_a, area_b)
    return proximity * size_ratio * _SOFT_IOU_CAP


def _greedy_match_iou(gts: List[Dict], ags: List[Dict],
                       page_w: float, page_h: float) -> List[float]:
    """Greedy 1-to-1 soft-IoU-maximising matching. Returns matched scores.

    Sort GT instances by area descending so bigger elements claim their
    best counterpart first — gives stable, sensible matches when sizes
    differ. Unmatched on either side don't appear in the return.
    """
    used_ag: set = set()
    matched: List[float] = []
    gt_sorted = sorted(
        range(len(gts)), key=lambda i: -gts[i]["w"] * gts[i]["h"]
    )
    for gi in gt_sorted:
        g = gts[gi]
        best_idx, best_score = -1, 0.0
        for j, a in enumerate(ags):
            if j in used_ag:
                continue
            score = _soft_iou(g, a, page_w, page_h)
            if score > best_score:
                best_score = score
                best_idx = j
        if best_idx >= 0 and best_score > 0:
            used_ag.add(best_idx)
            matched.append(best_score)
    return matched


def _page_dims(items: List[Dict],
               viewport_w: float = None,
               viewport_h: float = None) -> Tuple[float, float]:
    """Estimated page extent for normalising centroid distances.

    Width = the viewport width (always the layout width). Height = the
    document height (taken as max y+h across visible items, or viewport
    height if the page fits in the viewport).

    Defaults preserve the back-compat 1280×800 viewport.
    """
    if viewport_w is None:
        viewport_w = VIEWPORT["width"]
    if viewport_h is None:
        viewport_h = VIEWPORT["height"]
    page_w = float(viewport_w)
    if items:
        max_y = max(it["y"] + it["h"] for it in items)
        page_h = max(float(viewport_h), float(max_y))
    else:
        page_h = float(viewport_h)
    return page_w, page_h


def _layout_score_iou(gt_items: List[Dict], agent_items: List[Dict],
                      viewport_w: float = None,
                      viewport_h: float = None) -> float:
    """Per-tag bbox-match (soft IoU), weighted by tag importance.

    Catches fine-grained position differences. For each layout-significant
    tag class, greedy-matches by soft-IoU and averages with a count-mismatch
    penalty (sum/max(n_gt, n_ag)).

    Tends to be strict — penalises tag substitution heavily (e.g. agent
    used <div> where GT used <nav> → score 0 for the nav tag, even if
    visually the same).
    """
    by_tag_gt: Dict[str, List[Dict]] = {}
    by_tag_ag: Dict[str, List[Dict]] = {}
    for it in gt_items:
        if it["tag"] in LAYOUT_TAGS:
            by_tag_gt.setdefault(it["tag"], []).append(it)
    for it in agent_items:
        if it["tag"] in LAYOUT_TAGS:
            by_tag_ag.setdefault(it["tag"], []).append(it)

    tags = set(by_tag_gt) | set(by_tag_ag)
    if not tags:
        return 1.0

    gt_w, gt_h = _page_dims(gt_items, viewport_w, viewport_h)
    ag_w, ag_h = _page_dims(agent_items, viewport_w, viewport_h)
    page_w = max(gt_w, ag_w)
    page_h = max(gt_h, ag_h)

    total_w = 0.0
    total_score = 0.0
    for tag in tags:
        w = COMPONENT_WEIGHT.get(tag, DEFAULT_COMPONENT_WEIGHT)
        gts = by_tag_gt.get(tag, [])
        ags = by_tag_ag.get(tag, [])
        if not gts and not ags:
            continue
        if not gts or not ags:
            tag_score = 0.0
        else:
            ious = _greedy_match_iou(gts, ags, page_w, page_h)
            denom = max(len(gts), len(ags))
            tag_score = sum(ious) / denom if denom > 0 else 0.0
        total_score += w * tag_score
        total_w += w

    return total_score / total_w if total_w > 0 else 0.0


# Multi-resolution grids for the layout-grid signal. Coarse-to-fine: each
# resolution averaged with equal weight. Sizes empirically chosen for
# 1280-wide viewport with 1-3x tall full pages.
_LAYOUT_GRIDS = [(4, 8), (8, 16), (16, 32)]


def _rasterize_grid(items: List[Dict], page_w: float, page_h: float,
                    grid_w: int, grid_h: int,
                    tag_filter: bool = True) -> np.ndarray:
    """Render visible elements onto a ``grid_h × grid_w`` count grid.

    Each cell counts elements that overlap it. With ``tag_filter=True``,
    only layout-significant elements (nav, h1, etc.) are rasterized; with
    False, all visible elements.
    """
    grid = np.zeros((grid_h, grid_w))
    if page_w <= 0 or page_h <= 0:
        return grid
    for it in items:
        if tag_filter and it["tag"] not in LAYOUT_TAGS:
            continue
        cx1 = int(it["x"] / page_w * grid_w)
        cy1 = int(it["y"] / page_h * grid_h)
        cx2 = int((it["x"] + it["w"]) / page_w * grid_w)
        cy2 = int((it["y"] + it["h"]) / page_h * grid_h)
        for cy in range(max(0, cy1), min(grid_h, cy2 + 1)):
            for cx in range(max(0, cx1), min(grid_w, cx2 + 1)):
                grid[cy, cx] += 1
    return grid


def _layout_score_grid(gt_items: List[Dict], agent_items: List[Dict],
                       viewport_w: float = None,
                       viewport_h: float = None) -> float:
    """Multi-resolution layout-grid cosine similarity.

    Rasterises elements onto coarse grids (4×8, 8×16, 16×32) and computes
    cosine similarity per resolution, then averages. Inherently smooth —
    small position shifts move elements between adjacent cells, so the
    score doesn't crash to 0 on positional offsets.

    Captures "do similar regions of the page have the same kinds of
    stuff?" — the granularity at which a human reads a layout. Pairs
    well with _layout_score_iou which catches the fine positioning.
    """
    gt_w, gt_h = _page_dims(gt_items, viewport_w, viewport_h)
    ag_w, ag_h = _page_dims(agent_items, viewport_w, viewport_h)
    page_w = max(gt_w, ag_w)
    page_h = max(gt_h, ag_h)
    sims: List[float] = []
    for gw, gh in _LAYOUT_GRIDS:
        g = _rasterize_grid(gt_items, page_w, page_h, gw, gh)
        a = _rasterize_grid(agent_items, page_w, page_h, gw, gh)
        gn = float(np.linalg.norm(g))
        an = float(np.linalg.norm(a))
        if gn == 0 and an == 0:
            sims.append(1.0)
            continue
        if gn == 0 or an == 0:
            sims.append(0.0)
            continue
        sims.append(max(0.0, min(1.0, float(np.dot(g.flatten(), a.flatten()) / (gn * an)))))
    return float(np.mean(sims)) if sims else 0.0


# Weights inside the combined layout score. The IoU half catches "did you
# put the nav at exactly y=0", the grid half catches "is the page roughly
# the same regions of stuff." Combined gives a layout score that doesn't
# crash to 0.2 when the agent uses different DOM tags but matches visually.
_LAYOUT_IOU_WEIGHT = 0.40
_LAYOUT_GRID_WEIGHT = 0.60


def _layout_score(gt_items: List[Dict], agent_items: List[Dict],
                  viewport_w: float = None,
                  viewport_h: float = None) -> float:
    """Hybrid layout score: per-tag soft-IoU + multi-resolution grid cosine.

    See GRADER.md §"Hybrid layout (v3.2)" for the why. Roughly:
    - IoU half (40%) catches fine-grained positioning of named elements.
    - Grid half (60%) catches "are the same regions of the page filled
      with similar stuff" — the granularity at which humans read layout.

    Both are bounded in [0, 1]. Combined is bounded in [0, 1]. Oracle
    (byte-identical reproduction) → both → 1.0. Empty agent → both → 0.0.
    """
    iou_score = _layout_score_iou(gt_items, agent_items, viewport_w, viewport_h)
    grid_score = _layout_score_grid(gt_items, agent_items, viewport_w, viewport_h)
    return float(
        _LAYOUT_IOU_WEIGHT * iou_score
        + _LAYOUT_GRID_WEIGHT * grid_score
    )


# ---------------------------------------------------------------------------
# Signal 3: Component recall — weighted multiset Jaccard over visible tags.
# ---------------------------------------------------------------------------


def _component_recall(gt_tags: List[str], agent_tags: List[str]) -> float:
    a = Counter(gt_tags)
    b = Counter(agent_tags)
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    weighted_diff = 0.0
    weighted_total = 0.0
    for k in keys:
        w = COMPONENT_WEIGHT.get(k, DEFAULT_COMPONENT_WEIGHT)
        weighted_diff += w * abs(a.get(k, 0) - b.get(k, 0))
        weighted_total += w * (a.get(k, 0) + b.get(k, 0))
    if weighted_total == 0:
        return 0.0
    return float(max(0.0, 1.0 - weighted_diff / weighted_total))


# ---------------------------------------------------------------------------
# Signal 4: Text — weighted F1 over visible-text tokens.
# ---------------------------------------------------------------------------


_WORD = re.compile(r"[A-Za-z0-9]+")


def _token_weights(segments: List[Dict]) -> Dict[str, float]:
    """For each unique token in the visible text, take the maximum parent-
    tag weight across all its occurrences. This way 'Pricing' appearing in
    <h1> isn't diluted by also appearing in <span>."""
    out: Dict[str, float] = {}
    for seg in segments:
        w = TEXT_WEIGHT.get(seg.get("tag", "p"), DEFAULT_TEXT_WEIGHT)
        for tok in _WORD.findall((seg.get("text") or "").lower()):
            prev = out.get(tok, 0.0)
            if w > prev:
                out[tok] = w
    return out


def _text_score(gt_segments: List[Dict], agent_segments: List[Dict]) -> float:
    """Weighted F1 over visible-text tokens, with a structural gate.

    Each token's contribution to the matched intersection is scaled by
    the ratio of its parent-tag importance weights between GT and agent.
    A token "Pricing" appearing in GT's `<h1>` (weight 3.0) but only in
    agent's `<p>` (weight 1.0) contributes ratio=0.33, not full credit.
    This stops a "text dump" agent (right words, no structure) from
    farming a high text score without producing the right elements.
    """
    gw = _token_weights(gt_segments)
    aw = _token_weights(agent_segments)
    if not gw and not aw:
        return 1.0
    if not gw or not aw:
        return 0.0
    keys = set(gw) | set(aw)
    # Weight-aware intersection: tokens count only proportionally to how
    # well their parent-tag importance matches between GT and agent.
    inter_w = 0.0
    for k in keys:
        g = gw.get(k, 0.0)
        a = aw.get(k, 0.0)
        if g <= 0 or a <= 0:
            continue
        ratio = min(g, a) / max(g, a)
        inter_w += min(g, a) * ratio
    gt_total = sum(gw.values())
    ag_total = sum(aw.values())
    if inter_w == 0 or gt_total == 0 or ag_total == 0:
        return 0.0
    precision = inter_w / ag_total
    recall = inter_w / gt_total
    if (precision + recall) == 0:
        return 0.0
    return float(2 * precision * recall / (precision + recall))


# ---------------------------------------------------------------------------
# Signal 5: Style — cosine of HSV color histograms.
# ---------------------------------------------------------------------------


# Style — CIEDE2000 perceptual color distance in CIE Lab space.
# v3 used HSV-histogram cosine, which had a known failure mode: on
# near-monochrome (dark/light) regimes, hue is numerically meaningless but
# the histogram bin still depends on it, so two visually-identical dark
# pages with bg #000000 vs #0c0c0e would land in different hue bins and
# score cosine ≈ 0. We confirmed this on splash_3d (7/9 false negatives)
# and dashboard_dense (8/10 false negatives). v4 swaps to CIEDE2000 in
# CIE Lab — perceptually uniform, no binning artifact.

def _srgb_to_lab(rgb_u8: np.ndarray) -> np.ndarray:
    """Convert (N, 3) sRGB-uint8 → (N, 3) CIE Lab. Pure numpy, D65 white."""
    rgb = rgb_u8.astype(np.float64) / 255.0
    mask = rgb > 0.04045
    lin = np.where(mask, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
    M = np.array([
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ])
    xyz = lin @ M.T / np.array([0.95047, 1.00000, 1.08883])
    eps = (6.0 / 29.0) ** 3
    kappa = (29.0 / 6.0) ** 2 / 3.0
    f = np.where(xyz > eps, np.cbrt(xyz), kappa * xyz + 4.0 / 29.0)
    L = 116.0 * f[:, 1] - 16.0
    a = 500.0 * (f[:, 0] - f[:, 1])
    b = 200.0 * (f[:, 1] - f[:, 2])
    return np.stack([L, a, b], axis=1)


def _ciede2000(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    """Element-wise CIEDE2000 between two (N, 3) CIE Lab arrays."""
    L1, a1, b1 = lab1[:, 0], lab1[:, 1], lab1[:, 2]
    L2, a2, b2 = lab2[:, 0], lab2[:, 1], lab2[:, 2]
    C1 = np.sqrt(a1 * a1 + b1 * b1)
    C2 = np.sqrt(a2 * a2 + b2 * b2)
    Cbar = (C1 + C2) / 2.0
    G = 0.5 * (1 - np.sqrt(Cbar ** 7 / (Cbar ** 7 + 25.0 ** 7 + 1e-12)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p = np.sqrt(a1p * a1p + b1 * b1)
    C2p = np.sqrt(a2p * a2p + b2 * b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp = L2 - L1
    dCp = C2p - C1p
    dhp = h2p - h1p
    dhp = np.where(dhp > 180, dhp - 360, dhp)
    dhp = np.where(dhp < -180, dhp + 360, dhp)
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp / 2.0))
    Lbarp = (L1 + L2) / 2.0
    Cbarp = (C1p + C2p) / 2.0
    hbarp = np.where(np.abs(h1p - h2p) > 180, (h1p + h2p + 360) / 2.0, (h1p + h2p) / 2.0)
    T = (1 - 0.17 * np.cos(np.radians(hbarp - 30))
         + 0.24 * np.cos(np.radians(2 * hbarp))
         + 0.32 * np.cos(np.radians(3 * hbarp + 6))
         - 0.20 * np.cos(np.radians(4 * hbarp - 63)))
    dtheta = 30 * np.exp(-(((hbarp - 275) / 25.0) ** 2))
    Rc = 2 * np.sqrt(Cbarp ** 7 / (Cbarp ** 7 + 25.0 ** 7 + 1e-12))
    Sl = 1 + (0.015 * (Lbarp - 50) ** 2) / np.sqrt(20 + (Lbarp - 50) ** 2)
    Sc = 1 + 0.045 * Cbarp
    Sh = 1 + 0.015 * Cbarp * T
    Rt = -np.sin(np.radians(2 * dtheta)) * Rc
    return np.sqrt(
        (dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2
        + Rt * (dCp / Sc) * (dHp / Sh)
    )


def _dominant_palette(path: Path, k: int = 5) -> Tuple[np.ndarray, np.ndarray]:
    """Top-k dominant sRGB colors of a screenshot, with pixel weights.
    Returns (colors[k,3] uint8, weights[k] float summing to ≤1)."""
    img = Image.open(path).convert("RGB").resize((128, 128))
    arr = np.asarray(img, dtype=np.uint8).reshape(-1, 3)
    q = (arr >> 3).astype(np.int32)         # quantize 5 bits/channel
    keys = q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2]
    counts = Counter(keys.tolist())
    total = sum(counts.values())
    cols, ws = [], []
    for key, cnt in counts.most_common(k):
        r = (key // 1024) << 3
        g = ((key // 32) % 32) << 3
        b = (key % 32) << 3
        cols.append([r, g, b])
        ws.append(cnt / total)
    return np.array(cols, dtype=np.uint8), np.array(ws, dtype=np.float64)


def _style_score(gt_png: Path, agent_png: Path) -> float:
    """Rank-aligned palette comparison in CIE Lab via CIEDE2000.

    Pair top-1 GT color with top-1 agent color (both being the dominant
    pixel color of their image), top-2 with top-2, etc. Average ΔE
    weighted by min(GT_weight, agent_weight) at each rank, then map to
    similarity in [0, 1] via 1 - mean_ΔE / 50. Multiplied by the same
    coverage gate that visual uses (so a blank agent doesn't farm style
    points by sharing whitespace with the GT).

    The rank-alignment matters: Hungarian-matching the palettes
    destroys the dominance-ordering signal — a white-bg agent vs a
    black-bg GT would otherwise pair white→white via the agent's #2
    color, hiding the failure. Rank alignment forces top-vs-top."""
    gt_p, gt_w = _dominant_palette(gt_png, k=5)
    ag_p, ag_w = _dominant_palette(agent_png, k=5)
    n = min(len(gt_p), len(ag_p))
    if n == 0:
        return 0.0
    de = _ciede2000(_srgb_to_lab(gt_p[:n]), _srgb_to_lab(ag_p[:n]))
    weights = np.minimum(gt_w[:n], ag_w[:n])
    if weights.sum() == 0:
        return 0.0
    mean_de = float(np.average(de, weights=weights))
    raw = max(0.0, 1.0 - mean_de / 50.0)
    return float(raw * _coverage_gate(gt_png, agent_png))


# ---------------------------------------------------------------------------
# Signal 6 (v4): TreeBLEU — recall of 1-height DOM subtrees.
# ---------------------------------------------------------------------------

_TREE_SKIP_TAGS = frozenset({"script", "style", "meta", "link", "br", "hr",
                              "head", "html", "noscript"})


def _one_height_subtrees(html: str) -> Counter:
    """Multiset of (parent_tag, sorted_tuple_of_child_tags) over all
    elements in the document. Skips meta/script/style/etc. so the score
    reflects content structure, not boilerplate."""
    if not html:
        return Counter()
    soup = BeautifulSoup(html, "html.parser")
    out: Counter = Counter()
    for el in soup.find_all():
        if el.name in _TREE_SKIP_TAGS:
            continue
        children = [c.name for c in el.find_all(recursive=False)
                    if c.name and c.name not in _TREE_SKIP_TAGS]
        if not children:
            continue
        out[(el.name, tuple(sorted(children)))] += 1
    return out


def _tree_bleu(gt_html: str, agent_html: str) -> float:
    """Recall of 1-height subtrees: |GT ∩ agent| / |GT|. WebCode2M (Gui
    et al., WWW 2025) reports precision over the agent; we use recall to
    penalize agents that build skeletal DOMs. Returns 0 if agent is empty;
    1 if GT is empty (degenerate task)."""
    g = _one_height_subtrees(gt_html)
    if not g:
        return 1.0 if not agent_html else 0.0
    a = _one_height_subtrees(agent_html)
    inter = sum(min(g[k], a[k]) for k in g)
    return inter / sum(g.values())


# ---------------------------------------------------------------------------
# Per-page + report dataclasses.
# ---------------------------------------------------------------------------


@dataclass
class ViewportPageScore:
    """6 sub-signals + a combined score for one page at one viewport."""
    layout: float
    visual: float
    component: float
    text: float
    style: float
    tree_bleu: float
    combined: float


@dataclass
class PageScore:
    """Per-page rollup. ``per_viewport[vp]`` has the per-viewport
    breakdowns; ``combined`` is the weighted average across viewports
    (per VIEWPORT_WEIGHTS). Top-level ``layout/visual/...`` mirror the
    desktop sub-scores so existing diagnostic tooling (analyze_layout,
    viewers) keeps working without changes."""
    name: str
    layout: float
    visual: float
    component: float
    text: float
    style: float
    tree_bleu: float
    combined: float
    per_viewport: Dict[str, ViewportPageScore] = field(default_factory=dict)


@dataclass
class GradeReport:
    score: float
    per_page: List[PageScore] = field(default_factory=list)
    missing_pages: List[str] = field(default_factory=list)
    extra_pages: List[str] = field(default_factory=list)
    error: str | None = None

    def reward_payload(self) -> Dict[str, float]:
        """Flat scalar-only payload for Harbor's reward.json schema.

        Layout: ``score`` + per-page combined + per-page per-viewport
        breakdowns. The desktop pass's individual sub-signals are also
        emitted at the top page level for back-compat with existing
        diagnostic scripts (analyze_layout, viewers).
        """
        payload: Dict[str, float] = {"score": float(self.score)}
        for p in self.per_page:
            # Combined per page (weighted across viewports)
            payload[f"{p.name}_combined"]  = float(p.combined)
            # Back-compat: desktop sub-signals at the page level
            payload[f"{p.name}_layout"]    = float(p.layout)
            payload[f"{p.name}_visual"]    = float(p.visual)
            payload[f"{p.name}_component"] = float(p.component)
            payload[f"{p.name}_text"]      = float(p.text)
            payload[f"{p.name}_style"]     = float(p.style)
            payload[f"{p.name}_tree_bleu"] = float(p.tree_bleu)
            # Per-viewport breakdowns
            for vp_name, vp_score in p.per_viewport.items():
                payload[f"{p.name}_{vp_name}_layout"]    = float(vp_score.layout)
                payload[f"{p.name}_{vp_name}_visual"]    = float(vp_score.visual)
                payload[f"{p.name}_{vp_name}_component"] = float(vp_score.component)
                payload[f"{p.name}_{vp_name}_text"]      = float(vp_score.text)
                payload[f"{p.name}_{vp_name}_style"]     = float(vp_score.style)
                payload[f"{p.name}_{vp_name}_tree_bleu"] = float(vp_score.tree_bleu)
                payload[f"{p.name}_{vp_name}_combined"]  = float(vp_score.combined)
        return payload

    def diagnostics(self) -> Dict:
        out = {
            "score": float(self.score),
            "signal_weights": dict(WEIGHTS),
            "viewport_weights": dict(VIEWPORT_WEIGHTS),
            "viewports": dict(VIEWPORTS),
            "per_page": [asdict(p) for p in self.per_page],
            "missing_pages": self.missing_pages,
            "extra_pages": self.extra_pages,
        }
        if self.error:
            out["error"] = self.error
        return out


# ---------------------------------------------------------------------------
# Top-level grade() — render at every viewport, score per viewport, combine.
# ---------------------------------------------------------------------------


def _score_one_viewport(
    gt_page: RenderedPage, agent_page: RenderedPage | None,
    viewport: Dict[str, int],
) -> ViewportPageScore:
    """Compute the 5 sub-signals + combined for one (gt_page, agent_page)
    pair at a specific viewport."""
    if agent_page is None:
        return ViewportPageScore(
            layout=0.0, visual=0.0, component=0.0,
            text=0.0, style=0.0, combined=0.0,
        )
    vw = viewport["width"]
    vh = viewport["height"]
    visual    = _visual_similarity(gt_page.png, agent_page.png)
    layout    = _layout_score(
        gt_page.visible_items, agent_page.visible_items,
        viewport_w=vw, viewport_h=vh,
    )
    component = _component_recall(
        [it["tag"] for it in gt_page.visible_items],
        [it["tag"] for it in agent_page.visible_items],
    )
    text      = _text_score(gt_page.text_segments, agent_page.text_segments)
    style     = _style_score(gt_page.png, agent_page.png)
    tree_bleu = _tree_bleu(gt_page.html, agent_page.html)
    combined = (
        WEIGHTS["layout"]    * layout
        + WEIGHTS["visual"]    * visual
        + WEIGHTS["component"] * component
        + WEIGHTS["text"]      * text
        + WEIGHTS["style"]     * style
        + WEIGHTS["tree_bleu"] * tree_bleu
    )
    return ViewportPageScore(
        layout=layout, visual=visual, component=component,
        text=text, style=style, tree_bleu=tree_bleu, combined=combined,
    )


def grade() -> GradeReport:
    if not TESTS_GT_DIR.exists():
        return GradeReport(score=0.0, error=f"Missing {TESTS_GT_DIR}")
    if not list(TESTS_GT_DIR.glob("*.html")):
        return GradeReport(score=0.0, error=f"No GT HTML files in {TESTS_GT_DIR}")

    # Render every page at every viewport. Both GT and agent are rendered
    # in the SAME chromium session per viewport so visual SSIM is
    # apples-to-apples per viewport.
    agent_by_vp: Dict[str, Dict[str, RenderedPage]] = {}
    gt_by_vp: Dict[str, Dict[str, RenderedPage]] = {}
    for vp_name, vp in VIEWPORTS.items():
        agent_by_vp[vp_name] = _render_pages(
            APP_DIR, REWARD_DIR / f"agent_screenshots_{vp_name}", vp,
        )
        gt_by_vp[vp_name] = _render_pages(
            TESTS_GT_DIR, REWARD_DIR / f"gt_screenshots_{vp_name}", vp,
        )

    # Use the first viewport (desktop) as the "canonical" page set for
    # missing/extra detection — page sets should be identical across
    # viewports anyway since they come from the same .html files.
    canonical_vp = next(iter(VIEWPORTS))
    gt_pages = gt_by_vp[canonical_vp]
    agent_pages = agent_by_vp[canonical_vp]
    missing = sorted(set(gt_pages) - set(agent_pages))
    extra = sorted(set(agent_pages) - set(gt_pages))

    per_page: List[PageScore] = []
    for name in sorted(gt_pages):
        # Score this page at every viewport
        per_vp: Dict[str, ViewportPageScore] = {}
        for vp_name, vp in VIEWPORTS.items():
            gt_page = gt_by_vp[vp_name].get(name)
            agent_page = agent_by_vp[vp_name].get(name)
            if gt_page is None:
                continue
            per_vp[vp_name] = _score_one_viewport(gt_page, agent_page, vp)

        # Weighted aggregate across viewports for the page combined score
        page_combined = sum(
            VIEWPORT_WEIGHTS.get(vp_name, 0.0) * vp_score.combined
            for vp_name, vp_score in per_vp.items()
        )

        # Back-compat top-level fields use the desktop viewport's signals
        # (which is what existing tooling expects to read from reward.json)
        desktop = per_vp.get(canonical_vp)
        if desktop is None:
            desktop = ViewportPageScore(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        per_page.append(PageScore(
            name=name,
            layout=desktop.layout, visual=desktop.visual,
            component=desktop.component, text=desktop.text,
            style=desktop.style, tree_bleu=desktop.tree_bleu,
            combined=page_combined,
            per_viewport=per_vp,
        ))

    overall = float(np.mean([p.combined for p in per_page])) if per_page else 0.0
    return GradeReport(
        score=overall,
        per_page=per_page,
        missing_pages=missing,
        extra_pages=extra,
    )


def main() -> int:
    REWARD_DIR.mkdir(parents=True, exist_ok=True)
    try:
        report = grade()
    except Exception:
        err = traceback.format_exc()
        print(err, file=sys.stderr)
        report = GradeReport(score=0.0, error=err.splitlines()[-1])

    payload = report.reward_payload()
    diagnostics = report.diagnostics()
    print(json.dumps(diagnostics, indent=2))
    (REWARD_DIR / "reward.json").write_text(json.dumps(payload, indent=2))
    (REWARD_DIR / "diagnostics.json").write_text(json.dumps(diagnostics, indent=2))
    return 1 if report.error else 0


if __name__ == "__main__":
    sys.exit(main())
