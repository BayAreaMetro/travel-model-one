from src.data.observed.schema import validate_observed_schema

def standardize_observed_aadtt(aadtt, crosswalk):
    """Reshape and rename BATA AADTT estimates into the shared observed schema.

    Merges estimated volumes with a plaza-to-link crosswalk, derives a
    secondary truck-type classification (``truck_type_2``, consistent with 
    the TM-1.6 assignment aggregation SM and HM), renames columns
    to the canonical names, and validates the result against the observed
    schema.

    Parameters
    ----------
    aadtt : pd.DataFrame
        Output of :func:`~src.data.observed.bata.aadtt.estimate_bata_aadtt`
        with columns ``Plaza``, ``TOD``, ``vehicle_type``, and
        ``mean_volume``.
    crosswalk : pd.DataFrame
        Station-to-link mapping with at least columns
        ``count_location_id`` (matched to ``Plaza``) and ``link_id``.

    Returns
    -------
    pd.DataFrame
        Validated observed dataset with columns ``count_location_id``,
        ``link_id``, ``tod``, ``truck_type_1``, ``truck_type_2``,
        ``type`` (``"observed"``), ``source`` (``"bata_2023"``),
        ``quality_flag``, and ``volume``.
    """
    # Second mapping to compare with TM outputs. 
    truck_type_2_map = {"ctruck": "HV", "struck": "SM", "mtruck": "SM", "vstruck": "SM"}
    
    df = aadtt.merge(crosswalk, left_on="Plaza", right_on="count_location_id", how="right") 
    df["type"] = "observed"
    df["source"] = "bata_2023"
    df["mean_volume"] = df["mean_volume"].round(0).astype("int")
    df["quality_flag"] = "none"
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
        "mean_volume": "volume"
    }
    df = df.rename(columns=cols)[list(cols.values())]
    return validate_observed_schema(df)