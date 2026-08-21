import pandas as pd
import numpy as np
import openmatrix as omx

def get_od_marginals(
        matrixes_names: list[str], 
        source_matrices: omx.File, 
        index_range: tuple[int, int]=(1, 1454), 
        index_col_name: str ="TAZ1454"
        ) -> pd.DataFrame:
    """ Calculate production and attraction marginals from square O-D matrices.

    This function extracts specified O-D matrix from a OMX file object. 
    These cores must be square 2D matrices where both rows and columns 
    represent the exact same spatial zone system. 

    The function slices a subset of the zone system defined by `index_range`. 
    It then calculates the marginal totals across this subset: summing along 
    rows to compute trip productions (origins), and summing down columns to 
    compute trip attractions (destinations).

    Parameters
    ----------
    matrixes_names : list of str
        A list of matrix keys/names to process from `source_matrices`.
    source_matrices : dict of {str : array_like}
        A dictionary where keys match `matrixes_names` and values are 2D
        array-like objects (e.g., h5py datasets, numpy arrays) containing
        travel demand or trip data.
    index_range : tuple of int, default (1, 1454)
        A tuple defining the (lower, upper) inclusive bounds of the zone IDs
        using 1-based indexing.
    index_col_name : str, default "TAZ1454"
        The column name to use for the zone IDs in the returned DataFrame.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the zone ID column, followed by pairs of
        `{matrix_name}_production` and `{matrix_name}_attraction` columns for
        each processed matrix.
    """
    lower, upper = index_range
    marginals_df = pd.DataFrame()
    marginals_df[index_col_name] = range(lower, upper + 1)
   
    for matrix_name in matrixes_names:
        matrix = np.array(source_matrices[matrix_name][:], dtype=np.float32)
        marginals_df[f"{matrix_name}_production"] = matrix[lower -1 :upper, :upper].sum(axis=1)
        marginals_df[f"{matrix_name}_attraction"] = matrix[:upper, lower -1 :upper].sum(axis=0)

    return marginals_df

    
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
        6986: "SJC AIRPORT",
        2659: "PORT OF RICHMOND"
        }

    trip_generation = pd.DataFrame(index=range(1, 7001))

    internal_gates = (
        crosswalk[crosswalk.type == "internal_gate"]
        .drop_duplicates()
        .copy()
    )

    for matrix_name in matrixes_names:
        matrix = np.array(source_matrices[matrix_name][:], dtype=np.float32)
        trip_generation[f"{matrix_name}_production"] = matrix.sum(axis=1)
        trip_generation[f"{matrix_name}_attraction"] = matrix.sum(axis=0)

    df = internal_gates[["from_zone_id", "to_zone_id"]].merge(
        trip_generation,
        how="left",
        left_on="from_zone_id",
        right_index=True
    )

    df = df.rename(columns={
        "from_zone_id": "CSF2TDM_node_id",
        "to_zone_id": "TAZ1454"
    })

    # Filter out zero-trip rows (across all prod/attr columns)
    trip_cols = [col for col in df.columns if col not in ["CSF2TDM_node_id", "TAZ1454"]]
    df = df[df[trip_cols].sum(axis=1) > 0]

    df["zone_name"] = df["CSF2TDM_node_id"].map(sw_tnl_map).fillna("INTERNAL GATE")
    return df