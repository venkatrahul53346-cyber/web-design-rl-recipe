"""Aggregate Harbor job results into the final report.

Reads ``jobs/<run-name>/<task>__<trial-id>/{config.json,verifier/reward.json}``
for every trial, groups by task name, and prints:

- per-task mean ± std, min, max across attempts
- per-signal breakdown (layout / visual / component / text / style)
- markdown tables ready for REPORT.md

Usage:
    .venv/bin/python -m src.report_aggregate jobs/final-eval-opus-v34/
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


SIGNALS = ("layout", "visual", "component", "text", "style", "combined")


def _load_trial(trial_dir: Path) -> Dict | None:
    cfg_path = trial_dir / "config.json"
    rwd_path = trial_dir / "verifier" / "reward.json"
    if not (cfg_path.exists() and rwd_path.exists()):
        return None
    cfg = json.loads(cfg_path.read_text())
    rwd = json.loads(rwd_path.read_text())
    task_path = cfg.get("task", {}).get("path", "") or cfg.get("task_path", "")
    task = Path(task_path).name if task_path else trial_dir.name.split("__")[0]
    model = cfg.get("agent", {}).get("model_name") or "unknown"
    return {"task": task, "model": model, "reward": rwd, "trial": trial_dir.name}


def _per_signal_means(rewards: List[Dict]) -> Dict[str, float]:
    """Average each <page>_<signal> within rewards, then average per
    signal across pages. Returns one number per signal."""
    by_signal: Dict[str, List[float]] = defaultdict(list)
    for r in rewards:
        per_signal_in_this_reward: Dict[str, List[float]] = defaultdict(list)
        for k, v in r.items():
            if not isinstance(v, (int, float)):
                continue
            for s in SIGNALS:
                if k.endswith(f"_{s}"):
                    per_signal_in_this_reward[s].append(float(v))
        for s, vals in per_signal_in_this_reward.items():
            if vals:
                by_signal[s].append(statistics.fmean(vals))
    return {s: statistics.fmean(by_signal[s]) if by_signal.get(s) else float("nan")
            for s in SIGNALS}


def _stats(scores: List[float]) -> Dict[str, float]:
    if not scores:
        return {"n": 0, "mean": float("nan"), "std": float("nan"),
                "min": float("nan"), "max": float("nan")}
    return {
        "n": len(scores),
        "mean": statistics.fmean(scores),
        "std": statistics.pstdev(scores) if len(scores) > 1 else 0.0,
        "min": min(scores),
        "max": max(scores),
    }


def aggregate(jobs_dir: Path) -> Dict:
    by_task: Dict[str, List[Dict]] = defaultdict(list)
    for trial_dir in sorted(jobs_dir.iterdir()):
        if not trial_dir.is_dir():
            continue
        loaded = _load_trial(trial_dir)
        if loaded is None:
            continue
        by_task[loaded["task"]].append(loaded)

    out: Dict = {"jobs_dir": str(jobs_dir), "by_task": {}}
    for task, trials in by_task.items():
        scores = [t["reward"].get("score", float("nan")) for t in trials]
        signals = _per_signal_means([t["reward"] for t in trials])
        out["by_task"][task] = {
            "n_trials": len(trials),
            "models": sorted({t["model"] for t in trials}),
            "score": _stats([s for s in scores if not math.isnan(s)]),
            "signals": signals,
            "trials": [
                {"trial": t["trial"], "score": t["reward"].get("score")}
                for t in sorted(trials, key=lambda x: x["reward"].get("score", 0))
            ],
        }
    return out


def render_markdown(agg: Dict) -> str:
    lines: List[str] = []
    lines.append(f"### Aggregated from `{agg['jobs_dir']}`")
    lines.append("")
    lines.append("| Task | n | Mean | Std | Min | Max | Layout | Visual | Comp | Text | Style |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    rows = sorted(agg["by_task"].items(),
                  key=lambda kv: -kv[1]["score"]["mean"]
                  if not math.isnan(kv[1]["score"]["mean"]) else 0)
    for task, d in rows:
        s = d["score"]
        sig = d["signals"]
        lines.append(
            f"| `{task}` | {s['n']} | "
            f"{s['mean']:.3f} | {s['std']:.3f} | {s['min']:.3f} | {s['max']:.3f} | "
            f"{sig.get('layout',float('nan')):.3f} | "
            f"{sig.get('visual',float('nan')):.3f} | "
            f"{sig.get('component',float('nan')):.3f} | "
            f"{sig.get('text',float('nan')):.3f} | "
            f"{sig.get('style',float('nan')):.3f} |"
        )
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("jobs_dir", type=Path)
    p.add_argument("--json", action="store_true",
                   help="Dump full aggregation as JSON to stdout instead of markdown.")
    args = p.parse_args()

    if not args.jobs_dir.is_dir():
        print(f"not a directory: {args.jobs_dir}", file=sys.stderr)
        return 1

    agg = aggregate(args.jobs_dir)
    if args.json:
        print(json.dumps(agg, indent=2))
    else:
        print(render_markdown(agg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
