USAGE = r"""
Post-processes outputs of the CTRAMP logsums calculation step. See RunLogsums.bat for usage.
Does the following:
    - Join logsum outputs to households so that they're easier to map; converted from logsumJoiner.R
      (https://github.com/BayAreaMetro/travel-model-one/blob/TM1.6.1/model-files/scripts/core_summaries/logsumJoiner.R)
    - Summarize accessibility markets; converted from summarizeAccessibilityMarkets.R
      (https://github.com/BayAreaMetro/travel-model-one/blob/TM1.6.1/model-files/scripts/core_summaries/AccessibilityMarkets.R)

"""
import argparse, pathlib
import pandas as pd
import numpy as np

ACCESSIBILITY_MARKET_COLUMNS = ['taz', 'walk_subzone', 'walk_subzone_label',
    'incQ', 'incQ_label', 'autoSuff', 'autoSuff_label', 'hasAV']

WORKER_FILTER = ["Full-time worker", "Part-time worker"]
STUDENT_FILTER = ["University student", "Student of non-driving age", "Student of driving age"]

def get_income_label_from_incQ(income_group):
    if income_group == 1:
        return "lowInc"
    elif income_group == 2:
        return "medInc"
    elif income_group == 3:
        return "highInc"
    elif income_group == 4:
        return "veryHighInc"
    return ""

def get_auto_label(autos, workers):
    if autos == 0:
        return "0_autos"
    elif autos < workers:
        return "autos_lt_workers"
    else:
        return "autos_ge_workers"

def get_av_label(autonomousVehicles):
    return "AV" if autonomousVehicles > 0 else "noAV"

def add_income_label_from_income(households):
    # incQ are Income Quartiles
    # there are negative incomes in the data; set the min to the actual minimum income
    min_hh_income = households['income'].min()
    households['incQ_label'] = pd.cut(
        households['income'],
        bins=[min_hh_income, 30000, 60000, 100000, float('inf')],
        labels=["lowInc", "medInc", "highInc", "veryHighInc"],
        right=False
    )
    incQ_mapping = {"lowInc": 1, "medInc": 2, "highInc": 3, "veryHighInc": 4}
    households['incQ'] = households['incQ_label'].map(incQ_mapping)

# auto sufficiency labels
AUTOSUFF_MAPPING = {
        "0_autos": 0,
        "autos_lt_workers": 1,
        "autos_ge_workers": 2
    }

# walk_subzone labels, see http://analytics.mtc.ca.gov/foswiki/Main/Household
WALK_SUBZONE_MAPPING = {
    0: "Cannot walk to transit",
    1: "Short-walk to transit",
    2: "Long-walk to transit"
}


def reformat_logsums(LOGSUMS_DIR, ITER,
                     worklogsum_file = "person_workDCLogsum.csv",
                     worklogsum_spread_file = "workDCLogsum.csv",
                     mandacc_spread_file = "mandatoryAccessibilities.csv",
                     shoplogsum_file = "tour_shopDCLogsum.csv",
                     shoplogsum_spread_file = "shopDCLogsum.csv",
                     nonmandacc_spread_file = "nonMandatoryAccessibilities.csv"):
    """
    Reformat logsums outputs. Note the CTAMP logsum step uses dummy persons and househods.
    
    """
    ### INPUT
    person_data = pd.read_csv(LOGSUMS_DIR / f"personData_{ITER}.csv")
    household_data = pd.read_csv(LOGSUMS_DIR / f"householdData_{ITER}.csv")
    indivtour_data = pd.read_csv(LOGSUMS_DIR / f"indivTourData_{ITER}.csv")

    # OUTPUT
    WORKLOGSUM_OUTFILE = LOGSUMS_DIR / worklogsum_file
    WORKLOGSUM_OUTFILE_SPREAD = LOGSUMS_DIR / worklogsum_spread_file
    MANDACC_OUTFILE_SPREAD = LOGSUMS_DIR / mandacc_spread_file
    SHOPLOGSUM_OUTFILE = LOGSUMS_DIR / shoplogsum_file
    SHOPLOGSUM_OUTFILE_SPREAD = LOGSUMS_DIR / shoplogsum_spread_file
    NONMANDACC_OUTFILE_SPREAD = LOGSUMS_DIR / nonmandacc_spread_file

    ### MANDATORY LOGSUMS - full-time work persons only
    # Join household_data into person_data
    person_data = person_data.merge(household_data, how='left', on='hh_id', validate='many_to_one')

    # Sort by person_id
    person_data = person_data.sort_values('person_id').reset_index(drop=True)

    # Make incgroup variable
    income_vals = sorted(person_data['income'].unique())
    person_data['income_group'] = person_data['income'].apply(lambda x: income_vals.index(x) + 1)

    # Create unique key -- one per taz+walksubzone
    person_data['tw_key'] = person_data.apply(
        lambda row: f"{get_income_label_from_incQ(row['income_group'])}_{get_auto_label(row['autos'], row['workers'])}_{get_av_label(row['autonomousVehicles'])}", 
        axis=1
    )

    # Another key for just taz
    person_data['key'] = person_data.apply(lambda row: f"{row['tw_key']}_subz{row['walk_subzone']}", axis=1)

    # Filter for full-time workers
    work_person_data = person_data.loc[person_data['type'] == "Full-time worker"]

    # Write work logsums for full time workers
    work_person_data[['taz', 'walk_subzone', 'autos', 'autonomousVehicles', 'income_group', 'workDCLogsum']].to_csv(
        WORKLOGSUM_OUTFILE, index=False
    )

    # Spread - with taz-only key for mapping
    person_data_spread = work_person_data[['taz', 'key', 'workDCLogsum']].pivot_table(
        index='taz', columns='key', values='workDCLogsum', aggfunc='first'
    ).reset_index()
    person_data_spread.to_csv(WORKLOGSUM_OUTFILE_SPREAD, index=False)

    # Spread - with taz+walk subzone key for consistency with old mandatoryAccessibilities file, used in BAUS accessibility calculation
    person_data_spread = work_person_data[['taz', 'walk_subzone', 'tw_key', 'workDCLogsum']].pivot_table(
        index=['taz', 'walk_subzone'], columns='tw_key', values='workDCLogsum', aggfunc='first'
    ).reset_index()
    person_data_spread = person_data_spread.rename(columns={'walk_subzone': 'subzone'})
    person_data_spread['destChoiceAlt'] = 3 * (person_data_spread['taz'] - 1) + person_data_spread['subzone']

    # Order the columns consistently with before
    column_order = [
        "lowInc_0_autos_noAV", "lowInc_autos_lt_workers_noAV", "lowInc_autos_lt_workers_AV", "lowInc_autos_ge_workers_noAV", "lowInc_autos_ge_workers_AV",
        "medInc_0_autos_noAV", "medInc_autos_lt_workers_noAV", "medInc_autos_lt_workers_AV", "medInc_autos_ge_workers_noAV", "medInc_autos_ge_workers_AV",
        "highInc_0_autos_noAV", "highInc_autos_lt_workers_noAV", "highInc_autos_lt_workers_AV", "highInc_autos_ge_workers_noAV", "highInc_autos_ge_workers_AV",
        "veryHighInc_0_autos_noAV", "veryHighInc_autos_lt_workers_noAV", "veryHighInc_autos_lt_workers_AV", "veryHighInc_autos_ge_workers_noAV", "veryHighInc_autos_ge_workers_AV",
        "destChoiceAlt", "taz", "subzone"
    ]
    person_data_spread = person_data_spread[column_order]
    person_data_spread.to_csv(MANDACC_OUTFILE_SPREAD, index=False)

    ### NON-MANDATORY LOGSUMS - individual shopping tours only
    indivtour_data = indivtour_data.merge(person_data, how='left')
    indivtour_data = indivtour_data[indivtour_data['tour_purpose'] == "shopping"]

    # Write tour logsums for shopping tours
    indivtour_data[['taz', 'walk_subzone', 'autos', 'autonomousVehicles', 'income_group', 'dcLogsum']].to_csv(
        SHOPLOGSUM_OUTFILE, index=False
    )

    # Spread
    indivtour_data_spread = indivtour_data[['taz', 'key', 'dcLogsum']].pivot_table(
        index='taz', columns='key', values='dcLogsum', aggfunc='first'
    ).reset_index()
    indivtour_data_spread.to_csv(SHOPLOGSUM_OUTFILE_SPREAD, index=False)

    # Spread - with taz+walk subzone key for consistency with old mandatoryAccessibilities file, used in BAUS accessibility calculation
    indivtour_data_spread = indivtour_data[['taz', 'walk_subzone', 'tw_key', 'dcLogsum']].pivot_table(
        index=['taz', 'walk_subzone'], columns='tw_key', values='dcLogsum', aggfunc='first'
    ).reset_index()
    indivtour_data_spread = indivtour_data_spread.rename(columns={'walk_subzone': 'subzone'})
    indivtour_data_spread['destChoiceAlt'] = 3 * (indivtour_data_spread['taz'] - 1) + indivtour_data_spread['subzone']

    # Order the columns consistently with before
    indivtour_data_spread = indivtour_data_spread[column_order]
    indivtour_data_spread.to_csv(NONMANDACC_OUTFILE_SPREAD, index=False)


def summarizeAccessibilityMarket(ITER, SAMPLESHARE,
                                 POPSYN_DIR,
                                 SIMULATION_MAIN_DIR,
                                 CORE_SUMMARIES_DIR,
                                 accessibility_outfile = "AccessibilityMarkets.csv"
                                 ):
    
    ### INPUT
    # There are two household files:
    # * the model input file from the synthesized household/population (http://analytics.mtc.ca.gov/foswiki/Main/PopSynHousehold)
    # * the model output file (http://analytics.mtc.ca.gov/foswiki/Main/Household)
    popsyn_households = pd.read_csv(POPSYN_DIR / "hhFile.csv")
    model_households = pd.read_csv(SIMULATION_MAIN_DIR / f"householdData_{ITER}.csv")
    # model output persons
    persons = pd.read_csv(SIMULATION_MAIN_DIR / f"personData_{ITER}.csv")

    ### OUTPUT
    ACCESSIBILITY_OUTFILE = CORE_SUMMARIES_DIR / accessibility_outfile

    ### households and persons
    # Rename/drop some columns and join them on household id. Also join with tazData to get the super district and county.
    popsyn_households = popsyn_households[['HHID', 'PERSONS', 'hworkers']].rename(columns={'HHID': 'hh_id'})
    model_households = model_households.drop(columns=['jtf_choice'], errors='ignore')

    # in case households aren't numeric - make the columns numeric
    for col in popsyn_households.columns:
        popsyn_households[col] = pd.to_numeric(popsyn_households[col], errors='coerce')

    households = popsyn_households.merge(model_households, on='hh_id', how='inner')

    # clean up
    del popsyn_households, model_households

    # recode a few new variables
    #   * income quartiles (`incQ`) and labels (`incQ_label`)
    #   * auto sufficiency (`autoSuff`) and labels (`autoSuff_label`)
    #   * walk subzone and labels (`walk_subzone` and `walk_subzone_label`)
    #   * has Autonomous Vehicles (`hasAV`)

    add_income_label_from_income(households)

    # # workers are hworkers capped at 4
    # households['workers'] = np.where(households['hworkers'] >= 4, 4, households['hworkers'])

    # auto sufficiency labels
    households['autoSuff_label'] = households.apply(
        lambda row: get_auto_label(row['autos'], row['hworkers']), axis=1
    )
    households['autoSuff'] = households['autoSuff_label'].map(AUTOSUFF_MAPPING)
    
    # walk subzone label
    households['walk_subzone_label'] = households['walk_subzone'].map(WALK_SUBZONE_MAPPING)

    # has Autonomous Vehicles
    households['hasAV'] = np.where(households['autonomousVehicles'] > 0, 1, 0)

    # add household attributes to persons
    persons = persons.merge(
        households[ACCESSIBILITY_MARKET_COLUMNS + ['hh_id']],
        on='hh_id', how='left', validate='many_to_one'
    )

    ### Accessibility Market Summaries
    # select workers only, and workers+students only
    workers = persons.loc[persons['type'].isin(WORKER_FILTER)]
    workers_students = persons.loc[persons['type'].isin(WORKER_FILTER + STUDENT_FILTER)]

    # summarise
    workers_summary = workers.groupby(ACCESSIBILITY_MARKET_COLUMNS)['person_id'].count().reset_index(name="num_workers")
    workers_summary = workers_summary.loc[workers_summary['num_workers'] > 0]
    workers_summary['num_workers'] = workers_summary['num_workers'] / SAMPLESHARE

    workers_students_summary = workers_students.groupby(ACCESSIBILITY_MARKET_COLUMNS)['person_id'].count().reset_index(name="num_workers_students")
    workers_students_summary = workers_students_summary.loc[workers_students_summary['num_workers_students'] > 0]
    workers_students_summary['num_workers_students'] = workers_students_summary['num_workers_students'] / SAMPLESHARE

    persons_summary = persons.groupby(ACCESSIBILITY_MARKET_COLUMNS)['person_id'].count().reset_index(name='num_persons')
    persons_summary = persons_summary.loc[persons_summary['num_persons'] > 0]   
    persons_summary['num_persons'] = persons_summary['num_persons'] / SAMPLESHARE

    acc_market_summary = persons_summary.merge(workers_summary, how='left', on=ACCESSIBILITY_MARKET_COLUMNS)
    acc_market_summary = acc_market_summary.merge(workers_students_summary, how='left', on=ACCESSIBILITY_MARKET_COLUMNS)

    # Make NAs zero
    for col in ['num_workers', 'num_workers_students', 'num_persons']:
        acc_market_summary[col] = acc_market_summary[col].fillna(0)
        acc_market_summary[col] = acc_market_summary[col].astype(int)

    acc_market_summary.to_csv(ACCESSIBILITY_OUTFILE, index=False)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description = USAGE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("--iter",
                        help="Iteration for which to configure.  If not specified, will configure for pre-run.",
                        type=int, choices=[1,2,3])
    parser.add_argument("--sampleShare", 
                        help="Sample share of the population.",
                        type=float, default=None)

    my_args = parser.parse_args()

    ITER = my_args.iter
    assert ITER > 0, "ITER environment variable not set"
    print(f"ITER        = {ITER}")
    SAMPLESHARE = my_args.sampleShare
    assert SAMPLESHARE is not None, "SAMPLESHARE environment variable not set"
    print(f"SAMPLESHARE = {SAMPLESHARE}")

    print("Reformatting logsums output")
    # first, define directory

    LOGSUMS_DIR         = pathlib.Path("logsums")
    # reformat
    reformat_logsums(LOGSUMS_DIR, ITER)
    print("Done reformatting logsums output")


    print("Summarizing accessibility markets")
    # first, define directories
    # input directories
    POPSYN_DIR          = pathlib.Path("popsyn")
    SIMULATION_MAIN_DIR = pathlib.Path("main")

    # output directory; create core_summaries directory if it doesn't exist
    CORE_SUMMARIES_DIR  = pathlib.Path("core_summaries")
    if not CORE_SUMMARIES_DIR.exists():
        CORE_SUMMARIES_DIR.mkdir()
        print(f"Created directory: {CORE_SUMMARIES_DIR}")
    else:
        print(f"Directory already exists: {CORE_SUMMARIES_DIR}")
    
    # summarize
    summarizeAccessibilityMarket(ITER, SAMPLESHARE,
                                 POPSYN_DIR,
                                 SIMULATION_MAIN_DIR,
                                 CORE_SUMMARIES_DIR)
    print("Done summarizing accessibility markets")
