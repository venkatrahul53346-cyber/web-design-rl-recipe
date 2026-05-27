"""Experimental v5 grader — Design2Code-inspired Block-Match as the primary
signal, with TreeBLEU and visual SSIM as orthogonal supplements.

Goal: replace the v4 architecture (six independent global signals) with a
match-then-diff architecture: text-anchored Hungarian matching of DOM
elements between GT and agent, then per-pair diffs along position / text /
color / font / border / size. The match step puts like next to like before
measuring.

Signals (weights):

  Block-Match Position   (0.15) — `1 - max(|Δx|, |Δy|)` per matched pair
                                  on viewport-normalized centroids.
  Block-Match Text       (0.10) — char-bigram Sørensen-Dice per matched pair.
  Block-Match Color      (0.15) — weighted CIEDE2000 in CIE Lab on text+bg
                                  color, 0.6 × text + 0.4 × bg per pair.
  Block-Match Font       (0.10) — family (tiered) × size (spectrum) ×
                                  weight (spectrum). All continuous.
  Block-Match Border     (0.05) — radius (spectrum) + style (tiered) +
                                  shadow presence (tiered).
  Block-Match Size       (0.05) — min(area)/max(area) per pair.
  Block-Match Recall     (0.10) — area-weighted matched-block recall, the
                                  Block-Match-proper score from D2C.
  TreeBLEU               (0.20) — orthogonal: DOM 1-height subtree recall.
                                  Catches non-text elements Block-Match
                                  can't anchor (icons, decoration).
  Visual SSIM            (0.10) — orthogonal: high-level "looks similar"
                                  head, gradients/imagery Block-Match
                                  can't see.

Total = 1.00.

Every per-pair sub-score is continuous in [0,1]. Tiered fallbacks (same /
similar / different) are used only where there's no defensible numeric
distance — font family, border style, shadow presence. No 0/1 cliffs.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from scipy.optimize import linear_sum_assignment
from skimage.metrics import structural_similarity as ssim


# Reuse CIEDE2000 + tree_bleu + coverage gate from the v4 grader. Try the
# package-qualified path first (eval scripts that run from the repo root);
# fall back to a sibling import (when this file ships as `tests/grade.py`
# inside a Harbor task with `_container_grade.py` next to it).
try:
    from src._container_grade import (
        _srgb_to_lab,
        _ciede2000,
        _tree_bleu,
        _coverage_gate,
        _content_coverage,
    )
except ImportError:
    from _container_grade import (
        _srgb_to_lab,
        _ciede2000,
        _tree_bleu,
        _coverage_gate,
        _content_coverage,
    )


# ---------------------------------------------------------------------------
# Weights — sum must be 1.000.
# ---------------------------------------------------------------------------

WEIGHTS = {
    "bm_position":  0.20,
    "bm_text":      0.10,
    "bm_color":     0.15,
    "bm_font":      0.10,
    "bm_border":    0.00,
    "bm_size":      0.05,
    "bm_recall":    0.15,
    "tree_bleu":    0.20,
    "visual_ssim":  0.05,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, sum(WEIGHTS.values())


VIEWPORT = {"width": 1280, "height": 800}

# Min text length (after whitespace squash) for an element to be a Block-Match
# anchor. Below this, the signal is too noisy to align reliably.
_MIN_TEXT_LEN = 4

# Sørensen-Dice threshold: matched pairs below this are dropped.
_MATCH_THRESHOLD = 0.5


# ---------------------------------------------------------------------------
# Rich playwright extractor — per-element record with computed style.
# ---------------------------------------------------------------------------

_RICH_JS = r"""
() => {
  const out = [];
  const all = document.querySelectorAll('*');
  // v5.1: walk up the parent chain to find the nearest non-transparent
  // ancestor's backgroundColor — the "effective" visible bg an element
  // sits on. Without this, transparent leaves match each other as 1.0
  // even when their ancestral page bg differs (e.g., GT body=black,
  // agent body=white).
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

  for (const el of all) {
    const rect = el.getBoundingClientRect();
    if (!(rect.width > 0 && rect.height > 0)) continue;
    if (!(rect.right > 0 && rect.bottom > 0)) continue;
    const s = getComputedStyle(el);
    if (s.display === 'none') continue;
    if (s.visibility === 'hidden') continue;
    const op = parseFloat(s.opacity || '1');
    if (!(op > 0)) continue;

    // Extract own text (immediate text-node children only — avoids
    // counting child elements' text twice).
    let ownText = '';
    for (const c of el.childNodes) {
      if (c.nodeType === 3) ownText += (c.nodeValue || '');
    }
    ownText = ownText.replace(/\s+/g, ' ').trim();

    out.push({
      tag: el.tagName.toLowerCase(),
      x: rect.left, y: rect.top, w: rect.width, h: rect.height,
      text: ownText,
      fontFamily: s.fontFamily || '',
      fontSize: parseFloat(s.fontSize) || 0,
      fontWeight: parseInt(s.fontWeight) || 400,
      color: s.color || '',
      backgroundColor: s.backgroundColor || '',
      effectiveBackgroundColor: effectiveBg(el),
      borderRadius: parseFloat(s.borderTopLeftRadius) || 0,
      borderStyle: s.borderTopStyle || 'none',
      borderColor: s.borderTopColor || '',
      borderWidth: parseFloat(s.borderTopWidth) || 0,
      boxShadow: s.boxShadow || 'none',
    });
  }
  return out;
}
"""


@dataclass
class RichRendered:
    name: str
    png: Path
    elements: List[Dict]   # full per-element records from _RICH_JS


def render_pages_rich(html_dir: Path, screenshot_out_dir: Path,
                      viewport: Dict[str, int] = None) -> Dict[str, RichRendered]:
    """Render every .html in html_dir, screenshot, and pull the rich
    per-element list. One playwright session per call."""
    viewport = viewport or VIEWPORT
    screenshot_out_dir.mkdir(parents=True, exist_ok=True)
    out: Dict[str, RichRendered] = {}
    htmls = sorted(html_dir.glob("*.html"))
    if not htmls:
        return out
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            context = browser.new_context(viewport=viewport, device_scale_factor=1)
            page = context.new_page()
            for html in htmls:
                try:
                    page.goto(html.as_uri(), wait_until="load", timeout=15000)
                    page.wait_for_timeout(200)
                    elements = page.evaluate(_RICH_JS)
                    png = screenshot_out_dir / (html.stem + ".png")
                    page.screenshot(path=str(png), full_page=True)
                    out[html.stem] = RichRendered(
                        name=html.stem, png=png, elements=elements,
                    )
                except Exception as exc:
                    print(f"  render failed for {html.name}: {exc}")
        finally:
            browser.close()
    return out


# ---------------------------------------------------------------------------
# Color parsing — 'rgb(...)' / 'rgba(...)' string → (r,g,b,a) uint8.
# ---------------------------------------------------------------------------

_RGB_RE = re.compile(r"rgba?\(([^)]+)\)")


def parse_css_color(s: str) -> Optional[Tuple[int, int, int, float]]:
    """Parse a computed-style color string into (r, g, b, alpha).
    Alpha 0 → returned, but caller treats those as 'no color'."""
    if not s:
        return None
    m = _RGB_RE.search(s)
    if not m:
        return None
    parts = [p.strip() for p in m.group(1).split(",")]
    try:
        r = int(float(parts[0]))
        g = int(float(parts[1]))
        b = int(float(parts[2]))
        a = float(parts[3]) if len(parts) >= 4 else 1.0
    except ValueError:
        return None
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)), a)


def color_distance_de(c_a: Optional[Tuple], c_b: Optional[Tuple]) -> float:
    """Return CIEDE2000 ΔE between two parsed colors. Treat alpha=0 as
    'no color' — return None means "no opinion, skip this pair."

    For purposes of v5: if BOTH are alpha=0 (e.g., transparent bg on both
    sides), we score them as a perfect match (no information). If one is
    transparent and the other isn't, that's a meaningful difference, so we
    treat the transparent one as white (ΔE against white).
    """
    a_transp = (c_a is None) or (c_a[3] < 0.05)
    b_transp = (c_b is None) or (c_b[3] < 0.05)
    if a_transp and b_transp:
        return 0.0
    if a_transp:
        c_a = (255, 255, 255, 1.0)
    if b_transp:
        c_b = (255, 255, 255, 1.0)
    rgb_a = np.array([[c_a[0], c_a[1], c_a[2]]], dtype=np.uint8)
    rgb_b = np.array([[c_b[0], c_b[1], c_b[2]]], dtype=np.uint8)
    de = _ciede2000(_srgb_to_lab(rgb_a), _srgb_to_lab(rgb_b))[0]
    return float(de)


# ---------------------------------------------------------------------------
# Font categorization — for the tiered font-family score.
# ---------------------------------------------------------------------------

_SERIF_KEYWORDS = ("serif", "georgia", "garamond", "playfair", "merriweather",
                    "lora", "times", "cambria", "fraunces", "roboto slab",
                    "ibm plex serif", "source serif")
_MONO_KEYWORDS = ("mono", "courier", "menlo", "consolas", "fira code",
                   "jetbrains", "ibm plex mono", "sf mono", "ui-monospace")
_DISPLAY_KEYWORDS = ("display", "bebas", "abril", "righteous", "oswald",
                      "anton", "permanent marker", "lobster")


def font_category(family: str) -> str:
    """Classify a CSS font-family string into one of {sans, serif, mono,
    display}. Sans is the default catch-all."""
    f = family.lower()
    if any(k in f for k in _MONO_KEYWORDS):
        return "mono"
    if any(k in f for k in _DISPLAY_KEYWORDS):
        return "display"
    if any(k in f for k in _SERIF_KEYWORDS):
        return "serif"
    return "sans"


def font_family_score(fa: str, fb: str) -> float:
    """Tiered: same primary family (1.0) / same category (0.6) / different (0.0).
    'Same primary family' compares the first comma-separated token of each
    string, lowercased and stripped of quotes."""
    def primary(f: str) -> str:
        head = f.split(",")[0].strip().strip('"\'').lower()
        return head
    if not fa or not fb:
        return 0.0
    if primary(fa) == primary(fb):
        return 1.0
    if font_category(fa) == font_category(fb):
        return 0.6
    return 0.0


# ---------------------------------------------------------------------------
# Border / shadow scores.
# ---------------------------------------------------------------------------

def border_radius_score(ra: float, rb: float) -> float:
    """Spectrum. Both 0 → 1.0 (both square corners). One 0, other > 0 → 0.5
    (different but not opposite). Both > 0 → ratio."""
    if ra <= 0 and rb <= 0:
        return 1.0
    if ra <= 0 or rb <= 0:
        return 0.5
    return min(ra, rb) / max(ra, rb)


def border_style_score(sa: str, sb: str) -> float:
    """Tiered. Same → 1.0. Both have non-'none' borders but different
    style → 0.5. One has border, other doesn't → 0.0."""
    if not sa: sa = "none"
    if not sb: sb = "none"
    if sa == sb:
        return 1.0
    if sa != "none" and sb != "none":
        return 0.5
    return 0.0


def shadow_presence_score(sa: str, sb: str) -> float:
    """Tiered. Both have a non-'none' shadow → 1.0. Both 'none' → 1.0.
    Mismatch → 0.0."""
    has_a = bool(sa and sa.lower() != "none")
    has_b = bool(sb and sb.lower() != "none")
    if has_a == has_b:
        return 1.0
    return 0.0


def border_score(a: Dict, b: Dict) -> float:
    """Composite border signal: 0.4 × radius + 0.3 × style + 0.3 × shadow."""
    return (0.4 * border_radius_score(a.get("borderRadius", 0), b.get("borderRadius", 0))
            + 0.3 * border_style_score(a.get("borderStyle", "none"), b.get("borderStyle", "none"))
            + 0.3 * shadow_presence_score(a.get("boxShadow", "none"), b.get("boxShadow", "none")))


# ---------------------------------------------------------------------------
# Font composite.
# ---------------------------------------------------------------------------

def font_score(a: Dict, b: Dict) -> float:
    """Composite font signal: 0.4 × family (tiered) + 0.4 × size (spectrum)
    + 0.2 × weight (spectrum)."""
    fam = font_family_score(a.get("fontFamily", ""), b.get("fontFamily", ""))
    sa, sb = a.get("fontSize", 0), b.get("fontSize", 0)
    if max(sa, sb) <= 0:
        size = 1.0
    else:
        size = min(sa, sb) / max(sa, sb)
    wa, wb = a.get("fontWeight", 400), b.get("fontWeight", 400)
    weight = max(0.0, 1.0 - abs(wa - wb) / 700.0)
    return 0.4 * fam + 0.4 * size + 0.2 * weight


# ---------------------------------------------------------------------------
# Color composite — text + bg, weighted.
# ---------------------------------------------------------------------------

def color_score(a: Dict, b: Dict) -> float:
    """0.6 × text-color match + 0.4 × bg-color match.

    Match: 1 - ΔE/50, clipped to [0,1]. Higher = more similar.

    v5.1: bg uses effectiveBackgroundColor when available (the nearest
    non-transparent ancestor's bg). Falls back to literal backgroundColor
    for back-compat. This catches body-bg-flip failures that pure-leaf
    backgrounds (mostly transparent) would otherwise miss."""
    def to_match(de: Optional[float]) -> float:
        if de is None:
            return 1.0
        return max(0.0, min(1.0, 1.0 - de / 50.0))

    text_de = color_distance_de(parse_css_color(a.get("color", "")),
                                  parse_css_color(b.get("color", "")))
    a_bg = a.get("effectiveBackgroundColor") or a.get("backgroundColor", "")
    b_bg = b.get("effectiveBackgroundColor") or b.get("backgroundColor", "")
    bg_de = color_distance_de(parse_css_color(a_bg),
                                parse_css_color(b_bg))
    return 0.6 * to_match(text_de) + 0.4 * to_match(bg_de)


# ---------------------------------------------------------------------------
# Text similarity — char-bigram Sørensen-Dice (matches Design2Code).
# ---------------------------------------------------------------------------

def text_dice(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    bgs_a = Counter(a[i:i + 2] for i in range(len(a) - 1))
    bgs_b = Counter(b[i:i + 2] for i in range(len(b) - 1))
    inter = sum((bgs_a & bgs_b).values())
    return 2 * inter / (sum(bgs_a.values()) + sum(bgs_b.values()) + 1e-9)


# ---------------------------------------------------------------------------
# Position + size.
# ---------------------------------------------------------------------------

def position_score(a: Dict, b: Dict, vw: float, vh: float) -> float:
    """Normalized centroid distance → 1 - max(|Δx|, |Δy|)."""
    cx_a = (a["x"] + a["w"] / 2) / max(vw, 1)
    cy_a = (a["y"] + a["h"] / 2) / max(vh, 1)
    cx_b = (b["x"] + b["w"] / 2) / max(vw, 1)
    cy_b = (b["y"] + b["h"] / 2) / max(vh, 1)
    return max(0.0, 1.0 - max(abs(cx_a - cx_b), abs(cy_a - cy_b)))


def size_score(a: Dict, b: Dict) -> float:
    aa = a["w"] * a["h"]
    bb = b["w"] * b["h"]
    if max(aa, bb) <= 0:
        return 1.0
    return min(aa, bb) / max(aa, bb)


# ---------------------------------------------------------------------------
# Block-Match: extract anchors, match, score.
# ---------------------------------------------------------------------------

def text_anchors(elements: List[Dict]) -> List[Dict]:
    """Filter to elements whose own text content is long enough to anchor
    a Block-Match pair."""
    return [e for e in elements if len(e.get("text", "")) >= _MIN_TEXT_LEN]


def block_match_pairs(gt_anchors: List[Dict], ag_anchors: List[Dict],
                      threshold: float = _MATCH_THRESHOLD
                      ) -> Tuple[List[Tuple[int, int, float]], np.ndarray]:
    """Hungarian-match GT anchors to agent anchors by text Dice.
    Returns: (list of (gt_idx, ag_idx, dice_score), full sim matrix)."""
    if not gt_anchors or not ag_anchors:
        return [], np.zeros((len(gt_anchors), len(ag_anchors)))
    # Cap to avoid huge cost matrices on text-rich pages.
    gt_anchors = gt_anchors[:300]
    ag_anchors = ag_anchors[:300]
    sim = np.zeros((len(gt_anchors), len(ag_anchors)))
    for i, g in enumerate(gt_anchors):
        for j, a in enumerate(ag_anchors):
            sim[i, j] = text_dice(g["text"], a["text"])
    rows, cols = linear_sum_assignment(-sim)
    pairs = []
    for r, c in zip(rows, cols):
        if sim[r, c] >= threshold:
            pairs.append((int(r), int(c), float(sim[r, c])))
    return pairs, sim


def block_match_recall(gt_anchors: List[Dict], pairs: List[Tuple[int, int, float]]) -> float:
    """Area-weighted recall: matched-area / total-GT-area."""
    if not gt_anchors:
        return 1.0
    matched_idx = {p[0] for p in pairs}
    total = sum(g["w"] * g["h"] for g in gt_anchors) + 1e-9
    matched = sum(gt_anchors[i]["w"] * gt_anchors[i]["h"] for i in matched_idx)
    return matched / total


# ---------------------------------------------------------------------------
# Visual SSIM (reuse logic, kept here so module is self-contained).
# ---------------------------------------------------------------------------

def visual_ssim(gt_png: Path, agent_png: Path) -> float:
    def _resized_gray(p: Path) -> np.ndarray:
        return np.asarray(Image.open(p).convert("L").resize((640, 400)),
                          dtype=np.float64)
    g = _resized_gray(gt_png)
    a = _resized_gray(agent_png)
    raw, _ = ssim(g, a, full=True, data_range=255)
    raw = max(0.0, min(1.0, float(raw)))
    return raw * _coverage_gate(gt_png, agent_png)


# ---------------------------------------------------------------------------
# Per-page grader.
# ---------------------------------------------------------------------------

@dataclass
class V5PageScore:
    name: str
    n_gt_anchors: int
    n_ag_anchors: int
    n_matched: int
    bm_position: float
    bm_text: float
    bm_color: float
    bm_font: float
    bm_border: float
    bm_size: float
    bm_recall: float
    tree_bleu: float
    visual_ssim: float
    combined: float


def grade_page(gt_render: RichRendered, ag_render: Optional[RichRendered],
               gt_html: str, ag_html: str,
               vw: float = 1280, vh: float = 800,
               weighting: str = "flat") -> V5PageScore:
    """Score a single (gt, agent) page pair under v5.

    weighting: "flat" (v5.1, np.mean) or "sqrt_area" (v5.2, np.average with
    weights = sqrt(GT bbox area), normalised). Sqrt-area weighting makes
    bigger anchors contribute more to bm_position/text/color/font/border/size,
    consistent with how bm_recall is already area-weighted.
    """
    if ag_render is None:
        return V5PageScore(
            name=gt_render.name, n_gt_anchors=0, n_ag_anchors=0, n_matched=0,
            bm_position=0.0, bm_text=0.0, bm_color=0.0, bm_font=0.0,
            bm_border=0.0, bm_size=0.0, bm_recall=0.0,
            tree_bleu=0.0, visual_ssim=0.0, combined=0.0,
        )
    gt_anchors = text_anchors(gt_render.elements)
    ag_anchors = text_anchors(ag_render.elements)
    pairs, _ = block_match_pairs(gt_anchors, ag_anchors)

    if pairs:
        if weighting == "sqrt_area":
            areas = np.array([gt_anchors[i]["w"] * gt_anchors[i]["h"] for i, _, _ in pairs])
            w = np.sqrt(np.maximum(areas, 1.0))
            w = w / w.sum()
            agg = lambda vals: float(np.average(vals, weights=w))
        else:
            agg = lambda vals: float(np.mean(vals))

        bm_pos    = agg([position_score(gt_anchors[i], ag_anchors[j], vw, vh) for i, j, _ in pairs])
        bm_text   = agg([sim for _, _, sim in pairs])
        bm_color  = agg([color_score(gt_anchors[i], ag_anchors[j])  for i, j, _ in pairs])
        bm_font   = agg([font_score(gt_anchors[i], ag_anchors[j])   for i, j, _ in pairs])
        bm_border = agg([border_score(gt_anchors[i], ag_anchors[j]) for i, j, _ in pairs])
        bm_size   = agg([size_score(gt_anchors[i], ag_anchors[j])   for i, j, _ in pairs])
    else:
        bm_pos = bm_text = bm_color = bm_font = bm_border = bm_size = 0.0

    bm_rec = block_match_recall(gt_anchors, pairs)
    tb = _tree_bleu(gt_html, ag_html)
    vis = visual_ssim(gt_render.png, ag_render.png)

    combined = (
        WEIGHTS["bm_position"] * bm_pos
      + WEIGHTS["bm_text"]     * bm_text
      + WEIGHTS["bm_color"]    * bm_color
      + WEIGHTS["bm_font"]     * bm_font
      + WEIGHTS["bm_border"]   * bm_border
      + WEIGHTS["bm_size"]     * bm_size
      + WEIGHTS["bm_recall"]   * bm_rec
      + WEIGHTS["tree_bleu"]   * tb
      + WEIGHTS["visual_ssim"] * vis
    )
    return V5PageScore(
        name=gt_render.name,
        n_gt_anchors=len(gt_anchors), n_ag_anchors=len(ag_anchors),
        n_matched=len(pairs),
        bm_position=bm_pos, bm_text=bm_text, bm_color=bm_color,
        bm_font=bm_font, bm_border=bm_border, bm_size=bm_size,
        bm_recall=bm_rec, tree_bleu=tb, visual_ssim=vis,
        combined=combined,
    )


# ---------------------------------------------------------------------------
# Container entry point — used when this file is baked as `tests/grade.py`
# inside a Harbor task. Reads agent files from /app/ and GT files from
# /tests/ground_truth/, renders both with the same chromium, scores each
# page with grade_page, and writes /logs/verifier/reward.json (flat
# scalars only, per Harbor schema) plus diagnostics.json.
# ---------------------------------------------------------------------------

import json as _json
import sys as _sys
import tempfile as _tempfile
import traceback as _traceback

APP_DIR = Path("/app")
TESTS_GT_DIR = Path("/tests/ground_truth")
REWARD_DIR = Path("/logs/verifier")


def _container_grade() -> Dict:
    """Render agent + GT, score every page, return a flat-scalar payload."""
    if not TESTS_GT_DIR.exists():
        raise FileNotFoundError(f"GT dir missing: {TESTS_GT_DIR}")
    if not APP_DIR.exists():
        raise FileNotFoundError(f"Agent dir missing: {APP_DIR}")

    with _tempfile.TemporaryDirectory(prefix="bm-grade-") as td:
        td_path = Path(td)
        gt_screens = td_path / "gt_screens"
        ag_screens = td_path / "ag_screens"

        gt_renders = render_pages_rich(TESTS_GT_DIR, gt_screens, VIEWPORT)
        ag_renders = render_pages_rich(APP_DIR, ag_screens, VIEWPORT)

        per_page: List[V5PageScore] = []
        for page_name in sorted(gt_renders):
            gt_r = gt_renders[page_name]
            ag_r = ag_renders.get(page_name)
            gt_html = (TESTS_GT_DIR / f"{page_name}.html").read_text()
            ag_html_path = APP_DIR / f"{page_name}.html"
            ag_html = ag_html_path.read_text() if ag_html_path.exists() else ""
            per_page.append(grade_page(
                gt_r, ag_r, gt_html, ag_html,
                vw=VIEWPORT["width"], vh=VIEWPORT["height"],
            ))

    if not per_page:
        return {"score": 0.0, "n_pages": 0, "error": "no pages graded"}

    overall = float(np.mean([p.combined for p in per_page]))
    payload: Dict[str, float] = {
        "score": overall,
        "n_pages": float(len(per_page)),
    }
    for sig in WEIGHTS.keys():
        payload[f"sig_{sig}"] = float(np.mean([getattr(p, sig) for p in per_page]))
    payload["n_matched_avg"] = float(np.mean([p.n_matched for p in per_page]))

    diagnostics = {
        "score": overall,
        "weights": WEIGHTS,
        "per_page": [
            {
                "name": p.name,
                "combined": p.combined,
                "n_gt_anchors": p.n_gt_anchors,
                "n_ag_anchors": p.n_ag_anchors,
                "n_matched": p.n_matched,
                **{sig: getattr(p, sig) for sig in WEIGHTS.keys()},
            }
            for p in per_page
        ],
    }
    return {"payload": payload, "diagnostics": diagnostics}


def main() -> int:
    REWARD_DIR.mkdir(parents=True, exist_ok=True)
    try:
        result = _container_grade()
    except Exception:
        err = _traceback.format_exc()
        print(err, file=_sys.stderr)
        (REWARD_DIR / "reward.json").write_text(_json.dumps(
            {"score": 0.0, "error": err.splitlines()[-1]}, indent=2,
        ))
        return 1

    payload = result.get("payload") or {"score": 0.0, "error": result.get("error", "")}
    diagnostics = result.get("diagnostics", payload)
    print(_json.dumps(diagnostics, indent=2))
    (REWARD_DIR / "reward.json").write_text(_json.dumps(payload, indent=2))
    (REWARD_DIR / "diagnostics.json").write_text(_json.dumps(diagnostics, indent=2))
    return 0


if __name__ == "__main__":
    _sys.exit(main())
