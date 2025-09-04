USAGE = """
This is not a travel model bespoke request but I had to put it in GitHub so here we are.
"""

import pathlib
import pandas as pd

WORKPLAN_DIR = pathlib.Path("E:\Box\Modeling and Surveys\FMS Work Planning")
WORKPLAN_FILE = WORKPLAN_DIR / "FMS Work Planning.xlsx"
WORKPLAN_SHEETNAME = "FMS Staff Hours FY24-25"
WORKPLAN_HEADER = 2
WORKPLAN_USECOLS = "A:P"

if __name__ == '__main__':
    workplan_df = pd.read_excel(
        WORKPLAN_FILE,
        sheet_name=WORKPLAN_SHEETNAME,
        header=WORKPLAN_HEADER,
        usecols=WORKPLAN_USECOLS
    )
    print(workplan_df.dtypes)
    # drop these columns
    workplan_df.drop(columns=["START DATE","END DATE","EFFORT HOURS CHECK","EFFORT HOURS"], inplace=True)
    # drop null project name
    workplan_df = workplan_df.loc[ pd.notnull(workplan_df["PROJECT NAME"]) ]
    # drop roll-up project category
    workplan_df = workplan_df.loc[ workplan_df["Project Category"] != "Roll-up"]
    print(workplan_df)

    # wide-to-long
    workplan_long_df = pd.melt(
        frame=workplan_df,
        id_vars=["Harvest Task","Project Category","PROJECT NAME"],
        var_name="Full Name",
        value_name="Workplan Estimated Hours")
    print(workplan_long_df)

    output_file = WORKPLAN_DIR / f"{WORKPLAN_SHEETNAME}_long.csv"
    workplan_long_df.to_csv(output_file, index=False)
    print(f"Wrote {output_file}")