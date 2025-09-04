USAGE="""
Creates TAZ1454_long.csv from a BAUS file to compare with census-based versions.

Used for Assess BAUS control totals for 2020 & 2025 to see if 2023 is consistent enough with BAUS
https://app.asana.com/1/11860278793487/project/1203879112191908/task/1209239150303964?focus=true

Writes TAZ1454_long.csv in the current directory with columns
"ZONE","DISTRICT","DISTRICT_NAME","COUNTY","County_Name","Year","Variable","Value"
"""
import argparse, pathlib
import pandas as pd

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument("BAUS_dir", help="BAUS run directory")
    parser.add_argument("year", help="Model year", type=int)

    # topsheet + scenario_metrics only option?
    my_args = parser.parse_args()
    print(my_args)

    # read the taz summaries
    BAUS_dir = pathlib.Path(my_args.BAUS_dir)
    taz_summary_file = BAUS_dir / "travel_model_summaries" / f"{BAUS_dir.parts[-1]}_taz1_summary_{my_args.year}.csv"
    print(f"Reading {taz_summary_file}")
    taz_summary_df = pd.read_csv(taz_summary_file, usecols=[
    # keep only "High level variables"
        'TAZ','SD','COUNTY',
        'TOTPOP','HHPOP','GQPOP',
        'EMPRES','TOTHH','TOTEMP'
    ]).rename(columns={'COUNTY':'County_Name'})
    print(taz_summary_df.head())

    # add SD_NAME and COUNTY number
    geo_crosswalk_file = pathlib.Path(__file__) / ".." / ".." / "geographies" / "superdistrict-county.csv"
    geo_crosswalk_df = pd.read_csv(geo_crosswalk_file, usecols=['SD','SD_NAME','COUNTY','COUNTY_NAME'])
    geo_crosswalk_df.rename(columns={'COUNTY_NAME':'County_Name'}, inplace=True)
    print(f"Read from {geo_crosswalk_file.resolve()=}:\n{geo_crosswalk_df.head()}")

    taz_summary_df = pd.merge(
        left=taz_summary_df,
        right=geo_crosswalk_df,
        on=['SD','County_Name'],
        validate='many_to_one'
    )
    taz_summary_df.rename(columns={'TAZ':'ZONE','SD':'DISTRICT','SD_NAME':'DISTRICT_NAME','GQPOP':'gqpop'}, inplace=True)
    print(taz_summary_df.head())

    # melt
    taz_long_df = pd.melt(
        taz_summary_df,
        id_vars=['ZONE','DISTRICT','DISTRICT_NAME','COUNTY','County_Name'],
        var_name="Variable",
        value_name="Value"
    )
    taz_long_df['Value'] = taz_long_df['Value'].astype(int)
    taz_long_df['Year'] = my_args.year
    
    taz_long_df.to_csv("TAZ1454_long.csv", index=False)
    print(f"Wrote {len(taz_long_df)} rows to TAZ1454_long.csv")
