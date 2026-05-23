"""Experimental v6 grader — multi-tier matching + hierarchy_consistency.

v5 architecture critique: Block-Match anchors only on text-bearing leaf
elements. Container divs (cards, panels, hero sections), image-only
elements, and decorative blocks are completely invisible to the per-pair
signals. Hierarchy is captured only by tree_bleu's 1-height subtree
multiset, which can't pin "which element is in the wrong context."

v6 fixes both:

  1. Multi-tier matching covers more of the DOM:
     Tier A — text leaves          (own-text Dice)        confidence 1.0
     Tier B — content containers   (descendant content    confidence 0.8
                                   bag composite cost)
     Tier C — image elements       (src + alt Dice)       confidence 0.7
     Tier D — structural fallback  (tag + bbox IoU)       confidence 0.5

     Each tier matches what previous tiers left unmatched. Per-pair
     scores are weighted by tier confidence so a Tier D match contributes
     less than a Tier A match.

  2. New signals:
     bm_spacing            (0.05) — per-pair padding+margin similarity
     hierarchy_consistency (0.10) — fraction of matched pairs whose
                                    parent is also a matched pair
     body_bg_color         (0.10) — rank-aligned CIEDE2000 on screenshot
                                    dominant palette (re-added from v4)

Weights (sum = 1.000):
  bm_position            0.10
  bm_text                0.10
  bm_color               0.10
  bm_font                0.10
  bm_border              0.05
  bm_size                0.05
  bm_spacing             0.05   NEW
  bm_recall              0.05
  tree_bleu              0.10
  hierarchy_consistency  0.10   NEW
  body_bg_color          0.10   NEW
  visual_ssim            0.10
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from scipy.optimize import linear_sum_assignment
from skimage.metrics import structural_similarity as ssim

from src._container_grade import (
    _srgb_to_lab, _ciede2000, _tree_bleu, _coverage_gate,
)
from src._blockmatch_grade import (
    parse_css_color, color_distance_de,
    font_score, border_score,
    text_dice, position_score, size_score,
    color_score as _bm_color_score,
)


WEIGHTS = {
    "bm_position":           0.10,
    "bm_text":               0.10,
    "bm_color":              0.10,
    "bm_font":               0.10,
    "bm_border":             0.05,
    "bm_size":               0.05,
    "bm_spacing":            0.05,
    "bm_recall":             0.05,
    "tree_bleu":             0.10,
    "hierarchy_consistency": 0.10,
    "body_bg_color":         0.10,
    "visual_ssim":           0.10,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, sum(WEIGHTS.values())

VIEWPORT = {"width": 1280, "height": 800}

# Tier confidence multipliers — applied to per-pair sub-scores.
TIER_CONF = {"A": 1.0, "B": 0.8, "C": 0.7, "D": 0.5}

_MIN_TEXT_LEN = 4
_MIN_DESCENDANT_TEXT_LEN = 16   # higher bar for Tier B
_TIER_A_THRESHOLD = 0.5
_TIER_B_THRESHOLD = 0.4
_TIER_C_THRESHOLD = 0.3
_TIER_D_IOU_MIN = 0.2


# ---------------------------------------------------------------------------
# Extended playwright extractor — per-element record with parent index,
# descendant content bag, padding/margin, image src/alt.
# ---------------------------------------------------------------------------

_RICH_JS_V6 = r"""
() => {
  // Pre-walk to assign each visible element a stable index, and capture
  // parent indices in the SAME index space.
  const all = document.querySelectorAll('*');
  const idMap = new Map();
  const visible = [];
  for (const el of all) {
    const rect = el.getBoundingClientRect();
    if (!(rect.width > 0 && rect.height > 0)) continue;
    if (!(rect.right > 0 && rect.bottom > 0)) continue;
    const s = getComputedStyle(el);
    if (s.display === 'none') continue;
    if (s.visibility === 'hidden') continue;
    const op = parseFloat(s.opacity || '1');
    if (!(op > 0)) continue;
    visible.push(el);
    idMap.set(el, visible.length - 1);
  }
  const out = [];
  for (let i = 0; i < visible.length; i++) {
    const el = visible[i];
    const rect = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    let ownText = '';
    for (const c of el.childNodes) {
      if (c.nodeType === 3) ownText += (c.nodeValue || '');
    }
    ownText = ownText.replace(/\s+/g, ' ').trim();
    const innerText = (el.innerText || '').replace(/\s+/g, ' ').trim();
    const descendants = el.querySelectorAll('*');
    const descTags = {};
    for (const d of descendants) {
      const t = d.tagName.toLowerCase();
      descTags[t] = (descTags[t] || 0) + 1;
    }
    let parentIdx = -1;
    if (el.parentElement && idMap.has(el.parentElement)) {
      parentIdx = idMap.get(el.parentElement);
    }
    const tag = el.tagName.toLowerCase();
    out.push({
      idx: i,
      tag: tag,
      x: rect.left, y: rect.top, w: rect.width, h: rect.height,
      text: ownText,
      descendantText: innerText,
      descendantTags: descTags,
      nChildren: el.children.length,
      parentIdx: parentIdx,
      imgSrc: tag === 'img' ? (el.getAttribute('src') || '') : '',
      imgAlt: tag === 'img' ? (el.getAttribute('alt') || '') : '',
      fontFamily: s.fontFamily || '',
      fontSize: parseFloat(s.fontSize) || 0,
      fontWeight: parseInt(s.fontWeight) || 400,
      color: s.color || '',
      backgroundColor: s.backgroundColor || '',
      borderRadius: parseFloat(s.borderTopLeftRadius) || 0,
      borderStyle: s.borderTopStyle || 'none',
      borderColor: s.borderTopColor || '',
      borderWidth: parseFloat(s.borderTopWidth) || 0,
      boxShadow: s.boxShadow || 'none',
      paddingTop:    parseFloat(s.paddingTop)    || 0,
      paddingRight:  parseFloat(s.paddingRight)  || 0,
      paddingBottom: parseFloat(s.paddingBottom) || 0,
      paddingLeft:   parseFloat(s.paddingLeft)   || 0,
      marginTop:    parseFloat(s.marginTop)    || 0,
      marginRight:  parseFloat(s.marginRight)  || 0,
      marginBottom: parseFloat(s.marginBottom) || 0,
      marginLeft:   parseFloat(s.marginLeft)   || 0,
    });
  }
  return out;
}
"""


@dataclass
class RichRenderedV6:
    name: str
    png: Path
    elements: List[Dict]


def render_pages_rich_v6(html_dir: Path, screenshot_out_dir: Path,
                          viewport: Dict[str, int] = None) -> Dict[str, RichRenderedV6]:
    viewport = viewport or VIEWPORT
    screenshot_out_dir.mkdir(parents=True, exist_ok=True)
    out: Dict[str, RichRenderedV6] = {}
    htmls = sorted(html_dir.glob("*.html"))
    if not htmls:
        return out
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            ctx = browser.new_context(viewport=viewport, device_scale_factor=1)
            page = ctx.new_page()
            for html in htmls:
                try:
                    page.goto(html.as_uri(), wait_until="load", timeout=15000)
                    page.wait_for_timeout(200)
                    elements = page.evaluate(_RICH_JS_V6)
                    png = screenshot_out_dir / (html.stem + ".png")
                    page.screenshot(path=str(png), full_page=True)
                    out[html.stem] = RichRenderedV6(
                        name=html.stem, png=png, elements=elements,
                    )
                except Exception as exc:
                    print(f"  render failed for {html.name}: {exc}")
        finally:
            browser.close()
    return out


# ---------------------------------------------------------------------------
# Multi-tier matching.
# ---------------------------------------------------------------------------

def _hungarian_filter(sim: np.ndarray, threshold: float) -> List[Tuple[int, int, float]]:
    if sim.size == 0:
        return []
    rows, cols = linear_sum_assignment(-sim)
    return [(int(r), int(c), float(sim[r, c])) for r, c in zip(rows, cols)
            if sim[r, c] >= threshold]


def _bag_jaccard(a: Dict[str, int], b: Dict[str, int]) -> float:
    keys = set(a) | set(b)
    if not keys: return 1.0
    inter = sum(min(a.get(k, 0), b.get(k, 0)) for k in keys)
    union = sum(max(a.get(k, 0), b.get(k, 0)) for k in keys)
    return inter / union if union else 0.0


def _bbox_iou(a: Dict, b: Dict) -> float:
    ax1, ay1 = a["x"], a["y"]
    ax2, ay2 = ax1 + a["w"], ay1 + a["h"]
    bx1, by1 = b["x"], b["y"]
    bx2, by2 = bx1 + b["w"], by1 + b["h"]
    ix1 = max(ax1, bx1); iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2); iy2 = min(ay2, by2)
    iw = max(0.0, ix2 - ix1); ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union > 0 else 0.0


def multi_tier_match(gt_els: List[Dict], ag_els: List[Dict]
                      ) -> List[Tuple[int, int, str, float]]:
    """Return list of (gt_idx, ag_idx, tier, score) for matched pairs.
    Each tier excludes elements that earlier tiers matched."""
    matches: List[Tuple[int, int, str, float]] = []
    used_gt: set = set()
    used_ag: set = set()

    def _filt(elements: List[Dict], used: set, predicate) -> List[Tuple[int, Dict]]:
        return [(i, e) for i, e in enumerate(elements)
                if i not in used and predicate(e)]

    # Tier A: text leaves
    gtA = _filt(gt_els, used_gt, lambda e: len(e.get("text", "")) >= _MIN_TEXT_LEN)
    agA = _filt(ag_els, used_ag, lambda e: len(e.get("text", "")) >= _MIN_TEXT_LEN)
    if gtA and agA:
        gtA = gtA[:300]; agA = agA[:300]
        sim = np.zeros((len(gtA), len(agA)))
        for i, (_, g) in enumerate(gtA):
            for j, (_, a) in enumerate(agA):
                sim[i, j] = text_dice(g["text"], a["text"])
        for gi, aj, sc in _hungarian_filter(sim, _TIER_A_THRESHOLD):
            gx = gtA[gi][0]; ax = agA[aj][0]
            matches.append((gx, ax, "A", sc))
            used_gt.add(gx); used_ag.add(ax)

    # Tier B: content-bag containers (no own text, has descendant content)
    def _is_container(e):
        return (len(e.get("text", "")) < _MIN_TEXT_LEN
                and len(e.get("descendantText", "")) >= _MIN_DESCENDANT_TEXT_LEN)
    gtB = _filt(gt_els, used_gt, _is_container)
    agB = _filt(ag_els, used_ag, _is_container)
    if gtB and agB:
        gtB = gtB[:200]; agB = agB[:200]
        sim = np.zeros((len(gtB), len(agB)))
        for i, (_, g) in enumerate(gtB):
            for j, (_, a) in enumerate(agB):
                td = text_dice(g["descendantText"], a["descendantText"])
                tj = _bag_jaccard(g.get("descendantTags", {}),
                                  a.get("descendantTags", {}))
                cn_g = g.get("nChildren", 0); cn_a = a.get("nChildren", 0)
                cn = (min(cn_g, cn_a) / max(cn_g, cn_a)) if max(cn_g, cn_a) > 0 else 1.0
                sim[i, j] = 0.6 * td + 0.3 * tj + 0.1 * cn
        for gi, aj, sc in _hungarian_filter(sim, _TIER_B_THRESHOLD):
            gx = gtB[gi][0]; ax = agB[aj][0]
            matches.append((gx, ax, "B", sc))
            used_gt.add(gx); used_ag.add(ax)

    # Tier C: images
    def _is_img(e): return e.get("tag") == "img"
    gtC = _filt(gt_els, used_gt, _is_img)
    agC = _filt(ag_els, used_ag, _is_img)
    if gtC and agC:
        sim = np.zeros((len(gtC), len(agC)))
        for i, (_, g) in enumerate(gtC):
            g_key = (g.get("imgSrc", "").rsplit("/", 1)[-1] + " "
                     + g.get("imgAlt", ""))
            for j, (_, a) in enumerate(agC):
                a_key = (a.get("imgSrc", "").rsplit("/", 1)[-1] + " "
                         + a.get("imgAlt", ""))
                sim[i, j] = text_dice(g_key, a_key)
        for gi, aj, sc in _hungarian_filter(sim, _TIER_C_THRESHOLD):
            gx = gtC[gi][0]; ax = agC[aj][0]
            matches.append((gx, ax, "C", sc))
            used_gt.add(gx); used_ag.add(ax)

    # Tier D: tag + bbox IoU greedy on remaining
    by_tag_gt: Dict[str, List[int]] = {}
    by_tag_ag: Dict[str, List[int]] = {}
    for i, e in enumerate(gt_els):
        if i in used_gt: continue
        by_tag_gt.setdefault(e["tag"], []).append(i)
    for i, e in enumerate(ag_els):
        if i in used_ag: continue
        by_tag_ag.setdefault(e["tag"], []).append(i)
    for tag, gidxs in by_tag_gt.items():
        aidxs = by_tag_ag.get(tag, [])
        if not aidxs: continue
        # Sort GT by area (desc) so big elements claim partners first
        gidxs_sorted = sorted(gidxs, key=lambda i: -gt_els[i]["w"] * gt_els[i]["h"])
        used_local: set = set()
        for gi in gidxs_sorted:
            best_j, best_iou = -1, 0.0
            for aj in aidxs:
                if aj in used_local: continue
                iou = _bbox_iou(gt_els[gi], ag_els[aj])
                if iou > best_iou:
                    best_iou = iou; best_j = aj
            if best_j >= 0 and best_iou >= _TIER_D_IOU_MIN:
                matches.append((gi, best_j, "D", best_iou))
                used_gt.add(gi); used_ag.add(best_j); used_local.add(best_j)

    return matches


# ---------------------------------------------------------------------------
# Per-pair sub-score evaluators.
# ---------------------------------------------------------------------------

def _per_pair_scores(g: Dict, a: Dict, vw: float, vh: float) -> Dict[str, float]:
    return {
        "position": position_score(g, a, vw, vh),
        "text":     text_dice(g.get("text", ""), a.get("text", "")),
        "color":    _bm_color_score(g, a),
        "font":     font_score(g, a),
        "border":   border_score(g, a),
        "size":     size_score(g, a),
        "spacing":  _spacing_score(g, a),
    }


def _spacing_score(a: Dict, b: Dict) -> float:
    """Mean ratio across 8 sides: padding {t,r,b,l} and margin {t,r,b,l}.
    Each side: min(va,vb)/max(va,vb) if both > 0, 1 if both <= 1, 0.5 otherwise."""
    keys = ("paddingTop", "paddingRight", "paddingBottom", "paddingLeft",
            "marginTop", "marginRight", "marginBottom", "marginLeft")
    vals = []
    for k in keys:
        va = a.get(k, 0) or 0; vb = b.get(k, 0) or 0
        if va <= 1 and vb <= 1:
            vals.append(1.0)
        elif va <= 1 or vb <= 1:
            vals.append(0.5)
        else:
            vals.append(min(va, vb) / max(va, vb))
    return float(np.mean(vals)) if vals else 1.0


# ---------------------------------------------------------------------------
# Body-bg signal — re-added from v4. Rank-aligned CIEDE2000 on top-5
# dominant pixel colors of the screenshot, weighted by min coverage.
# ---------------------------------------------------------------------------

def _dominant_palette(path: Path, k: int = 5) -> Tuple[np.ndarray, np.ndarray]:
    img = Image.open(path).convert("RGB").resize((128, 128))
    arr = np.asarray(img, dtype=np.uint8).reshape(-1, 3)
    q = (arr >> 3).astype(np.int32)
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


def body_bg_color_score(gt_png: Path, agent_png: Path) -> float:
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
# Visual SSIM (same as v5).
# ---------------------------------------------------------------------------

def visual_ssim(gt_png: Path, agent_png: Path) -> float:
    def _gr(p: Path) -> np.ndarray:
        return np.asarray(Image.open(p).convert("L").resize((640, 400)),
                          dtype=np.float64)
    raw, _ = ssim(_gr(gt_png), _gr(agent_png), full=True, data_range=255)
    return max(0.0, min(1.0, float(raw))) * _coverage_gate(gt_png, agent_png)


# ---------------------------------------------------------------------------
# Page-level grader.
# ---------------------------------------------------------------------------

@dataclass
class V6PageScore:
    name: str
    n_matched_total: int
    n_matched_per_tier: Dict[str, int]
    bm_position: float
    bm_text: float
    bm_color: float
    bm_font: float
    bm_border: float
    bm_size: float
    bm_spacing: float
    bm_recall: float
    tree_bleu: float
    hierarchy_consistency: float
    body_bg_color: float
    visual_ssim: float
    combined: float


def _tier_weighted_mean(values: List[float], confidences: List[float]) -> float:
    if not values: return 0.0
    w = np.array(confidences, dtype=np.float64)
    if w.sum() == 0: return 0.0
    return float(np.average(np.array(values, dtype=np.float64), weights=w))


def _hierarchy_consistency(matches: List[Tuple[int, int, str, float]],
                           gt_els: List[Dict], ag_els: List[Dict]) -> float:
    """Fraction of matched pairs whose parents are also a matched pair."""
    if not matches: return 0.0
    pair_set = {(g, a) for g, a, _, _ in matches}
    hits = 0; total = 0
    for g, a, _, _ in matches:
        gp = gt_els[g].get("parentIdx", -1)
        ap = ag_els[a].get("parentIdx", -1)
        if gp < 0 or ap < 0:
            continue
        total += 1
        if (gp, ap) in pair_set:
            hits += 1
    return hits / total if total else 0.0


def grade_page(gt_render: RichRenderedV6, ag_render: Optional[RichRenderedV6],
               gt_html: str, ag_html: str,
               vw: float = 1280, vh: float = 800) -> V6PageScore:
    if ag_render is None:
        return V6PageScore(
            name=gt_render.name, n_matched_total=0,
            n_matched_per_tier={"A":0,"B":0,"C":0,"D":0},
            bm_position=0, bm_text=0, bm_color=0, bm_font=0, bm_border=0,
            bm_size=0, bm_spacing=0, bm_recall=0,
            tree_bleu=0, hierarchy_consistency=0, body_bg_color=0,
            visual_ssim=0, combined=0,
        )
    gt_els = gt_render.elements
    ag_els = ag_render.elements

    matches = multi_tier_match(gt_els, ag_els)

    # Per-pair sub-scores, weighted by tier confidence.
    if matches:
        per_pair: Dict[str, List[float]] = {
            k: [] for k in ("position","text","color","font","border","size","spacing")}
        confs: List[float] = []
        for gi, aj, tier, _ in matches:
            sc = _per_pair_scores(gt_els[gi], ag_els[aj], vw, vh)
            for k, v in sc.items(): per_pair[k].append(v)
            confs.append(TIER_CONF[tier])
        bm_pos     = _tier_weighted_mean(per_pair["position"], confs)
        bm_text    = _tier_weighted_mean(per_pair["text"],     confs)
        bm_color   = _tier_weighted_mean(per_pair["color"],    confs)
        bm_font    = _tier_weighted_mean(per_pair["font"],     confs)
        bm_border  = _tier_weighted_mean(per_pair["border"],   confs)
        bm_size    = _tier_weighted_mean(per_pair["size"],     confs)
        bm_spacing = _tier_weighted_mean(per_pair["spacing"],  confs)
    else:
        bm_pos = bm_text = bm_color = bm_font = bm_border = bm_size = bm_spacing = 0.0

    # Block-Match recall: matched-area / total-GT-area, over Tier A+B+C+D matched GT elements.
    matched_gt_idx = {g for g, _, _, _ in matches}
    total_area = sum(e["w"] * e["h"] for e in gt_els) + 1e-9
    matched_area = sum(gt_els[i]["w"] * gt_els[i]["h"] for i in matched_gt_idx)
    bm_recall = matched_area / total_area

    tb = _tree_bleu(gt_html, ag_html)
    hc = _hierarchy_consistency(matches, gt_els, ag_els)
    bg = body_bg_color_score(gt_render.png, ag_render.png)
    vs = visual_ssim(gt_render.png, ag_render.png)

    combined = (
        WEIGHTS["bm_position"]            * bm_pos
      + WEIGHTS["bm_text"]                * bm_text
      + WEIGHTS["bm_color"]               * bm_color
      + WEIGHTS["bm_font"]                * bm_font
      + WEIGHTS["bm_border"]              * bm_border
      + WEIGHTS["bm_size"]                * bm_size
      + WEIGHTS["bm_spacing"]             * bm_spacing
      + WEIGHTS["bm_recall"]              * bm_recall
      + WEIGHTS["tree_bleu"]              * tb
      + WEIGHTS["hierarchy_consistency"]  * hc
      + WEIGHTS["body_bg_color"]          * bg
      + WEIGHTS["visual_ssim"]            * vs
    )

    tier_counts = Counter(t for _, _, t, _ in matches)
    return V6PageScore(
        name=gt_render.name,
        n_matched_total=len(matches),
        n_matched_per_tier={t: tier_counts.get(t, 0) for t in "ABCD"},
        bm_position=bm_pos, bm_text=bm_text, bm_color=bm_color,
        bm_font=bm_font, bm_border=bm_border, bm_size=bm_size,
        bm_spacing=bm_spacing, bm_recall=bm_recall,
        tree_bleu=tb, hierarchy_consistency=hc,
        body_bg_color=bg, visual_ssim=vs,
        combined=combined,
    )
