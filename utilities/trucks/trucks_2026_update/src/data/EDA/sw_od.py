import pandas as pd
import numpy as np
import h5py
import openmatrix as omx

def read_sw_trips(path, mtc_mask) -> pd.DataFrame:
    
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
    
    # MTC Map:
    # Make sure to only include TAZs and TLN in the MTC region 
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