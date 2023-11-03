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
#     Columns include: ORIG_TAZ1454,DEST_TAZ1454,[DA,S2,TAXI,TRANSIT]_[EA,AM,MD.PM,EV]
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

MODEL_INPUTS_ROOT = BOX_ROOT / "Modeling and Surveys/Development/Travel_Model_1.6/Model_Inputs/CHSR" # check this
# MODEL_INPUTS_ROOT = pathlib.Path(".") # Don't commit
ACCESS_OUTPUT = MODEL_INPUTS_ROOT / "tripsHsr_YYYY.csv"  # year

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
    'DA': 5848 / 9276,           # DA veh trips  / total personal auto person trips
    'S2': (1147+196+137) / 9276, # S2+ veh trips / total personal auto person trips
}
TAXI_PERSON_TRIPS_TO_VEH_TRIPS = 2427/2865  # from above, taxi/tnc veh trips / person trips
print("Assuming AUTO_PERSON_TRIPS_TO_VEH_TRIPS: {}".format(AUTO_PERSON_TRIPS_TO_VEH_TRIPS))
print("Assuming TAXI_PERSON_TRIPS_TO_VEH_TRIPS: {}".format(TAXI_PERSON_TRIPS_TO_VEH_TRIPS))

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
    # convert to daily from annual
    access_trips_df['AUTO']    = access_trips_df['AUTO']    * ANNUAL_TO_DAILY_FACTOR
    access_trips_df['TAXI']    = access_trips_df['TAXI']    * ANNUAL_TO_DAILY_FACTOR
    access_trips_df['TRANSIT'] = access_trips_df['TRANSIT'] * ANNUAL_TO_DAILY_FACTOR
    access_trips_df['TOTAL']   = access_trips_df['TOTAL']   * ANNUAL_TO_DAILY_FACTOR
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
        {'AUTO':'sum','TAXI':'sum','TRANSIT':'sum'})
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
    internal_trips_df['AUTO'   ] = internal_trips_df['AUTO'   ] * internal_trips_df['pct_area_sqm']
    internal_trips_df['TAXI'   ] = internal_trips_df['TAXI'   ] * internal_trips_df['pct_area_sqm']
    internal_trips_df['TRANSIT'] = internal_trips_df['TRANSIT'] * internal_trips_df['pct_area_sqm']
    # aggregate to MTC TAZ
    internal_trips_df = internal_trips_df.groupby(by=['year','STATION','DEST_TAZ1454','ORIG_TAZ1454']).agg(
        {'AUTO':'sum','TAXI':'sum','TRANSIT':'sum'}).reset_index()
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
    external_trips_df['type'] = 'external'

    # put internal and external together
    int_ext_trips_df = pandas.concat([
        internal_trips_df[['year','STATION','DEST_TAZ1454','type','ORIG_TAZ1454','AUTO','TAXI','TRANSIT']], 
        external_trips_df[['year','STATION','DEST_TAZ1454','type','ORIG_TAZ1454','AUTO','TAXI','TRANSIT']].reset_index(drop=True)],
        axis='index',
        ignore_index=True)
    int_ext_trips_df['ORIG_TAZ1454'] = int_ext_trips_df['ORIG_TAZ1454'].astype(int)
    int_ext_trips_df['DEST_TAZ1454'] = int_ext_trips_df['DEST_TAZ1454'].astype(int)

    # convert person trips to vehicle trips
    int_ext_trips_df['DA']   = int_ext_trips_df['AUTO'] * AUTO_PERSON_TRIPS_TO_VEH_TRIPS['DA']
    int_ext_trips_df['S2']   = int_ext_trips_df['AUTO'] * AUTO_PERSON_TRIPS_TO_VEH_TRIPS['S2']
    int_ext_trips_df['TAXI'] = int_ext_trips_df['TAXI'] * TAXI_PERSON_TRIPS_TO_VEH_TRIPS
    # convert auto person trips to 
    # distribute across time periods
    for timeperiod in TIME_OF_DAY_DISTRIBUTION.keys():
        int_ext_trips_df['DA_{}'.format(timeperiod)     ] = int_ext_trips_df['DA'     ]*TIME_OF_DAY_DISTRIBUTION[timeperiod]
        int_ext_trips_df['S2_{}'.format(timeperiod)     ] = int_ext_trips_df['S2'     ]*TIME_OF_DAY_DISTRIBUTION[timeperiod]
        int_ext_trips_df['TAXI_{}'.format(timeperiod)   ] = int_ext_trips_df['TAXI'   ]*TIME_OF_DAY_DISTRIBUTION[timeperiod]
        int_ext_trips_df['TRANSIT_{}'.format(timeperiod)] = int_ext_trips_df['TRANSIT']*TIME_OF_DAY_DISTRIBUTION[timeperiod]
    int_ext_trips_df.reset_index(drop=False, inplace=True)

    # output, one file per year
    YEARS = int_ext_trips_df['year'].drop_duplicates().to_list()
    for year in YEARS:
        int_ext_trips_by_year_df = int_ext_trips_df.loc[int_ext_trips_df.year == year]
        ACCESS_OUTPUT_FILE = pathlib.Path(str(ACCESS_OUTPUT).replace("YYYY", str(year)))
        int_ext_trips_by_year_df[['ORIG_TAZ1454','DEST_TAZ1454',
                                   'DA_EA','S2_EA','TAXI_EA','TRANSIT_EA',
                                   'DA_AM','S2_AM','TAXI_AM','TRANSIT_AM',
                                   'DA_MD','S2_MD','TAXI_MD','TRANSIT_MD',
                                   'DA_PM','S2_PM','TAXI_PM','TRANSIT_PM',
                                   'DA_EV','S2_EV','TAXI_EV','TRANSIT_EV']].to_csv(
                                       ACCESS_OUTPUT_FILE, index=False, float_format='%.5f')
        print("Wrote {:,} rows to {}".format(len(int_ext_trips_by_year_df), ACCESS_OUTPUT_FILE))

    summary_df = int_ext_trips_df.groupby(by=['type','year','DEST_TAZ1454','STATION']).agg(
        {'AUTO':'sum','TAXI':'sum','TRANSIT':'sum'})

    print("Trips summary:\n{}".format(summary_df))

    # ===============================================================================================
    # missing access trips - for these, the origin had no mapping to internal nor external zones
    missing_df = access_trips_df.loc[(access_trips_df.within_region_merge=='left_only') & 
                                     (access_trips_df.external_merge=='left_only') &
                                     (access_trips_df.TOTAL>0)]
    assert(len(missing_df)==0)
    # print("missing_df:\n{}".format(missing_df))
    # missing_df.to_csv("missing.csv")