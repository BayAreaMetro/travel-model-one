import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.models.specs import ModelSpec


def make_predictions(
    df: pd.DataFrame,
    spec: ModelSpec,
    model,
    extra_cols: list[str] | None = None,
) -> pd.DataFrame:
    """
    Predict model 
    """
    extra_cols = extra_cols or []

    cols = spec.required_columns() + extra_cols
    model_df = df[cols].dropna().copy()

    X = pd.DataFrame(
        {
            feat: model_df.eval(feat, engine = "python", resolvers=[{"np": np}]) for feat in spec.features
        },
        index=model_df.index
        )
    # X = sm.add_constant(X, has_constant="add")

    observed = model_df.eval(spec.target, engine = "python", resolvers=[{"np": np}]).to_numpy()
    predicted = model.predict(X)

    output = model_df[[*extra_cols]].copy()
    output["model_name"] = spec.name
    output["target"] = spec.target
    output["observed"] = observed
    output["predicted"] = predicted
    output["residual"] = observed - predicted
    output["abs_error"] = np.abs(output["residual"])
    output["squared_error"] = output["residual"] ** 2

    output["pct_error"] = np.where(
        output["observed"] != 0,
        output["residual"] / output["observed"],
        np.nan,
    )

    return output