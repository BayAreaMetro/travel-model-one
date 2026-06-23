import re
import ast

from dataclasses import dataclass, field
from typing import Literal


ModelType = Literal["ols", "wls"]
cov_types = Literal["nonrobust", "fixed scale",
                     "HC0", "HC1", "HC2", "HC3", "HAC", "hac-panel", "hac-groupsum", "cluster"]



def extract_column_names(expr: str) -> list[str]:
    """Extract column names from a Python expression using AST."""
    tree = ast.parse(expr, mode='eval')
    cols = set()

    class ColumnVisitor(ast.NodeVisitor):
        def visit_Name(self, node):
            # Capture variable names (could be columns or function names)
            cols.add(node.id)

        def visit_Attribute(self, node):
            # Handles things like np.log
            # We only care about the base object (e.g., np)
            self.visit(node.value)

    ColumnVisitor().visit(tree)

    # Remove known non-column names (modules/functions)
    blacklist = {"np", "log", "exp"}  # extend if needed
    return [c for c in cols if c not in blacklist]




@dataclass(frozen=True)
class ModelSpec:
    name: str
    target: str
    features: list[str]
    model_type: ModelType = "ols"
    weight_col: str | None = None
    group_col: str | None = None
    description: str = ""
    tags: list[str] = field(default_factory=list)

    def required_columns(self) -> list[str]:
        # Scans the target and feature strings to extract individual column names
        all_exprs = [self.target, *self.features]
        extracted_cols = []
        
        for expr in all_exprs:
            # Matches any valid python variable/column name pattern
            extracted_cols.extend(extract_column_names(expr))

        cols = [*extracted_cols]

        if self.weight_col:
            cols.append(self.weight_col)

        if self.group_col:
            cols.append(self.group_col)

        # Remove duplicates while keeping order
        return list(dict.fromkeys(cols))