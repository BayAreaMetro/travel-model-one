#
# Create updated HSR input tables for Travel Model 1.6
# using CHSR_data_from_DB-ECO_July2023 (https://mtcdrive.box.com/s/pbf7j2taz45ulfl22ltauorninx6wwq6)
#
# Input:
#   Total access trips from CHSR zones to the 5 Bay Area CHSR station in 2040 and 2050
# Output:
#   

import pathlib
import pandas
import re
import simpledbf

BOX_ROOT = pathlib.Path("E:\Box")
EXOGENOUS_ROOT = BOX_ROOT / "Plan Bay Area 2050+/Federal and State Approvals/CARB Technical Methodology/Exogenous Forces"
CHSR_ROOT = EXOGENOUS_ROOT / "CHSR/CHSR_data_from_DB-ECO_July2023"

if __name__ == '__main__':

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
    print(access_trips_df)

    # read the Zones
    CHSR_ZONES_DBF = CHSR_ROOT / "CRRM Zones/D2Zones.dbf"
    CHSR_zones_df = simpledbf.Dbf5(CHSR_ZONES_DBF).to_dataframe()
    print(CHSR_zones_df.head())
    
    # read the zones intersect TAZ1454 file
    CHSR_ZONES_TAZ1454_DBF = CHSR_ROOT / "CRRM Zones/D2Zones_intersect_taz1454.dbf"
    CHSR_zones_taz1454_df = simpledbf.Dbf5(CHSR_ZONES_TAZ1454_DBF).to_dataframe()
    print(CHSR_zones_taz1454_df.head())

