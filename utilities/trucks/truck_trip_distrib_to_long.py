USAGE = r"""

  python truck_trip_distrib_to_long.py truck_trip_distrib_[model_run_id].csv

  Converts wide version of file output by extract_truck_trip_distrib.job into long version
  by moving the truck classes from columns to rows.
"""
import argparse,os,re,sys
import pandas

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=USAGE)
    parser.add_argument("input_file", help="File output by extract_truck_trip_distrib.job")
    args = parser.parse_args()

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

    trucks_long_df = pandas.wide_to_long(trucks_df, ["skim time","skim toll time","daily trips"], 
                                         i=["production","attraction","truck_k"], j="truck class", sep=" ",
                                         suffix=r"(verySmall|small|medium|large)")
    trucks_long_df.reset_index(drop=False, inplace=True)

    # very small trucks don't use k factors
    print(trucks_long_df.head())
    trucks_long_df.loc[trucks_long_df["truck class"]=="verySmall", "truck_k"] = 1.0

    trucks_long_df.to_csv(output_file, index=False)
    print("Wrote {}".format(output_file))
