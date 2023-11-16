USAGE = """
  Converts Clipper daily ridership from wide to long.

"""

import argparse, os, sys
import pandas

CLIPPER_DIR    = "M:\\Data\\Clipper"
CLIPPER_INPUT  = os.path.join(CLIPPER_DIR, "MonthlySpreadsheet_Jun-2023.xlsx")
CLIPPER_OUTPUT = os.path.join(CLIPPER_DIR, "clipper_daily_ridership_long.xlsx")
if __name__ == '__main__':

    pandas.options.display.width    = 1000
    pandas.options.display.max_rows = 1000
    pandas.options.display.max_columns = 35

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    args = parser.parse_args()

    clipper_daily_df = pandas.read_excel(CLIPPER_INPUT,
                                         sheet_name="Daily Ridership",
                                         skiprows=[0,1])
    clipper_daily_df.drop(columns=["Weekday/Weekend","Unnamed: 33","Unnamed: 34","Unnamed: 35"], inplace=True)
    print(clipper_daily_df.dtypes)

    clipper_daily_df = pandas.melt(clipper_daily_df,
                                   id_vars=["Calendar Day"],
                                   var_name = "Operator",
                                   value_name="Daily Clipper Ridership")
    clipper_daily_df.to_excel(CLIPPER_OUTPUT, sheet_name="Daily Ridership", index=False)
    print("Wrote {:,} rows to {}".format(len(clipper_daily_df), CLIPPER_OUTPUT))