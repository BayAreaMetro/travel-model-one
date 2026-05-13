from dataclasses import dataclass, field
from typing import Literal


ModelType = Literal["ols", "wls"]
cov_types = Literal["nonrobust", "fixed scale",
                     "HC0", "HC1", "HC2", "HC3", "HAC", "hac-panel", "hac-groupsum", "cluster"]


@dataclass(frozen=True)
class ModelSpec:
    name: str
    target: str
    features: list[str]
    model_type: ModelType = "ols"
    weight_col: str | None = None
    group_col: str | None = None
    geography_id_col: str = "taz_id"
    description: str = ""
    tags: list[str] = field(default_factory=list)

    def required_columns(self) -> list[str]:
        cols = [self.target, *self.features, self.geography_id_col]

        if self.weight_col:
            cols.append(self.weight_col)

        if self.group_col:
            cols.append(self.group_col)

        return list(dict.fromkeys(cols))