USAGE = """

  python reformatEmissions.py

  Reformats metrics\vmt_vht_metrics.csv emisions-related items for ITHIM inputs
  Outputs metrics\ITHIM\emissions.csv

"""

import os, sys
import pandas, numpy

#if __name__ == '__main__':
pandas.set_option('display.width', 500)

infile = os.path.join("metrics","vmt_vht_metrics_by_county_test1.csv")
vmt_vht_metrics_df = pandas.read_table(infile, sep=",")

vmt_vht_metrics_df["gl"]=vmt_vht_metrics_df["gl"].apply(str)

    # aggregate vehicle classes
gl_mapping = {
        "1" : "San Francisco",
        "2" : "San Mateo",
        "3" : "Santa Clara",
        "4" : "Alameda",
        "5" : "Contra Costa",
        "6": "Solano",
        "7": "Napa",
        "8": "Sonoma",
        "9": "Marin",
        "10": "External"
    }
vmt_vht_metrics_df.replace({"gl":gl_mapping}, inplace=True)

vmt_vht_metrics_df.drop(['timeperiod','vehicle class'], axis=1, inplace=True)
#print vmt_vht_metrics_df

county_metrics_df = vmt_vht_metrics_df.groupby(["gl"]).sum()

print vmt_vht_metrics_df
print county_metrics_df

outfile = os.path.join("metrics","Metrics By County.csv")
county_metrics_df.to_csv(outfile)
print "Wrote %s" % outfile
