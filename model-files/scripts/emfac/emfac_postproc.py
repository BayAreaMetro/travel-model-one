USAGE = """

    This script is to be run after EMFAC is completed.
    It takes the EMFAC output file as an input and then write out a concise summary of the regional level results.

    To run this script, start from the model run directory, e.g. A:\Projects\2050_TM152_FBP_PlusCrossing_16

    - Run this scrpit, with SB375 or EIR as an argument
      e.g. python ctramp/scripts/emfac/emfac_postproc.py SB375

"""

import pandas as pd

import os.path
from os import path

import shutil 
import glob

from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows

import argparse

# -------------------------------------------------------------------
# Input/output file names and locations
# -------------------------------------------------------------------
project_dir = os.getcwd()
run_id = project_dir.split('\\')[-1]

parser = argparse.ArgumentParser(description=USAGE)
parser.add_argument("emfacVersion", help="Specify SB375 or EIR.")
args = parser.parse_args()

if args.emfacVersion=="SB375":
    # this is the path for the output of EMFAC 2014, used for SB375
    EMFAC_PATH = "\\\mainmodel\MainModelShare\emfac\emfac2014_v1.0.7\output"

if args.emfacVersion=="EIR":
    # this is the path for the output of EMFAC 2014, used for SB375
    EMFAC_PATH = "\\\mainmodel\MainModelShare\emfac\emfac2017-v1.0.2\EMFAC2017-v1.0.2\output"

for emfacfile in glob.glob(EMFAC_PATH + "\\" + "ready4emfac_" + run_id + "_sb375*.xlsx"):
    print(emfacfile)
    shutil.copy2(emfacfile, project_dir + "/emfac_prep")

emfac_output_xlsx = emfacfile.split('\\')[-1]

emfac_output_xlsx_fullpath = "emfac_prep\\" + emfac_output_xlsx

output_csv = "emfac_prep\\emfac_ghg.csv"

# -------------------------------------------------------------------
# Read the results in the "By Sub-Area" tab and then write them out
# -------------------------------------------------------------------

print "\n\n================================================================"
print "Generating a regional-level summary of the EMFAC output"
print "================================================================"

print "\nLoading the workbook "+emfac_output_xlsx_fullpath
workbook = load_workbook(filename=emfac_output_xlsx_fullpath)
print "\nWhat are the different tabs in this workbook?"
print workbook.sheetnames

# make "By Sub-Area" the active tab
sheet = workbook["By Sub-Area"]
print "\nActivated the tab:"
print sheet

# Read the results in the "By Sub-Area" tab
print "\nReading the data from the <By Sub-Area> tab"
EMFACresults = sheet.values

# Set the first row as the headers for the DataFrame
cols = next(EMFACresults)
EMFACresults = list(EMFACresults)

EMFACresults_df = pd.DataFrame(EMFACresults, columns=cols)

# Read the results in the "By Sub-Area" tab
print "\nFinished reading the data from the <By Sub-Area> tab"

# keep if the column "EMFAC2007 Category" = "All Vehicles"
EMFACsummary_df = EMFACresults_df.loc[EMFACresults_df['EMFAC2007 Category'] == " All Vehicles"]

# keep only the relevant columns
EMFACsummary_df = EMFACsummary_df[['EMFAC2007 Category','VMT', 'Trips', 'CO2_RUNEX', 'CO2_IDLEX', 'CO2_STREX', 'CO2_TOTEX']]

# calculate the sum for the region
EMFACsummary_df = EMFACsummary_df.groupby('EMFAC2007 Category', as_index=False).sum()

# add a column named directory
EMFACsummary_df['Directory'] = run_id

# drop the column named "EMFAC2007 Category"
EMFACsummary_df = EMFACsummary_df[['Directory','VMT', 'Trips', 'CO2_RUNEX', 'CO2_IDLEX', 'CO2_STREX', 'CO2_TOTEX']]

EMFACsummary_df.to_csv(output_csv, header=True, index=False)

# Read the results in the "By Sub-Area" tab
print "\nFinished writing out the regional-level EMFAC results to emfac_prep\\emfac_ghg.csv"

# copy emfac_ghg.csv back to the metrics folder in the model output directory on M
M_DIR = os.getenv('MODEL_DIR')

M_OUTPUT = os.path.join(M_DIR, "OUTPUT") 
if not os.path.isdir(M_OUTPUT):
    os.mkdir(M_OUTPUT)

M_METRICS = os.path.join(M_DIR, "OUTPUT", "metrics") 
if not os.path.isdir(M_METRICS):
    os.mkdir(M_METRICS)

shutil.copy2("emfac_prep\\emfac_ghg.csv", os.path.join(M_DIR,"OUTPUT","metrics"))