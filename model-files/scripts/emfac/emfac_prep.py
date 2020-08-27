# this script is run after the Cube scripts for EMFAC



import pandas as pd

import os.path
from os import path

from openpyxl import load_workbook


# -------------------------------------------------------------------
# Input/output file names and locations
# -------------------------------------------------------------------
arg1_filename = "emfac_prep\\ByVehFuel_Emfac2014_SB375_Yr2035_11Subareas.xlsx"

output_filename1 = "emfac_prep\\vmt_b4reshape.csv"
output_filename2 = "emfac_prep\\vmt.csv"
output_filename = "emfac_prep\\hourlyfraction.csv"


# -------------------------------------------------------------------
# Calcuate the hourly fraction from CreateSpeedBinsBetweenZones and CreateSpeedBinsWithinZones
# -------------------------------------------------------------------
# The Travel Model doesn't have the concept of Veh_Tech, so the fractions are the assumed to be same for each subarea-hour combination

# read in between zones VMT and intrazonal VMT
BetweenZones_df = pd.read_csv(os.path.join(os.getcwd(), "emfac_prep", "CreateSpeedBinsBetweenZones_sums.csv"), index_col=False, sep=",")
WithinZones_df = pd.read_csv(os.path.join(os.getcwd(), "emfac_prep", "CreateSpeedBinsWithinZones_sums.csv"), index_col=False, sep=",")

# what is the format of these VMT files?
# rows    = countyName (9 counties + 1 external) x speed bin (13) + header (1) = 10 x 13 + 1 = 131
# (in the future, rows = AirBasinName (11 airbains + 1 external) x speed bin (18) + header (1) = 12 x 18 + 1 = 217)
# columns = 24 hours + 3 index columns (countyName, arbCounty, speedBin) = 27

# if it's the old format, rename countyName to subareaName
numLine_Between = len(BetweenZones_df.index)
print "\nFinished reading CreateSpeedBinsBetweenZones_sums.csv"
print "Number of rows in CreateSpeedBinsBetweenZones_sums.csv = " + str(numLine_Between)

numLine_Within = len(WithinZones_df.index)
print "\nFinished reading CreateSpeedBinsWithinZones_sums.csv"
print "Number of rows in CreateSpeedBinsWithinZones_sums.csv = " + str(numLine_Within)

if numLine_Between+numLine_Within == 260:
    BetweenZones_df.rename(columns={"countyName": "subareaName"}, inplace=True)
    WithinZones_df.rename(columns={"countyName": "subareaName"}, inplace=True)

# add the between zones VMT and intrazonal VMT together
VMT_df = BetweenZones_df.add(WithinZones_df, fill_value=0)

# fix the index columns (countyName, arbCounty, speedBin) - countyName is messed up but fixing it is not a priority
VMT_df[' arbCounty'] = VMT_df[' arbCounty']/2
VMT_df[' speedBin'] = VMT_df[' speedBin']/2

VMT_df['nameLen'] = (VMT_df['subareaName'].str.len() / 2).astype(int) # temporary column
# VMT_df['subareaName'] = VMT_df['subareaName'].str[:VMT_df['nameLen']]  # this way of slicing does not work
# VMT_df['subareaName'] = VMT_df['subareaName'].str.slice(start=-VMT_df['nameLen']) # this way of slicing does not work either
VMT_df['subareaName'] = VMT_df.apply(lambda r: r.subareaName[:r.nameLen], axis=1) # this way of slicing worked

# drop the temporary nameLen column
VMT_df.drop(['nameLen'], axis=1, inplace=True)

# drop external VMT
VMT_df = VMT_df.loc[VMT_df[' arbCounty'] != 9999]

VMT_df.to_csv(output_filename1, header=True, index=False)

# reshape the data frame so that:
# The rows are subarea (11) x hour (24)
# The columns are the 18 speed bins

# create dataframe for each subsarea and loop through tem
# store your dataframes into a dictionary
dict_of_df = {}
for subarea in ['Alameda', 'Contra Costa', 'Marin']:

    key_name = 'VMT_'+str(subarea)+'_df'

    dict_of_df[key_name] = VMT_df.loc[VMT_df['subareaName'] == subarea]
    dict_of_df[key_name] = dict_of_df[key_name].transpose()

    # take the data less the first 3 rows
    dict_of_df[key_name] = dict_of_df[key_name][3:]

    # give the columns the speedBin name

    # if the cube outputs only have 13 speed bins, add the extra speed bins
    if numLine_Between+numLine_Within == 260:
        dict_of_df[key_name]["70mph"] = 0
        dict_of_df[key_name]["75mph"] = 0
        dict_of_df[key_name]["80mph"] = 0
        dict_of_df[key_name]["85mph"] = 0
        dict_of_df[key_name]["90mph"] = 0

    dict_of_df[key_name].rename(columns={ dict_of_df[key_name].columns[0]: "5mph" }, inplace = True)
    dict_of_df[key_name].rename(columns={ dict_of_df[key_name].columns[1]: "10mph" }, inplace = True)
    dict_of_df[key_name].rename(columns={ dict_of_df[key_name].columns[2]: "15mph" }, inplace = True)
    dict_of_df[key_name].rename(columns={ dict_of_df[key_name].columns[3]: "20mph" }, inplace = True)
    dict_of_df[key_name].rename(columns={ dict_of_df[key_name].columns[4]: "25mph" }, inplace = True)
    dict_of_df[key_name].rename(columns={ dict_of_df[key_name].columns[5]: "30mph" }, inplace = True)
    dict_of_df[key_name].rename(columns={ dict_of_df[key_name].columns[6]: "35mph" }, inplace = True)
    dict_of_df[key_name].rename(columns={ dict_of_df[key_name].columns[7]: "40mph" }, inplace = True)
    dict_of_df[key_name].rename(columns={ dict_of_df[key_name].columns[8]: "45mph" }, inplace = True)
    dict_of_df[key_name].rename(columns={ dict_of_df[key_name].columns[9]: "50mph" }, inplace = True)
    dict_of_df[key_name].rename(columns={ dict_of_df[key_name].columns[10]: "55mph" }, inplace = True)
    dict_of_df[key_name].rename(columns={ dict_of_df[key_name].columns[11]: "60mph" }, inplace = True)
    dict_of_df[key_name].rename(columns={ dict_of_df[key_name].columns[12]: "65mph" }, inplace = True)
    if numLine_Between+numLine_Within > 260:
        dict_of_df[key_name].rename(columns={ dict_of_df[key_name].columns[13]: "70mph" }, inplace = True)
        dict_of_df[key_name].rename(columns={ dict_of_df[key_name].columns[14]: "75mph" }, inplace = True)
        dict_of_df[key_name].rename(columns={ dict_of_df[key_name].columns[15]: "80mph" }, inplace = True)
        dict_of_df[key_name].rename(columns={ dict_of_df[key_name].columns[16]: "85mph" }, inplace = True)
        dict_of_df[key_name].rename(columns={ dict_of_df[key_name].columns[17]: "90mph" }, inplace = True)

    # after transposing, need to add a column with the subaraeName and hour
    dict_of_df[key_name]['subareaName'] = subarea

    dict_of_df[key_name]['Hour'] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]

    # reorder columns
    dict_of_df[key_name] = dict_of_df[key_name][['subareaName','Hour', '5mph','10mph','15mph','20mph','25mph','30mph','35mph','40mph','45mph','50mph','55mph','60mph','65mph','70mph','75mph','80mph','85mph','90mph']]

    # add it to the final data DataFrame
    if subarea == 'Alameda': # the air basin name may be different ... to be fixed
        VMT_reshpae_df = dict_of_df[key_name]
    else:
        VMT_reshpae_df = VMT_reshpae_df.append(dict_of_df[key_name])

    VMT_reshpae_df.to_csv(output_filename2, header=True, index=False)

# -------------------------------------------------------------------
# Input the Travel Model data into the EMFAC Custom Activity Template
# -------------------------------------------------------------------

print "\nLoading the workbook "+arg1_filename
workbook = load_workbook(filename=arg1_filename)
print "\nWhat are the different tabs in this workbook?"
print workbook.sheetnames

# make "the hourly fraction tab" the active tab
sheet = workbook["Hourly_Fraction_Veh_Tech_Speed"]
print "\nActivated the tab:"
print sheet

# The key data items I want to extract from this tab are the Sub-Area column (column A) and the Hour column (column F)
# as these two columns will from the "index"
# but it seeems easier to just read all the data in this sheet, so this is what've done below.
print "\nReading in Hourly_Fraction_Veh_Tech_Speed"
DefaultHourlyFraction = sheet.values

# Set the first row as the columns for the DataFrame
cols = next(DefaultHourlyFraction)
DefaultHourlyFraction = list(DefaultHourlyFraction)

DefaultHourlyFraction_df = pd.DataFrame(DefaultHourlyFraction, columns=cols)
DefaultHourlyFraction_df.to_csv(output_filename, header=True, index=False)

print "\nFinish reading in the default Hourly_Fraction_Veh_Tech_Speed"

# Some notes about the "Hourly_Fraction_Veh_Tech_Speed" tab:

# there are 11 Sub-Areas (9 counties but Solano and Sonoma are in 2 air basins)
# the Sub-Areas are ordered as followed when the "custom activity template" was generated by EMFAC:
# Solano (SV)
# Alameda (SF)
# Contra Costa (SF)
# Marin (SF)
# Napa (SF)
# San Francisco (SF)
# San Mateo (SF)
# Santa Clara (SF)
# Solano (SF)
# Sonoma (SF)
# Sonoma (NC)

# The "Hourly_Fraction_Veh_Tech_Speed" is essentially a table of subarea (11) x hour (24) x speed bins (18).
# The rows are subarea (11) x hour (24)
# The columns are the 18 speed bins
