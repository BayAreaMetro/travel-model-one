USAGE = """

This script is to be run after HPMS_to_TM_SpatialJoin.py
It matches AADT measurements in the HPMS shapefile to the links in the Travel Model network and calculate %RMSE.

"""
import os
import arcpy
import pandas as pd
from simpledbf import Dbf5
import numpy as np

arcpy.env.workspace = r"M:\Data\Traffic\HPMS\2015\Test17"

# Separate the free flow network into 16 pieces ( [N, E, S, W] x [use = 1, 2, 3, 4])
# e.g. arcpy.conversion.FeatureClassToFeatureClass(INPUT_TM1shapefile, "", "freeflow_links_freeway_N_Use1.shp", "USE = 1 And ROUTEDIR = 'N'")
# note: only freeway routes are coded with direction in the TM1 network; there are 49 freeway routes in TM1

direction_list = ["N", "E", "S", "W"]
use_list = ["1", "2", "3", "4"]

# -------------------------------
# switch to dbf processing (not arcpy)
# -------------------------------
# e.g.
# dbf_Fwy = Dbf5('HPMS_to_TM_N_Use1.dbf')
# x[N1] = dbf_Fwy.to_dataframe()

# use dictionary
x = {}

for d in direction_list:
    for u in use_list:
        dbf_Fwy = Dbf5(arcpy.env.workspace + "\HPMS_to_TM_" + d + "_Use" + u + ".dbf")
        x[d + u] = dbf_Fwy.to_dataframe()


# Union N+E and S+W (so, one file contains freeway segments going either north or east; and one file contains freeway segments going either South or West)
# this reduces the number of dataframes
# the goal is to be able to sum up the volume of N+S and E+W by joining the objectID in later steps
df_FwyNorthEast1 = x["N1"].append(x["E1"])
df_FwySouthWest1 = x["S1"].append(x["W1"])

df_FwyNorthEast2 = x["N2"].append(x["E2"])
df_FwySouthWest2 = x["S2"].append(x["W2"])

df_FwyNorthEast3 = x["N3"].append(x["E3"])
df_FwySouthWest3 = x["S3"].append(x["W3"])

df_FwyNorthEast4 = x["N4"].append(x["E4"])
df_FwySouthWest4 = x["S4"].append(x["W4"])

# add suffix
df_FwyNorthEast1 = df_FwyNorthEast1.add_suffix("_NE1")
df_FwySouthWest1 = df_FwySouthWest1.add_suffix("_SW1")

df_FwyNorthEast2 = df_FwyNorthEast2.add_suffix("_NE2")
df_FwySouthWest2 = df_FwySouthWest2.add_suffix("_SW2")

df_FwyNorthEast3 = df_FwyNorthEast3.add_suffix("_NE3")
df_FwySouthWest3 = df_FwySouthWest3.add_suffix("_SW3")

df_FwyNorthEast4 = df_FwyNorthEast4.add_suffix("_NE4")
df_FwySouthWest4 = df_FwySouthWest4.add_suffix("_SW4")


# for use = 1
# inner join because we only want the freeway segments where we get volumes for both directions
df_FwyBiDirection = pd.merge(
    df_FwyNorthEast1,
    df_FwySouthWest1,
    left_on="OBJECTID_NE1",
    right_on="OBJECTID_SW1",
    how="inner",
)
# keep only the relevant columns
# df_FwyBiDirection = df_FwyBiDirection[['OBJECTID', 'route_numb_NE1', 'route_numb_SW1', 'aadt_NE1', 'aadt_SW1', 'A_NE1', 'B_NE1', 'A_SW1', 'B_SW1']]

# left join the other tables
df_FwyBiDirection = pd.merge(
    df_FwyBiDirection,
    df_FwyNorthEast2,
    left_on="OBJECTID_NE1",
    right_on="OBJECTID_NE2",
    how="left",
)
df_FwyBiDirection = pd.merge(
    df_FwyBiDirection,
    df_FwySouthWest2,
    left_on="OBJECTID_NE1",
    right_on="OBJECTID_SW2",
    how="left",
)
df_FwyBiDirection = pd.merge(
    df_FwyBiDirection,
    df_FwyNorthEast3,
    left_on="OBJECTID_NE1",
    right_on="OBJECTID_NE3",
    how="left",
)
df_FwyBiDirection = pd.merge(
    df_FwyBiDirection,
    df_FwySouthWest3,
    left_on="OBJECTID_NE1",
    right_on="OBJECTID_SW3",
    how="left",
)
df_FwyBiDirection = pd.merge(
    df_FwyBiDirection,
    df_FwyNorthEast4,
    left_on="OBJECTID_NE1",
    right_on="OBJECTID_NE4",
    how="left",
)
df_FwyBiDirection = pd.merge(
    df_FwyBiDirection,
    df_FwySouthWest4,
    left_on="OBJECTID_NE1",
    right_on="OBJECTID_SW4",
    how="left",
)

# rename the aadt column for clarity
df_FwyBiDirection.rename(
    columns={"aadt_NE1": "aadt", "route_numb_NE1": "route_numb"}, inplace=True
)

# keep only the relevant columns
df_FwyBiDirection = df_FwyBiDirection[
    [
        "OBJECTID_NE1",
        "route_numb",
        "route_numb_SW1",
        "aadt",
        "A_NE1",
        "B_NE1",
        "A_SW1",
        "B_SW1",
        "A_NE2",
        "B_NE2",
        "A_SW2",
        "B_SW2",
        "A_NE3",
        "B_NE3",
        "A_SW3",
        "B_SW3",
        "A_NE4",
        "B_NE4",
        "A_SW4",
        "B_SW4",
    ]
]


output_filename = arcpy.env.workspace + "\HPMS_to_TM.csv"
df_FwyBiDirection.to_csv(output_filename, header=True, index=False)

# left join to avgload5period.csv
df_avgload5period = pd.read_csv(
    os.path.join(arcpy.env.workspace, "avgload5period.csv"), index_col=False, sep=","
)
df_avgload5period["vol5period"] = (
    df_avgload5period["   volEA_tot"]
    + df_avgload5period["   volAM_tot"]
    + df_avgload5period["   volMD_tot"]
    + df_avgload5period["   volPM_tot"]
    + df_avgload5period["   volEV_tot"]
)
df_FwyBiDirection = pd.merge(
    df_FwyBiDirection,
    df_avgload5period[["       a", "       b", "vol5period"]],
    left_on=["A_NE1", "B_NE1"],
    right_on=["       a", "       b"],
    how="left",
    suffixes=("", "_TMne1"),
)
df_FwyBiDirection = pd.merge(
    df_FwyBiDirection,
    df_avgload5period[["       a", "       b", "vol5period"]],
    left_on=["A_SW1", "B_SW1"],
    right_on=["       a", "       b"],
    how="left",
    suffixes=("", "_TMsw1"),
)
df_FwyBiDirection = pd.merge(
    df_FwyBiDirection,
    df_avgload5period[["       a", "       b", "vol5period"]],
    left_on=["A_NE2", "B_NE2"],
    right_on=["       a", "       b"],
    how="left",
    suffixes=("", "_TMne2"),
)
df_FwyBiDirection = pd.merge(
    df_FwyBiDirection,
    df_avgload5period[["       a", "       b", "vol5period"]],
    left_on=["A_SW2", "B_SW2"],
    right_on=["       a", "       b"],
    how="left",
    suffixes=("", "_TMsw2"),
)
df_FwyBiDirection = pd.merge(
    df_FwyBiDirection,
    df_avgload5period[["       a", "       b", "vol5period"]],
    left_on=["A_NE3", "B_NE3"],
    right_on=["       a", "       b"],
    how="left",
    suffixes=("", "_TMne3"),
)
df_FwyBiDirection = pd.merge(
    df_FwyBiDirection,
    df_avgload5period[["       a", "       b", "vol5period"]],
    left_on=["A_SW3", "B_SW3"],
    right_on=["       a", "       b"],
    how="left",
    suffixes=("", "_TMsw3"),
)
df_FwyBiDirection = pd.merge(
    df_FwyBiDirection,
    df_avgload5period[["       a", "       b", "vol5period"]],
    left_on=["A_NE4", "B_NE4"],
    right_on=["       a", "       b"],
    how="left",
    suffixes=("", "_TMne4"),
)
df_FwyBiDirection = pd.merge(
    df_FwyBiDirection,
    df_avgload5period[["       a", "       b", "vol5period"]],
    left_on=["A_SW4", "B_SW4"],
    right_on=["       a", "       b"],
    how="left",
    suffixes=("", "_TMsw4"),
)
# force the '_TMne1' suffix
df_FwyBiDirection.rename(
    columns={
        "       a": "       a_TMne1",
        "       b": "       b_TMne1",
        "vol5period": "vol5period_TMne1",
    },
    inplace=True,
)

# sum the volume
df_FwyBiDirection.fillna(0, inplace=True)
df_FwyBiDirection["modelled_daily_volume"] = (
    df_FwyBiDirection["vol5period_TMne1"]
    + df_FwyBiDirection["vol5period_TMsw1"]
    + df_FwyBiDirection["vol5period_TMne2"]
    + df_FwyBiDirection["vol5period_TMsw2"]
    + df_FwyBiDirection["vol5period_TMne3"]
    + df_FwyBiDirection["vol5period_TMsw3"]
    + df_FwyBiDirection["vol5period_TMne4"]
    + df_FwyBiDirection["vol5period_TMsw4"]
)

output_filename2 = arcpy.env.workspace + "\HPMS_to_TM_avgload5period_multistations.csv"
df_FwyBiDirection.to_csv(output_filename2, header=True, index=False)

# if there is more than one station matched to any given link, take average
df_FwyBiDirection_GroupedbyAB = df_FwyBiDirection.groupby(
    ["A_NE1", "B_NE1"], as_index=False
).mean()

output_filename3 = arcpy.env.workspace + "\HPMS_to_TM_avgload5period.csv"
df_FwyBiDirection_GroupedbyAB.to_csv(output_filename3, header=True, index=False)

df_FwyBiDirection_GroupedbyAB["HPMS_Weekday_Vol"] = (
    df_FwyBiDirection_GroupedbyAB["aadt"] * 1.1
)
df_FwyBiDirection_GroupedbyAB["Count_minus_Modelled"] = (
    df_FwyBiDirection_GroupedbyAB["modelled_daily_volume"]
    - df_FwyBiDirection_GroupedbyAB["HPMS_Weekday_Vol"]
)
df_FwyBiDirection_GroupedbyAB["Count_minus_Modelled_Squared"] = (
    df_FwyBiDirection_GroupedbyAB["Count_minus_Modelled"]
    * df_FwyBiDirection_GroupedbyAB["Count_minus_Modelled"]
)

# calculate %RMSE by route
df_FwyBiDirection_GroupedbyRoute = df_FwyBiDirection_GroupedbyAB.groupby(
    "route_numb"
).agg(
    {
        "route_numb": ["first", "count"],
        "Count_minus_Modelled_Squared": ["sum"],
        "HPMS_Weekday_Vol": ["sum"],
    }
)
df_FwyBiDirection_GroupedbyRoute.columns = [
    "route_numb",
    "N_counters_matched",
    "Sum_Count_minus_Modelled_Squared",
    "Sum_HPMS_Weekday_Vol",
]
df_FwyBiDirection_GroupedbyRoute["RMSE"] = np.sqrt(
    df_FwyBiDirection_GroupedbyRoute["Sum_Count_minus_Modelled_Squared"]
    / df_FwyBiDirection_GroupedbyRoute["N_counters_matched"]
)
df_FwyBiDirection_GroupedbyRoute["Percent_RMSE"] = df_FwyBiDirection_GroupedbyRoute[
    "RMSE"
] / (
    df_FwyBiDirection_GroupedbyRoute["Sum_HPMS_Weekday_Vol"]
    / df_FwyBiDirection_GroupedbyRoute["N_counters_matched"]
)

output_filename4 = arcpy.env.workspace + "\Percent_RMSE_by_Route.csv"
df_FwyBiDirection_GroupedbyRoute.to_csv(output_filename4, header=True, index=False)
