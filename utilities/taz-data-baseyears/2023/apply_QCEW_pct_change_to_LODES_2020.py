USAGE = """

  Since more recent data is available from QCEW (as of July 2023), this script will:
   - calculate the percent change in annual employment, by county and ABAG6 industry 
     category, from 2021 to 2023 in the QCEW annual data, and
   - apply that percent change to the 2020 employment data (which is really 2021 employment
     data -- see Note 5 in create_2020_tazdata.R).

  See discussion in Asana task: https://app.asana.com/0/0/1204885735452348/f

"""
import os, sys
import numpy, pandas

sys.path.append("..")
from common import NAICS2_EMPSIX

TAZ_EMPLOYMENT_2021_FILE        = "..\\2020\\Employment\\lodes_wac_employment_2021.csv"
TAZ_SUPERDISTRICT_COUNTY_FILE   = "X:\\travel-model-one-master\\utilities\\geographies\\taz-superdistrict-county.csv"
QCEW_FILE                       = "M:\\Data\\QCEW\\qcew_BayArea_{}_annual.csv" # arg is year
OUTPUT_FILE                     = "employment_2021_with_QCEW_pct_change_applied.csv"

if __name__ == "__main__":

    # first, read the QCEW data for 2021 and 2023
    qcew_df = pandas.concat([
        pandas.read_csv(QCEW_FILE.format(2021), 
                        usecols=['year','industry_code','county','annual_avg_emplvl'],
                        dtype={'industry_code':str}),
        pandas.read_csv(QCEW_FILE.format(2023),
                        usecols=['year','industry_code','county','annual_avg_emplvl'],
                        dtype={'industry_code':str})
    ])
    print("Read {:,} lines from 2021, 2023 QCEW".format(len(qcew_df)))

    # filter to NAICS2
    qcew_df = qcew_df.loc[
        ((qcew_df.industry_code.str.len()==2) & (qcew_df.industry_code != '10')) |    # by length, but 10 is not valid
        ((qcew_df.industry_code.str.len()==5) & (qcew_df.industry_code.str[2]=='-'))  # to catch 31-33, etc
    ]
    qcew_df.industry_code = str('NAICS ') + qcew_df.industry_code
    print("Filtered to {:,} rows with industry_code.value_counts():\n{}".format(
        len(qcew_df), qcew_df.industry_code.value_counts()))
    
    # add empsix
    qcew_df['empsix'] = qcew_df.industry_code.map(NAICS2_EMPSIX)
    assert( len(pandas.isnull(qcew_df.empsix)== 0))

    # aggregate to county, year, empsix
    qcew_df = qcew_df.groupby(by=['year','county','empsix']).aggregate({'annual_avg_emplvl':'sum'}).reset_index(drop=False)
    print("qcew_df.head:\n{}".format(qcew_df.head()))

    # pivot year to columns
    qcew_df = pandas.pivot_table(qcew_df, values='annual_avg_emplvl', index=['county','empsix'], columns=['year'])
    qcew_df.reset_index(drop=False, inplace=True)
    qcew_df.rename(columns={2021:'qcew_emp_2021', 2023:'qcew_emp_2023'}, inplace=True)

    # calculate diff and percent diff
    qcew_df['qcew_emp_diff'] = qcew_df.qcew_emp_2023 - qcew_df.qcew_emp_2021
    qcew_df['qcew_pct_diff'] = qcew_df.qcew_emp_diff / qcew_df.qcew_emp_2021

    # 8/9/2023: employment is too high -- apply half
    qcew_df['qcew_pct_diff'] = 0.5*qcew_df.qcew_pct_diff
    print("qcew_df final head():\n{}".format(qcew_df.head()))

    # read 2021 employment data
    employment_df = pandas.read_csv(TAZ_EMPLOYMENT_2021_FILE)
    print("Read {:,} lines from {}".format(
        len(employment_df), TAZ_EMPLOYMENT_2021_FILE))
    print(employment_df.head())

    # map TAZ to county
    taz_county_df = pandas.read_csv(TAZ_SUPERDISTRICT_COUNTY_FILE, usecols=['ZONE','COUNTY_NAME'])
    taz_county_df.rename(columns={'ZONE':'TAZ1454', 'COUNTY_NAME':'county'}, inplace=True)
    employment_df = pandas.merge(
        left=employment_df,
        right=taz_county_df,
        indicator = True
    )
    # verify all rows matched
    merge_value_counts = employment_df['_merge'].value_counts()
    assert(merge_value_counts['both']==len(employment_df))

    employment_df.rename(columns={
        'RETEMPN':'EMPN_RET',
        'FPSEMPN':'EMPN_FPS',
        'HEREMPN':'EMPN_HER',
        'AGREMPN':'EMPN_AGR',
        'MWTEMPN':'EMPN_MWT',
        'OTHEMPN':'EMPN_OTH'}, inplace=True)
    employment_df.drop(columns=['_merge','TOTEMP'], inplace=True)
    print(employment_df.head())

    # pivot to long employment categories
    employment_df = pandas.wide_to_long(
        employment_df,
        stubnames = 'EMPN',
        i = ['county','TAZ1454'],
        j = 'empsix',
        sep = '_',
        suffix = '\D+').reset_index(drop=False)
    employment_df.rename(columns={'EMPN':'emp_2021'}, inplace=True)
    employment_df.empsix = employment_df.empsix + str("EMPN")
    print(employment_df.head())

    # merge with QCEW pct diff by county/empsix category to estimate chage
    employment_df = pandas.merge(
        left=employment_df,
        right=qcew_df[['county','empsix','qcew_pct_diff']],
        how='left',
        on=['county','empsix'],
        indicator=True)
    # verify all rows matched
    merge_value_counts = employment_df['_merge'].value_counts()
    assert(merge_value_counts['both']==len(employment_df))
    employment_df.drop(columns=['_merge'], inplace=True)

    # convert to factor for multiplication
    employment_df['factor'] = 1.0 + employment_df.qcew_pct_diff
    # log convert inf to 1.0 
    print("Converting inf factors to 1.0:\n{}".format(
        employment_df.loc[ employment_df.factor == numpy.inf]
    ))
    employment_df.loc[ employment_df.factor == numpy.inf, 'factor'] = 1.0

    print("employment_df with qcew pct diff head():\n{}".format(employment_df.head()))
    # apply the percent diff (if non NaN)
    employment_df['emp_2023'] = employment_df.emp_2021
    employment_df.loc[ pandas.notna(employment_df.factor), 'emp_2023'] = employment_df.emp_2021*employment_df.factor

    # round result and convert to int
    employment_df.emp_2023 = employment_df.emp_2023.round(0).astype(int)
    # check if any values are negative
    assert( len(employment_df.loc[ employment_df.emp_2023 < 0])== 0)
    
    print("Final employment_df.head():\n{}".format(employment_df.head()))
    employment_2023_summary_df = employment_df.groupby(['county','empsix']).agg(
        {'emp_2021':'sum','emp_2023':'sum', 'qcew_pct_diff':'first'})
    employment_2023_summary_df['emp_diff'] = employment_2023_summary_df.emp_2023 - employment_2023_summary_df.emp_2021
    employment_2023_summary_df['pct_diff'] = employment_2023_summary_df.emp_diff/employment_2023_summary_df.emp_2021

    print('Summary:\n{}'.format(employment_2023_summary_df))
    print('Total change: {:,}'.format(employment_2023_summary_df['emp_diff'].sum()))

    # convert back to format we need -- long back to wide
    employment_2023_df = pandas.pivot_table(
        employment_df,
        values='emp_2023',
        index=['TAZ1454'],
        columns=['empsix']
    ).reset_index(drop=False)
    for col in ['AGREMPN','FPSEMPN','HEREMPN','MWTEMPN','OTHEMPN','RETEMPN']:
        employment_2023_df[col] = employment_2023_df[col].astype(int)
    employment_2023_df['TOTEMP'] = \
        employment_2023_df.AGREMPN + \
        employment_2023_df.FPSEMPN + \
        employment_2023_df.HEREMPN + \
        employment_2023_df.MWTEMPN + \
        employment_2023_df.OTHEMPN + \
        employment_2023_df.RETEMPN
    
    employment_2023_df.to_csv(OUTPUT_FILE, index=False)
    print("Wrote {:,} rows to {}".format(len(employment_2023_df), OUTPUT_FILE))
