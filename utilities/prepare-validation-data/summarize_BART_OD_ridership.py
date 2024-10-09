USAGE = """

  Reads BART OD-data from M:\Data\BART_ridership\\ridership_[2015,2023] excel files
  And summarizes for "typical model months" to annual numbers

  Saves file, 'avg_weekday_OD_2015_2023.csv' with columns:
  * year
  * [entry|exit]_station_code
  * [Entry|Exit] Station Name
  * [Entry|Exit] Station County
  * avg_weekday_ridership
"""

import calendar
import pathlib
import pandas as pd

BART_RIDERSHIP_DIR = pathlib.Path("M:\Data\BART_ridership")

STATION_LOOKUP_EXCEL = BART_RIDERSHIP_DIR / "station-names.xls"
STATION_LOOKUP_DF = pd.read_excel(STATION_LOOKUP_EXCEL)
# columns: Two-Letter Station Code, Station Name, County

# Travel models represent March, April, May, September, October, November
MODEL_MONTHS = [3,4,5,9,10,11]
MODEL_YEARS = [2015,2023]

if __name__ == '__main__':

    all_BART_ridership_df = pd.DataFrame()
    for year in MODEL_YEARS:
        for month_num in MODEL_MONTHS:
            
            if year == 2015:
                filename = f"Ridership_{calendar.month_name[month_num]}{year}.xlsx"
                sheet_name = "Weekday OD"
            elif year == 2023:
                filename = f"Ridership_{year}{month_num:02}.xlsx"
                sheet_name = "Avg Weekday OD"
            
            fullpath = BART_RIDERSHIP_DIR / f"ridership_{year}" / filename

            print(f"Reading {fullpath}, sheet {sheet_name}")

            BART_ridership_df = pd.read_excel(fullpath, sheet_name=sheet_name,skiprows=1, header=0, index_col=0)
            # print(BART_ridership_df.head())

            # keep only columns before 'Exits'
            cols = BART_ridership_df.columns.to_list()
            cols = cols[:cols.index('Exits')]
            BART_ridership_df = BART_ridership_df[cols]

            # and rows before 'Entries'
            rows = BART_ridership_df.index.to_list()
            rows = rows[:rows.index('Entries')]
            BART_ridership_df = BART_ridership_df.loc[rows]
            # print(BART_ridership_df.head())
            # print(BART_ridership_df.tail())

            # move index to column, "entry_station_code"
            BART_ridership_df.index.set_names("entry_station_code", inplace=True)
            BART_ridership_df.reset_index(drop=False, inplace=True)
            BART_ridership_df = pd.melt(BART_ridership_df, 
                                        id_vars="entry_station_code",
                                        var_name="exit_station_code",
                                        value_name="avg_weekday_ridership")
            # columns are now entry_station_code, exit_station_code, avg_weekday_ridership
            # print(BART_ridership_df.head())
            BART_ridership_df['year'] = year
            BART_ridership_df['month'] = month_num

            # compile it
            all_BART_ridership_df = pd.concat([all_BART_ridership_df, BART_ridership_df])

    print(f"Full ridership for {MODEL_YEARS}: {len(all_BART_ridership_df):,} rows")
    print(all_BART_ridership_df.head())

    # average across months in a year
    annual_avg_BART_ridership_df = all_BART_ridership_df.groupby(
        by=['year','entry_station_code','exit_station_code']).agg({'avg_weekday_ridership':'mean'}).reset_index(drop=False)
    print(f"Avg ridership for {MODEL_YEARS}: {len(annual_avg_BART_ridership_df):,} rows")
    print(annual_avg_BART_ridership_df.head())

    # join with station names/counties for entry/exit
    for entry_exit in ['Entry','Exit']:
        annual_avg_BART_ridership_df = pd.merge(
            left=annual_avg_BART_ridership_df,
            right=STATION_LOOKUP_DF,
            how='left',
            left_on=f'{entry_exit.lower()}_station_code',
            right_on='Two-Letter Station Code',
            validate='many_to_one'
        )
        annual_avg_BART_ridership_df.drop(columns=['Two-Letter Station Code'],inplace=True)
        annual_avg_BART_ridership_df.rename(
            columns={'Station Name':f'{entry_exit} Station Name',
                     'County':f'{entry_exit} Station County'},
            inplace=True
        )
    print(annual_avg_BART_ridership_df.head())

    output_file = BART_RIDERSHIP_DIR / "avg_weekday_OD_2015_2023.csv"
    annual_avg_BART_ridership_df.to_csv(output_file, index=False)
    print(f"Wrote {len(annual_avg_BART_ridership_df):,} rows to {output_file}")
