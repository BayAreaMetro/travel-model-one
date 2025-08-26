"""
Maintain regional growth but invest all growth into SF
"""
# %%
import pandas as pd

taz_summary_2035 = "M:/urban_modeling/baus//PBA50Plus/PBA50Plus_FinalBlueprint/PBA50Plus_Final_Blueprint_v65/travel_model_summaries/PBA50Plus_Final_Blueprint_v65_taz1_summary_2035.csv"
taz_summary_2020 = "M:/urban_modeling/baus//PBA50Plus/PBA50Plus_FinalBlueprint/PBA50Plus_Final_Blueprint_v65/travel_model_summaries/PBA50Plus_Final_Blueprint_v65_taz1_summary_2020.csv"

taz_summary = pd.read_csv(taz_summary_2035)
taz_np = pd.read_csv(taz_summary_2020)

# Calculate total growth in the region from 2020 to 2035 - household, persons, jobs, residential units, and employed residents


# Calculate total household growth by income group
total_hhin1_growth = taz_summary['HHINCQ1'].sum() - taz_np['HHINCQ1'].sum()
total_hhin2_growth = taz_summary['HHINCQ2'].sum() - taz_np['HHINCQ2'].sum()
total_hhin3_growth = taz_summary['HHINCQ3'].sum() - taz_np['HHINCQ3'].sum()
total_hhin4_growth = taz_summary['HHINCQ4'].sum() - taz_np['HHINCQ4'].sum()
total_hh_growth = taz_summary['TOTHH'].sum() - taz_np['TOTHH'].sum()
print(total_hh_growth)  # Print total household growth for verification


# Calculate total population growth by age group
total_age0004_growth = taz_summary['AGE0004'].sum() - taz_np['AGE0004'].sum()
total_age0519_growth = taz_summary['AGE0519'].sum() - taz_np['AGE0519'].sum()
total_age2044_growth = taz_summary['AGE2044'].sum() - taz_np['AGE2044'].sum()
total_age4564_growth = taz_summary['AGE4564'].sum() - taz_np['AGE4564'].sum()
total_age65p_growth = taz_summary['AGE65P'].sum() - taz_np['AGE65P'].sum()
total_pp_growth = taz_summary['TOTPOP'].sum() - taz_np['TOTPOP'].sum()

# Calculate total job growth by job type
total_agrempn_growth = taz_summary['AGREMPN'].sum() - taz_np['AGREMPN'].sum()
total_fpsempn_growth = taz_summary['FPSEMPN'].sum() - taz_np['FPSEMPN'].sum()
total_herempn_growth = taz_summary['HEREMPN'].sum() - taz_np['HEREMPN'].sum()
total_retempn_growth = taz_summary['RETEMPN'].sum() - taz_np['RETEMPN'].sum()
total_mwtempn_growth = taz_summary['MWTEMPN'].sum() - taz_np['MWTEMPN'].sum()
total_othempn_growth = taz_summary['OTHEMPN'].sum() - taz_np['OTHEMPN'].sum()
total_job_growth = taz_summary['TOTEMP'].sum() - taz_np['TOTEMP'].sum()


# Calculate total residential unit growth
total_res_units_growth = taz_summary['RES_UNITS'].sum() - taz_np['RES_UNITS'].sum()

# Calculate total employed resident growth
total_emp_res_growth = taz_summary['EMPRES'].sum() - taz_np['EMPRES'].sum()


# Pinpoint San Francisco TAZs or Superdistricts
sf_tazs = taz_np[taz_np['COUNTY'] == 'San Francisco']

# If scaling only superdistrictis with low VMT:
sf_tazs = taz_np[(taz_np['COUNTY'] == 'San Francisco') & (taz_np['SD'].isin([1,3]))]
print(sf_tazs[['TAZ','HHINCQ1', 'HHINCQ2', 'HHINCQ3', 'HHINCQ4', 'TOTHH', "TOTPOP", 'TOTEMP', 'RES_UNITS', 'EMPRES']])  # Display the first few rows of the DataFrame


## Applying growth proprotional to current distribution within SF 

## Distribute household growth
print(sf_tazs[['HHINCQ1', 'HHINCQ2', 'HHINCQ3', 'HHINCQ4', 'TOTHH']])
sf_tazs['HHINCQ1'] += round((sf_tazs['HHINCQ1'] / sf_tazs['HHINCQ1'].sum()) * total_hhin1_growth, 0)
sf_tazs['HHINCQ2'] += round((sf_tazs['HHINCQ2'] / sf_tazs['HHINCQ2'].sum()) * total_hhin2_growth, 0)
sf_tazs['HHINCQ3'] += round((sf_tazs['HHINCQ3'] / sf_tazs['HHINCQ3'].sum()) * total_hhin3_growth, 0)
sf_tazs['HHINCQ4'] += round((sf_tazs['HHINCQ4'] / sf_tazs['HHINCQ4'].sum()) * total_hhin4_growth, 0)

sf_tazs['TOTHH_P'] = sf_tazs['TOTHH']
sf_tazs['TOTHH'] = sf_tazs['HHINCQ1'] + sf_tazs['HHINCQ2'] + sf_tazs['HHINCQ3'] + sf_tazs['HHINCQ4']

sf_tazs['hh_scale'] = (sf_tazs['TOTHH'] - sf_tazs['TOTHH_P']) / sf_tazs['TOTHH_P']
sf_tazs['HH_KIDS_YES'] += round(sf_tazs['HH_KIDS_YES'] * sf_tazs['hh_scale'], 0)
sf_tazs['HH_KIDS_NO'] += round(sf_tazs['HH_KIDS_NO'] * sf_tazs['hh_scale'], 0)

sf_tazs['HH_WRKS_0'] += round(sf_tazs['HH_WRKS_0'] * sf_tazs['hh_scale'], 0)
sf_tazs['HH_WRKS_1'] += round(sf_tazs['HH_WRKS_1'] * sf_tazs['hh_scale'], 0)
sf_tazs['HH_WRKS_2'] += round(sf_tazs['HH_WRKS_2'] * sf_tazs['hh_scale'], 0)
sf_tazs['HH_WRKS_3_PLUS'] += round(sf_tazs['HH_WRKS_3_PLUS'] * sf_tazs['hh_scale'], 0)

sf_tazs['HH_SIZE_1'] += round(sf_tazs['HH_SIZE_1'] * sf_tazs['hh_scale'], 0)
sf_tazs['HH_SIZE_2'] += round(sf_tazs['HH_SIZE_2'] * sf_tazs['hh_scale'], 0)
sf_tazs['HH_SIZE_3'] += round(sf_tazs['HH_SIZE_3'] * sf_tazs['hh_scale'], 0)
sf_tazs['HH_SIZE_4_PLUS'] += round(sf_tazs['HH_SIZE_4_PLUS'] * sf_tazs['hh_scale'], 0)


## Applying age scalers and growth for population variables
sf_tazs['AGE0004'] += round((sf_tazs['AGE0004'] / sf_tazs['AGE0004'].sum()) * total_age0004_growth, 0)
sf_tazs['AGE0519'] += round((sf_tazs['AGE0519'] / sf_tazs['AGE0519'].sum()) * total_age0519_growth, 0)
sf_tazs['AGE2044'] += round((sf_tazs['AGE2044'] / sf_tazs['AGE2044'].sum()) * total_age2044_growth, 0)
sf_tazs['AGE4564'] += round((sf_tazs['AGE4564'] / sf_tazs['AGE4564'].sum()) * total_age4564_growth, 0)
sf_tazs['AGE65P'] += round((sf_tazs['AGE65P'] / sf_tazs['AGE65P'].sum()) * total_age65p_growth, 0)
sf_tazs['TOTPOP_P'] = sf_tazs['TOTPOP']
sf_tazs['TOTPOP'] = sf_tazs['AGE0519'] + sf_tazs['AGE2044'] + sf_tazs['AGE4564'] + sf_tazs['AGE65P']

sf_tazs['pop_scale'] = (sf_tazs['TOTPOP'] - sf_tazs['TOTPOP_P']) / sf_tazs['TOTPOP_P']
sf_tazs['HHPOP'] += round(sf_tazs['HHPOP'] * sf_tazs['pop_scale'], 0)
sf_tazs['GQPOP'] += round(sf_tazs['GQPOP'] * sf_tazs['pop_scale'], 0 )
sf_tazs['GQ_TYPE_MIL'] += round(sf_tazs['GQ_TYPE_MIL'] * sf_tazs['pop_scale'], 0)
sf_tazs['GQ_TYPE_UNIV'] += round(sf_tazs['GQ_TYPE_UNIV'] * sf_tazs['pop_scale'], 0)
sf_tazs['GQ_TYPE_OTHNON'] += round(sf_tazs['GQ_TYPE_OTHNON'] * sf_tazs['pop_scale'], 0)
sf_tazs['GQ_TOT_POP'] = sf_tazs['GQ_TYPE_MIL'] + sf_tazs['GQ_TYPE_UNIV'] + sf_tazs['GQ_TYPE_OTHNON']


## Applying job growth
sf_tazs['AGREMPN'] += round((sf_tazs['AGREMPN'] / sf_tazs['AGREMPN'].sum()) * total_agrempn_growth, 0)
sf_tazs['FPSEMPN'] += round((sf_tazs['FPSEMPN'] / sf_tazs['FPSEMPN'].sum()) * total_fpsempn_growth, 0)
sf_tazs['HEREMPN'] += round((sf_tazs['HEREMPN'] / sf_tazs['HEREMPN'].sum()) * total_herempn_growth, 0)
sf_tazs['RETEMPN'] += round((sf_tazs['RETEMPN'] / sf_tazs['RETEMPN'].sum()) * total_retempn_growth, 0)
sf_tazs['MWTEMPN'] += round((sf_tazs['MWTEMPN'] / sf_tazs['MWTEMPN'].sum()) * total_mwtempn_growth, 0)
sf_tazs['OTHEMPN'] += round((sf_tazs['OTHEMPN'] / sf_tazs['OTHEMPN'].sum()) * total_othempn_growth, 0)
sf_tazs['TOTEMP'] = sf_tazs['AGREMPN'] + sf_tazs['FPSEMPN'] + sf_tazs['HEREMPN'] + sf_tazs['RETEMPN'] + sf_tazs['MWTEMPN'] + sf_tazs['OTHEMPN']
print(f"Total employment in SF TAZs: {sf_tazs['TOTEMP'].sum()}")
print(f"Total Job Growth: {total_job_growth}")  # Print total job growth

## Adjust for units
sf_tazs['RES_UNITS_P'] = sf_tazs['RES_UNITS']
sf_tazs['RES_UNITS'] += round((sf_tazs['RES_UNITS'] / sf_tazs['RES_UNITS'].sum()) * total_res_units_growth, 0)
sf_tazs['units_scale'] = (sf_tazs['RES_UNITS'] - sf_tazs['RES_UNITS_P']) / sf_tazs['RES_UNITS_P']
sf_tazs['MFDU'] += round(sf_tazs['MFDU'] * sf_tazs['units_scale'], 0)
sf_tazs['SFDU'] += round(sf_tazs['SFDU'] * sf_tazs['units_scale'], 0)

sf_tazs['EMPRES'] += round((sf_tazs['EMPRES'] / sf_tazs['EMPRES'].sum()) * total_emp_res_growth, 0)
print(sf_tazs)  # Display the updated DataFrame

# Update density variables
sf_tazs['DENSITY_POP'] = sf_tazs['TOTPOP'] / sf_tazs['TOTACRE']
sf_tazs['DENSITY_EMP'] = (sf_tazs['TOTEMP'] * 2.5) / sf_tazs['TOTACRE']
sf_tazs['DENSITY'] = sf_tazs['DENSITY_POP'] + sf_tazs['DENSITY_EMP']


taz_output = taz_np.copy()  # Create a copy of the original DataFrame to avoid modifying it directly
taz_output.update(sf_tazs)  # Update the original DataFrame with the new values
print(taz_output[['COUNTY', 'SD', 'TOTHH', 'TOTPOP', 'TOTEMP']].head())  # Display the updated DataFrame

## Create county marginal csv
county_marginal = pd.DataFrame(index = taz_output['COUNTY'].unique())
county_marginal['gqpop'] = taz_output.groupby('COUNTY').GQ_TOT_POP.sum()
county_marginal['pop'] = taz_output.groupby('COUNTY').HHPOP.sum()
county_marginal[['hh_wrks_1', 'hh_wrks_2', 'hh_wrks_3']] = taz_output.groupby('COUNTY').agg({'HH_WRKS_1': 'sum', 'HH_WRKS_2': 'sum', 'HH_WRKS_3_PLUS': 'sum'})
county_marginal['workers'] = taz_output.groupby('COUNTY').TOTEMP.sum()
county_marginal[['pers_occ_management', 'pers_occ_professional','pers_occ_services','pers_occ_retail', 'pers_occ_manual','pers_occ_military']] = taz_output.groupby('COUNTY').agg({
    'AGREMPN': 'sum', 'FPSEMPN': 'sum', 'HEREMPN': 'sum', 'RETEMPN': 'sum', 'MWTEMPN': 'sum', 'OTHEMPN': 'sum'})

taz_output.to_csv("M:/Application/Model One/RTP2025/lowVMT_stress_test/taz_summaries_SF_SD_Growth_2035.csv", index=False)
county_marginal.to_csv("M:/Application/Model One/RTP2025/lowVMT_stress_test/county_marginal_SF_SD_Growth_2035.csv")

