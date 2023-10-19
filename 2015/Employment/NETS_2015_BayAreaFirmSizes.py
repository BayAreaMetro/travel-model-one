USAGE = """
  Creates file with Bay Area firm sizes from establishment data.

  Takes National Establishment Time-Series (NETS) Database 2015 and filters to Bay Area FIPS15,
  groups by headquarters DUNS (HQDuns15) and outputs Emp15 sum.

  Output file contains columns:
  * HQDuns15 - the HQDuns15 used in the groupby
  * BayAreaEstCount - count of matching establishments with Bay Area FIPS15
  * BayAreaFirmEmp15 - sum of Emp15 for those establishments with Bay Area FIPS15

"""

import os, sys
import pandas

NETS_DIR  = "M:\\Data\\NETS\\2015"
NETS_FILE = os.path.join(NETS_DIR, "NETSData2015_CA.txt")
OUT_FILE  = os.path.join(NETS_DIR, "BayAreaFirmSizes.csv")
BAY_AREA_FIPS = [
    "06001", # Alameda
    "06013", # Contra Costa
    "06041", # Marin
    "06055", # Napa
    "06075", # San Francisco
    "06081", # San Mateo
    "06085", # Santa Clara
    "06095", # Solano
    "06097", # Sonoma
]

if __name__ == '__main__':
    nets_df = pandas.read_csv(NETS_FILE, sep="\t", usecols=["DunsNumber","Emp15","HQDuns15","FIPS15"], 
                             dtype={"DunsNumber":'str',"HQDuns15":'str',"FIPS15":'str'})
    print("Read {} rows from {}; head:\n{}".format(len(nets_df), NETS_FILE, nets_df.head()))

    # filter to Bay Area counties
    nets_df = nets_df[nets_df.FIPS15.isin(BAY_AREA_FIPS)]
    print("Filtered to Bay Area FIP15 to get {} rows".format(len(nets_df)))

    # how many blank Emp15?
    print("Count of null    Emp15: {}".format(len(nets_df.loc[pandas.isnull(nets_df.Emp15)])))
    print("Count of null HQDuns15: {}".format(len(nets_df.loc[pandas.isnull(nets_df.HQDuns15)])))

    # groupby HQDuns15
    nets_hq_df = nets_df.groupby(["HQDuns15"]).aggregate({"DunsNumber":"count", "Emp15":"sum"})
    nets_hq_df.rename(columns={"DunsNumber":"BayAreaEstCount", "Emp15":"BayAreaFirmEmp15"}, inplace=True)
    nets_hq_df.reset_index(drop=False, inplace=True)
    print("Grouped to HQDuns15: \n{}".format(nets_hq_df.head()))

    nets_hq_df.to_csv(OUT_FILE, index=False)
    print("Wrote {} rows to {}".format(len(nets_hq_df), OUT_FILE))
