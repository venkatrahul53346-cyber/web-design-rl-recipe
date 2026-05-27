"""Run two adversarial agent submissions on auth_glassy-001 and grade them
using the v5.1 grader, mirroring the layout that scripts/perturb_test.py uses
so we re-use the same render+grade primitives.

Cases:
  1. empty:           agent submits <html><body></body></html> for every page
  2. screenshot_embed:agent submits a single <img src="<gt-screenshot>"> sized
                     to the viewport for every page (the §1.5 "cheat")

Output: report_figures/adversarial_results.csv
"""
from __future__ import annotations

import csv
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src._blockmatch_grade import grade_page, render_pages_rich, VIEWPORT  # noqa: E402

import numpy as np  # noqa: E402

TASK_DIR = REPO / "datasets" / "final" / "auth_glassy-001"
GT = TASK_DIR / "solution" / "ground_truth"
SCREENS = TASK_DIR / "environment" / "prompt" / "screenshots"
OUT_CSV = REPO / "report_figures" / "adversarial_results.csv"

PAGES = ["login", "signup", "verify", "onboarding-step-1",
         "onboarding-step-2", "dashboard-empty"]

EMPTY_HTML = "<!DOCTYPE html><html><head><title>blank</title></head><body></body></html>\n"

EMBED_HTML_TMPL = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>html,body{{margin:0;padding:0;background:#fff}}img{{display:block;width:100%;height:auto}}</style>
</head><body><img src="{img}" alt=""></body></html>
"""


def make_empty(scratch: Path) -> None:
    for p in PAGES:
        (scratch / f"{p}.html").write_text(EMPTY_HTML)


def make_embed(scratch: Path) -> None:
    # Copy screenshots into the agent dir and reference them.
    for p in PAGES:
        src_png = SCREENS / f"{p}.png"
        dst_png = scratch / f"{p}.png"
        shutil.copy2(src_png, dst_png)
        (scratch / f"{p}.html").write_text(EMBED_HTML_TMPL.format(title=p, img=f"{p}.png"))


def grade_case(label: str, builder) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"adv-{label}-") as td:
        td_p = Path(td)
        gt_scratch = td_p / "gt"
        ag_scratch = td_p / "ag"
        gt_scratch.mkdir(); ag_scratch.mkdir()

        for f in GT.iterdir():
            shutil.copy2(f, gt_scratch / f.name)

        builder(ag_scratch)

        gt_renders = render_pages_rich(gt_scratch, td_p / "gt_screens", VIEWPORT)
        ag_renders = render_pages_rich(ag_scratch, td_p / "ag_screens", VIEWPORT)

        per_page = []
        for page in sorted(gt_renders):
            gt_r = gt_renders[page]
            ag_r = ag_renders.get(page)
            gt_html = (gt_scratch / f"{page}.html").read_text()
            ag_html_path = ag_scratch / f"{page}.html"
            ag_html = ag_html_path.read_text() if ag_html_path.exists() else ""
            per_page.append(grade_page(gt_r, ag_r, gt_html, ag_html,
                                       vw=VIEWPORT["width"], vh=VIEWPORT["height"]))

    out = {
        "label": label,
        "score": float(np.mean([p.combined for p in per_page])),
        "n_pages": len(per_page),
    }
    for sig in ("bm_position", "bm_text", "bm_color", "bm_font", "bm_border",
                "bm_size", "bm_recall", "tree_bleu", "visual_ssim"):
        out[sig] = float(np.mean([getattr(p, sig) for p in per_page]))
    return out


def main() -> int:
    rows = []
    for label, fn in [("empty", make_empty), ("screenshot_embed", make_embed)]:
        print(f"[adversarial] grading {label}...", flush=True)
        r = grade_case(label, fn)
        rows.append(r)
        print(f"  score={r['score']:.4f}  recall={r['bm_recall']:.3f}  tree={r['tree_bleu']:.3f}  ssim={r['visual_ssim']:.3f}")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    cols = ["label", "score", "n_pages",
            "bm_position", "bm_text", "bm_color", "bm_font", "bm_border",
            "bm_size", "bm_recall", "tree_bleu", "visual_ssim"]
    with OUT_CSV.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in cols})
    print(f"wrote {OUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
