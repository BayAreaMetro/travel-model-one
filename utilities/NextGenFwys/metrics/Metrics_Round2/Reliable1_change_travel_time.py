USAGE = """

  python Reliable1_change_in_travel_time.py

  Run this from the model run dir.
  Processes model outputs and creates csvs for the relevant metric for every relevant scenario, called metrics\\Reliable1_change_in_travel_time_XX.csv
  
  Inputs:
    taz1454_epcPBA50plus_2024_02_23.csv: Lookup file indicating Equity Priority Communitiy (EPC) designation for TAZs, used for classification.
    avgload5period_vehclasses.csv: Roadway network information containing attributes like facility type, volume, and toll class designations.
    ParallelArterialLinks.csv: Lookup file indicating parallel arterial designation for Roadway network, used for classification.
    network_links_TAZ.csv: Lookup table linking network links to Traffic Analysis Zones (TAZ) for geographic analysis.
    goods_routes_a_b.csv: Lookup file indicating goods routes designation for Roadway network, used for classification.
  
  This file will have the following columns:
    'grouping',
    'congested/other',
    'Metric Description',
    'value',
    'Road Type',
    'Model Run ID',
    'Metric ID',
    'Intermediate/Final',
    'Year',
    'taz_epc'
    
  Metrics are:
    1) Reliable 1: Travel time on freeways and parallel local streets in region and EPCs, for people and goods

"""

import os
import pandas as pd
import argparse
import logging
import numpy

# paths
TM1_GIT_DIR             = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
NGFS_MODEL_RUNS_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "ModelRuns_Round2.xlsx")
NGFS_SCENARIOS          = "L:\\Application\\Model_One\\NextGenFwys_Round2\\Scenarios"
NGFS_TOLLCLASS_FILE     = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "TOLLCLASS_Designations.xlsx")

# These calculations are complex enough that a debug log file would be helpful to track what's happening
LOG_FILE                = "Reliable1_change_in_travel_time.log" # in the cwd
LOGGER                  = None # will initialize in main     

# EPC lookup file - indicates whether a TAZ is designated as an EPC in PBA2050+
NGFS_EPC_TAZ_FILE    = "M:\\Application\\Model One\\RTP2025\\INPUT_DEVELOPMENT\\metrics\\metrics_01\\taz1454_epcPBA50plus_2024_02_23.csv"
NGFS_EPC_TAZ_DF      = pd.read_csv(NGFS_EPC_TAZ_FILE)

def calculate_Reliable1_change_travel_time_on_freeways(tm_run_id: str) -> pd.DataFrame:  
    """ Calculates Reliable 1: Change in travel time on freeway and non-freeway facilities

    Args:
        tm_run_id (str): Travel model run ID
    
    Returns:
        pd.DataFrame: with columns including
          Metric ID          = 'Reliable 1'
          Model Run ID        = tm_run_id
          Intermediate/Final = final
        Metrics return:
          Freeway/Non-Freeway               Facility Type Definition               Metric Description
          Freeway|Non-Freeway               EPCs|Non-EPCs|Region                   Travel Time                      (EPC/non-EPC breakdown)

    Notes: Uses
    * avgload5period.csv (for facility type breakdown)
    """
    METRIC_ID = 'Reliable 1'
    LOGGER.info("Calculating {} for {}".format(METRIC_ID, tm_run_id))

    loaded_network_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "avgload5period_vehclasses.csv")    
    loaded_network_df = pd.read_csv(loaded_network_file)
    loaded_network_df.rename(columns=lambda x: x.strip(), inplace=True)
    loaded_network_df['vmtAM_tot'] = loaded_network_df['distance'] * loaded_network_df['volAM_tot']
    LOGGER.info("  Read {:,} rows from {}".format(len(loaded_network_df), loaded_network_file))
    LOGGER.debug("  Columns:".format(list(loaded_network_df.columns)))
    LOGGER.debug("loaded_network_df =\n{}".format(loaded_network_df))
    loaded_network_df = loaded_network_df.loc[(loaded_network_df['useAM'] == 1)&(loaded_network_df['ft'] != 6)]
    
    # join to tolled minor group freeway links lookup table 
    loaded_network_df = pd.merge(left=loaded_network_df, right=TOLLED_FWY_MINOR_GROUP_LINKS_DF, how='left', left_on=['a','b'], right_on=['a','b'])

    # compute Fwy and Non_Fwy travel time    
    # fill empty collumns of DF with a string to retain all values in the DF
    loaded_network_df.grouping = loaded_network_df.grouping.fillna('NA')
    loaded_network_df.grouping_dir = loaded_network_df.grouping_dir.fillna('NA')

    ctim_metrics_df = loaded_network_df.groupby(by=['grouping', 'grouping_dir']).agg({'ctimAM':'sum', \
                                                                                    'ctimPM':'sum',\
                                                                                    'distance':'sum',\
                                                                                    'vmtAM_tot':'sum'}).reset_index()

    ctim_metrics_df['vmt_weighted_ctimAM'] = ctim_metrics_df['vmtAM_tot'] * ctim_metrics_df['ctimAM']

    LOGGER.debug("ctim_metrics_df:\n{}".format(ctim_metrics_df))
    
    ctimAM_metrics_df = ctim_metrics_df.loc[(ctim_metrics_df.grouping_dir == 'AM'), ['grouping', 'ctimAM', 'distance', 'vmtAM_tot', 'vmt_weighted_ctimAM']]
    ctimPM_metrics_df = ctim_metrics_df.loc[(ctim_metrics_df.grouping_dir == 'PM'), ['grouping', 'ctimPM']]
    ctim_df = pd.merge(left=ctimAM_metrics_df, right=ctimPM_metrics_df, how='left', left_on=['grouping'], right_on=['grouping'])
    ctim_df['AVGctimPEAK'] = (ctim_df['ctimAM'] + ctim_df['ctimPM'])/2

    # add row for averages from the corridors
    average_values = ctim_df.select_dtypes(include=['number']).mean()
    # Convert the Pandas Series to a DataFrame
    average_df = pd.DataFrame([average_values])
    average_df['grouping'] = 'Simple Average from Corridors'
    # add row for sum of values 
    sum_of_values = ctim_df.select_dtypes(include=['number']).sum()
    # convert pandas series to a dataframe
    sum_df = pd.DataFrame([sum_of_values])
    sum_df['grouping'] = 'Sum of Values for Weighted Average'
    
    # add column for congested vs other segments then take average for both groupings
    ctim_df = pd.merge(left = ctim_df, right = TOLLED_FWY_CONGESTED_LINKS_DF, how = 'left', left_on = ['grouping'], right_on = ['grouping'])
    # filter out the congested segments
    congested_segments_df = ctim_df.loc[ctim_df['congested/other'] == 'congested segment']
    # add row for the averages from the congested segments
    congested_segments_average_values = congested_segments_df.select_dtypes(include=['number']).mean()
    # convert the pandas series to a dataframe
    congested_segments_average_df = pd.DataFrame([congested_segments_average_values])
    congested_segments_average_df['grouping'] = 'Simple Average of Congested Segments'
    
    # filter out the other segments
    other_segments_df = ctim_df.loc[ctim_df['congested/other'] == 'other segment']
    # add row for the averages from the congested segments
    other_segments_average_values = other_segments_df.select_dtypes(include=['number']).mean()
    # convert the pandas series to a dataframe
    other_segments_average_df = pd.DataFrame([other_segments_average_values])
    other_segments_average_df['grouping'] = 'Simple Average of Other Segments'

    # combine all DFs together
    ctim_df = pd.concat([ctim_df, sum_df, congested_segments_average_df, other_segments_average_df, average_df], ignore_index=True)

    # add column post summation for weighted average
    ctim_df['VMTweightedAVG_ctimAM'] = ctim_df['vmt_weighted_ctimAM'] / ctim_df['vmtAM_tot']

    # put it together, move to long form and return
    fwy_travel_times_df = ctim_df
    fwy_travel_times_df = fwy_travel_times_df.melt(id_vars=['grouping', 'congested/other'], var_name='Metric Description')
    fwy_travel_times_df['Road Type'] = 'Congested Freeway'
    fwy_travel_times_df['Model Run ID'] = tm_run_id
    fwy_travel_times_df['Metric ID'] = METRIC_ID
    fwy_travel_times_df['Intermediate/Final'] = 'final'
    # identify extra, intermediate, or debug steps for easy filtering
    fwy_travel_times_df.loc[(fwy_travel_times_df['Metric Description'].str.contains('distance') == True), 'Intermediate/Final'] = 'Extra'
    fwy_travel_times_df.loc[(fwy_travel_times_df['Metric Description'].str.contains('vmtAM_tot') == True), 'Intermediate/Final'] = 'Intermediate'
    fwy_travel_times_df.loc[(fwy_travel_times_df['Metric Description'].str.contains('vmt_weighted_ctimAM') == True), 'Intermediate/Final'] = 'Intermediate'
    fwy_travel_times_df.loc[(fwy_travel_times_df['grouping'].str.contains('Sum of Values for Weighted Average') == False) & (fwy_travel_times_df['Metric Description'].str.contains('VMTweightedAVG_ctimAM') == True), 'Intermediate/Final'] = 'Debug Step'
    fwy_travel_times_df.loc[(fwy_travel_times_df['grouping'].str.contains('Sum of Values for Weighted Average') == True) & (fwy_travel_times_df['Metric Description'].str.contains('VMTweightedAVG_ctimAM') == False), 'Intermediate/Final'] = 'Debug Step'
    fwy_travel_times_df.loc[(fwy_travel_times_df['grouping'].str.contains('Congested Segment') == True), 'congested/other'] = 'congested segment'
    fwy_travel_times_df.loc[(fwy_travel_times_df['grouping'].str.contains('Other Segment') == True), 'congested/other'] = 'other segment'

    fwy_travel_times_df['Year'] = tm_run_id[:4]
    LOGGER.debug("fwy_travel_times_df for reliable 1:\n{}".format(fwy_travel_times_df))

    return fwy_travel_times_df

def calculate_Reliable1_change_travel_time_on_parallel_arterials(tm_run_id: str) -> pd.DataFrame:  
    """ Calculates Reliable 1: Change in travel time on parallel arterials

    Args:
        tm_run_id (str): Travel model run ID
    
    Returns:
        pd.DataFrame: with columns including
          Metric ID          = 'Reliable 1'
          Model Run ID        = tm_run_id
          Intermediate/Final = final
        Metrics return:
          Freeway/Non-Freeway               Facility Type Definition               Metric Description
          Freeway|Non-Freeway               EPCs|Non-EPCs|Region                   Travel Time                      (EPC/non-EPC breakdown)

    Notes: Uses
    * avgload5period.csv (for facility type breakdown)
    """
    METRIC_ID = 'Reliable 1'
    LOGGER.info("Calculating {} for {}".format(METRIC_ID, tm_run_id))

    loaded_network_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "avgload5period_vehclasses.csv")
    loaded_network_df = pd.read_csv(loaded_network_file)
    loaded_network_df.rename(columns=lambda x: x.strip(), inplace=True)
    loaded_network_df['vmtAM_tot'] = loaded_network_df['distance'] * loaded_network_df['volAM_tot']
    LOGGER.info("  Read {:,} rows from {}".format(len(loaded_network_df), loaded_network_file))
    LOGGER.debug("  Columns:".format(list(loaded_network_df.columns)))
    LOGGER.debug("loaded_network_df =\n{}".format(loaded_network_df))
    loaded_network_df = loaded_network_df.loc[(loaded_network_df['useAM'] == 1)&(loaded_network_df['ft'] != 6)]
    
    # join to parallel arterial links lookup table
    parallel_arterials_file = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "metrics", "Metrics_Round2", "Input Files", "ParallelArterialLinks.csv")
    parallel_arterials_links_df = pd.read_csv(parallel_arterials_file)
    parallel_arterials_links_df.rename(columns=lambda x: x.strip(), inplace=True)
    parallel_arterials_links_df.rename(columns={"A":"a", "B":"b"}, inplace=True)
    # split 'Parallel_Corridor' to 'grouping' (now without direction) and 'grouping_dir'
    parallel_arterials_links_df['grouping_dir'] = parallel_arterials_links_df['Parallel_Corridor'].str[-2:]
    parallel_arterials_links_df['grouping']     = parallel_arterials_links_df['Parallel_Corridor'].str[:-3]
    loaded_network_df = pd.merge(left=loaded_network_df, right=parallel_arterials_links_df, how='left', left_on=['a','b'], right_on=['a','b'])

    # compute Fwy and Non_Fwy travel time    
    # fill empty collumns of DF with a string to retain all values in the DF
    loaded_network_df.grouping = loaded_network_df.grouping.fillna('NA')
    loaded_network_df.grouping_dir = loaded_network_df.grouping_dir.fillna('NA')

    ctim_metrics_df = loaded_network_df.groupby(by=['grouping', 'grouping_dir']).agg({'ctimAM':'sum', \
                                                                                    'ctimPM':'sum',\
                                                                                    'distance':'sum',\
                                                                                    'vmtAM_tot':'sum'}).reset_index()

    ctim_metrics_df['vmt_weighted_ctimAM'] = ctim_metrics_df['vmtAM_tot'] * ctim_metrics_df['ctimAM']

    LOGGER.debug("ctim_metrics_df:\n{}".format(ctim_metrics_df))
    
    ctimAM_metrics_df = ctim_metrics_df.loc[(ctim_metrics_df.grouping_dir == 'AM'), ['grouping', 'ctimAM', 'distance', 'vmtAM_tot', 'vmt_weighted_ctimAM']]
    # TODO: replace this hardcoded solution to using the same links for 2 corridors
    # Specify the conditions for filtering
    column_grouping_condition = 'SanMateo_101_AM_SanMateo_28092'
    # Filter the DataFrame based on conditions
    filtered_rows = ctimAM_metrics_df[(ctimAM_metrics_df['grouping'] == column_grouping_condition)]

    # Check if any rows meet the conditions
    if not filtered_rows.empty:
        # Assuming only one row matches the conditions, if multiple rows can match, handle accordingly
        row_to_duplicate = filtered_rows
        
        # Modify 'grouping' column value in the original row
        ctimAM_metrics_df.loc[filtered_rows.index, 'grouping'] = 'SanMateo_101'
        
        # Modify 'grouping' column value in the copied row
        row_to_duplicate_copy = row_to_duplicate.copy()
        row_to_duplicate_copy['grouping'] = 'SanMateo_28092'
        
        # Concatenate the DataFrame with the modified copied row
        ctimAM_metrics_df = pd.concat([ctimAM_metrics_df, row_to_duplicate_copy], ignore_index=True)
        print("Row duplicated and added to DataFrame.")
    else:
        print("No rows found matching the specified conditions.")
        
    ctimPM_metrics_df = ctim_metrics_df.loc[(ctim_metrics_df.grouping_dir == 'PM'), ['grouping', 'ctimPM']]
    # TODO: replace this hardcoded solution to using the same links for 2 corridors
    # Specify the conditions for filtering
    column_grouping_condition = 'SanMateo_101_PM_SanMateo_28092'
    # Filter the DataFrame based on conditions
    filtered_rows = ctimPM_metrics_df[(ctimPM_metrics_df['grouping'] == column_grouping_condition)]

    LOGGER.debug("filtered_rows:\n{}".format(filtered_rows))

    # Check if any rows meet the conditions
    if not filtered_rows.empty:
        # Assuming only one row matches the conditions, if multiple rows can match, handle accordingly
        row_to_duplicate = filtered_rows
        
        # Modify 'grouping' column value in the original row
        ctimPM_metrics_df.loc[filtered_rows.index, 'grouping'] = 'SanMateo_101'
        
        # Modify 'grouping' column value in the copied row
        row_to_duplicate_copy = row_to_duplicate.copy()
        row_to_duplicate_copy['grouping'] = 'SanMateo_28092'
        
        # Concatenate the DataFrame with the modified copied row
        ctimPM_metrics_df = pd.concat([ctimPM_metrics_df, row_to_duplicate_copy], ignore_index=True)
        print("Row duplicated and added to DataFrame.")
    else:
        print("No rows found matching the specified conditions.")
        
    # merge the dataframes with different peak directions/periods
    ctim_df = pd.merge(left=ctimAM_metrics_df, right=ctimPM_metrics_df, how='left', left_on=['grouping'], right_on=['grouping'])
    ctim_df['AVGctimPEAK'] = (ctim_df['ctimAM'] + ctim_df['ctimPM'])/2

    # add row for averages from the corridors
    average_values = ctim_df.select_dtypes(include=['number']).mean()
    # Convert the Pandas Series to a DataFrame
    average_df = pd.DataFrame([average_values])
    average_df['grouping'] = 'Simple Average from Corridors'
    # add row for sum of values 
    sum_of_values = ctim_df.select_dtypes(include=['number']).sum()
    # convert pandas series to a dataframe
    sum_df = pd.DataFrame([sum_of_values])
    sum_df['grouping'] = 'Sum of Values for Weighted Average'
    
    # add column for congested vs other segments then take average for both groupings
    ctim_df = pd.merge(left = ctim_df, right = TOLLED_FWY_CONGESTED_LINKS_DF, how = 'left', left_on = ['grouping'], right_on = ['grouping'])
    # filter out the congested segments
    congested_segments_df = ctim_df.loc[ctim_df['congested/other'] == 'congested segment']
    # add row for the averages from the congested segments
    congested_segments_average_values = congested_segments_df.select_dtypes(include=['number']).mean()
    # convert the pandas series to a dataframe
    congested_segments_average_df = pd.DataFrame([congested_segments_average_values])
    congested_segments_average_df['grouping'] = 'Simple Average of Congested Segments'
    
    # filter out the other segments
    other_segments_df = ctim_df.loc[ctim_df['congested/other'] == 'other segment']
    # add row for the averages from the congested segments
    other_segments_average_values = other_segments_df.select_dtypes(include=['number']).mean()
    # convert the pandas series to a dataframe
    other_segments_average_df = pd.DataFrame([other_segments_average_values])
    other_segments_average_df['grouping'] = 'Simple Average of Other Segments'

    # combine all DFs together
    ctim_df = pd.concat([ctim_df, sum_df, congested_segments_average_df, other_segments_average_df, average_df], ignore_index=True)

    # add column post summation for weighted average
    ctim_df['VMTweightedAVG_ctimAM'] = ctim_df['vmt_weighted_ctimAM'] / ctim_df['vmtAM_tot']

    # put it together, move to long form and return
    parallel_arterials_travel_times_df = ctim_df
    parallel_arterials_travel_times_df = parallel_arterials_travel_times_df.melt(id_vars=['grouping', 'congested/other'], var_name='Metric Description')
    parallel_arterials_travel_times_df['Road Type'] = 'Parallel Arterials'
    parallel_arterials_travel_times_df['Model Run ID'] = tm_run_id
    parallel_arterials_travel_times_df['Metric ID'] = METRIC_ID
    parallel_arterials_travel_times_df['Intermediate/Final'] = 'final'
    # identify extra, intermediate, or debug steps for easy filtering
    parallel_arterials_travel_times_df.loc[(parallel_arterials_travel_times_df['Metric Description'].str.contains('distance') == True), 'Intermediate/Final'] = 'Extra'
    parallel_arterials_travel_times_df.loc[(parallel_arterials_travel_times_df['Metric Description'].str.contains('vmtAM_tot') == True), 'Intermediate/Final'] = 'Intermediate'
    parallel_arterials_travel_times_df.loc[(parallel_arterials_travel_times_df['Metric Description'].str.contains('vmt_weighted_ctimAM') == True), 'Intermediate/Final'] = 'Intermediate'
    parallel_arterials_travel_times_df.loc[(parallel_arterials_travel_times_df['grouping'].str.contains('Sum of Values for Weighted Average') == False) & (parallel_arterials_travel_times_df['Metric Description'].str.contains('VMTweightedAVG_ctimAM') == True), 'Intermediate/Final'] = 'Debug Step'
    parallel_arterials_travel_times_df.loc[(parallel_arterials_travel_times_df['grouping'].str.contains('Sum of Values for Weighted Average') == True) & (parallel_arterials_travel_times_df['Metric Description'].str.contains('VMTweightedAVG_ctimAM') == False), 'Intermediate/Final'] = 'Debug Step'
    parallel_arterials_travel_times_df.loc[(parallel_arterials_travel_times_df['grouping'].str.contains('Congested Segment') == True), 'congested/other'] = 'congested segment'
    parallel_arterials_travel_times_df.loc[(parallel_arterials_travel_times_df['grouping'].str.contains('Other Segment') == True), 'congested/other'] = 'other segment'
    
    parallel_arterials_travel_times_df['Year'] = tm_run_id[:4]
    LOGGER.debug("parallel_arterials_travel_times_df for reliable 1:\n{}".format(parallel_arterials_travel_times_df))

    return parallel_arterials_travel_times_df

def calculate_Reliable1_change_travel_time_on_parallel_arterials_epc_non(tm_run_id: str) -> pd.DataFrame:  
    """ Calculates Reliable 1: Change in travel time on parallel arterials

    Args:
        tm_run_id (str): Travel model run ID
    
    Returns:
        pd.DataFrame: with columns including
          Metric ID          = 'Reliable 1'
          Model Run ID        = tm_run_id
          Intermediate/Final = final
        Metrics return:
          Freeway/Non-Freeway               Facility Type Definition               Metric Description
          Freeway|Non-Freeway               EPCs|Non-EPCs|Region                   Travel Time                      (EPC/non-EPC breakdown)

    Notes: Uses
    * avgload5period.csv (for facility type breakdown)
    """
    METRIC_ID = 'Reliable 1'
    LOGGER.info("Calculating {} for {}".format(METRIC_ID, tm_run_id))

    loaded_network_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "avgload5period_vehclasses.csv")
    loaded_network_df = pd.read_csv(loaded_network_file)
    loaded_network_df.rename(columns=lambda x: x.strip(), inplace=True)
    loaded_network_df['vmtAM_tot'] = loaded_network_df['distance'] * loaded_network_df['volAM_tot']
    LOGGER.info("  Read {:,} rows from {}".format(len(loaded_network_df), loaded_network_file))
    LOGGER.debug("  Columns:".format(list(loaded_network_df.columns)))
    LOGGER.debug("loaded_network_df =\n{}".format(loaded_network_df))
    loaded_network_df = loaded_network_df.loc[(loaded_network_df['useAM'] == 1)&(loaded_network_df['ft'] != 6)]
    
    # join to parallel arterial links lookup table
    parallel_arterials_file = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "metrics", "Metrics_Round2", "Input Files", "ParallelArterialLinks.csv")
    parallel_arterials_links_df = pd.read_csv(parallel_arterials_file)
    parallel_arterials_links_df.rename(columns=lambda x: x.strip(), inplace=True)
    parallel_arterials_links_df.rename(columns={"A":"a", "B":"b"}, inplace=True)
    # split 'Parallel_Corridor' to 'grouping' (now without direction) and 'grouping_dir'
    parallel_arterials_links_df['grouping_dir'] = parallel_arterials_links_df['Parallel_Corridor'].str[-2:]
    parallel_arterials_links_df['grouping']     = parallel_arterials_links_df['Parallel_Corridor'].str[:-3]
    loaded_network_df = pd.merge(left=loaded_network_df, right=parallel_arterials_links_df, how='left', left_on=['a','b'], right_on=['a','b'])
    
    # load network_links_TAZ.csv as lookup df to use for equity metric:
    #     --> calculate VMT for arterial road links in EPCs vs region
    #         --> tolled aerterials within EPCs 
    # load network link to TAZ lookup file

    tm_network_links_taz_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "shapefile", "network_links_TAZ.csv")
    tm_network_links_taz_df = pd.read_csv(tm_network_links_taz_file)[['A', 'B', 'TAZ1454', 'linktaz_share']]
    LOGGER.info("  Read {:,} rows from {}".format(len(tm_network_links_taz_df), tm_network_links_taz_file))
    # join to epc lookup table
    tm_network_links_with_epc_df = pd.merge(
        left=tm_network_links_taz_df,
        right=NGFS_EPC_TAZ_DF,
        left_on="TAZ1454",
        right_on="TAZ1454",
        how='left')
    tm_network_links_with_epc_df = tm_network_links_with_epc_df.sort_values('linktaz_share', ascending=False).drop_duplicates(['A', 'B']).sort_index()
    LOGGER.debug("tm_network_links_with_epc_df =\n{}".format(tm_network_links_with_epc_df))
    
    loaded_network_df = pd.merge(left= loaded_network_df, right= tm_network_links_with_epc_df, left_on= ['a','b'], right_on= ['A', 'B'], how='left')
    LOGGER.debug("loaded_network_df =\n{}".format(loaded_network_df))

    # compute Fwy and Non_Fwy travel time    
    # fill empty collumns of DF with a string to retain all values in the DF
    loaded_network_df.grouping = loaded_network_df.grouping.fillna('NA')
    loaded_network_df.grouping_dir = loaded_network_df.grouping_dir.fillna('NA')

    ctim_metrics_df = loaded_network_df.groupby(by=['grouping', 'grouping_dir', 'taz_epc']).agg({'ctimAM':'sum', \
                                                                                    'ctimPM':'sum',\
                                                                                    'distance':'sum',\
                                                                                    'vmtAM_tot':'sum'}).reset_index()

    ctim_metrics_df['vmt_weighted_ctimAM'] = ctim_metrics_df['vmtAM_tot'] * ctim_metrics_df['ctimAM']

    LOGGER.debug("ctim_metrics_df:\n{}".format(ctim_metrics_df))
    
    ctimAM_metrics_df = ctim_metrics_df.loc[(ctim_metrics_df.grouping_dir == 'AM'), ['grouping', 'taz_epc', 'ctimAM', 'distance', 'vmtAM_tot', 'vmt_weighted_ctimAM']]
    # TODO: replace this hardcoded solution to using the same links for 2 corridors
    # Specify the conditions for filtering
    column_grouping_condition = 'SanMateo_101_AM_SanMateo_28092'
    # Filter the DataFrame based on conditions
    filtered_rows = ctimAM_metrics_df[(ctimAM_metrics_df['grouping'] == column_grouping_condition)]

    LOGGER.debug("filtered_rows:\n{}".format(filtered_rows))

    # Check if any rows meet the conditions
    if not filtered_rows.empty:
        # Assuming only one row matches the conditions, if multiple rows can match, handle accordingly
        row_to_duplicate = filtered_rows
        
        # Modify 'grouping' column value in the original row
        ctimAM_metrics_df.loc[filtered_rows.index, 'grouping'] = 'SanMateo_101'
        
        # Modify 'grouping' column value in the copied row
        row_to_duplicate_copy = row_to_duplicate.copy()
        row_to_duplicate_copy['grouping'] = 'SanMateo_28092'
        
        # Concatenate the DataFrame with the modified copied row
        ctimAM_metrics_df = pd.concat([ctimAM_metrics_df, row_to_duplicate_copy], ignore_index=True)
        print("Row duplicated and added to DataFrame.")
    else:
        print("No rows found matching the specified conditions.")
        
    ctimPM_metrics_df = ctim_metrics_df.loc[(ctim_metrics_df.grouping_dir == 'PM'), ['grouping', 'taz_epc', 'ctimPM']]
    # TODO: replace this hardcoded solution to using the same links for 2 corridors
    # Specify the conditions for filtering
    column_grouping_condition = 'SanMateo_101_PM_SanMateo_28092'
    # Filter the DataFrame based on conditions
    filtered_rows = ctimPM_metrics_df[(ctimPM_metrics_df['grouping'] == column_grouping_condition)]

    LOGGER.debug("filtered_rows:\n{}".format(filtered_rows))

    # Check if any rows meet the conditions
    if not filtered_rows.empty:
        # Assuming only one row matches the conditions, if multiple rows can match, handle accordingly
        row_to_duplicate = filtered_rows
        
        # Modify 'grouping' column value in the original row
        ctimPM_metrics_df.loc[filtered_rows.index, 'grouping'] = 'SanMateo_101'
        
        # Modify 'grouping' column value in the copied row
        row_to_duplicate_copy = row_to_duplicate.copy()
        row_to_duplicate_copy['grouping'] = 'SanMateo_28092'
        
        # Concatenate the DataFrame with the modified copied row
        ctimPM_metrics_df = pd.concat([ctimPM_metrics_df, row_to_duplicate_copy], ignore_index=True)
        print("Row duplicated and added to DataFrame.")
    else:
        print("No rows found matching the specified conditions.")
        
    # merge the dataframes with different peak directions/periods
    ctim_df = pd.merge(left=ctimAM_metrics_df, right=ctimPM_metrics_df, how='left', left_on=['grouping', 'taz_epc'], right_on=['grouping', 'taz_epc'])
    ctim_df['AVGctimPEAK'] = (ctim_df['ctimAM'] + ctim_df['ctimPM'])/2
    
    # take average for taz vs non segments 
    # filter out the taz segments
    EPC_segments_df = ctim_df.loc[ctim_df['taz_epc'] == 1]
    # add row for the averages from the EPC segments
    EPC_segments_average_values = EPC_segments_df.select_dtypes(include=['number']).mean()
    # convert the pandas series to a dataframe
    EPC_segments_average_df = pd.DataFrame([EPC_segments_average_values])
    EPC_segments_average_df['grouping'] = 'Simple Average of EPC Segments'
    
    # filter out the non segments
    NonEPC_segments_df = ctim_df.loc[ctim_df['taz_epc'] == 0]
    # add row for the averages from the EPC segments
    NonEPC_segments_average_values = NonEPC_segments_df.select_dtypes(include=['number']).mean()
    # convert the pandas series to a dataframe
    NonEPC_segments_average_df = pd.DataFrame([NonEPC_segments_average_values])
    NonEPC_segments_average_df['grouping'] = 'Simple Average of NonEPC Segments'

    # combine all DFs together
    ctim_df = pd.concat([ctim_df, EPC_segments_average_df, NonEPC_segments_average_df], ignore_index=True)

    # put it together, move to long form and return
    parallel_arterials_travel_times_df = ctim_df
    parallel_arterials_travel_times_df = parallel_arterials_travel_times_df.melt(id_vars=['grouping', 'taz_epc'], var_name='Metric Description')
    parallel_arterials_travel_times_df['Road Type'] = 'Parallel Arterials'
    parallel_arterials_travel_times_df['Model Run ID'] = tm_run_id
    parallel_arterials_travel_times_df['Metric ID'] = METRIC_ID
    parallel_arterials_travel_times_df['Intermediate/Final'] = 'final'
    # identify extra, intermediate, or debug steps for easy filtering
    parallel_arterials_travel_times_df.loc[(parallel_arterials_travel_times_df['Metric Description'].str.contains('distance') == True), 'Intermediate/Final'] = 'Extra'
    parallel_arterials_travel_times_df.loc[(parallel_arterials_travel_times_df['Metric Description'].str.contains('vmtAM_tot') == True), 'Intermediate/Final'] = 'Intermediate'
    parallel_arterials_travel_times_df.loc[(parallel_arterials_travel_times_df['Metric Description'].str.contains('vmt_weighted_ctimAM') == True), 'Intermediate/Final'] = 'Intermediate'
    parallel_arterials_travel_times_df.loc[(parallel_arterials_travel_times_df['grouping'].str.contains('Sum of Values for Weighted Average') == False) & (parallel_arterials_travel_times_df['Metric Description'].str.contains('VMTweightedAVG_ctimAM') == True), 'Intermediate/Final'] = 'Debug Step'
    parallel_arterials_travel_times_df.loc[(parallel_arterials_travel_times_df['grouping'].str.contains('Sum of Values for Weighted Average') == True) & (parallel_arterials_travel_times_df['Metric Description'].str.contains('VMTweightedAVG_ctimAM') == False), 'Intermediate/Final'] = 'Debug Step'
    parallel_arterials_travel_times_df.loc[(parallel_arterials_travel_times_df['grouping'].str.contains('EPC Segment') == True), 'taz_epc'] = 'EPC segment'
    parallel_arterials_travel_times_df.loc[(parallel_arterials_travel_times_df['grouping'].str.contains('NonEPC Segment') == True), 'taz_epc'] = 'NonEPC segment'
    parallel_arterials_travel_times_df.loc[parallel_arterials_travel_times_df['taz_epc'] == 1, 'taz_epc'] = 'EPC segment'
    parallel_arterials_travel_times_df.loc[parallel_arterials_travel_times_df['taz_epc'] == 0, 'taz_epc'] = 'NonEPC segment'
    
    parallel_arterials_travel_times_df['Year'] = tm_run_id[:4]
    LOGGER.debug("parallel_arterials_travel_times_df for reliable 1:\n{}".format(parallel_arterials_travel_times_df))

    return parallel_arterials_travel_times_df

def calculate_Reliable1_change_travel_time_on_GoodsRoutes(tm_run_id: str) -> pd.DataFrame:  
    """ Calculates Reliable 1: Change in travel time on goods routes and other corridors

    Args:
        tm_run_id (str): Travel model run ID
    
    Returns:
        pd.DataFrame: with columns including
          Metric ID          = 'Reliable 1'
          Model Run ID        = tm_run_id
          Intermediate/Final = final
        Metrics return:
          goods routes and other corridors                             Metric Description
          goods routes and other corridors                             Travel Time       

    Notes: Uses
    * avgload5period.csv (for facility type breakdown)
    """
    
    METRIC_ID = 'Reliable 1'
    LOGGER.info("Calculating {} for {}".format(METRIC_ID, tm_run_id))

    loaded_network_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "avgload5period_vehclasses.csv")
    loaded_network_df = pd.read_csv(loaded_network_file)
    loaded_network_df.rename(columns=lambda x: x.strip(), inplace=True)
    loaded_network_df['vmtAM_tot'] = loaded_network_df['distance'] * loaded_network_df['volAM_tot']
    LOGGER.info("  Read {:,} rows from {}".format(len(loaded_network_df), loaded_network_file))
    LOGGER.debug("  Columns:".format(list(loaded_network_df.columns)))
    LOGGER.debug("loaded_network_df =\n{}".format(loaded_network_df))

    goods_routes_a_b_links_file = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "metrics", "Metrics_Round2", "Input Files", "goods_routes_a_b.csv")
    goods_routes_a_b_links_df = pd.read_csv(goods_routes_a_b_links_file)
    goods_routes_a_b_links_df.rename(columns={"A":"a", "B":"b"}, inplace=True)
    # merge loaded network with df containing route information
    # remove HOV lanes from the network
    loaded_network_with_goods_routes_df = loaded_network_df.loc[(loaded_network_df['useAM'] ==1)]
    # loaded_network_with_goods_routes_df = loaded_network_with_goods_routes_df[['a','b','ctimAM','ctimPM']]
    loaded_network_with_goods_routes_df = pd.merge(left=loaded_network_with_goods_routes_df, right=goods_routes_a_b_links_df, how='left', left_on=['a','b'], right_on=['a','b'])    
    loaded_network_with_goods_routes_df = loaded_network_with_goods_routes_df.melt(id_vars=['a','b','ctimAM','ctimPM', 'distance', 'vmtAM_tot'], var_name='grouping', value_name='time_period')  
    loaded_network_with_goods_routes_df = loaded_network_with_goods_routes_df.groupby(by=['grouping', 'time_period']).agg({'ctimAM':'sum', \
                                                                                'ctimPM':'sum',\
                                                                                'distance':'sum',\
                                                                                'vmtAM_tot':'sum'}).reset_index()

    loaded_network_with_goods_routes_df['vmt_weighted_ctimAM'] = loaded_network_with_goods_routes_df['vmtAM_tot'] * loaded_network_with_goods_routes_df['ctimAM']

    ctimAM_metrics_df = loaded_network_with_goods_routes_df.loc[(loaded_network_with_goods_routes_df.time_period == 'AM'), ['grouping', 'ctimAM', 'distance', 'vmtAM_tot', 'vmt_weighted_ctimAM']]
    ctimPM_metrics_df = loaded_network_with_goods_routes_df.loc[(loaded_network_with_goods_routes_df.time_period == 'PM'), ['grouping', 'ctimPM']]
    ctim_df = pd.merge(left=ctimAM_metrics_df, right=ctimPM_metrics_df, how='left', left_on=['grouping'], right_on=['grouping'])
    ctim_df['AVGctimPEAK'] = (ctim_df['ctimAM'] + ctim_df['ctimPM'])/2

    # add row for averages from the goods routes
    ctim_df = ctim_df.loc[(ctim_df['grouping'].str.contains('Port') == True)]
    average_values_from_goodsroutes = ctim_df.select_dtypes(include=['number']).mean()
    # Convert the Pandas Series to a DataFrame
    average_from_goodsroutes_df = pd.DataFrame([average_values_from_goodsroutes])
    average_from_goodsroutes_df['grouping'] = 'Simple Average from Goods Routes'

    # add row for sum of values 
    sum_of_values = ctim_df.select_dtypes(include=['number']).sum()
    # convert pandas series to a dataframe
    sum_df = pd.DataFrame([sum_of_values])
    sum_df['grouping'] = 'Sum of Values for Weighted Average'
    ctim_df = pd.concat([ctim_df, sum_df, average_from_goodsroutes_df], ignore_index=True)

    # add column post summation for weighted average
    ctim_df['VMTweightedAVG_ctimAM'] = ctim_df['vmt_weighted_ctimAM'] / ctim_df['vmtAM_tot']

    # put it together, move to long form and return
    grouping_travel_times_df = ctim_df
    grouping_travel_times_df = grouping_travel_times_df.melt(id_vars=['grouping'], var_name='Metric Description')
    grouping_travel_times_df['Road Type'] = 'Goods Routes'
    LOGGER.debug("grouping_travel_times_df =\n{}".format(grouping_travel_times_df))
    # filter out other corridors data, if present
    grouping_travel_times_df = grouping_travel_times_df.loc[(grouping_travel_times_df['Road Type'] == 'Goods Routes')]
    grouping_travel_times_df['Model Run ID'] = tm_run_id
    grouping_travel_times_df['Metric ID'] = METRIC_ID
    grouping_travel_times_df['Intermediate/Final'] = 'final'
    # identify extra, intermediate, or debug steps for easy filtering
    grouping_travel_times_df.loc[(grouping_travel_times_df['Metric Description'].str.contains('distance') == True), 'Intermediate/Final'] = 'Extra'
    grouping_travel_times_df.loc[(grouping_travel_times_df['Metric Description'].str.contains('vmtAM_tot') == True), 'Intermediate/Final'] = 'Intermediate'
    grouping_travel_times_df.loc[(grouping_travel_times_df['Metric Description'].str.contains('vmt_weighted_ctimAM') == True), 'Intermediate/Final'] = 'Intermediate'
    grouping_travel_times_df.loc[(grouping_travel_times_df['grouping'].str.contains('Sum of Values for Weighted Average') == False) & (grouping_travel_times_df['Metric Description'].str.contains('VMTweightedAVG_ctimAM') == True), 'Intermediate/Final'] = 'Debug Step'
    grouping_travel_times_df.loc[(grouping_travel_times_df['grouping'].str.contains('Sum of Values for Weighted Average') == True) & (grouping_travel_times_df['Metric Description'].str.contains('VMTweightedAVG_ctimAM') == False), 'Intermediate/Final'] = 'Debug Step'

    grouping_travel_times_df['Year'] = tm_run_id[:4]
    LOGGER.debug("grouping_travel_times_df for reliable 1:\n{}".format(grouping_travel_times_df))

    return grouping_travel_times_df

def calculate_Reliable1_change_travel_time_on_Othercorridors(tm_run_id: str) -> pd.DataFrame:  
    """ Calculates Reliable 1: Change in travel time on goods routes and other corridors

    Args:
        tm_run_id (str): Travel model run ID
    
    Returns:
        pd.DataFrame: with columns including
          Metric ID          = 'Reliable 1'
          Model Run ID        = tm_run_id
          Intermediate/Final = final
        Metrics return:
          goods routes and other corridors                             Metric Description
          goods routes and other corridors                             Travel Time       

    Notes: Uses
    * avgload5period.csv (for facility type breakdown)
    """
    
    METRIC_ID = 'Reliable 1'
    LOGGER.info("Calculating {} for {}".format(METRIC_ID, tm_run_id))

    loaded_network_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "avgload5period_vehclasses.csv")
    loaded_network_df = pd.read_csv(loaded_network_file)
    loaded_network_df.rename(columns=lambda x: x.strip(), inplace=True)
    loaded_network_df['vmtAM_tot'] = loaded_network_df['distance'] * loaded_network_df['volAM_tot']
    LOGGER.info("  Read {:,} rows from {}".format(len(loaded_network_df), loaded_network_file))
    LOGGER.debug("  Columns:".format(list(loaded_network_df.columns)))
    LOGGER.debug("loaded_network_df =\n{}".format(loaded_network_df))

    goods_routes_a_b_links_file = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "metrics", "Metrics_Round2", "Input Files", "goods_routes_a_b.csv")
    goods_routes_a_b_links_df = pd.read_csv(goods_routes_a_b_links_file)
    goods_routes_a_b_links_df.rename(columns={"A":"a", "B":"b"}, inplace=True)
    # merge loaded network with df containing route information
    # remove HOV lanes from the network
    loaded_network_with_goods_routes_df = loaded_network_df.loc[(loaded_network_df['useAM'] !=3)]
    # loaded_network_with_goods_routes_df = loaded_network_with_goods_routes_df[['a','b','ctimAM','ctimPM']]
    loaded_network_with_goods_routes_df = pd.merge(left=loaded_network_with_goods_routes_df, right=goods_routes_a_b_links_df, how='left', left_on=['a','b'], right_on=['a','b'])    
    loaded_network_with_goods_routes_df = loaded_network_with_goods_routes_df.melt(id_vars=['a','b','ctimAM','ctimPM', 'distance', 'vmtAM_tot'], var_name='grouping', value_name='time_period')  
    loaded_network_with_goods_routes_df = loaded_network_with_goods_routes_df.groupby(by=['grouping', 'time_period']).agg({'ctimAM':'sum', \
                                                                                'ctimPM':'sum',\
                                                                                'distance':'sum',\
                                                                                'vmtAM_tot':'sum'}).reset_index()

    loaded_network_with_goods_routes_df['vmt_weighted_ctimAM'] = loaded_network_with_goods_routes_df['vmtAM_tot'] * loaded_network_with_goods_routes_df['ctimAM']

    ctimAM_metrics_df = loaded_network_with_goods_routes_df.loc[(loaded_network_with_goods_routes_df.time_period == 'AM'), ['grouping', 'ctimAM', 'distance', 'vmtAM_tot', 'vmt_weighted_ctimAM']]
    ctimPM_metrics_df = loaded_network_with_goods_routes_df.loc[(loaded_network_with_goods_routes_df.time_period == 'PM'), ['grouping', 'ctimPM']]
    ctim_df = pd.merge(left=ctimAM_metrics_df, right=ctimPM_metrics_df, how='left', left_on=['grouping'], right_on=['grouping'])
    ctim_df['AVGctimPEAK'] = (ctim_df['ctimAM'] + ctim_df['ctimPM'])/2

    # add row for averages from the other corridors
    ctim_df = ctim_df.loc[(ctim_df['grouping'].str.contains('Port') == False)]
    average_values_from_othercorridors = ctim_df.select_dtypes(include=['number']).mean()
    # Convert the Pandas Series to a DataFrame
    average_from_othercorridors_df = pd.DataFrame([average_values_from_othercorridors])
    average_from_othercorridors_df['grouping'] = 'Simple Average from Other corridors'

    # add row for sum of values 
    sum_of_values = ctim_df.select_dtypes(include=['number']).sum()
    # convert pandas series to a dataframe
    sum_df = pd.DataFrame([sum_of_values])
    sum_df['grouping'] = 'Sum of Values for Weighted Average'
    ctim_df = pd.concat([ctim_df, sum_df, average_from_othercorridors_df], ignore_index=True)

    # add column post summation for weighted average
    ctim_df['VMTweightedAVG_ctimAM'] = ctim_df['vmt_weighted_ctimAM'] / ctim_df['vmtAM_tot']

    # put it together, move to long form and return
    grouping_travel_times_df = ctim_df
    grouping_travel_times_df = grouping_travel_times_df.melt(id_vars=['grouping'], var_name='Metric Description')
    grouping_travel_times_df.loc[(grouping_travel_times_df['grouping'].str.contains('Port') == False) & (grouping_travel_times_df['grouping'].str.contains('Goods') == False), 'Road Type'] = 'Other Corridor'
    LOGGER.debug("grouping_travel_times_df =\n{}".format(grouping_travel_times_df))
    # filter out goods routes data, if present
    grouping_travel_times_df = grouping_travel_times_df.loc[(grouping_travel_times_df['Road Type'] == 'Other Corridor')]
    grouping_travel_times_df['Model Run ID'] = tm_run_id
    grouping_travel_times_df['Metric ID'] = METRIC_ID
    grouping_travel_times_df['Intermediate/Final'] = 'final'
    # identify extra, intermediate, or debug steps for easy filtering
    grouping_travel_times_df.loc[(grouping_travel_times_df['Metric Description'].str.contains('distance') == True), 'Intermediate/Final'] = 'Extra'
    grouping_travel_times_df.loc[(grouping_travel_times_df['Metric Description'].str.contains('vmtAM_tot') == True), 'Intermediate/Final'] = 'Intermediate'
    grouping_travel_times_df.loc[(grouping_travel_times_df['Metric Description'].str.contains('vmt_weighted_ctimAM') == True), 'Intermediate/Final'] = 'Intermediate'
    grouping_travel_times_df.loc[(grouping_travel_times_df['grouping'].str.contains('Sum of Values for Weighted Average') == False) & (grouping_travel_times_df['Metric Description'].str.contains('VMTweightedAVG_ctimAM') == True), 'Intermediate/Final'] = 'Debug Step'
    grouping_travel_times_df.loc[(grouping_travel_times_df['grouping'].str.contains('Sum of Values for Weighted Average') == True) & (grouping_travel_times_df['Metric Description'].str.contains('VMTweightedAVG_ctimAM') == False), 'Intermediate/Final'] = 'Debug Step'

    grouping_travel_times_df['Year'] = tm_run_id[:4]
    LOGGER.debug("grouping_travel_times_df for reliable 1:\n{}".format(grouping_travel_times_df))

    return grouping_travel_times_df

def determine_tolled_minor_group_links(tm_run_id: str, fwy_or_arterial: str) -> pd.DataFrame:
    """ Given a travel model run ID, reads the loaded network and the tollclass designations,
    and returns a table that will be used to define which links belong to which tollclass minor grouping.

    If fwy_or_arterial == "fwy",      tm_run_id should be a Pathway 1 model run, and this will return tolled freeway links
    If fwy_or_arterial == "arterial", tm_run_id should be a Pathway 2 model run, and this will return arterial freeway links

    This replaces 'Input Files\\a_b_with_minor_groupings.csv' because this uses the model network information directly

    Args:
        tm_run_id (str):      travel model run ID (should be Pathway 1 or 2)
        fwy_or_arterial(str): one of "fwy" or "arterial"

    Returns:
        pd.DataFrame: mapping from links to tollclass minor groupings.  Columns:
        a (int):              link A node
        b (int):              link B node
        grouping (str):       minor grouping without direction, e.g. EastBay_68024980, EastBay_880680, etc.
        grouping_dir (str):   either AM or PM for the grouping
    """
    if fwy_or_arterial not in ["fwy","arterial"]: raise ValueError

    LOGGER.info("=== determine_tolled_minor_group_links({}, {}) ===".format(tm_run_id, fwy_or_arterial))
    loaded_roadway_network = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "avgload5period_vehclasses.csv")
    tm_loaded_network_df = pd.read_csv(loaded_roadway_network, 
                                       usecols=['a','b','tollclass','ft'],
                                       dtype={'a':numpy.int64, 'b':numpy.int64, 'tollclass':numpy.int64},
                                       na_values=[''])
    LOGGER.info("  Read {:,} rows from {}".format(len(tm_loaded_network_df), loaded_roadway_network))

    # read toll class groupings
    tollclass_df = pd.read_excel(NGFS_TOLLCLASS_FILE)
    LOGGER.info("  Read {:,} rows from {}".format(len(tollclass_df), NGFS_TOLLCLASS_FILE))
    # select NextGenFwy tollclasses where 'Grouping minor' exists
    tollclass_df = tollclass_df.loc[(tollclass_df.project == 'NextGenFwy') & pd.notna(tollclass_df['Grouping minor'])]

    # See TOLLCLASS_Designations.xlsx workbook, Readme - numbering convention
    if fwy_or_arterial == "fwy":
        tollclass_df = tollclass_df.loc[tollclass_df.tollclass > 900000]
    elif fwy_or_arterial == "arterial":
        tollclass_df = tollclass_df.loc[(tollclass_df.tollclass > 700000) & 
                                        (tollclass_df.tollclass < 900000)]

    LOGGER.info("  Filtered to {:,} rows for project=='NextGenFwy' with notna 'Grouping minor' and tollclass appropriate to {}".format(
        len(tollclass_df), fwy_or_arterial))
    # LOGGER.info("  Grouping minor: {}".format(sorted(tollclass_df['Grouping minor'].to_list())))

    # add to loaded roadway network -- INNER JOIN
    grouping_df = pd.merge(
        left=tm_loaded_network_df,
        right=tollclass_df[['tollclass','Grouping minor']],
        on=['tollclass'],
        how='inner'
    )
    # remove rows with 'Minor grouping' that doesn't end in AM or PM
    grouping_df = grouping_df.loc[
        grouping_df['Grouping minor'].str.endswith('_AM') |
        grouping_df['Grouping minor'].str.endswith('_PM')
    ]

    # log the facility type summary
    LOGGER.debug("  Tolled {} facility types:\n{}".format(fwy_or_arterial, grouping_df['ft'].value_counts()))

    # split 'Grouping minor' to 'grouping' (now without direction) and 'grouping_dir'
    grouping_df['grouping_dir'] = grouping_df['Grouping minor'].str[-2:]
    grouping_df['grouping']     = grouping_df['Grouping minor'].str[:-3]
    grouping_df.drop(columns=['Grouping minor','tollclass','ft'], inplace=True)
    LOGGER.debug("  Returning {:,} links:\n{}".format(len(grouping_df), grouping_df))
    return grouping_df

def determine_congested_segment_links(tm_run_id: str) -> pd.DataFrame:
    """ Given a travel model run ID, reads the loaded network and the tollclass designations,
    and returns a table that will be used to define which links belong to which tollclass minor grouping.

        Args:
        tm_run_id (str):      travel model run ID (should be Pathway 1 or 2)

    Returns:
        pd.DataFrame: mapping from links to tollclass minor groupings.  Columns:
        a (int):              link A node
        b (int):              link B node
    """

    LOGGER.info("=== determine_congested_segment_links({}) ===".format(tm_run_id))
    loaded_roadway_network = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "avgload5period_vehclasses.csv")
    tm_loaded_network_df = pd.read_csv(loaded_roadway_network, 
                                       usecols=['a', 'b', 'tollclass', 'useAM', 'distance', 'tollAM_da', 'tollPM_da'],
                                       dtype={'a':numpy.int64, 'b':numpy.int64, 'tollclass':numpy.int64},
                                       na_values=[''])
    LOGGER.info("  Read {:,} rows from {}".format(len(tm_loaded_network_df), loaded_roadway_network))

    # read toll class groupings
    tollclass_df = pd.read_excel(NGFS_TOLLCLASS_FILE)
    LOGGER.info("  Read {:,} rows from {}".format(len(tollclass_df), NGFS_TOLLCLASS_FILE))
    # select NextGenFwy tollclasses where 'Grouping minor' exists
    tollclass_df = tollclass_df.loc[(tollclass_df.project == 'NextGenFwy') & pd.notna(tollclass_df['Grouping minor'])]

    # See TOLLCLASS_Designations.xlsx workbook, Readme - numbering convention
    tollclass_df = tollclass_df.loc[(tollclass_df.tollclass > 30)]
    
    LOGGER.info("  Filtered to {:,} rows for project=='NextGenFwy' with notna 'Grouping minor' and links in the peak AM direction".format(
    len(tollclass_df)))
    # LOGGER.info("  Grouping minor: {}".format(sorted(tollclass_df['Grouping minor'].to_list())))

    # add to loaded roadway network -- INNER JOIN
    grouping_df = pd.merge(
        left=tm_loaded_network_df,
        right=tollclass_df[['tollclass','Grouping minor']],
        on=['tollclass'],
        how='inner'
    )
    
    # calculate toll per mile for each link
    grouping_df['toll_per_mile_AM_da'] = grouping_df['tollAM_da'] / grouping_df['distance']
    grouping_df['toll_per_mile_PM_da'] = grouping_df['tollPM_da'] / grouping_df['distance']
    # Calculate row-wise average and round the result
    grouping_df['toll_per_mile_PeakPeriod_da'] = (grouping_df['toll_per_mile_AM_da'] + grouping_df['toll_per_mile_PM_da']) / 2  # Calculate average
    # grouping_df['toll_per_mile_PeakPeriod_da'] = grouping_df['toll_per_mile_PeakPeriod_da'].round()     # Round the result

    # remove rows with 'toll_per_mile_PeakPeriod_da' that isn't 3, 5, or 16 cents
    # meant to remove links with bridge tolls
    grouping_df = grouping_df.loc[
        (grouping_df.toll_per_mile_PeakPeriod_da > 0) & 
        (grouping_df.toll_per_mile_PeakPeriod_da < 17)
    ]
    # remove rows of HOV links
    grouping_df = grouping_df.loc[(grouping_df.useAM == 1)]

    # split 'Grouping minor' to 'grouping' (now without direction)
    grouping_df['grouping']     = grouping_df['Grouping minor'].str[:-3]
    grouping_df['congested/other'] = 'other segment'
    grouping_df.loc[(grouping_df.toll_per_mile_PeakPeriod_da > 10),'congested/other'] = 'congested segment'
    grouping_df = grouping_df.groupby(by=['grouping', 'congested/other']).agg({'toll_per_mile_PeakPeriod_da':'mean'}).reset_index()
    grouping_df.drop(columns=['toll_per_mile_PeakPeriod_da'], inplace=True)
    LOGGER.debug("  Returning {:,} links:\n{}".format(len(grouping_df), grouping_df))
    return grouping_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip_if_exists", action="store_true", help="Use this option to skip creating metrics files if one exists already")
    args = parser.parse_args()

    pd.options.display.width = 500 # redirect output to file so this will be readable
    pd.options.display.max_columns = 100
    pd.options.display.max_rows = 500
    pd.options.mode.chained_assignment = None  # default='warn'

    # set up logging
    # create logger
    LOGGER = logging.getLogger(__name__)
    LOGGER.setLevel('DEBUG')

    # console handler
    ch = logging.StreamHandler()
    ch.setLevel('INFO')
    ch.setFormatter(logging.Formatter('%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    LOGGER.addHandler(ch)
    # file handler -- append if skip_if_exists is passed
    fh = logging.FileHandler(LOG_FILE, mode='a' if args.skip_if_exists else 'w')
    fh.setLevel('DEBUG')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    LOGGER.addHandler(fh)

    LOGGER.debug("args = {}".format(args))

    current_runs_df = pd.read_excel(NGFS_MODEL_RUNS_FILE, sheet_name='all_runs', usecols=['project','year','directory','run_set','category','short_name','status'])
    current_runs_df = current_runs_df.loc[ current_runs_df['status'] == 'current']
    # only process metrics for 2035 model runs 
    current_runs_df = current_runs_df.loc[ current_runs_df['year'] == 2035]

    LOGGER.info("current_runs_df: \n{}".format(current_runs_df))

    current_runs_list = current_runs_df['directory'].to_list()
      
    # find the last pathway 1 run, since we'll use that to determine which links are in the fwy minor groupings
    pathway1_runs = current_runs_df.loc[ current_runs_df['category'].str.startswith("P1_AllLaneTolling")]
    PATHWAY1_SCENARIO_RUN_ID = pathway1_runs['directory'].tolist()[-1] # take the last one
    LOGGER.info("=> PATHWAY1_SCENARIO_RUN_ID = {}".format(PATHWAY1_SCENARIO_RUN_ID))
    TOLLED_FWY_MINOR_GROUP_LINKS_DF = determine_tolled_minor_group_links(PATHWAY1_SCENARIO_RUN_ID, "fwy")
    # TOLLED_FWY_MINOR_GROUP_LINKS_DF.to_csv("TOLLED_FWY_MINOR_GROUP_LINKS.csv", index=False)
    TOLLED_FWY_CONGESTED_LINKS_DF = determine_congested_segment_links(PATHWAY1_SCENARIO_RUN_ID)
    # TOLLED_FWY_CONGESTED_LINKS_DF.to_csv("TOLLED_FWY_CONGESTED_LINKS.csv", index=False)

    for tm_run_id in current_runs_list:
        out_filename = os.path.join(os.getcwd(),"Reliable1_change_in_travel_time_{}.csv".format(tm_run_id))

        if args.skip_if_exists and os.path.exists(out_filename):
            LOGGER.info("Skipping {} -- {} exists".format(tm_run_id, out_filename))
            continue

        LOGGER.info("Processing run {}".format(tm_run_id))

        # results will be stored here
        metrics_df = pd.DataFrame()

        metrics_df = pd.concat([calculate_Reliable1_change_travel_time_on_freeways(tm_run_id),\
            calculate_Reliable1_change_travel_time_on_parallel_arterials(tm_run_id),\
            calculate_Reliable1_change_travel_time_on_parallel_arterials_epc_non(tm_run_id),\
            calculate_Reliable1_change_travel_time_on_GoodsRoutes(tm_run_id),\
            calculate_Reliable1_change_travel_time_on_Othercorridors(tm_run_id)])
        LOGGER.info("@@@@@@@@@@@@@ R1 Done")

        metrics_df.to_csv(out_filename, float_format='%.5f', index=False) #, header=False
        LOGGER.info("Wrote {}".format(out_filename))

        # for testing, stop here
        # sys.exit()