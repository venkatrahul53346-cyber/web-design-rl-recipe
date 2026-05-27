"""Compose 5 slide-ready PNG panels summarising the v5.1 Opus 4.7 evaluation.

Reads:
  report_figures/v51_results.csv               (110-trial Part 1 eval)
  report_figures/perturbation_results.csv      (gibberish + oracle anchors)
  report_figures/adversarial_results.csv       (screenshot-embed cheat)
  report_figures/pairs_v51/*.png               (best/worst stitched GT-vs-agent)

Writes:
  report_figures/slides/A_per_task_spread.png
  report_figures/slides/B_best_vs_worst_signals.png
  report_figures/slides/C_adversarial_anchors.png
  report_figures/slides/D_opus_failure_modes.png
  report_figures/slides/E_signal_discrimination.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from PIL import Image
from scipy.stats import spearmanr

REPO = Path(__file__).resolve().parent.parent
FIG = REPO / "report_figures"
OUT = FIG / "slides"
OUT.mkdir(parents=True, exist_ok=True)

SIGNAL_COLS = ["bm_position", "bm_text", "bm_color", "bm_font",
               "bm_border", "bm_size", "bm_recall", "tree_bleu",
               "visual_ssim"]
WEIGHTS = {"bm_position": 0.20, "bm_text": 0.10, "bm_color": 0.15,
           "bm_font": 0.10, "bm_border": 0.00, "bm_size": 0.05,
           "bm_recall": 0.15, "tree_bleu": 0.20, "visual_ssim": 0.05}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 12,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titleweight": "bold",
    "axes.titlesize": 14,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

TASK_LABELS = {
    "auth_glassy-001": "auth (glassy)",
    "pricing_dark-001": "pricing (dark)",
    "saas_minimal-001": "saas (minimal)",
    "docs_mono-001": "docs (mono)",
    "dashboard_dense-001": "dashboard (dense)",
    "portfolio_neobrut-001": "portfolio (neobrut)",
    "government__dark_native_clean-001": "government (dark)",
    "hotel_booking__photo_warm_display-001": "hotel (photo)",
    "news_portal__editorial_dark-001": "news (dark)",
    "healthcare_clinic__glassy_pastel-001": "healthcare (glassy)",
    "product_splash__crypto_neon-001": "product splash (neon)",
}

DIFFICULTY = {
    "auth_glassy-001": "easy",
    "pricing_dark-001": "easy",
    "saas_minimal-001": "easy",
    "docs_mono-001": "hard",
    "dashboard_dense-001": "hard",
    "portfolio_neobrut-001": "hard",
    "government__dark_native_clean-001": "hard",
    "hotel_booking__photo_warm_display-001": "hard",
    "news_portal__editorial_dark-001": "hard",
    "healthcare_clinic__glassy_pastel-001": "hard",
    "product_splash__crypto_neon-001": "hard",
}

EASY_C = "#2e7d32"
HARD_C = "#c62828"
ADV_C  = "#5e35b1"
GRID_C = "#e0e0e0"


def _viewport_crop(img_path: Path, max_h: int = 800) -> Image.Image:
    im = Image.open(img_path)
    if im.height > max_h:
        im = im.crop((0, 0, im.width, max_h))
    return im


# Panel A -------------------------------------------------------------------

def panel_a(df: pd.DataFrame) -> None:
    grouped = df.groupby("task")["score"].agg(["mean", "std", "min", "max", "count"])
    grouped = grouped.sort_values("mean", ascending=True)
    tasks = grouped.index.tolist()
    labels = [TASK_LABELS[t] for t in tasks]
    data = [df[df.task == t]["score"].values for t in tasks]
    colors = [EASY_C if DIFFICULTY[t] == "easy" else HARD_C for t in tasks]

    fig, ax = plt.subplots(figsize=(15, 8))
    bplots = ax.boxplot(data, vert=False, patch_artist=True, widths=0.55,
                        showfliers=True, medianprops={"color": "#222", "lw": 2})
    for patch, c in zip(bplots["boxes"], colors):
        patch.set_facecolor(c); patch.set_alpha(0.45)
    for median in bplots["medians"]:
        median.set_linewidth(2.0)
    ax.set_yticks(range(1, len(tasks) + 1))
    ax.set_yticklabels(labels, fontsize=11)
    ax.set_xlim(-0.05, 1.05)
    ax.set_xlabel("v5.1 composite score (10 Opus 4.7 attempts per task)", fontsize=12)
    ax.axvline(0.05, color=ADV_C, linestyle=":", lw=1.2, alpha=0.7)
    ax.text(0.06, 0.5, "screenshot-embed cheat = 0.05", color=ADV_C, fontsize=9,
            rotation=90, va="bottom", ha="left", alpha=0.85)
    ax.axvline(1.0, color="#888", linestyle=":", lw=1.0, alpha=0.6)
    ax.text(0.99, 0.5, "oracle = 1.000", color="#666", fontsize=9,
            rotation=90, va="bottom", ha="right", alpha=0.85)
    ax.grid(axis="x", color=GRID_C, lw=0.5)

    for i, t in enumerate(tasks, start=1):
        spread = grouped.loc[t, "max"] - grouped.loc[t, "min"]
        n = int(grouped.loc[t, "count"])
        ax.text(grouped.loc[t, "max"] + 0.012, i,
                f"mu={grouped.loc[t,'mean']:.2f}  spread={spread:.2f}  n={n}",
                fontsize=9, va="center", color="#444")

    legend = [mpatches.Patch(color=EASY_C, alpha=0.5, label="saturated/easy task"),
              mpatches.Patch(color=HARD_C, alpha=0.5, label="hard task")]
    ax.legend(handles=legend, loc="lower right", frameon=False, fontsize=10)

    fig.suptitle("Per-task score distribution: Opus 4.7 x 11 web-design tasks (n=106)",
                 fontsize=15, fontweight="bold", y=0.97)
    fig.text(0.5, 0.92,
             "Spreads are wider on hard tasks (0.10-0.23) where models actually disagree; "
             "saturated tasks have tight spreads near the top of the score range.",
             ha="center", fontsize=11, color="#444")
    fig.tight_layout(rect=[0, 0, 1, 0.91])
    out = OUT / "A_per_task_spread.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


# Panel B -------------------------------------------------------------------

def panel_b(df: pd.DataFrame) -> None:
    """3 rows. Each row: best_pair (GT|agent stitched) | worst_pair | per-signal bar."""
    targets = [
        ("docs_mono-001", "docs (mono): 3-pane developer-doc layout"),
        ("portfolio_neobrut-001", "portfolio (neobrut): oversized italic + colour blocks"),
        ("government__dark_native_clean-001", "government (dark): dense civic forms"),
    ]

    fig = plt.figure(figsize=(20, 16))
    gs = fig.add_gridspec(3, 3, width_ratios=[1.0, 1.0, 1.6],
                          hspace=0.42, wspace=0.18)

    for row, (task, title) in enumerate(targets):
        sub = df[df.task == task].sort_values("score")
        worst = sub.iloc[0]
        best = sub.iloc[-1]

        worst_png = next((FIG / "pairs_v51").glob(f"{task}__worst__*.png"), None)
        best_png = next((FIG / "pairs_v51").glob(f"{task}__best__*.png"), None)

        ax_best = fig.add_subplot(gs[row, 0])
        if best_png:
            ax_best.imshow(_viewport_crop(best_png, max_h=1100))
        ax_best.set_xticks([]); ax_best.set_yticks([])
        ax_best.set_title(f"{title}\nBEST Opus run  -  score {best['score']:.3f}  (GT | agent)",
                          fontsize=11, loc="left", color=EASY_C)

        ax_worst = fig.add_subplot(gs[row, 1])
        if worst_png:
            ax_worst.imshow(_viewport_crop(worst_png, max_h=1100))
        ax_worst.set_xticks([]); ax_worst.set_yticks([])
        ax_worst.set_title(f"\nWORST Opus run  -  score {worst['score']:.3f}  (GT | agent)",
                           fontsize=11, loc="left", color=HARD_C)

        ax_bar = fig.add_subplot(gs[row, 2])
        deltas = [best[c] - worst[c] for c in SIGNAL_COLS]
        colors_bar = ["#2e7d32" if d >= 0 else "#c62828" for d in deltas]
        weights_arr = np.array([WEIGHTS[c] for c in SIGNAL_COLS])
        weighted_contrib = np.array(deltas) * weights_arr
        ypos = np.arange(len(SIGNAL_COLS))
        ax_bar.barh(ypos, deltas, color=colors_bar, alpha=0.30, label="raw delta")
        ax_bar.barh(ypos, weighted_contrib, color=colors_bar, alpha=0.95,
                    label="weighted contribution to composite")
        for y, d, w in zip(ypos, deltas, weighted_contrib):
            ax_bar.text(max(d, 0) + 0.012, y, f"{d:+.2f}  -> {w:+.3f}",
                        va="center", fontsize=9, color="#333")
        ax_bar.set_yticks(ypos)
        ax_bar.set_yticklabels([f"{c}  (w={WEIGHTS[c]:.2f})" for c in SIGNAL_COLS],
                               fontsize=10)
        ax_bar.set_xlabel("(best - worst) raw   |   * weight = contribution to composite spread")
        ax_bar.set_xlim(-0.10, 0.85)
        ax_bar.axvline(0, color="#888", lw=0.8)
        ax_bar.invert_yaxis()
        ax_bar.grid(axis="x", color=GRID_C, lw=0.4)
        ax_bar.set_title(f"per-signal contribution to composite spread = {best['score']-worst['score']:+.3f}",
                         fontsize=11, loc="left")
        if row == 0:
            ax_bar.legend(loc="lower right", fontsize=9, frameon=False)

    fig.suptitle("Best vs worst Opus run on 3 highest-spread tasks: what makes the difference",
                 fontsize=17, fontweight="bold", y=0.99)
    fig.text(0.5, 0.965,
             "Across all three tasks, bm_position and bm_recall do most of the discriminative work; "
             "bm_text, bm_border, bm_font barely move.",
             ha="center", fontsize=11, color="#444")
    out = OUT / "B_best_vs_worst_signals.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


# Panel C -------------------------------------------------------------------

def panel_c(df: pd.DataFrame) -> None:
    pert = pd.read_csv(FIG / "perturbation_results.csv")
    adv = pd.read_csv(FIG / "adversarial_results.csv")
    pert_auth = pert[pert.task == "auth_glassy-001"]
    real_auth_mean = df[df.task == "auth_glassy-001"]["score"].mean()

    cols = [
        ("gibberish",
         "random ASCII\nno CSS",
         float(pert_auth[pert_auth.severity == 0]["score"].iloc[0]),
         "every signal = 0",
         "#c62828"),
        ("screenshot embed",
         "<img src=GT.png>\nthe SSIM cheat",
         float(adv[adv.label == "screenshot_embed"]["score"].iloc[0]),
         "ssim=1.0  recall=tree=text=0\nweight ceiling at 0.05",
         ADV_C),
        ("structure only",
         "GT layout\ntext shuffled",
         float(pert_auth[pert_auth.severity == 1]["score"].iloc[0]),
         "layout signals fire\ntext+SSIM penalised",
         "#f9a825"),
        ("real Opus 4.7",
         "10-attempt mean\non this task",
         real_auth_mean,
         "actual model behaviour",
         "#1565c0"),
        ("oracle",
         "GT verbatim\n(byte-for-byte)",
         float(pert_auth[pert_auth.severity == 4]["score"].iloc[0]),
         "submission == ground truth",
         EASY_C),
    ]

    fig, ax = plt.subplots(figsize=(17, 9))
    xs = np.arange(len(cols))
    bars = ax.bar(xs, [c[2] for c in cols], color=[c[4] for c in cols], alpha=0.88,
                  edgecolor="white", lw=2, width=0.65)
    for x, c in zip(xs, cols):
        ax.text(x, c[2] + 0.015, f"{c[2]:.3f}", ha="center", fontsize=15,
                fontweight="bold", color=c[4])
    ax.set_xticks(xs)
    ax.set_xticklabels([c[0] for c in cols], fontsize=12, fontweight="bold")
    ax.set_ylim(0, 1.15)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_ylabel("v5.1 composite score", fontsize=12)
    ax.axhline(0.05, color=ADV_C, linestyle=":", lw=1.0, alpha=0.6)
    ax.text(-0.45, 0.07, "0.05  (SSIM weight ceiling)", color=ADV_C, fontsize=8, alpha=0.8)
    ax.axhline(1.0, color="#888", linestyle=":", lw=1.0, alpha=0.5)
    ax.text(-0.45, 1.02, "1.000  (oracle)", color="#666", fontsize=8, alpha=0.8)
    ax.grid(axis="y", color=GRID_C, lw=0.5)
    ax.set_axisbelow(True)

    # caption rows below x-tick labels
    for x, c in zip(xs, cols):
        ax.annotate(c[1], xy=(x, 0), xycoords=("data", "axes fraction"),
                    xytext=(0, -36), textcoords="offset points",
                    ha="center", fontsize=10, color="#333")
        ax.annotate(c[3], xy=(x, 0), xycoords=("data", "axes fraction"),
                    xytext=(0, -68), textcoords="offset points",
                    ha="center", fontsize=9, color="#666",
                    style="italic")

    fig.suptitle("The grader is correctly anchored: trivial cheats fall below 0.10, oracle hits 1.000",
                 fontsize=15, fontweight="bold", y=0.98)
    fig.text(0.5, 0.93,
             "Same task (auth_glassy-001, 6 pages). The visual_ssim=1.0 cheat is the strongest "
             "adversarial attack and it scores 0.05 - the SSIM weight ceiling.",
             ha="center", fontsize=11, color="#444")
    fig.tight_layout(rect=[0, 0.12, 1, 0.91])
    out = OUT / "C_adversarial_anchors.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


# Panel D -------------------------------------------------------------------

def panel_d(df: pd.DataFrame) -> None:
    """2x2 failure-mode taxonomy. Each cell is a worst-pair PNG with a clean caption."""
    cells = [
        ("Symmetric drift",
         "portfolio_neobrut-001",
         "GT has staggered colour blocks; Opus collapses to a regular 12-col grid.",
         "bm_position drops 0.16 -> 0.63 between worst and best run"),
        ("Column compression",
         "news_portal__editorial_dark-001",
         "GT uses narrow editorial measure (~40ch); Opus defaults to wide single column.",
         "bm_position + bm_recall both fall ~0.30 on affected runs"),
        ("Hero compression",
         "government__dark_native_clean-001",
         "GT has tall hero with whitespace; Opus crams content upward into the fold.",
         "bm_recall drops 0.46 (matched area), tree_bleu 0.22"),
        ("Density underproduction",
         "docs_mono-001",
         "GT shows full 3-pane mono layout; Opus collapses to dark single column.",
         "bm_recall drops 0.60, bm_position 0.47"),
    ]

    fig = plt.figure(figsize=(20, 15))
    gs = fig.add_gridspec(2, 2, hspace=0.55, wspace=0.20,
                          left=0.04, right=0.98, top=0.86, bottom=0.04)

    for i, (failure, task, what, signal_diag) in enumerate(cells):
        r, c = divmod(i, 2)
        ax = fig.add_subplot(gs[r, c])
        worst_png = next((FIG / "pairs_v51").glob(f"{task}__worst__*.png"), None)
        if worst_png is None:
            ax.text(0.5, 0.5, f"missing {task} worst", ha="center", va="center")
        else:
            ax.imshow(_viewport_crop(worst_png, max_h=1100))
        ax.set_xticks([]); ax.set_yticks([])
        worst_score = df[df.task == task]["score"].min()
        ax.set_title(f"{failure}  -  {task}   (worst run, score {worst_score:.3f})",
                     fontsize=13, loc="left", fontweight="bold")
        ax.text(0.0, -0.14, "what:  " + what,
                transform=ax.transAxes, fontsize=11, color="#222", va="top")
        ax.text(0.0, -0.22, "signal:  " + signal_diag,
                transform=ax.transAxes, fontsize=11, color="#7a1f1f",
                va="top", style="italic")

    fig.suptitle("What Opus 4.7 consistently struggles with: four canonical failure modes",
                 fontsize=17, fontweight="bold", y=0.965)
    fig.text(0.5, 0.92,
             "Each panel: GT (left half) | agent worst run (right half). The signal that "
             "exposes each failure is named below.",
             ha="center", fontsize=11, color="#444")
    out = OUT / "D_opus_failure_modes.png"
    fig.savefig(out, dpi=110, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


# Panel E -------------------------------------------------------------------

def panel_e(df: pd.DataFrame) -> None:
    rows = []
    for c in SIGNAL_COLS:
        rho = spearmanr(df[c], df["score"]).correlation
        weighted_var = (WEIGHTS[c] * df[c].std()) ** 2
        rows.append({"signal": c, "weight": WEIGHTS[c], "mean": df[c].mean(),
                     "std": df[c].std(), "spearman": rho,
                     "weighted_var": weighted_var})
    sigdf = pd.DataFrame(rows)
    total = sigdf["weighted_var"].sum() if sigdf["weighted_var"].sum() > 0 else 1.0
    sigdf["variance_share"] = sigdf["weighted_var"] / total
    sigdf = sigdf.sort_values("variance_share", ascending=True)

    fig, axes = plt.subplots(1, 2, figsize=(18, 8), gridspec_kw={"width_ratios": [1.2, 1.0]})

    ax0 = axes[0]
    ypos = np.arange(len(sigdf))
    ax0.barh(ypos, sigdf["variance_share"], color="#1565c0", alpha=0.9)
    for y, row in zip(ypos, sigdf.itertuples()):
        ax0.text(row.variance_share + 0.005, y,
                 f"{row.variance_share*100:.1f}%   (w={row.weight:.2f}, s={row.std:.2f})",
                 va="center", fontsize=10)
    ax0.set_yticks(ypos)
    ax0.set_yticklabels(sigdf["signal"], fontsize=11)
    ax0.set_xlabel("share of composite variance attributable to signal ((w*sigma)^2 normalised)")
    ax0.set_xlim(0, 0.7)
    ax0.grid(axis="x", color=GRID_C, lw=0.5)
    ax0.set_title("Where the score actually comes from", fontsize=13, loc="left")

    ax1 = axes[1]
    sigdf2 = sigdf.sort_values("spearman", ascending=True)
    ypos2 = np.arange(len(sigdf2))
    colors_e = ["#c62828" if v < 0 else "#2e7d32" for v in sigdf2["spearman"]]
    ax1.barh(ypos2, sigdf2["spearman"], color=colors_e, alpha=0.85)
    for y, row in zip(ypos2, sigdf2.itertuples()):
        ax1.text(row.spearman + (0.015 if row.spearman > 0 else -0.015), y,
                 f"{row.spearman:+.2f}",
                 va="center",
                 ha="left" if row.spearman > 0 else "right",
                 fontsize=10, color="#222")
    ax1.set_yticks(ypos2)
    ax1.set_yticklabels(sigdf2["signal"], fontsize=11)
    ax1.set_xlabel("Spearman rho between signal and composite score")
    ax1.set_xlim(-0.2, 1.0)
    ax1.axvline(0, color="#888", lw=0.8)
    ax1.grid(axis="x", color=GRID_C, lw=0.5)
    ax1.set_title("How well each signal tracks overall quality", fontsize=13, loc="left")

    fig.suptitle("Signal contributions to score discrimination (n=106 Opus 4.7 trials)",
                 fontsize=16, fontweight="bold", y=0.99)
    fig.text(0.5, 0.94,
             "bm_position carries 57% of composite variance - the single most discriminative signal. "
             "bm_text correlates strongly with quality (rho=+0.90) but doesn't separate runs (low sigma).",
             ha="center", fontsize=11, color="#444")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    out = OUT / "E_signal_discrimination.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def main() -> int:
    df = pd.read_csv(FIG / "v51_results.csv")
    panel_a(df)
    panel_b(df)
    panel_c(df)
    panel_d(df)
    panel_e(df)
    return 0


if __name__ == "__main__":
    sys.exit(main())
