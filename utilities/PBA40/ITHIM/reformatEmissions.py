USAGE = """

  python reformatEmissions.py

  Reformats metrics\vmt_vht_metrics.csv emisions-related items for ITHIM inputs
  Outputs metrics\ITHIM\emissions.csv

"""

import os, sys
import pandas, numpy

if __name__ == '__main__':
    pandas.set_option('display.width', 500)

    infile = os.path.join("metrics","vmt_vht_metrics.csv")
    vmt_vht_metrics_df = pandas.read_table(infile, sep=",")

    # aggregate vehicle classes
    vehclass_mapping = {
        "DA" : "car",
        "S2" : "car",
        "S3" : "car",
        "SM" : "truck",
        "HV" : "truck",
        "DAT": "car",
        "S2T": "car",
        "S3T": "car",
        "SMT": "truck",
        "HVT": "truck"
    }
    vmt_vht_metrics_df.replace({"vehicle class":vehclass_mapping}, inplace=True)

    vmt_vht_metrics_df = vmt_vht_metrics_df.groupby(["vehicle class"]).sum()

    # only keep emissions
    vmt_vht_metrics_df = vmt_vht_metrics_df[["ROG","S_NOx","SOx","W_NOx","CO2","Diesel_PM2.5","Gas_PM2.5","Diesel PM",
                                             "Butadiene","Benzene","Acetaldehyde","Formaldehyde","TOG_exh","PM10","PM10_wear","PM2.5_wear"]]

    vmt_vht_metrics_df = vmt_vht_metrics_df.unstack().reset_index()
    vmt_vht_metrics_df.rename(columns={"level_0":"Parameter", "vehicle class":"Mode", 0:"value"}, inplace=True)
    vmt_vht_metrics_df["Units"] = "metric tons"

    outfile = os.path.join("metrics","ITHIM","emissions.csv")
    vmt_vht_metrics_df.to_csv(outfile, index=False)
    print "Wrote %s" % outfile
