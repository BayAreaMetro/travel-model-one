USAGE = """

Filter out households and persons with home TAZ in unconnected zones from accessibilities/logsums inputs.

  Input:   skims\\unconnected_zones.dbf (from skims\\findNoAccessZones.job)
           logsums\\accessibilities_dummy_full_households.csv
           logsums\\accessibilities_dummy_full_persons.csv
           logsums\\accessibilities_dummy_full_model_households.csv
           logsums\\accessibilities_dummy_full_model_persons.csv
           logsums\\accessibilities_dummy_full_indivTours.csv

  Output:  logsums\\accessibilities_dummy_households.csv
           logsums\\accessibilities_dummy_persons.csv
           logsums\\accessibilities_dummy_model_households.csv
           logsums\\accessibilities_dummy_model_persons.csv
           logsums\\accessibilities_dummy_indivTours.csv
"""

import os, shutil, sys
import pandas
from dbfpy import dbf

FILES = ["households", "persons", "model_households", "model_persons", "indivTours"]

if __name__ == "__main__":

    unconnected_zones = []
    unconnected_zones_file = os.path.join("skims", "unconnected_zones.dbf")
    db = dbf.Dbf(unconnected_zones_file)
    for rec in db:
        # rec["NOCONNECT"] == 1
        unconnected_zones.append(rec["ZONE"])

    print(
        "Found {} unconnected zone(s) in {}".format(
            len(unconnected_zones), unconnected_zones_file
        )
    )

    # exclude external zones
    unconnected_zones[:] = [x for x in unconnected_zones if x <= 1454]
    print(
        "Found {} unconnected zone(s) in {} after excluding external zones".format(
            len(unconnected_zones), unconnected_zones_file
        )
    )

    # nothing to do -- just copy the files
    if len(unconnected_zones) == 0:
        print("No filtering to do -- copying files")
        for fileword in FILES:
            shutil.copyfile(
                src=os.path.join(
                    "logsums", "accessibilities_dummy_full_{}.csv".format(fileword)
                ),
                dst=os.path.join(
                    "logsums", "accessibilities_dummy_{}.csv".format(fileword)
                ),
            )
        sys.exit(0)

    # let's filter
    filter_hh_ids = []
    for fileword in FILES:
        infile = os.path.join(
            "logsums", "accessibilities_dummy_full_{}.csv".format(fileword)
        )
        df = pandas.read_csv(infile)
        print("Read {:9d} lines from {}".format(len(df), infile))

        # first, we need the list of household IDs
        if len(filter_hh_ids) == 0:
            filter_hh_ids = (
                df.loc[df.TAZ.isin(unconnected_zones), "HHID"].unique().tolist()
            )
            print(
                "Filtering out {} households: {}".format(
                    len(filter_hh_ids), filter_hh_ids
                )
            )

        # HHID or hh_id
        if "HHID" in list(df.columns.values):
            df = df.loc[~df.HHID.isin(filter_hh_ids)]
        elif "hh_id" in list(df.columns.values):
            df = df.loc[~df.hh_id.isin(filter_hh_ids)]
        else:
            raise NotImplementedError("Input file has neither HHID or hh_id")

        # write it out
        outfile = os.path.join(
            "logsums", "accessibilities_dummy_{}.csv".format(fileword)
        )
        df.to_csv(outfile, index=False)
        print("Wrote {:8d} lines to   {}".format(len(df), outfile))
