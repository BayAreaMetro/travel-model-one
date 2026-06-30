from src.data.observed.schema import validate_observed_schema

def standardize_observed_aadtt(aadtt, crosswalk):
    truck_type_2_map = {"ctruck": "HV", "struck": "SM", "mtruck": "SM", "vstruck": "SM"}
    df = aadtt.merge(crosswalk[["control_station_id", "link_id"]], on="control_station_id", how="right") 
    df["type"] = "observed"
    df["source"] = "caltrans_2018"
    df["mean"] = df["mean"].round(0).astype("int")
    df["vehicle_type_2"] = df["vehicle_type"].map(truck_type_2_map)
    cols = {
        "control_station_id": "count_location_id",
        "link_id": "link_id",
        "TOD": "tod",
        "vehicle_type": "truck_type_1",
        "vehicle_type_2": "truck_type_2",
        "type": "type",
        "source": "source",
        "quality_flag": "quality_flag",
        "mean": "volume"
    }
    df = df.rename(columns=cols)[list(cols.values())]
    return validate_observed_schema(df)