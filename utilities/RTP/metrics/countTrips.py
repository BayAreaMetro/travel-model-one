import collections, datetime, os, sys
import numpy, pandas

USAGE = r"""

  python countTrips.py

  Simple script that reads

  * main\\[indiv,joint]TripDataIncome_%ITER%.csv and
  * main\\jointTourData_%ITER%.csv (for the person ids for joint trips)
  * main\\personData_%ITER%.csv (for person ages)
  * database\ActiveTimeSkimsDatabase[timeperiod].csv (for active times)

  and tallies the trips by timeperiod, income category and trip mode.
  Household income is $2000; see http://analytics.mtc.ca.gov/foswiki/Main/Household
  Income categories are as follows:

  * inc1: income in \[ 0k, 30k )
  * inc2: income in \[30k, 60k )
  * inc3: income in \[60k, 100k)
  * inc4: income in \[100k,    )

  Outputs:

  * main\\trips[EA,AM,MD,PM,EV]inc[1,2,3,4].dat
  * main\\trips[EA,AM,MD,PM,EV]_2074.dat
  * main\\trips[EA,AM,MD,PM,EV]_2064.dat
  * metrics\unique_active_travelers.csv

  The latter two .dat files are the same as the first but not split by income category,
  and filtered by age (20-74 year olds and 20-64 year olds, respectively) to be used for
  the active-travel mortality reduction metrics.

  The last file (unique_active_travelers.csv) is also for the active-travel
  mortality reduction metrics, and is a sum of the number of unique persons
  doing the traveling.

  Note: this script DOES factor the trips by SAMPLESHARE.
"""

# note that there are 32 modes and they are a hybrid of tour modes and those used in assignment
# they include all 21 tour and trip modes in here  (https://github.com/BayAreaMetro/modeling-website/wiki/TravelModes#tour-and-trip-modes)
# plus 'wlk_loc_drv', 'wlk_lrf_drv', 'wlk_exp_drv', 'wlk_hvy_drv', 'wlk_com_drv'
# and 'da_av_notoll', 'da_av_toll', 'sr2_av_notoll','sr2_av_toll', 'sr3_av_notoll', 'sr3_av_toll'
COLUMNS = ['orig_taz','dest_taz',
           'da',       'da_toll',
           'sr2',      'sr2_toll',
           'sr3',      'sr3_toll',
           'walk',     'bike',
           'wlk_loc_wlk', 'wlk_lrf_wlk', 'wlk_exp_wlk', 'wlk_hvy_wlk', 'wlk_com_wlk',
           'drv_loc_wlk', 'drv_lrf_wlk', 'drv_exp_wlk', 'drv_hvy_wlk', 'drv_com_wlk',
           'wlk_loc_drv', 'wlk_lrf_drv', 'wlk_exp_drv', 'wlk_hvy_drv', 'wlk_com_drv',
           'taxi', 'tnc', 'tnc_shared',
           'da_av_notoll', 'da_av_toll',  'sr2_av_notoll',  'sr2_av_toll', 'sr3_av_notoll', 'sr3_av_toll']

ACTIVE_MINUTES_THRESHOLD = 30

def find_number_of_active_adults(trips_df):
    """
    For update on morbidity calculation:
    Calculates the number of adults (18+ year olds) that have more than ACTIVE_MINUTES_THRESHOLD
    minutes of active travel per day and returns it.

    Reads database\ActiveTimeSkimsDatabase[timeperiod].csv
    """
    # active adult trips -- filter out youths and driving trips
    active_adult_trips_df = trips_df.loc[trips_df['age']>=18,
                            ['hh_id','person_id','age','orig_taz','dest_taz','trip_mode_str','time_period','num_participants']].copy()

    # map modes to simplified mode for skim
    active_adult_trips_df.loc[:,'active_mode'] = active_adult_trips_df['trip_mode_str']
    active_adult_trips_df.loc[active_adult_trips_df['trip_mode_str']=='wlk_loc_wlk', 'active_mode'] = 'wTrnW'
    active_adult_trips_df.loc[active_adult_trips_df['trip_mode_str']=='wlk_lrf_wlk', 'active_mode'] = 'wTrnW'
    active_adult_trips_df.loc[active_adult_trips_df['trip_mode_str']=='wlk_exp_wlk', 'active_mode'] = 'wTrnW'
    active_adult_trips_df.loc[active_adult_trips_df['trip_mode_str']=='wlk_hvy_wlk', 'active_mode'] = 'wTrnW'
    active_adult_trips_df.loc[active_adult_trips_df['trip_mode_str']=='wlk_com_wlk', 'active_mode'] = 'wTrnW'

    active_adult_trips_df.loc[active_adult_trips_df['trip_mode_str']=='drv_loc_wlk', 'active_mode'] = 'dTrnW'
    active_adult_trips_df.loc[active_adult_trips_df['trip_mode_str']=='drv_lrf_wlk', 'active_mode'] = 'dTrnW'
    active_adult_trips_df.loc[active_adult_trips_df['trip_mode_str']=='drv_exp_wlk', 'active_mode'] = 'dTrnW'
    active_adult_trips_df.loc[active_adult_trips_df['trip_mode_str']=='drv_hvy_wlk', 'active_mode'] = 'dTrnW'
    active_adult_trips_df.loc[active_adult_trips_df['trip_mode_str']=='drv_com_wlk', 'active_mode'] = 'dTrnW'

    active_adult_trips_df.loc[active_adult_trips_df['trip_mode_str']=='wlk_loc_drv', 'active_mode'] = 'wTrnD'
    active_adult_trips_df.loc[active_adult_trips_df['trip_mode_str']=='wlk_lrf_drv', 'active_mode'] = 'wTrnD'
    active_adult_trips_df.loc[active_adult_trips_df['trip_mode_str']=='wlk_exp_drv', 'active_mode'] = 'wTrnD'
    active_adult_trips_df.loc[active_adult_trips_df['trip_mode_str']=='wlk_hvy_drv', 'active_mode'] = 'wTrnD'
    active_adult_trips_df.loc[active_adult_trips_df['trip_mode_str']=='wlk_com_drv', 'active_mode'] = 'wTrnD'

    active_adult_trips_df.loc[:,'active_minutes'] = 0.0

    # print(active_adult_trips_df['active_mode'].value_counts())
    # print(active_adult_trips_df['time_period'].value_counts())
    active_adult_trips_df_len = len(active_adult_trips_df)

    # figure out how many minutes of activity per trip: join with activeTimeSkims
    for time_period in ['EA','AM','MD','PM','EV']:
        filename = os.path.join("database", "ActiveTimeSkimsDatabase%s.csv" % time_period)
        print("{} Reading {}".format(datetime.datetime.now().strftime("%x %X"), filename))
        skim_df  = pandas.read_table(filename, sep=",")
        skim_df.loc[:, 'time_period'] = time_period

        for active_mode in ['walk','bike','wTrnW','dTrnW','wTrnD']:
            # get the skim for this mode
            skim_tp_df = skim_df.loc[:,['orig','dest','time_period',active_mode]]
            skim_tp_df.loc[:,'active_mode']=active_mode
            skim_tp_df.rename(columns={'orig':'orig_taz','dest':'dest_taz'}, inplace=True)

            # join it, adding active_mode-named column
            active_adult_trips_df = pandas.merge(left    =active_adult_trips_df,
                                                 right   =skim_tp_df,
                                                 on      =['orig_taz','dest_taz','time_period','active_mode'],
                                                 how     ='left')
            # set those minutes
            active_adult_trips_df.loc[active_adult_trips_df[active_mode].notnull(), 'active_minutes'] = active_adult_trips_df[active_mode]
            # drop the new column
            active_adult_trips_df.drop(active_mode, axis=1, inplace=True)

    # make sure we didn't lose anyone
    assert(active_adult_trips_df_len == len(active_adult_trips_df))
    # keep only the successful joins
    active_adult_trips_df = active_adult_trips_df.loc[active_adult_trips_df['active_minutes']>0]
    # see how many trips had failed joins
    percent_fail = 100.0*len(active_adult_trips_df)/active_adult_trips_df_len
    print("{} Have {} valid active times out of {}, or {:.2f}% join successes".format
      (datetime.datetime.now().strftime("%x %X"),
       len(active_adult_trips_df),
       active_adult_trips_df_len,
       percent_fail))

    # each row is 1 trip
    active_adult_trips_df['num_trips'] = 1
    # count active minutes for people
    active_counts_df = active_adult_trips_df[['hh_id','person_id','num_participants','num_trips','active_minutes']]\
        .groupby(['hh_id','person_id'])\
        .agg({'num_participants':numpy.mean, 'num_trips':numpy.sum, 'active_minutes':numpy.sum})
    print(active_counts_df.describe())

    # filter to just active persons (above ACTIVE_MINUTES_THRESHOLD)
    active_counts_len = len(active_counts_df)
    active_counts_df  = active_counts_df.loc[active_counts_df['active_minutes']>=ACTIVE_MINUTES_THRESHOLD]
    percent_active = 100.0*len(active_counts_df)/active_counts_len
    print("{} Have {} active (above {} minutes threshold) out of {} total adults with active minutes, or {:.2f}% very active".format
        (datetime.datetime.now().strftime("%x %X"),
         len(active_counts_df), ACTIVE_MINUTES_THRESHOLD,
         active_counts_len, percent_active))
    print(active_counts_df.describe())
    return(active_counts_df['num_participants'].sum())

def write_trips_by_od(trips_df, by_income_cat, outsuffix):
    """
    Groups up the trip list by time_period, income_cat (if by_income_cat=true), orig_taz, dest_taz, trip_mode_str
    And then unstacks so the trip_mode_str form columns.
    Writes it out to main \ trips[timeperiod]inc[1-4][outsuffix].dat (inc part dropped if by_income_cat=false)
    """
    income_list = []
    if by_income_cat:
        # group it and then unstack to index = time_period, income_cat, orig_taz, dest_taz, trip_mode_str
        trip_counts = trips_df[['time_period','income_cat','orig_taz','dest_taz','trip_mode_str','num_participants']].groupby(['time_period','income_cat','orig_taz','dest_taz','trip_mode_str']).sum()
        trip_counts = trip_counts.unstack().fillna(0)
        income_list = range(1,5)
    else:
        trip_counts = trips_df[['time_period',             'orig_taz','dest_taz','trip_mode_str','num_participants']].groupby(['time_period',             'orig_taz','dest_taz','trip_mode_str']).sum()
        trip_counts = trip_counts.unstack().fillna(0)
        income_list = [0]

    for timeperiod in ['EA','AM','MD','PM','EV']:
        for income_cat in income_list:

            # select the specific ones
            trip_counts_tpinc = trip_counts.loc[timeperiod, income_cat] if by_income_cat else trip_counts.loc[timeperiod]
            trip_counts_tpinc.reset_index(inplace=True)
            # rename columns which we can't do with rename() I guess, because we have multiindex columns
            cols     = trip_counts_tpinc.columns.tolist()
            new_cols = []
            for col in cols:
                if   col == ('orig_taz',''): new_cols.append( ('orig_taz','orig_taz'))
                elif col == ('dest_taz',''): new_cols.append( ('dest_taz','dest_taz'))
                else: new_cols.append(col)
            trip_counts_tpinc.columns = pandas.MultiIndex.from_tuples(new_cols)
            trip_counts_tpinc.columns = trip_counts_tpinc.columns.droplevel()

            # some modes may not be here; put it in
            for col in COLUMNS[2:]:
                if col not in trip_counts_tpinc.columns.tolist():
                    trip_counts_tpinc[col] = 0

            trip_counts_tpinc = trip_counts_tpinc[COLUMNS]
            trip_counts_tpinc = trip_counts_tpinc.astype(int)
            if by_income_cat:
                output_filename = os.path.join("main", "trips%sinc%d%s.dat" % (timeperiod, income_cat, outsuffix))
            else:
                output_filename = os.path.join("main", "trips%s%s.dat" % (timeperiod, outsuffix))

            trip_counts_tpinc.to_csv(output_filename, sep=' ',header=False, index=False)
            print("{}  Wrote {}".format(datetime.datetime.now().strftime("%x %X"), output_filename))


if __name__ == '__main__':

    pandas.set_option('display.width', 500)
    iteration       = int(os.environ['ITER'])
    sampleshare   = float(os.environ['SAMPLESHARE'])
    # (mode,time period,income,orig,dest) -> count

    trips_df = None
    for trip_type in ['indiv', 'joint']:
        filename = os.path.join("main", "%sTripDataIncome_%d.csv" % (trip_type, iteration))
        print("{} Reading {}".format(datetime.datetime.now().strftime("%x %X"), filename))
        temp_trips_df = pandas.read_table(filename, sep=",")
        print("{} Done reading {} {} trips".format(datetime.datetime.now().strftime("%x %X"), len(temp_trips_df), trip_type))

        if trip_type == 'indiv':
            # each row is a trip; scale by sampleshare
            temp_trips_df['num_participants'] = 1.0/sampleshare

            trips_df = temp_trips_df
        else:
            # scale by sample share
            temp_trips_df['num_participants'] = temp_trips_df['num_participants']/sampleshare
            trips_df = pandas.concat([trips_df, temp_trips_df], axis=0)

    print("{} Read {} lines total".format(datetime.datetime.now().strftime("%x %X"), len(trips_df)))
    # print trips_df.head()

    # set time period
    trips_df['time_period'] = "unknown"
    trips_df.loc[(trips_df['depart_hour']>= 3)&(trips_df['depart_hour']< 6), 'time_period'] = 'EA'
    trips_df.loc[(trips_df['depart_hour']>= 6)&(trips_df['depart_hour']<10), 'time_period'] = 'AM'
    trips_df.loc[(trips_df['depart_hour']>=10)&(trips_df['depart_hour']<15), 'time_period'] = 'MD'
    trips_df.loc[(trips_df['depart_hour']>=15)&(trips_df['depart_hour']<19), 'time_period'] = 'PM'
    trips_df.loc[(trips_df['depart_hour']>=19)|(trips_df['depart_hour']< 3), 'time_period'] = 'EV'
    assert(len(trips_df.loc[trips_df['time_period']=="unknown"])==0)

    # set mode string
    trips_df['trip_mode_str'] = "unknown"
    trips_df.loc[(trips_df['trip_mode']== 1)&(trips_df['avAvailable']==0), 'trip_mode_str'] = 'da'
    trips_df.loc[(trips_df['trip_mode']== 2)&(trips_df['avAvailable']==0), 'trip_mode_str'] = 'da_toll'
    trips_df.loc[(trips_df['trip_mode']== 3)&(trips_df['avAvailable']==0), 'trip_mode_str'] = 'sr2'
    trips_df.loc[(trips_df['trip_mode']== 4)&(trips_df['avAvailable']==0), 'trip_mode_str'] = 'sr2_toll'
    trips_df.loc[(trips_df['trip_mode']== 5)&(trips_df['avAvailable']==0), 'trip_mode_str'] = 'sr3'
    trips_df.loc[(trips_df['trip_mode']== 6)&(trips_df['avAvailable']==0), 'trip_mode_str'] = 'sr3_toll'
    trips_df.loc[(trips_df['trip_mode']== 7), 'trip_mode_str'] = 'walk'
    trips_df.loc[(trips_df['trip_mode']== 8), 'trip_mode_str'] = 'bike'
    trips_df.loc[(trips_df['trip_mode']== 9), 'trip_mode_str'] = 'wlk_loc_wlk'
    trips_df.loc[(trips_df['trip_mode']==10), 'trip_mode_str'] = 'wlk_lrf_wlk'
    trips_df.loc[(trips_df['trip_mode']==11), 'trip_mode_str'] = 'wlk_exp_wlk'
    trips_df.loc[(trips_df['trip_mode']==12), 'trip_mode_str'] = 'wlk_hvy_wlk'
    trips_df.loc[(trips_df['trip_mode']==13), 'trip_mode_str'] = 'wlk_com_wlk'

    trips_df.loc[(trips_df['trip_mode']==14)&(trips_df['inbound']==0), 'trip_mode_str'] = 'drv_loc_wlk'
    trips_df.loc[(trips_df['trip_mode']==15)&(trips_df['inbound']==0), 'trip_mode_str'] = 'drv_lrf_wlk'
    trips_df.loc[(trips_df['trip_mode']==16)&(trips_df['inbound']==0), 'trip_mode_str'] = 'drv_exp_wlk'
    trips_df.loc[(trips_df['trip_mode']==17)&(trips_df['inbound']==0), 'trip_mode_str'] = 'drv_hvy_wlk'
    trips_df.loc[(trips_df['trip_mode']==18)&(trips_df['inbound']==0), 'trip_mode_str'] = 'drv_com_wlk'

    trips_df.loc[(trips_df['trip_mode']==14)&(trips_df['inbound']==1), 'trip_mode_str'] = 'wlk_loc_drv'
    trips_df.loc[(trips_df['trip_mode']==15)&(trips_df['inbound']==1), 'trip_mode_str'] = 'wlk_lrf_drv'
    trips_df.loc[(trips_df['trip_mode']==16)&(trips_df['inbound']==1), 'trip_mode_str'] = 'wlk_exp_drv'
    trips_df.loc[(trips_df['trip_mode']==17)&(trips_df['inbound']==1), 'trip_mode_str'] = 'wlk_hvy_drv'
    trips_df.loc[(trips_df['trip_mode']==18)&(trips_df['inbound']==1), 'trip_mode_str'] = 'wlk_com_drv'

    trips_df.loc[(trips_df['trip_mode']==19), 'trip_mode_str'] = 'taxi'
    trips_df.loc[(trips_df['trip_mode']==20), 'trip_mode_str'] = 'tnc'
    trips_df.loc[(trips_df['trip_mode']==21), 'trip_mode_str'] = 'tnc_shared'

    trips_df.loc[(trips_df['trip_mode']== 1)&(trips_df['avAvailable']==1), 'trip_mode_str'] = 'da_av_notoll'
    trips_df.loc[(trips_df['trip_mode']== 2)&(trips_df['avAvailable']==1), 'trip_mode_str'] = 'da_av_toll'
    trips_df.loc[(trips_df['trip_mode']== 3)&(trips_df['avAvailable']==1), 'trip_mode_str'] = 'sr2_av_notoll'
    trips_df.loc[(trips_df['trip_mode']== 4)&(trips_df['avAvailable']==1), 'trip_mode_str'] = 'sr2_av_toll'
    trips_df.loc[(trips_df['trip_mode']== 5)&(trips_df['avAvailable']==1), 'trip_mode_str'] = 'sr3_av_notoll'
    trips_df.loc[(trips_df['trip_mode']== 6)&(trips_df['avAvailable']==1), 'trip_mode_str'] = 'sr3_av_toll'

    assert(len(trips_df.loc[trips_df['trip_mode_str']=="unknown"])==0)

    # set income category
    trips_df['income_cat'] = 0
    trips_df.loc[                             (trips_df['income']< 30000), 'income_cat'] = 1
    trips_df.loc[(trips_df['income']>= 30000)&(trips_df['income']< 60000), 'income_cat'] = 2
    trips_df.loc[(trips_df['income']>= 60000)&(trips_df['income']<100000), 'income_cat'] = 3
    trips_df.loc[(trips_df['income']>=100000)                            , 'income_cat'] = 4
    assert(len(trips_df.loc[trips_df['income_cat']==0])==0)

    # write it
    write_trips_by_od(trips_df, by_income_cat=True, outsuffix="")

    # Doing active transportation - drop auto
    trips_df = trips_df.loc[trips_df.trip_mode >= 7]
    print("{} Filtered to non-auto trips, of which there are {}".format(datetime.datetime.now().strftime("%x %X"), len(trips_df)))

    # Joint trips don't have person_ids -- remove them and fill them from joint tours
    joint_trips_df = trips_df.loc[trips_df['person_id'].isnull()]
    trips_df       = trips_df.loc[trips_df['person_id'].notnull()]
    num_joint_trips= joint_trips_df['num_participants'].sum()
    print("{} => {} indiv trips, {} joint trip rows making {} joint trips".format
        (datetime.datetime.now().strftime("%x %X"), len(trips_df), len(joint_trips_df), num_joint_trips))

    # Read joint tours to get person ids for the joint trips
    joint_tours   = pandas.read_table(os.path.join("main", "jointTourData_%d.csv" % iteration),
                                      sep=",", index_col=False)
    joint_tours   = joint_tours[['hh_id','tour_id','tour_participants']]
    joint_tours['num_participants'] = (joint_tours.tour_participants.str.count(' ') + 1.0)/sampleshare
    joint_tour_participants = joint_tours.num_participants.sum()
    # Split joint tours by space and give each its own row
    s           = joint_tours['tour_participants'].str.split(' ').apply(pandas.Series, 1).stack()
    s.index     = s.index.droplevel(-1)
    s.name      = 'person_num'
    s           = s.astype(int)  # no strings
    joint_tours = joint_tours.join(s)

    joint_trips_df.drop('person_num', axis=1, inplace=True) # this will come from tours
    joint_trips_df = pandas.merge(left      = joint_trips_df,
                                  right     = joint_tours,
                                  how       = 'left',
                                  left_on   = ['hh_id','tour_id','num_participants'],
                                  right_on  = ['hh_id','tour_id','num_participants'])
    # now each row is a single person-trip
    joint_trips_df['num_participants'] = 1.0/sampleshare
    # check the number of rows matches the number of joint trips we expect
    assert(joint_trips_df['num_participants'].sum() == num_joint_trips)

    # put it back together
    trips_df = pandas.concat([trips_df, joint_trips_df], axis=0)
    print("{} => {} total trips".format(datetime.datetime.now().strftime("%x %X"), len(trips_df)))

    # join trips to persons for ages
    trips_df.drop('person_id', axis=1, inplace=True) # this will come from hh_id, person_num and persons table
    filename = os.path.join("main", "personData_%d.csv" % iteration)
    print("{} Reading {}".format(datetime.datetime.now().strftime("%x %X"), filename))
    persons_df = pandas.read_table(filename, sep=",")
    print("{} Done reading {} persons".format(datetime.datetime.now().strftime("%x %X"), len(persons_df)))
    trips_df = pandas.merge(left=trips_df,
                            right=persons_df[['hh_id','person_num','person_id','age']],
                            how="left",
                            left_on=['hh_id','person_num'],
                            right_on=['hh_id','person_num'])

    travelers_dict = {}

    travelers_dict['number_active_adults'] = find_number_of_active_adults(trips_df)

    # filter to 20-74 year olds for walking
    trips_df = trips_df.loc[(trips_df['age']>=20)&(trips_df['age']<=74)]
    print("{} Filtered to {} trips between 20-74 year olds".format
        (datetime.datetime.now().strftime("%x %X"), len(trips_df)))

    # write it
    write_trips_by_od(trips_df, by_income_cat=False, outsuffix="_2074")


    # unique persons who walk
    walking_2074 = trips_df.loc[trips_df['trip_mode_str']=='walk']
    walking_2074 = walking_2074[['person_id']].drop_duplicates()
    travelers_dict['unique_walkers_2074'] = len(walking_2074)/sampleshare
    print("{} => made by {} unique individuals walking".format
        (datetime.datetime.now().strftime("%x %X"), travelers_dict['unique_walkers_2074']))

    # unique persons who transit
    transit_2074 = trips_df.loc[trips_df['trip_mode']>=9]
    transit_2074 = transit_2074[['person_id']].drop_duplicates()
    travelers_dict['unique_transiters_2074'] = len(transit_2074)/sampleshare
    print("{} => made by {} unique individuals taking transit".format
        (datetime.datetime.now().strftime("%x %X"), travelers_dict['unique_transiters_2074']))

    # filter to 20-64 year olds for biking
    trips_df = trips_df.loc[(trips_df['age']>=20)&(trips_df['age']<=64)]
    print("{} Filtered to {} trips between 20-64 year olds".format
        (datetime.datetime.now().strftime("%x %X"), len(trips_df)))

    # write it
    write_trips_by_od(trips_df, by_income_cat=False, outsuffix="_2064")

    # unique persons who bike
    biking_2064 = trips_df.loc[(trips_df['trip_mode_str']=='bike')]
    biking_2064[['trip_mode_str']].describe()
    biking_2064 = biking_2064[['person_id']].drop_duplicates()
    travelers_dict['unique_cyclists_2064'] = len(biking_2064)/sampleshare
    print("{} => made by {} unique individuals biking".format
        (datetime.datetime.now().strftime("%x %X"), travelers_dict['unique_cyclists_2064']))

    output_filename = os.path.join("metrics", "unique_active_travelers.csv")
    travelers_s = pandas.Series(travelers_dict.values(), index=travelers_dict.keys())
    travelers_s.to_csv(output_filename, index=True)
    print("{}  Wrote {}".format(datetime.datetime.now().strftime("%x %X"), output_filename))
