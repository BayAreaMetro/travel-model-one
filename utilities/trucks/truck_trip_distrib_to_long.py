USAGE = r"""

  python truck_trip_distrib_to_long.py truck_trip_distrib_[model_run_id].csv

  Converts wide version of file output by extract_truck_trip_distrib.job into long version
  by moving the truck classes from columns to rows.
"""
import argparse,os,sys
import pandas,numpy

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=USAGE)
    parser.add_argument("input_file", help="File output by extract_truck_trip_distrib.job")
    args = parser.parse_args()

    model_run = args.input_file.replace(".\\truck_trip_distrib_", "")
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

    trucks_long_df = pandas.wide_to_long(trucks_df, ["skim time","skim toll time","daily trips"], 
                                         i=["production","attraction","truck_k", "TOLLDISTVSM_AM"], j="truck class", sep=" ",
                                         suffix=r"(verySmall|small|medium|large)")
    trucks_long_df.reset_index(drop=False, inplace=True)

    # very small trucks don't use k factors
    print(trucks_long_df.head())
    trucks_long_df.loc[trucks_long_df["truck class"]=="verySmall", "truck_k"] = 1.0

    trucks_long_df.to_csv(output_file, index=False)
    print("Wrote {}".format(output_file))

    # validation -- sum to production and attraction
    production_df = pandas.pivot_table(trucks_long_df, values="daily trips", index=["production","truck class"], aggfunc=numpy.sum)
    production_df.reset_index(drop=False, inplace=True)
    production_df.rename(columns={"production":"zone", "daily trips":"daily trips produced"}, inplace=True)
    print(production_df.head())

    attraction_df = pandas.pivot_table(trucks_long_df, values="daily trips", index=["attraction","truck class"], aggfunc=numpy.sum)
    attraction_df.reset_index(drop=False, inplace=True)
    attraction_df.rename(columns={"attraction":"zone", "daily trips":"daily trips attracted"}, inplace=True)
    print(attraction_df.head())

    trip_gen_valid_df = pandas.merge(left=production_df, right=attraction_df, how="outer", on=["zone","truck class"])
    print(trip_gen_valid_df.head())

    trip_gen_df = pandas.read_table("truckTG_{}.txt".format(model_run), sep="\s+", 
        names=["zone",
        "trip_gen produced verySmall","trip_gen attracted verySmall",
        "trip_gen produced small",    "trip_gen attracted small",
        "trip_gen produced medium",   "trip_gen attracted medium",
        "trip_gen produced large",    "trip_gen attracted large"])
    trip_gen_df = pandas.wide_to_long(trip_gen_df, ["trip_gen produced","trip_gen attracted"], 
                                       i="zone", j="truck class", sep=" ",
                                       suffix=r"(verySmall|small|medium|large)")
    trip_gen_df.reset_index(drop=False, inplace=True)
    print(trip_gen_df.head())

    trip_gen_valid_df = pandas.merge(left=trip_gen_valid_df, right=trip_gen_df, how="outer", on=["zone", "truck class"])
    print(trip_gen_valid_df.head())

    # go long one more time
    trip_gen_valid_df = pandas.wide_to_long(trip_gen_valid_df, ["trip_gen","daily trips"],
        i=["zone","truck class"], j="p_or_a", sep=" ", suffix=r"(produced|attracted)")
    trip_gen_valid_df.reset_index(drop=False, inplace=True)
    print(trip_gen_valid_df.head())

    output_file = "truck_trip_distrib_validation_{}.csv".format(model_run)
    trip_gen_valid_df.to_csv(output_file, index=False)
    print("Wrote {}".format(output_file))
