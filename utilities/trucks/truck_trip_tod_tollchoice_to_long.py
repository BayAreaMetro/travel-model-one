USAGE = r"""

  python truck_trip_tod_tollchoice_to_long.py truck_trip_tod_tollchoice_[model_run_id].csv

  Converts wide version of file output by extract_truck_trip_tod_tollchoice.job into long version
  by moving the truck classes and time periods from columns to rows.
"""

import argparse,sys
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

    # remove lines with truck trips == 0
    print("Length: {:,}".format(len(trucks_long_df)))
    trucks_long_df = trucks_long_df.loc[ trucks_long_df["truck trips"] > 0 ]
    print("After filter, length: {:,}".format(len(trucks_long_df)))

    # read skims
    skim_file = "truck_skims_{}.csv".format(model_run)
    skims_df = pandas.read_csv(skim_file)
    skims_df.drop(columns=["one_a","one_b"], inplace=True)
    print(skims_df.head())
    print("columns: {}".format(skims_df.columns.values))

    # join to trucks_long_df to fill in time, dist, vtoll
    trucks_long_df["time"] = 0.00
    trucks_long_df["dist"] = 0.00
    trucks_long_df["vtoll"] = 0.00
    trucks_long_cols = list(trucks_long_df.columns.values)
    trucks_long_df = pandas.merge(
        left=trucks_long_df,
        right=skims_df,
        on=["orig","dest"]
    )
    for time_period in ["EA","AM","MD","PM","EV"]:
        for truck_class in ["verySmall","small","medium","large"]:
            for toll_choice in ["toll","noToll"]:
                skim_col = "{} {} {}".format(toll_choice, truck_class, time_period)
                # small==verySmall so the skims only have verySmall
                if truck_class == "small":
                    skim_col = skim_col.replace("small","verySmall")
                print("setting skim values for {}".format(skim_col))
                time_skim_col = "time {}".format(skim_col)
                trucks_long_df.loc[ (trucks_long_df["time period"]==time_period) & \
                                    (trucks_long_df["truck class"]==truck_class) & \
                                    (trucks_long_df["toll choice"]==toll_choice), "time"] = trucks_long_df[time_skim_col]
                dist_skim_col = "dist {}".format(skim_col)
                trucks_long_df.loc[ (trucks_long_df["time period"]==time_period) & \
                                    (trucks_long_df["truck class"]==truck_class) & \
                                    (trucks_long_df["toll choice"]==toll_choice), "dist"] = trucks_long_df[dist_skim_col]
                if toll_choice == "noToll": continue

                vtoll_skim_col = "vtoll {}".format(skim_col)
                trucks_long_df.loc[ (trucks_long_df["time period"]==time_period) & \
                                    (trucks_long_df["truck class"]==truck_class) & \
                                    (trucks_long_df["toll choice"]==toll_choice), "vtoll"] = trucks_long_df[vtoll_skim_col]

    print("Dropping extra cols")
    trucks_long_df = trucks_long_df[trucks_long_cols]

    trucks_long_df.to_csv(output_file, index=False)
    print("Wrote {}".format(output_file))

