"""Generate the visual report figures from a Harbor jobs directory.

Outputs:
  - <out_dir>/scores_per_task.png   — box plot of score distribution per task
  - <out_dir>/signals_per_task.png  — stacked bar of per-signal contribution
  - <out_dir>/scores.csv            — long-form trial-level data for further analysis

Usage:
  .venv/bin/python -m src.report_plots jobs/final-eval-opus-v34 --out report_figures/
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

# Lazy-import matplotlib so the aggregator can run without it.
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


SIGNALS = ("layout", "visual", "component", "text", "style")
SIGNAL_WEIGHTS = {
    "layout": 0.30, "visual": 0.25, "component": 0.20,
    "text": 0.15, "style": 0.10,
}


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
        task = Path(cfg.get("task", {}).get("path", "")).name or trial_dir.name.split("__")[0]
        score = rwd.get("score")
        if score is None:
            continue
        per_signal: Dict[str, List[float]] = defaultdict(list)
        for k, v in rwd.items():
            if not isinstance(v, (int, float)):
                continue
            for s in SIGNALS:
                if k.endswith(f"_{s}"):
                    per_signal[s].append(float(v))
        signals = {s: statistics.fmean(per_signal[s]) if per_signal.get(s) else float("nan")
                   for s in SIGNALS}
        rows.append({
            "task": task, "trial": trial_dir.name, "score": float(score),
            "model": cfg.get("agent", {}).get("model_name", "unknown"),
            **{f"sig_{s}": signals[s] for s in SIGNALS},
        })
    return rows


def write_csv(rows: List[Dict], out_path: Path) -> None:
    if not rows:
        return
    keys = list(rows[0].keys())
    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def plot_score_box(rows: List[Dict], out_path: Path) -> None:
    if plt is None:
        print("matplotlib not installed — skipping plots", file=sys.stderr)
        return
    by_task: Dict[str, List[float]] = defaultdict(list)
    for r in rows:
        by_task[r["task"]].append(r["score"])
    tasks_sorted = sorted(by_task.items(), key=lambda kv: -statistics.fmean(kv[1]))
    labels = [t for t, _ in tasks_sorted]
    data = [s for _, s in tasks_sorted]

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.boxplot(data, tick_labels=labels, vert=True, showmeans=True,
               meanprops={"marker": "D", "markerfacecolor": "red",
                          "markeredgecolor": "red", "markersize": 6})
    ax.set_ylabel("Reward score (v3.4 grader)")
    ax.set_title("Opus 4.7 × 10 attempts — score distribution per task")
    ax.set_ylim(0, 1)
    ax.axhline(0.5, color="gray", linestyle="--", alpha=0.4, linewidth=0.8)
    ax.grid(True, axis="y", alpha=0.25)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_signal_breakdown(rows: List[Dict], out_path: Path) -> None:
    if plt is None:
        return
    by_task: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        for s in SIGNALS:
            v = r.get(f"sig_{s}")
            if v is None or (isinstance(v, float) and math.isnan(v)):
                continue
            by_task[r["task"]][s].append(v)

    tasks_sorted = sorted(
        by_task.items(),
        key=lambda kv: -sum(SIGNAL_WEIGHTS[s] * statistics.fmean(kv[1][s])
                            for s in SIGNALS if kv[1].get(s)),
    )

    fig, ax = plt.subplots(figsize=(11, 5.5))
    bottoms = [0.0] * len(tasks_sorted)
    colors = {"layout": "#3B82F6", "visual": "#10B981", "component": "#F59E0B",
              "text": "#EF4444", "style": "#A78BFA"}
    for s in SIGNALS:
        heights = []
        for _, sigdict in tasks_sorted:
            vals = sigdict.get(s, [])
            mean = statistics.fmean(vals) if vals else 0.0
            heights.append(SIGNAL_WEIGHTS[s] * mean)
        ax.bar([t for t, _ in tasks_sorted], heights, bottom=bottoms,
               label=f"{s} ({SIGNAL_WEIGHTS[s]:.0%})", color=colors[s])
        bottoms = [b + h for b, h in zip(bottoms, heights)]

    ax.set_ylabel("Weighted contribution to mean score")
    ax.set_title("Per-signal contribution to mean reward (Opus 4.7 × 10)")
    ax.set_ylim(0, 1)
    ax.legend(loc="upper right", fontsize=9)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("jobs_dir", type=Path)
    p.add_argument("--out", type=Path, default=Path("report_figures"))
    args = p.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    rows = load_trials(args.jobs_dir)
    if not rows:
        print(f"no trials with reward.json found under {args.jobs_dir}", file=sys.stderr)
        return 1

    write_csv(rows, args.out / "scores.csv")
    print(f"wrote {args.out/'scores.csv'} ({len(rows)} trials)")

    plot_score_box(rows, args.out / "scores_per_task.png")
    print(f"wrote {args.out/'scores_per_task.png'}")

    plot_signal_breakdown(rows, args.out / "signals_per_task.png")
    print(f"wrote {args.out/'signals_per_task.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
