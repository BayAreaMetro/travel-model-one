import pandas as pd
import numpy as np
import h5py
import openmatrix as omx

def read_sw_trips(path, mtc_mask) -> pd.DataFrame:
    """Read CSF2TDM (statewide or SW model) truck OD trip matrices from OMX, 
    filtered to the MTC region.

    Applies a boolean mask to extract only the rows and columns corresponding
    to MTC TAZs/TLNs from the full 7000×7000 CSF2TDM matrix and returns a
    long format DataFrame indexed by origin-destination pair.

    Parameters
    ----------
    path : str
        File path to the statewide OD OMX file.
    mtc_mask : np.ndarray of bool, shape (7000,)
        Boolean mask where ``True`` marks positions (0-based) of MTC TAZs
        and TLN zones in the full statewide matrix.

    Returns
    -------
    pd.DataFrame
        Long-format DataFrame with columns ``origin``, ``destination``
        (1-based zone IDs), and one column per truck-type matrix found in
        the OMX file. 
    """
    zone_ids = np.where(mtc_mask)[0] + 1
    trips = pd.DataFrame(
        index=pd.MultiIndex.from_product([zone_ids, zone_ids], names=['origin', 'destination'])
    ).reset_index()

    od_omx = omx.open_file(path, "r")
    for name in od_omx.list_matrices():
        matrix = np.array(od_omx[name])
        mtc_matrix = matrix[mtc_mask][:, mtc_mask]
        trips[name] = mtc_matrix.flatten()
    od_omx.close()
    return trips

def read_sw_skims(path, mtc_idx) -> pd.DataFrame:
    """Read statewide highway skims from HDF5, filtered to MTC TAZ pairs.

    Reads the ``auto`` dataset in chunks from the CSF2TDM skims HDF5 file
    and keeps only records where both origin and destination belong to the
    set of MTC TAZ/TLN IDs.  Returns distance and time skim columns for
    truck classes.

    Parameters
    ----------
    path : str
        File path to the statewide skims HDF5 file (``skims.h5``).
    mtc_idx : np.ndarray of int
        1-based zone IDs for MTC TAZs and TLN locations, used to filter
        origin-destination pairs.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns ``origin``, ``destination``, and all skim
        columns whose names contain ``"TRUCK"``. 
    """
    store = h5py.File(path, 'r')
    filtered_chunks = []
    dset = store['auto']
    chunk_size = 1_000_000

    for i in range(0, len(dset), chunk_size):
        chunk = dset[i:i+chunk_size]

        mask = np.isin(chunk['origin'], mtc_idx) & np.isin(chunk['destination'], mtc_idx)
        filtered = chunk[mask]

        if len(filtered) > 0:
            filtered_chunks.append(filtered)

    filtered_data = np.concatenate(filtered_chunks)
    skims = pd.DataFrame(filtered_data)
    skims = skims[["origin", "destination"] + list(skims.columns[skims.columns.str.contains("TRUCK")])]
    store.close()
    return skims

def sw_od_long_format(input_paths: dict):
    """Build a long-format statewide OD table with truck trips, skims, and county labels.

    Reads the CSF2TDM trip OMX and highway skims HDF5, restricts both to
    MTC TAZs and TLN gateway zones, merges them, and derives aggregated
    truck-type columns, composite skims (1/3 AM + 2/3 Mid), and county
    name labels.

    Parameters
    ----------
    input_paths : dict
        Dictionary with the following keys:

        ``"od_omx"`` : str
            Path to the statewide trip OMX file.
        ``"skims"`` : str
            Path to the statewide skims HDF5 file.
        ``"taz_county"`` : str
            Path to the TAZ-to-MPO/county mapping CSV.
        ``"tln_indices"`` : dict
            Mapping of TLN zone ID (int) to location name (str) for
            ports and airports to include alongside TAZs.

    Returns
    -------
    pd.DataFrame
        One row per origin-destination zone pair with columns for raw trip
        matrices, skim values, and derived columns: ``origin_county``,
        ``destination_county``, ``total_trips``, ``light_trucks``,
        ``medium_trucks``, ``heavy_trucks``, ``dist_comp``, ``time_comp``,
        and ``source`` (``"CSF2TDM"``).
    """
    # MTC Map:
    # Makes sure to only include TAZs and TLN in the MTC region 
    # mtc_index: TAZ IDs in the MTC region (1-based)
    # mtc_mask: boolean mask for selecting MTC TAZs from the 7000x7000 matrix (0-based)
    # -------------------------
    taz_map = pd.read_csv(input_paths["taz_county"])

    # MTC Map: 
    mtc_tazs = taz_map[taz_map["MPO_Name"].isin(["MTC"])]

    # TAZ idx -> County
    taz_to_county = dict(zip(mtc_tazs["TAZ12"], mtc_tazs["CountyName"]))
    taz_to_county = {**taz_to_county, **input_paths["tln_indices"]}

    # Position of MTC TAZs in the CSF2TDM 7000 X 7000 OD Matrix
    mtc_idx = np.array(list(taz_to_county.keys()))
    mtc_mask = np.zeros(7000, dtype=bool)
    mtc_mask[mtc_idx - 1] = True # Offset for OMX matrix (0-based indexed) lookups
    
    # -------------------------------
    trips = read_sw_trips(input_paths["od_omx"], mtc_mask)
    skims = read_sw_skims(input_paths["skims"], mtc_idx)

    df = trips.merge(skims, how = "outer", on = ["origin", "destination"])
    df["origin_county"] = df["origin"].map(taz_to_county)
    df["destination_county"] = df["destination"].map(taz_to_county)
    df['total_trips'] = df.filter(regex=r'^(LT|MT1|MT2|HT)').sum(axis = 1)
    df["light_trucks"] = df.loc[:, df.columns.str.startswith("LT")].sum(axis=1)
    df["medium_trucks"] = df.loc[:, df.columns.str.startswith(("MT1", "MT2"))].sum(axis=1)
    df["heavy_trucks"] = df.loc[:, df.columns.str.startswith("HT")].sum(axis=1)
    df['dist_comp'] = ((1/3)*df['TRUCK_Dist_AM'] + (2/3)*df['TRUCK_Dist_Mid']).fillna(0)
    df['time_comp'] = ((1/3)*df['TRUCK_Time_AM'] + (2/3)*df['TRUCK_Time_Mid']).fillna(0)
    df["source"] = "CSF2TDM"
    return df