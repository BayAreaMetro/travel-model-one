# This script converts dynamic toll results to a simple toll plan
# The main output is a new tolls.csv

import os
import pandas as pd
import geopandas as gpd
import numpy as np

# user settings
# (they are determined based on a manual review of the toll rate histogram)

# toll rates in cents
high_toll_cents   = 30
medium_toll_cents = 20
low_toll_cents    = 10

high_cutoff    = 23
medium_cutoff  = 13
low_cutoff     = 4

# specify "yes" below if there will be no midday tolls
no_tolls_in_midday = "yes"

project_dir ="L:/Application/Model_One/NextGenFwys/" 
modelrun_with_DynamicTolling = "2035_TM152_NGF_NP02_BPALTsegmented_03_SensDyn00_1"

# output directory
output_dir = "INPUT_DEVELOPMENT/Static_toll_plans/Test2"

# to do: add a log file to record to config 


# ------------------
# Inputs
#-------------------

# input 1
# the toll plan of the dynamic toll run
tollcsv_df = pd.read_csv(os.path.join(project_dir,"Scenarios", modelrun_with_DynamicTolling, "INPUT", "hwy", "tolls.csv")) 

# input 2
# the loaded network from a dynamic tolling run, in which the all-lane tolling system is represented as many short segments (100+)
loadednetwork_100psegs_shp_gdf = gpd.read_file(os.path.join(project_dir, "Scenarios", modelrun_with_DynamicTolling, "OUTPUT", "shapefile", "network_links.shp")) 

# input 
# the file with the tollclass groupings
TollclassGrouping_df = pd.read_csv('X:/travel-model-one-master/utilities/NextGenFwys/TollclassGrouping.csv', index_col=False, sep=",")

# ------------------
# Create data for a toll rate histogram - still to do
#-------------------

# calculate the toll rate of each link (this step isn't really needed)
#loadednetwork_100psegs_shp_gdf["toll_rate am da 100plus"] = loadednetwork_100psegs_shp_gdf["TOLLAM_DA"] / loadednetwork_100psegs_shp_gdf["DISTANCE"]


# merge the tollclass grouping to the loaded network 
loadednetwork_100psegs_shp_gdf = pd.merge(loadednetwork_100psegs_shp_gdf,
                             TollclassGrouping_df,
                             how='left',
                             left_on=['TOLLCLASS'], 
                             right_on = ['TOLLCLASS (network links 100plusSeg.shp)'],
                             indicator=True)


# keep only the links that are part of the all-lane tolling system i.e. tollclass > 700,000
loadednetwork_100psegs_shp_gdf = loadednetwork_100psegs_shp_gdf.loc[loadednetwork_100psegs_shp_gdf['TOLLCLASS'] > 700000]




# ------------------
# Convert average toll rates to high, medium, low 
#-------------------
TimePeriods = ["EA", "AM", "MD", "PM", "EV"]
for tp in TimePeriods:
    print("\n", tp)
    if tp=="EA":
        loadednetwork_100psegs_shp_gdf['USEtp']     = loadednetwork_100psegs_shp_gdf['USEEA']
        loadednetwork_100psegs_shp_gdf['TOLLtp_DA'] = loadednetwork_100psegs_shp_gdf['TOLLEA_DA']
    if tp=="AM":
        loadednetwork_100psegs_shp_gdf['USEtp']     = loadednetwork_100psegs_shp_gdf['USEAM']
        loadednetwork_100psegs_shp_gdf['TOLLtp_DA'] = loadednetwork_100psegs_shp_gdf['TOLLAM_DA']  
    if tp=="MD":
        loadednetwork_100psegs_shp_gdf['USEtp']     = loadednetwork_100psegs_shp_gdf['USEMD']
        loadednetwork_100psegs_shp_gdf['TOLLtp_DA'] = loadednetwork_100psegs_shp_gdf['TOLLMD_DA']  
    if tp=="PM":
        loadednetwork_100psegs_shp_gdf['USEtp']     = loadednetwork_100psegs_shp_gdf['USEPM']
        loadednetwork_100psegs_shp_gdf['TOLLtp_DA'] = loadednetwork_100psegs_shp_gdf['TOLLPM_DA']         
    if tp=="EV":
        loadednetwork_100psegs_shp_gdf['USEtp']     = loadednetwork_100psegs_shp_gdf['USEEV']
        loadednetwork_100psegs_shp_gdf['TOLLtp_DA'] = loadednetwork_100psegs_shp_gdf['TOLLEV_DA']  

    # keep only the variables that are needed
    streamlined_shp_df = loadednetwork_100psegs_shp_gdf[['Grouping major','Grouping minor','USEtp','DISTANCE', 'TOLLtp_DA']] 

    # calculate average toll rate
    SimpleToll_tp_df = streamlined_shp_df.groupby(['Grouping minor', 'USEtp'], as_index=False).sum()
    SimpleToll_tp_df['avg_toll_rate'] = SimpleToll_tp_df['TOLLtp_DA']/SimpleToll_tp_df['DISTANCE']

    # apply a simple rule to convert the results to high, medium, low toll

    # toll rates in dollars
    high_toll_dollars   = high_toll_cents / 100
    medium_toll_dollars = medium_toll_cents / 100
    low_toll_dollars    = low_toll_cents / 100

    TollLevel_conditions = [
        (SimpleToll_tp_df['avg_toll_rate'] >  high_cutoff),
        (SimpleToll_tp_df['avg_toll_rate'] >= medium_cutoff),
        (SimpleToll_tp_df['avg_toll_rate'] >= low_cutoff),
        (SimpleToll_tp_df['avg_toll_rate'] >= 0)]
    TollLevel_choices = [high_toll_dollars, medium_toll_dollars, low_toll_dollars, 0.0001] 
    # note 0.0001 is applied instead of 0 
    # because settolls.job has an input verification step which rejects the tolls.csv if it finds a tolled link with peak period DA tolls equal to 0 
    # as ((TOLLAM_DA == 0) && (TOLLPM_DA == 0)) could means that a TOLLCLASS and USE combination is missing from the tolls.csv
    # https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/preprocess/SetTolls.JOB#L215-L221
    # settolls.job includes codes that sets anything toll value less than 1 cent to 0
    # https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/preprocess/SetTolls.JOB#L224-L269


    SimpleToll_tp_df['simplified_toll'] = np.select(TollLevel_conditions, TollLevel_choices, default='null')

    # store the average toll rate and simplied toll rate for each time period
    if tp=="EA":
        SimpleToll_tp_df['avg_toll_rate_EA']       = SimpleToll_tp_df['avg_toll_rate']
        SimpleToll_tp_df['simplified_toll_EA']     = SimpleToll_tp_df['simplified_toll']
        SimpleToll_EA_df = SimpleToll_tp_df
        # drop variables that are not needed for subsequent processing
        SimpleToll_EA_df.drop(columns=['DISTANCE','TOLLtp_DA', 'avg_toll_rate','simplified_toll'], inplace=True)
        # temp output 
        output_filename1 = os.path.join(project_dir, output_dir,"average_n_simplified_toll_rate_EA.csv")
        SimpleToll_EA_df.to_csv(output_filename1, header=True, index=False)
    if tp=="AM":
        SimpleToll_tp_df['avg_toll_rate_AM']       = SimpleToll_tp_df['avg_toll_rate']
        SimpleToll_tp_df['simplified_toll_AM']     = SimpleToll_tp_df['simplified_toll']
        SimpleToll_AM_df = SimpleToll_tp_df
        # drop variables that are not needed for subsequent processing
        SimpleToll_AM_df.drop(columns=['DISTANCE','TOLLtp_DA', 'avg_toll_rate','simplified_toll'], inplace=True)
        # temp output 
        output_filename1 = os.path.join(project_dir, output_dir,"average_n_simplified_toll_rate_AM.csv")
        SimpleToll_AM_df.to_csv(output_filename1, header=True, index=False)
    if tp=="MD":
        SimpleToll_tp_df['avg_toll_rate_MD']       = SimpleToll_tp_df['avg_toll_rate']
        SimpleToll_tp_df['simplified_toll_MD']     = SimpleToll_tp_df['simplified_toll']
        SimpleToll_MD_df = SimpleToll_tp_df
        # drop variables that are not needed for subsequent processing
        SimpleToll_MD_df.drop(columns=['DISTANCE','TOLLtp_DA', 'avg_toll_rate','simplified_toll'], inplace=True)
    if tp=="PM":
        SimpleToll_tp_df['avg_toll_rate_PM']       = SimpleToll_tp_df['avg_toll_rate']
        SimpleToll_tp_df['simplified_toll_PM']     = SimpleToll_tp_df['simplified_toll']
        SimpleToll_PM_df = SimpleToll_tp_df
        # drop variables that are not needed for subsequent processing
        SimpleToll_PM_df.drop(columns=['DISTANCE','TOLLtp_DA', 'avg_toll_rate','simplified_toll'], inplace=True)     
    if tp=="EV":
        SimpleToll_tp_df['avg_toll_rate_EV']       = SimpleToll_tp_df['avg_toll_rate']
        SimpleToll_tp_df['simplified_toll_EV']     = SimpleToll_tp_df['simplified_toll']
        SimpleToll_EV_df = SimpleToll_tp_df
        # drop variables that are not needed for subsequent processing
        SimpleToll_EV_df.drop(columns=['DISTANCE','TOLLtp_DA', 'avg_toll_rate','simplified_toll'], inplace=True)

    # get a combination of the 5 data frames
    if tp=="EA":
        SimpleToll_5tp_df =  SimpleToll_EA_df
    if tp=="AM":
        SimpleToll_5tp_df = pd.merge(SimpleToll_5tp_df,
                              SimpleToll_AM_df,
                              how='outer',
                              left_on=['Grouping minor', 'USEtp'], 
                              right_on = ['Grouping minor', 'USEtp'],
                              indicator=False)
    if tp=="MD":
        SimpleToll_5tp_df = pd.merge(SimpleToll_5tp_df,
                              SimpleToll_MD_df,
                              how='outer',
                              left_on=['Grouping minor', 'USEtp'], 
                              right_on = ['Grouping minor', 'USEtp'],
                              indicator=False)
    if tp=="PM":
        SimpleToll_5tp_df = pd.merge(SimpleToll_5tp_df,
                              SimpleToll_PM_df,
                              how='outer',
                              left_on=['Grouping minor', 'USEtp'], 
                              right_on = ['Grouping minor', 'USEtp'],
                              indicator=False)
    if tp=="EV":
        SimpleToll_5tp_df = pd.merge(SimpleToll_5tp_df,
                              SimpleToll_EV_df,
                              how='outer',
                              left_on=['Grouping minor', 'USEtp'], 
                              right_on = ['Grouping minor', 'USEtp'],
                              indicator=False)

        # temp output 
        output_filename1 = os.path.join(project_dir, output_dir,"average_n_simplified_toll_rate_5tp.csv")
        SimpleToll_5tp_df.to_csv(output_filename1, header=True, index=False)

# ------------------
# merge the simple toll df back to a dataframe of toll classes
#-------------------
TollClass_SimpleToll_df = pd.merge(TollclassGrouping_df,
                              SimpleToll_5tp_df,
                              how='outer',
                              left_on=['Grouping minor'], 
                              right_on = ['Grouping minor'],
                              indicator=False)


# keep only the tollclasses and use that are part of the all-lane tolling system i.e. tollclass > 700,000
TollClass_SimpleToll_df = TollClass_SimpleToll_df.loc[TollClass_SimpleToll_df['TOLLCLASS (network links 100plusSeg.shp)'] > 700000]

# keep only the relevant variables
#TollClass_SimpleToll_df = TollClass_SimpleToll_df[['TOLLCLASS (network links 100plusSeg.shp)','USEtp','simplified_toll']] 
    
# temp output 2
output_filename2 = os.path.join(project_dir, output_dir, "tollclass_simpletoll.csv")
TollClass_SimpleToll_df.to_csv(output_filename2, header=True, index=False)
  

#-------------------  
# merge the TollClass_SimpleToll df back to the tolls csv
#-------------------
new_tollscsv_df = pd.merge(tollcsv_df,
                       TollClass_SimpleToll_df,
                       how='left',
                       left_on=['tollclass','use'], 
                       right_on = ['TOLLCLASS (network links 100plusSeg.shp)','USEtp'],
                       indicator=True)

# replace the values
# only use simplified toll value for AM and PM; no tolls for MD
# (when we looked at the results, there aren't many links need to be tolled in thd midday. So it was decided that we do no toll the midday at all.)
TimePeriods = ["AM", "MD", "PM"]
for tp in TimePeriods:
    
    if tp=="AM": 
        new_tollscsv_df["tollam_da"] = np.where(new_tollscsv_df["tollclass"] >= 700000, new_tollscsv_df['simplified_toll_AM'], new_tollscsv_df["tollam_da"])

        # what about two-occupant vehicles?
        # according to the heuristic used in PPA (https://github.com/BayAreaMetro/travel-model-one/tree/master/utilities/toll_calibration),
        # two-occupant vehicles are only charged if drive alone tolls go over $1 per mile. In such cases, two-occupant vehicles is set to have half of the drive alone tolls

        # Three-or-more-occupant vehicles use the express lanes for free.

        # trucks (vsm, sml, med and lrg) are assumed to pay the same toll as da
        new_tollscsv_df["tollam_vsm"] = np.where(new_tollscsv_df["tollclass"] >= 700000, new_tollscsv_df['simplified_toll_AM'], new_tollscsv_df["tollam_vsm"])
        new_tollscsv_df["tollam_sml"] = np.where(new_tollscsv_df["tollclass"] >= 700000, new_tollscsv_df['simplified_toll_AM'], new_tollscsv_df["tollam_sml"])
        new_tollscsv_df["tollam_med"] = np.where(new_tollscsv_df["tollclass"] >= 700000, new_tollscsv_df['simplified_toll_AM'], new_tollscsv_df["tollam_med"])
        new_tollscsv_df["tollam_lrg"] = np.where(new_tollscsv_df["tollclass"] >= 700000, new_tollscsv_df['simplified_toll_AM'], new_tollscsv_df["tollam_lrg"])
    
    if tp=="PM": 
        new_tollscsv_df["tollpm_da"]  = np.where(new_tollscsv_df["tollclass"] >= 700000, new_tollscsv_df['simplified_toll_PM'], new_tollscsv_df["tollpm_da"])
        new_tollscsv_df["tollpm_vsm"] = np.where(new_tollscsv_df["tollclass"] >= 700000, new_tollscsv_df['simplified_toll_PM'], new_tollscsv_df["tollpm_vsm"])
        new_tollscsv_df["tollpm_sml"] = np.where(new_tollscsv_df["tollclass"] >= 700000, new_tollscsv_df['simplified_toll_PM'], new_tollscsv_df["tollpm_sml"])
        new_tollscsv_df["tollpm_med"] = np.where(new_tollscsv_df["tollclass"] >= 700000, new_tollscsv_df['simplified_toll_PM'], new_tollscsv_df["tollpm_med"])
        new_tollscsv_df["tollpm_lrg"] = np.where(new_tollscsv_df["tollclass"] >= 700000, new_tollscsv_df['simplified_toll_PM'], new_tollscsv_df["tollpm_lrg"])


    if tp=="MD":
        if no_tolls_in_midday == "yes": 
            # set midday tolls to zero 
            new_tollscsv_df["tollmd_da"]  = np.where(new_tollscsv_df["tollclass"] >= 700000, 0, new_tollscsv_df["tollpm_da"])
            new_tollscsv_df["tollmd_vsm"] = np.where(new_tollscsv_df["tollclass"] >= 700000, 0, new_tollscsv_df["tollpm_vsm"])
            new_tollscsv_df["tollmd_sml"] = np.where(new_tollscsv_df["tollclass"] >= 700000, 0, new_tollscsv_df["tollpm_sml"])
            new_tollscsv_df["tollmd_med"] = np.where(new_tollscsv_df["tollclass"] >= 700000, 0, new_tollscsv_df["tollpm_med"])
            new_tollscsv_df["tollmd_lrg"] = np.where(new_tollscsv_df["tollclass"] >= 700000, 0, new_tollscsv_df["tollpm_lrg"])
        else: 
            # use simplified tolls from the dynamic toll run
            new_tollscsv_df["tollmd_da"]  = np.where(new_tollscsv_df["tollclass"] >= 700000, new_tollscsv_df['simplified_toll_MD'], new_tollscsv_df["tollpm_da"])
            new_tollscsv_df["tollmd_vsm"] = np.where(new_tollscsv_df["tollclass"] >= 700000, new_tollscsv_df['simplified_toll_MD'], new_tollscsv_df["tollpm_vsm"])
            new_tollscsv_df["tollmd_sml"] = np.where(new_tollscsv_df["tollclass"] >= 700000, new_tollscsv_df['simplified_toll_MD'], new_tollscsv_df["tollpm_sml"])
            new_tollscsv_df["tollmd_med"] = np.where(new_tollscsv_df["tollclass"] >= 700000, new_tollscsv_df['simplified_toll_MD'], new_tollscsv_df["tollpm_med"])
            new_tollscsv_df["tollmd_lrg"] = np.where(new_tollscsv_df["tollclass"] >= 700000, new_tollscsv_df['simplified_toll_MD'], new_tollscsv_df["tollpm_lrg"])

  
# keep only variables that are part of the tolls.csv
new_tollscsv_df = new_tollscsv_df[['facility_name', 'fac_index', 'tollclass', 'tollseg', 'tolltype', 'use', 'tollea_da', 'tollam_da', 'tollmd_da', 'tollpm_da', 'tollev_da', 'tollea_s2', 'tollam_s2', 'tollmd_s2', 'tollpm_s2', 'tollev_s2', 'tollea_s3', 'tollam_s3', 'tollmd_s3', 'tollpm_s3', 'tollev_s3', 'tollea_vsm', 'tollam_vsm', 'tollmd_vsm', 'tollpm_vsm', 'tollev_vsm', 'tollea_sml', 'tollam_sml', 'tollmd_sml', 'tollpm_sml', 'tollev_sml', 'tollea_med', 'tollam_med', 'tollmd_med', 'tollpm_med', 'tollev_med', 'tollea_lrg', 'tollam_lrg', 'tollmd_lrg', 'tollpm_lrg', 'tollev_lrg', 'toll_flat']]

# temp output 3
output_filename3 = os.path.join(project_dir, output_dir, "tolls_simplified.csv")
new_tollscsv_df.to_csv(output_filename3, header=True, index=False)

# need to test this tolls csv - by running just settolls.job