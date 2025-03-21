
import pandas as pd
  
lodes_year = 2021
self_emp_year = 2020 # ignoring self employment for now
tm_year = 2023

LODES_EMPLOYMENT_byTAZ_FILE        = f"X:\\travel-model-one-v1.6.1_develop\\utilities\\taz-data-baseyears\\2020\\Employment\\lodes_wac_employment_{lodes_year}.csv"
TAZ_SUPERDISTRICT_COUNTY_FILE      = "X:\\travel-model-one-master\\utilities\\geographies\\taz-superdistrict-county.csv"
EDD_FILE                           = "M:\\Data\\California EDD\\edd_summary_county_sector_date.csv"
OUTPUT_FILE                        = f"employment_{lodes_year}_with_EDD_pct_change_applied.csv"


# Read LODES employment data
loads_byTAZ_df = pd.read_csv(LODES_EMPLOYMENT_byTAZ_FILE)
print(f"Read {len(loads_byTAZ_df):,} rows from {LODES_EMPLOYMENT_byTAZ_FILE}")

# Display the first few rows of the DataFrame
print(loads_byTAZ_df.head())

# Add county info to lodes employment by taz file
# -------------------------------------------------

# Read TAZ to county correspondence
taz_county_df = pd.read_csv(TAZ_SUPERDISTRICT_COUNTY_FILE, usecols=['ZONE','COUNTY_NAME'])
print(f"Read {len(taz_county_df):,} rows from {TAZ_SUPERDISTRICT_COUNTY_FILE}")

# Merge county info to lodes employment by taz file
lodes_emp_with_county_df = pd.merge(
    left=loads_byTAZ_df,
    right=taz_county_df,
    left_on='TAZ1454',  
    right_on='ZONE',    
    indicator=True     
)


# Verify successful merge
merge_value_counts = lodes_emp_with_county_df['_merge'].value_counts()
print(f"Merge results:\n{merge_value_counts}")

# Ensure all rows in loads_byTAZ_df matched
both_count = merge_value_counts.get('both', 0)
expected_count = len(loads_byTAZ_df)
assert both_count == expected_count, (
    f"Merge failed: {both_count} rows matched, but {expected_count} were expected. "
    f"Check left_only and right_only categories."
)

# Drop the variable _merge as it is no longer needed
lodes_emp_with_county_df = lodes_emp_with_county_df.drop(columns=['_merge'])

# Drop the variable ZONE as it is duplicative
lodes_emp_with_county_df = lodes_emp_with_county_df.drop(columns=['ZONE'])


# Process the EDD data
# -------------------------------------------------

edd_df = pd.read_csv(EDD_FILE, parse_dates=['date'])
print(edd_df.info())

# Recode the industry name
industry_mapping = {
    'Agriculture & Natural Resources': 'AGREMPN_eddchange',
    'Health, Educational & Recreational Services': 'HEREMPN_eddchange',
    'Other': 'OTHEMPN_eddchange',
    'Financial & Professional Services': 'FPSEMPN_eddchange',
    'Manufacturing, Wholesale & Transportation': 'MWTEMPN_eddchange',
    'Retail ': 'RETEMPN_eddchange' # note the space in 'Retail '
}

edd_df['industry'] = edd_df['naics_mtc'].map(industry_mapping)

# add a year column based on date
edd_df['year'] = edd_df['date'].dt.year

# Group by 'year' and calculate the average of 'value'
edd_annual_df = edd_df.groupby(['county_name', 'naics_mtc', 'industry', 'year'], as_index=False)['value'].mean()
edd_annual_df.rename(columns={'value': 'annual_employment'}, inplace=True)

# Pivot the data to create separate columns for 2021 and 2023 average values
edd_pivot_df = edd_annual_df.pivot_table(
    index=['county_name', 'naics_mtc', 'industry'], 
    columns='year', 
    values='annual_employment'
).reset_index()

# Calculate the percentage change for each county and naics_mtc
edd_pivot_df['edd_change_TmYearVsLodesYear'] = (edd_pivot_df[tm_year] / edd_pivot_df[lodes_year] - 1)
edd_pivot_df['edd_change_TmYearVsSelfEmpYear'] = (edd_pivot_df[tm_year] / edd_pivot_df[self_emp_year] - 1)
print(edd_pivot_df.head())
print(edd_pivot_df.columns)

# Pivot the data again create separate columns for each industry
edd_with_industrycols_df = edd_pivot_df.pivot_table(
    index=['county_name'], 
    columns='industry', 
    values='edd_change_TmYearVsLodesYear',  
).reset_index()

# Reorder the columns
edd_with_industrycols_df = edd_with_industrycols_df[['county_name', 'RETEMPN_eddchange', 'FPSEMPN_eddchange', 'HEREMPN_eddchange', 'AGREMPN_eddchange', 'MWTEMPN_eddchange', 'OTHEMPN_eddchange']]

# Display the resulting DataFrame
#print(edd_with_industrycols_df.head())
print(edd_with_industrycols_df.columns)

# Merge EDD percentage change to LODES employment data
# -------------------------------------------------
# Merge LODES employment data with EDD percentage changes
lodes_withEDDchanges_df = pd.merge(
    left=lodes_emp_with_county_df,
    right=edd_with_industrycols_df,
    left_on='COUNTY_NAME',  
    right_on='county_name',
    how='left',
    indicator=True    
)

# Verify successful merge
merge_value_counts = lodes_withEDDchanges_df['_merge'].value_counts()
print(f"Merge results:\n{merge_value_counts}")

# Ensure all rows in lodes_withEDDchanges_df matched
both_count = merge_value_counts.get('both', 0)
expected_count = len(lodes_emp_with_county_df)
assert both_count == expected_count, (
    f"Merge failed: {both_count} rows matched, but {expected_count} were expected. "
    f"Check left_only and right_only categories."
)

# Drop the variable _merge as it is no longer needed
lodes_withEDDchanges_df = lodes_withEDDchanges_df.drop(columns=['_merge'])

# Drop duplicate 'county_name' column if necessary
lodes_withEDDchanges_df.drop(columns=['county_name'], inplace=True)

# Calculate scaled employment numbers by industry
# -------------------------------------------------
# Calculate the scaled values for each industry (round
lodes_withEDDchanges_df['RETEMPN_scaled'] = (lodes_withEDDchanges_df['RETEMPN'] * (1 + lodes_withEDDchanges_df['RETEMPN_eddchange'])).round().astype(int)
lodes_withEDDchanges_df['FPSEMPN_scaled'] = (lodes_withEDDchanges_df['FPSEMPN'] * (1 + lodes_withEDDchanges_df['FPSEMPN_eddchange'])).round().astype(int)
lodes_withEDDchanges_df['HEREMPN_scaled'] = (lodes_withEDDchanges_df['HEREMPN'] * (1 + lodes_withEDDchanges_df['HEREMPN_eddchange'])).round().astype(int)
lodes_withEDDchanges_df['AGREMPN_scaled'] = (lodes_withEDDchanges_df['AGREMPN'] * (1 + lodes_withEDDchanges_df['AGREMPN_eddchange'])).round().astype(int)
lodes_withEDDchanges_df['MWTEMPN_scaled'] = (lodes_withEDDchanges_df['MWTEMPN'] * (1 + lodes_withEDDchanges_df['MWTEMPN_eddchange'])).round().astype(int)
lodes_withEDDchanges_df['OTHEMPN_scaled'] = (lodes_withEDDchanges_df['OTHEMPN'] * (1 + lodes_withEDDchanges_df['OTHEMPN_eddchange'])).round().astype(int)

lodes_withEDDchanges_df['TOTEMP_scaled'] = (
    lodes_withEDDchanges_df['RETEMPN_scaled'] +
    lodes_withEDDchanges_df['FPSEMPN_scaled'] +
    lodes_withEDDchanges_df['HEREMPN_scaled'] +
    lodes_withEDDchanges_df['AGREMPN_scaled'] +
    lodes_withEDDchanges_df['MWTEMPN_scaled'] +
    lodes_withEDDchanges_df['OTHEMPN_scaled']
)

# Write intermediate output lodes_withEDDchanges_df
lodes_withEDDchanges_df.to_csv('lodes_withEDDchanges_df.csv', index=False)

lodes_scaled_df = lodes_withEDDchanges_df
lodes_scaled_df = lodes_scaled_df[['TAZ1454', 'TOTEMP_scaled', 'RETEMPN_scaled', 'FPSEMPN_scaled', 'HEREMPN_scaled', 'AGREMPN_scaled', 'MWTEMPN_scaled', 'OTHEMPN_scaled']]

# rename them with the same name as the TAZ data
lodes_scaled_df = lodes_scaled_df.copy() # do this to avoid the 'A value is trying to be set on a copy of a slice from a DataFrame' warning
lodes_scaled_df.rename(columns={'TOTEMP_scaled' : 'TOTEMP'},  inplace=True)
lodes_scaled_df.rename(columns={'RETEMPN_scaled': 'RETEMPN'}, inplace=True)
lodes_scaled_df.rename(columns={'FPSEMPN_scaled': 'FPSEMPN'}, inplace=True)
lodes_scaled_df.rename(columns={'HEREMPN_scaled': 'HEREMPN'}, inplace=True)
lodes_scaled_df.rename(columns={'AGREMPN_scaled': 'AGREMPN'}, inplace=True)
lodes_scaled_df.rename(columns={'MWTEMPN_scaled': 'MWTEMPN'}, inplace=True)
lodes_scaled_df.rename(columns={'OTHEMPN_scaled': 'OTHEMPN'}, inplace=True)

# Write lodes_withEDDchanges_df to the specified OUTFILE
lodes_scaled_df.to_csv(OUTPUT_FILE, index=False)

