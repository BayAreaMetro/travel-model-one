USAGE = """

  python rollupITHIM.py

  Reads ITHIM files and rolls them up to a single file
  Gets the scenario id from the current working directory

  * Reads
    * metrics\ITHIM\percapita_daily_dist_time.csv
    * metrics\ITHIM\DistanceTraveledByFacilityType_auto+truck.csv
    * metrics\ITHIM\DistanceTraveledByFacilityType_transit.csv
    * metrics\ITHIM\emissions.csv

  * combines and write metrics\ITHIM\results.csv

"""

import datetime,os,sys
import pandas

FILES = [
    os.path.join("metrics","ITHIM","percapita_daily_dist_time.csv"),
    os.path.join("metrics","ITHIM","DistanceTraveledByFacilityType_auto+truck.csv"),
    os.path.join("metrics","ITHIM","DistanceTraveledByFacilityType_transit.csv"),
    # os.path.join("metrics","ITHIM","emissions.csv")
]

ITEM_IDS = pandas.DataFrame(
    columns=['item_id','item_name'],
    data  =[['1'      ,'Per Capita Mean Daily Travel Time'                    ],
            ['3'      ,'Per Capita Mean Daily Travel Distance'                ],
            ['18'     ,'Population Forecasts (ABM)'                           ],
            ['10.1'   ,'Total PMT'                                            ],
            ['10.2'   ,'Total PHT'                                            ],
            ['11'     ,'Proportion of Vehicle Miles by Mode and Facility Type']])

COLUMNS = ["scenid_itemid_mode_strata_age_sex",
           "query_id",
           "scenario_id",
           "item_id",
           "item_name",
           "units",
           "urbrur",
           "report_year",
           "geotype",
           "geotype_name",
           "geotype_code",
           "mode",
           "mode_code",
           "strata_type",
           "strata",
           "strata_code",
           "age_group",
           "sex",
           "unwt_n",
           "wt_n",
           "item_result",
           "se",
           "cv",
           "Date",
           "Source"]

def string_formatter(x):
    if x==None:
        return ""
    if pandas.isnull(x):
        return ""
    return str(x)

if __name__ == '__main__':

    all_results_df   = None
    all_results_init = False

    for filename in FILES:
        results_df = pandas.read_table(filename, sep=",")
        print "Read %s" % filename

        if all_results_init:
            all_results_df = all_results_df.append(results_df)
        else:
            all_results_df = results_df
            all_results_init = True

    all_results_df.rename(columns={"item_value":"item_result"}, inplace=True)

    # add a couple missing rows
    all_results_df = all_results_df.append({"item_name":"Per Capita Mean Daily Travel Time",
                                            "units"    :"minutes",
                                            "mode"     :"other"},
                                            ignore_index=True)
    all_results_df = all_results_df.append({"item_name":"Per Capita Mean Daily Travel Distance",
                                            "units"    :"miles",
                                            "mode"     :"other"},
                                            ignore_index=True)

    # join to get the item ids
    all_results_df = pandas.merge(left=all_results_df, right=ITEM_IDS, how='left')

    # set the scenario id from the current working dir
    all_results_df["scenario_id"] = os.path.split(os.getcwd())[1]
    # for now, make it the same, but this should really be human readable
    all_results_df["report_year"] = all_results_df["scenario_id"]

    # use today's date
    all_results_df["Date"] = datetime.date.today().strftime("%m/%d/%y")
    # this is MTC model one
    all_results_df["Source"] = "MTC Travel Model One"

    # make sure all the columns are there
    have_cols = list(all_results_df.columns.values)
    for col in COLUMNS:
        if col not in have_cols:
            all_results_df[col] = None

    # this one is special
    all_results_df["scenid_itemid_mode_strata_age_sex"] = all_results_df["scenario_id"].map(string_formatter) + "_" + \
                                                          all_results_df["item_id"].map(string_formatter)     + "_" + \
                                                          all_results_df["mode"].map(string_formatter)        + "_" + \
                                                          all_results_df["strata"].map(string_formatter)      + "_" + \
                                                          all_results_df["age_group"].map(string_formatter)   + "_" + \
                                                          all_results_df["sex"].map(string_formatter)

    # sort by numeric item_id
    all_results_df["numeric item_id"] = all_results_df["item_id"].astype(float)

    # change freeway strata to highway
    all_results_df.loc[all_results_df["strata"]=="freeway", "strata"] = "highway"

    # order the columns and sort by item_id them
    all_results_df = all_results_df.sort_values(by=["numeric item_id","mode","strata"])[COLUMNS]

    outfile = os.path.join("metrics","ITHIM","results.csv")
    all_results_df.to_csv(outfile, index=False)
    print "Wrote %s" % outfile