"""
validation.py
-------------
All validation plots and diagnostics. Nothing here changes the model —
it only reads results and produces figures.

Plots produced
--------------
1. plot_tlfd_comparison     : observed vs modeled TLFD per truck type
2. plot_friction_curves     : gamma F(t) curves for all truck types
3. plot_od_scatter          : observed vs modeled OD scatter (log scale)
4. plot_od_residuals        : spatial heatmap of (modeled - observed) / observed
5. plot_calibration_loss    : loss history during optimization
6. print_validation_summary : tabular summary of key stats
"""

from pathlib import Path
from typing import Dict, Optional

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from .config import TRUCK_TYPES, TLFD_BINS
from .calibration import CalibrationResult, compute_tlfd, avg_trip_length
from .friction import GammaParams, evaluate_ff_curve
from .gravity import GravityResult


# ── Color scheme ───────────────────────────────────────────────────────────────
TRUCK_COLORS = {
    "light_trucks":  "#2196F3",   # blue
    "medium_trucks": "#FF9800",   # orange
    "heavy_trucks":  "#4CAF50",   # green
}

TRUCK_LABELS = {
    "light_trucks":  "Light Trucks",
    "medium_trucks": "Medium Trucks",
    "heavy_trucks":  "Heavy Trucks",
}


# ── Plot 1: TLFD comparison ────────────────────────────────────────────────────

def plot_tlfd_comparison(
    calibration_results: Dict[str, CalibrationResult],
    output_path: Optional[Path] = None,
) -> plt.Figure:
    """
    Side-by-side bar charts of observed vs modeled TLFD for each truck type.

    One subplot per truck type. Bars = observed; line = modeled.
    Annotates average trip length for both.
    """
    n = len(TRUCK_TYPES)
    fig, axes = plt.subplots(1, n, figsize=(6 * n, 5), sharey=False)
    if n == 1:
        axes = [axes]

    bin_mids = 0.5 * (TLFD_BINS[:-1] + TLFD_BINS[1:])
    bin_width = TLFD_BINS[1] - TLFD_BINS[0]

    for ax, tt in zip(axes, TRUCK_TYPES):
        r = calibration_results[tt]
        color = TRUCK_COLORS[tt]

        # Bars: observed
        ax.bar(
            bin_mids, r.observed_tlfd * 100,
            width=bin_width * 0.8,
            color=color, alpha=0.5,
            label="Observed (statewide)",
        )
        # Line: modeled
        ax.plot(
            bin_mids, r.modeled_tlfd * 100,
            color=color, linewidth=2.5, marker="o", markersize=4,
            label="Modeled (gravity)",
        )

        # Avg trip length annotations
        ax.axvline(r.observed_avg_tl, color="gray", linestyle="--", linewidth=1,
                   label=f"Obs ATL = {r.observed_avg_tl:.1f} min")
        ax.axvline(r.modeled_avg_tl, color=color, linestyle="--", linewidth=1.5,
                   label=f"Mod ATL = {r.modeled_avg_tl:.1f} min")

        ax.set_title(TRUCK_LABELS[tt], fontsize=13, fontweight="bold")
        ax.set_xlabel("Travel Time (min)", fontsize=11)
        ax.set_ylabel("Share of Trips (%)", fontsize=11)
        ax.legend(fontsize=9)
        ax.set_xlim(0, TLFD_BINS[-1])
        ax.grid(axis="y", alpha=0.3)

        # Annotate gamma params
        ax.text(
            0.97, 0.95,
            f"b = {r.b:.3f}\nc = {r.c:.4f}",
            transform=ax.transAxes,
            ha="right", va="top",
            fontsize=9,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7),
        )

    fig.suptitle("TLFD: Observed vs Modeled", fontsize=15, fontweight="bold", y=1.02)
    fig.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"  Saved: {output_path}")

    return fig


# ── Plot 2: Friction factor curves ────────────────────────────────────────────

def plot_friction_curves(
    params: Dict[str, GammaParams],
    output_path: Optional[Path] = None,
) -> plt.Figure:
    """
    Plot F(t) curves for all truck types on one axis.
    Shows how deterrence varies with travel time by truck class.
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    for tt in TRUCK_TYPES:
        p = params[tt]
        t_vals, f_vals = evaluate_ff_curve(p.b, p.c, t_max=120)
        # Normalize so curves are comparable (max = 1)
        f_norm = f_vals / f_vals[0]
        ax.plot(
            t_vals, f_norm,
            color=TRUCK_COLORS[tt],
            linewidth=2.5,
            label=f"{TRUCK_LABELS[tt]} (b={p.b:.3f}, c={p.c:.4f})",
        )

    ax.set_xlabel("Travel Time (min)", fontsize=12)
    ax.set_ylabel("Normalized Friction Factor F(t) / F(1)", fontsize=12)
    ax.set_title("Gamma Friction Factor Curves by Truck Type", fontsize=13,
                 fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)
    ax.set_xlim(1, 120)
    ax.set_ylim(0, 1.05)

    fig.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"  Saved: {output_path}")

    return fig


# ── Plot 3: OD scatter (observed vs modeled) ───────────────────────────────────

def plot_od_scatter(
    gravity_results: Dict[str, GravityResult],
    observed_od: Dict[str, np.ndarray],
    output_path: Optional[Path] = None,
    min_trips: float = 1.0,
) -> plt.Figure:
    """
    Log-log scatter plot of observed vs modeled OD flows.

    Each point = one OD pair. Points near the diagonal = good fit.
    Useful for spotting systematic over/under-prediction.

    Parameters
    ----------
    min_trips : only plot OD pairs with observed trips >= min_trips
                (filters out structural zeros)
    """
    n = len(TRUCK_TYPES)
    fig, axes = plt.subplots(1, n, figsize=(6 * n, 5))
    if n == 1:
        axes = [axes]

    for ax, tt in zip(axes, TRUCK_TYPES):
        obs = observed_od[tt].ravel()
        mod = gravity_results[tt].trips.ravel()
        color = TRUCK_COLORS[tt]

        # Filter to nonzero observed pairs
        mask = obs >= min_trips
        obs_f, mod_f = obs[mask], mod[mask]

        if len(obs_f) == 0:
            ax.set_title(f"{TRUCK_LABELS[tt]}\n(no data)")
            continue

        # Compute R² on log scale
        log_obs = np.log10(obs_f + 1)
        log_mod = np.log10(mod_f + 1)
        ss_res = np.sum((log_obs - log_mod) ** 2)
        ss_tot = np.sum((log_obs - log_obs.mean()) ** 2)
        r2 = 1 - ss_res / (ss_tot + 1e-12)

        ax.scatter(obs_f, mod_f, alpha=0.3, s=5, color=color, rasterized=True)

        # 1:1 line
        lim_min = min(obs_f.min(), mod_f.min())
        lim_max = max(obs_f.max(), mod_f.max())
        ax.plot([lim_min, lim_max], [lim_min, lim_max],
                "k--", linewidth=1.5, label="1:1 line")

        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Observed Trips", fontsize=11)
        ax.set_ylabel("Modeled Trips", fontsize=11)
        ax.set_title(f"{TRUCK_LABELS[tt]}\nR² (log) = {r2:.3f}", fontsize=12,
                     fontweight="bold")
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)

    fig.suptitle("Observed vs Modeled OD Flows (log scale)", fontsize=14,
                 fontweight="bold", y=1.02)
    fig.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"  Saved: {output_path}")

    return fig


# ── Plot 4: OD residuals heatmap ───────────────────────────────────────────────

def plot_od_residuals(
    gravity_results: Dict[str, GravityResult],
    observed_od: Dict[str, np.ndarray],
    output_path: Optional[Path] = None,
    min_trips: float = 5.0,
    n_zones_display: int = 100,
) -> plt.Figure:
    """
    Heatmap of relative residuals: (modeled - observed) / observed.

    Red  = model over-predicts
    Blue = model under-predicts

    Large systematic blocks → consider K-factors for those corridor pairs.

    Parameters
    ----------
    min_trips        : mask out OD pairs with observed < min_trips
    n_zones_display  : show only the first N zones (for readability)
    """
    n = len(TRUCK_TYPES)
    fig, axes = plt.subplots(1, n, figsize=(6 * n, 5))
    if n == 1:
        axes = [axes]

    nz = n_zones_display

    for ax, tt in zip(axes, TRUCK_TYPES):
        obs = observed_od[tt][:nz, :nz]
        mod = gravity_results[tt].trips[:nz, :nz]

        residual = np.where(
            obs >= min_trips,
            (mod - obs) / (obs + 1e-9),
            np.nan,
        )

        # Clip at ±2 (200% error) for color scale
        residual_clipped = np.clip(residual, -2, 2)

        im = ax.imshow(
            residual_clipped,
            cmap="RdBu_r",
            vmin=-2, vmax=2,
            aspect="auto",
            interpolation="nearest",
        )
        plt.colorbar(im, ax=ax, label="(mod - obs) / obs", shrink=0.8)
        ax.set_title(f"{TRUCK_LABELS[tt]}\n(first {nz} zones)", fontsize=11,
                     fontweight="bold")
        ax.set_xlabel("Destination Zone", fontsize=10)
        ax.set_ylabel("Origin Zone", fontsize=10)

    fig.suptitle(
        "Relative OD Residuals: (Modeled - Observed) / Observed\n"
        "Red = over-predicted, Blue = under-predicted",
        fontsize=13, fontweight="bold", y=1.02,
    )
    fig.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"  Saved: {output_path}")

    return fig


# ── Plot 5: Calibration loss history ──────────────────────────────────────────

def plot_calibration_loss(
    calibration_results: Dict[str, CalibrationResult],
    output_path: Optional[Path] = None,
) -> plt.Figure:
    """
    Plot the optimization loss history per truck type.
    Useful for diagnosing whether the optimizer converged cleanly.
    """
    fig, ax = plt.subplots(figsize=(8, 4))

    for tt in TRUCK_TYPES:
        r = calibration_results[tt]
        if r.loss_history:
            ax.plot(r.loss_history, color=TRUCK_COLORS[tt],
                    linewidth=1.5, label=TRUCK_LABELS[tt], alpha=0.8)

    ax.set_xlabel("Function Evaluation", fontsize=11)
    ax.set_ylabel("Loss (weighted SSE)", fontsize=11)
    ax.set_title("Calibration Loss History", fontsize=13, fontweight="bold")
    ax.set_yscale("log")
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)
    fig.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"  Saved: {output_path}")

    return fig


# ── Tabular summary ────────────────────────────────────────────────────────────

def print_validation_summary(
    calibration_results: Dict[str, CalibrationResult],
    gravity_results: Dict[str, GravityResult],
    observed_od: Dict[str, np.ndarray],
    skims: Dict[str, np.ndarray],
) -> None:
    """
    Print a concise validation table to stdout.

    Columns: truck type | b | c | obs ATL | mod ATL | ATL error% |
             obs total trips | mod total trips | gravity RMSE
    """
    header = (
        f"{'Truck Type':<16} {'b':>7} {'c':>8} "
        f"{'Obs ATL':>9} {'Mod ATL':>9} {'ATL Err%':>9} "
        f"{'Obs Trips':>12} {'Mod Trips':>12} {'Grav RMSE':>10}"
    )
    print("\n" + "=" * len(header))
    print("VALIDATION SUMMARY")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for tt in TRUCK_TYPES:
        cr = calibration_results[tt]
        gr = gravity_results[tt]
        obs_trips = observed_od[tt].sum()
        mod_trips = gr.trips.sum()
        atl_err = 100 * (cr.modeled_avg_tl - cr.observed_avg_tl) / (cr.observed_avg_tl + 1e-9)

        print(
            f"{tt:<16} {cr.b:>7.4f} {cr.c:>8.5f} "
            f"{cr.observed_avg_tl:>9.1f} {cr.modeled_avg_tl:>9.1f} {atl_err:>+9.1f}% "
            f"{obs_trips:>12.0f} {mod_trips:>12.0f} {gr.final_rmse:>10.2f}"
        )

    print("=" * len(header))
    print("ATL = Average Trip Length (minutes)")
    print("ATL Err% = (modeled - observed) / observed * 100")
    print()
