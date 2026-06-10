"""
run.py
------
Top-level entry point for the truck trip distribution model.

See config.py for configurable parameters.
Outputs written to output_dir/
    calibrated_params.csv     gamma b, c per truck type
    modeled_od_{tt}.npy       modeled trip matrix per truck type
    tlfd_comparison.png
    friction_curves.png
    od_scatter.png
    od_residuals.png
    calibration_loss.png



trip_distribution
=================
Gravity model calibration and application for truck trip distribution.

Truck types: light_trucks, medium_trucks, heavy_trucks
Time periods: AM (6-10am), MD (10am-3pm)
Impedance: blended travel time (1/3 AM + 2/3 MD), optionally toll-adjusted

Typical workflow
----------------
1. Load inputs (PA table, skims, observed OD, observed TLFD)
2. Calibrate gamma parameters (b, c) per truck type against observed TLFD
3. Apply gravity model with calibrated parameters
4. Validate: compare modeled vs observed TLFD, inspect residuals
5. Decide whether K-factors are needed

Entry point: run.py
    
"""

from pathlib import Path
import numpy as np
import pandas as pd

from .io import (
    load_pa,
    load_blended_skims,
    load_od_matrix,
    load_observed_tlfd,
    pa_from_od,
)
from .calibration import calibrate_all, params_from_calibration
from .gravity import run_all_gravity
from .validation import (
    plot_tlfd_comparison,
    plot_friction_curves,
    plot_od_scatter,
    plot_od_residuals,
    plot_calibration_loss,
    print_validation_summary,
)
from .config import (
    PA_PATH,
    AM_SKIM_PATH,
    MD_SKIM_PATH,
    OD_PATH,
    TLFD_PATH,
    OUTPUT_DIR,
    USE_OD_FOR_PA,
)
from .config import OUTPUT_DIR as output_directory
from .config import USE_OD_FOR_PA


def run() -> None:
    """
    Full pipeline: load → calibrate → apply → validate → save.
    
    Reads all configuration from config.py.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. Loading inputs ──────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 1: Loading inputs")
    print("=" * 60)

    print("\nLoading skims...")
    skims = load_blended_skims(AM_SKIM_PATH, MD_SKIM_PATH)

    print("\nLoading observed OD matrix...")
    observed_od = load_od_matrix(OD_PATH)

    print("\nLoading observed TLFD...")
    observed_tlfds = load_observed_tlfd(TLFD_PATH)

    if USE_OD_FOR_PA:
        print("\nDeriving P/A from OD matrix (temporary mode)...")
        pa_data = pa_from_od(observed_od)
    else:
        print(f"\nLoading P/A from {PA_PATH}...")
        pa_data = load_pa(PA_PATH)

    # ── 2. Calibrate gamma parameters ─────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 2: Calibrating gamma parameters")
    print("=" * 60)

    calibration_results = calibrate_all(
        pa_data=pa_data,
        skims=skims,
        observed_tlfds=observed_tlfds,
        verbose=True,
    )

    # Save calibrated parameters
    params = params_from_calibration(calibration_results)
    params_df = pd.DataFrame(
        [{"truck_type": tt, "b": p.b, "c": p.c} for tt, p in params.items()]
    )
    params_path = OUTPUT_DIR / "calibrated_params.csv"
    params_df.to_csv(params_path, index=False)
    print(f"\n  Saved calibrated parameters: {params_path}")

    # ── 3. Applying gravity model ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 3: Applying gravity model")
    print("=" * 60)

    gravity_results = run_all_gravity(
        pa_data=pa_data,
        skims=skims,
        gamma_params=params,
    )

    # Save modeled OD matrices
    for tt, gr in gravity_results.items():
        T_out = gr.trips * OUTPUT_SCALE_FACTOR
        out_path = OUTPUT_DIR / f"modeled_od_{tt}.npy"
        np.save(out_path, T_out)
        print(f"  Saved modeled OD [{tt}]: {out_path}")

    # ── 4. Validation ────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 4: Validation")
    print("=" * 60)

    print_validation_summary(
        calibration_results=calibration_results,
        gravity_results=gravity_results,
        observed_od=observed_od,
        skims=skims,
    )

    print("\nGenerating plots...")

    plot_tlfd_comparison(
        calibration_results,
        output_path=OUTPUT_DIR / "tlfd_comparison.png",
    )
    plot_friction_curves(
        params,
        output_path=OUTPUT_DIR / "friction_curves.png",
    )
    plot_od_scatter(
        gravity_results,
        observed_od,
        output_path=OUTPUT_DIR / "od_scatter.png",
    )
    plot_od_residuals(
        gravity_results,
        observed_od,
        output_path=OUTPUT_DIR / "od_residuals.png",
    )
    plot_calibration_loss(
        calibration_results,
        output_path=OUTPUT_DIR / "calibration_loss.png",
    )

    print(f"\nAll outputs written to: {OUTPUT_DIR}")

def _parse_args():
    return None

if __name__ == "__main__":
    run()
