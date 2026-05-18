from pathlib import Path

import pandas as pd


def write_tableau_csv(
    df: pd.DataFrame,
    output_path: str | Path,
) -> None:
    """
    Write a Tableau-friendly CSV.

    Keeps column names flat and avoids index columns.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cleaned = df.copy()
    cleaned.columns = [
        col.lower()
        .strip()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        for col in cleaned.columns
    ]

    cleaned.to_csv(output_path, index=False)
