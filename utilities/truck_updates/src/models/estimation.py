import pandas as pd
import statsmodels.api as sm

from src.models.specs import ModelSpec

def fit_model(
    df: pd.DataFrame,
    spec: ModelSpec,
    robust_cov_type: str = "HC3",
):
    """
    Fit a regression model from a ModelSpec.

    Parameters
    ----------
    df:
        Modeling dataframe.
    spec:
        Model specification.
    robust_cov_type:
        statsmodels covariance type. Common options: 'HC3', 'cluster', 'nonrobust'.

    Returns
    -------
    statsmodels regression results object.
    """
    model_df = df[spec.required_columns()].dropna().copy()

    y = model_df[spec.target]
    X = model_df[spec.features]
    # X = sm.add_constant(X, has_constant="add")

    if spec.model_type == "ols":
        model = sm.OLS(y, X)

        if robust_cov_type == "cluster":
            if spec.group_col is None:
                raise ValueError(
                    f"Model {spec.name} uses cluster covariance but has no group_col."
                )

            return model.fit(
                cov_type="cluster",
                cov_kwds={"groups": model_df[spec.group_col]},
            )

        return model.fit(cov_type=robust_cov_type)

    if spec.model_type == "wls":
        if spec.weight_col is None:
            raise ValueError(f"Model {spec.name} is WLS but has no weight_col.")

        model = sm.WLS(y, X, weights=model_df[spec.weight_col])
        return model.fit(cov_type=robust_cov_type)

    raise NotImplementedError(f"Model type not implemented: {spec.model_type}")