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


def collapse_projected_sw_omx_to_type_tod(omx_file: omx.File) -> dict[tuple[str, str], np.ndarray]:
    """
    Collapse a projected statewide OMX by summing over FR/NF and CA/EXT
    variants, returning matrices aggregated by truck class and TOD.
    
    The input OMX is assumed to be a "projected" output produced by: 
    src.data.od_projection.projection.project_matrices

    Returns
    -------
    dict mapping (statewide_truck_type, statewide_tod) → float32 numpy array
    """
    aggregated: dict[tuple[str, str], np.ndarray] = {}


    for name in omx_file.list_matrices():
        try:
            truck_type, tod = _parse_matrix_name(name)
        except ValueError as exc:
            logger.warning("Skipping unrecognised matrix name: %s", exc)
            continue

        data = np.array(omx_file[name], dtype=np.float32)
        key  = (truck_type, tod)
        aggregated[key] = data if key not in aggregated else aggregated[key] + data

    logger.info(
        "Projected OMX: %d matrices aggregated into %d (type, TOD) groups: %s",
        sum(1 for _ in aggregated),   # same as len, kept explicit
        len(aggregated),
        sorted(f"{p}/{t}" for p, t in aggregated),
    )
    return aggregated


def compute_tod_split_proportions(mtc_format_configs: dict) -> dict[str, dict[str, np.ndarray]]:
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
    in_pattern = mtc_format_configs["input_omx_pattern"]
    result: dict[str, dict[str, np.ndarray]] = {}

    for sw_tod, mapping in mtc_format_configs["tod_mapping"].items():
        mtc_tods = mapping["mtc_tods"]
        if len(mtc_tods) <= 1:
            continue  # direct mapping, no split needed

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
            reference_omx = omx.open_file(ref_path, "r")
            available = set(reference_omx.list_matrices())
            for rtype in ref_types:
                if rtype not in available:
                    logger.warning(
                        "Reference '%s' has no matrix '%s'; skipped.",
                        ref_path, rtype,
                    )
                    continue
                data = np.array(reference_omx[rtype], dtype=np.float64)
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


def build_mtc_matrix(
    mtc_tod: str,
    mtc_truck: str,
    truck_cfg: dict,
    aggregated: dict[tuple[str, str], np.ndarray],
    proportions: dict[str, dict[str, np.ndarray]],
    tod_mapping: dict,
    fallback: np.ndarray | None,
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
    fallback          : Default matrix from MTC reference file, or None
    """
    from_types = truck_cfg.get("from_types")

    # ── No statewide equivalent: preserve the MTC reference matrix ────────────
    if from_types is None:
        if fallback is not None:
            return fallback.copy(), "MTC reference (preserved)"
        return None, "from_types=null and no reference matrix available"

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

    # # ── No statewide data at all: warn and fall back to reference ──────────────
    # if fallback is not None:
    #     logger.warning(
    #         "  %s / %-8s  no projected data for types %s — "
    #         "falling back to MTC reference.",
    #         mtc_tod, mtc_truck, from_types,
    #     )
    #     return fallback.copy(), "MTC reference (fallback — no statewide data)"

    # return None, f"no statewide data for {from_types} feeding {mtc_tod}, and no reference"


def patch_cube_omx_with_new_matrices(aggregated, proportions, configs):
    tods = configs["mtc_tods"]
    tod_mapping = configs["tod_mapping"]
    truck_mapping = configs["truck_type_mapping"]
    in_pattern  = configs["input_omx_pattern"]
    out_pattern = configs["output_omx_pattern"]
    
    tod_totals: dict[str, float] = {}

    logger.info(_SEP)
    logger.info(
        "  %-5s  %-10s  %14s   %s",
        "TOD", "Truck type", "Trips", "Source",
    )
    logger.info(_SEP)

    for mtc_tod in tods:
        out_path = out_pattern.format(tod=mtc_tod)
        ref_path = in_pattern.format(tod=mtc_tod)

        # For fallback use if SW doesn't provide data for a truck type (e.g. very small trucks)
        ref_matrices: dict[str, np.ndarray] = {}
        reference_omx = omx.open_file(ref_path, "r")
        for mat_name in reference_omx.list_matrices():
            ref_matrices[mat_name] = np.array(reference_omx[mat_name], dtype=np.float32)
       

        tod_trip_total = 0.0
        
        out_omx = omx.open_file(out_path, "a")
    
        for mtc_truck, truck_cfg in truck_mapping.items():
            matrix, source = build_mtc_matrix(
                mtc_tod, mtc_truck, truck_cfg,
                aggregated, proportions, tod_mapping,
                ref_matrices.get(mtc_truck),
            )

            matrix_node = out_omx[mtc_truck]
            replacement_data = np.asarray(matrix, dtype=matrix_node.atom.dtype)
            matrix_node[:] = replacement_data

            trips = float(matrix.sum())
            tod_trip_total += trips
            logger.info(
                "  %-5s  %-10s  %14.0f   %s",
                mtc_tod, mtc_truck, trips, source,
            )
        out_omx.flush()
        tod_totals[mtc_tod] = tod_trip_total
        out_omx.close()
        reference_omx.close()

    # ── Summary ────────────────────────────────────────────────────────────────
    grand_total = sum(tod_totals.values())
    logger.info(_SEP)
    logger.info("  %-5s  %-10s  %14s", "TOD", "", "Total trips")
    logger.info(_SEP)
    for tod in tods:
        pct = 100.0 * tod_totals[tod] / grand_total if grand_total > 0 else 0.0
        logger.info("  %-5s  %-10s  %14.0f   (%5.1f%%)", tod, "", tod_totals[tod], pct)
    logger.info("  %-5s  %-10s  %14.0f", "TOTAL", "", grand_total)
    logger.info(_SEP)
    logger.info(
        "Output written to: %s",
        str(Path(out_pattern.format(tod="*")).parent / Path(out_pattern.format(tod="*")).name),
    )

    return None


def format_mtc_output(sw_projection, mtc_format_configs) -> None:
    """
    Build the five MTC TOD OMX files from the projected statewide output.

    For each MTC TOD and each MTC truck type:
      • If from_types is null  → copy the matrix from the MTC reference file unchanged.
      • Otherwise              → sum the relevant projected statewide matrices,
                                 apply any configured TOD split proportions. 
    
    """
    # ── Step 1: Aggregate projected matrices ──────────────────────────
    aggregated = collapse_projected_sw_omx_to_type_tod(sw_projection)

    # ── Step 2: compute TOD split proportions ─────────────────────────────────
    logger.info("Computing TOD split proportions from MTC reference files …")
    proportions = compute_tod_split_proportions(mtc_format_configs)

    # ── Step 3: write one OMX per MTC TOD ─────────────────────────────────────
    patch_cube_omx_with_new_matrices(aggregated, proportions, mtc_format_configs)
    