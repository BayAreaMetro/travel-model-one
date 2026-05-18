"""
Project CSF truck-trip matrices to the MTC zoning system using JAX sparse matrices.

Algorithm
─────────
    M_to = W_row.T  @  M_from  @  W_col

where W_row and W_col are sparse (n_from × n_to) BCOO weight matrices derived from
the crosswalk.  The projection is JIT-compiled and applied to a batch of matrices
using a reshape-based approach (JAX sparse does not support vmap):

    Step 1 — left multiply by W_row.T  (sparse × dense):
        M_flat   = M_batch  transposed and reshaped to (n_from, B × n_from)
        step1    = W_row_T  @  M_flat                 → (n_to,  B × n_from)  dense
        reshape back to                               → (B, n_to, n_from)

    Step 2 — right multiply by W_col  (dense × sparse):
        step2    = step1     reshaped to (B × n_to, n_from)
                   @  W_col                           → (B × n_to, n_to)    dense
        reshape back to                               → (B, n_to, n_to)

Both weight matrices are stored as jax.experimental.sparse.BCOO objects, so only
the non-zero entries are held in memory.  Each matmul uses JAX's built-in sparse
× dense kernel (jax.experimental.sparse.BCOO @ dense).

External-to-external zeroing
────────────────────────────
After projection the block M_to[n_internal:, n_internal:] is zeroed because
trips with both origin and destination outside the TO region are not modelled.

Projection metrics (per matrix + aggregate)
───────────────────────────────────────────
For each projected matrix the following are reported:

  statewide      – total trips in the FROM (statewide) matrix
  TO-relevant    – statewide trips whose origin OR destination FROM zone has any
                   crosswalk weight pointing into the internal TO zone system
                   (i.e. at least one trip end touches the TO region)
  coverage       – TO-relevant / statewide  ← "what share of statewide trips
                   involve the TO region at all?"
  projected      – total trips in the output TO matrix
  approx-loss    – TO-relevant − projected  ← trips that should have been captured
                   but were not, due to crosswalk weight approximation (boundary
                   zones routing a fraction to gateways; gateway×gateway zeroing)
  approx-loss %  – approx-loss / TO-relevant

An aggregate row summing all matrices is printed at the end.

Run from project root:
    python -m src.data.project_matrix
"""

import logging
import math

import numpy as np
import openmatrix as omx
import pandas as pd
from pathlib import Path
import scipy.sparse as sp

from src.utils import setup_logging, load_config

logger = logging.getLogger(__name__)

_SEP = "─" * 108


# ── Build sparse JAX weight matrices ──────────────────────────────────────────

import jax.experimental.sparse as jsparse
import jax.numpy as jnp
import pandas as pd
from typing import Tuple

def build_weight_matrices(
    df: pd.DataFrame, 
    row_col: str, 
    col_col: str, 
    val_col: str, 
    shape: Tuple[int, int], 
    offset: int = 1, 
) -> jsparse.BCOO:
    """
    Converts a pandas DataFrame into a JAX sparse BCOO matrix.
    
    Parameters:
        df: The source pandas DataFrame.
        row_col: Column name representing row indices.
        col_col: Column name representing column indices.
        val_col: Column name representing matrix values.
        shape: A tuple containing the target matrix dimensions (rows, columns).
    """
    row_index = df[row_col].values - offset
    col_index = df[col_col].values - offset
    indices = jnp.column_stack((row_index, col_index))
    data = jnp.array(df[val_col].values)
    return jsparse.BCOO((data, indices), shape=shape)




# ── JAX sparse batched projection ─────────────────────────────────────────────

def make_project_fn(W_row: jsparse.BCOO, W_col: jsparse.BCOO) -> callable:
    """
    Return a JIT-compiled function that projects a batch of matrices using sparse
    weight matrices.

        project_batch(M_batch) → M_to_batch
        M_batch   : (B, n_from, n_from)  float32
        M_to_batch: (B, n_to,   n_to  )  float32

    Algorithm: M_to = W_row.T @ M_from @ W_col

    Because jax.experimental.sparse does not support vmap, batching is handled
    via reshape:

        Step 1  W_row_T @ M_flat  where M_flat = (n_from, B × n_from)
        Step 2  step1_flat @ W_col  where step1_flat = (B × n_to, n_from)
    """
    W_row_T = W_row.T   # BCOO (n_to, n_from)

    n_to, n_from = W_row_T.shape

    @jax.jit
    def project_batch(M_batch: jax.Array) -> jax.Array:
        B = M_batch.shape[0]

        # ── Step 1: W_row_T (sparse) @ M_batch (dense) ────────────────────────
        # Reshape M_batch: (B, n_from, n_from) → (n_from, B × n_from)
        M_flat     = M_batch.transpose(1, 0, 2).reshape(n_from, B * n_from)
        # Sparse × dense matmul: (n_to, n_from) @ (n_from, B*n_from) → (n_to, B*n_from)
        step1_flat = W_row_T @ M_flat
        # Reshape back: (n_to, B*n_from) → (B, n_to, n_from)
        step1      = step1_flat.reshape(n_to, B, n_from).transpose(1, 0, 2)

        # ── Step 2: step1 (dense) @ W_col (sparse) ────────────────────────────
        # Reshape step1: (B, n_to, n_from) → (B*n_to, n_from)
        step2_flat = step1.reshape(B * n_to, n_from)
        # Dense × sparse matmul: (B*n_to, n_from) @ (n_from, n_to) → (B*n_to, n_to)
        step2_flat = step2_flat @ W_col
        # Reshape back: (B*n_to, n_to) → (B, n_to, n_to)
        return step2_flat.reshape(B, n_to, n_to)

    return project_batch


# ── Projection metrics helpers ─────────────────────────────────────────────────

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


def compute_metrics(
    M_from: np.ndarray,
    M_to: np.ndarray,
    internal_mask: np.ndarray,
) -> dict[str, float]:
    """
    Compute projection quality metrics for a single FROM / TO matrix pair.

    Parameters
    ----------
    M_from        : (n_from, n_from) float32 — statewide FROM matrix
    M_to          : (n_to,   n_to  ) float32 — projected TO matrix (ext-ext already zeroed)
    internal_mask : (n_from,) bool — True for FROM indices touching the internal TO region

    Returns
    -------
    statewide    : total trips in the FROM matrix
    to_relevant  : FROM trips with origin OR destination touching the internal TO region
                   computed via inclusion-exclusion:
                       |origin ∈ TO| + |dest ∈ TO| − |both ∈ TO|
    projected    : total trips in the output TO matrix
    approx_loss  : to_relevant − projected
                   (trips not captured due to crosswalk approximation)
    """
    idx = np.where(internal_mask)[0]

    statewide   = float(M_from.sum())
    origin_sum  = float(M_from[idx, :].sum())
    dest_sum    = float(M_from[:, idx].sum())
    both_sum    = float(M_from[np.ix_(idx, idx)].sum())
    to_relevant = origin_sum + dest_sum - both_sum
    projected   = float(M_to.sum())
    approx_loss = to_relevant - projected

    return {
        "statewide":   statewide,
        "to_relevant": to_relevant,
        "projected":   projected,
        "approx_loss": approx_loss,
    }


def log_matrix_metrics(name: str, m: dict[str, float]) -> None:
    """Log projection metrics for a single matrix."""
    coverage_pct = 100.0 * m["to_relevant"] / m["statewide"]   if m["statewide"]   > 0 else 0.0
    loss_pct     = 100.0 * m["approx_loss"] / m["to_relevant"] if m["to_relevant"] > 0 else 0.0
    logger.info(
        "  %-22s  statewide: %12.0f  |  TO-relevant: %10.0f (%5.1f%%)  |"
        "  projected: %10.0f  |  approx-loss: %9.0f (%5.2f%%)",
        name,
        m["statewide"],
        m["to_relevant"], coverage_pct,
        m["projected"],
        m["approx_loss"], loss_pct,
    )


def log_aggregate_metrics(all_metrics: list[dict[str, float]]) -> None:
    """
    Log aggregate metrics summed across all projected matrices, followed by a
    plain-language interpretation of the two headline percentages.

    coverage %     — share of statewide trips that involve the TO region at all
    approx-loss %  — share of those relevant trips not captured by the projection
    """
    agg = {k: sum(m[k] for m in all_metrics) for k in all_metrics[0]}
    n   = len(all_metrics)

    coverage_pct = 100.0 * agg["to_relevant"] / agg["statewide"]   if agg["statewide"]   > 0 else 0.0
    loss_pct     = 100.0 * agg["approx_loss"] / agg["to_relevant"] if agg["to_relevant"] > 0 else 0.0

    logger.info(_SEP)
    logger.info(
        "  %-22s  statewide: %12.0f  |  TO-relevant: %10.0f (%5.1f%%)  |"
        "  projected: %10.0f  |  approx-loss: %9.0f (%5.2f%%)",
        f"TOTAL ({n} matrices)",
        agg["statewide"],
        agg["to_relevant"], coverage_pct,
        agg["projected"],
        agg["approx_loss"], loss_pct,
    )
    logger.info(_SEP)
    logger.info(
        "  coverage    %.1f%% — that share of statewide trips has at least one "
        "trip end in the TO region and is expected in the projected matrix.",
        coverage_pct,
    )
    logger.info(
        "  approx-loss %.2f%% — of those TO-region-relevant trips, that share was "
        "not captured, mainly because boundary FROM zones route part of their weight "
        "to gateways whose gateway×gateway O-D pairs are zeroed after projection.",
        loss_pct,
    )


# ── Entry point ────────────────────────────────────────────────────────────────

def main(config_path: str = "config/config.yaml") -> None:
    setup_logging()
    cfg = load_config(config_path)

    offset         = cfg["zones"]["zone_id_offset"]
    n_from         = cfg["zones"]["from_matrix_size"]
    int_lo, int_hi = cfg["zones"]["to_internal_range"]
    gw_lo,  gw_hi  = cfg["zones"]["to_gateway_range"]
    n_internal     = int_hi - int_lo + 1
    n_gateways     = gw_hi  - gw_lo  + 1
    n_to           = n_internal + n_gateways
    batch_size     = cfg["matrices"]["projection_batch_size"]
    matrix_names   = cfg["matrices"]["from_matrices_to_project"]

    out_path = cfg["paths"]["output_omx"]
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    # ── Load crosswalk and build JAX sparse weight matrices ───────────────────
    row_weight_col = cfg["matrices"]["row_weight"]
    col_weight_col = cfg["matrices"]["column_weight"]

    logger.info("Loading crosswalk from %s", cfg["paths"]["crosswalk"])
    crosswalk = pd.read_csv(cfg["paths"]["crosswalk"])
    W_row, W_col = build_weight_matrices(
        crosswalk, n_from, n_to, offset, int_lo, gw_lo,
        row_weight_col, col_weight_col,
    )

    # ── Precompute internal-zone mask for metrics ──────────────────────────────
    internal_mask = mask_1d(crosswalk, n_from, offset, int_lo, int_hi)
    logger.info(
        "TO-region mask: %d / %d FROM zones have weight in internal TO zones",
        int(internal_mask.sum()), n_from,
    )

    # ── Compile projection function (once, reused across batches) ──────────────
    logger.info("Compiling JAX sparse projection function (first call triggers JIT) …")
    project_batch = make_project_fn(W_row, W_col)

    # ── Identify available matrices in the FROM OMX ───────────────────────────
    with omx.open_file(cfg["paths"]["from_omx"], "r") as from_f:
        available = set(from_f.list_matrices())

    to_project = [n for n in matrix_names if n in available]
    skipped    = [n for n in matrix_names if n not in available]
    if skipped:
        logger.warning("Matrices not found in FROM OMX (skipped): %s", skipped)

    n_batches = math.ceil(len(to_project) / batch_size)
    logger.info(
        "Projecting %d matrices in %d batch(es) of up to %d",
        len(to_project), n_batches, batch_size,
    )

    # ── Project and write ──────────────────────────────────────────────────────
    all_metrics: list[dict[str, float]] = []

    logger.info(_SEP)
    logger.info(
        "  %-22s  %-26s  %-30s  %-26s  %s",
        "Matrix", "Statewide trips", "TO-relevant trips (coverage)",
        "Projected trips", "Approx-loss",
    )
    logger.info(_SEP)

    with omx.open_file(cfg["paths"]["from_omx"], "r") as from_f, \
         omx.open_file(out_path, "w") as out_f:

        for batch_idx in range(n_batches):
            batch_names = to_project[batch_idx * batch_size:(batch_idx + 1) * batch_size]

            # Load batch → (B, n_from, n_from) float32
            M_batch = jnp.stack(
                [jnp.array(np.array(from_f[n], dtype=np.float32)) for n in batch_names]
            )

            # Project entire batch in one JIT call; zero ext-ext block
            M_to_batch = project_batch(M_batch).at[:, n_internal:, n_internal:].set(0.0)

            for i, name in enumerate(batch_names):
                M_from_np = np.array(M_batch[i],    dtype=np.float32)
                M_to_np   = np.array(M_to_batch[i], dtype=np.float32)
                out_f[name] = M_to_np

                m = compute_metrics(M_from_np, M_to_np, internal_mask)
                log_matrix_metrics(name, m)
                all_metrics.append(m)

    log_aggregate_metrics(all_metrics)
    logger.info("Output written to %s", out_path)

def log_projection_metrics(matrix_name: str, original_matrix: np.ndarray, masked_matrix: np.ndarray, projected_matrix: np.ndarray) -> None:
    original_sum = float(original_matrix.sum())
    masked_sum   = float(masked_matrix.sum())
    projected_sum = float(projected_matrix.sum())
    logger.info(
        "  %-22s  original: %12.0f  |  masked: %12.0f  |  projected: %12.0f",
        matrix_name,
        original_sum,
        masked_sum,
        projected_sum,
    )

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

