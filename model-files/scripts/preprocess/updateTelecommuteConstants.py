USAGE = '''

  Creates/updates main/telecommute_constants_[CALIB_ITER].csv with columns
  ZONE, telecommuteConstant

  If in TELECOMMUTE_CALIBRATION mode, then uses CALIB_ITER
  Else, assumes this is in model run mode, and uses CALIB_ITER=ITER

  Uses environment variables TELECOMMUTE_CALIBRATION, CALIB_ITER, ITER, MODEL_YEAR, MODEL_DIR
  Filters to full-time workers and part-time workers
  For people who make multiple work tours_df, uses the first one for the purpose of tour tour mode
'''

import os,re,sys
import pandas


# input files
TAZDATA_FILE  = os.path.join('INPUT', 'landuse', 'tazData.csv')
TOUR_FILE     = os.path.join('main','indivTourData_{}.csv')
WSLOC_FILE    = os.path.join('main','wsLocResults_{}.csv')
# todo: add to input if run during model
TELERATE_FILE = os.path.join('INPUT','landuse','telecommute_max_rate_county.csv')

PARAMS_FILENAME = os.path.join('INPUT','params.properties')

# input and output; input {}=previous calib iter, output {}=CALIB_ITER
TELECOMMUTE_CONSTANTS_FILE = os.path.join('main','telecommute_constants_{:02d}.csv')

TARGET_AUTO_SHARE  = 0.40
# if max_telecommute_rate +/- this, then leave it alone
TELECOMMUTE_RATE_THRESHHOLD = 0.005

# todo: make this more intelligent
CONSTANT_INCREMENT = 0.05
CONSTANT_DECREMENT = 0.05

# see EN7 Telecommuting.xlsx (https://mtcdrive.box.com/s/uw3n8wyervle6r2cgoz1j6k4i5lmv253)
# for 2015 and before
P_notworking_if_noworktour_FT = 0.560554289
P_notworking_if_noworktour_PT = 0.553307383
# future
P_notworking_FT = 0.107904288
P_notworking_PT = 0.205942146


if __name__ == '__main__':
    pandas.options.display.width = 150

    TELECOMMUTE_CALIBRATION = "0"
    if 'TELECOMMUTE_CALIBRATION' in os.environ:
        TELECOMMUTE_CALIBRATION = os.environ['TELECOMMUTE_CALIBRATION']

    ITER                    = os.environ['ITER']
    MODEL_YEAR              = os.environ['MODEL_YEAR']
    MODEL_DIR               = os.environ['MODEL_DIR']

    # SAMPLESHARE not set for iter0 model run
    SAMPLESHARE             = "NA"
    if 'SAMPLESHARE' in os.environ:
        SAMPLESHARE = os.environ['SAMPLESHARE']

    if int(TELECOMMUTE_CALIBRATION) == 1:
        UPDATE_CONSTANT = True
        CALIB_ITER      = os.environ['CALIB_ITER']

    else:
        # model run mode -- use ITER for CALIB_ITER
        CALIB_ITER = "0"+ITER

        UPDATE_CONSTANT = False
        if (MODEL_DIR.upper().find("FBP") >= 0):
            if (int(MODEL_YEAR) < 2035) or \
               (MODEL_DIR.upper().find("NOPROJECT") >= 0) or \
               (MODEL_DIR.upper().find("NOTRANSPORTPROJECT") >= 0):
               UPDATE_CONSTANT = False
            else:
               UPDATE_CONSTANT = True

    print('MODEL_YEAR               = {}'.format(MODEL_YEAR))
    print('MODEL_DIR                = {}'.format(MODEL_DIR))
    print('TELECOMMUTE_CALIBRATION  = {}'.format(TELECOMMUTE_CALIBRATION))
    print('CALIB_ITER               = {}'.format(CALIB_ITER))
    print('ITER                     = {}'.format(ITER))
    print('SAMPLESHARE              = {}'.format(SAMPLESHARE))

    print("UPDATING TELECOMMUTE CONSTANTS? {}".format(UPDATE_CONSTANT))

    # read INPUT\params.properties
    myfile          = open( PARAMS_FILENAME, 'r' )
    PARAMS_CONTENTS = myfile.read()
    myfile.close()
    print("Read {} lines from {}".format(len(PARAMS_CONTENTS), PARAMS_FILENAME))

    # read tazdata
    TAZDATA_COLS = ['ZONE','DISTRICT','SD','COUNTY','RETEMPN','FPSEMPN','HEREMPN','OTHEMPN','AGREMPN','MWTEMPN','TOTEMP']
    tazdata_df = pandas.read_csv(TAZDATA_FILE, index_col=False, sep=',', usecols=TAZDATA_COLS)
    print('Read {} lines from {}; head:\n{}'.format(len(tazdata_df), TAZDATA_FILE, tazdata_df.head()))

    # read max telecommute rate
    telecommute_rate_df = pandas.read_csv(TELERATE_FILE, sep=',')
    print('Read {} lines from {}; head:\n{}'.format(len(telecommute_rate_df), TELERATE_FILE, telecommute_rate_df.head()))

    # join to tazdata to figure out effective max telecommute rate for each county
    telecommute_rate_df = pandas.merge(left=tazdata_df, right=telecommute_rate_df, how='left', on='COUNTY')
    telecommute_rate_df['max_telecommuters'] = \
        (telecommute_rate_df['AGREMPN']*telecommute_rate_df['AGREMPN_tele']) + \
        (telecommute_rate_df['FPSEMPN']*telecommute_rate_df['FPSEMPN_tele']) + \
        (telecommute_rate_df['HEREMPN']*telecommute_rate_df['HEREMPN_tele']) + \
        (telecommute_rate_df['MWTEMPN']*telecommute_rate_df['MWTEMPN_tele']) + \
        (telecommute_rate_df['RETEMPN']*telecommute_rate_df['RETEMPN_tele']) + \
        (telecommute_rate_df['OTHEMPN']*telecommute_rate_df['OTHEMPN_tele'])
    # aggregate back to county
    telecommute_rate_df = telecommute_rate_df.groupby('COUNTY').agg({'max_telecommuters':'sum', 'TOTEMP':'sum'}).reset_index()
    telecommute_rate_df['max_telecommute_rate'] = telecommute_rate_df['max_telecommuters']/telecommute_rate_df['TOTEMP']
    print(telecommute_rate_df)

    # initialize primary df
    telecommute_df = tazdata_df[['ZONE','SD','COUNTY']].copy()

    # if in a model run, iter 0
    if int(ITER)==0:
        if UPDATE_CONSTANT:
            # no data yet, don't create file -- the initial calibrated constants should be present
            print("Model run ITER0 -- using initial calibrated constants")

            # all the same, let's verify
            if not os.path.exists(TELECOMMUTE_CONSTANTS_FILE.format(0)):
                print("However - the file {} is not found -- core will hang!".format(TELECOMMUTE_CONSTANTS_FILE.format(0)))
                sys.exit(2)
            sys.exit(0)

        # otherwise, default to zero
        telecommute_df['CALIB_ITER'] = int(CALIB_ITER)
        telecommute_df['telecommuteConstant'] = 0.0

    # no results yet -- start at zero
    elif int(TELECOMMUTE_CALIBRATION)==1 and int(CALIB_ITER)==0:

        if os.path.exists(TELECOMMUTE_CONSTANTS_FILE.format(0)):
            print("Telecommute Calibration CALIB_ITER 0 -- initial constants found.")
            sys.exit(0)

        # otherwise, make empty file
        print("Calibrating -- iter0.  Start at zero")

        # default to zero
        telecommute_df['CALIB_ITER'] = int(CALIB_ITER)
        telecommute_df['telecommuteConstant'] = 0.0

    # read results, create metrics and update
    else:

        TOUR_COLS = ['hh_id','tour_id','person_id','person_num','person_type',
                     'tour_purpose','tour_mode','dest_taz','sampleRate']

        # no need to read joint tours_df; they are never work
        tours_df = pandas.read_csv(TOUR_FILE.format(ITER), usecols=TOUR_COLS)
        print('Read {} lines from {}; head:\n{}'.format(len(tours_df),TOUR_FILE.format(ITER),tours_df.head()))
        # print(tours_df.dtypes)

        # filter to work
        tours_df = tours_df.loc[ tours_df['tour_purpose'].str.slice(stop=4)=='work' ]
        print('  Filtered to {} rows of work tours_df; head:\n{}'.format(len(tours_df), tours_df.head()))
        num_work_tours_df = len(tours_df)

        # deduplicate -- some people have multiple work tours_df
        tours_df.drop_duplicates(subset=['hh_id','person_id','person_num'], keep='first', inplace=True)
        print('  Dropped {} second work tours_df'.format(num_work_tours_df - len(tours_df)))

        # read work locations to get people who don't make work tours_df
        wslocs_df = pandas.read_csv(WSLOC_FILE.format(ITER), usecols=['HHID','PersonID','PersonNum','PersonType','WorkLocation'])
        # make columns consistent
        wslocs_df.rename(columns={'HHID':'hh_id',
                               'PersonID':'person_id',
                               'PersonNum':'person_num',
                               'PersonType':'person_type_str'}, inplace=True)
        print('Read {} lines from {}; head:\n{}'.format(len(wslocs_df),WSLOC_FILE.format(ITER),wslocs_df.head()))
        # print(wslocs_df.dtypes)
        # print(tours_df.dtypes)

        # filter to people with work locations
        wslocs_df = wslocs_df.loc[ wslocs_df['WorkLocation']>0 ]
        print('  Filtered to {} rows with work locations'.format(len(wslocs_df)))

        # join together
        work_tours_df = pandas.merge(left=wslocs_df, right=tours_df,
                                  on =['hh_id','person_id','person_num'],
                                  how='outer',
                                  indicator=True)
        print(work_tours_df['_merge'].value_counts())
        # make sure no right only (tours_df without wsloc)
        assert(len(work_tours_df.loc[ work_tours_df._merge=='right_only'])==0)
        # make sure dest_taz == workLocation where it's set
        work_tours_df_with_dest = work_tours_df.loc[pandas.notnull(work_tours_df.dest_taz),]
        pandas.testing.assert_series_equal(work_tours_df_with_dest['WorkLocation'],
                                           work_tours_df_with_dest['dest_taz'],
                                           check_dtype=False,
                                           check_names=False)
        del work_tours_df_with_dest

        # fill in tour_mode as 0 for doesn't make tour
        work_tours_df.loc[ pandas.isnull(work_tours_df.tour_mode), 'tour_mode'] = 0
        work_tours_df = work_tours_df.astype({'tour_mode': int})
        # print(work_tours_df['tour_mode'].value_counts())

        # fill in sample rate
        work_tours_df.loc[ pandas.isnull(work_tours_df.sampleRate), 'sampleRate'] = float(SAMPLESHARE)

        # recode tour_mode to auto, non-auto, no tour
        work_tours_df['simple_mode'] = 'unset'
        work_tours_df.loc[ work_tours_df.tour_mode==0,                                'simple_mode'] = 'no tour'
        work_tours_df.loc[(work_tours_df.tour_mode>  0)&(work_tours_df.tour_mode<=6), 'simple_mode'] = 'auto'
        work_tours_df.loc[(work_tours_df.tour_mode>=19),                              'simple_mode'] = 'auto' # tnc
        work_tours_df.loc[(work_tours_df.tour_mode>= 7)&(work_tours_df.tour_mode<=18),'simple_mode'] = 'non-auto'
        print(work_tours_df.simple_mode.value_counts())

        # join to work place superdistricts
        work_tours_df = pandas.merge(left    =work_tours_df,
                                     right   =tazdata_df[['ZONE','SD','COUNTY']],
                                     left_on ='WorkLocation',
                                     right_on='ZONE',
                                     how     ='left')
        # expand from sampleRate
        work_tours_df['num_workers'] = 1.0/work_tours_df['sampleRate']
        print(work_tours_df.head(10))

        # filter to just Full-time workers and Part-time workers
        work_tours_df = work_tours_df.loc[(work_tours_df['person_type_str']=='Full-time worker')|
                                          (work_tours_df['person_type_str']=='Part-time worker'), ]
        # aggregate to work SD
        work_mode_SD_df = work_tours_df.groupby(['person_type_str','COUNTY','SD','simple_mode']).agg({'num_workers':'sum'}).reset_index()
        
        # move person_type_str and simple mode to columns
        work_mode_SD_df = pandas.pivot_table(work_mode_SD_df, index=['COUNTY','SD'], 
                                             columns=['person_type_str','simple_mode'], values='num_workers').reset_index()
        # flatten columns
        work_mode_SD_df.columns = [' '.join(col).strip() for col in work_mode_SD_df.columns.values]

        print(work_mode_SD_df)

        # calculate not working to take them out of the universe
        if (int(MODEL_YEAR) <= 2020):
            work_mode_SD_df['Full-time worker not-working'] = P_notworking_if_noworktour_FT*work_mode_SD_df['Full-time worker no tour']
            work_mode_SD_df['Part-time worker not-working'] = P_notworking_if_noworktour_PT*work_mode_SD_df['Part-time worker no tour']
        else:
            work_mode_SD_df['Full-time worker not-working'] = P_notworking_FT*work_tours_df['num_workers']
            work_mode_SD_df['Part-time worker not-working'] = P_notworking_PT*work_tours_df['num_workers']

        # they cannot exceed no tour
        work_mode_SD_df['Full-time worker not-working'] = work_mode_SD_df[['Full-time worker not-working','Full-time worker no tour']].min(axis=1) # min across columns
        work_mode_SD_df['Part-time worker not-working'] = work_mode_SD_df[['Part-time worker not-working','Part-time worker no tour']].min(axis=1) # min across columns
        # remaining is telecommute
        work_mode_SD_df['Full-time worker telecommute'] = work_mode_SD_df['Full-time worker no tour'] - work_mode_SD_df['Full-time worker not-working']
        work_mode_SD_df['Part-time worker telecommute'] = work_mode_SD_df['Part-time worker no tour'] - work_mode_SD_df['Part-time worker not-working']
        # create total workers not taking time off
        work_mode_SD_df['Full-time worker working'] = work_mode_SD_df['Full-time worker auto'] + work_mode_SD_df['Full-time worker non-auto'] + work_mode_SD_df['Full-time worker telecommute']
        work_mode_SD_df['Part-time worker working'] = work_mode_SD_df['Part-time worker auto'] + work_mode_SD_df['Part-time worker non-auto'] + work_mode_SD_df['Part-time worker telecommute']

        # generic
        work_mode_SD_df['working'    ] = work_mode_SD_df['Full-time worker working'    ] + work_mode_SD_df['Part-time worker working'    ]
        work_mode_SD_df['telecommute'] = work_mode_SD_df['Full-time worker telecommute'] + work_mode_SD_df['Part-time worker telecommute']
        work_mode_SD_df['auto'       ] = work_mode_SD_df['Full-time worker auto'       ] + work_mode_SD_df['Part-time worker auto'       ]

        # "mode shares" are now a function of people working
        work_mode_SD_df['telecommute_rate'] = work_mode_SD_df['telecommute'] / work_mode_SD_df['working']
        work_mode_SD_df['auto_share']       = work_mode_SD_df['auto']        / work_mode_SD_df['working']

        # join with max telecommute rate (county-based)
        work_mode_SD_df = pandas.merge(left  =work_mode_SD_df, 
                                       right =telecommute_rate_df[['COUNTY','max_telecommute_rate']],
                                       how   ='left',
                                       on    ='COUNTY')

        print('work_mode_SD_df:\n{}'.format(work_mode_SD_df))

        # read pervious CONSTANTS
        telecommute_df = pandas.read_csv(TELECOMMUTE_CONSTANTS_FILE.format(int(CALIB_ITER)-1))

        telecommute_df = telecommute_df[['ZONE','SD','COUNTY','telecommuteConstant']]
        telecommute_df.rename(columns={'telecommuteConstant':'telecommuteConstant_prev'}, inplace=True)

        # join with work_mode_SD_df
        telecommute_df = pandas.merge(left=telecommute_df, right=work_mode_SD_df) 

        # THIS IS IT
        # start at previous value
        telecommute_df['telecommuteConstant'] = telecommute_df['telecommuteConstant_prev']

        # telecommute within threshold of max
        telecommute_df['telecomute_diff']     = telecommute_df['max_telecommute_rate'] - telecommute_df['telecommute_rate']
        telecommute_df['telecomute_near_max'] = telecommute_df['telecomute_diff'].abs() < TELECOMMUTE_RATE_THRESHHOLD

        if UPDATE_CONSTANT:
            # increase (negative) if auto share is high and we're not at max
            telecommute_df.loc[ (telecommute_df['auto_share'] > TARGET_AUTO_SHARE) & 
                                (telecommute_df['telecommute_rate'] < telecommute_df['max_telecommute_rate']) &
                                (telecommute_df['telecomute_near_max'] == False),
                'telecommuteConstant' ] = telecommute_df['telecommuteConstant'] - CONSTANT_INCREMENT
            # decrease if telecommute share is high
            telecommute_df.loc[ (telecommute_df['telecommute_rate'] > telecommute_df['max_telecommute_rate']) &
                                (telecommute_df['telecomute_near_max'] == False), 
                'telecommuteConstant' ] = telecommute_df['telecommuteConstant'] + CONSTANT_DECREMENT

            # don't go positive
            telecommute_df.loc[ telecommute_df['telecommuteConstant'] > 0, 'telecommuteConstant' ] = 0

        # drop person_type_str column and other temp cols
        telecommute_df.drop(columns=['telecomute_diff','telecomute_near_max'], inplace=True)
        telecommute_df['CALIB_ITER'] = int(CALIB_ITER)


    # write it with calib iter
    telecommute_df.to_csv(TELECOMMUTE_CONSTANTS_FILE.format(int(CALIB_ITER)), header=True, index=False)
    print("Wrote {} lines to {}".format(len(telecommute_df), TELECOMMUTE_CONSTANTS_FILE.format(int(CALIB_ITER))))

    sys.exit(0)