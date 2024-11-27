USAGE = """

  Converts Longitudinal Employer-Household Dynamics (LEHD) 
  Origin-Destination Employment Statistics (LODES) 
  Workplace Area Characteristics (WAC) to TM1 TAZ geographies and the
  six TM1 employment categories.

  Outputs to lodes_wac_employment.csv in the current working directory.

  Note: this file does *not* do any scaling, for totals nor to remove incommute.

  See discussion in Asana task: https://app.asana.com/0/0/1204885735452348/f
"""
import argparse, sys
import pandas

sys.path.append("..\..")
from common import BAY_AREA_COUNTY_FIPS, NAICS2_EMPSIX

# arg is year
WAC_FILE = "M:\\Data\\Census\\LEHD\\Workplace Area Characteristics (WAC)\\ca_wac_S000_JT00_{}.csv"
CENSUS_2020_BLOCK_TO_TAZ = "M:\\Data\\GIS layers\\TM1_taz_census2020\\2020block_to_TAZ1454.csv"
OUTPUT_FILE = "lodes_wac_employment_{}.csv"

# from LODESTechDoc8.0.pdf
CNS_NAICS = {
    'CNS01': 'NAICS 11',    # Agriculture, Forestry, Fishing and Hunting
    'CNS02': 'NAICS 21',    # Mining, Quarrying, and Oil and Gas Extraction
    'CNS03': 'NAICS 22',    # Utilities
    'CNS04': 'NAICS 23',    # Construction
    'CNS05': 'NAICS 31-33', # Manufacturing
    'CNS06': 'NAICS 42',    # Wholesale Trade
    'CNS07': 'NAICS 44-45', # Retail Trade
    'CNS08': 'NAICS 48-49', # Transportation and Warehousing
    'CNS09': 'NAICS 51',    # Information
    'CNS10': 'NAICS 52',    # Finance and Insurance
    'CNS11': 'NAICS 53',    # Real Estate and Rental and Leasing
    'CNS12': 'NAICS 54',    # Professional, Scientific, and Technical Services
    'CNS13': 'NAICS 55',    # Management of Companies and Enterprises
    'CNS14': 'NAICS 56',    # Administrative and Support and Waste Management and Remediation Services
    'CNS15': 'NAICS 61',    # Educational Services
    'CNS16': 'NAICS 62',    # Health Care and Social Assistance
    'CNS17': 'NAICS 71',    # Arts, Entertainment, and Recreation
    'CNS18': 'NAICS 72',    # Accomodation and Food Services
    'CNS19': 'NAICS 81',    # Other Services [except Public Administration]
    'CNS20': 'NAICS 92'     # Public Administration
}


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument("year", help='Year of data')
    args = parser.parse_args()

    # read the block to TAZ mapping
    BLOCK_TO_TAZ_DF = pandas.read_csv(CENSUS_2020_BLOCK_TO_TAZ)
    BLOCK_TO_TAZ_DF = BLOCK_TO_TAZ_DF[['GEOID','TAZ1454']]

    # read the workplace data for this year
    wac_df = pandas.read_csv(WAC_FILE.format(args.year))
    print("Read {:,} rows from {}".format(len(wac_df), WAC_FILE.format(args.year)))
    # select columns with employment by sector
    wac_df = wac_df[['w_geocode', 'C000'] + ['CNS{:02d}'.format(n) for n in range(1,21)]]
    # add geoid text and filter to Bay Area counties
    wac_df['w_county_txt'] = wac_df['w_geocode'].apply(str)
    wac_df['w_county_txt'] = '0' + wac_df['w_county_txt'].str[:4]
    wac_df = wac_df.loc[wac_df['w_county_txt'].isin(BAY_AREA_COUNTY_FIPS.keys())]
    print("Filtered to {:,} rows in Bay Area counties:\n{}".format(
        len(wac_df),
        wac_df['w_county_txt'].value_counts()))

    # join to BLOCK_TO_TAZ_DF
    wac_df = pandas.merge(
        left      = wac_df,
        right     = BLOCK_TO_TAZ_DF,
        left_on   = 'w_geocode',
        right_on  = 'GEOID',
        how       = 'left',
        indicator = True
    )
    # verify all rows matched
    merge_value_counts = wac_df['_merge'].value_counts()
    assert(merge_value_counts['both']==len(wac_df))

    # rename CNS to NAICS
    wac_df.rename(columns=CNS_NAICS, inplace=True)
    print("After renaming CNS columns to NAICS, wac_df.head():\n{}".format(wac_df.head()))

    # sum to TAZs
    wac_NAICS_df = wac_df.drop(columns=['w_geocode','w_county_txt','GEOID','_merge']).groupby(by=['TAZ1454']).sum()
    wac_NAICS_df.reset_index(drop=False, inplace=True)
    print("After groupby to TAZ, wac_NAICS_df.head():\n".format(wac_NAICS_df.head()))

    # aggregate NAICS to EMPSIX
    wac_NAICS_df['TOTEMP'] = 0
    for (naics2,empsix) in NAICS2_EMPSIX.items():
        if empsix not in list(wac_NAICS_df.columns):
            wac_NAICS_df[empsix] = 0
        wac_NAICS_df[empsix] = wac_NAICS_df[empsix]     + wac_NAICS_df[naics2]
        wac_NAICS_df['TOTEMP'] = wac_NAICS_df['TOTEMP'] + wac_NAICS_df[naics2]
    print(wac_NAICS_df.head())
    assert(wac_NAICS_df['TOTEMP'].equals(wac_NAICS_df['C000']))

    # write result
    wac_NAICS_df[['TAZ1454', 'TOTEMP', 'RETEMPN', 'FPSEMPN', 'HEREMPN', 'AGREMPN', 'MWTEMPN', 'OTHEMPN']].to_csv(
        OUTPUT_FILE.format(args.year), index=False
    )
    print("Wrote {:,} lines to {}".format(len(wac_NAICS_df), OUTPUT_FILE.format(args.year)))