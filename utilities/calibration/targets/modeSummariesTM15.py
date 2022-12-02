import numpy as np
import pandas as pd

pd.set_option("display.width", 300)


"""
TRIP MODE CHOICE SUMMARIES
"""

infile = r"E:\projects\clients\mtc\data\CHTS_Summaries\tripModeChoice_TM15.csv"
TRIPMODE_TM15 = pd.read_csv(infile)
TRIPMODE_TM15["uno"] = 1

trip_modes = {
    1: "01_Walk",
    2: "02_Bike/Moped",
    3: "03_Drive Alone",
    4: "04_Shared Ride 2",
    5: "05_Shared Ride 3+",
    6: "06_Walk-Local",
    7: "07_Walk-Light Rail",
    8: "08_Walk-Ferry",
    9: "09_Walk-Express Bus",
    10: "10_Walk-Heavy Rail",
    11: "11_Walk-Commuter Rail",
    12: "12_Drive-Local",
    13: "13_Drive-Light Rail",
    14: "14_Drive-Ferry",
    15: "15_Drive-Express Bus",
    16: "16_Drive-Heavy Rail",
    17: "17_Drive-Commuter Rail",
    18: "18_School Bus",
    19: "19_Taxi/Shuttle",
    20: "20_Other",
}

tour_modes = {
    1: "01_Walk",
    2: "02_Bike/Moped",
    3: "03_Drive Alone",
    4: "04_Shared Ride 2",
    5: "05_Shared Ride 3+",
    6: "06_Walk-Local",
    7: "07_Walk-Light Rail",
    8: "08_Walk-Ferry",
    9: "09_Walk-Express Bus",
    10: "10_Walk-Heavy Rail",
    11: "11_Walk-Commuter Rail",
    12: "12_Drive-Local",
    13: "13_Drive-Light Rail",
    14: "14_Drive-Ferry",
    15: "15_Drive-Express Bus",
    16: "16_Drive-Heavy Rail",
    17: "17_Drive-Commuter Rail",
    18: "18_School Bus",
    19: "19_Taxi/Shuttle",
    20: "20_Other",
}

TRIPMODE_TM15["TRIPMODE_TM15"] = TRIPMODE_TM15["TRIPMODE_TM15"].astype("category")
TRIPMODE_TM15["TRIPMODE_TM15"] = TRIPMODE_TM15["TRIPMODE_TM15"].cat.set_categories(
    trip_modes.values()
)

TRIPMODE_TM15["TOURMODE_TM15"] = TRIPMODE_TM15["TOURMODE_TM15"].astype("category")
TRIPMODE_TM15["TOURMODE_TM15"] = TRIPMODE_TM15["TOURMODE_TM15"].cat.set_categories(
    tour_modes.values()
)

# Filtering out irrelevant tour purposes
TRIPMODE_TM15 = TRIPMODE_TM15.loc[
    (~TRIPMODE_TM15["TOURPURP_RECODE"].isin(["Other", "Change Mode", "Loop"]))
    & (TRIPMODE_TM15["finalweight"] != 0),
    :,
]

# Create market segments
workTrip = TRIPMODE_TM15.loc[
    (
        TRIPMODE_TM15["TOURPURP_RECODE"].isin(["Work"]) & TRIPMODE_TM15["finalweight"]
        != 0
    ),
    :,
]
univTrip = TRIPMODE_TM15.loc[
    (
        TRIPMODE_TM15["TOURPURP_RECODE"].isin(["University"])
        & TRIPMODE_TM15["finalweight"]
        != 0
    ),
    :,
]
schlTrip = TRIPMODE_TM15.loc[
    (
        TRIPMODE_TM15["TOURPURP_RECODE"].isin(["School"]) & TRIPMODE_TM15["finalweight"]
        != 0
    ),
    :,
]
indMTrip = TRIPMODE_TM15.loc[
    (
        TRIPMODE_TM15["TOURPURP_RECODE"].isin(["Indi-Main"])
        & TRIPMODE_TM15["finalweight"]
        != 0
    ),
    :,
]
indDTrip = TRIPMODE_TM15.loc[
    (
        TRIPMODE_TM15["TOURPURP_RECODE"].isin(["Indi-Disc"])
        & TRIPMODE_TM15["finalweight"]
        != 0
    ),
    :,
]
jntMTrip = TRIPMODE_TM15.loc[
    (
        TRIPMODE_TM15["TOURPURP_RECODE"].isin(["Joint-Main"])
        & TRIPMODE_TM15["finalweight"]
        != 0
    ),
    :,
]
jntDTrip = TRIPMODE_TM15.loc[
    (
        TRIPMODE_TM15["TOURPURP_RECODE"].isin(["Joint-Disc"])
        & TRIPMODE_TM15["finalweight"]
        != 0
    ),
    :,
]
atWrTrip = TRIPMODE_TM15.loc[
    (
        TRIPMODE_TM15["TOURPURP_RECODE"].isin(["At-Work"])
        & TRIPMODE_TM15["finalweight"]
        != 0
    ),
    :,
]

# Tabulate results [weighted]
allp_trip_summary = pd.pivot_table(
    TRIPMODE_TM15,
    values="finalweight",
    index="TRIPMODE_TM15",
    columns=["TOURMODE_TM15"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
work_trip_summary = pd.pivot_table(
    workTrip,
    values="finalweight",
    index="TRIPMODE_TM15",
    columns=["TOURMODE_TM15"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
univ_trip_summary = pd.pivot_table(
    univTrip,
    values="finalweight",
    index="TRIPMODE_TM15",
    columns=["TOURMODE_TM15"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
schl_trip_summary = pd.pivot_table(
    schlTrip,
    values="finalweight",
    index="TRIPMODE_TM15",
    columns=["TOURMODE_TM15"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
indM_trip_summary = pd.pivot_table(
    indMTrip,
    values="finalweight",
    index="TRIPMODE_TM15",
    columns=["TOURMODE_TM15"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
indD_trip_summary = pd.pivot_table(
    indDTrip,
    values="finalweight",
    index="TRIPMODE_TM15",
    columns=["TOURMODE_TM15"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
jntM_trip_summary = pd.pivot_table(
    jntMTrip,
    values="finalweight",
    index="TRIPMODE_TM15",
    columns=["TOURMODE_TM15"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
jntD_trip_summary = pd.pivot_table(
    jntDTrip,
    values="finalweight",
    index="TRIPMODE_TM15",
    columns=["TOURMODE_TM15"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
atWr_trip_summary = pd.pivot_table(
    atWrTrip,
    values="finalweight",
    index="TRIPMODE_TM15",
    columns=["TOURMODE_TM15"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)

allp_trip_summary["PURPOSE"] = "TOTAL"
work_trip_summary["PURPOSE"] = "WORK"
univ_trip_summary["PURPOSE"] = "UNIVERSITY"
schl_trip_summary["PURPOSE"] = "SCHOOL"
indM_trip_summary["PURPOSE"] = "INDIVIDUAL MAINTENANCE"
indD_trip_summary["PURPOSE"] = "INDIVIDUAL DISCRETIONARY"
jntM_trip_summary["PURPOSE"] = "JOINT MAINTENANCE"
jntD_trip_summary["PURPOSE"] = "JOINT DISCRETIONARY"
atWr_trip_summary["PURPOSE"] = "AT-WORK"

pd.concat(
    [
        work_trip_summary,
        univ_trip_summary,
        schl_trip_summary,
        indM_trip_summary,
        indD_trip_summary,
        jntM_trip_summary,
        jntD_trip_summary,
        atWr_trip_summary,
        allp_trip_summary,
    ],
    sort=True,
).to_csv("tripModeSummary_TM15.csv")

# Tabulate results [unweighted]
allp_trip_summary = pd.pivot_table(
    TRIPMODE_TM15,
    values="uno",
    index="TRIPMODE_TM15",
    columns=["TOURMODE_TM15"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
work_trip_summary = pd.pivot_table(
    workTrip,
    values="uno",
    index="TRIPMODE_TM15",
    columns=["TOURMODE_TM15"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
univ_trip_summary = pd.pivot_table(
    univTrip,
    values="uno",
    index="TRIPMODE_TM15",
    columns=["TOURMODE_TM15"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
schl_trip_summary = pd.pivot_table(
    schlTrip,
    values="uno",
    index="TRIPMODE_TM15",
    columns=["TOURMODE_TM15"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
indM_trip_summary = pd.pivot_table(
    indMTrip,
    values="uno",
    index="TRIPMODE_TM15",
    columns=["TOURMODE_TM15"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
indD_trip_summary = pd.pivot_table(
    indDTrip,
    values="uno",
    index="TRIPMODE_TM15",
    columns=["TOURMODE_TM15"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
jntM_trip_summary = pd.pivot_table(
    jntMTrip,
    values="uno",
    index="TRIPMODE_TM15",
    columns=["TOURMODE_TM15"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
jntD_trip_summary = pd.pivot_table(
    jntDTrip,
    values="uno",
    index="TRIPMODE_TM15",
    columns=["TOURMODE_TM15"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
atWr_trip_summary = pd.pivot_table(
    atWrTrip,
    values="uno",
    index="TRIPMODE_TM15",
    columns=["TOURMODE_TM15"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)

allp_trip_summary["PURPOSE"] = "TOTAL"
work_trip_summary["PURPOSE"] = "WORK"
univ_trip_summary["PURPOSE"] = "UNIVERSITY"
schl_trip_summary["PURPOSE"] = "SCHOOL"
indM_trip_summary["PURPOSE"] = "INDIVIDUAL MAINTENANCE"
indD_trip_summary["PURPOSE"] = "INDIVIDUAL DISCRETIONARY"
jntM_trip_summary["PURPOSE"] = "JOINT MAINTENANCE"
jntD_trip_summary["PURPOSE"] = "JOINT DISCRETIONARY"
atWr_trip_summary["PURPOSE"] = "AT-WORK"

pd.concat(
    [
        work_trip_summary,
        univ_trip_summary,
        schl_trip_summary,
        indM_trip_summary,
        indD_trip_summary,
        jntM_trip_summary,
        jntD_trip_summary,
        atWr_trip_summary,
        allp_trip_summary,
    ],
    sort=True,
).to_csv("tripModeSummaryUnweighted_TM15.csv")


"""
TOUR MODE CHOICE SUMMARIES
"""
infile = r"E:\projects\clients\mtc\data\CHTS_Summaries\tourModeChoice_TM15.csv"
TOURMODE_TM15 = pd.read_csv(infile)
TOURMODE_TM15["uno"] = 1

tour_modes = {
    1: "01_Walk",
    2: "02_Bike/Moped",
    3: "03_Drive Alone",
    4: "04_Shared Ride 2",
    5: "05_Shared Ride 3+",
    6: "06_Walk-Local",
    7: "07_Walk-Light Rail",
    8: "08_Walk-Ferry",
    9: "09_Walk-Express Bus",
    10: "10_Walk-Heavy Rail",
    11: "11_Walk-Commuter Rail",
    12: "12_Drive-Local",
    13: "13_Drive-Light Rail",
    14: "14_Drive-Ferry",
    15: "15_Drive-Express Bus",
    16: "16_Drive-Heavy Rail",
    17: "17_Drive-Commuter Rail",
    18: "18_School Bus",
    19: "19_Taxi/Shuttle",
    20: "20_Other",
}

TOURMODE_TM15["TOURMODE_TM15"] = TOURMODE_TM15["TOURMODE_TM15"].astype("category")
TOURMODE_TM15["TOURMODE_TM15"] = TOURMODE_TM15["TOURMODE_TM15"].cat.set_categories(
    tour_modes.values()
)

# Filtering out irrelevant tour purposes
TOURMODE_TM15 = TOURMODE_TM15.loc[
    (~TOURMODE_TM15["TOURPURP_RECODE"].isin(["Other", "Change Mode", "Loop"]))
    & (TOURMODE_TM15["finalweight"] != 0),
    :,
]

# Create market segments
workTour = TOURMODE_TM15.loc[
    (
        TOURMODE_TM15["TOURPURP_RECODE"].isin(["Work"]) & TOURMODE_TM15["finalweight"]
        != 0
    ),
    :,
]
univTour = TOURMODE_TM15.loc[
    (
        TOURMODE_TM15["TOURPURP_RECODE"].isin(["University"])
        & TOURMODE_TM15["finalweight"]
        != 0
    ),
    :,
]
schlTour = TOURMODE_TM15.loc[
    (
        TOURMODE_TM15["TOURPURP_RECODE"].isin(["School"]) & TOURMODE_TM15["finalweight"]
        != 0
    ),
    :,
]
indMTour = TOURMODE_TM15.loc[
    (
        TOURMODE_TM15["TOURPURP_RECODE"].isin(["Indi-Main"])
        & TOURMODE_TM15["finalweight"]
        != 0
    ),
    :,
]
indDTour = TOURMODE_TM15.loc[
    (
        TOURMODE_TM15["TOURPURP_RECODE"].isin(["Indi-Disc"])
        & TOURMODE_TM15["finalweight"]
        != 0
    ),
    :,
]
jntMTour = TOURMODE_TM15.loc[
    (
        TOURMODE_TM15["TOURPURP_RECODE"].isin(["Joint-Main"])
        & TOURMODE_TM15["finalweight"]
        != 0
    ),
    :,
]
jntDTour = TOURMODE_TM15.loc[
    (
        TOURMODE_TM15["TOURPURP_RECODE"].isin(["Joint-Disc"])
        & TOURMODE_TM15["finalweight"]
        != 0
    ),
    :,
]
atWrTour = TOURMODE_TM15.loc[
    (
        TOURMODE_TM15["TOURPURP_RECODE"].isin(["At-Work"])
        & TOURMODE_TM15["finalweight"]
        != 0
    ),
    :,
]

# Tabulate results [weighted]
allp_tour_summary = pd.pivot_table(
    TOURMODE_TM15,
    values="finalweight",
    index="TOURMODE_TM15",
    columns=["AUTOSUFF"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
work_tour_summary = pd.pivot_table(
    workTour,
    values="finalweight",
    index="TOURMODE_TM15",
    columns=["AUTOSUFF"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
univ_tour_summary = pd.pivot_table(
    univTour,
    values="finalweight",
    index="TOURMODE_TM15",
    columns=["AUTOSUFF"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
schl_tour_summary = pd.pivot_table(
    schlTour,
    values="finalweight",
    index="TOURMODE_TM15",
    columns=["AUTOSUFF"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
indM_tour_summary = pd.pivot_table(
    indMTour,
    values="finalweight",
    index="TOURMODE_TM15",
    columns=["AUTOSUFF"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
indD_tour_summary = pd.pivot_table(
    indDTour,
    values="finalweight",
    index="TOURMODE_TM15",
    columns=["AUTOSUFF"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
jntM_tour_summary = pd.pivot_table(
    jntMTour,
    values="finalweight",
    index="TOURMODE_TM15",
    columns=["AUTOSUFF"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
jntD_tour_summary = pd.pivot_table(
    jntDTour,
    values="finalweight",
    index="TOURMODE_TM15",
    columns=["AUTOSUFF"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
atWr_tour_summary = pd.pivot_table(
    atWrTour,
    values="finalweight",
    index="TOURMODE_TM15",
    columns=["AUTOSUFF"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)

allp_tour_summary["PURPOSE"] = "TOTAL"
work_tour_summary["PURPOSE"] = "WORK"
univ_tour_summary["PURPOSE"] = "UNIVERSITY"
schl_tour_summary["PURPOSE"] = "SCHOOL"
indM_tour_summary["PURPOSE"] = "INDIVIDUAL MAINTENANCE"
indD_tour_summary["PURPOSE"] = "INDIVIDUAL DISCRETIONARY"
jntM_tour_summary["PURPOSE"] = "JOINT MAINTENANCE"
jntD_tour_summary["PURPOSE"] = "JOINT DISCRETIONARY"
atWr_tour_summary["PURPOSE"] = "AT-WORK"

pd.concat(
    [
        work_tour_summary,
        univ_tour_summary,
        schl_tour_summary,
        indM_tour_summary,
        indD_tour_summary,
        jntM_tour_summary,
        jntD_tour_summary,
        atWr_tour_summary,
        allp_tour_summary,
    ],
    sort=True,
).to_csv("tourModeummary_TM15.csv")

# Tabulate results [unweighted]
allp_tour_summary = pd.pivot_table(
    TOURMODE_TM15,
    values="uno",
    index="TOURMODE_TM15",
    columns=["AUTOSUFF"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
work_tour_summary = pd.pivot_table(
    workTour,
    values="uno",
    index="TOURMODE_TM15",
    columns=["AUTOSUFF"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
univ_tour_summary = pd.pivot_table(
    univTour,
    values="uno",
    index="TOURMODE_TM15",
    columns=["AUTOSUFF"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
schl_tour_summary = pd.pivot_table(
    schlTour,
    values="uno",
    index="TOURMODE_TM15",
    columns=["AUTOSUFF"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
indM_tour_summary = pd.pivot_table(
    indMTour,
    values="uno",
    index="TOURMODE_TM15",
    columns=["AUTOSUFF"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
indD_tour_summary = pd.pivot_table(
    indDTour,
    values="uno",
    index="TOURMODE_TM15",
    columns=["AUTOSUFF"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
jntM_tour_summary = pd.pivot_table(
    jntMTour,
    values="uno",
    index="TOURMODE_TM15",
    columns=["AUTOSUFF"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
jntD_tour_summary = pd.pivot_table(
    jntDTour,
    values="uno",
    index="TOURMODE_TM15",
    columns=["AUTOSUFF"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)
atWr_tour_summary = pd.pivot_table(
    atWrTour,
    values="uno",
    index="TOURMODE_TM15",
    columns=["AUTOSUFF"],
    dropna=False,
    margins=True,
    aggfunc=np.sum,
).fillna(0)

allp_tour_summary["PURPOSE"] = "TOTAL"
work_tour_summary["PURPOSE"] = "WORK"
univ_tour_summary["PURPOSE"] = "UNIVERSITY"
schl_tour_summary["PURPOSE"] = "SCHOOL"
indM_tour_summary["PURPOSE"] = "INDIVIDUAL MAINTENANCE"
indD_tour_summary["PURPOSE"] = "INDIVIDUAL DISCRETIONARY"
jntM_tour_summary["PURPOSE"] = "JOINT MAINTENANCE"
jntD_tour_summary["PURPOSE"] = "JOINT DISCRETIONARY"
atWr_tour_summary["PURPOSE"] = "AT-WORK"

pd.concat(
    [
        work_tour_summary,
        univ_tour_summary,
        schl_tour_summary,
        indM_tour_summary,
        indD_tour_summary,
        jntM_tour_summary,
        jntD_tour_summary,
        atWr_tour_summary,
        allp_tour_summary,
    ],
    sort=True,
).to_csv("tourModeSummaryUnweighted_TM15.csv")
