from src.data.observed.schema import validate_observed_schema

def standardize_observed_aadtt(aadtt, crosswalk):
    df = aadtt.merge(crosswalk[["control_station_id", "link_id"]], on="control_station_id", how="right") 
    df["type"] = "observed"
    df["source"] = "caltrans_2018"
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