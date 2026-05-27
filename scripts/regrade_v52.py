"""Re-grade all 110 final-eval-opus-v51 trials with both v5.1 (flat-mean) and
v5.2 (sqrt-area weighted) per-pair aggregation, in one render pass per trial.

For each trial:
  1. Replay Write / Edit calls in trajectory.json to reconstruct final /app state
  2. Copy GT assets (placeholder JPGs, stylesheets that came pre-staged)
  3. Render both GT and agent in the same Chromium
  4. Run grade_page twice (once per weighting mode) — share the renders
  5. Append a row per (trial, mode) to report_figures/v52_compare.csv
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src._blockmatch_grade import (  # noqa: E402
    grade_page, render_pages_rich, VIEWPORT,
)
import numpy as np  # noqa: E402

JOBS_DIR = REPO / "jobs" / "final-eval-opus-v51"
DATASETS = REPO / "datasets" / "final"
OUT_CSV = REPO / "report_figures" / "v52_compare.csv"

SIGNAL_COLS = ["bm_position", "bm_text", "bm_color", "bm_font", "bm_border",
               "bm_size", "bm_recall", "tree_bleu", "visual_ssim"]


def replay_writes(trajectory_path: Path, out_dir: Path) -> List[str]:
    """Replay Write/Edit tool calls from the trajectory into out_dir.
    Returns list of files created. Last write wins. Edit calls do
    old_string -> new_string substitution on existing file."""
    data = json.loads(trajectory_path.read_text())
    files = {}  # rel_path -> str content

    for step in data.get("steps", []):
        for tc in (step.get("tool_calls") or []):
            name = tc.get("function_name") or tc.get("name") or ""
            args = tc.get("arguments") or tc.get("input") or {}
            fp = args.get("file_path") or args.get("path") or ""
            if not fp.startswith("/app/"):
                continue
            rel = fp[len("/app/"):]
            if name == "Write":
                content = args.get("content") or args.get("file_text") or ""
                files[rel] = content
            elif name in ("Edit", "MultiEdit"):
                if rel not in files:
                    continue  # can't edit something we never wrote
                old = args.get("old_string") or ""
                new = args.get("new_string") or ""
                if old:
                    files[rel] = files[rel].replace(old, new, 1)

    written = []
    for rel, content in files.items():
        dst = out_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(content)
        written.append(rel)
    return written


def task_dir_for_trial(trial_id: str) -> Optional[Path]:
    # trial_id like "auth_glassy-001__PEMFUqo" -> task "auth_glassy-001"
    # but some are "government__dark_native_clean-00__KNDEZmJ" which is truncated;
    # match against datasets/final/* by prefix
    for d in DATASETS.iterdir():
        if not d.is_dir():
            continue
        # task names in trial ids may be truncated to 32 chars; match by prefix
        if trial_id.startswith(d.name):
            return d
        # truncated prefix attempt
        if trial_id.startswith(d.name[:32]):
            return d
    return None


def grade_trial(trial_dir: Path, task_dir: Path) -> Optional[Dict]:
    """Render and grade one trial under both v5.1 and v5.2 modes.
    Returns dict with both row payloads or None on irrecoverable error."""
    trial_id = trial_dir.name
    traj_path = trial_dir / "agent" / "trajectory.json"
    if not traj_path.exists():
        return None

    gt_dir = task_dir / "solution" / "ground_truth"
    asset_dir = task_dir / "environment" / "assets"

    with tempfile.TemporaryDirectory(prefix=f"v52-{trial_id[:24]}-") as td:
        td_p = Path(td)
        gt_scratch = td_p / "gt"
        ag_scratch = td_p / "ag"
        gt_scratch.mkdir()
        ag_scratch.mkdir()

        # Copy GT files
        for f in gt_dir.iterdir():
            shutil.copy2(f, gt_scratch / f.name)
        # Copy assets to BOTH dirs (agent likely refs them)
        if asset_dir.is_dir():
            for f in asset_dir.iterdir():
                if f.name.startswith("."):
                    continue
                shutil.copy2(f, gt_scratch / f.name)
                shutil.copy2(f, ag_scratch / f.name)

        # Replay agent writes
        replay_writes(traj_path, ag_scratch)

        # Render once
        try:
            gt_renders = render_pages_rich(gt_scratch, td_p / "gt_screens", VIEWPORT)
            ag_renders = render_pages_rich(ag_scratch, td_p / "ag_screens", VIEWPORT)
        except Exception:
            return None

        per_page_v51 = []
        per_page_v52 = []
        for page in sorted(gt_renders):
            gt_r = gt_renders[page]
            ag_r = ag_renders.get(page)
            gt_html = (gt_scratch / f"{page}.html").read_text()
            ag_html_path = ag_scratch / f"{page}.html"
            ag_html = ag_html_path.read_text() if ag_html_path.exists() else ""
            ps_v51 = grade_page(gt_r, ag_r, gt_html, ag_html,
                                vw=VIEWPORT["width"], vh=VIEWPORT["height"],
                                weighting="flat")
            ps_v52 = grade_page(gt_r, ag_r, gt_html, ag_html,
                                vw=VIEWPORT["width"], vh=VIEWPORT["height"],
                                weighting="sqrt_area")
            per_page_v51.append(ps_v51)
            per_page_v52.append(ps_v52)

        if not per_page_v51:
            return None

        def aggregate(per_page, mode_label):
            row = {
                "trial": trial_id, "task": task_dir.name, "mode": mode_label,
                "score": float(np.mean([p.combined for p in per_page])),
                "n_pages": len(per_page),
                "n_matched_avg": float(np.mean([p.n_matched for p in per_page])),
            }
            for sig in SIGNAL_COLS:
                row[sig] = float(np.mean([getattr(p, sig) for p in per_page]))
            return row

        return {
            "v51": aggregate(per_page_v51, "v51"),
            "v52": aggregate(per_page_v52, "v52"),
        }


def main() -> int:
    # Showcase subset: 3 highest-spread tasks (where v5.2 should matter most)
    # + 1 saturated control (where v5.1 and v5.2 should agree).
    SHOWCASE = {
        "docs_mono-001",
        "portfolio_neobrut-001",
        "government__dark_native_clean-001",
        "auth_glassy-001",
    }
    all_trials = sorted([t for t in JOBS_DIR.iterdir() if t.is_dir()])
    trials = [t for t in all_trials
              if any(t.name.startswith(task[:32]) for task in SHOWCASE)]
    print(f"[regrade] {len(trials)} trials (subset of {len(all_trials)}) in {JOBS_DIR}")

    cols = ["trial", "task", "mode", "score", "n_pages", "n_matched_avg"] + SIGNAL_COLS
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    success = fail = 0
    with OUT_CSV.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for i, trial_dir in enumerate(trials, 1):
            task_dir = task_dir_for_trial(trial_dir.name)
            if task_dir is None:
                print(f"  [{i:>3}/{len(trials)}] {trial_dir.name}: NO TASK DIR")
                fail += 1
                continue
            try:
                out = grade_trial(trial_dir, task_dir)
            except Exception:
                print(f"  [{i:>3}/{len(trials)}] {trial_dir.name}: EXCEPTION")
                traceback.print_exc()
                fail += 1
                continue
            if out is None:
                print(f"  [{i:>3}/{len(trials)}] {trial_dir.name}: render fail")
                fail += 1
                continue
            for row in (out["v51"], out["v52"]):
                w.writerow({k: row.get(k, "") for k in cols})
            fh.flush()
            print(f"  [{i:>3}/{len(trials)}] {trial_dir.name}: "
                  f"v51={out['v51']['score']:.3f}  v52={out['v52']['score']:.3f}")
            success += 1

    print(f"[regrade] done: {success} ok, {fail} failed -> {OUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
