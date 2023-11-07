#
# Create updated HSR input tables for Travel Model 1.6
# using CHSR_data_from_DB-ECO_July2023 (https://mtcdrive.box.com/s/pbf7j2taz45ulfl22ltauorninx6wwq6)
#
# Input:
#   Total access trips from CHSR zones to the 5 Bay Area CHSR station in 2040 and 2050
# Output:
#   tripsHsr_YYYY.csv: Allocation of access trips from MTC zones.
#     For trips from within-MTC-region, the trips are allocated to MTC zones using area-based calculations.
#     For trips from external zones, the zones are manually mapped to external MTC zones based on
#     the nearest freeway/directions.
#     Columns include: ORIG_TAZ1454,DEST_TAZ1454,[DA,SR2,TAXI,TRANSIT]_[EA,AM,MD.PM,EV]
#   tripsHsr_long.csv: Long version of the above.
# See also:
#   convert_access_trips_to_matrix.job
#

import pathlib
import pandas
import re
import simpledbf
import sys
import Wrangler # to read HSR coding

BOX_ROOT = pathlib.Path("E:\Box")
EXOGENOUS_ROOT = BOX_ROOT / "Plan Bay Area 2050+/Federal and State Approvals/CARB Technical Methodology/Exogenous Forces"
CHSR_ROOT = EXOGENOUS_ROOT / "CHSR/CHSR_data_from_DB-ECO_July2023"

MODEL_INPUTS_ROOT = BOX_ROOT / "Modeling and Surveys/Development/Travel_Model_1.6/Model_Inputs/CHSR"
ACCESS_OUTPUT = MODEL_INPUTS_ROOT / "tripsHsr_YYYY.csv"  # year
# ACCESS_OUTPUT = pathlib.Path(".") / "tripsHsr_YYYY.csv"  # DONT COMMIT

# Bay Area HSR stations to MTC TAZs
STATION_TO_MTC_TAZ = {
    'San Francisco (STC)':  14,
    'San Francisco (4TH)': 109,
    'Millbrae/SFO'       : 240,
    'San Jose'           : 538,
    'Gilroy'             : 707
}
STATION_TO_MTC_TAZ_DF = pandas.DataFrame.from_dict(STATION_TO_MTC_TAZ, orient='index').reset_index()
STATION_TO_MTC_TAZ_DF.columns=['STATION','DEST_TAZ1454']
# print(STATION_TO_MTC_TAZ_DF)

# The inputs to this script are annual trips, so this factor is used to convert to daily.
ANNUAL_TO_DAILY_FACTOR = 1.0/365.0

# TODO: CHSR consultants will give us their assumptions
TIME_OF_DAY_DISTRIBUTION = {
    # interim assumption calculated below
}

# The inputs to this script are person trips. CHSR consultants say they have no assumptions for 
# how to convert these to vehicle trips. These are therefore based on airport access trips, or Q9 from
# 2014-2015 SFO/OAK Ground Access Study (http://ccgresearch.com/wp-content/uploads/2017/10/Final-SFO-OAK-report.pdf)
#                  Personal Vehicle + Rental Car                              Taxi + TNC 
# Party Size                        Person Trips   Veh Trips                         Person Trips  Veh Trips
#          1    (0.66*6689) + (0.54*2654) = 5848   /1 = 5848     (0.69*1827) + (0.78*1038) = 2070  /1 = 2070
#          2    (0.22*6689) + (0.31*2654) = 2294   /2 = 1147     (0.22*1827) + (0.19*1038) =  599  /2 =  300
#          3    (0.06*6689) + (0.07*2654) =  587   /3 =  196     (0.04*1827) + (0.02*1038) =   94  /3 =   31
#         4+    (0.05*6689) + (0.08*2654) =  547   /4 =  137     (0.05*1827) + (0.01*1038) =  102  /4 =   26
#                                           9276        7328                                 2865       2427
#
AUTO_PERSON_TRIPS_TO_VEH_TRIPS = { # from above
    'DA': 5848 / 9276,            # DA veh trips  / total personal auto person trips
    'SR2': (1147+196+137) / 9276, # SR2+ veh trips / total personal auto person trips
}
TAXI_PERSON_TRIPS_TO_VEH_TRIPS = 2427/2865  # from above, taxi/tnc veh trips / person trips
print("Assuming AUTO_PERSON_TRIPS_TO_VEH_TRIPS: {}".format(AUTO_PERSON_TRIPS_TO_VEH_TRIPS))
print("Assuming TAXI_PERSON_TRIPS_TO_VEH_TRIPS: {}".format(TAXI_PERSON_TRIPS_TO_VEH_TRIPS))
# average vehicle occupancy for SR2+:
AVG_SR2_PLUS_OCC = (2294+587+547+599+94+102)/(1147+196+137+300+31+26)
print("Average SR2+ vehicle occupancy: {}".format(AVG_SR2_PLUS_OCC))

# The Consultants didn't send over detailed egress tables, only access, beyond high level summaries
# indicating that access trips are approx equal to egress trips. This script will therefore generate
# egress trips from access trips.
#
# Source: RTP2021/TM1.5 input
# See HSR_access_egress tableau workbook, Egress over Access:
# https://10ay.online.tableau.com/t/metropolitantransportationcommission/views/HSR_access_egress/EgressoverAccess
# Note: there are no EA numbers from this dataset, and the 4th and King station isn't included
ACCESS_TO_EGRESS_PERS = {
    # year DEST_TAZ1454, station                   AM     MD     PM     EV
    (2040,           14, 'San Francisco (STC)', 2.360, 1.401, 2.343, 1.401),
    (2040,          240, 'Millbrae/SFO',        0.391, 0.385, 0.392, 0.385),
    (2040,          538, 'San Jose',            0.731, 0.636, 0.729, 0.636),
    (2040,          707, 'Gilroy',              0.761, 1.142, 0.766, 1.142),
    # year DEST_TAZ1454, station                   AM     MD     PM     EV
    (2050,           14, 'San Francisco (STC)', 2.277, 1.380, 2.261, 1.380),
    (2050,          240, 'Millbrae/SFO',        0.399, 0.405, 0.400, 0.405),
    (2050,          538, 'San Jose',            0.827, 0.684, 0.826, 0.684),
    (2050,          707, 'Gilroy',              0.651, 0.952, 0.655, 0.952),
}
ACCESS_TO_EGRESS_PERS_DF = pandas.DataFrame(
    data=ACCESS_TO_EGRESS_PERS, 
    columns=['year','DEST_TAZ1454','STATION','ACC_TO_EGR_PERS_AM','ACC_TO_EGR_PERS_MD','ACC_TO_EGR_PERS_PM','ACC_TO_EGR_PERS_EV'])

if __name__ == '__main__':
    pandas.options.display.width    = 1000
    pandas.options.display.max_rows = 1000
    pandas.options.display.max_columns = 35
    print("CHSR_ROOT={}".format(CHSR_ROOT))

    # In the interim, distribute these trips based on the service distribution we have coded for CHSR
    HSR_line_file = BOX_ROOT / "Modeling and Surveys/TM1_NetworkProjects/HSR/hsr.lin"
    trn_net = Wrangler.TransitNetwork(modelType=Wrangler.Network.MODEL_TYPE_TM1, modelVersion=1.0)
    trn_net.parseFile(str(HSR_line_file))
    HSR_freqs = trn_net.getCombinedFreq(re.compile(".*"))
    print("Read transit network from {}: {}".format(HSR_line_file, trn_net))
    print("Combined frequencies: {}".format(HSR_freqs))
    TIMEPERIODS = ['EA','AM','MD','PM','EV']
    runs_per_timeperiod = {}
    total_runs = 0.0
    for timeperiod_idx in range(len(TIMEPERIODS)):
        timeperiod = TIMEPERIODS[timeperiod_idx]
        runs_per_timeperiod[timeperiod] =  60.0 * Wrangler.TransitLine.HOURS_PER_TIMEPERIOD[Wrangler.Network.MODEL_TYPE_TM1][timeperiod]*60.0 / HSR_freqs[timeperiod_idx]
        total_runs += runs_per_timeperiod[timeperiod]
    # distribute access trips based on share of runs per time period
    print("Resulting TIME_OF_DAY_DISTRIBUTION:")
    for timeperiod in TIMEPERIODS:
        TIME_OF_DAY_DISTRIBUTION[timeperiod] = runs_per_timeperiod[timeperiod]/total_runs
        print("  {}:{:.4f}".format(timeperiod, TIME_OF_DAY_DISTRIBUTION[timeperiod]))

    # We have no data for San Francisco (4TH) so assume similar to STC but more moderate
    # So let's bring it halfway closer to 1.0
    ACCESS_TO_EGRESS_PERS_DF.set_index(['year','DEST_TAZ1454','STATION'], inplace=True)
    SF_4th_rows = [{
        'year'          : 2040,
        'DEST_TAZ1454'  : 109,
        'STATION'       : 'San Francisco (4TH)',
        'ACC_TO_EGR_PERS_AM': (ACCESS_TO_EGRESS_PERS_DF.loc[(2040,14,'San Francisco (STC)'),'ACC_TO_EGR_PERS_AM'] + 1.0)/2.0,
        'ACC_TO_EGR_PERS_MD': (ACCESS_TO_EGRESS_PERS_DF.loc[(2040,14,'San Francisco (STC)'),'ACC_TO_EGR_PERS_MD'] + 1.0)/2.0,
        'ACC_TO_EGR_PERS_PM': (ACCESS_TO_EGRESS_PERS_DF.loc[(2040,14,'San Francisco (STC)'),'ACC_TO_EGR_PERS_PM'] + 1.0)/2.0,
        'ACC_TO_EGR_PERS_EV': (ACCESS_TO_EGRESS_PERS_DF.loc[(2040,14,'San Francisco (STC)'),'ACC_TO_EGR_PERS_EV'] + 1.0)/2.0,
    },{
        'year'          : 2050,
        'DEST_TAZ1454'  : 109,
        'STATION'       : 'San Francisco (4TH)',
        'ACC_TO_EGR_PERS_AM': (ACCESS_TO_EGRESS_PERS_DF.loc[(2050,14,'San Francisco (STC)'),'ACC_TO_EGR_PERS_AM'] + 1.0)/2.0,
        'ACC_TO_EGR_PERS_MD': (ACCESS_TO_EGRESS_PERS_DF.loc[(2050,14,'San Francisco (STC)'),'ACC_TO_EGR_PERS_MD'] + 1.0)/2.0,
        'ACC_TO_EGR_PERS_PM': (ACCESS_TO_EGRESS_PERS_DF.loc[(2050,14,'San Francisco (STC)'),'ACC_TO_EGR_PERS_PM'] + 1.0)/2.0,
        'ACC_TO_EGR_PERS_EV': (ACCESS_TO_EGRESS_PERS_DF.loc[(2050,14,'San Francisco (STC)'),'ACC_TO_EGR_PERS_EV'] + 1.0)/2.0,
    }]
    ACCESS_TO_EGRESS_PERS_DF = pandas.concat([
        ACCESS_TO_EGRESS_PERS_DF.reset_index(drop=False), 
        pandas.DataFrame.from_dict(SF_4th_rows)], ignore_index=True).sort_values(by=['year','DEST_TAZ1454'])
    print("ACCESS_TO_EGRESS_PERS_DF:\n{}".format(ACCESS_TO_EGRESS_PERS_DF))

    # ===============================================================================================
    # read the access trips from CHSR zones to Bay Area stations
    access_trips_df = pandas.DataFrame()
    spreadsheets = list(CHSR_ROOT.glob('Spreadsheets/PH1_20*0_Access_Egress_Zones_*.xlsx'))
    filename_pattern = re.compile(r"PH1_(\d\d\d\d)_Access_Egress_Zones_(.*)\.xlsx")

    for spreadsheet in spreadsheets:

        match_obj = filename_pattern.match(spreadsheet.name)
        print("Reading {}".format(spreadsheet))

        trips_df = pandas.read_excel(spreadsheet)
        trips_df['year'] = int(match_obj.group(1))
        print("  -> read {:,} rows".format(len(trips_df)))

        access_trips_df = pandas.concat([access_trips_df, trips_df])

    # remove zero-trip lines
    access_trips_df = access_trips_df.loc[access_trips_df.TOTAL>0]
    # rename for clarity
    access_trips_df.rename(columns={'AUTO':'AUTO_PERS', 'TAXI':'TAXI_PERS','TOTAL':'TOTAL_PERS'}, inplace=True)
    # convert to daily from annual
    access_trips_df['AUTO_PERS']    = access_trips_df['AUTO_PERS' ] * ANNUAL_TO_DAILY_FACTOR
    access_trips_df['TAXI_PERS']    = access_trips_df['TAXI_PERS' ] * ANNUAL_TO_DAILY_FACTOR
    access_trips_df['TRANSIT']      = access_trips_df['TRANSIT'   ] * ANNUAL_TO_DAILY_FACTOR
    access_trips_df['TOTAL_PERS']   = access_trips_df['TOTAL_PERS'] * ANNUAL_TO_DAILY_FACTOR
    # translate STATION to relevant MTC TAZ
    access_trips_df = pandas.merge(
        left  = access_trips_df,
        right = STATION_TO_MTC_TAZ_DF,
        how   = 'left',
        on    = 'STATION'
    )
    access_trips_df.rename(columns={'ZONE':'CHSR_ZONE','TAZ1454':'ORIG_TAZ1454'}, inplace=True)
    # drop these columns -- they're duplicative
    access_trips_df.drop(columns=['ORIGIN','DESTINATION'], inplace=True)
    access_summary_df = access_trips_df.groupby(by=['year','DEST_TAZ1454','STATION']).agg(
        {'AUTO_PERS':'sum','TAXI_PERS':'sum','TRANSIT':'sum','TOTAL_PERS':'sum'})
    print("Read the following access trips:\n{}".format(access_summary_df))
    print("access_trips_df.head():\n{}".format(access_trips_df.head()))

    # read the zones intersect TAZ1454 file
    CHSR_ZONES_TAZ1454_DBF = CHSR_ROOT / "CRRM Zones/D2Zones_intersect_taz1454.dbf"
    CHSR_zones_taz1454_df = simpledbf.Dbf5(CHSR_ZONES_TAZ1454_DBF).to_dataframe()
    CHSR_zones_taz1454_df.rename(columns={'TAZ':'CHSR_ZONE'}, inplace=True)
    print("Read CHSR_ZONES_TAZ1454_DBF: {}".format(CHSR_ZONES_TAZ1454_DBF))
    print("CHSR_zones_taz1454_df.head():\n{}".format(CHSR_zones_taz1454_df.head()))


    # ===============================================================================================
    # First, let's handle the within-region access trips
    # We need to translate each CHSR zone to MTC zone.
    # 1) Create columns total_area_sqm and count_TAZ1454 to join back
    # #  to CHSR_zones_taz1454_df
    CHSR_to_MTC_zone_df = CHSR_zones_taz1454_df.groupby(by=['CHSR_ZONE']).agg(
        total_area_sqm = pandas.NamedAgg(column='area_sqm', aggfunc='sum'),
        count_TAZ1454 = pandas.NamedAgg(column='TAZ1454', aggfunc='count')
    ).reset_index(drop=False)
    # print(CHSR_to_MTC_zone_df)
    CHSR_to_MTC_zone_df = pandas.merge(
        left  = CHSR_zones_taz1454_df,
        right = CHSR_to_MTC_zone_df,
        on    = 'CHSR_ZONE',
        how   = 'left'
    )
    CHSR_to_MTC_zone_df['pct_area_sqm'] = CHSR_to_MTC_zone_df['area_sqm']/CHSR_to_MTC_zone_df['total_area_sqm']
    # join to trips
    access_trips_df = pandas.merge(
        left      = access_trips_df,
        right     = CHSR_to_MTC_zone_df, 
        on        = 'CHSR_ZONE',
        how       = 'left',
        indicator = True
    ).rename(columns={"TAZ1454":"ORIG_TAZ1454","_merge":"within_region_merge"})
    
    # select out internal only and scale by the percent area relevant to the MTC TAZ
    internal_trips_df = access_trips_df.loc[access_trips_df.within_region_merge=='both'].copy()
    # scale trips based on taz area
    internal_trips_df['AUTO_PERS']  = internal_trips_df['AUTO_PERS'] * internal_trips_df['pct_area_sqm']
    internal_trips_df['TAXI_PERS']  = internal_trips_df['TAXI_PERS'] * internal_trips_df['pct_area_sqm']
    internal_trips_df['TRANSIT']    = internal_trips_df['TRANSIT']   * internal_trips_df['pct_area_sqm']
    internal_trips_df['TOTAL_PERS'] = internal_trips_df['TOTAL_PERS']* internal_trips_df['pct_area_sqm']
    # aggregate to MTC TAZ
    internal_trips_df = internal_trips_df.groupby(by=['year','STATION','DEST_TAZ1454','ORIG_TAZ1454']).agg(
        {'AUTO_PERS':'sum','TAXI_PERS':'sum','TRANSIT':'sum', 'TOTAL_PERS':'sum'}).reset_index()
    internal_trips_df['type'] = 'internal'

    # ===============================================================================================
    # Now, we'll handle the external-to-MTC trips to Bay Area Stations

    # read the Zones
    CHSR_ZONES_DBF = CHSR_ROOT / "CRRM Zones/D2Zones.dbf"
    CHSR_zones_df = simpledbf.Dbf5(CHSR_ZONES_DBF).to_dataframe()
    print("Read CHSR_ZONES_DBF: {}".format(CHSR_ZONES_DBF))
    CHSR_zones_df.rename(columns={'TAZ':'CHSR_ZONE'}, inplace=True)
    CHSR_zones_df.drop(columns=['id','Area'], inplace=True)
    # keep only rows with an external zone
    CHSR_zones_df = CHSR_zones_df.loc[pandas.notnull(CHSR_zones_df.MTC_ex_TAZ)]
    CHSR_zones_df['CHSR_ZONE']  = CHSR_zones_df['CHSR_ZONE'].astype(int)
    CHSR_zones_df['MTC_ex_TAZ'] = CHSR_zones_df['MTC_ex_TAZ'].astype(int)
    print("CHSR_zones_df.head()\n{}".format(CHSR_zones_df.head()))
    
    # join to trips
    access_trips_df = pandas.merge(
        left      = access_trips_df,
        right     = CHSR_zones_df, 
        on        = 'CHSR_ZONE',
        how       = 'left',
        indicator = True
    ).rename(columns={"_merge":"external_merge"})

    # select out trips for external access only; don't include ones that were already counted as internal
    external_trips_df = access_trips_df.loc[(access_trips_df.within_region_merge=='left_only')&
                                            (access_trips_df.external_merge=='both')].copy()
    external_trips_df.drop(columns=['ORIG_TAZ1454'], inplace=True)
    external_trips_df.rename(columns={'MTC_ex_TAZ':'ORIG_TAZ1454'}, inplace=True)

    # collapse since many external trips come through the same MTC_ex_TAZ/ORIG_TAZ1454
    external_trips_df = external_trips_df.groupby(by=['year','STATION','DEST_TAZ1454','ORIG_TAZ1454']).agg(
        {'AUTO_PERS':'sum','TAXI_PERS':'sum','TRANSIT':'sum','TOTAL_PERS':'sum'}).reset_index()
    external_trips_df['type'] = 'external'

    # ===============================================================================================
    # put internal and external together
    int_ext_trips_df = pandas.concat([
        internal_trips_df[['year','STATION','DEST_TAZ1454','type','ORIG_TAZ1454','AUTO_PERS','TAXI_PERS','TRANSIT','TOTAL_PERS']], 
        external_trips_df[['year','STATION','DEST_TAZ1454','type','ORIG_TAZ1454','AUTO_PERS','TAXI_PERS','TRANSIT','TOTAL_PERS']].reset_index(drop=True)],
        axis='index',
        ignore_index=True)
    int_ext_trips_df['ORIG_TAZ1454'] = int_ext_trips_df['ORIG_TAZ1454'].astype(int)
    int_ext_trips_df['DEST_TAZ1454'] = int_ext_trips_df['DEST_TAZ1454'].astype(int)
    int_ext_trips_df['acc_egr'] = 'access'

    # convert person trips to vehicle trips
    int_ext_trips_df['DA_VEH']   = int_ext_trips_df['AUTO_PERS'] * AUTO_PERSON_TRIPS_TO_VEH_TRIPS['DA']
    int_ext_trips_df['SR2_VEH']  = int_ext_trips_df['AUTO_PERS'] * AUTO_PERSON_TRIPS_TO_VEH_TRIPS['SR2']
    int_ext_trips_df['TAXI_VEH'] = int_ext_trips_df['TAXI_PERS'] * TAXI_PERSON_TRIPS_TO_VEH_TRIPS
    # convert auto person trips to 
    # distribute across time periods
    for timeperiod in TIME_OF_DAY_DISTRIBUTION.keys():
        int_ext_trips_df['DA_VEH_{}'.format(timeperiod)  ] = int_ext_trips_df['DA_VEH'  ]*TIME_OF_DAY_DISTRIBUTION[timeperiod]
        int_ext_trips_df['SR2_VEH_{}'.format(timeperiod) ] = int_ext_trips_df['SR2_VEH' ]*TIME_OF_DAY_DISTRIBUTION[timeperiod]
        int_ext_trips_df['TAXI_VEH_{}'.format(timeperiod)] = int_ext_trips_df['TAXI_VEH']*TIME_OF_DAY_DISTRIBUTION[timeperiod]
        int_ext_trips_df['TRANSIT_{}'.format(timeperiod) ] = int_ext_trips_df['TRANSIT' ]*TIME_OF_DAY_DISTRIBUTION[timeperiod]
        # person trips
        int_ext_trips_df['AUTO_PERS_{}'.format(timeperiod)] = int_ext_trips_df['AUTO_PERS']*TIME_OF_DAY_DISTRIBUTION[timeperiod]
        int_ext_trips_df['TAXI_PERS_{}'.format(timeperiod)] = int_ext_trips_df['TAXI_PERS']*TIME_OF_DAY_DISTRIBUTION[timeperiod]
    # remove the non-timeperiod cols
    # int_ext_trips_df.drop(columns=['DA_VEH','SR2_VEH','TAXI_VEH','TRANSIT','TOTAL_PERS'], inplace=True)
    int_ext_trips_df.reset_index(drop=True, inplace=True)
    print("int_ext_trips_df.dtypes\n{}".format(int_ext_trips_df.dtypes))

    # ===============================================================================================
    # At this point, we have all the access trips but we need to fill in the egress trips
    # Start by using access-to-egress ratios by station and by time period from the previous RTP2021/TM1.5 input
    egress_trips_df = int_ext_trips_df.copy()
    egress_trips_df['acc_egr'] = 'egress'
    # join with ACCESS_TO_EGRESS_PERS_DF to get factors
    egress_trips_df = pandas.merge(
        how       = 'left',
        left      = egress_trips_df,
        right     = ACCESS_TO_EGRESS_PERS_DF,
        on        = ['year','DEST_TAZ1454','STATION'],
        indicator = True,
    )
    print(egress_trips_df[['DEST_TAZ1454','STATION','_merge']].value_counts())
    egress_trips_df.drop(columns=['_merge'], inplace=True)
    # reverse access trip to become egress trips
    egress_trips_df.rename(columns={'ORIG_TAZ1454':'TEMP_TAZ1454', 'DEST_TAZ1454':'ORIG_TAZ1454'}, inplace=True)
    egress_trips_df.rename(columns={'TEMP_TAZ1454':'DEST_TAZ1454'}, inplace=True)
    print("egress_trips_df.head():\n{}".format(egress_trips_df.head()))
    # multiply the access to get egress
    for timeperiod in ['AM','MD','PM','EV']:
        # use access to egress person trips by timeperiod
        for mode in ['AUTO_PERS','TAXI_PERS','TRANSIT']:
            egress_trips_df['{}_{}'.format(mode,timeperiod)] = egress_trips_df['{}_{}'.format(mode,timeperiod)]*egress_trips_df['ACC_TO_EGR_PERS_{}'.format(timeperiod)]
        egress_trips_df.drop(columns=['ACC_TO_EGR_PERS_{}'.format(timeperiod)], inplace=True)
        # convert person trips to vehicle trips by time period
        egress_trips_df['DA_VEH_{}'.format(timeperiod)]   = egress_trips_df['AUTO_PERS_{}'.format(timeperiod)] * AUTO_PERSON_TRIPS_TO_VEH_TRIPS['DA']
        egress_trips_df['SR2_VEH_{}'.format(timeperiod)]  = egress_trips_df['AUTO_PERS_{}'.format(timeperiod)] * AUTO_PERSON_TRIPS_TO_VEH_TRIPS['SR2']
        egress_trips_df['TAXI_VEH_{}'.format(timeperiod)] = egress_trips_df['TAXI_PERS_{}'.format(timeperiod)] * TAXI_PERSON_TRIPS_TO_VEH_TRIPS
    # roll up to daily
    for mode in ['AUTO_PERS','TAXI_PERS','TRANSIT','DA_VEH','SR2_VEH','TAXI_VEH']:
        egress_trips_df[mode] = \
            egress_trips_df['{}_EA'.format(mode)] + \
            egress_trips_df['{}_AM'.format(mode)] + \
            egress_trips_df['{}_MD'.format(mode)] + \
            egress_trips_df['{}_PM'.format(mode)] + \
            egress_trips_df['{}_EV'.format(mode)]
    egress_trips_df['TOTAL_PERS'] = egress_trips_df['AUTO_PERS'] + egress_trips_df['TAXI_PERS'] + egress_trips_df['TRANSIT']
    print("egress_trips_df.head():\n{}".format(egress_trips_df.head()))

    # summarize
    egress_summary_df = egress_trips_df.groupby(by=['year','ORIG_TAZ1454','STATION']).agg({
        # person trips
        'AUTO_PERS':'sum','TAXI_PERS':'sum','TRANSIT':'sum','TOTAL_PERS':'sum',
        # vehicle trips
        'DA_VEH':'sum','SR2_VEH':'sum','TAXI_VEH':'sum'
    })
    print("egress_summary_df:\n{}".format(egress_summary_df))

    # add egress trips to the access trips
    int_ext_trips_df = pandas.concat([int_ext_trips_df, egress_trips_df])

    # ===============================================================================================
    # output, one file per year
    YEARS = int_ext_trips_df['year'].drop_duplicates().to_list()
    for year in YEARS:
        int_ext_trips_by_year_df = int_ext_trips_df.loc[int_ext_trips_df.year == year]
        ACCESS_OUTPUT_FILE = pathlib.Path(str(ACCESS_OUTPUT).replace("YYYY", str(year)))
        output_df = int_ext_trips_by_year_df[['ORIG_TAZ1454','DEST_TAZ1454',
                                   'DA_VEH_EA','SR2_VEH_EA','TAXI_VEH_EA','TRANSIT_EA',
                                   'DA_VEH_AM','SR2_VEH_AM','TAXI_VEH_AM','TRANSIT_AM',
                                   'DA_VEH_MD','SR2_VEH_MD','TAXI_VEH_MD','TRANSIT_MD',
                                   'DA_VEH_PM','SR2_VEH_PM','TAXI_VEH_PM','TRANSIT_PM',
                                   'DA_VEH_EV','SR2_VEH_EV','TAXI_VEH_EV','TRANSIT_EV']].copy()
        output_df = output_df.groupby(by=['ORIG_TAZ1454','DEST_TAZ1454']).agg('sum').reset_index(drop=False)
        output_df.to_csv(ACCESS_OUTPUT_FILE, index=False, float_format='%.5f')
        print("Wrote {:,} rows to {}".format(len(output_df), ACCESS_OUTPUT_FILE))

    # create long version of person trips / vehicle trips
    ACCESS_OUTPUT_FILE = pathlib.Path(str(ACCESS_OUTPUT).replace("YYYY", "long"))
    dupes = int_ext_trips_df['dupe'] = int_ext_trips_df.duplicated(subset=['year','acc_egr','ORIG_TAZ1454','DEST_TAZ1454'])
    print(dupes)
    output_df = pandas.wide_to_long(
        df        = int_ext_trips_df[[
                        'year','acc_egr','ORIG_TAZ1454','DEST_TAZ1454',
                        'DA_VEH_EA','SR2_VEH_EA','TAXI_VEH_EA','TRANSIT_EA','AUTO_PERS_EA','TAXI_PERS_EA',
                        'DA_VEH_AM','SR2_VEH_AM','TAXI_VEH_AM','TRANSIT_AM','AUTO_PERS_AM','TAXI_PERS_AM',
                        'DA_VEH_MD','SR2_VEH_MD','TAXI_VEH_MD','TRANSIT_MD','AUTO_PERS_MD','TAXI_PERS_MD',
                        'DA_VEH_PM','SR2_VEH_PM','TAXI_VEH_PM','TRANSIT_PM','AUTO_PERS_PM','TAXI_PERS_PM',
                        'DA_VEH_EV','SR2_VEH_EV','TAXI_VEH_EV','TRANSIT_EV','AUTO_PERS_EV','TAXI_PERS_EV']],
        stubnames = ['DA_VEH','SR2_VEH','TAXI_VEH','TRANSIT','AUTO_PERS','TAXI_PERS'],
        i         = ['year','acc_egr','ORIG_TAZ1454','DEST_TAZ1454'],
        j         = 'timeperiod',
        sep       = '_',
        suffix    = '(EA|AM|MD|PM|EV)').reset_index()
    # move mode to column
    output_df = pandas.melt(
        output_df, 
        id_vars=['year','acc_egr','ORIG_TAZ1454','DEST_TAZ1454','timeperiod'],
        value_vars=['DA_VEH','SR2_VEH','TAXI_VEH','TRANSIT','AUTO_PERS','TAXI_PERS'],
        var_name='mode',
        value_name='trips')

    output_df = output_df.loc[output_df.trips > 0]
    output_df.to_csv(ACCESS_OUTPUT_FILE, index=False, float_format='%.5f')
    print("Wrote {:,} rows to {}".format(len(output_df), ACCESS_OUTPUT_FILE))

    summary_df = int_ext_trips_df.groupby(by=['year','acc_egr','STATION']).agg(
        {'AUTO_PERS':'sum','TAXI_PERS':'sum','TOTAL_PERS':'sum',
         'DA_VEH':'sum','SR2_VEH':'sum','TAXI_VEH':'sum','TRANSIT':'sum'})
         # 'TRANSIT_EA':'sum','TRANSIT_AM':'sum','TRANSIT_MD':'sum','TRANSIT_PM':'sum','TRANSIT_EV':'sum'})
    print("Trips summary:\n{}".format(summary_df))

    # ===============================================================================================
    # missing access trips - for these, the origin had no mapping to internal nor external zones
    missing_df = access_trips_df.loc[(access_trips_df.within_region_merge=='left_only') & 
                                     (access_trips_df.external_merge=='left_only') &
                                     (access_trips_df.TOTAL_PERS>0)]
    assert(len(missing_df)==0)
    # print("missing_df:\n{}".format(missing_df))
    # missing_df.to_csv("missing.csv")