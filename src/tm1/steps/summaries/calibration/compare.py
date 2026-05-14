"""Side-by-side comparison of summarization results across labeled datasets."""

import polars as pl


def build_comparison(
    results: dict[str, dict[str, dict[str, pl.DataFrame]]],
) -> dict[str, dict[str, pl.DataFrame]]:
    """Merge results from multiple datasets into comparison DataFrames.

    Args:
        results: ``{label: {submodel: {table_name: DataFrame}}}``

    Returns:
        ``{submodel: {table_name: comparison_DataFrame}}`` where each
        comparison DataFrame has the original index columns plus one value
        column per label (suffixed with the label name).
    """
    labels = list(results)
    if len(labels) < 2:  # noqa: PLR2004
        return {}

    all_submodels = _collect_submodels(results)
    comparisons: dict[str, dict[str, pl.DataFrame]] = {}

    for submodel in sorted(all_submodels):
        tables = _compare_submodel(results, labels, submodel)
        if tables:
            comparisons[submodel] = tables

    return comparisons


def _collect_submodels(
    results: dict[str, dict[str, dict[str, pl.DataFrame]]],
) -> set[str]:
    """Return the union of submodel names across all labels."""
    out: set[str] = set()
    for per_label in results.values():
        out.update(per_label)
    return out


def _compare_submodel(
    results: dict[str, dict[str, dict[str, pl.DataFrame]]],
    labels: list[str],
    submodel: str,
) -> dict[str, pl.DataFrame]:
    """Build comparison tables for one submodel across labels."""
    table_names: set[str] = set()
    for label in labels:
        sub = results.get(label, {}).get(submodel, {})
        if sub:
            table_names.update(sub)

    # Tables containing raw samples should not be merged (they are used
    # directly by renderers, not compared side-by-side).
    _SKIP_PREFIXES = ("dist_samples",)

    out: dict[str, pl.DataFrame] = {}
    for table_name in sorted(table_names):
        if any(table_name.startswith(p) for p in _SKIP_PREFIXES):
            continue
        frames: list[tuple[str, pl.DataFrame]] = []
        for label in labels:
            df = results.get(label, {}).get(submodel, {}).get(table_name)
            if df is not None:
                frames.append((label, df))
        if len(frames) < 2:  # noqa: PLR2004
            continue
        merged = _merge_frames(frames, table_name)
        if merged is not None:
            out[table_name] = merged
    return out


def write_comparison_csvs(
    comparisons: dict[str, dict[str, pl.DataFrame]],
    output_dir: object,
) -> None:
    """Write comparison DataFrames as CSVs under *output_dir*/comparison/."""
    from pathlib import Path  # noqa: PLC0415

    out = Path(output_dir) / "comparison"
    out.mkdir(parents=True, exist_ok=True)

    for submodel, tables in comparisons.items():
        for table_name, df in tables.items():
            path = out / f"{submodel}_{table_name}.csv"
            df.write_csv(path)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _merge_frames(
    frames: list[tuple[str, pl.DataFrame]],
    table_name: str,  # noqa: ARG001
) -> pl.DataFrame | None:
    """Merge multiple labeled DataFrames on shared index columns.

    Strategy: identify columns that look like indices (non-float, present in
    all frames) and join on those, suffixing value columns with the label.
    """
    if not frames:
        return None

    # Find common non-float columns to use as join keys
    first_label, first_df = frames[0]
    if first_df.width == 0:
        return None
    index_cols = [
        c
        for c in first_df.columns
        if first_df.schema[c] not in (pl.Float32, pl.Float64)
    ]
    if not index_cols:
        # Fall back to first column as index
        index_cols = [first_df.columns[0]]

    value_cols = [c for c in first_df.columns if c not in index_cols]

    # Start with the first frame
    merged = first_df.rename({vc: f"{vc}_{first_label}" for vc in value_cols})

    for label, df in frames[1:]:
        if df.width == 0:
            continue
        renamed = df.rename({vc: f"{vc}_{label}" for vc in value_cols if vc in df.columns})
        merged = merged.join(renamed, on=index_cols, how="full", coalesce=True)

    return merged
