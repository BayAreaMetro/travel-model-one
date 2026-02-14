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
from enum import StrEnum, Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError
from pydantic_core import core_schema

################################################################
### Codebook Definitions for CTRAMP
################################################################

class CTRAMPCounty(Enum):
    SAN_FRANCISCO = (1, 'San Francisco')
    SAN_MATEO = (2, 'San Mateo')
    SANTA_CLARA = (3, 'Santa Clara')
    ALAMEDA = (4, 'Alameda')
    CONTRA_COSTA = (5, 'Contra Costa')
    SOLANO = (6, 'Solano')
    NAPA = (7, 'Napa')
    SONOMA = (8, 'Sonoma')
    MARIN = (9, 'Marin')

    @property
    def id(self):
        return self.value[0]
    
    @property
    def label(self):
        return self.value[1]
    
    @classmethod
    def from_value(cls, v):
        if isinstance(v, cls):
            return v
        for member in cls:
            if v == member.id or v == member.label:
                return member
        raise ValueError(f"Invalid county: {v}")

    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler):
        return core_schema.no_info_plain_validator_function(cls.from_value)
    
class CTRAMPPersonType(Enum):
    FULL_TIME_WORKER = (1, "Full-time worker")
    PART_TIME_WORKER = (2, "Part-time worker")
    UNIVERSITY_STUDENT = (3, "University student")
    NON_WORKER = (4, "Nonworker")
    RETIRED = (5, "Retired")
    CHILD_NON_DRIVING_AGE = (6, "Child of non-driving age")
    CHILD_DRIVING_AGE = (7, "Child of driving age")
    CHILD_UNDER_5 = (8, "Child too young for school")

class CTRAMPPurpose(Enum):
    """Enumeration for tour purpose."""

    HOME = "Home", "Home"
    WORK_LOW = "work_low", "Work - Low income"
    WORK_MED = "work_med", "Work - Medium income"
    WORK_HIGH = "work_high", "Work - High income"
    WORK_VERY_HIGH = "work_very high", "Work - Very High income"
    UNIVERSITY = "university", "University"
    SCHOOL_HIGH = "school_high", "School - High school"
    SCHOOL_GRADE = "school_grade", "School - Grade school"
    ATWORK_BUSINESS = "atwork_business", "At-work - Business"
    ATWORK_EAT = "atwork_eat", "At-work - Eating"
    ATWORK_MAINT = "atwork_maint", "At-work - Maintenance"
    EATOUT = "eatout", "Eating out"
    ESCORT_KIDS = "escort_kids", "Escort - Kids"
    ESCORT_NO_KIDS = "escort_no kids", "Escort - No kids"
    SHOPPING = "shopping", "Shopping"
    SOCIAL = "social", "Social/recreational"
    OTHMAINT = "othmaint", "Other maintenance"
    OTHDISCR = "othdiscr", "Other discretionary"    


################################################################
### Data Model for Output Results
################################################################

# Usual Work School Location
class CountyTripSummary(BaseModel):
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

# Auto Ownership 
class AutoOwnershipModel(BaseModel):
    ZER0_VEHICLE: float = Field(ge =0, alias = 0) | Literal['NA']
    ONE_VEHICLE: float = Field(ge =0, alias = 1) | Literal['NA']
    TWO_VEHICLE: float = Field(ge =0, alias = 2) | Literal['NA']
    THREE_VEHICLE: float = Field(ge =0, alias = 3) | Literal['NA']
    FOUR_PLUS_VEHICLE: float = Field(ge =0, alias = 4) | Literal['NA']

class AutoOwnershipCountySummary(AutoOwnershipModel):
    """Model for auto ownership county summmary"""
    model_config = ConfigDict(validate_by_name = True, validate_by_alias = True)
    COUNTY:CTRAMPCounty
    county_name: CTRAMPCounty

class AutoOwnershipTAZSummary(AutoOwnershipModel):
    model_config = ConfigDict(validate_by_name = True, validate_by_alias = True)
    TAZ: int = Field(ge = 1, alias = 'taz')
    source: str

class AutoOwnershipLongSummary(BaseModel):
    model_config = ConfigDict(validate_by_name = True, validate_by_alias = True)
    TAZ: int = Field(ge = 1, alias = 'taz')
    num_vehicle: int = Field(ge = 0)
    num_hh: float = Field(ge = 0, description="Number of households")
    source: str

# CDAP
class CDAPSummary(BaseModel):
    model_config = ConfigDict(validate_by_name = True, validate_by_alias = True)
    person_type: CTRAMPPersonType
    home: float = Field(ge=0, alias = 'H') | Literal['NA']
    mandatory: float = Field(ge=0, alias = 'M') | Literal['NA']
    non_mandatory: float = Field(ge=0, alias = 'N') | Literal['NA']

# Non-Work Choice Destination 
class NonMandAvgTripLength(BaseModel):
    trip_purpose: CTRAMPPurpose = Field(alias='trip_type')
    avg_trip_length: float = Field(ge=0, alias = 'mean_trip_length')

class NonMandTripLengthFrequency(BaseModel):
    distbin: int = Field(ge = 1, description = 'Distance bin')
    escort: float = Field(ge=0, alias=('Escort'))
    shop: float = Field(ge=0, alias=('Shop'))
    maintenance: float = Field(ge=0, alias=('Maintenance'))
    eat_out: float = Field(ge=0, alias=('eatout'))
    visit: float = Field(ge = 0, alias = ('Visit'))
    discretionary: float = Field(ge=0)
    at_work: float = Field(ge=0, alias=('atwork'))


################################################################
# # Helper functions for DataFrame validation
################################################################
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


