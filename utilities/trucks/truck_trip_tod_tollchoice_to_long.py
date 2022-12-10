USAGE = r"""

  python truck_trip_tod_tollchoice_to_long.py truck_trip_tod_tollchoice_[model_run_id].csv

  Converts wide version of file output by extract_truck_trip_tod_tollchoice.job into long version
  by moving the truck classes and time periods from columns to rows.
"""

import argparse
import pandas

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=USAGE)
    parser.add_argument("input_file", help="File output by extract_truck_trip_distrib.job")
    args = parser.parse_args()

    model_run = args.input_file.replace(".\\truck_trip_tod_tollchoice_", "")
    model_run = model_run.replace(".csv", "")
    print("Model run: {}".format(model_run))

    output_file = args.input_file.replace(".csv","_long.csv")
    print(output_file)

    trucks_df = pandas.read_csv(args.input_file)
    # strip spaces from column names
    column_names = list(trucks_df.columns.values)
    column_renames = {}
    for col in column_names:
        column_renames[col] = col.strip()
    trucks_df.rename(columns=column_renames, inplace=True)

    # remove the ones
    trucks_df.drop(columns=["one_a","one_b"], inplace=True)
    print(trucks_df.head())

    trucks_long_df = pandas.wide_to_long(
        trucks_df, 
        ["truck trips noToll verySmall","truck trips noToll small", "truck trips noToll medium","truck trips noToll large",
         "truck trips toll verySmall",  "truck trips toll small",   "truck trips toll medium",  "truck trips toll large"],
        i=["orig","dest"], 
        j="time period",
        sep=" ",
        suffix=r"(EA|AM|MD|PM|EV)"
    )
    trucks_long_df.reset_index(drop=False, inplace=True)

    trucks_long_df = pandas.wide_to_long(
        trucks_long_df, 
        ["truck trips noToll","truck trips toll"],
        i=["orig","dest","time period"], 
        j="truck class",
        sep=" ",
        suffix=r"(verySmall|small|medium|large)"
    )
    trucks_long_df.reset_index(drop=False, inplace=True)
    print(trucks_long_df.head())

    trucks_long_df = pandas.wide_to_long(
        trucks_long_df, 
        ["truck trips"],
        i=["orig","dest","time period","truck class"], 
        j="toll choice",
        sep=" ",
        suffix=r"(toll|noToll)"
    )
    trucks_long_df.reset_index(drop=False, inplace=True)
    print(trucks_long_df.head())

    trucks_long_df.to_csv(output_file, index=False)
    print("Wrote {}".format(output_file))

