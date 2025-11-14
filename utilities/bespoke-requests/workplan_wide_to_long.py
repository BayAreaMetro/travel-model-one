USAGE = """
This is not a travel model bespoke request but I had to put it in GitHub so here we are.
"""

import getpass
import pathlib
import platform
import pandas as pd

WORKPLAN_DIR = pathlib.Path("E:\Box\Modeling and Surveys\FMS Work Planning")
WORKPLAN_SHEETNAME = "FMS FY25-26"
WORKPLAN_HEADER = 3
WORKPLAN_USECOLS = "A:C,O:X"

if platform.system() == "Darwin" and getpass.getuser() == "lzorn":
    WORKPLAN_DIR = pathlib.Path("/Users/lzorn/Library/CloudStorage/Box-Box/Modeling and Surveys/FMS Work Planning")

WORKPLAN_FILE = WORKPLAN_DIR / "FMS Work Planning.xlsx"

if __name__ == '__main__':
    workplan_df = pd.read_excel(
        WORKPLAN_FILE,
        sheet_name=WORKPLAN_SHEETNAME,
        header=WORKPLAN_HEADER,
        usecols=WORKPLAN_USECOLS
    )

    print(workplan_df.dtypes)
    # drop null project name
    workplan_df = workplan_df.loc[ pd.notnull(workplan_df["PROJECT NAME"]) ]
    # drop roll-up project category
    workplan_df = workplan_df.loc[ workplan_df["Project Category"] != "Roll-up"]
    print(workplan_df.loc[ workplan_df["Project Category"]=="Travel Model Development"])

    # wide-to-long
    workplan_long_df = pd.melt(
        frame=workplan_df,
        id_vars=["Harvest Task","Project Category","PROJECT NAME"],
        var_name="Full Name",
        value_name="Workplan Estimated Hours")

    pd.set_option('display.max_rows', 200)
    workplan_long_df.fillna(value={"Workplan Estimated Hours":0}, inplace=True)
    print(workplan_long_df.loc[ workplan_long_df["Project Category"]=="Travel Model Development"])

    output_file = WORKPLAN_DIR / f"{WORKPLAN_SHEETNAME}_long.csv"
    workplan_long_df.to_csv(output_file, index=False)
    print(f"Wrote {output_file}")