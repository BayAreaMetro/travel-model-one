from src.data.observed.schema import validate_observed_schema

def standardize_observed_aadtt(aadtt, crosswalk):
    df = aadtt.merge(crosswalk, left_on="Plaza", right_on="count_location_id", how="right") 
    df["type"] = "observed"
    df["source"] = "bata_2023"
    df["mean"] = df["mean"].round(0).astype("int")
    df["quality_flag"] = "none"
    cols = {
        "control_station_id": "count_location_id",
        "link_id": "link_id",
        "TOD": "tod",
        "vehicle_type": "truck_type",
        "type": "type",
        "source": "source",
        "quality_flag": "quality_flag",
        "mean": "value"
    }
    df = df.rename(columns=cols)[list(cols.values())]
    return validate_observed_schema(df)