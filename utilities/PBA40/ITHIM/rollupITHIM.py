USAGE = """

  python rollupITHIM.py

  Reads ITHIM files and rolls them up to a single file

  * Reads
    * metrics\ITHIM\percapita_daily_dist_time.csv
    * metrics\ITHIM\DistanceTraveledByFacilityType_auto+truck.csv
    * metrics\ITHIM\DistanceTraveledByFacilityType_transit.csv

  * combines and write metrics\ITHIM\results.csv

"""

import os,sys
import pandas

FILES = [
    os.path.join("metrics","ITHIM","percapita_daily_dist_time.csv"),
    os.path.join("metrics","ITHIM","DistanceTraveledByFacilityType_auto+truck.csv"),
    os.path.join("metrics","ITHIM","DistanceTraveledByFacilityType_transit.csv"),
]

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

    outfile = os.path.join("metrics","ITHIM","results.csv")
    all_results_df.to_csv(outfile, index=False)
    print "Wrote %s" % outfile