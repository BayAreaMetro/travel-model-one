import numpy as np
import pandas as pd


def regression_metrics(
    observed: pd.Series,
    predicted: pd.Series,
) -> dict:
    residual = observed - predicted

    return {
        "n_obs": int(observed.notna().sum()),
        "mean_observed": float(observed.mean()),
        "mean_predicted": float(predicted.mean()),
        "total_observed": float(observed.sum()),
        "total_predicted": float(predicted.sum()),
        "bias": float(residual.mean()),
        "total_bias": float(predicted.sum() - observed.sum()),
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual**2))),
    }


def aggregate_validation(
    prediction_df: pd.DataFrame,
    group_cols: list[str],
) -> pd.DataFrame:
    """
    Aggregate observed and predicted values by group_cols (e.g: geography, county, district, etc.)
    """
    grouped = (
        prediction_df
        .groupby(["model_name", "target", *group_cols], dropna=False)
        .agg(
            observed=("observed", "sum"),
            predicted=("predicted", "sum"),
            n_geographies=("observed", "size"),
        )
        .reset_index()
    )

    grouped["difference"] = grouped["predicted"] - grouped["observed"]
    grouped["pct_difference"] = np.where(
        grouped["observed"] != 0,
        grouped["difference"] / grouped["observed"],
        np.nan,
    )

    return grouped