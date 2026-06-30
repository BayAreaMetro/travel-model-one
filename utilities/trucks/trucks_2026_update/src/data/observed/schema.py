import pandas as pd

EXPECTED_COLUMNS = {
    "count_location_id": "str",
    "link_id": "str",
    "tod": "str",
    "truck_type_1": "str",
    "truck_type_2": "str",
    "type": "str",
    "source": "str",
    "quality_flag": "str",
    "volume": "float64",
}


def validate_observed_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and normalize observed dataset schema.

    - Ensures required columns exist
    - Enforces column types
    - Reorders columns
    """

    #  Check missing columns
    missing = set(EXPECTED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Keep only expected columns (optional but recommended)
    df = df[list(EXPECTED_COLUMNS.keys())].copy()

    # Enforce dtypes
    for col, dtype in EXPECTED_COLUMNS.items():
        if col == "volume":
            df[col] = pd.to_numeric(df[col], errors="raise")
        else:
            df[col] = df[col].astype(dtype)

    #  Basic sanity checks
    if df["volume"].isna().any():
        raise ValueError("Column 'volume' contains NaNs")

    return df