USAGE = """

 This is a quick companion script to estimate_WFH_from_BATS2023.ipynb so that BATS data
 and modeled data can be loaded into the same Tableau for direct comparison.

"""

import pathlib, sys
import pyreadr
import pandas as pd

WORKING_DIR = pathlib.Path("M:\\Development\\Travel Model One\\Estimation\\WFH_BATS_2023")

if __name__ == "__main__":
    # don't truncate
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)

    # this is output by this script:
    # https://github.com/BayAreaMetro/travel-model-one/blob/v1.6.1_develop/utilities/telecommute/estimate_WFH_from_BATS2023.ipynb
    BATS_FILE = WORKING_DIR / "bats_day.csv"
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
        'hh_id','person_id','empsix','age','employment','student','home_TAZ1454','work_TAZ1454','hhld_income_imputed',
        'telecommute_time','wfh','num_trips', 'made_work_trip','vmt','vmt_trips',
        'day_weight']]
    
    BATS_df['employment'] = BATS_df.employment.map( {1: 'Employed full-time', 2:'Employed part-time'})

    print(f"BATS_df.tail()\n:{BATS_df.tail()}")
    print(f"{BATS_df[['survey_year','empsix'             ]].value_counts(dropna=False)=}")
    print(f"{BATS_df[['survey_year','age'                ]].value_counts(dropna=False)=}")
    print(f"{BATS_df[['survey_year','employment'         ]].value_counts(dropna=False)=}")
    print(f"{BATS_df[['survey_year','student'            ]].value_counts(dropna=False)=}")
    print(f"{BATS_df[['survey_year','hhld_income_imputed']].value_counts(dropna=False)=}")

    # todo: upstream script doesn't pass household income for 2019 survey; income_imputed is person-based

    DOLLARS_2023_TO_2000 = 1.0/1.88
    BATS_df['inc_2000d'] = 'unset'
    BATS_df.loc[ (BATS_df.survey_year == 2023)&(BATS_df.hhld_income_imputed=='000to025k'), 'inc_2000d'] = "Less than $13k"
    BATS_df.loc[ (BATS_df.survey_year == 2023)&(BATS_df.hhld_income_imputed=='025to050k'), 'inc_2000d'] = "13k to $27k"
    BATS_df.loc[ (BATS_df.survey_year == 2023)&(BATS_df.hhld_income_imputed=='050to075k'), 'inc_2000d'] = "27k to $40k"
    BATS_df.loc[ (BATS_df.survey_year == 2023)&(BATS_df.hhld_income_imputed=='075to100k'), 'inc_2000d'] = "40k to $53k"
    BATS_df.loc[ (BATS_df.survey_year == 2023)&(BATS_df.hhld_income_imputed=='100to200k'), 'inc_2000d'] = "53k to $106k"
    BATS_df.loc[ (BATS_df.survey_year == 2023)&(BATS_df.hhld_income_imputed=='200plusk' ), 'inc_2000d'] = "More than 106k"

    BATS_df.rename(columns={
        'survey_year':'year',
        'age'        :'age_cat',
        'empsix'     :'industry',
        'day_weight' :'weight'
    }, inplace=True)
    BATS_df.loc[ pd.notnull(BATS_df.industry), 'industry'] = BATS_df.industry.str[0:3]
    BATS_df['data_type'] = 'survey'
    print(f"BATS_df.tail()\n:{BATS_df.tail()}")

    # add modeled to this
    combined_df = BATS_df.copy()

    for model_year in MODEL_RUNS.keys():

        print(f"Reading  {MODEL_RUNS[model_year]}")

        result = pyreadr.read_r(MODEL_RUNS[model_year] / "OUTPUT" / "updated_output" / "persons.RData")
        model_persons_df = result['persons'] 
        print(f"Read {len(model_persons_df):,} rows from persons.Ddata")
        print(f"persons dtypes:\n{model_persons_df.dtypes}\n\n")

        # filter to subset of columns
        model_persons_df = model_persons_df[[
            'hh_id','person_id','industry','AGE','pemploy','pstudent','taz','WorkLocation','incQ_label',
            'wfh_choice','person_trips','vmt','sampleRate'
        ]]

        # filter to worker with work locations
        model_persons_df = model_persons_df.loc[model_persons_df.WorkLocation != 0]
        print(f"Filtered to {len(model_persons_df):,} rows of persons with WorkLocations set")
        print(f"trips_df.head()\n:{model_persons_df.head()}")

        # read trips just to see if the person makes a work trip
        result = pyreadr.read_r(MODEL_RUNS[model_year] / "OUTPUT" / "updated_output" / "trips.RData")
        model_trips_df = result['trips'] 
        print(f"trips dtypes:\n{model_trips_df.dtypes}\n\n")
        model_trips_df = model_trips_df[['hh_id','person_id','tour_purpose']].copy()
        model_trips_df['made_work_trip'] = 0
        model_trips_df.loc[ model_trips_df.tour_purpose.str.startswith('work'), 'made_work_trip'] = 1
        model_trips_df = model_trips_df.groupby(['hh_id','person_id']).agg({'made_work_trip':'max'}).reset_index(drop=False)

        print(f"model_trips_df:\n{model_trips_df.head()}")

        # add that column to persons
        model_persons_df = pd.merge(
            left=model_persons_df,
            right=model_trips_df,
            how='left',
            on=['hh_id','person_id'],
            validate='one_to_one'
        )
        model_persons_df.fillna({'made_work_trip':0}, inplace=True)
        print(f"After merge, model_persons_df.head:\n{model_persons_df.head()}")

        # code age categories
        model_persons_df['age_cat'] = 'unset'
        model_persons_df.loc[model_persons_df.AGE < 5, 'age_cat'] = 'under 5'
        model_persons_df.loc[(model_persons_df.AGE >=  5) & (model_persons_df.AGE <= 15), 'age_cat'] = '5-15'
        model_persons_df.loc[(model_persons_df.AGE >= 16) & (model_persons_df.AGE <= 17), 'age_cat'] = '16-17'
        model_persons_df.loc[(model_persons_df.AGE >= 18) & (model_persons_df.AGE <= 24), 'age_cat'] = '18-24'
        model_persons_df.loc[(model_persons_df.AGE >= 25) & (model_persons_df.AGE <= 34), 'age_cat'] = '25-34'
        model_persons_df.loc[(model_persons_df.AGE >= 35) & (model_persons_df.AGE <= 44), 'age_cat'] = '35-44'
        model_persons_df.loc[(model_persons_df.AGE >= 45) & (model_persons_df.AGE <= 54), 'age_cat'] = '45-54'
        model_persons_df.loc[(model_persons_df.AGE >= 55) & (model_persons_df.AGE <= 64), 'age_cat'] = '55-64'
        model_persons_df.loc[(model_persons_df.AGE >= 65) & (model_persons_df.AGE <= 74), 'age_cat'] = '65-74'
        model_persons_df.loc[(model_persons_df.AGE >= 75), 'age_cat'] = '75 or older'
        # pemploy and pstudent
        model_persons_df['employment'] = model_persons_df.pemploy.map({
            1: 'Employed full-time',
            2: 'Employed part-time',
            3: 'Not in the labor force',
            4: 'Student under 16'
        })
        model_persons_df['student'] = model_persons_df.pstudent.map({
            1: 'Full-time student',
            2: 'Student',
            3: 'Not a student'
        })

        # for consistency
        model_persons_df.rename(columns={
            'taz'         :'home_TAZ1454',
            'WorkLocation':'work_TAZ1454',
            'wfh_choice'  :'wfh',
            'incQ_label'  :'inc_2000d',
            'person_trips':'num_trips', # note these are linked versus unlinked
        }, inplace=True)
        model_persons_df['hh_id'         ] = model_persons_df.hh_id.astype('int32')
        model_persons_df['person_id'     ] = model_persons_df.person_id.astype('int32')
        model_persons_df['home_TAZ1454'  ] = model_persons_df.home_TAZ1454.astype('int')
        model_persons_df['work_TAZ1454'  ] = model_persons_df.work_TAZ1454.astype('int')
        model_persons_df['made_work_trip'] = model_persons_df.made_work_trip.astype('int8')

        # metadata
        model_persons_df['weight'   ] = 1.0/model_persons_df.sampleRate
        model_persons_df['year'     ] = model_year
        model_persons_df['model_run'] = MODEL_RUNS[model_year]
        model_persons_df['data_type'] = 'model'

        # these have been replaced
        model_persons_df.drop(columns=['pemploy','pstudent','sampleRate','AGE'], inplace=True)
        
        print(f"Before concat, model_persons_df.tail():\n{model_persons_df.tail()}")

        combined_df = pd.concat([combined_df, model_persons_df])
        print(f"Combined_df has {len(combined_df):,} rows")

        del result, model_trips_df

    # write it out
    combined_df.to_csv(WORKING_DIR / "BATS_and_model.csv", index=False)
    print(f"Wrote {len(combined_df):,} rows to {WORKING_DIR / 'BATS_and_model.csv'}")