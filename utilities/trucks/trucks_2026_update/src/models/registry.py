import yaml
from pathlib import Path

from src.models.specs import ModelSpec


def load_model_specs_from_yaml(path: str | Path) -> list[ModelSpec]:
    path = Path(path)

    with open(path, "r") as f:
        config = yaml.safe_load(f)

    specs = []

    for model_dict in config.get("models", []):
        specs.append(
            ModelSpec(
                name=model_dict["name"],
                target=model_dict["target"],
                features=model_dict["features"],
                model_type=model_dict.get("model_type", "ols"),
                weight_col=model_dict.get("weight_col"),
                group_col=model_dict.get("group_col"),
                geography_id_col=model_dict.get("geography_id_col", "taz_id"),
                description=model_dict.get("description", ""),
                tags=model_dict.get("tags", []),
            )
        )

    return specs