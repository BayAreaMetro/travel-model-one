USAGE="""

  Fetches Census Longitudinal Employer-Household Dynamics (LEHD)
  Origin-Destination Employment Statistcs (LODES) data and summarizes
  to Bay Area counties by year

"""

import argparse, io, sys, pathlib, gzip
import urllib.request
import us
import pandas as pd
import common

# XX = state (ca, etc)
# YYYY = year, 2015-2022
# ZZZ = main or aux. 
#       The main part includes jobs with both workplace and residence in the state and 
#       the aux part includes jobs with the workplace in the state and the residence outside of the state.
URL = "https://lehd.ces.census.gov/data/lodes/LODES8/XX/od/XX_od_ZZZ_JT00_YYYY.csv.gz"

WORKING_DIR = pathlib.Path("M:\Data\Census\LEHD\Origin-Destination Employment Statistics (LODES)")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument("year", help='Year of data')
    args = parser.parse_args()

    print(f"Fetching data for {args.year}")
    print(common.BAY_AREA_COUNTY_FIPS)
    print(us.states.mapping('fips', 'name'))

    full_dataframe = pd.DataFrame()

    for state in us.states.STATES_AND_TERRITORIES:

        # process aux for all states except for CA, where we'll process main as well
        parts = ['aux']
        if state.name == 'California': parts = ['aux','main']

        for part in parts:
            my_url = URL.replace("XX",state.abbr.lower())
            my_url = my_url.replace("YYYY",args.year)
            my_url = my_url.replace("ZZZ",part)

            print(f" Processing {state} {state.abbr} => {my_url}")

            try:
                response = urllib.request.urlopen(my_url)
                print(f"   response: {response}")
                # Decompress the file
                with gzip.GzipFile(fileobj=response) as f:
                    decompressed_data = f.read()
                
                # create dataframe
                my_dataframe = pd.read_csv(
                    io.StringIO(decompressed_data.decode()),
                    dtype={'w_geocode':'str', 'h_geocode':'str'})
                # print(my_dataframe.head())
        
                # add workplace and home state
                my_dataframe['w_state'] = my_dataframe['w_geocode'].str[:2].map(us.states.mapping('fips', 'name'))
                my_dataframe['h_state'] = my_dataframe['h_geocode'].str[:2].map(us.states.mapping('fips', 'name'))

                
                # add workplace and home county (if Bay Area)
                my_dataframe['w_county'] = my_dataframe['w_geocode'].str[:5].map(common.BAY_AREA_COUNTY_FIPS)
                my_dataframe['h_county'] = my_dataframe['h_geocode'].str[:5].map(common.BAY_AREA_COUNTY_FIPS)


                # for California, keep home or work county in Bay Area
                if state.name == "California":
                    my_dataframe = my_dataframe.loc[pd.notna(my_dataframe.h_county) |
                                                    pd.notna(my_dataframe.w_county)].reset_index(drop=True)
                
                # for non-California, workplace will be in that state -- we only care about home county in the Bay Area
                if state.name != "California":
                    # keep only h_county in Bay Area
                    my_dataframe = my_dataframe.loc[pd.notna(my_dataframe.h_county)].reset_index(drop=True)

                # fill na for groupby
                my_dataframe.fillna({
                    'w_state':'Outside US', 
                    'h_state':'Outside US',
                    'w_county':'Outside Bay Area', 
                    'h_county':'Outside Bay Area'
                }, inplace=True)

                # finally, just aggregate to tract id; block is too much
                my_dataframe['w_tract'] = my_dataframe['w_geocode'].str[:11]
                my_dataframe['h_tract'] = my_dataframe['h_geocode'].str[:11]

                # print(my_dataframe.head())

                my_dataframe = my_dataframe.groupby(['w_state','h_state','w_county','h_county','w_tract','h_tract']).agg(
                    Total_Workers=pd.NamedAgg(column="S000", aggfunc="sum"),
                ).reset_index(drop=False)
                print(f"   appending {len(my_dataframe):,} rows")

                # print(my_dataframe.head())
                full_dataframe = pd.concat([full_dataframe, my_dataframe])

            except Exception as e:
                print(f"Exception {e}")

    output_file = WORKING_DIR / f"LODES_Bay_Area_tract_{args.year}.csv"
    full_dataframe.to_csv(output_file, index=False)
    print(f"Wrote {len(full_dataframe)} rows to {output_file}")

    # create county version
    full_dataframe = full_dataframe.groupby(['w_state','h_state','w_county','h_county']).agg(
        Total_Workers=pd.NamedAgg(column="Total_Workers", aggfunc="sum"),
    ).reset_index(drop=False)
    print(f"Aggregated to county")

    output_file = WORKING_DIR / f"LODES_Bay_Area_county_{args.year}.csv"
    full_dataframe.to_csv(output_file, index=False)
    print(f"Wrote {len(full_dataframe)} rows to {output_file}")
