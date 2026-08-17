from pathlib import Path

import pandas as pd

from src.models.estimation import fit_model
from src.models.prediction import make_predictions
from src.models.specs import ModelSpec
from src.validation.metrics import regression_metrics, aggregate_validation
from src.validation.model_selection import rank_models
from src.reporting.tableau import write_tableau_csv


def run_model_suite(
    df: pd.DataFrame,
    model_specs: list[ModelSpec],
    output_dir: str | Path,
    extra_prediction_cols: list[str] | None = None,
    aggregate_group_cols: list[str] | None = None,
):
    """
    Run a suite of regression models and write Tableau-ready outputs.
    """
    output_dir = Path(output_dir)
    extra_prediction_cols = extra_prediction_cols or []
    aggregate_group_cols = aggregate_group_cols or []

    model_summaries = []
    coefficient_tables = []
    prediction_tables = []

    fitted_models = {}

    for spec in model_specs:
        results = fit_model(df, spec)
        fitted_models[spec.name] = results

        predictions = make_predictions(
            df=df,
            spec=spec,
            model=results,
            extra_cols=extra_prediction_cols,
        )

        metrics = regression_metrics(
            observed=predictions["observed"],
            predicted=predictions["predicted"],
        )

        model_summaries.append(
            {
                "model_name": spec.name,
                "target": spec.target,
                "model_type": spec.model_type,
                "features": ", ".join(spec.features),
                "n_features": len(spec.features),
                "description": spec.description,
                "tags": ", ".join(spec.tags),
                "r2": results.rsquared if hasattr(results, "rsquared") else None,
                "adj_r2": results.rsquared_adj if hasattr(results, "rsquared_adj") else None,
                "aic": results.aic if hasattr(results, "aic") else None,
                "bic": results.bic if hasattr(results, "bic") else None,
                **metrics,
            }
        )

        coef_df = pd.DataFrame(
            {
                "model_name": spec.name,
                "target": spec.target,
                "term": results.params.index,
                "coefficient": results.params.values,
                "std_error": results.bse.values,
                "t_value": results.tvalues.values,
                "p_value": results.pvalues.values,
            }
        )

        coefficient_tables.append(coef_df)
        prediction_tables.append(predictions)

    comparison = pd.DataFrame(model_summaries)
    coefficients = pd.concat(coefficient_tables, ignore_index=True)
    predictions = pd.concat(prediction_tables, ignore_index=True)

    ranked_comparison = rank_models(comparison)

    write_tableau_csv(
        ranked_comparison,
        output_dir / "tableau" / "model_comparison.csv",
    )

    write_tableau_csv(
        coefficients,
        output_dir / "tableau" / "model_coefficients.csv",
    )

    write_tableau_csv(
        predictions,
        output_dir / "tableau" / "model_predictions.csv",
    )

    if aggregate_group_cols:
        aggregate_df = aggregate_validation(
            predictions,
            group_cols=aggregate_group_cols,
        )

        write_tableau_csv(
            aggregate_df,
            output_dir / "tableau" / "aggregate_validation.csv",
        )

    return {
        "comparison": ranked_comparison,
        "coefficients": coefficients,
        "predictions": predictions,
        "fitted_models": fitted_models,
    }