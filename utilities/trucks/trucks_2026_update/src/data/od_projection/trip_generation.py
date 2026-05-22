import pandas as pd
import numpy as np

def prepare_trip_generation_data(matrixes_names, source_matrices, index_range=(1, 1454), index_col_name="TAZ1454") -> pd.DataFrame:
    """
    Prepares the data for trip generation by merging the projected matrices with land use data.

    Parameters:
    matrixes_names (list): A list of matrix names to process.
    source_matrices (dict): A dictionary containing the source matrices.

    Returns:
    pd.DataFrame: A DataFrame ready for trip generation modeling.
    """
    lower, upper = index_range
    trip_generation = pd.DataFrame()
    trip_generation[index_col_name] = range(lower, upper + 1)
   

    # Compute productions and attractions
    for matrix_name in matrixes_names:
        matrix = np.array(source_matrices[matrix_name][:], dtype=np.float32)
        trip_generation[f"{matrix_name}_production"] = matrix.sum(axis=1)[lower - 1:upper]
        trip_generation[f"{matrix_name}_attraction"] = matrix.sum(axis=0)[lower - 1:upper]

    return trip_generation
    
def internal_gates_generation(matrixes_names, source_matrices, crosswalk) -> pd.DataFrame:
    """
    Compute productions/attractions from OMX matrices for internal gate only. 
    Filter out zero-trip rows.
    """
    sw_tnl_map = {
        2655: "PORT OF SAN FRANCISCO",
        2658: "PORT OF OAKLAND", 
        2656: "PORT OF REDWOOD CITY", 
        6987: "SFO AIRPORT",
        6988: "OAK AIRPORT",
        }

    # Trip generation table
    trip_generation = pd.DataFrame(index=range(1, 7001))

    # Internal gates
    internal_gates = (
        crosswalk[crosswalk.type == "internal_gate"]
        .drop_duplicates()
        .copy()
    )

    # Compute productions and attractions
    for matrix_name in matrixes_names:
        matrix = np.array(source_matrices[matrix_name][:], dtype=np.float32)
        trip_generation[f"{matrix_name}_production"] = matrix.sum(axis=1)
        trip_generation[f"{matrix_name}_attraction"] = matrix.sum(axis=0)

    # Merge using correct mapping fields
    df = internal_gates[["from_zone_id", "to_zone_id"]].merge(
        trip_generation,
        how="left",
        left_on="from_zone_id",
        right_index=True
    )

    # Rename columns
    df = df.rename(columns={
        "from_zone_id": "CSF2TDM_node_id",
        "to_zone_id": "TAZ1454"
    })

    # Filter out zero-trip rows (across all prod/attr columns)
    trip_cols = [col for col in df.columns if col not in ["CSF2TDM_node_id", "TAZ1454"]]
    df = df[df[trip_cols].sum(axis=1) > 0]

    df["zone_name"] = df["CSF2TDM_node_id"].map(sw_tnl_map).fillna("INTERNAL GATE")
    return df