"""BATS 2023 project-specific cleaning step.

Auto-discovered by ``tm1.steps.prepare_survey`` when it finds ``clean_*.py``
next to the pipeline config file.  The function name **must** match the module
name (``clean_2023_bats``).
"""

import logging

import polars as pl
from data_canon.codebook.households import IncomeBroad, ResidenceRentOwn, ResidenceType
from data_canon.codebook.persons import Ethnicity, Race
from pipeline.decoration import step
from utils.helpers import add_time_columns, expr_haversine

log = logging.getLogger(__name__)


@step()
def clean_2023_bats(
    households: pl.DataFrame,
    persons: pl.DataFrame,
    days: pl.DataFrame,
    unlinked_trips: pl.DataFrame,
) -> dict[str, pl.DataFrame]:
    """Custom cleaning steps for BATS 2023 survey data."""
    # CLEANUP UNLINKED TRIPS =================================
    log.info("Cleaning 2023 trip data")

    unlinked_trips = unlinked_trips.rename(
        {
            "arrive_second": "arrive_seconds",
            "trip_id": "unlinked_trip_id",
        }
    )

    unlinked_trips = add_time_columns(unlinked_trips)

    swap_condition = pl.col("depart_time") > pl.col("arrive_time")
    swap_cols = [
        ("depart_time", "arrive_time"),
        ("depart_hour", "arrive_hour"),
        ("depart_minute", "arrive_minute"),
        ("depart_seconds", "arrive_seconds"),
    ]

    unlinked_trips = unlinked_trips.with_columns(
        [
            pl.when(swap_condition).then(pl.col(b)).otherwise(pl.col(a)).alias(a)
            for a, b in swap_cols
        ]
        + [
            pl.when(swap_condition).then(pl.col(a)).otherwise(pl.col(b)).alias(b)
            for a, b in swap_cols
        ]
    )

    unlinked_trips = unlinked_trips.with_columns(
        [
            pl.when(pl.col(col_name) == -1).then(996).otherwise(pl.col(col_name)).alias(col_name)
            for col_name in [
                "o_purpose",
                "d_purpose",
                "o_purpose_category",
                "d_purpose_category",
            ]
        ]
    )

    unlinked_trips = unlinked_trips.with_columns(
        pl.when(pl.col("distance_meters").is_null())
        .then(
            expr_haversine(
                pl.col("o_lon"),
                pl.col("o_lat"),
                pl.col("d_lon"),
                pl.col("d_lat"),
            )
        )
        .otherwise(pl.col("distance_meters"))
        .alias("distance_meters")
    )

    unlinked_trips = unlinked_trips.with_columns(
        pl.when(pl.col("duration_minutes").is_null())
        .then((pl.col("arrive_time") - pl.col("depart_time")).dt.total_minutes())
        .otherwise(pl.col("duration_minutes"))
        .alias("duration_minutes")
    )

    unlinked_trips = unlinked_trips.drop(
        [
            "depart_date",
            "depart_hour",
            "depart_minute",
            "depart_seconds",
            "arrive_date",
            "arrive_hour",
            "arrive_minute",
            "arrive_seconds",
        ]
    )

    # ADD DAYS FOR PERSONS WITHOUT DAYS =================================
    persons_without_days = persons.filter(
        ~pl.col("person_id").is_in(days["person_id"].unique().implode())
    )

    log.info(
        "Creating dummy days for %d persons without days",
        len(persons_without_days),
    )

    days_for_dow = (
        days.select(["hh_id", "travel_dow", "travel_date", "day_num"])
        .filter(pl.col("hh_id").is_in(persons_without_days["hh_id"].unique().implode()))
        .unique()
    )

    day_cols = ["hh_id", "person_id", "day_id", "travel_dow", "travel_date", "day_num"]

    dummy_days = (
        persons_without_days.join(days_for_dow, on="hh_id", how="left")
        .with_columns(
            (pl.col("person_id") * 100 + pl.col("day_num")).alias("day_id")
        )
        .select(day_cols)
    )
    _days = days.clone()
    days = pl.concat([_days, dummy_days], how="diagonal")

    # CLEANUP HOUSEHOLD ATTRIBUTES =================================
    hh_attributes = persons.group_by("hh_id").agg(
        pl.col("residence_rent_own")
        .filter(
            ~pl.col("residence_rent_own").is_in(
                [ResidenceRentOwn.MISSING.value, ResidenceRentOwn.PNTA.value]
            )
        )
        .mode()
        .first()
        .fill_null(995),
        pl.col("residence_type")
        .filter(pl.col("residence_type") != ResidenceType.MISSING.value)
        .mode()
        .first()
        .fill_null(995),
    )
    households = households.join(hh_attributes, on="hh_id", how="left")

    # RECODE INCOME =========================================
    if "income_broad" in households.columns:
        households = households.rename({"income_broad": "income_bin"})
    elif "income_bin" not in households.columns:
        log.warning("No income column found — creating income_bin as MISSING")
        households = households.with_columns(pl.lit(IncomeBroad.MISSING.value).alias("income_bin"))

    valid_codes = {m.value for m in IncomeBroad}
    households = households.with_columns(
        pl.when(pl.col("income_bin").is_in(valid_codes))
        .then(pl.col("income_bin"))
        .otherwise(IncomeBroad.MISSING.value)
        .alias("income_bin")
    )

    # CLEANUP PERSON ATTRIBUTES =================================
    eth_cols = ["ethnicity_1", "ethnicity_2", "ethnicity_3", "ethnicity_4", "ethnicity_997"]
    race_cols = ["race_1", "race_2", "race_3", "race_4", "race_5", "race_997"]

    for col in [*race_cols, *eth_cols, "race_999", "ethnicity_999"]:
        if col in persons.columns:
            persons = persons.with_columns(
                pl.when(pl.col(col) == 995)  # noqa: PLR2004
                .then(0)
                .otherwise(pl.col(col))
                .alias(col)
            ).with_columns(pl.col(col).fill_null(0))

    persons = persons.with_columns(
        pl.when(pl.col("race_1") == 1)
        .then(pl.lit(Race.AFAM.value))
        .when(pl.col("race_2") == 1)
        .then(pl.lit(Race.NATIVE.value))
        .when(pl.col("race_3") == 1)
        .then(pl.lit(Race.ASIAN.value))
        .when(pl.col("race_4") == 1)
        .then(pl.lit(Race.PACIFIC.value))
        .when(pl.col("race_5") == 1)
        .then(pl.lit(Race.WHITE.value))
        .when(pl.col("race_997") == 1)
        .then(pl.lit(Race.OTHER.value))
        .when(pl.sum_horizontal(pl.col(race_cols)) > 1)
        .then(pl.lit(Race.MULTI.value))
        .when(pl.col("race_999") == 1)
        .then(pl.lit(None))
        .otherwise(None)
        .alias("race")
    )

    persons = persons.with_columns(
        pl.when(pl.col("ethnicity_1") == 1)
        .then(pl.lit(Ethnicity.NOT_HISPANIC.value))
        .when(pl.col("ethnicity_2") == 1)
        .then(pl.lit(Ethnicity.MEXICAN.value))
        .when(pl.col("ethnicity_3") == 1)
        .then(pl.lit(Ethnicity.PUERTO_RICAN.value))
        .when(pl.col("ethnicity_4") == 1)
        .then(pl.lit(Ethnicity.CUBAN.value))
        .when(pl.col("ethnicity_997") == 1)
        .then(pl.lit(Ethnicity.OTHER.value))
        .when(pl.sum_horizontal(pl.col(eth_cols)) > 1)
        .then(pl.lit(Ethnicity.OTHER.value))
        .when(pl.col("ethnicity_999") == 1)
        .then(pl.lit(None))
        .otherwise(None)
        .alias("ethnicity")
    )

    # ASSIGN COMPLETION STATUS =========================================
    results = {
        "households": households,
        "persons": persons,
        "days": days,
        "unlinked_trips": unlinked_trips,
    }

    column_mapping = {
        "households": "is_complete",
        "persons": "is_complete",
        "days": "is_complete",
        "unlinked_trips": "trip_survey_complete",
    }

    for key, old_col in column_mapping.items():
        results[key] = (
            results[key]
            .rename({old_col: "complete"})
            .with_columns(pl.col("complete").cast(pl.Boolean))
        )

    return results
