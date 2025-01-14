import pandas as pd
import numpy as np
import pyreadr
import os

USAGE = """

  python offmodel_prep.py

  Simple script that reads TAZ land use input data and trips output data, outputs
  the following .csv files to be used in the off-model calculation (PBA50+ version).
  * bikeshare.csv
  * carshare.csv
  * employerShuttle.csv
  * targetedTransportationAlternatives.csv
  * bikeInfrastructure.csv

"""

######## Bikeshare

def prep_data_for_bikeshare(taz_input_df):
    """
    Input:
    * TAZ land use input

    Output the following data:
    * total households
    * total employment (jobs)
    
    """
    print('create off-model calculation input data for bike share')
    bikeshare_taz_cols = ['TOTPOP', 'TOTEMP']  # only care about these fields
    bikeshare_taz = taz_input_df[bikeshare_taz_cols].sum()
    bikeshare_taz_df = pd.DataFrame(bikeshare_taz).reset_index()
    bikeshare_taz_df.columns = ['variable', 'value']

    bikeshare_taz_df.to_csv(os.path.join(OUTPUT_DIR, 'bikeshare.csv'), index=False)

######## Carshare

def prep_data_for_carshare(taz_input_df):
    """
    Input:
    * TAZ land use input

    Output the following data:
    * total population
    * population in "urban" TAZs (density > 10 persons/residential acre)
    * population in "non-urban" TAZs (density <= 10 persons/residential acre)
    * adult population (age 20-64) in "urban" TAZs (density > 10 persons/residential acre)
    * adult population (age 20-64) in "non-urban" TAZs (density <= 10 persons/residential acre)
    
    """
    print('create off-model calculation input data for car share')
    # Calculator constant: criteria for applying trip caps
    K_MIN_POP_DENSITY = 10   # Minimum density needed to be considered "urban" and support dense carshare (persons/residential acre)

    carshare_taz_cols = ['ZONE', 'COUNTY', 'SD', 'TOTPOP', 'RESACRE', 'AGE2044', 'AGE4564']
    carshare_taz_df = taz_input_df[carshare_taz_cols]

    carshare_taz_df['totpop_per_resacre'] = np.where(carshare_taz_df['RESACRE'] == 0, 0, carshare_taz_df['TOTPOP'] / carshare_taz_df['RESACRE'])
    carshare_taz_df['carshare_dense'] = carshare_taz_df['totpop_per_resacre'] > K_MIN_POP_DENSITY
    carshare_taz_df['totpop_dense'] = carshare_taz_df['TOTPOP'] * carshare_taz_df['carshare_dense']
    carshare_taz_df['totpop_sparse'] = carshare_taz_df['TOTPOP'] * (~carshare_taz_df['carshare_dense'])
    carshare_taz_df['adultpop_dense'] = (carshare_taz_df['AGE2044'] + carshare_taz_df['AGE4564']) * carshare_taz_df['carshare_dense']
    carshare_taz_df['adultpop_sparse'] = (carshare_taz_df['AGE2044'] + carshare_taz_df['AGE4564']) * (~carshare_taz_df['carshare_dense'])

    carshare_taz = carshare_taz_df[['TOTPOP', 'totpop_dense', 'totpop_sparse', 'adultpop_dense', 'adultpop_sparse']].sum()
    carshare_taz_df2 = pd.DataFrame(carshare_taz).reset_index()
    carshare_taz_df2.columns = ['variable', 'value']
    carshare_taz_df2.loc[carshare_taz_df2['variable'] == 'TOTPOP', 'variable'] = 'total_population'

    carshare_taz_df2.to_csv(os.path.join(OUTPUT_DIR, 'carshare.csv'), index=False)

######## Employer Shuttles

def prep_data_for_employerShuttle(trips_output_df):
    """
    Input:
    * trips output

    Output the following data:
    * trip mode share of work trips with distance > 30.0

    """
    print('create off-model calculation input data for employer shuttles')
    # filter to distance > 30.0 and work trips
    trips_sub = trips_output_df.loc[(trips_output_df['distance'] > 30.0) & (trips_output_df['tour_purpose'].str[:5] == "work_")]

    # summarize
    trips_summary = trips_sub.groupby(['trip_mode', 'mode_name', 'simple_mode'])[['hh_id']].count().reset_index()
    trips_summary.rename({'hh_id': 'simulated_trips'}, axis=1, inplace=True)
    trips_summary['estimated_trips'] = trips_summary['simulated_trips'] / SAMPLING_RATE

    # summarize to mode
    simple_mode_share = trips_summary.groupby(['simple_mode'])[['estimated_trips']].sum().apply(lambda x: x/x.sum()).reset_index()
    simple_mode_share.rename({'estimated_trips': 'value'}, axis=1, inplace=True)
    simple_mode_share['variable'] = 'mode_share'
    simple_mode_share.to_csv(os.path.join(OUTPUT_DIR, 'employerShuttle.csv'), index=False)

######## Targeted Transportation Alternatives

def prep_data_for_TargetedAlt(taz_input_df, tripdist_output_df):
    """
    Input:
    * TAZ land use input
    * trip distance by mode and SD output

    Output the following data:
    * total households
    * total employment (jobs)
    * average trip length of all trips
    * average trip length of drive-alone and work trips

    """
    print('create off-model calculation input data for targeted transportation alternatives')
    alt_taz_cols = ['ZONE', 'SD', 'COUNTY', 'TOTEMP', 'TOTHH', 'CIACRE', 'AREATYPE']
    alt_taz_df = taz_input_df[alt_taz_cols]
    alt_taz_summary = alt_taz_df[['TOTEMP', 'TOTHH']].sum()
    alt_taz_summary_df = pd.DataFrame(alt_taz_summary).reset_index()
    alt_taz_summary_df.columns = ['variable', 'value']
    
    # trip-distance-by-mode-superdistrict rollups
    tripdist_TargetedAlt = tripdist_output_df.copy()
    tripdist_TargetedAlt['total_distance'] = tripdist_TargetedAlt['mean_distance'] * tripdist_TargetedAlt['estimated_trips']
    tripdist_TargetedAlt['work_trip'] = 0
    tripdist_TargetedAlt['drive_alone'] = 0
    tripdist_TargetedAlt.loc[tripdist_TargetedAlt['tour_purpose'].str[:5] == "work_", 'work_trip'] = 1
    tripdist_TargetedAlt.loc[tripdist_TargetedAlt['simple_mode'] == 'SOV', 'drive_alone'] = 1

    tripdist_TargetedAlt['total_distance_work_da'] = tripdist_TargetedAlt['total_distance'] * tripdist_TargetedAlt['work_trip'] * tripdist_TargetedAlt['drive_alone']
    tripdist_TargetedAlt['estimated_trips_work_da'] = tripdist_TargetedAlt['estimated_trips'] * tripdist_TargetedAlt['work_trip'] * tripdist_TargetedAlt['drive_alone']

    tripdist_summary = tripdist_TargetedAlt[['total_distance', 'estimated_trips', 'total_distance_work_da', 'estimated_trips_work_da']].sum()
    tripdist_summary_df = pd.DataFrame(tripdist_summary).transpose()
    tripdist_summary_df['avg_trip_length'] = tripdist_summary_df['total_distance'] / tripdist_summary_df['estimated_trips']
    tripdist_summary_df['avg_trip_length_work_da'] = tripdist_summary_df['total_distance_work_da'] / tripdist_summary_df['estimated_trips_work_da']
    tripdist_summary_df = tripdist_summary_df[['avg_trip_length', 'avg_trip_length_work_da']].transpose().reset_index()
    tripdist_summary_df.columns = ['variable', 'value']

    alt_all_summary = pd.concat([alt_taz_summary_df, tripdist_summary_df])
    alt_all_summary.loc[alt_all_summary['variable'] == 'TOTHH', 'variable'] = 'total_households'
    alt_all_summary.loc[alt_all_summary['variable'] == 'TOTEMP', 'variable'] = 'total_jobs'

    alt_all_summary.to_csv(os.path.join(OUTPUT_DIR, 'targetedTransportationAlternatives.csv'), index=False)

######## Model Data - Bike Infrastructure.csv
# Data needed: TAZ input, trips output
def prep_data_for_bikeInfra(taz_input_df, tripdist_output_df):
    """
    Input:
    * TAZ land use input
    * trip distance by mode and SD output

    Output the following data by SD (SD==0 is region-level):
    * total_population
    * total_population_county
    * population_county_share
    * total_square_miles
    * bike_avg_trip_dist
    * bike_dist
    * bike_trip_mode_share
    * estimated_trips
    * sov_trip_mode_share
    
    """
    print('create off-model calculation input data for bike infrastructure')

    # population and land area by SD
    tazdata_sd_df = taz_input_df.groupby(['SD', 'COUNTY'])[['TOTPOP', 'TOTACRE']].sum().reset_index()
    tazdata_sd_df['total_square_miles'] = tazdata_sd_df['TOTACRE']/640.0
    # tazdata_sd_df.rename({'TOTPOP': 'SD_pop'}, axis=1, inplace=True)

    # total population and land area
    tazdata_all = taz_input_df[['TOTPOP', 'TOTACRE']].sum()
    tazdata_all_df = pd.DataFrame(tazdata_all).transpose()
    tazdata_all_df['total_square_miles'] = tazdata_all_df['TOTACRE']/640.0
    tazdata_all_df['SD'] = 0
    tazdata_all_df['COUNTY'] = 0

    # add all to SD data
    tazdata_sd_df = pd.concat([tazdata_sd_df, tazdata_all_df], ignore_index=True)

    # population by county
    tazdata_county_df = taz_input_df.groupby(['COUNTY'])[['TOTPOP']].sum().reset_index()
    tazdata_county_df.rename({'TOTPOP': 'COUNTY_pop'}, axis=1, inplace=True)

    # calculate SD population share of county
    tazdata_sd_df = tazdata_sd_df.merge(tazdata_county_df, on='COUNTY', how='left')
    tazdata_sd_df['pop_county_share'] = tazdata_sd_df['TOTPOP'] / tazdata_sd_df['COUNTY_pop']
    print(len(tazdata_sd_df))
    
    # For Bike Infrastructure, calculate bike and SOV trip mode share, and average bike trip distance
    tripdist_bikeInfra = tripdist_output_df.copy()
    tripdist_bikeInfra['bike_trips'] = \
        tripdist_bikeInfra['estimated_trips'] * (tripdist_bikeInfra['mode_name'] == 'Bike')
    tripdist_bikeInfra['bike_dist'] = \
        tripdist_bikeInfra['estimated_trips'] * (tripdist_bikeInfra['mode_name'] == 'Bike') * tripdist_bikeInfra['mean_distance']
    tripdist_bikeInfra['sov_trips'] = \
        tripdist_bikeInfra['estimated_trips'] * (tripdist_bikeInfra['simple_mode'] == 'SOV')

    tripdist_sd_summary_df = tripdist_bikeInfra.groupby(['dest_sd'])[['bike_trips', 'bike_dist', 'sov_trips', 'estimated_trips']].sum().reset_index()
    tripdist_sd_summary_df['bike_trip_mode_share'] = tripdist_sd_summary_df['bike_trips']/tripdist_sd_summary_df['estimated_trips']
    tripdist_sd_summary_df['bike_avg_trip_dist'] = tripdist_sd_summary_df['bike_dist']/tripdist_sd_summary_df['bike_trips']
    tripdist_sd_summary_df['sov_trip_mode_share'] = tripdist_sd_summary_df['sov_trips']/tripdist_sd_summary_df['estimated_trips']

    tripdist_all_summary = tripdist_bikeInfra[['bike_trips', 'bike_dist', 'sov_trips', 'estimated_trips']].sum()
    tripdist_all_summary_df = pd.DataFrame(tripdist_all_summary).transpose()
    tripdist_all_summary_df['bike_trip_mode_share'] = tripdist_all_summary_df['bike_trips']/tripdist_all_summary_df['estimated_trips']
    tripdist_all_summary_df['bike_avg_trip_dist'] = tripdist_all_summary_df['bike_dist']/tripdist_all_summary_df['bike_trips']
    tripdist_all_summary_df['sov_trip_mode_share'] = tripdist_all_summary_df['sov_trips']/tripdist_all_summary_df['estimated_trips']
    tripdist_all_summary_df['dest_sd'] = 0

    # add all to SD data
    tripdist_sd_summary_df = pd.concat([tripdist_sd_summary_df, tripdist_all_summary_df], ignore_index=True)
    print(len(tripdist_sd_summary_df))

    sd_all_df = pd.merge(
        tazdata_sd_df,
        tripdist_sd_summary_df,
        left_on='SD',
        right_on='dest_sd',
        how='left'
    )
    print(len(sd_all_df))

    # only keep needed columns
    col_needed = [
        'TOTPOP', 'COUNTY_pop', 'pop_county_share', 'total_square_miles',
        'bike_avg_trip_dist', 'bike_dist', 'bike_trip_mode_share', 'estimated_trips', 'sov_trip_mode_share'
    ]
    sd_all_df = sd_all_df[['SD'] + col_needed]

    # convert to long table
    sd_all_df_long = pd.melt(sd_all_df, id_vars=['SD'], value_vars=col_needed)

    # upate variable name to be consistent with off-model template
    var_name_dict = {
        'pop_county_share': 'population_county_share',
        'TOTPOP': 'total_population',
        'COUNTY_pop': 'total_population_county',
        'SD': 'superdistrict'
    }
    for i in var_name_dict:
        sd_all_df_long.loc[sd_all_df_long['variable'] == i, 'variable'] = var_name_dict[i]
    
    sd_all_df_long.to_csv(os.path.join(OUTPUT_DIR, 'bikeInfrastructure.csv'), index=False)


if __name__ == '__main__':

    # output dir
    OUTPUT_DIR = 'offmodel\\offmodel_prep'

    # TAZ land use input
    print('load TAZ land use data')
    tazdata_file = 'INPUT\\landuse\\tazData.csv'
    tazdata_df = pd.read_csv(tazdata_file)

    # trip output and associated variable
    # Mode look-up table
    LOOKUP_MODE = pd.DataFrame({
        'trip_mode': list(range(1, 22)),
        'mode_name': [
            'Drive alone - free', 'Drive alone - pay', 
            'Shared ride two - free', 'Shared ride two - pay',
            'Shared ride three - free', 'Shared ride three - pay',
            'Walk', 'Bike',
            'Walk to local bus', 'Walk to light rail or ferry', 'Walk to express bus', 
            'Walk to heavy rail', 'Walk to commuter rail',
            'Drive to local bus', 'Drive to light rail or ferry', 'Drive to express bus', 
            'Drive to heavy rail', 'Drive to commuter rail',
            'Taxi', 'TNC', 'TNC shared'
        ],
        'simple_mode': [
            'SOV', 'SOV',
            'HOV', 'HOV',
            'HOV 3.5', 'HOV 3.5',
            'Walk', 'Bike',
            'Walk to transit', 'Walk to transit', 
            'Walk to transit', 'Walk to transit', 
            'Walk to transit', 'Drive to transit',
            'Drive to transit', 'Drive to transit', 
            'Drive to transit', 'Drive to transit',
            'Taxi/TNC', 'Taxi/TNC', 'Taxi/TNC'
        ]
    })

    SAMPLING_RATE = 0.500

    # load trip data
    print('load trips output')
    trips_R_file = 'updated_output\\trips.rdata'
    trips_R = pyreadr.read_r(trips_R_file)

    # drop unneeded columns
    trips = trips_R['trips'][['hh_id', 'tour_purpose', 'distance', 'trip_mode', 'orig_taz', 'dest_taz']]

    # add origin SD and destination SD
    orig_sd = tazdata_df[['ZONE', 'SD']].rename(columns={'ZONE': 'orig_taz', 'SD': 'orig_sd'})
    trips_df = trips.merge(orig_sd, on='orig_taz', how='left')

    dest_sd = tazdata_df[['ZONE', 'SD']].rename(columns={'ZONE': 'dest_taz', 'SD': 'dest_sd'})
    trips_df = trips_df.merge(dest_sd, on='dest_taz', how='left')

    # add mode name and category
    trips_df = trips_df.merge(LOOKUP_MODE, on='trip_mode', how='left')

    # trip distance by mode and SD - will be used in multiple off-model prep calculations
    tripdist_df = trips_df.groupby(['trip_mode', 'mode_name', 'simple_mode', 'tour_purpose', 'orig_sd', 'dest_sd']).agg(
        {'hh_id': 'count', 
        'distance': 'mean'}).reset_index()
    tripdist_df.rename({'hh_id': 'simulated_trips', 'distance': 'mean_distance'}, axis=1, inplace=True)

    tripdist_df['estimated_trips'] = tripdist_df['simulated_trips'] / SAMPLING_RATE
    tripdist_df = tripdist_df[['trip_mode', 'mode_name', 'simple_mode', 'tour_purpose', 'orig_sd', 'dest_sd', 'simulated_trips', 'estimated_trips', 'mean_distance']]

    # run the functions
    prep_data_for_bikeshare(tazdata_df)
    prep_data_for_carshare(tazdata_df)
    prep_data_for_employerShuttle(trips_df)
    prep_data_for_TargetedAlt(tazdata_df, tripdist_df)
    prep_data_for_bikeInfra(tazdata_df, tripdist_df)
