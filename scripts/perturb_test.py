"""Perturbation calibration: confirm grader scores monotonically rise as
agent output approaches GT across severity levels.

Severity levels:
  0 — gibberish: random ASCII paragraphs in skeletal HTML, no styles.css
  1 — heavy:    GT structure but stripped CSS + shuffled-word text
  2 — medium:   GT structure + GT CSS but text replaced with shuffled-word copy
  3 — light:    GT exact, with 25% of text leaves shuffled at the word level
  4 — oracle:   identical to GT

The grader is run locally (no Modal). Each (task, severity) gets one grade.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import shutil
import string
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

import numpy as np
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src._blockmatch_grade import grade_page, render_pages_rich, VIEWPORT


# ---------------------------------------------------------------------------
# Perturbation strategies — each takes a dir of GT files and writes to dst.
# ---------------------------------------------------------------------------

def _gibberish_token(rng: random.Random, n: int) -> str:
    chars = string.ascii_letters + " "
    return "".join(rng.choice(chars) for _ in range(n)).strip() or "gibberish"


def perturb_severity_0_gibberish(gt: Path, dst: Path, rng: random.Random) -> None:
    """Skeletal HTML with random text. No CSS, no real structure."""
    for page in gt.glob("*.html"):
        out = ["<!DOCTYPE html><html><head><title>x</title></head><body>"]
        for _ in range(rng.randint(20, 40)):
            out.append(f"<p>{_gibberish_token(rng, rng.randint(8, 60))}</p>")
        out.append("</body></html>")
        (dst / page.name).write_text("\n".join(out))
    # No CSS file — pages render with browser defaults.


def _shuffle_words(text: str, rng: random.Random) -> str:
    words = re.findall(r"\S+|\s+", text)
    word_indices = [i for i, w in enumerate(words) if w.strip()]
    shuffled = list(word_indices)
    rng.shuffle(shuffled)
    new_words = list(words)
    for src, dst in zip(word_indices, shuffled):
        new_words[src] = words[dst]
    return "".join(new_words)


def _swap_text_leaves(html: str, rng: random.Random,
                     fraction: float = 1.0) -> str:
    """Walk text leaves; for each, swap with shuffled-word version with
    probability `fraction`. Skips text inside <script>/<style>/<noscript>
    so inline CSS and JS are preserved untouched."""
    soup = BeautifulSoup(html, "html.parser")
    skip_parents = {"script", "style", "noscript"}
    leaves = []
    for el in soup.find_all(string=True):
        if not el.strip():
            continue
        if any(p.name in skip_parents for p in el.parents if p.name):
            continue
        leaves.append(el)
    for leaf in leaves:
        if rng.random() < fraction:
            leaf.replace_with(_shuffle_words(str(leaf), rng))
    return str(soup)


def perturb_severity_1_heavy(gt: Path, dst: Path, rng: random.Random) -> None:
    """GT structure, no CSS, shuffled text."""
    for page in gt.glob("*.html"):
        html = page.read_text()
        # Drop the styles.css link so browser defaults apply.
        html = re.sub(r'<link[^>]*styles\.css[^>]*>', '', html)
        # Drop inline <style> blocks.
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        # Shuffle every text leaf.
        html = _swap_text_leaves(html, rng, fraction=1.0)
        (dst / page.name).write_text(html)
    # No styles.css.


def perturb_severity_2_medium(gt: Path, dst: Path, rng: random.Random) -> None:
    """GT structure, GT CSS, ALL text leaves shuffled."""
    for page in gt.glob("*.html"):
        html = page.read_text()
        html = _swap_text_leaves(html, rng, fraction=1.0)
        (dst / page.name).write_text(html)
    # Keep GT CSS / assets.
    for f in gt.iterdir():
        if f.suffix == ".css" or f.suffix == ".jpg":
            shutil.copy2(f, dst / f.name)


def perturb_severity_3_light(gt: Path, dst: Path, rng: random.Random) -> None:
    """GT, but 25% of text leaves get a within-leaf word-shuffle."""
    for page in gt.glob("*.html"):
        html = page.read_text()
        html = _swap_text_leaves(html, rng, fraction=0.25)
        (dst / page.name).write_text(html)
    for f in gt.iterdir():
        if f.suffix == ".css" or f.suffix == ".jpg":
            shutil.copy2(f, dst / f.name)


def perturb_severity_4_oracle(gt: Path, dst: Path, rng: random.Random) -> None:
    """Identical copy of GT — sanity floor."""
    for f in gt.iterdir():
        if f.suffix in (".html", ".css") or f.suffix == ".jpg":
            shutil.copy2(f, dst / f.name)


PERTURBERS = {
    0: ("gibberish", perturb_severity_0_gibberish),
    1: ("heavy",     perturb_severity_1_heavy),
    2: ("medium",    perturb_severity_2_medium),
    3: ("light",     perturb_severity_3_light),
    4: ("oracle",    perturb_severity_4_oracle),
}


# ---------------------------------------------------------------------------
# Per-task perturbation grade
# ---------------------------------------------------------------------------

def grade_task_at_severity(task_dir: Path, severity: int, seed: int) -> Dict:
    """Render GT and the perturbed version, run the v5.1 grader on every page
    pair, return mean score + per-page details."""
    name, perturb_fn = PERTURBERS[severity]
    gt = task_dir / "solution" / "ground_truth"
    asset = task_dir / "environment" / "assets"

    rng = random.Random(seed)

    with tempfile.TemporaryDirectory(prefix=f"pert-{task_dir.name[:20]}-{severity}-") as td:
        td_p = Path(td)
        gt_scratch = td_p / "gt"
        ag_scratch = td_p / "ag"
        gt_scratch.mkdir()
        ag_scratch.mkdir()

        for f in gt.iterdir():
            shutil.copy2(f, gt_scratch / f.name)
        if asset.is_dir():
            for f in asset.iterdir():
                if not f.name.startswith("."):
                    shutil.copy2(f, gt_scratch / f.name)
                    shutil.copy2(f, ag_scratch / f.name)

        perturb_fn(gt_scratch, ag_scratch, rng)

        gt_renders = render_pages_rich(gt_scratch, td_p / "gt_screens", VIEWPORT)
        ag_renders = render_pages_rich(ag_scratch, td_p / "ag_screens", VIEWPORT)

        per_page = []
        for page in sorted(gt_renders):
            gt_r = gt_renders[page]
            ag_r = ag_renders.get(page)
            gt_html = (gt_scratch / f"{page}.html").read_text()
            ag_html_path = ag_scratch / f"{page}.html"
            ag_html = ag_html_path.read_text() if ag_html_path.exists() else ""
            ps = grade_page(gt_r, ag_r, gt_html, ag_html,
                            vw=VIEWPORT["width"], vh=VIEWPORT["height"])
            per_page.append(ps)

    if not per_page:
        return {"task": task_dir.name, "severity": severity, "name": name,
                "score": 0.0, "n_pages": 0}

    overall = float(np.mean([p.combined for p in per_page]))
    out = {
        "task": task_dir.name,
        "severity": severity,
        "name": name,
        "score": overall,
        "n_pages": len(per_page),
    }
    for sig in ("bm_position", "bm_text", "bm_color", "bm_font", "bm_border",
                "bm_size", "bm_recall", "tree_bleu", "visual_ssim"):
        out[sig] = float(np.mean([getattr(p, sig) for p in per_page]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", nargs="+",
                    default=["auth_glassy-001",
                             "dashboard_dense-001",
                             "portfolio_neobrut-001"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out-csv", type=Path,
                    default=Path("report_figures/perturbation_results.csv"))
    args = ap.parse_args()

    rows = []
    for task_name in args.tasks:
        task_dir = ROOT / "datasets" / "final" / task_name
        if not task_dir.is_dir():
            print(f"[skip] {task_name} not found")
            continue
        print(f"\n=== {task_name} ===")
        for severity in sorted(PERTURBERS):
            r = grade_task_at_severity(task_dir, severity, args.seed)
            print(f"  sev {severity} ({r['name']:>10}) → score={r['score']:.3f}  "
                  f"n_pages={r['n_pages']}")
            rows.append(r)

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with open(args.out_csv, "w") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\nwrote {args.out_csv}")

    # Monotonicity check per task
    print("\nMONOTONICITY CHECK (score must rise with severity):")
    by_task: Dict[str, List[Dict]] = {}
    for r in rows:
        by_task.setdefault(r["task"], []).append(r)
    for task, results in by_task.items():
        results.sort(key=lambda r: r["severity"])
        scores = [r["score"] for r in results]
        monotone = all(s1 <= s2 + 0.02 for s1, s2 in zip(scores, scores[1:]))
        # Allow 0.02 slack for sub-pixel jitter at extremes.
        marker = "OK" if monotone else "FAIL"
        print(f"  [{marker}] {task}: {' < '.join(f'{s:.3f}' for s in scores)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
