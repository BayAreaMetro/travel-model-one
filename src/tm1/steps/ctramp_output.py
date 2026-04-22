"""ActivitySim → CTRAMP output converter.

Shared by core_summaries and calibration_summaries.  Reads ActivitySim
``final_*.csv`` outputs and writes CTRAMP-format CSVs into a ``main/``
directory that downstream R (or Python) summaries expect.

Column mapping is documented in ``docs/OUTPUT_MAPPING.md``.
"""

import logging
from pathlib import Path

import polars as pl

log = logging.getLogger(__name__)

# ActivitySim ptype int → CTRAMP person-type text labels
PTYPE_LABELS = {
    1: "Full-time worker",
    2: "Part-time worker",
    3: "University student",
    4: "Non-worker",
    5: "Retired",
    6: "Student of driving age",
    7: "Student of non-driving age",
    8: "Child too young for school",
}

# ActivitySim mode label → CTRAMP integer code (1-indexed).
# Order matches tour_mode_choice.csv / trip_mode_choice.csv column headers.
MODE_TO_INT: dict[str, int] = {
    "DRIVEALONEFREE": 1,
    "DRIVEALONEPAY": 2,
    "SHARED2FREE": 3,
    "SHARED2PAY": 4,
    "SHARED3FREE": 5,
    "SHARED3PAY": 6,
    "WALK": 7,
    "BIKE": 8,
    "WALK_LOC": 9,
    "WALK_LRF": 10,
    "WALK_EXP": 11,
    "WALK_HVY": 12,
    "WALK_COM": 13,
    "DRIVE_LOC": 14,
    "DRIVE_LRF": 15,
    "DRIVE_EXP": 16,
    "DRIVE_HVY": 17,
    "DRIVE_COM": 18,
    "TAXI": 19,
    "TNC_SINGLE": 20,
    "TNC_SHARED": 21,
}


def export_ctramp_csvs(output_dir: Path, work_dir: Path, iter_label: str) -> None:
    """Read ActivitySim outputs and write CTRAMP-format CSVs into ``work_dir/main/``.

    Parameters
    ----------
    output_dir : Path
        Directory containing ActivitySim ``final_*.csv`` files.
    work_dir : Path
        Root of the CTRAMP layout.  CSVs are written to ``work_dir/main/``.
    iter_label : str
        Iteration label for filenames (e.g. ``"1"``).
    """
    main = work_dir / "main"
    main.mkdir(parents=True, exist_ok=True)

    # --- Load ActivitySim outputs ---
    hh = pl.read_csv(output_dir / "final_households.csv")
    per = pl.read_csv(output_dir / "final_persons.csv")
    tours = pl.read_csv(output_dir / "final_tours.csv")
    trips = pl.read_csv(output_dir / "final_trips.csv")

    # --- person_num: row number within household ---
    per = per.with_columns(
        pl.col("person_id").rank("ordinal").over("household_id").cast(pl.Int32).alias("person_num")
    )

    # sample_rate lives on hh only in ActivitySim; propagate to per & tours
    hh_sr = hh.select("household_id", "sample_rate")
    per = per.join(hh_sr, on="household_id", how="left")
    tours = tours.join(hh_sr, on="household_id", how="left", suffix="_hh")

    # Convert mode labels (strings) → CTRAMP integer codes
    tours = tours.with_columns(
        pl.col("tour_mode").replace_strict(MODE_TO_INT, default=0).alias("tour_mode")
    )
    trips = trips.with_columns(
        pl.col("trip_mode").replace_strict(MODE_TO_INT, default=0).alias("trip_mode")
    )

    # -----------------------------------------------------------------
    # householdData
    # -----------------------------------------------------------------
    household_data = hh.select(
        pl.col("household_id").alias("hh_id"),
        pl.col("home_zone_id").alias("taz"),
        pl.lit(0).cast(pl.Int32).alias("walk_subzone"),  # TODO: needs walkAccessBuffers; affects JourneyToWork group-by
        pl.col("income"),
        pl.col("auto_ownership").alias("autos"),
        pl.col("hhsize").alias("size"),
        pl.col("num_workers").alias("workers"),
        pl.col("sample_rate").alias("sampleRate"),
    )
    household_data.write_csv(main / f"householdData_{iter_label}.csv")
    log.info("  Wrote householdData_%s.csv (%d rows)", iter_label, len(household_data))

    # -----------------------------------------------------------------
    # personData
    # -----------------------------------------------------------------
    person_data = per.select(
        pl.col("household_id").alias("hh_id"),
        pl.col("person_id"),
        pl.col("person_num"),
        pl.col("age"),
        pl.col("sex").map_elements(lambda v: "m" if v == 1 else "f", return_dtype=pl.Utf8).alias("gender"),
        pl.col("ptype").replace_strict(PTYPE_LABELS, default="Unknown").alias("type"),
        pl.col("value_of_time"),
        pl.col("free_parking_at_work").alias("fp_choice"),
        pl.col("cdap_activity").alias("activity_pattern"),
        pl.col("mandatory_tour_frequency").alias("imf_choice"),
        pl.col("non_mandatory_tour_frequency").alias("inmf_choice"),
        pl.col("sample_rate").alias("sampleRate"),
        pl.lit(0).cast(pl.Int32).alias("wfh_choice"),  # TODO: not yet modeled in ActivitySim
    )
    person_data.write_csv(main / f"personData_{iter_label}.csv")
    log.info("  Wrote personData_%s.csv (%d rows)", iter_label, len(person_data))

    # -----------------------------------------------------------------
    # Tour columns shared by indiv / joint
    # -----------------------------------------------------------------
    _TOUR_COLS = [
        pl.col("household_id").alias("hh_id"),
        pl.col("person_id"),
        pl.col("tour_id"),
        pl.col("primary_purpose").alias("tour_purpose"),
        pl.col("tour_category"),
        pl.col("origin").alias("orig_taz"),
        pl.col("destination").alias("dest_taz"),
        pl.col("start").alias("start_hour"),
        pl.col("end").alias("end_hour"),
        pl.col("tour_mode"),
    ]

    # -----------------------------------------------------------------
    # indivTourData
    # -----------------------------------------------------------------
    indiv_tours = tours.filter(pl.col("tour_category") != "joint")
    tour_per_num = per.select("person_id", "person_num", "ptype")
    indiv_tours_j = indiv_tours.join(tour_per_num, on="person_id", how="left")
    indiv_tour_data = indiv_tours_j.select(
        *_TOUR_COLS,
        pl.col("person_num"),
        pl.col("ptype").alias("person_type"),
        pl.col("stop_frequency").alias("atWork_freq"),  # R drops this; must exist
        pl.col("sample_rate").alias("sampleRate"),
    )
    indiv_tour_data.write_csv(main / f"indivTourData_{iter_label}.csv")
    log.info("  Wrote indivTourData_%s.csv (%d rows)", iter_label, len(indiv_tour_data))

    # -----------------------------------------------------------------
    # jointTourData
    # -----------------------------------------------------------------
    joint_tours = tours.filter(pl.col("tour_category") == "joint")
    # tour_participants: space-separated person_nums (R unwinds these)
    jtp_csv = output_dir / "final_joint_tour_participants.csv"
    if jtp_csv.exists():
        jtp = pl.read_csv(jtp_csv)
        jtp_with_num = jtp.join(per.select("person_id", "person_num"), on="person_id", how="left")
        tour_parts = (
            jtp_with_num
            .sort("tour_id", "person_num")
            .group_by("tour_id")
            .agg(pl.col("person_num").cast(pl.Utf8).str.concat(" ").alias("tour_participants"))
        )
        joint_tours = joint_tours.join(tour_parts, on="tour_id", how="left")
    else:
        log.warning("No final_joint_tour_participants.csv — tour_participants will be empty")
        joint_tours = joint_tours.with_columns(pl.lit("").alias("tour_participants"))

    joint_tour_data = joint_tours.select(
        pl.col("household_id").alias("hh_id"),
        pl.col("tour_id"),
        pl.col("tour_category"),
        pl.col("primary_purpose").alias("tour_purpose"),
        pl.col("composition").alias("tour_composition"),
        pl.col("tour_participants"),
        pl.col("origin").alias("orig_taz"),
        pl.col("destination").alias("dest_taz"),
        pl.col("start").alias("start_hour"),
        pl.col("end").alias("end_hour"),
        pl.col("tour_mode"),
        pl.col("sample_rate").alias("sampleRate"),
    )
    joint_tour_data.write_csv(main / f"jointTourData_{iter_label}.csv")
    log.info("  Wrote jointTourData_%s.csv (%d rows)", iter_label, len(joint_tour_data))

    # -----------------------------------------------------------------
    # Trip prep: join tour_category + sample_rate, derive fields
    # -----------------------------------------------------------------
    tour_keys = tours.select("tour_id", "tour_category", "tour_mode",
                             "primary_purpose", "number_of_participants",
                             "sample_rate")

    trip = (
        trips
        .join(tour_keys, on="tour_id", how="left", suffix="_tour")
    )

    # orig_purpose: previous trip's purpose within the same tour,
    # "Home" for first outbound, tour purpose for first inbound
    trip = trip.sort("household_id", "person_id", "tour_id", "outbound", "trip_num")
    trip = trip.with_columns(
        pl.col("purpose")
        .shift(1)
        .over("tour_id", "outbound")
        .alias("_prev_purpose")
    )
    trip = trip.with_columns(
        pl.when(pl.col("_prev_purpose").is_not_null())
        .then(pl.col("_prev_purpose"))
        .when(pl.col("outbound"))
        .then(pl.lit("Home"))
        .otherwise(pl.col("primary_purpose"))
        .alias("orig_purpose")
    )

    # inbound = 1 - outbound
    trip = trip.with_columns(
        pl.when(pl.col("outbound"))
        .then(pl.lit(0))
        .otherwise(pl.lit(1))
        .cast(pl.Int32)
        .alias("inbound")
    )

    # stop_id = trip_num - 1
    trip = trip.with_columns(
        (pl.col("trip_num") - 1).cast(pl.Int32).alias("stop_id")
    )

    # person_num from per
    per_num = per.select("person_id", "person_num")
    trip = trip.join(per_num, on="person_id", how="left")

    # -----------------------------------------------------------------
    # Shared trip columns (individual)
    # -----------------------------------------------------------------
    _TRIP_COLS = [
        pl.col("household_id").alias("hh_id"),
        pl.col("person_id"),
        pl.col("person_num"),
        pl.col("tour_id"),
        pl.col("stop_id"),
        pl.col("inbound"),
        pl.col("primary_purpose").alias("tour_purpose"),
        pl.col("orig_purpose"),
        pl.col("purpose").alias("dest_purpose"),
        pl.col("origin").alias("orig_taz"),
        pl.lit(0).cast(pl.Int32).alias("orig_walk_segment"),  # not modeled in ActivitySim
        pl.col("destination").alias("dest_taz"),
        pl.lit(0).cast(pl.Int32).alias("dest_walk_segment"),  # not modeled in ActivitySim
        pl.col("depart").alias("depart_hour"),
        pl.col("trip_mode"),
        pl.col("tour_mode"),
        pl.col("tour_category"),
        pl.lit(0).cast(pl.Int32).alias("avAvailable"),  # AV not in scope
        pl.col("sample_rate").alias("sampleRate"),
        pl.lit(0.0).cast(pl.Float64).alias("taxiWait"),  # TNC not in scope
        pl.lit(0.0).cast(pl.Float64).alias("singleTNCWait"),  # TNC not in scope
        pl.lit(0.0).cast(pl.Float64).alias("sharedTNCWait"),  # TNC not in scope
    ]

    # -----------------------------------------------------------------
    # indivTripData
    # -----------------------------------------------------------------
    indiv_trips = trip.filter(pl.col("tour_category") != "joint")
    indiv_trip_data = indiv_trips.select(*_TRIP_COLS)
    indiv_trip_data.write_csv(main / f"indivTripData_{iter_label}.csv")
    log.info("  Wrote indivTripData_%s.csv (%d rows)", iter_label, len(indiv_trip_data))

    # -----------------------------------------------------------------
    # jointTripData — no person_id/person_num, add num_participants
    # -----------------------------------------------------------------
    joint_trips = trip.filter(pl.col("tour_category") == "joint")
    joint_trip_data = joint_trips.select(
        pl.col("household_id").alias("hh_id"),
        pl.col("tour_id"),
        pl.col("stop_id"),
        pl.col("inbound"),
        pl.col("primary_purpose").alias("tour_purpose"),
        pl.col("orig_purpose"),
        pl.col("purpose").alias("dest_purpose"),
        pl.col("origin").alias("orig_taz"),
        pl.lit(0).cast(pl.Int32).alias("orig_walk_segment"),  # not modeled in ActivitySim
        pl.col("destination").alias("dest_taz"),
        pl.lit(0).cast(pl.Int32).alias("dest_walk_segment"),  # not modeled in ActivitySim
        pl.col("depart").alias("depart_hour"),
        pl.col("trip_mode"),
        pl.col("number_of_participants").alias("num_participants"),
        pl.col("tour_mode"),
        pl.col("tour_category"),
        pl.lit(0).cast(pl.Int32).alias("avAvailable"),  # AV not in scope
        pl.col("sample_rate").alias("sampleRate"),
        pl.lit(0.0).cast(pl.Float64).alias("taxiWait"),  # TNC not in scope
        pl.lit(0.0).cast(pl.Float64).alias("singleTNCWait"),  # TNC not in scope
        pl.lit(0.0).cast(pl.Float64).alias("sharedTNCWait"),  # TNC not in scope
    )
    joint_trip_data.write_csv(main / f"jointTripData_{iter_label}.csv")
    log.info("  Wrote jointTripData_%s.csv (%d rows)", iter_label, len(joint_trip_data))

    # -----------------------------------------------------------------
    # wsLocResults — workers only
    # -----------------------------------------------------------------
    workers = per.filter(pl.col("workplace_zone_id") > 0)
    ws = workers.join(hh.select("household_id", "income", "home_zone_id"),
                      on="household_id", how="left", suffix="_hh")
    ws_data = ws.select(
        pl.col("household_id").alias("HHID"),
        pl.col("person_id").alias("PersonID"),
        pl.col("person_num").alias("PersonNum"),
        pl.col("home_zone_id").alias("HomeTAZ"),
        pl.lit(0).cast(pl.Int32).alias("HomeSubZone"),  # TODO: derive from walkAccessBuffers
        pl.col("income").alias("Income"),
        pl.col("workplace_zone_id").alias("WorkLocation"),
        pl.lit(0).cast(pl.Int32).alias("WorkSubZone"),  # TODO: derive from walkAccessBuffers
    )
    ws_data.write_csv(main / f"wsLocResults_{iter_label}.csv")
    log.info("  Wrote wsLocResults_%s.csv (%d rows)", iter_label, len(ws_data))
