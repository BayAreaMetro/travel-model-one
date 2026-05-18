"""
Format projected statewide matrices into MTC-compatible trip-table OMX files.

The MTC travel model reads one OMX file per time-of-day period:
    tripstrk{TOD}x.omx   where TOD ∈ {EA, AM, MD, PM, EV}

Each file contains four matrices representing truck types:
    vstruck   struck   mtruck   ctruck

This step bridges the projection output to the MTC format through two mappings
defined in config.yaml under ``mtc_format``:

TOD mapping (statewide → MTC)
──────────────────────────────
  AM   → AM    (direct)
  MID  → MD    (rename only)
  PM   → PM    (direct)
  OFF  → EA + EV  (split using OD-level proportions from MTC reference files)

  For every statewide TOD that fans out to more than one MTC TOD, element-wise
  proportions are derived from the MTC reference files by summing the truck-type
  matrices listed under ``split_reference_types`` for each target period:

      prop_EA[i,j] = ref_EA_sum[i,j] / (ref_EA_sum[i,j] + ref_EV_sum[i,j])

  Where the denominator is zero the fallback is an equal split across all
  target periods.

Truck-type mapping (statewide prefixes → MTC truck types)
───────────────────────────────────────────────────────────
  vstruck : no statewide equivalent → original MTC matrix preserved unchanged
  struck  : sum of all LT_*  projected matrices for the matching TOD
  mtruck  : sum of all M1T_* + M2T_* projected matrices for the matching TOD
  ctruck  : sum of all HT_*  projected matrices for the matching TOD

Matrix aggregation
──────────────────
Projected matrix names follow the pattern <TYPE>_<fr/nf>_<ca/ext>_<TOD>.
The first token (TYPE) and last token (TOD) are parsed; matrices sharing the
same (TYPE, TOD) are summed before the truck-type mapping is applied, collapsing
the FR/NF and CA/EXT dimensions.

Run from project root:
    python -m src.data.format_mtc_output
"""

import logging
from pathlib import Path

import numpy as np
import openmatrix as omx
from tables import Filters

from src.utils import setup_logging, load_config

logger = logging.getLogger(__name__)

_SEP = "─" * 72


# ── Name parsing ───────────────────────────────────────────────────────────────

def _parse_matrix_name(name: str) -> tuple[str, str]:
    """
    Split a statewide projected matrix name into (truck_type_prefix, tod).

    Convention: <TYPE>_..._<TOD>  — first token is the type, last is the TOD.

    Examples
    --------
    'HT_FR_CA_AM'   → ('HT',  'AM')
    'M1T_FR_EXT_AM' → ('M1T', 'AM')
    'LT_NF_CA_MID'  → ('LT',  'MID')
    'LT_FR_CA_OFF'  → ('LT',  'OFF')
    """
    parts = name.split("_")
    if len(parts) < 2:
        raise ValueError(
            f"Cannot parse matrix name '{name}': "
            "expected '<TYPE>_..._<TOD>' with at least two '_'-separated tokens."
        )
    return parts[0], parts[-1]


# ── Step 1: aggregate projected matrices ──────────────────────────────────────

def load_and_aggregate_projected(cfg: dict) -> dict[tuple[str, str], np.ndarray]:
    """
    Read all matrices from the projected output OMX and aggregate (sum) by
    (truck_type_prefix, statewide_tod), collapsing FR/NF and CA/EXT variants.

    Returns
    -------
    dict mapping (prefix, statewide_tod) → float32 numpy array
    """
    aggregated: dict[tuple[str, str], np.ndarray] = {}

    with omx.open_file(cfg["paths"]["output_omx"], "r") as f:
        for name in f.list_matrices():
            try:
                prefix, tod = _parse_matrix_name(name)
            except ValueError as exc:
                logger.warning("Skipping unrecognised matrix name: %s", exc)
                continue

            data = np.array(f[name], dtype=np.float32)
            key  = (prefix, tod)
            aggregated[key] = data if key not in aggregated else aggregated[key] + data

    logger.info(
        "Projected OMX: %d matrices aggregated into %d (type, TOD) groups: %s",
        sum(1 for _ in aggregated),   # same as len, kept explicit
        len(aggregated),
        sorted(f"{p}/{t}" for p, t in aggregated),
    )
    return aggregated


# ── Step 2: compute TOD split proportions ─────────────────────────────────────

def compute_tod_split_proportions(cfg: dict) -> dict[str, dict[str, np.ndarray]]:
    """
    For every statewide TOD that maps to more than one MTC TOD, compute
    element-wise split proportions from the MTC reference OMX files.

    Returns
    -------
    dict mapping statewide_tod → {mtc_tod → proportion array (float32)}

    Proportions sum to 1.0 across all MTC target periods for each O-D cell.
    Cells where all reference periods are zero receive an equal-split fallback.
    Only statewide TODs with more than one MTC target appear in the result.
    """
    fmt        = cfg["mtc_format"]
    in_pattern = fmt["input_omx_pattern"]
    result: dict[str, dict[str, np.ndarray]] = {}

    for sw_tod, mapping in fmt["tod_mapping"].items():
        mtc_tods = mapping["mtc_tods"]
        if len(mtc_tods) <= 1:
            continue  # direct mapping — no split needed

        ref_types = mapping.get("split_reference_types", [])
        n_tods    = len(mtc_tods)

        if not ref_types:
            logger.warning(
                "TOD '%s' maps to %s but 'split_reference_types' is empty; "
                "applying equal split (1 / %d) as fallback.",
                sw_tod, mtc_tods, n_tods,
            )
            result[sw_tod] = {}   # empty dict → caller uses equal split
            continue

        # ── Sum reference matrices across the listed truck types for each period ──
        ref_totals: dict[str, np.ndarray | None] = {t: None for t in mtc_tods}
        for mtc_tod in mtc_tods:
            ref_path = in_pattern.format(tod=mtc_tod)
            with omx.open_file(ref_path, "r") as f:
                available = set(f.list_matrices())
                for rtype in ref_types:
                    if rtype not in available:
                        logger.warning(
                            "Reference '%s' has no matrix '%s'; skipped.",
                            ref_path, rtype,
                        )
                        continue
                    data = np.array(f[rtype], dtype=np.float64)
                    ref_totals[mtc_tod] = (
                        data if ref_totals[mtc_tod] is None else ref_totals[mtc_tod] + data
                    )
            if ref_totals[mtc_tod] is None:
                logger.warning(
                    "No reference data found for '%s' in '%s'; using zeros.",
                    mtc_tod, ref_path,
                )
                ref_totals[mtc_tod] = np.zeros((1, 1))

        # ── Compute proportions; equal-split fallback where denominator is zero ──
        denom = sum(v for v in ref_totals.values())   # element-wise
        # Pre-substitute 1.0 where denom == 0 so the division is always safe.
        # np.where evaluates BOTH branches unconditionally, so a plain division
        # by denom would trigger RuntimeWarning on zero-denominator cells even
        # though those cells are ultimately overwritten by the fallback value.
        safe_denom = np.where(denom > 0, denom, 1.0)
        props: dict[str, np.ndarray] = {}
        for mtc_tod in mtc_tods:
            p = np.where(denom > 0, ref_totals[mtc_tod] / safe_denom, 1.0 / n_tods)
            props[mtc_tod] = p.astype(np.float32)

        result[sw_tod] = props
        mean_props = {t: f"{float(props[t].mean()) * 100:.1f}%" for t in mtc_tods}
        logger.info(
            "TOD split '%s' → %s: mean proportions %s  (ref types: %s)",
            sw_tod, mtc_tods, mean_props, ref_types,
        )

    return result


# ── Step 3: assemble one (MTC TOD, MTC truck type) matrix ─────────────────────

def build_mtc_matrix(
    mtc_tod: str,
    mtc_truck: str,
    truck_cfg: dict,
    aggregated: dict[tuple[str, str], np.ndarray],
    proportions: dict[str, dict[str, np.ndarray]],
    tod_mapping: dict,
    reference_fallback: np.ndarray | None,
) -> tuple[np.ndarray | None, str]:
    """
    Assemble one MTC matrix from projected statewide data.

    Returns
    -------
    (matrix, source_description)
        matrix             : float32 array, or None if nothing is available
        source_description : human-readable string for logging

    Parameters
    ----------
    mtc_tod           : target MTC TOD, e.g. 'EA'
    mtc_truck         : target MTC truck type, e.g. 'ctruck'
    truck_cfg         : mtc_format.truck_type_mapping entry for this truck type
    aggregated        : output of load_and_aggregate_projected()
    proportions       : output of compute_tod_split_proportions()
    tod_mapping       : cfg["mtc_format"]["tod_mapping"]
    reference_fallback: matrix from MTC reference file, or None
    """
    from_types = truck_cfg.get("from_types")

    # ── No statewide equivalent: preserve the MTC reference matrix ────────────
    if from_types is None:
        if reference_fallback is not None:
            return reference_fallback.copy(), "MTC reference (preserved)"
        return None, "from_types=null but no reference matrix available"

    # ── Accumulate statewide contributions ────────────────────────────────────
    result: np.ndarray | None = None
    source_parts: list[str] = []

    for sw_tod, mapping in tod_mapping.items():
        if mtc_tod not in mapping["mtc_tods"]:
            continue  # this statewide TOD does not feed the current MTC TOD

        # Sum across all configured statewide prefixes for this TOD
        sw_total: np.ndarray | None = None
        found_keys: list[str] = []
        for prefix in from_types:
            key = (prefix, sw_tod)
            if key in aggregated:
                mat = aggregated[key]
                sw_total = mat.copy() if sw_total is None else sw_total + mat
                found_keys.append(f"{prefix}×{sw_tod}")

        if sw_total is None:
            continue  # no projected data for this (prefix, sw_tod) pair

        # Apply split proportion if this sw_tod fans out to multiple MTC TODs
        n_targets = len(mapping["mtc_tods"])
        if sw_tod in proportions:
            period_props = proportions[sw_tod]
            if period_props:
                # Proportions computed from reference data
                prop = period_props.get(mtc_tod)
                if prop is not None:
                    if prop.shape != sw_total.shape:
                        # Shape mismatch (e.g. reference used a different zone size);
                        # fall back to scalar mean proportion
                        prop_scalar = float(prop.mean())
                        logger.warning(
                            "  %s/%s: proportion shape %s ≠ data shape %s; "
                            "using scalar mean %.3f",
                            mtc_tod, mtc_truck, prop.shape, sw_total.shape, prop_scalar,
                        )
                        sw_total = sw_total * prop_scalar
                        source_parts.append(
                            f"{'+'.join(found_keys)}×{mtc_tod}_prop(mean={prop_scalar:.3f})"
                        )
                    else:
                        sw_total = sw_total * prop
                        source_parts.append(f"{'+'.join(found_keys)}×{mtc_tod}_prop")
                else:
                    # Equal-split fallback (this mtc_tod key missing from props)
                    sw_total = sw_total / n_targets
                    source_parts.append(f"{'+'.join(found_keys)}÷{n_targets}")
            else:
                # Empty proportions dict → split_reference_types was empty
                sw_total = sw_total / n_targets
                source_parts.append(f"{'+'.join(found_keys)}÷{n_targets}(equal)")
        else:
            source_parts.extend(found_keys)

        result = sw_total if result is None else result + sw_total

    if result is not None:
        return result.astype(np.float32), ", ".join(source_parts)

    # ── No statewide data at all: warn and fall back to reference ──────────────
    if reference_fallback is not None:
        logger.warning(
            "  %s / %-8s  no projected data for types %s — "
            "falling back to MTC reference.",
            mtc_tod, mtc_truck, from_types,
        )
        return reference_fallback.copy(), "MTC reference (fallback — no statewide data)"

    return None, f"no statewide data for {from_types} feeding {mtc_tod}, and no reference"


# ── Main entry point ───────────────────────────────────────────────────────────

def format_mtc_output(cfg: dict) -> None:
    """
    Build the five MTC TOD OMX files from the projected statewide output.

    For each MTC TOD and each MTC truck type:
      • If from_types is null  → copy the matrix from the MTC reference file unchanged.
      • Otherwise              → sum the relevant projected statewide matrices,
                                 apply any configured TOD split proportions, and
                                 write the result.

    Output files follow the pattern configured in mtc_format.output_omx_pattern.
    """
    fmt         = cfg["mtc_format"]
    in_pattern  = fmt["input_omx_pattern"]
    out_pattern = fmt["output_omx_pattern"]
    tod_mapping = fmt["tod_mapping"]

    # Ensure output directory exists
    Path(out_pattern.format(tod=fmt["mtc_tods"][0])).parent.mkdir(parents=True, exist_ok=True)

    # ── Step 1: load and aggregate projected matrices ──────────────────────────
    logger.info("Loading projected matrices from %s …", cfg["paths"]["output_omx"])
    aggregated = load_and_aggregate_projected(cfg)

    # ── Step 2: compute TOD split proportions ─────────────────────────────────
    logger.info("Computing TOD split proportions from MTC reference files …")
    proportions = compute_tod_split_proportions(cfg)

    # ── Step 3: write one OMX per MTC TOD ─────────────────────────────────────
    truck_mapping              = fmt["truck_type_mapping"]
    tod_totals: dict[str, float] = {}

    logger.info(_SEP)
    logger.info(
        "  %-5s  %-10s  %14s   %s",
        "TOD", "Truck type", "Trips", "Source",
    )
    logger.info(_SEP)

    for mtc_tod in fmt["mtc_tods"]:
        out_path = out_pattern.format(tod=mtc_tod)
        ref_path = in_pattern.format(tod=mtc_tod)

        # Pre-load this TOD's reference matrices (for preserved / fallback use)
        ref_matrices: dict[str, np.ndarray] = {}
        try:
            with omx.open_file(ref_path, "r") as f:
                for mat_name in f.list_matrices():
                    ref_matrices[mat_name] = np.array(f[mat_name], dtype=np.float32)
        except Exception as exc:
            logger.warning("Could not read MTC reference '%s': %s", ref_path, exc)

        tod_trip_total = 0.0
        with omx.open_file(out_path, "a") as out_f:
            for mtc_truck, truck_cfg in truck_mapping.items():
                matrix, source = build_mtc_matrix(
                    mtc_tod, mtc_truck, truck_cfg,
                    aggregated, proportions, tod_mapping,
                    ref_matrices.get(mtc_truck),
                )
                if matrix is None:
                    logger.error(
                        "  %-5s  %-10s  OMITTED: %s", mtc_tod, mtc_truck, source
                    )
                    continue

                matrix_node = out_f[mtc_truck]
                replacement_data = np.asarray(matrix, dtype=matrix_node.atom.dtype)
                matrix_node[:] = replacement_data

                trips = float(matrix.sum())
                tod_trip_total += trips
                logger.info(
                    "  %-5s  %-10s  %14.0f   %s",
                    mtc_tod, mtc_truck, trips, source,
                )
            out_f.flush()

        tod_totals[mtc_tod] = tod_trip_total

    # ── Summary ────────────────────────────────────────────────────────────────
    grand_total = sum(tod_totals.values())
    logger.info(_SEP)
    logger.info("  %-5s  %-10s  %14s", "TOD", "", "Total trips")
    logger.info(_SEP)
    for tod in fmt["mtc_tods"]:
        pct = 100.0 * tod_totals[tod] / grand_total if grand_total > 0 else 0.0
        logger.info("  %-5s  %-10s  %14.0f   (%5.1f%%)", tod, "", tod_totals[tod], pct)
    logger.info("  %-5s  %-10s  %14.0f", "TOTAL", "", grand_total)
    logger.info(_SEP)
    logger.info(
        "Output written to: %s",
        str(Path(out_pattern.format(tod="*")).parent / Path(out_pattern.format(tod="*")).name),
    )


# ── Entry point ────────────────────────────────────────────────────────────────

def main(config_path: str = "config/config.yaml") -> None:
    setup_logging()
    cfg = load_config(config_path)
    format_mtc_output(cfg)


if __name__ == "__main__":
    main()
