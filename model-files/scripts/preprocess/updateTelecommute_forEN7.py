USAGE = '''
  Uses environment variables EN7, ITER
  EN7 is expected to be one of ['ENABLED', 'DISABLED'] or the script will error.

  Log is written to: logs\\updateTelecommute_forEN7_[ITER]_[YYYYmmdd-HHMM].log
  Detailed debug output is written to main\\telecommute_forEN7_detail_[ITER].csv

  IF EN7=='DISABLED', then the script does nothing.
  IF EN7=='ENABLED', then the script will do the following:

   (1) Reads INPUT\\landuse\\tazData.csv and INPUT\\landuse\\telecommute_max_rate_county.csv
       to estimate maximum wfh by county based on the employment industry mix
   (2) Reads individual tours, person records and work locations files for ITER
   (3) Filters to workers only, and the first work tour for each person (dropping potential subsequent work tours)
   (4) Summarizes the (wfh choice, simplified work tour mode) for workers
   (5) Aggregates to superdistrict
   (6) Adjust wfh_EN7_boost
       (a) For superdistricts with auto_share > TARGET_AUTO_SHARE and wfh_share < max, 
           increase CDAP.WFH.EN7.Superdistrict[SD]
       (b) For superdistricts with wfh_share > max,
           decrease CDAP.WFH.EN7.Superdistrict[SD]
   (7) Writes CTRAMP\\runtime\\mtcTourBased.properties with CDAP.WFH.EN7.Superdistrict[SD] lines modified
'''

import logging,os,re,sys,time
import pandas

# input files
TAZDATA_FILE  = os.path.join('INPUT','landuse','tazData.csv')
PERSON_FILE   = os.path.join('main','personData_{}.csv')
TOUR_FILE     = os.path.join('main','indivTourData_{}.csv')
WSLOC_FILE    = os.path.join('main','wsLocResults_{}.csv')

# todo: add to input if run during model
TELERATE_FILE   = os.path.join('INPUT','landuse','telecommute_max_rate_county.csv')
PARAMS_FILENAME = os.path.join('INPUT','params.properties')

# update the superdistrict EN7 boosts in here
PROPERTIES_FILE = os.path.join('CTRAMP','runtime','mtcTourBased.properties')
PROPERTY_CDAP_WFH_EN7_RE  = re.compile(r"^CDAP.WFH.EN7.Superdistrict(\d+)\s*=\s*([\d\.]+)")  # read
PROPERTY_CDAP_WFH_EN7_STR = "CDAP.WFH.EN7.Superdistrict{:02d}={:.4f}\n" # write
# detail output
DETAIL_OUTPUT_FILE = os.path.join('main','telecommute_forEN7_detail_{}.csv')

# output
LOG_FILE = os.path.join('logs','updateTelecommute_forEN7_{}_{}.log'.format('{}',time.strftime("%Y%m%d-%H%M")))

# EN7
TARGET_AUTO_SHARE  = 0.40
# if max_wfh_share +/- this, then leave it alone
WFH_SHARE_THRESHHOLD = 0.005

if __name__ == '__main__':
    EN7     = os.environ['EN7']
    ITER    = os.environ['ITER']

    # create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(ch)
    # file handler
    fh = logging.FileHandler(LOG_FILE.format(ITER), mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(fh)

    pandas.options.display.width = 500
    pandas.options.display.max_columns = 30

    # expect EN7 to be ENABLED or DISABLED
    EN7_OPTIONS = ['ENABLED','DISABLED']
    if EN7 not in EN7_OPTIONS:
        logging.fatal("FATAL ERROR: EN7 environment variable (value={}) not in {}".format(EN7, EN7_OPTIONS))
        sys.exit(-100)

    logging.info("EN7   = {}".format(EN7))
    logging.info('ITER  = {}'.format(ITER))

    # read tazdata
    TAZDATA_COLS = ['ZONE','DISTRICT','SD','COUNTY','RETEMPN','FPSEMPN','HEREMPN','OTHEMPN','AGREMPN','MWTEMPN','TOTEMP']
    tazdata_df = pandas.read_csv(TAZDATA_FILE, index_col=False, sep=',', usecols=TAZDATA_COLS)
    logging.info('Read {:,} lines from {}; head:\n{}'.format(len(tazdata_df), TAZDATA_FILE, tazdata_df.head()))

    if EN7 == "DISABLED":
        logging.info("EN7 is disabled -- doing nothing.")
        sys.exit(0)


    properties_f = open(PROPERTIES_FILE, "r")
    properties_lines = properties_f.read().split("\n")
    properties_f.close()
    logging.debug("Read {:,} lines lines from {}".format(len(properties_lines), PROPERTIES_FILE))

    # read max telecommute rate
    wfh_share_df = pandas.read_csv(TELERATE_FILE, sep=',')
    logging.info('Read {:,} lines from {}; head:\n{}'.format(len(wfh_share_df), TELERATE_FILE, wfh_share_df.head()))

    # join to tazdata to figure out effective max telecommute rate for each county
    wfh_share_df = pandas.merge(left=tazdata_df, right=wfh_share_df, how='left', on='COUNTY')
    wfh_share_df['max_telecommuters'] = \
        (wfh_share_df['AGREMPN']*wfh_share_df['AGREMPN_tele']) + \
        (wfh_share_df['FPSEMPN']*wfh_share_df['FPSEMPN_tele']) + \
        (wfh_share_df['HEREMPN']*wfh_share_df['HEREMPN_tele']) + \
        (wfh_share_df['MWTEMPN']*wfh_share_df['MWTEMPN_tele']) + \
        (wfh_share_df['RETEMPN']*wfh_share_df['RETEMPN_tele']) + \
        (wfh_share_df['OTHEMPN']*wfh_share_df['OTHEMPN_tele'])
    # aggregate back to county
    wfh_share_df = wfh_share_df.groupby('COUNTY').agg({'max_telecommuters':'sum', 'TOTEMP':'sum'}).reset_index()
    wfh_share_df['max_wfh_share'] = wfh_share_df['max_telecommuters']/wfh_share_df['TOTEMP']
    logging.info("Maximum telecommute rate:\n{}".format(wfh_share_df))

    # read results, create metrics and update

    # read tours for tour mode choice
    TOUR_COLS = ['hh_id','tour_id','person_id','person_num','person_type',
                 'tour_purpose','tour_mode','dest_taz']
    # no need to read joint tours_df; they are never work
    tours_df = pandas.read_csv(TOUR_FILE.format(ITER), usecols=TOUR_COLS)
    logging.info('Read {:,} lines from {}; head:\n{}'.format(len(tours_df),TOUR_FILE.format(ITER),tours_df.head()))

    # filter to work
    tours_df = tours_df.loc[ tours_df['tour_purpose'].str.slice(stop=4)=='work' ]
    logging.info('  Filtered to {:,} rows of work tours_df; head:\n{}'.format(len(tours_df), tours_df.head()))
    num_work_tours_df = len(tours_df)
    # deduplicate -- some people have multiple work tours_df
    tours_df.drop_duplicates(subset=['hh_id','person_id','person_num'], keep='first', inplace=True)
    logging.info('  Dropped {:,} second work tours_df'.format(num_work_tours_df - len(tours_df)))

    # read persons for wfh_choice
    PERSON_COLS = ['hh_id','person_id','sampleRate','wfh_choice']
    persons_df = pandas.read_csv(PERSON_FILE.format(ITER), usecols=PERSON_COLS)
    logging.info('Read {:,} lines from {}; head:\n{}'.format(
        len(persons_df), PERSON_FILE.format(ITER), persons_df.head()))

    # read work locations
    WSLOC_COLS = ['HHID','PersonID','PersonType','EmploymentCategory','WorkLocation']
    wslocs_df = pandas.read_csv(WSLOC_FILE.format(ITER), usecols=WSLOC_COLS)
    logging.info('Read {:,} lines from {}; head:\n{}'.format(
        len(wslocs_df), WSLOC_FILE.format(ITER), wslocs_df.head()))
    
    # filter to employed people
    wslocs_df = wslocs_df.loc[(wslocs_df.EmploymentCategory=='Full-time worker') |
                              (wslocs_df.EmploymentCategory=='Part-time worker')]
    logging.info('  Filtered to {:,} rows with EmploymentCategory == Full|Part-time worker'.format(len(wslocs_df)))

    # make columns consistent
    wslocs_df.rename(columns={'HHID':'hh_id',
                             'PersonID':'person_id',
                             'PersonType':'person_type_str'}, inplace=True)

    # work locations with persons for wfh_choice
    wslocs_df = pandas.merge(
        left      = wslocs_df, 
        right     = persons_df,
        on        = ['hh_id','person_id'],
        how       = 'left',
        indicator = True)
    logging.debug("Merge results from wslocs_df with persons_df:\n{}".format(
        wslocs_df['_merge'].value_counts()))
    # make sure join always succeeds
    assert(len(wslocs_df.loc[ wslocs_df._merge!='both'])==0)
    wslocs_df.drop(columns=['_merge'], inplace=True)

    # join to work place superdistricts
    wslocs_df = pandas.merge(
        left    = wslocs_df,
        right   =tazdata_df[['ZONE','SD','COUNTY']],
        left_on ='WorkLocation',
        right_on='ZONE',
        how     ='left')
    # expand from sampleRate
    wslocs_df['num_workers'] = 1.0/wslocs_df['sampleRate']
    logging.debug("wslocs joined with tazdata:\n{}".format(wslocs_df.head(10)))

    # work tours with work locations
    work_tours_df = pandas.merge(
        left      = wslocs_df,
        right     = tours_df,
        on        = ['hh_id','person_id'],
        how       = 'outer',
        indicator = True)
    logging.debug("work_tours merge result with wslocs_df:\n{}".format(work_tours_df['_merge'].value_counts()))
    logging.debug("work_tours_df.dtypes()\n:{}".format(work_tours_df.dtypes))
    # make sure no right only (tours_df without wsloc)
    assert(len(work_tours_df.loc[ work_tours_df._merge=='right_only'])==0)
    # make sure dest_taz == workLocation where it's set
    work_tours_df_with_dest = work_tours_df.loc[pandas.notnull(work_tours_df.dest_taz),]
    pandas.testing.assert_series_equal(
        work_tours_df_with_dest['WorkLocation'],
        work_tours_df_with_dest['dest_taz'],
        check_dtype=False,
        check_names=False)
    del work_tours_df_with_dest

    # fill in tour_mode as 0 for doesn't make tour
    work_tours_df.loc[ pandas.isnull(work_tours_df.tour_mode), 'tour_mode'] = 0
    work_tours_df = work_tours_df.astype({'tour_mode': int})
    # print("work_tours_df tour_modes:\n{}".format(work_tours_df['tour_mode'].value_counts()))

    # recode tour_mode to auto, non-auto, no tour
    work_tours_df['simple_mode'] = 'unset'
    work_tours_df.loc[ work_tours_df.tour_mode==0,                                'simple_mode'] = 'no_tour'
    work_tours_df.loc[(work_tours_df.tour_mode>  0)&(work_tours_df.tour_mode<=6), 'simple_mode'] = 'auto'
    work_tours_df.loc[(work_tours_df.tour_mode>=19),                              'simple_mode'] = 'auto' # tnc
    work_tours_df.loc[(work_tours_df.tour_mode>= 7)&(work_tours_df.tour_mode<=18),'simple_mode'] = 'non_auto'

    # recode wfh_choice
    work_tours_df['wfh_choice_str'] = 'unset'
    work_tours_df.loc[ work_tours_df.wfh_choice == 0, 'wfh_choice_str'] = 'does_not_wfh'
    work_tours_df.loc[ work_tours_df.wfh_choice == 1, 'wfh_choice_str'] = 'wfh'
    # make sure there are only four combinations:
    # wfh           no_tour
    # does_not_wfh  auto, non_auto, no_tour
    wfh_mode_value_counts = work_tours_df[['wfh_choice_str','simple_mode']].value_counts()
    logging.debug("work_tours_df wfh_choice_str,simple_mode:\n{}".format(wfh_mode_value_counts))
    assert(len(wfh_mode_value_counts)==4)

    # aggregate to work SD
    work_mode_SD_df = work_tours_df.groupby(
        ['COUNTY','SD','wfh_choice_str','simple_mode']).agg({'num_workers':'sum'}).reset_index()
    logging.debug("work_mode_SD_df:\n{}".format(work_mode_SD_df))

    # move simple mode to columns
    work_mode_SD_df = pandas.pivot_table(
        work_mode_SD_df,
        index=['COUNTY','SD'],
        columns=['wfh_choice_str','simple_mode'], 
        values='num_workers'
    ).reset_index()
    logging.debug("work_mode_SD_df:\n{}".format(work_mode_SD_df))

    # flatten columns; they're now
    # COUNTY  SD  does_not_wfh auto  does_not_wfh no_tour  does_not_wfh non_auto  wfh no_tour
    work_mode_SD_df.columns = [' '.join(col).strip() for col in work_mode_SD_df.columns.values]
    logging.debug("work_mode_SD_df:\n{}".format(work_mode_SD_df))

    # calculate auto share
    work_mode_SD_df['workers'] = \
        work_mode_SD_df['wfh no_tour'          ] + \
        work_mode_SD_df['does_not_wfh auto'    ] + \
        work_mode_SD_df['does_not_wfh non_auto'] + \
        work_mode_SD_df['does_not_wfh no_tour' ]
    # denominator here is all workers, going to work or not
    work_mode_SD_df['auto_share'] = work_mode_SD_df['does_not_wfh auto']/work_mode_SD_df['workers']
    work_mode_SD_df['wfh_share' ] = work_mode_SD_df['wfh no_tour'      ]/work_mode_SD_df['workers']

    # join with max telecommute rate (county-based)
    work_mode_SD_df = pandas.merge(
        left  = work_mode_SD_df,
        right = wfh_share_df[['COUNTY','max_wfh_share']],
        how   = 'left',
        on    = 'COUNTY')
    logging.debug("work_mode_SD_df:\n{}".format(work_mode_SD_df))

    # initialize primary df
    EN7_boost_df = tazdata_df[['COUNTY','SD']].copy().drop_duplicates()
    # create dataframe with current EN7_wfh_boost; columns = COUNTY, SD, en7_wfh_boost_prev
    EN7_wfh_boost_dict_list = []
    for line in properties_lines:
        match = re.match(PROPERTY_CDAP_WFH_EN7_RE, line)
        if match: 
            # logging.debug(match.groups())
            en7_dict = {'SD': int(match[1]), 'en7_wfh_boost_prev':float(match[2])}
            EN7_wfh_boost_dict_list.append(en7_dict)
    EN7_boost_df = pandas.merge(
        left  = EN7_boost_df, # this just has COUNTY, district
        right = pandas.DataFrame(EN7_wfh_boost_dict_list)
    )
    logging.debug("Properties file - EN7_boost_df:\n{}".format(EN7_boost_df))

    # join with work_mode_SD_df
    EN7_boost_df = pandas.merge(
         left  = EN7_boost_df, 
         right = work_mode_SD_df)
    logging.debug("After merge, EN7_boost_df (len={}):\n{}".format(len(EN7_boost_df), EN7_boost_df))

    # THIS IS IT
    # start at previous value
    EN7_boost_df['en7_wfh_boost'] = EN7_boost_df['en7_wfh_boost_prev']

    # wfh within threshold of max
    EN7_boost_df['wfh_diff']     = EN7_boost_df['max_wfh_share'] - EN7_boost_df['wfh_share']
    EN7_boost_df['wfh_near_max'] = EN7_boost_df['wfh_diff'].abs() < WFH_SHARE_THRESHHOLD
    EN7_boost_df['change']       = 'none'

    # increase (negative) if auto share is high and we're not at max
    EN7_boost_df.loc[ 
        (EN7_boost_df['auto_share'] > TARGET_AUTO_SHARE) &
        (EN7_boost_df['wfh_share'] < EN7_boost_df['max_wfh_share']) &
        (EN7_boost_df['wfh_near_max'] == False), 
        'change'] = 'increase_wfh'

    # decrease if wfh share is high
    EN7_boost_df.loc[ 
        (EN7_boost_df['wfh_share'] > EN7_boost_df['max_wfh_share']) &
        (EN7_boost_df['wfh_near_max'] == False), 
        'change'] = 'decrease_wfh'

    # implement change: original plus share to bring it to max
    # 0.95 is to back it off a bit
    EN7_boost_df.loc[ EN7_boost_df.change != 'none',
                     'en7_wfh_boost' ] = EN7_boost_df.en7_wfh_boost + (EN7_boost_df['max_wfh_share'] - EN7_boost_df['wfh_share'])*0.95
    
    # but don't let it go negative; we're only boosting
    # this isn't that alarming; the estimated max is from pre-COVID times
    EN7_boost_df.loc[ EN7_boost_df.en7_wfh_boost < 0, 'change'        ] = 'wfh_higher_than_est_max'
    EN7_boost_df.loc[ EN7_boost_df.en7_wfh_boost < 0, 'en7_wfh_boost' ] = 0

    # log summary
    logging.debug(EN7_boost_df[['COUNTY','change']].value_counts())
    logging.debug("Final EN7_boost_df (len={}):\n{}".format(len(EN7_boost_df), EN7_boost_df))

    # write detail
    EN7_boost_df.to_csv(DETAIL_OUTPUT_FILE.format(ITER), header=True, index=False)
    logging.info("Wrote {} lines to {}".format(len(EN7_boost_df), DETAIL_OUTPUT_FILE.format(ITER)))

    # create dict: SD => en7_wfh_boost
    EN7_boost_df_dict = EN7_boost_df.set_index('SD')['en7_wfh_boost'].to_dict()
    logging.debug(EN7_boost_df_dict)

    # update properties file
    PROPERTIES_OUTPUT_FILE = PROPERTIES_FILE # PROPERTIES_FILE.replace(".properties",".test")
    properties_f = open(PROPERTIES_OUTPUT_FILE, "w")
    for line in properties_lines:
        match = re.match(PROPERTY_CDAP_WFH_EN7_RE, line)
        if match: 
            SD = int(match[1])
            properties_f.write(PROPERTY_CDAP_WFH_EN7_STR.format(SD, EN7_boost_df_dict[SD]))
        else:
            properties_f.write(line + '\n')
    properties_f.close()
    logging.info("Wrote {} lines to {}".format(len(properties_lines), PROPERTIES_OUTPUT_FILE))

    sys.exit(0)
