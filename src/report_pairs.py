"""Build side-by-side ground-truth vs agent screenshot pairs for the report.

For each task, picks the best- and worst-scoring trial (and optionally
the median) and stitches a single PNG showing GT (left) vs agent (right)
for the index page. This is what makes "higher score = better
replication" visible to a human reviewer.

Usage:
  .venv/bin/python -m src.report_pairs jobs/final-eval-opus-v34 --out report_figures/pairs/
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None


def load_trials(jobs_dir: Path) -> List[Dict]:
    rows: List[Dict] = []
    for trial_dir in sorted(jobs_dir.iterdir()):
        if not trial_dir.is_dir():
            continue
        cfg_path = trial_dir / "config.json"
        rwd_path = trial_dir / "verifier" / "reward.json"
        if not (cfg_path.exists() and rwd_path.exists()):
            continue
        cfg = json.loads(cfg_path.read_text())
        rwd = json.loads(rwd_path.read_text())
        score = rwd.get("score")
        if score is None:
            continue
        task = Path(cfg.get("task", {}).get("path", "")).name or trial_dir.name.split("__")[0]
        rows.append({
            "task": task, "trial": trial_dir.name,
            "trial_dir": trial_dir, "score": float(score),
        })
    return rows


def find_first_page_pair(trial_dir: Path) -> Optional[Tuple[Path, Path, str]]:
    """Find a (gt_png, agent_png, page_name) triple. Prefer 'index' if present.

    v3.4 splits screenshots into desktop/mobile dirs with viewport suffix.
    Pre-v3.4 used a single ``{agent,gt}_screenshots/`` pair. Try the
    v3.4 layout first, then fall back.
    """
    candidates_dir_pairs = [
        (trial_dir / "verifier" / "gt_screenshots_desktop",
         trial_dir / "verifier" / "agent_screenshots_desktop"),
        (trial_dir / "verifier" / "gt_screenshots",
         trial_dir / "verifier" / "agent_screenshots"),
    ]
    for gt_dir, ag_dir in candidates_dir_pairs:
        if not (gt_dir.is_dir() and ag_dir.is_dir()):
            continue
        candidates = sorted({p.name for p in gt_dir.iterdir() if p.suffix == ".png"} &
                            {p.name for p in ag_dir.iterdir() if p.suffix == ".png"})
        if not candidates:
            continue
        pref = "index.png"
        chosen = pref if pref in candidates else candidates[0]
        return gt_dir / chosen, ag_dir / chosen, Path(chosen).stem
    return None


def stitch_pair(gt_path: Path, agent_path: Path, *, label: str,
                out_path: Path, max_height: int = 800) -> None:
    if Image is None:
        raise RuntimeError("Pillow not installed")
    gt = Image.open(gt_path).convert("RGB")
    ag = Image.open(agent_path).convert("RGB")
    # Scale both to the same height for fair side-by-side.
    target_h = min(max_height, gt.height, ag.height)
    def _scale(im, h):
        if im.height == h:
            return im
        w = round(im.width * h / im.height)
        return im.resize((w, h), Image.LANCZOS)
    gt = _scale(gt, target_h)
    ag = _scale(ag, target_h)
    gap = 16
    header_h = 32
    W = gt.width + ag.width + gap
    H = target_h + header_h
    canvas = Image.new("RGB", (W, H), "white")
    canvas.paste(gt, (0, header_h))
    canvas.paste(ag, (gt.width + gap, header_h))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except (OSError, IOError):
        font = ImageFont.load_default()
    draw.text((8, 6), f"GROUND TRUTH — {label}", fill="black", font=font)
    draw.text((gt.width + gap + 8, 6), f"AGENT — {label}", fill="black", font=font)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("jobs_dir", type=Path)
    p.add_argument("--out", type=Path, default=Path("report_figures/pairs"))
    p.add_argument("--levels", default="best,worst",
                   help="Comma list: best,median,worst (subset).")
    args = p.parse_args()

    rows = load_trials(args.jobs_dir)
    if not rows:
        print("no trials found", file=sys.stderr)
        return 1

    by_task: Dict[str, List[Dict]] = defaultdict(list)
    for r in rows:
        by_task[r["task"]].append(r)

    levels = [s.strip() for s in args.levels.split(",") if s.strip()]
    args.out.mkdir(parents=True, exist_ok=True)

    for task, trials in sorted(by_task.items()):
        trials_sorted = sorted(trials, key=lambda r: r["score"])
        picks: Dict[str, Dict] = {}
        if "worst" in levels:
            picks["worst"] = trials_sorted[0]
        if "median" in levels and len(trials_sorted) >= 3:
            picks["median"] = trials_sorted[len(trials_sorted) // 2]
        if "best" in levels:
            picks["best"] = trials_sorted[-1]

        for level, trial in picks.items():
            pair = find_first_page_pair(trial["trial_dir"])
            if pair is None:
                print(f"skip {task} {level}: no screenshots in {trial['trial_dir'].name}",
                      file=sys.stderr)
                continue
            gt, ag, page = pair
            label = f"{task}/{page} | score={trial['score']:.3f} | {level}"
            out = args.out / f"{task}__{level}__score_{trial['score']:.3f}.png"
            stitch_pair(gt, ag, label=label, out_path=out)
            print(f"wrote {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
