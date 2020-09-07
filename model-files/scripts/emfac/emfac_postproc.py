USAGE = """

    This script is to be run after EMFAC is completed.
    It takes the EMFAC output file as an input and then write out a concise summary of the regional level results.

    To run this script, start from the model run directory, e.g. B:\Projects\2035_TM152_FBP_Plus_01
    Note that the emfac output file name should be included as an argument of the run command.
    e.g. python ctramp/scripts/emfac/emfac_postproc.py ready4emfac_2035_TM152_DBP_Plus_08_emfac_sb375_20200902173104.xlsx

"""

import pandas as pd
#import numpy as np

import os.path
from os import path

from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows

import argparse

# -------------------------------------------------------------------
# Input/output file names and locations
# -------------------------------------------------------------------
project_dir = os.getcwd()
run_id = project_dir.split('\\')[-1]

parser = argparse.ArgumentParser(description=USAGE)
parser.add_argument("emfacfile", help="The output file from EMFAC, which will be the input to the current process.")
args = parser.parse_args()

# the input file name will be an argument
emfac_output_xlsx = args.emfacfile
# could potentially use file name wildcards e.g. ready4emfac*
# emfac_output_xlsx = "ready4emfac_2035_TM152_DBP_Plus_08_emfac_sb375_20200902173104.xlsx"
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
