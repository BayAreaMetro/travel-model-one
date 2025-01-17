USAGE = """

 This is a quick companion script to estimate_WFH_from_BATS2023.ipynb so that BATS data
 and modeled data can be loaded into the same Tableau for direct comparison.

"""

import pathlib, sys
import pyreadr
import pandas as pd

if __name__ == "__main__":
    # don't truncate
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)

    # this is output by this script:
    # https://github.com/BayAreaMetro/travel-model-one/blob/v1.6.1_develop/utilities/telecommute/estimate_WFH_from_BATS2023.ipynb
    BATS_FILE = pathlib.Path("M:\\Development\\Travel Model One\\Estimation\\WFH_BATS_2023\\bats_day.csv")
    # Documentation: 
    MODEL_RUNS = {
        2015: pathlib.Path("M:\\Application\\Model One\\RTP2025\\IncrementalProgress\\2015_TM161_IPA_08"),
        2023: pathlib.Path("M:\\Application\\Model One\\RTP2025\\IncrementalProgress\\2023_TM161_IPA_24"),
    }

    # read BATS file
    BATS_df = pd.read_csv(BATS_FILE)
    print(f"Read {len(BATS_df):,} lines from {BATS_FILE}; dtypes:\n{BATS_df.dtypes}\n\n")
    # print(f"{BATS_df.work_county.value_counts(dropna=False)=}")
    # filter to subset of columns
    BATS_df = BATS_df[[
        'survey_year',
        'hh_id','person_id','empsix','age','employment','student','home_TAZ1454','work_TAZ1454','hhld_income_imputed_nominal_2000d',
        'wfh','num_trips', 'made_work_trip','vmt','vmt_trips',
        'day_weight']]
    print(f"BATS_df.head()\n:{BATS_df.head()}")
    print(f"{BATS_df[['survey_year','empsix'    ]].value_counts(dropna=False)=}")
    print(f"{BATS_df[['survey_year','age'       ]].value_counts(dropna=False)=}")
    print(f"{BATS_df[['survey_year','employment']].value_counts(dropna=False)=}")
    print(f"{BATS_df[['survey_year','student'   ]].value_counts(dropna=False)=}")

    # todo: upstream script doesn't pass household income for 2019 survey; income_imputed is person-based

    for model_year in MODEL_RUNS.keys():

        print(f"Reading  {MODEL_RUNS[model_year]}")

        result = pyreadr.read_r(MODEL_RUNS[model_year] / "OUTPUT" / "updated_output" / "persons.RData")
        model_persons_df = result['persons'] 
        print(f"Read {len(model_persons_df):,} rows from persons.Ddata")
        print(f"persons dtypes:\n{model_persons_df.dtypes}\n\n")

        # filter to subset of columns
        model_persons_df = model_persons_df[[
            'hh_id','person_id','industry','AGE','pemploy','pstudent','taz','county_name','WorkLocation','incQ_label',
            'wfh_choice','person_trips','vmt'
        ]]

        # filter to worker with work locations
        model_persons_df = model_persons_df.loc[model_persons_df.WorkLocation != 0]
        print(f"Filtered to {len(model_persons_df):,} rows of persons with WorkLocations set")
        print(f"trips_df.head()\n:{model_persons_df.head()}")

        # read trips just to see if the person makes a work trip
        result = pyreadr.read_r(MODEL_RUNS[model_year] / "OUTPUT" / "updated_output" / "trips.RData")
        model_trips_df = result['trips'] 
        print(f"trips dtypes:\n{model_trips_df.dtypes}\n\n")
        model_trips_df = model_trips_df[['hh_id','person_id','tour_purpose']]
        model_trips_df['make_work_trip'] = 0
        model_trips_df.loc[ model_trips_df.tour_purpose.str.startswith('work'), 'make_work_trip'] = 1
        model_trips_df = model_trips_df.groupby(['hh_id','person_id']).agg({'make_work_trip':'max'}).reset_index(drop=False)

        print(f"model_trips_df:\n{model_trips_df.head()}")

        # add that column to persons
        model_persons_df = pd.merge(
            left=model_persons_df,
            right=model_trips_df,
            how='left',
            on=['hh_id','person_id'],
            validate='one_to_one'
        )
        print(f"After merge, model_persons_df.head:\n{model_persons_df.head()}")
        del result, model_trips_df
        sys.exit()
