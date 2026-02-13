"""
Data models for calibration processing using Pydantic for validation.

Field Name Standardization Strategy:
- Model attributes use snake_case (Python convention): home_taz, work_location
- Field aliases accept original names: ZONE, WorkLocation, HomeTAZ
- Use model_dump() to export with standardized names
- Use model_dump(by_alias=True) to export with original names

"""
from typing import Optional, Literal
import pandas as pd
from enum import StrEnum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError

### Codebook Definitions for CTRAMP
class CTRAMPCounty(StrEnum):
    SAN_FRANCISCO = 'San Francisco'
    SAN_MATEO = 'San Mateo'
    SANTA_CLARA = 'Santa Clara'
    ALAMEDA = 'Alameda'
    CONTRA_COSTA = 'Contra Costa'
    SOLANO = 'Solano'
    NAPA = 'Napa'
    SONOMA = 'Sonoma'
    MARIN ='Marin'



### Data Model for Output Results
class CountySummary(BaseModel):
    """Model for county-to-county summary results."""
    model_config = ConfigDict(validate_by_name = True, validate_by_alias = True)

    home_county_name: CTRAMPCounty = Field(alias = 'HomeCounty_name')
    San_Francisco: float = Field(alias="San Francisco", ge=0)
    San_Mateo: float = Field(alias="San Mateo", ge=0)
    Santa_Clara: float = Field(alias="Santa Clara", ge=0)
    Alameda: float = Field(ge=0)
    Contra_Costa: float = Field(alias="Contra Costa", ge=0)
    Solano: float = Field(ge=0)
    Napa: float = Field(ge=0)
    Sonoma: float = Field(ge=0)
    Marin: float = Field(ge=0)
    

class TripLengthFrequency(BaseModel):
    """Model for trip length frequency distribution."""
    model_config = ConfigDict(validate_by_name = True, validate_by_alias = True)

    distbin: int = Field(ge=1, description = "Distance bin")
    # County columns
    San_Francisco: float = Field(alias="San Francisco", ge=0)
    San_Mateo: float = Field(alias="San Mateo", ge=0)
    Santa_Clara: float = Field(alias="Santa Clara", ge=0)
    Alameda: float = Field(ge=0)
    Contra_Costa: float = Field(alias="Contra Costa", ge=0)
    Solano: float = Field(ge=0)
    Napa: float = Field(ge=0)
    Sonoma: float = Field(ge=0)
    Marin: float = Field(ge=0)

    # Total column - REQUIRED
    Total: float = Field(ge=0, description="Total across all counties")


class AverageTripLength(BaseModel):
    """Model for average trip length by county and type."""
    county: CTRAMPCounty | Literal['Total']
    work: float
    univ: float
    school: float

class CalibrationResults(BaseModel):
    """Model for calibration processing results."""
    county_summary: Optional[dict] = None
    trip_tlfd_work: Optional[dict] = None
    trip_tlfd_univ: Optional[dict] = None
    trip_tlfd_school: Optional[dict] = None
    avg_trip_lengths: Optional[dict] = None


# Helper functions for DataFrame validation
def validate_dataframe(
        df: pd.DataFrame, 
        model_class,
        expected_rows: int | None = None) -> None:
    """
    Validate DataFrame rows against Pydantic model.

    Args:
        df: DataFrame to validate the Pydantic model
        model_class: Model Class
        expected_rows: Expected number of rows for validation
                        If None, does not validate for row count

    Raises:
        ValidationError: If any row fails validation

    """
    errors = []
        
    total_rows = len(df)

    # Check row count first if expected_rows is not none
    if expected_rows is not None:
        if total_rows != expected_rows:
            raise ValueError(
                f"{model_class.__name__} has {total_rows}, expected {expected_rows}"
            )
        else:
            print(f"✓ Row count validated for {model_class.__name__}")
    # Convert entire DataFrame to list of dicts once 
    rows = df.to_dict(orient = 'records')

    # Batch validate with progress reporting
    batch_size = 100_000
    error_groups: dict[str, list[int]] = {}
    max_unique_errors = 10

    for batch_start in range(0, total_rows, batch_size):
        batch_end = min(batch_start + batch_size, total_rows)
        batch = rows[batch_start:batch_end]

        # Validate each row in batch
        for i, row in enumerate(batch):
            row_idx = batch_start + i
            try:
                model_class(**row)
            except ValidationError as e:
                msg = str(e)
                if msg not in error_groups:
                    error_groups[msg] = []
                error_groups[msg].append(row_idx)

                if len(error_groups) >= max_unique_errors:
                    break
        if len(error_groups) >= max_unique_errors:
            break

    _report_errors(error_groups)

def _report_errors(error_groups: dict[str, list[int]]) -> None:
    """Report validation errors for a DataFrame"""
    if not error_groups:
        return
    
    total_error_count = sum(len(rows) for rows in error_groups.values())

    # Format error summary
    error_lines = []
    max_rows_to_show = 3

    for msg, row_indices in error_groups.items():
        num_affected = len(row_indices)

        if num_affected <= max_rows_to_show:
            rows_str = f"Row(s) {', '.join(map(str, row_indices))}"
        else:
            shown = row_indices[:max_rows_to_show]
            rows_str = f"{num_affected} rows (e.g., {', '.join(map(str, shown))})"

        error_lines.append(f"  {rows_str}: {msg}")

    error_summary = "\n".join(error_lines)
    num_unique = len(error_groups)

    summary_msg = (
        f"Found {num_unique} unique error type"
        f"{'s' if num_unique > 1 else ''} "
        f"affecting {total_error_count} row"
        f"{'s' if total_error_count > 1 else ''}:\n"
        f"{error_summary}"
    )

    raise ValueError(
        summary_msg
    )


