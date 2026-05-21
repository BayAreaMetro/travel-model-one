import logging
import math

import numpy as np
import pandas as pd
import openmatrix as omx
import pandas as pd
from pathlib import Path
import scipy.sparse as sp

from src.utils import setup_logging, load_config

logger = logging.getLogger(__name__)

_SEP = "─" * 108

def mask_1d(
    indices: np.array,
    lenght: int,
) -> np.ndarray:
    """
    Build a boolean mask of given lenght. True Values are in index.
    """
    mask_1d = np.zeros(lenght, dtype=bool)
    mask_1d[indices] = True
    return mask_1d



def log_matrix_projection(
    name: str,
    M_from: np.ndarray,
    M_masked: np.ndarray,
    M_to: np.ndarray,
) -> dict[str, float]:
    """
    Compute and log projection metrics for one matrix.

    Parameters
    ----------
    name     : matrix name (for logging)
    M_from   : original statewide matrix
    M_masked : masked matrix (only trips touching TO region kept)
    M_to     : projected matrix
    """
    statewide   = float(M_from.sum())
    to_relevant = float(M_masked.sum())
    projected   = float(M_to.sum())
    approx_loss = to_relevant - projected

    coverage_pct = 100.0 * to_relevant / statewide   if statewide   > 0 else 0.0
    loss_pct     = 100.0 * approx_loss / to_relevant if to_relevant > 0 else 0.0

    logger.info(
        "  %-22s  statewide: %12.0f  |  TO-relevant: %10.0f (%5.1f%%)  |"
        "  projected: %10.0f  |  approx-loss: %9.0f (%5.2f%%)",
        name,
        statewide,
        to_relevant, coverage_pct,
        projected,
        approx_loss, loss_pct,
    )

    return {
        "statewide": statewide,
        "to_relevant": to_relevant,
        "projected": projected,
        "approx_loss": approx_loss,
    }


def log_aggregate_projection(all_metrics: list[dict[str, float]]) -> None:
    """Aggregate and log metrics across all matrices."""
    if not all_metrics:
        return

    agg = {k: sum(m[k] for m in all_metrics) for k in all_metrics[0]}

    coverage_pct = 100.0 * agg["to_relevant"] / agg["statewide"] if agg["statewide"] > 0 else 0.0
    loss_pct     = 100.0 * agg["approx_loss"] / agg["to_relevant"] if agg["to_relevant"] > 0 else 0.0

    logger.info("-" * 110)
    logger.info(
        "  %-22s  statewide: %12.0f  |  TO-relevant: %10.0f (%5.1f%%)  |"
        "  projected: %10.0f  |  approx-loss: %9.0f (%5.2f%%)",
        f"TOTAL ({len(all_metrics)} matrices)",
        agg["statewide"],
        agg["to_relevant"], coverage_pct,
        agg["projected"],
        agg["approx_loss"], loss_pct,
    )
    logger.info("-" * 110)


def project_omx(matrixes_names, source_matrices, target_matrices, W_row_gates, W_col_gates, mask):
    """
    """
    all_metrics =[]
    # Create an on-the-fly 2D broadcasting filter (True if row OR col is internal)
    # This prevents creating a massive 2D matrix in memory
    keep_filter = mask[:, None] | mask[None, :]

    for matrix_name in matrixes_names:
        original_matrix = np.array(source_matrices[matrix_name][:], dtype=np.float32) 
        masked_matrix = original_matrix * keep_filter
        projected_matrix = W_row_gates.T @ masked_matrix @ W_col_gates
        target_matrices[matrix_name] = np.array(projected_matrix, dtype=np.float32)
        log = log_matrix_projection(matrix_name, original_matrix, masked_matrix, projected_matrix)
        all_metrics.append(log)
    log_aggregate_projection(all_metrics)
    return target_matrices
    

def internal_gates_generation(matrixes_names, source_matrices, crosswalk: pd.DataFrame) -> pd.DataFrame:
    """
    """
    trip_generation = pd.DataFrame(index = range(1, 7001))
    internal_gates = crosswalk[crosswalk.type == "internal_gate"].drop_duplicates()

    for matrix_name in matrixes_names:
        matrix = np.array(source_matrices[matrix_name][:], dtype=np.float32) 
        trip_generation[f"{matrix_name}_production"] = matrix.sum(axis = 1)
        trip_generation[f"{matrix_name}_attraction"] = matrix.sum(axis = 0)

    df = internal_gates.merge(df, how = "left", left_on="from_zone_id", right_index=True)
    return df


def project_matrices(
        source_matrices,
        target_matrices, 
        crosswalk: pd.DataFrame, 
        row_weight_col: str,
        col_weight_col: str,
        offset, 
        n_from, 
        n_to,
        matrixes_names: None,
        zone_types: list[str], 
        ) -> omx.File:
    """Inline projection step — reuses logic from project_matrix without re-reading crosswalk.

    Weight matrices are built as jax.experimental.sparse.BCOO objects; the JIT-compiled
    projection function handles batching via reshape rather than vmap (JAX sparse does
    not support vmap).

    Per-matrix and aggregate metrics are logged:
      - statewide trips (total FROM matrix)
      - TO-region-relevant trips (origin OR destination touches internal TO zone)
      - projected trips (total output TO matrix)
      - approximation loss (relevant − projected)
    """
    if matrixes_names is None:
        matrixes_names   = source_matrices.list_matrices()

    # Masks 
    ids = crosswalk[crosswalk["type"].isin(zone_types)]["from_zone_id"].unique() - offset
    mask = mask_1d(ids, n_from)

    # Crosswalk Weight matrices 
    row_id = crosswalk["from_zone_id"].values - offset
    col_id = crosswalk["to_zone_id"].values - offset
    row_weights = crosswalk[row_weight_col].values
    col_weights = crosswalk[col_weight_col].values
    W_row = sp.coo_matrix((row_weights, (row_id, col_id)), shape=(n_from, n_to))
    W_col = sp.coo_matrix((col_weights, (row_id, col_id)), shape=(n_from, n_to))
    
    # internal_gates_generation_df = internal_gates_generation(matrixes_names, source_matrices, crosswalk)

    return project_omx(
        matrixes_names,
        source_matrices, 
        target_matrices, 
        W_row, 
        W_col, 
        mask,
        )

