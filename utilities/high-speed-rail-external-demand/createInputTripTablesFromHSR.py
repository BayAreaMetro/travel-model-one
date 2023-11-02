#
# Create updated HSR input tables for Travel Model 1.6
# using CHSR_data_from_DB-ECO_July2023 (https://mtcdrive.box.com/s/pbf7j2taz45ulfl22ltauorninx6wwq6)
#
# Input:
#   Total access trips from CHSR zones to the 5 Bay Area CHSR station in 2040 and 2050
# Output:
#   tripsHsr_YYYY.csv: Allocation of access trips from MTC zones (using area-based calculations)
#     Columns include: ORIG_TAZ1454,DEST_TAZ1454,[DA,S2,TAXI,TRANSIT]_[EA,AM,MD.PM,EV]
#   tripsHsr_YYYY_ext.csv: Allocation of access trips from external zones
#     Columns include: ORIG_EXT_TAZ1454, DEST_1454, [DA,S2,TAXI,TRANSIT]_[EA,AM,MD,PM,EV]
# See also:
#   [some cube scripts to process these into matrices]

import pathlib
import pandas
import re
import simpledbf
import sys

BOX_ROOT = pathlib.Path("E:\Box")
EXOGENOUS_ROOT = BOX_ROOT / "Plan Bay Area 2050+/Federal and State Approvals/CARB Technical Methodology/Exogenous Forces"
CHSR_ROOT = EXOGENOUS_ROOT / "CHSR/CHSR_data_from_DB-ECO_July2023"

MODEL_INPUTS_ROOT = BOX_ROOT / "Modeling and Surveys/Development/Travel_Model_1.6/Model_Input/nonres" # check this
INTERNAL_ACCESS_OUTPUT = MODEL_INPUTS_ROOT / "tripsHsr_YYYY.csv"  # year

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

# TODO: Base this on something better; placeholder for now
TIME_OF_DAY_DISTRIBUTION = {
    'EA': 0.10,
    'AM': 0.25,
    'MD': 0.20,
    'PM': 0.25,
    'EV': 0.20
}
# Assuming the inputs to this script are person trips (being verified), these factors conver them to vehicle trips.
# TODO: Base this on something better; placeholder for now
AUTO_PERSON_TRIPS_TO_VEH_TRIPS = { # multiply by AUTO, assuming those are person trips, to get vehicle trips.
    'DA': 0.70,
    'S2': 0.20, # These do not add to one; assuming some are sharing rides with other CHSR passenger but some are getting a ride
}

if __name__ == '__main__':
    print("CHSR_ROOT={}".format(CHSR_ROOT))

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
    # translate STATION to relevant MTC TAZ
    access_trips_df = pandas.merge(
        left  = access_trips_df,
        right = STATION_TO_MTC_TAZ_DF,
        how   = 'left',
        on    = 'STATION'
    )
    access_trips_df.rename(columns={'ZONE':'CHSR_ZONE','TAZ1454':'ORIG_TAZ1454'}, inplace=True)
    # drop these columns -- they're duplicative
    access_trips_df.drop(columns=['ORIGIN','DESTINATION','TOTAL'], inplace=True)
    print("Read the following access trips:")
    print(access_trips_df.groupby(by=['year','DEST_TAZ1454','STATION']).agg(
        {'AUTO':'sum','TAXI':'sum','TRANSIT':'sum'}
    ))
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
    internal_trips_df['AUTO'   ] = internal_trips_df['AUTO'   ] * internal_trips_df['pct_area_sqm']
    internal_trips_df['TAXI'   ] = internal_trips_df['TAXI'   ] * internal_trips_df['pct_area_sqm']
    internal_trips_df['TRANSIT'] = internal_trips_df['TRANSIT'] * internal_trips_df['pct_area_sqm']
    # aggregate to MTC TAZ
    internal_trips_df = internal_trips_df.groupby(by=['year','STATION','DEST_TAZ1454','ORIG_TAZ1454']).agg(
        {'AUTO':'sum','TAXI':'sum','TRANSIT':'sum'})
    # convert person trips to vehicle trips
    internal_trips_df['DA'] = internal_trips_df['AUTO'] * AUTO_PERSON_TRIPS_TO_VEH_TRIPS['DA']
    internal_trips_df['S2'] = internal_trips_df['AUTO'] * AUTO_PERSON_TRIPS_TO_VEH_TRIPS['S2']
    # convert auto person trips to 
    # distribute across time periods
    for timeperiod in TIME_OF_DAY_DISTRIBUTION.keys():
        internal_trips_df['DA_{}'.format(timeperiod)     ] = internal_trips_df['DA'     ]*TIME_OF_DAY_DISTRIBUTION[timeperiod]
        internal_trips_df['S2_{}'.format(timeperiod)     ] = internal_trips_df['S2'     ]*TIME_OF_DAY_DISTRIBUTION[timeperiod]
        internal_trips_df['TAXI_{}'.format(timeperiod)   ] = internal_trips_df['TAXI'   ]*TIME_OF_DAY_DISTRIBUTION[timeperiod]
        internal_trips_df['TRANSIT_{}'.format(timeperiod)] = internal_trips_df['TRANSIT']*TIME_OF_DAY_DISTRIBUTION[timeperiod]
    internal_trips_df.reset_index(drop=False, inplace=True)
    print(internal_trips_df)

    # output, one file per year
    YEARS = internal_trips_df['year'].drop_duplicates().to_list()
    for year in YEARS:
        internal_trips_by_year_df = internal_trips_df.loc[internal_trips_df.year == year]
        INTERNAL_ACCESS_OUTPUT_FILE = pathlib.Path(str(INTERNAL_ACCESS_OUTPUT).replace("YYYY", str(year)))
        internal_trips_by_year_df[['ORIG_TAZ1454','DEST_TAZ1454',
                                   'DA_EA','S2_EA','TAXI_EA','TRANSIT_EA',
                                   'DA_AM','S2_AM','TAXI_AM','TRANSIT_AM',
                                   'DA_MD','S2_MD','TAXI_MD','TRANSIT_MD',
                                   'DA_PM','S2_PM','TAXI_PM','TRANSIT_PM',
                                   'DA_EV','S2_EV','TAXI_EV','TRANSIT_EV']].to_csv(INTERNAL_ACCESS_OUTPUT_FILE, index=False)
        print("Wrote {:,} rows to {}".format(len(internal_trips_by_year_df), INTERNAL_ACCESS_OUTPUT_FILE))

    # ===============================================================================================
    # Now, we'll handle the external-to-MTC trips to Bay Area Stations

    # read the Zones
    CHSR_ZONES_DBF = CHSR_ROOT / "CRRM Zones/D2Zones.dbf"
    CHSR_zones_df = simpledbf.Dbf5(CHSR_ZONES_DBF).to_dataframe()
    print("Read CHSR_ZONES_DBF: {}".format(CHSR_ZONES_DBF))
    # keep only rows with an external zone
    # CHSR_zones_df = CHSR_zones_df.loc[pandas.notnull(CHSR_zones_df.MTC_ex_TAZ)]
    print("CHSR_zones_df.head()\n{}".format(CHSR_zones_df.info()))
    