USAGE = """

  Converts Longitudinal Employer-Household Dynamics (LEHD) 
  Workplace Area Characteristics (WAC) to TM1 TAZ geographies and the
  six TM1 employment categories.

  Per M:\Data\Census\LEHD\DesignComparisonLODESandACSCommutingDataProducts.pdf
  The LEHD WAC data represents:

  Coverage: 
    "All jobs covered under state unemployment insurance law (95 percent of private sector
    wage and salary employment) plus most civilian federal employment. Does not cover
    the following groups: self-employment, military employment, the U.S. Postal Service, and
    informal employment. Job holders may be of any age."

  Location Definitions (Workplace and Residence)
    "The employment location is reported by employers. In some cases this may not be the
    location at which an employee performs his/her work duties. Residence location is derived from
    annual federal administrative data. LODES includes no information on commute mode, or
    whether the origin-destination flow constitutes an actual trip."
    
  However, the LEHD Origin-Destination Employment Statistics (LODES) data includes the home
  location for those workplaces. The travel model is concerned with jobs that are held by
  residents of the Bay Area, so we'll summarize those from the LODES data and scale
  down to match the jobs (by county) held by residents of the Bay Area.

  Outputs to lodes_wac_employment_YYYY.csv in the current working directory.

  This script does the following:
  1) Reads in the LEHD LODES WAC data and aggregates to TAZ (from Census 2020 blocks)
  2) Aggregates from NAICS to the ABAG6 ("empsix") industry categories
  3) Since the Travel Model is concerned with Bay Area jobs held by Bay Area residents,
     the county totals are reduced to match the county totals of jobs held by Bay Area residents,
     based upon the LEHD LODES data (which includes home location but not industry detail).
     These reductions are assumed to be in the sectors for which remote work is possible, so
     the reductions are distributed according to telework shares across empsix from PUMS 2023.
  4) Then a simple estimate of US Postal Service workers are added to the MWTEMPN totals by county
  5) County totals by empsix industries are then applied to TAZs using the original distribution
     of that employment amongst TAZs (e.g., retail employment distribution amongst Alameda county TAZs
     is assumed to be unchanged, even if the total is now reduced)
  6) The output is written to 
     CWD\lodes_wac_employment_{yyyy}.csv and a log file is written to
     CWD\lodes_wac_employment_{yyyy}.log

  Note that self-employment will be added after this script.

  See discussion in Asana tasks:
  * Create 2020 land use file v1 > Update employment data: https://app.asana.com/0/0/1204885735452348/f
  * Refresh 2023 travel model tazdata: https://app.asana.com/0/1182463234225195/1208403592422847/f
"""
import argparse, logging, pathlib, random, sys
import pandas

sys.path.append("..\..")
from common import BAY_AREA_COUNTY_FIPS, NAICS2_EMPSIX

# arg is year
LEHD_WAC_FILE   = "M:\\Data\\Census\\LEHD\\Workplace Area Characteristics (WAC)\\ca_wac_S000_JT00_{}.csv"
LEHD_LODES_FILE = "M:\\Data\\Census\\LEHD\\Origin-Destination Employment Statistics (LODES)\\LODES_Bay_Area_county_{}.csv"
CENSUS_2020_BLOCK_TO_TAZ = "M:\\Data\\GIS layers\\TM1_taz_census2020\\2020block_to_TAZ1454.csv"
TAZ_SD_COUNTY_FILE = pathlib.Path(__file__) / ".." / ".." / "geographies" / "taz-superdistrict-county.csv"
OUTPUT_FILE = "lodes_wac_employment_{}.csv"
LOG_FILE    = "lodes_wac_employment_{}.log"

# from M:\Data\Census\LEHD\LODESTechDoc.pdf
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

    # ================= Create logger =================
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(ch)
    # file handler
    fh = logging.FileHandler(LOG_FILE.format(args.year), mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(fh)
    logger.info(f"Writing to log file {LOG_FILE.format(args.year)}")

    # read the block to TAZ mapping
    BLOCK_TO_TAZ_DF = pandas.read_csv(
        CENSUS_2020_BLOCK_TO_TAZ,
        dtype={'GEOID':str})
    BLOCK_TO_TAZ_DF = BLOCK_TO_TAZ_DF[['GEOID','TAZ1454']]
    logger.info(f"Read {len(BLOCK_TO_TAZ_DF):,} rows from {CENSUS_2020_BLOCK_TO_TAZ}")
    logger.info(f"\n{BLOCK_TO_TAZ_DF}")

    # read the workplace data for this year
    wac_df = pandas.read_csv(LEHD_WAC_FILE.format(args.year), dtype={'w_geocode':str})
    logger.info("Read {:,} rows from {}".format(len(wac_df), LEHD_WAC_FILE.format(args.year)))
    # select columns with employment by sector
    wac_df = wac_df[['w_geocode', 'C000'] + ['CNS{:02d}'.format(n) for n in range(1,21)]]
    # add geoid text and filter to Bay Area counties
    wac_df['w_county_txt'] = wac_df['w_geocode'].str[:5]
    wac_df = wac_df.loc[wac_df['w_county_txt'].isin(BAY_AREA_COUNTY_FIPS.keys())]
    logger.info("Filtered to {:,} rows in Bay Area counties:\n{}".format(
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
    logger.info("After renaming CNS columns to NAICS, wac_df.head():\n{}".format(wac_df.head()))

    # sum to TAZs
    # drop w_county_txt because some TAZs are associated with multiple counties and we need to keep to just one
    # we'll add back the county later
    wac_NAICS_df = wac_df.drop(columns=['w_geocode','GEOID','w_county_txt','_merge'])
    wac_NAICS_df = wac_NAICS_df.groupby(by=['TAZ1454']).sum()
    wac_NAICS_df.reset_index(drop=False, inplace=True)
    logger.info(f"After groupby to TAZ, wac_NAICS_df.head():\n{wac_NAICS_df.head()}")

    # aggregate NAICS to EMPSIX
    wac_NAICS_df['TOTEMP'] = 0
    for (naics2,empsix) in NAICS2_EMPSIX.items():
        if empsix not in list(wac_NAICS_df.columns):
            wac_NAICS_df[empsix] = 0
        wac_NAICS_df[empsix] = wac_NAICS_df[empsix]     + wac_NAICS_df[naics2]
        wac_NAICS_df['TOTEMP'] = wac_NAICS_df['TOTEMP'] + wac_NAICS_df[naics2]
    assert(wac_NAICS_df['TOTEMP'].equals(wac_NAICS_df['C000']))

    # add back counties
    taz_county_df = pandas.read_csv(TAZ_SD_COUNTY_FILE)
    logger.info(f"Read {len(taz_county_df)} lines from {TAZ_SD_COUNTY_FILE}")
    taz_county_df = taz_county_df[['ZONE','COUNTY','COUNTY_NAME']].drop_duplicates()
    taz_county_df.rename(columns={'ZONE':'TAZ1454'}, inplace=True)
    logger.info(f"\n{taz_county_df}")

    # filter to empsix only
    wac_empsix_df = wac_NAICS_df[['TAZ1454','TOTEMP', 'RETEMPN', 'FPSEMPN', 'HEREMPN', 'AGREMPN', 'MWTEMPN', 'OTHEMPN']]
    wac_empsix_df = pandas.merge(
        left=wac_empsix_df,
        right=taz_county_df,
        how='left',
        on='TAZ1454'
    )
    logger.info(f"wac_empsix_df regional total:{wac_empsix_df.TOTEMP.sum():,}:\n{wac_empsix_df.head()}")

    # summarize to county for scaling
    wac_empsix_county_df = wac_empsix_df.drop(columns=['TAZ1454']).groupby(['COUNTY','COUNTY_NAME']).sum().reset_index(drop=False)
    logger.info(f"wac_empsix_county_df regional total:{wac_empsix_county_df.TOTEMP.sum():,}:\n{wac_empsix_county_df}")

    #### US Postal Service jobs are not included in LEHD so add an estimation of them here
    # These jobs are NAICS 491110: https://www.naics.com/naics-code-description/?code=491110 which is MWTEMP
    # Per BLS, there are approximately 1.83 Post Service Mail Carriers per thousand jobs
    # These will get added later, after the scaling below
    USPS_PER_THOUSAND_JOBS = 1.83
    county_usps_df = wac_empsix_county_df[['COUNTY','COUNTY_NAME','TOTEMP']].copy()
    county_usps_df['est_USPS_jobs'] = (county_usps_df.TOTEMP/1000.0)*USPS_PER_THOUSAND_JOBS
    county_usps_df['est_USPS_jobs'] = county_usps_df['est_USPS_jobs'].round(decimals=0).astype(int)
    logger.info(f"=> Estimated USPS workers:\n{county_usps_df}")
    county_usps_df.drop(columns='TOTEMP', inplace=True)

    #### Scaling: Since the Travel Model is concerned with Bay Area jobs held by Bay Area residents,
    # the county totals are reduced to match the county totals of jobs held by Bay Area residents,
    # based upon the LEHD LODES data (which includes home location but not industry detail).
    # These reductions are assumed to be in the sectors for which remote work is possible, so
    # the reductions are distributed according to telework shares across empsix from PUMS 2023.
    lodes_df = pandas.read_csv(LEHD_LODES_FILE.format(args.year))
    logger.info(f"Read {len(lodes_df)} from {LEHD_LODES_FILE.format(args.year)}")
    # filter to home in Bay Area *and* work in Bay Area
    lodes_df = lodes_df.loc[(lodes_df.w_county != "Outside Bay Area") &
                            (lodes_df.h_county != "Outside Bay Area")].reset_index(drop=True)
    # summarize to work county and rename for clarity
    lodes_df = lodes_df.groupby("w_county").agg({'Total_Workers':'sum'}).reset_index(drop=False)
    lodes_df.rename(columns={'w_county':'COUNTY_NAME','Total_Workers':'LODES_BayArea_ResidentWorkers'}, inplace=True)
    logger.info(f"lodes_df  regional total: {lodes_df.LODES_BayArea_ResidentWorkers.sum():,}:\n{lodes_df}")

    # put them together
    wac_empsix_county_df = pandas.merge(
        left=wac_empsix_county_df,
        right=lodes_df,
        on='COUNTY_NAME'
    )
    # this is our reduction by county
    wac_empsix_county_df['TOTEMP_minus_LODES'] = wac_empsix_county_df.TOTEMP - wac_empsix_county_df.LODES_BayArea_ResidentWorkers

    # translate reduction by county to industry sectors
    # source: PUMS WorkFromHomeInvestigation / Remote Work by Empsix
    # https://10ay.online.tableau.com/t/metropolitantransportationcommission/views/WorkFromHomeInvestigation/RemoteWorkbyEmpsix
    ACS_PUMS_2023_REMOTE_WORK_BY_EMPSIX = {
        'AGREMPN': 0.00,
        'FPSEMPN': 0.47,
        'HEREMPN': 0.23,
        'MWTEMPN': 0.13,
        'RETEMPN': 0.05,
        'OTHEMPN': 0.12
    }
    EMPSIX = list(ACS_PUMS_2023_REMOTE_WORK_BY_EMPSIX.keys())
    # distribute reductions
    wac_empsix_county_df['total_reduction'] = 0
    for sector in ACS_PUMS_2023_REMOTE_WORK_BY_EMPSIX.keys():
        wac_empsix_county_df[f'reduce_{sector}'] = wac_empsix_county_df.TOTEMP_minus_LODES * ACS_PUMS_2023_REMOTE_WORK_BY_EMPSIX[sector]
        wac_empsix_county_df[f'reduce_{sector}'] = wac_empsix_county_df[f'reduce_{sector}'].round(decimals=0).astype(int)
        wac_empsix_county_df['total_reduction'] = wac_empsix_county_df['total_reduction'] + wac_empsix_county_df[f'reduce_{sector}']

    # rounding might cause the reduction to be off by one. if so, add or remove one more by sampling
    extra_reduction = random.choices(
        population=EMPSIX, 
        weights=ACS_PUMS_2023_REMOTE_WORK_BY_EMPSIX.values(), 
        k=len(wac_empsix_county_df))
    for idx in range(len(wac_empsix_county_df)):
        if wac_empsix_county_df.at[idx, 'total_reduction'] > wac_empsix_county_df.at[idx, 'TOTEMP_minus_LODES']:
            wac_empsix_county_df.at[idx, f'reduce_{extra_reduction[idx]}'] -= 1
            wac_empsix_county_df.at[idx, 'total_reduction'] -= 1
        if wac_empsix_county_df.at[idx, 'total_reduction'] < wac_empsix_county_df.at[idx, 'TOTEMP_minus_LODES']:
            wac_empsix_county_df.at[idx, f'reduce_{extra_reduction[idx]}'] += 1
            wac_empsix_county_df.at[idx, 'total_reduction'] += 1

    logging.info(f"wac_empsix_county_df with reduction distributed (but not applied):\n{wac_empsix_county_df}")

    # apply the reductions
    wac_empsix_county_df['TOTEMP'] = 0

    for sector in ACS_PUMS_2023_REMOTE_WORK_BY_EMPSIX.keys():

        wac_empsix_county_df[sector] = wac_empsix_county_df[sector] - wac_empsix_county_df[f'reduce_{sector}']
        wac_empsix_county_df[sector] = wac_empsix_county_df[sector]
        # no negatives
        wac_empsix_county_df.loc[wac_empsix_county_df[sector] < 0, sector] = 0
        # update total
        wac_empsix_county_df['TOTEMP'] = wac_empsix_county_df['TOTEMP'] + wac_empsix_county_df[sector]
    logger.info(f"wac_empsix_county_df after reductions:\n{wac_empsix_county_df}")
    # drop columns - we're done
    wac_empsix_county_df.drop(columns=[
        'LODES_BayArea_ResidentWorkers','TOTEMP_minus_LODES','total_reduction',
        'reduce_AGREMPN','reduce_FPSEMPN','reduce_HEREMPN', 'reduce_MWTEMPN','reduce_RETEMPN','reduce_OTHEMPN'], inplace=True)

    ###### Add in estimates of USPS workers to MWTEMPN
    wac_empsix_county_df = pandas.merge(
        left=wac_empsix_county_df, 
        right=county_usps_df,
        on=['COUNTY','COUNTY_NAME']
    )
    wac_empsix_county_df['MWTEMPN'] = wac_empsix_county_df.MWTEMPN + wac_empsix_county_df.est_USPS_jobs
    wac_empsix_county_df['TOTEMP']  = wac_empsix_county_df.TOTEMP  + wac_empsix_county_df.est_USPS_jobs
    wac_empsix_county_df.set_index(keys='COUNTY_NAME', inplace=True)
    logger.info(f"wac_empsix_county_df with estimated USPS added:\n{wac_empsix_county_df}")

    # finally, translate county numbers back to TAZ numbers
    # let's do this by sampling because rounding will cause too many problems
    all_county_tazdata_df = pandas.DataFrame()
    for county in wac_empsix_county_df.index.tolist():
        wac_empsix_df_thiscounty = wac_empsix_df.loc[wac_empsix_df.COUNTY_NAME == county]
        logger.info(f"Generating employment for {county} based on these distributions:\n{wac_empsix_df_thiscounty}")        
        county_tazdata = pandas.DataFrame()
        for empsix in EMPSIX:
            num_jobs = wac_empsix_county_df.at[county, empsix]
            logging.info(f" => {empsix}: {num_jobs:,}")

            # use distribution of this empsix across TAZs in this county
            # this is a list of TAZs, each item is a job
            county_emsix_tazs = random.choices(
                population=wac_empsix_df_thiscounty['TAZ1454'].tolist(),
                weights=wac_empsix_df_thiscounty[empsix].tolist(),
                k=num_jobs
            )
            # logger.info(f"county_emsix_tazs len:{len(county_emsix_tazs):,}")
            this_county_empsix_jobs_df = pandas.DataFrame(data={
                'TAZ1454':county_emsix_tazs, 
                'COUNTY_NAME':[county]*num_jobs,
                empsix:[1]*num_jobs})
            # logger.info(f"this_county_empsix_jobs_df:\n{this_county_empsix_jobs_df}")
            this_county_empsix_jobs_df = this_county_empsix_jobs_df.groupby(by=['COUNTY_NAME','TAZ1454']).agg('sum').reset_index(drop=False)
            # logging.info(f"this_county_empsix_jobs_df=\n{this_county_empsix_jobs_df}")

            if len(county_tazdata) == 0: county_tazdata = this_county_empsix_jobs_df
            else: county_tazdata = pandas.merge(
                left=county_tazdata,
                right=this_county_empsix_jobs_df,
                on=['COUNTY_NAME','TAZ1454'],
                how='outer'
            )
            
        # logging.info(f"county_tazdata:\n{county_tazdata}")
        all_county_tazdata_df = pandas.concat([all_county_tazdata_df, county_tazdata])

    # sort by TAZ
    all_county_tazdata_df.sort_values(by='TAZ1454', inplace=True)
    # fillna and calculate TOTEMP
    all_county_tazdata_df.fillna(0, inplace=True)
    for empsix in EMPSIX: all_county_tazdata_df[empsix] = all_county_tazdata_df[empsix].astype(int)
    all_county_tazdata_df['TOTEMP'] = all_county_tazdata_df[EMPSIX].sum(axis='columns')
    logging.info(f"all_county_tazdata_df:\n{all_county_tazdata_df}")

    # make one final summary
    print(f"all_county_tazdata_df summarized to county:\n{all_county_tazdata_df.drop(columns='TAZ1454').groupby('COUNTY_NAME').agg('sum')}")

    # write result with COUNTY_NAME included
    all_county_tazdata_df.to_csv(OUTPUT_FILE.format(args.year), index=False)
    logger.info("Wrote {:,} lines to {}".format(len(all_county_tazdata_df), OUTPUT_FILE.format(args.year)))