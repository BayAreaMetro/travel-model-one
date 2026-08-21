import pandas as pd


def rank_models(comparison_df: pd.DataFrame) -> pd.DataFrame:
    """
    Rank models using simple transparent criteria.

    Lower score is better.
    """
    ranked = comparison_df.copy()

    ranked["rank_rmse"] = ranked.groupby("target")["rmse"].rank()
    ranked["rank_mae"] = ranked.groupby("target")["mae"].rank()
    ranked["rank_bic"] = ranked.groupby("target")["bic"].rank()
    ranked["rank_adj_r2"] = ranked.groupby("target")["adj_r2"].rank(ascending=False)

    ranked["overall_rank_score"] = (
        ranked["rank_rmse"]
        + ranked["rank_mae"]
        + ranked["rank_bic"]
        + ranked["rank_adj_r2"]
    )

    ranked = ranked.sort_values(["target", "overall_rank_score"])

    return ranked