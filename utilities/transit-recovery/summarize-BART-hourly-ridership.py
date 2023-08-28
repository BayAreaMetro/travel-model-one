USAGE = """
  This script is to summarize BART hourly ridership data so that it's relevant for TM modeling
  summaries, including looking at the changes in distance distributions over time.
  
"""
import datetime, pathlib, sys
import pandas
import pandas.tseries.holiday

# files are "date-hour-soo-dest-YYYY.csv"
# columns are Day, Hour, Origin Station, Destination Station, and Trip Count
HOURLY_RIDERSHIP_DIR = pathlib.Path("M:\\Data\\Transit\\BART\\Hourly Ridership Data")

# 2-letter code, Name, GTFS stop_id
BART_STATIONS_FILE = "BART_stations.csv"

# OD Stations to distances
BART_OD_DISTS = pathlib.Path("M:\\Data\\Transit\\511\\2023-08-GTFSTransitData_BA-orig-dest-distances.csv")

# output files
MONTHLY_HOURLY_RIDERSHIP_OUTPUT     = HOURLY_RIDERSHIP_DIR.parents[0] / "BART-hourly-ridership.csv"
MONTHLY_TIMEPERIOD_RIDERSHIP_OUTPUT = HOURLY_RIDERSHIP_DIR.parents[0] / "BART-timeperiod-ridership.csv"

if __name__ == '__main__':
    pandas.set_option("display.max_columns", 40)
    pandas.set_option("display.max_rows", 10000)
    pandas.set_option("display.width",     5000)

    BART_dist_df = pandas.read_csv(BART_OD_DISTS)
    print(BART_dist_df.head())

    cal = pandas.tseries.holiday.USFederalHolidayCalendar()

    all_ridership_df = pandas.DataFrame()
    for file in HOURLY_RIDERSHIP_DIR.glob("date-hour-soo-dest-*.csv"):
        year = int(str(file)[-8:-4])

        date_range = pandas.date_range(start='{}-01-01'.format(year), end='{}-12-31'.format(year))
        holidays = cal.holidays(start=date_range.min(), end=date_range.max())
        # print(holidays)

        ridership_df = pandas.read_csv(
            file, names=['day','hour','origin_station','destination_station','trip_count'],
            parse_dates=['day'])
        print("Read {:,} rows from {}".format(len(ridership_df), file))

        ridership_df['day_of_week'] = ridership_df['day'].dt.day_name()
        ridership_df['year'] = ridership_df['day'].dt.year
        ridership_df['month'] = ridership_df['day'].dt.month
        ridership_df['is_holiday'] = ridership_df['day'].isin(holidays)
        # fill in TM timeperiod
        # https://github.com/BayAreaMetro/modeling-website/wiki/TimePeriods
        ridership_df['timeperiod'] = 'EV'
        ridership_df.loc[ (ridership_df.hour >= 3)&(ridership_df.hour< 6),'timeperiod'] = 'EA'
        ridership_df.loc[ (ridership_df.hour >= 6)&(ridership_df.hour<10),'timeperiod'] = 'AM'
        ridership_df.loc[ (ridership_df.hour >=10)&(ridership_df.hour<15),'timeperiod'] = 'MD'
        ridership_df.loc[ (ridership_df.hour >=15)&(ridership_df.hour<19),'timeperiod'] = 'PM'
        # print(ridership_df[['hour','timeperiod']].value_counts())
        # print(ridership_df.head())
        # print(ridership_df.dtypes)

        # drop holidays
        ridership_df = ridership_df.loc[ ridership_df.is_holiday==False ]
        # keep only Tues, Wed, Thurs
        ridership_df = ridership_df.loc[ ridership_df.day_of_week.isin(['Tuesday','Wednesday','Thursday']) ]
        print("Filtered to {:,} rows after dropping holidays, weekends, Mondays and Fridays".format(
            len(ridership_df)
        ))

        day_count_df = ridership_df.groupby(by=['year','month']).agg(
            num_avg_weekdays = pandas.NamedAgg(column='day', aggfunc='nunique')
        ).reset_index()
        # print(day_count_df)

        ridership_df = ridership_df.groupby(
            by=['year','month','timeperiod','hour','origin_station','destination_station']).agg(
            trip_count = pandas.NamedAgg(column='trip_count', aggfunc='sum')
        ).reset_index(drop=False)
        print("Aggregated to {:,} rows with monthly counts".format(len(ridership_df)))

        # join with day_count
        ridership_df = pandas.merge(
            left=ridership_df,
            right=day_count_df,
            how='left'
        )
        ridership_df['avg_daily_trips'] = ridership_df['trip_count']/ridership_df['num_avg_weekdays']
        # print(ridership_df.head())

        # join with distanes
        ridership_df = pandas.merge(
            left=ridership_df,
            right=BART_dist_df,
            left_on=['origin_station','destination_station'],
            right_on=['stop_id_A','stop_id_B'],
            how='left',
            indicator=True
        )
        print(ridership_df['_merge'].value_counts())
        ridership_df.drop(columns=['_merge','stop_id_A','stop_id_B'], inplace=True)

        all_ridership_df = pandas.concat([all_ridership_df, ridership_df])
    
    all_ridership_df.to_csv(MONTHLY_HOURLY_RIDERSHIP_OUTPUT, index=False)
    print("Wrote {:,} rows to {}".format(len(all_ridership_df),MONTHLY_HOURLY_RIDERSHIP_OUTPUT))

    # summarize to timeperiod
    ridership_df = ridership_df.groupby(
        by=['year','month','timeperiod','origin_station','destination_station']).agg(
        trip_count       = pandas.NamedAgg(column='trip_count',       aggfunc='sum'),
        num_avg_weekdays = pandas.NamedAgg(column='num_avg_weekdays', aggfunc='first'),
        dist             = pandas.NamedAgg(column='dist',             aggfunc='first'),
        route_ids        = pandas.NamedAgg(column='route_ids',        aggfunc='first'),
    ).reset_index(drop=False)
    ridership_df['avg_daily_trips'] = ridership_df['trip_count']/ridership_df['num_avg_weekdays']

    all_ridership_df.to_csv(MONTHLY_TIMEPERIOD_RIDERSHIP_OUTPUT, index=False)
    print("Wrote {:,} rows to {}".format(len(all_ridership_df),MONTHLY_TIMEPERIOD_RIDERSHIP_OUTPUT))
