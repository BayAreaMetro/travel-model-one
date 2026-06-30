"""Plot renderer for the truck trip distribution model.

All matplotlib code lives here. No computation, no openpyxl.
Reads from a fully populated ``ReportData`` object and writes PNG files.

Output files written to ``plots_dir``
--------------------------------------
``tlfd_comparison.png``
    Always. One subplot per successful run — bars = observed TLFD, line =
    modelled TLFD, dashed vertical lines for observed/modelled average trip
    length (ATL).

``friction_curves.png``
    Always. All successful runs on one axes, curves normalised to F(1 min)=1,
    legend entries include calibrated b and c values.

``calibration_loss.png``
    Always. One subplot per successful run — optimizer loss (log-scale)
    sampled every 10 evaluations, plus a final-loss marker.

``pa_residuals_{short_name}_{geo_col}.png``
    One file per run × ``geo_agg_col``, only when ``geo_agg_cols`` is set.
    Grouped bar chart — target attractions vs modelled attractions by
    geographic unit.

``od_scatter_{short_name}.png``
    One file per run with ``target_od_path`` set. Log-log scatter of observed
    vs modelled OD flows, with a 1:1 reference line, fitted trend line, slope
    and R² annotations.

``od_residuals_{short_name}_{geo_col}.png``
    One file per run × ``geo_agg_col``, only when both ``target_od_path`` AND
    ``geo_agg_cols`` are set. Diverging colour heatmap showing (mod − obs) /
    obs × 100 % for each origin × destination geography pair.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from src.models.trip_distribution.friction import gamma_ff
from .report import ReportData, RunReport


# ---------------------------------------------------------------------------
# Colour constants
# ---------------------------------------------------------------------------

_BLUE   = "#4472C4"   # observed / target data
_ORANGE = "#ED7D31"   # modelled data (bar charts)
_RED    = "#C0392B"   # modelled line / trend line


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok_runs(report: ReportData) -> list[RunReport]:
    """Return only the successfully completed runs."""
    return [r for r in report.runs if r.status == "OK"]


def _subplot_grid(
    n: int,
    col_width: float = 5.0,
    row_height: float = 5.0,
    max_cols: int = 3,
) -> tuple:
    """Return (fig, axes 2-D array) for *n* subplots arranged in a grid."""
    n_cols = min(n, max_cols)
    n_rows = math.ceil(n / n_cols)
    fig, axes = plt.subplots(
        n_rows, n_cols,
        figsize=(col_width * n_cols, row_height * n_rows),
        squeeze=False,
    )
    # Hide any unused cells
    for idx in range(n, n_rows * n_cols):
        axes[idx // n_cols][idx % n_cols].set_visible(False)
    return fig, axes


def _no_runs_fig(path: Path) -> None:
    """Write a placeholder PNG when there are no successful runs."""
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.text(0.5, 0.5, "No successful runs available",
            transform=ax.transAxes, ha="center", va="center",
            fontsize=12, color="gray")
    ax.set_axis_off()
    plt.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Individual plot functions
# ---------------------------------------------------------------------------

def _plot_tlfd_comparison(report: ReportData, plots_dir: Path) -> None:
    """Observed vs modelled TLFD bars + line, one subplot per run.

    Bars represent observed shares; the red line shows modelled shares.
    Dashed vertical lines mark observed (blue) and modelled (red) ATL.
    """
    ok = _ok_runs(report)
    out = plots_dir / "tlfd_comparison.png"

    if not ok:
        _no_runs_fig(out)
        return

    fig, axes = _subplot_grid(len(ok), col_width=5.5, row_height=5.0)

    for idx, run in enumerate(ok):
        ax = axes[idx // min(len(ok), 3)][idx % min(len(ok), 3)]
        tbl = run.tlfd_table

        starts = tbl["bin_start"].to_numpy()
        ends   = tbl["bin_end"].to_numpy()
        midpts = (starts + ends) / 2.0
        widths = ends - starts
        obs_s  = tbl["observed_share"].to_numpy()
        mod_s  = tbl["modeled_share"].to_numpy()

        obs_atl = float((midpts * obs_s).sum())
        mod_atl = float((midpts * mod_s).sum())

        # Bars for observed
        ax.bar(starts, obs_s, width=widths, align="edge",
               color=_BLUE, alpha=0.60, label="Observed", zorder=2)
        # Line for modelled
        ax.plot(midpts, mod_s, "o-", color=_RED,
                linewidth=1.6, markersize=5, label="Modelled", zorder=3)
        # ATL vertical lines
        ax.axvline(obs_atl, color=_BLUE, linestyle="--", linewidth=1.2,
                   label=f"Obs ATL  {obs_atl:.1f} min", alpha=0.85)
        ax.axvline(mod_atl, color=_RED, linestyle="--", linewidth=1.2,
                   label=f"Mod ATL  {mod_atl:.1f} min", alpha=0.85)

        ax.set_title(run.run_name, fontweight="bold")
        ax.set_xlabel("Travel time (min)")
        ax.set_ylabel("Share")
        ax.set_xticks(starts)
        ax.set_xticklabels([str(int(v)) for v in starts], rotation=45, ha="right")
        ax.legend(fontsize=7, loc="upper right")
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle("TLFD Comparison — Observed vs Modelled",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_friction_curves(report: ReportData, plots_dir: Path) -> None:
    """Normalised gamma F(t) curves for all successful runs on one axes.

    Each curve is normalised so F(1 min) = 1, allowing shape comparison
    across runs regardless of scale. Legend entries show calibrated b and c.
    """
    ok = [r for r in report.runs if r.status == "OK" and r.b_final is not None]
    out = plots_dir / "friction_curves.png"

    fig, ax = plt.subplots(figsize=(8, 5))

    if not ok:
        ax.text(0.5, 0.5, "No successful runs available",
                transform=ax.transAxes, ha="center", va="center",
                fontsize=12, color="gray")
        ax.set_axis_off()
    else:
        # Determine sensible t range from observed TLFD upper bounds
        t_max = 120.0
        for r in ok:
            if r.tlfd_table is not None:
                t_max = max(t_max, float(r.tlfd_table["bin_end"].max()))

        t = np.linspace(1.0, t_max, 500)
        colors = plt.cm.tab10.colors

        for i, run in enumerate(ok):
            f = gamma_ff(t, run.b_final, run.c_final)
            f0 = f[0]
            f_norm = f / f0 if f0 > 0.0 else f
            label = (
                f"{run.run_name}"
                f"  (b = {run.b_final:.3f},  c = {run.c_final:.4f})"
            )
            ax.plot(t, f_norm, linewidth=2.0, color=colors[i % 10], label=label)

        ax.set_xlabel("Travel time (min)")
        ax.set_ylabel("F(t) / F(1 min)  [normalised]")
        ax.set_title("Gamma Friction Factor Curves", fontweight="bold")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)

    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_calibration_loss(report: ReportData, plots_dir: Path) -> None:
    """Optimizer loss convergence, log-scale y-axis, one subplot per run.

    Points are sampled every 10 function evaluations (from ``loss_history``).
    The dashed horizontal line marks the final loss at termination.
    """
    ok = [r for r in report.runs if r.status == "OK" and r.final_loss is not None]
    out = plots_dir / "calibration_loss.png"

    if not ok:
        _no_runs_fig(out)
        return

    fig, axes = _subplot_grid(len(ok), col_width=5.0, row_height=4.0)

    for idx, run in enumerate(ok):
        ax = axes[idx // min(len(ok), 3)][idx % min(len(ok), 3)]

        if run.loss_history:
            x_pts = [10 * (k + 1) for k in range(len(run.loss_history))]
            ax.semilogy(x_pts, run.loss_history, "o-",
                        color=_BLUE, linewidth=1.5, markersize=5,
                        label="Loss (every 10 evals)")

        # Final-loss marker and horizontal guide
        ax.axhline(run.final_loss, color=_RED, linestyle="--",
                   linewidth=1.5, alpha=0.85,
                   label=f"Final loss: {run.final_loss:.4g}")
        ax.scatter([run.n_iters], [run.final_loss],
                   color=_RED, s=60, zorder=5)

        ax.set_title(run.run_name, fontweight="bold")
        ax.set_xlabel("Optimizer evaluations")
        ax.set_ylabel("Loss")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3, which="both")

    fig.suptitle("Calibration Loss Convergence",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_pa_residuals(report: ReportData, plots_dir: Path) -> None:
    """Grouped bar chart — target vs modelled attractions by geography.

    One PNG per run × geographic column.  The attraction comparison is shown
    because production residuals are near-zero by IPF construction.
    """
    for run in report.runs:
        if run.status != "OK" or not run.pa_geo:
            continue

        for geo_col, gdf in run.pa_geo.items():
            n_groups = len(gdf)
            fig_w = max(7.0, n_groups * 1.8)
            fig, ax = plt.subplots(figsize=(fig_w, 5))

            x = np.arange(n_groups)
            w = 0.35

            ax.bar(x - w / 2, gdf["target_A"], width=w,
                   color=_BLUE, alpha=0.85, label="Target A", zorder=2)
            ax.bar(x + w / 2, gdf["modeled_A"], width=w,
                   color=_ORANGE, alpha=0.85, label="Modelled A", zorder=2)

            geo_labels = gdf[geo_col].astype(str).tolist()
            ax.set_xticks(x)
            ax.set_xticklabels(geo_labels, rotation=30, ha="right")
            ax.set_xlabel(geo_col.replace("_", " ").title())
            ax.set_ylabel("Daily vehicle trips")
            ax.set_title(
                f"{run.run_name} — Attractions by "
                f"{geo_col.replace('_', ' ')}",
                fontweight="bold",
            )
            ax.legend(fontsize=9)
            ax.grid(axis="y", alpha=0.3)

            plt.tight_layout()
            fname = f"pa_residuals_{run.short_name}_{geo_col}.png"
            fig.savefig(plots_dir / fname, dpi=150, bbox_inches="tight")
            plt.close(fig)


def _plot_od_scatter(report: ReportData, plots_dir: Path) -> None:
    """Log-log scatter of observed vs modelled OD flows, one PNG per run.

    Shows only pairs where both observed and modelled > 0. Overlays:
      - 1:1 perfect-fit reference line (dashed black)
      - Fitted trend line (solid red) using the stored ``slope_log`` and
        ``intercept_log`` from the log-log regression
      - R² and slope text box (upper-left)
    """
    for run in report.runs:
        if run.status != "OK" or run.od_pairs is None:
            continue

        obs = run.od_pairs["observed_trips"].to_numpy(dtype=np.float64)
        mod = run.od_pairs["modeled_trips"].to_numpy(dtype=np.float64)
        mask = (obs > 0.0) & (mod > 0.0)

        if mask.sum() < 2:
            continue

        obs_p = obs[mask]
        mod_p = mod[mask]

        fig, ax = plt.subplots(figsize=(7, 6))

        # Scatter
        ax.scatter(obs_p, mod_p, alpha=0.35, s=18, color=_BLUE,
                   label="OD pairs", zorder=2)

        # 1:1 reference line
        v_min = min(float(obs_p.min()), float(mod_p.min()))
        v_max = max(float(obs_p.max()), float(mod_p.max()))
        ax.plot([v_min, v_max], [v_min, v_max],
                color="black", linestyle="--", linewidth=1.5,
                label="1:1 line", zorder=3)

        # Fitted trend line (slope + intercept both in log-space → power law)
        if run.slope_log is not None and run.intercept_log is not None:
            log_range = np.linspace(np.log(v_min), np.log(v_max), 200)
            fit_vals = np.exp(run.slope_log * log_range + run.intercept_log)
            ax.plot(np.exp(log_range), fit_vals,
                    color=_RED, linestyle="-", linewidth=1.5,
                    label=f"Fit  (slope = {run.slope_log:.3f})", zorder=4)

        # Annotation box
        if run.r2_log is not None:
            lines = [f"R² = {run.r2_log:.3f}"]
            if run.slope_log is not None:
                lines.append(f"slope = {run.slope_log:.3f}")
            ax.text(
                0.05, 0.95, "\n".join(lines),
                transform=ax.transAxes, va="top", ha="left", fontsize=10,
                bbox=dict(boxstyle="round,pad=0.4",
                          facecolor="wheat", alpha=0.75),
            )

        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Observed OD trips (log scale)")
        ax.set_ylabel("Modelled OD trips (log scale)")
        ax.set_title(f"OD Scatter — {run.run_name}", fontweight="bold")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3, which="both")

        plt.tight_layout()
        fname = f"od_scatter_{run.short_name}.png"
        fig.savefig(plots_dir / fname, dpi=150, bbox_inches="tight")
        plt.close(fig)


def _plot_od_residuals(report: ReportData, plots_dir: Path) -> None:
    """Diverging heatmap of OD residuals aggregated to geography, per run × geo.

    Cell colour = (modelled − observed) / observed × 100 %.
    Blue = under-prediction, red = over-prediction, white = perfect fit.
    Cells are annotated with their % value when the matrix is small (≤ 100 cells).
    """
    for run in report.runs:
        if run.status != "OK" or not run.od_geo:
            continue

        for geo_col, pivot in run.od_geo.items():
            if pivot.empty:
                continue

            data = pivot.to_numpy(dtype=np.float64)
            n_r, n_c = data.shape

            # Symmetric colour range: 95th-percentile of absolute values
            abs_vals = np.abs(data[~np.isnan(data)])
            if len(abs_vals) == 0:
                continue
            vmax = (
                float(np.percentile(abs_vals, 95))
                if len(abs_vals) > 1
                else float(abs_vals[0])
            )
            if vmax < 1.0:
                vmax = 1.0

            fig_w = max(6.0, n_c * 1.3)
            fig_h = max(5.0, n_r * 1.1)
            fig, ax = plt.subplots(figsize=(fig_w, fig_h))

            im = ax.imshow(data, cmap="RdBu_r",
                           vmin=-vmax, vmax=vmax, aspect="auto")

            col_labels = [str(c) for c in pivot.columns]
            row_labels = [str(r) for r in pivot.index]

            ax.set_xticks(np.arange(n_c))
            ax.set_xticklabels(col_labels, rotation=45, ha="right", fontsize=9)
            ax.set_yticks(np.arange(n_r))
            ax.set_yticklabels(row_labels, fontsize=9)
            ax.set_xlabel(f"Destination {geo_col}", labelpad=10)
            ax.set_ylabel(f"Origin {geo_col}", labelpad=8)
            ax.set_title(
                f"OD Residuals — {run.run_name}\n"
                f"by {geo_col}  [(mod − obs) / obs × 100 %]",
                fontweight="bold",
            )

            plt.colorbar(im, ax=ax, label="Residual (%)", shrink=0.8)

            # Annotate cells when the matrix is small enough to read
            if n_r * n_c <= 100:
                for i in range(n_r):
                    for j in range(n_c):
                        v = data[i, j]
                        if not np.isnan(v):
                            txt_color = (
                                "white" if abs(v) > vmax * 0.55 else "black"
                            )
                            ax.text(j, i, f"{v:.0f}%",
                                    ha="center", va="center",
                                    fontsize=8, color=txt_color)

            plt.tight_layout()
            fname = f"od_residuals_{run.short_name}_{geo_col}.png"
            fig.savefig(plots_dir / fname, dpi=150, bbox_inches="tight")
            plt.close(fig)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_plots(report: ReportData, plots_dir: Path) -> None:
    """Write all validation PNG figures to ``plots_dir``.

    Always written (even if all runs failed):
      - ``tlfd_comparison.png``
      - ``friction_curves.png``
      - ``calibration_loss.png``

    Conditional (based on config flags and per-run settings):
      - ``pa_residuals_{sn}_{geo}.png``  — when ``geo_agg_cols`` is configured
      - ``od_scatter_{sn}.png``          — when ``target_od_path`` is set
      - ``od_residuals_{sn}_{geo}.png``  — when both OD and geo are configured

    Parameters
    ----------
    report : ReportData
        Fully populated report data object from ``build_report_data``.
    plots_dir : Path
        Directory to write PNG files into. Must already exist.

    Raises
    ------
    OSError
        If ``plots_dir`` does not exist or is not writable.
    """
    _plot_tlfd_comparison(report, plots_dir)
    _plot_friction_curves(report, plots_dir)
    _plot_calibration_loss(report, plots_dir)

    if report.has_geo:
        _plot_pa_residuals(report, plots_dir)

    if report.has_od:
        _plot_od_scatter(report, plots_dir)

    if report.has_od and report.has_geo:
        _plot_od_residuals(report, plots_dir)
