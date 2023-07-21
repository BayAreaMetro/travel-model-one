USAGE = r"""

  python scenarioMetrics.py

  Run this from the model run dir.
  Processes model outputs and creates a single csv with scenario metrics, called metrics\scenario_metrics.csv

  This file will have 3 columns:
    1) scenario ID
    2) metric description
    3) metric value

  Metrics are:

"""

import datetime, os, sys
import numpy, pandas

def tally_travel_cost(iteration, sampleshare, metrics_dict):
    """
    Adds the following keys to metrics_dict:
    total_transit_fares_inc[1-4] ($2000)
    total_transit_person_trips_inc[1-4]
    total_auto_cost_inc[1-4] ($2000)
    total_auto_person_trips_inc[1-4]
    total_households_inc[1-4]
    total_hh_inc_inc[1-4] ($2000)
    """
    print("Tallying travel costs")
    transit_df = pandas.read_csv(os.path.join("metrics","transit_times_by_mode_income.csv"),
                                 sep=",", index_col=[0,1])
    transit_df['Total Cost'] = transit_df['Daily Trips']*transit_df['Avg Cost']
    transit_df = transit_df.groupby('Income').agg('sum')
    for inc_level in range(1,5):
        metrics_dict['total_transit_fares_inc%d' % inc_level] = transit_df.loc['_no_zpv_inc%d' % inc_level, 'Total Cost']
        metrics_dict['total_transit_trips_inc%d' % inc_level] = transit_df.loc['_no_zpv_inc%d' % inc_level, 'Daily Trips']

    auto_df = pandas.read_csv(os.path.join("metrics","auto_times.csv"),
                              sep=",", index_col=[0,1])
    auto_df = auto_df.groupby('Income').agg('sum')
    for inc_level in range(1,5):
        metrics_dict['total_auto_cost_inc%d'  % inc_level] = auto_df.loc['inc%d' % inc_level, ['Total Cost', 
                                                                                               'Bridge Tolls', 
                                                                                               'Value Tolls with discount',
                                                                                               'Cordon tolls with discount']].sum()/100  # cents -> dollars
        metrics_dict['total_auto_trips_inc%d' % inc_level] = auto_df.loc['inc%d' % inc_level, 'Daily Person Trips']

    # Count households from disaggregate output
    household_df = pandas.read_csv(os.path.join("main", "householdData_%d.csv" % iteration),
                                   sep=",")
    household_df['income_cat'] = 0
    household_df.loc[                                 (household_df['income']< 30000), 'income_cat'] = 1
    household_df.loc[(household_df['income']>= 30000)&(household_df['income']< 60000), 'income_cat'] = 2
    household_df.loc[(household_df['income']>= 60000)&(household_df['income']<100000), 'income_cat'] = 3
    household_df.loc[(household_df['income']>=100000)                                , 'income_cat'] = 4
    household_df['num_hhs'] = 1.0/sampleshare


    for inc_level in range(1,5):
        metrics_dict['total_households_inc%d' % inc_level] = household_df.loc[household_df.income_cat==inc_level, 'num_hhs'].sum()
        metrics_dict['total_hh_inc_inc%d'     % inc_level] = household_df.loc[household_df.income_cat==inc_level, 'income' ].sum()

def tally_access_to_jobs(iteration, sampleshare, metrics_dict):
    """
    Reads in database\TimeSkimsDatabaseAM.csv and filters it to O/Ds with
    da time <= 30 minutes OR wTrnW time <= 45 minutes.

    Joining the dest TAZs to jobs, we find the number of jobs accessible from each TAZ
    (within the travel time windows).

    Adds the following keys to the metrics_dict:
    * jobacc_acc_jobs_weighted_persons         : accessible jobs weighted by persons
    * jobacc_trn_only_acc_jobs_weighted_persons:   accessible by transit (and not drv) jobs weighted by persons
    * jobacc_drv_only_acc_jobs_weighted_persons:   accessible by drv (and not transit) jobs weighted by persons
    * jobacc_trn_drv_acc_jobs_weighted_persons :   accessible by transit *and* drv jobs weighted by persons
    * jobacc_total_jobs_weighted_persons       : total jobs x total persons
    * jobacc_accessible_job_share              : accessible job share = jobacc_acc_jobs_weighted_persons/jobacc_total_jobs_weighted_persons
    * jobacc_trn_only_acc_accessible_job_share :   accessible job share for transit (and not drv)
    * jobacc_drv_only_acc_accessible_job_share :   accessible job share for drv (and not transit)
    * jobacc_trn_drv_acc_accessible_job_share  :   accessible job share for transit *and drv

    """
    print("Tallying access to jobs")
    traveltime_df = pandas.read_csv(os.path.join("database","TimeSkimsDatabaseAM.csv"),
                                    sep=",")
    traveltime_df = traveltime_df[['orig','dest','da','wTrnW']]
    # -999 is really no-access
    traveltime_df.replace(to_replace=[-999.0], value=[None], inplace=True)
    len_traveltime_df = len(traveltime_df)

    # look at only those O/D pairs with wTrnW <= 45 OR da <= 30
    traveltime_df = traveltime_df.loc[(traveltime_df.wTrnW <=45)|(traveltime_df.da <=30)]
    print("  Out of {} O/D pairs, {} are accessible within 45 min wTrnW or 30 min da".format
        (len_traveltime_df, len(traveltime_df)))

    # separate the three disjoint sets
    traveltime_df['trn_only'] = 0
    traveltime_df['drv_only'] = 0
    traveltime_df['trn_drv' ] = 0
    traveltime_df.loc[ (traveltime_df.wTrnW <=45)&((traveltime_df.da  >30)|pandas.isnull(traveltime_df.da)), 'trn_only'] = 1
    traveltime_df.loc[((traveltime_df.wTrnW > 45)|pandas.isnull(traveltime_df.wTrnW))&(traveltime_df.da <=30), 'drv_only'] = 1
    traveltime_df.loc[ (traveltime_df.wTrnW <=45)&(traveltime_df.da <=30), 'trn_drv' ] = 1
    assert(traveltime_df.trn_only.sum() + traveltime_df.drv_only.sum() + traveltime_df.trn_drv.sum() == len(traveltime_df))

    # destinations are jobs => find number of jobs accessible from each TAZ within the travel time windows
    tazdata_df = pandas.read_csv(os.path.join("landuse", "tazData.csv"), sep=",")
    tazdata_df = tazdata_df[['ZONE','TOTHH','TOTPOP','EMPRES','TOTEMP']]
    total_emp  = tazdata_df['TOTEMP'].sum()
    total_pop  = tazdata_df['TOTPOP'].sum()

    traveltime_df = pandas.merge(left=traveltime_df, right=tazdata_df[['ZONE','TOTEMP']],
                                 left_on="dest",     right_on="ZONE",
                                 how="left")
    traveltime_df.drop('ZONE', axis=1, inplace=True)  # ZONE == dest
    # make these total employment
    traveltime_df.trn_only = traveltime_df.trn_only*traveltime_df.TOTEMP
    traveltime_df.drv_only = traveltime_df.drv_only*traveltime_df.TOTEMP
    traveltime_df.trn_drv  = traveltime_df.trn_drv *traveltime_df.TOTEMP
    # make these numeric
    traveltime_df["da"   ] = pandas.to_numeric(traveltime_df["da"   ])
    traveltime_df["wTrnW"] = pandas.to_numeric(traveltime_df["wTrnW"])
    # print(traveltime_df.head())

    # aggregate to origin
    traveltime_df_grouped = traveltime_df.groupby(['orig'])
    accessiblejobs_df = traveltime_df_grouped.agg({'da':numpy.mean, 'wTrnW':numpy.mean,
                                                  'TOTEMP':numpy.sum, 'trn_only':numpy.sum, 'drv_only':numpy.sum, 'trn_drv':numpy.sum})
    # print(accessiblejobs_df.head())

    # read communities of concern
    coc_df = pandas.read_csv(os.path.join("metrics", "CommunitiesOfConcern.csv"), sep=",")
    tazdata_df = pandas.merge(left=tazdata_df, right=coc_df, left_on="ZONE", right_on="taz")
    tazdata_df.rename(columns={"in_set":"in_coc"}, inplace=True)
    print("  Read {} TAZs in communities of concern".format(tazdata_df["in_coc"].sum()))

    # read hra
    hra_df = pandas.read_csv(os.path.join("INPUT", "metrics", "taz_hra_crosswalk.csv"))
    hra_df.loc[ pandas.isnull(hra_df["taz_hra"]), "taz_hra"] = 0  # make it 0 or 1
    hra_df["taz_hra"] = hra_df["taz_hra"].astype(int)
    print("  Read {} TAZs in HRAs".format(hra_df["taz_hra"].sum()))
    tazdata_df = pandas.merge(left=tazdata_df, right=hra_df[["taz1454","taz_hra"]], left_on="ZONE", right_on="taz1454")
    tazdata_df.rename(columns={"taz_hra":"in_hra"}, inplace=True)

    # read urban/suburban categories
    urban_suburban_df = pandas.read_csv(os.path.join("INPUT","metrics", "taz_urban_suburban.csv"))
    urban_suburban_df.rename(columns={"area_type":"U_S_R"}, inplace=True)  # Urban Suburban Rural
    print("  Read urban_suburban_df:\n{}".format(urban_suburban_df["U_S_R"].value_counts()))
    tazdata_df = pandas.merge(left=tazdata_df, right=urban_suburban_df, left_on="ZONE", right_on="TAZ1454")
    tazdata_df.drop(columns=["taz","taz1454","TAZ1454"], inplace=True)
    print("  => tazdata_df head:\n{}".format(tazdata_df.head()))

    # join persons to origin
    accessiblejobs_df = pandas.merge(left=accessiblejobs_df, right=tazdata_df[['ZONE','TOTPOP','in_coc','in_hra','U_S_R']],
                                     left_index=True,         right_on="ZONE",
                                     how="left")
    accessiblejobs_df[  'TOTEMP_weighted'] = accessiblejobs_df[  'TOTEMP']*accessiblejobs_df['TOTPOP']
    accessiblejobs_df['trn_only_weighted'] = accessiblejobs_df['trn_only']*accessiblejobs_df['TOTPOP']
    accessiblejobs_df['drv_only_weighted'] = accessiblejobs_df['drv_only']*accessiblejobs_df['TOTPOP']
    accessiblejobs_df[ 'trn_drv_weighted'] = accessiblejobs_df[ 'trn_drv']*accessiblejobs_df['TOTPOP']
    # print(accessiblejobs_df.head())

    for suffix in ["", "_coc","_noncoc","_hra","_nonhra","_urban","_suburban","_rural"]:

        # restrict to suffix if necessary
        accjob_subset_df = accessiblejobs_df
        totalpop_subset  = total_pop
        if suffix == "_coc":
            accjob_subset_df = accessiblejobs_df.loc[accessiblejobs_df["in_coc"]==1]
            totalpop_subset  = tazdata_df.loc[tazdata_df["in_coc"]==1, "TOTPOP"].sum()
        elif suffix == "_noncoc":
            accjob_subset_df = accessiblejobs_df.loc[accessiblejobs_df["in_coc"]==0]
            totalpop_subset  = tazdata_df.loc[tazdata_df["in_coc"]==0, "TOTPOP"].sum()
        elif suffix == "_hra":
            accjob_subset_df = accessiblejobs_df.loc[accessiblejobs_df["in_hra"]==1]
            totalpop_subset  = tazdata_df.loc[tazdata_df["in_hra"]==1, "TOTPOP"].sum()
        elif suffix == "_nonhra":
            accjob_subset_df = accessiblejobs_df.loc[accessiblejobs_df["in_hra"]==0]
            totalpop_subset  = tazdata_df.loc[tazdata_df["in_hra"]==0, "TOTPOP"].sum()
        elif suffix == "_urban":
            accjob_subset_df = accessiblejobs_df.loc[accessiblejobs_df["U_S_R"]=="urban"]
            totalpop_subset  = tazdata_df.loc[tazdata_df["U_S_R"]=="urban", "TOTPOP"].sum()
        elif suffix == "_suburban":
            accjob_subset_df = accessiblejobs_df.loc[accessiblejobs_df["U_S_R"]=="suburban"]
            totalpop_subset  = tazdata_df.loc[tazdata_df["U_S_R"]=="suburban", "TOTPOP"].sum()
        elif suffix == "_rural":
            accjob_subset_df = accessiblejobs_df.loc[accessiblejobs_df["U_S_R"]=="rural"]
            totalpop_subset  = tazdata_df.loc[tazdata_df["U_S_R"]=="rural", "TOTPOP"].sum()

        # numerator = accessible jobs weighted by persons
        #  e.g. sum over TAZs of (totpop at TAZ x totemp jobs accessible)
        # denominator = total jobs weighted by persons
        metrics_dict['jobacc_acc_jobs_weighted_persons%s'          % suffix] = accjob_subset_df[  'TOTEMP_weighted'].sum()
        metrics_dict['jobacc_trn_only_acc_jobs_weighted_persons%s' % suffix] = accjob_subset_df['trn_only_weighted'].sum()
        metrics_dict['jobacc_drv_only_acc_jobs_weighted_persons%s' % suffix] = accjob_subset_df['drv_only_weighted'].sum()
        metrics_dict['jobacc_trn_drv_acc_jobs_weighted_persons%s'  % suffix] = accjob_subset_df[ 'trn_drv_weighted'].sum()
        metrics_dict['jobacc_total_jobs_weighted_persons%s'        % suffix] = total_emp*totalpop_subset
        metrics_dict['jobacc_accessible_job_share%s'               % suffix] = float(metrics_dict['jobacc_acc_jobs_weighted_persons%s'          % suffix]) / float(metrics_dict['jobacc_total_jobs_weighted_persons%s' % suffix])
        metrics_dict['jobacc_trn_only_acc_accessible_job_share%s'  % suffix] = float(metrics_dict['jobacc_trn_only_acc_jobs_weighted_persons%s' % suffix]) / float(metrics_dict['jobacc_total_jobs_weighted_persons%s' % suffix])
        metrics_dict['jobacc_drv_only_acc_accessible_job_share%s'  % suffix] = float(metrics_dict['jobacc_drv_only_acc_jobs_weighted_persons%s' % suffix]) / float(metrics_dict['jobacc_total_jobs_weighted_persons%s' % suffix])
        metrics_dict['jobacc_trn_drv_acc_accessible_job_share%s'   % suffix] = float(metrics_dict['jobacc_trn_drv_acc_jobs_weighted_persons%s'  % suffix]) / float(metrics_dict['jobacc_total_jobs_weighted_persons%s' % suffix])

def tally_access_to_jobs_v2(iteration, sampleshare, metrics_dict):
    """
    v2 of tally_access_to_jobs() for Blueprint (see Update and expand accessibility metrics @ https://app.asana.com/0/403262763383022/1174396999538101/f)

    Reads in database\TimeSkimsDatabaseAM.csv and outputs accessible jobs weighted by persons for the following:
    * wTrnW time   <= 45 minutes
    * da time      <= 30 minutes
    * da toll time <= 30 minutes
    * bike time    <= 20 minutes
    * walk time    <= 20 minutes

    Unlike tally_access_to_jobs(), each of these are independent metrics

    Joining the dest TAZs to jobs, we find the number of jobs accessible from each TAZ
    (within the travel time windows).

    Adds the following keys to the metrics_dict:
    * jobacc2_wtrn_45_acc_jobs_weighted_persons  : accessible by walk-transit-walk (in 45 min) jobs weighted by persons
    * jobacc2_wtrn_30_acc_jobs_weighted_persons  : accessible by walk-transit-walk (in 30 min) jobs weighted by persons
    * jobacc2_da_30_acc_jobs_weighted_persons    : accessible by drive alone       (in 30 min) jobs weighted by persons
    * jobacc2_dat_30_acc_jobs_weighted_persons   : accessible by drive alone toll  (in 30 min) jobs weighted by persons
    * jobacc2_bike_20_acc_jobs_weighted_persons  : accessibly by bike              (in 20 min) jobs weighted by persons
    * jobacc2_walk_20_acc_jobs_weighted_persons  : accessibly by walk              (in 20 min) jobs weighted by persons

    * jobacc2_total_jobs_weighted_persons        : total jobs x total persons

    * jobacc2_wtrn_45_accessible_job_share       : accessible job share = jobacc2_wtrn_45_acc_jobs_weighted_persons/jobacc2_total_jobs_weighted_persons
    * jobacc2_wtrn_30_accessible_job_share       : accessible job share = jobacc2_wtrn_30_acc_jobs_weighted_persons/jobacc2_total_jobs_weighted_persons
    * jobacc2_da_30_accessible_job_share         : accessible job share = jobacc2_da_30_acc_jobs_weighted_persons  /jobacc2_total_jobs_weighted_persons
    * jobacc2_dat_30_accessible_job_share        : accessible job share = jobacc2_dat_30_acc_jobs_weighted_persons /jobacc2_total_jobs_weighted_persons
    * jobacc2_bike_20_accessible_job_share       : accessible job share = jobacc2_bike_20_acc_jobs_weighted_persons/jobacc2_total_jobs_weighted_persons
    * jobacc2_walk_20_accessible_job_share       : accessible job share = jobacc2_walk_20_acc_jobs_weighted_persons/jobacc2_total_jobs_weighted_persons

    Also do by household (rather than persons) and by household income quartiles

    """
    print("Tallying access to jobs v2")
    traveltime_df = pandas.read_csv(os.path.join("database","TimeSkimsDatabaseAM.csv"),
                                    sep=",")
    traveltime_df = traveltime_df[['orig','dest','da','daToll','wTrnW','bike','walk']]
    # -999 is really no-access
    traveltime_df.replace(to_replace=[-999.0], value=[None], inplace=True)
    len_traveltime_df = len(traveltime_df)

    traveltime_df['wtrn_45'] = 0
    traveltime_df['wtrn_30'] = 0
    traveltime_df['da_30'  ] = 0
    traveltime_df['dat_30' ] = 0
    traveltime_df['bike_20'] = 0
    traveltime_df['walk_20'] = 0
    traveltime_df.loc[ (traveltime_df.wTrnW  <=45) , 'wtrn_45'] = 1
    traveltime_df.loc[ (traveltime_df.wTrnW  <=30) , 'wtrn_30'] = 1
    traveltime_df.loc[ (traveltime_df.da     <=30) , 'da_30'  ] = 1
    traveltime_df.loc[ (traveltime_df.daToll <=30) , 'dat_30' ] = 1
    traveltime_df.loc[ (traveltime_df.bike   <=20) , 'bike_20'] = 1
    traveltime_df.loc[ (traveltime_df.walk   <=20) , 'walk_20'] = 1

    # destinations are jobs => find number of jobs accessible from each TAZ within the travel time windows
    tazdata_df = pandas.read_csv(os.path.join("landuse", "tazData.csv"), sep=",")
    tazdata_df = tazdata_df[['ZONE','TOTHH','HHINCQ1','HHINCQ2','HHINCQ3','HHINCQ4','TOTPOP','EMPRES','TOTEMP']]
    total_emp  = tazdata_df['TOTEMP'].sum()
    total_pop  = tazdata_df['TOTPOP'].sum()

    traveltime_df = pandas.merge(left=traveltime_df, right=tazdata_df[['ZONE','TOTEMP']],
                                 left_on="dest",     right_on="ZONE",
                                 how="left")
    traveltime_df.drop('ZONE', axis=1, inplace=True)  # ZONE == dest
    # make these total employment
    traveltime_df.wtrn_45  = traveltime_df.wtrn_45 *traveltime_df.TOTEMP
    traveltime_df.wtrn_30  = traveltime_df.wtrn_30 *traveltime_df.TOTEMP
    traveltime_df.da_30    = traveltime_df.da_30   *traveltime_df.TOTEMP
    traveltime_df.dat_30   = traveltime_df.dat_30  *traveltime_df.TOTEMP
    traveltime_df.bike_20  = traveltime_df.bike_20 *traveltime_df.TOTEMP
    traveltime_df.walk_20  = traveltime_df.walk_20 *traveltime_df.TOTEMP
    # make these numeric
    traveltime_df['wTrnW' ] = pandas.to_numeric(traveltime_df['wTrnW' ])
    traveltime_df['da'    ] = pandas.to_numeric(traveltime_df['da'    ])
    traveltime_df['daToll'] = pandas.to_numeric(traveltime_df['daToll'])
    traveltime_df['bike'  ] = pandas.to_numeric(traveltime_df['bike'  ])
    traveltime_df['walk'  ] = pandas.to_numeric(traveltime_df['walk'  ])
    # print(traveltime_df.head())

    # aggregate to origin
    traveltime_df_grouped = traveltime_df.groupby(['orig'])
    accessiblejobs_df = traveltime_df_grouped.agg({'wTrnW'  :numpy.mean,
                                                   'da'     :numpy.mean,
                                                   'daToll' :numpy.mean,
                                                   'bike'   :numpy.mean,
                                                   'walk'   :numpy.mean,
                                                   'TOTEMP' :numpy.sum,
                                                   'wtrn_45':numpy.sum,
                                                   'wtrn_30':numpy.sum,
                                                   'da_30'  :numpy.sum,
                                                   'dat_30' :numpy.sum,
                                                   'bike_20':numpy.sum,
                                                   'walk_20':numpy.sum})
    # print(accessiblejobs_df.head())

    # read communities of concern
    coc_df = pandas.read_csv(os.path.join("metrics", "CommunitiesOfConcern.csv"), sep=",")
    tazdata_df = pandas.merge(left=tazdata_df, right=coc_df, left_on="ZONE", right_on="taz")
    tazdata_df.rename(columns={"in_set":"in_coc"}, inplace=True)
    print("  Read {} TAZs in communities of concern".format(tazdata_df["in_coc"].sum()))

    # read hra
    hra_df = pandas.read_csv(os.path.join("INPUT","metrics", "taz_hra_crosswalk.csv"))
    hra_df.loc[ pandas.isnull(hra_df["taz_hra"]), "taz_hra"] = 0  # make it 0 or 1
    hra_df["taz_hra"] = hra_df["taz_hra"].astype(int)
    print("  Read {} TAZs in HRAs".format(hra_df["taz_hra"].sum()))
    tazdata_df = pandas.merge(left=tazdata_df, right=hra_df[["taz1454","taz_hra"]], left_on="ZONE", right_on="taz1454")
    tazdata_df.rename(columns={"taz_hra":"in_hra"}, inplace=True)

    # read urban/suburban categories
    urban_suburban_df = pandas.read_csv(os.path.join("INPUT", "metrics", "taz_urban_suburban.csv"))
    urban_suburban_df.rename(columns={"area_type":"U_S_R"}, inplace=True)  # Urban Suburban Rural
    print("  Read urban_suburban_df:\n{}".format(urban_suburban_df["U_S_R"].value_counts()))
    tazdata_df = pandas.merge(left=tazdata_df, right=urban_suburban_df, left_on="ZONE", right_on="TAZ1454")
    tazdata_df.drop(columns=["taz","taz1454","TAZ1454"], inplace=True)
    print("  => tazdata_df head:\n{}".format(tazdata_df.head()))

    # join persons to origin
    accessiblejobs_df = pandas.merge(left=accessiblejobs_df, right=tazdata_df[['ZONE','TOTPOP','TOTHH','HHINCQ1','HHINCQ2','HHINCQ3','HHINCQ4',
                                                                               'in_coc',"in_hra","U_S_R"]],
                                     left_index=True,         right_on="ZONE",
                                     how="left")

    # population version
    accessiblejobs_df[ 'TOTEMP_weighted'] = accessiblejobs_df[ 'TOTEMP']*accessiblejobs_df['TOTPOP']
    accessiblejobs_df['wtrn_45_weighted'] = accessiblejobs_df['wtrn_45']*accessiblejobs_df['TOTPOP']
    accessiblejobs_df['wtrn_30_weighted'] = accessiblejobs_df['wtrn_30']*accessiblejobs_df['TOTPOP']
    accessiblejobs_df[  'da_30_weighted'] = accessiblejobs_df[  'da_30']*accessiblejobs_df['TOTPOP']
    accessiblejobs_df[ 'dat_30_weighted'] = accessiblejobs_df[ 'dat_30']*accessiblejobs_df['TOTPOP']
    accessiblejobs_df['bike_20_weighted'] = accessiblejobs_df['bike_20']*accessiblejobs_df['TOTPOP']
    accessiblejobs_df['walk_20_weighted'] = accessiblejobs_df['walk_20']*accessiblejobs_df['TOTPOP']


    # print(accessiblejobs_df.head())

    for suffix in ["", "_coc","_noncoc","_hra","_nonhra","_urban","_suburban","_rural"]:

        # restrict to suffix if necessary
        accjob_subset_df = accessiblejobs_df
        totalpop_subset  = total_pop
        if suffix == "_coc":
            accjob_subset_df = accessiblejobs_df.loc[accessiblejobs_df["in_coc"]==1]
            totalpop_subset  = tazdata_df.loc[tazdata_df["in_coc"]==1, "TOTPOP"].sum()
        elif suffix == "_noncoc":
            accjob_subset_df = accessiblejobs_df.loc[accessiblejobs_df["in_coc"]==0]
            totalpop_subset  = tazdata_df.loc[tazdata_df["in_coc"]==0, "TOTPOP"].sum()
        elif suffix == "_hra":
            accjob_subset_df = accessiblejobs_df.loc[accessiblejobs_df["in_hra"]==1]
            totalpop_subset  = tazdata_df.loc[tazdata_df["in_hra"]==1, "TOTPOP"].sum()
        elif suffix == "_nonhra":
            accjob_subset_df = accessiblejobs_df.loc[accessiblejobs_df["in_hra"]==0]
            totalpop_subset  = tazdata_df.loc[tazdata_df["in_hra"]==0, "TOTPOP"].sum()
        elif suffix == "_urban":
            accjob_subset_df = accessiblejobs_df.loc[accessiblejobs_df["U_S_R"]=="urban"]
            totalpop_subset  = tazdata_df.loc[tazdata_df["U_S_R"]=="urban", "TOTPOP"].sum()
        elif suffix == "_suburban":
            accjob_subset_df = accessiblejobs_df.loc[accessiblejobs_df["U_S_R"]=="suburban"]
            totalpop_subset  = tazdata_df.loc[tazdata_df["U_S_R"]=="suburban", "TOTPOP"].sum()
        elif suffix == "_rural":
            accjob_subset_df = accessiblejobs_df.loc[accessiblejobs_df["U_S_R"]=="rural"]
            totalpop_subset  = tazdata_df.loc[tazdata_df["U_S_R"]=="rural", "TOTPOP"].sum()

        # numerator = accessible jobs weighted by persons
        #  e.g. sum over TAZs of (totpop at TAZ x totemp jobs accessible)
        # denominator = total jobs weighted by persons
        metrics_dict['jobacc2_acc_jobs_weighted_persons%s'          % suffix] = accjob_subset_df[  'TOTEMP_weighted'].sum()
        metrics_dict['jobacc2_wtrn_45_acc_jobs_weighted_persons%s'  % suffix] = accjob_subset_df[ 'wtrn_45_weighted'].sum()
        metrics_dict['jobacc2_wtrn_30_acc_jobs_weighted_persons%s'  % suffix] = accjob_subset_df[ 'wtrn_30_weighted'].sum()
        metrics_dict['jobacc2_da_30_acc_jobs_weighted_persons%s'    % suffix] = accjob_subset_df[   'da_30_weighted'].sum()
        metrics_dict['jobacc2_dat_30_acc_jobs_weighted_persons%s'   % suffix] = accjob_subset_df[  'dat_30_weighted'].sum()
        metrics_dict['jobacc2_bike_20_acc_jobs_weighted_persons%s'  % suffix] = accjob_subset_df[ 'bike_20_weighted'].sum()
        metrics_dict['jobacc2_walk_20_acc_jobs_weighted_persons%s'  % suffix] = accjob_subset_df[ 'walk_20_weighted'].sum()

        metrics_dict['jobacc2_total_jobs_weighted_persons%s'        % suffix] = total_emp*totalpop_subset

        metrics_dict['jobacc2_wtrn_45_acc_accessible_job_share%s'  % suffix] = float(metrics_dict['jobacc2_wtrn_45_acc_jobs_weighted_persons%s' % suffix]) / float(metrics_dict['jobacc2_total_jobs_weighted_persons%s' % suffix])
        metrics_dict['jobacc2_wtrn_30_acc_accessible_job_share%s'  % suffix] = float(metrics_dict['jobacc2_wtrn_30_acc_jobs_weighted_persons%s' % suffix]) / float(metrics_dict['jobacc2_total_jobs_weighted_persons%s' % suffix])
        metrics_dict['jobacc2_da_30_acc_accessible_job_share%s'    % suffix] = float(metrics_dict['jobacc2_da_30_acc_jobs_weighted_persons%s'   % suffix]) / float(metrics_dict['jobacc2_total_jobs_weighted_persons%s' % suffix])
        metrics_dict['jobacc2_dat_30_acc_accessible_job_share%s'   % suffix] = float(metrics_dict['jobacc2_dat_30_acc_jobs_weighted_persons%s'  % suffix]) / float(metrics_dict['jobacc2_total_jobs_weighted_persons%s' % suffix])
        metrics_dict['jobacc2_bike_20_acc_accessible_job_share%s'  % suffix] = float(metrics_dict['jobacc2_bike_20_acc_jobs_weighted_persons%s' % suffix]) / float(metrics_dict['jobacc2_total_jobs_weighted_persons%s' % suffix])
        metrics_dict['jobacc2_walk_20_acc_accessible_job_share%s'  % suffix] = float(metrics_dict['jobacc2_walk_20_acc_jobs_weighted_persons%s' % suffix]) / float(metrics_dict['jobacc2_total_jobs_weighted_persons%s' % suffix])

        # reset so these don't get used accidentally
        accjob_subset_df = None
        totalpop_subset  = None

    # household version
    accessiblejobs_df[ 'TOTEMP_weightedhh'] = accessiblejobs_df[ 'TOTEMP']*accessiblejobs_df['TOTHH']
    accessiblejobs_df['wtrn_45_weightedhh'] = accessiblejobs_df['wtrn_45']*accessiblejobs_df['TOTHH']
    accessiblejobs_df['wtrn_30_weightedhh'] = accessiblejobs_df['wtrn_30']*accessiblejobs_df['TOTHH']
    accessiblejobs_df[  'da_30_weightedhh'] = accessiblejobs_df[  'da_30']*accessiblejobs_df['TOTHH']
    accessiblejobs_df[ 'dat_30_weightedhh'] = accessiblejobs_df[ 'dat_30']*accessiblejobs_df['TOTHH']
    accessiblejobs_df['bike_20_weightedhh'] = accessiblejobs_df['bike_20']*accessiblejobs_df['TOTHH']
    accessiblejobs_df['walk_20_weightedhh'] = accessiblejobs_df['walk_20']*accessiblejobs_df['TOTHH']

    accessiblejobs_df[ 'TOTEMP_weightedhhq1q2'] = accessiblejobs_df[ 'TOTEMP']*(accessiblejobs_df['HHINCQ1']+accessiblejobs_df['HHINCQ2'])
    accessiblejobs_df['wtrn_45_weightedhhq1q2'] = accessiblejobs_df['wtrn_45']*(accessiblejobs_df['HHINCQ1']+accessiblejobs_df['HHINCQ2'])
    accessiblejobs_df['wtrn_30_weightedhhq1q2'] = accessiblejobs_df['wtrn_30']*(accessiblejobs_df['HHINCQ1']+accessiblejobs_df['HHINCQ2'])
    accessiblejobs_df[  'da_30_weightedhhq1q2'] = accessiblejobs_df[  'da_30']*(accessiblejobs_df['HHINCQ1']+accessiblejobs_df['HHINCQ2'])
    accessiblejobs_df[ 'dat_30_weightedhhq1q2'] = accessiblejobs_df[ 'dat_30']*(accessiblejobs_df['HHINCQ1']+accessiblejobs_df['HHINCQ2'])
    accessiblejobs_df['bike_20_weightedhhq1q2'] = accessiblejobs_df['bike_20']*(accessiblejobs_df['HHINCQ1']+accessiblejobs_df['HHINCQ2'])
    accessiblejobs_df['walk_20_weightedhhq1q2'] = accessiblejobs_df['walk_20']*(accessiblejobs_df['HHINCQ1']+accessiblejobs_df['HHINCQ2'])

    accessiblejobs_df[ 'TOTEMP_weightedhhq3q4'] = accessiblejobs_df[ 'TOTEMP']*(accessiblejobs_df['HHINCQ3']+accessiblejobs_df['HHINCQ4'])
    accessiblejobs_df['wtrn_45_weightedhhq3q4'] = accessiblejobs_df['wtrn_45']*(accessiblejobs_df['HHINCQ3']+accessiblejobs_df['HHINCQ4'])
    accessiblejobs_df['wtrn_30_weightedhhq3q4'] = accessiblejobs_df['wtrn_30']*(accessiblejobs_df['HHINCQ3']+accessiblejobs_df['HHINCQ4'])
    accessiblejobs_df[  'da_30_weightedhhq3q4'] = accessiblejobs_df[  'da_30']*(accessiblejobs_df['HHINCQ3']+accessiblejobs_df['HHINCQ4'])
    accessiblejobs_df[ 'dat_30_weightedhhq3q4'] = accessiblejobs_df[ 'dat_30']*(accessiblejobs_df['HHINCQ3']+accessiblejobs_df['HHINCQ4'])
    accessiblejobs_df['bike_20_weightedhhq3q4'] = accessiblejobs_df['bike_20']*(accessiblejobs_df['HHINCQ3']+accessiblejobs_df['HHINCQ4'])
    accessiblejobs_df['walk_20_weightedhhq3q4'] = accessiblejobs_df['walk_20']*(accessiblejobs_df['HHINCQ3']+accessiblejobs_df['HHINCQ4'])

    for hhsuffix in ["", "q1q2","q3q4"]:
        metrics_dict['jobacc2_acc_jobs_weighted_hh{}'        .format(hhsuffix)] = accessiblejobs_df[  'TOTEMP_weightedhh{}'.format(hhsuffix)].sum()
        metrics_dict['jobacc2_wtrn_45_acc_jobs_weighted_hh{}'.format(hhsuffix)] = accessiblejobs_df[ 'wtrn_45_weightedhh{}'.format(hhsuffix)].sum()
        metrics_dict['jobacc2_wtrn_30_acc_jobs_weighted_hh{}'.format(hhsuffix)] = accessiblejobs_df[ 'wtrn_30_weightedhh{}'.format(hhsuffix)].sum()
        metrics_dict['jobacc2_da_30_acc_jobs_weighted_hh{}'  .format(hhsuffix)] = accessiblejobs_df[   'da_30_weightedhh{}'.format(hhsuffix)].sum()
        metrics_dict['jobacc2_dat_30_acc_jobs_weighted_hh{}' .format(hhsuffix)] = accessiblejobs_df[  'dat_30_weightedhh{}'.format(hhsuffix)].sum()
        metrics_dict['jobacc2_bike_20_acc_jobs_weighted_hh{}'.format(hhsuffix)] = accessiblejobs_df[ 'bike_20_weightedhh{}'.format(hhsuffix)].sum()
        metrics_dict['jobacc2_walk_20_acc_jobs_weighted_hh{}'.format(hhsuffix)] = accessiblejobs_df[ 'walk_20_weightedhh{}'.format(hhsuffix)].sum()

        metrics_dict['jobacc2_total_jobs_weighted_hh{}'      .format(hhsuffix)] = metrics_dict['jobacc2_acc_jobs_weighted_hh{}'.format(hhsuffix)]

        metrics_dict['jobacc2_wtrn_45_acc_accessible_job_share_hh{}'.format(hhsuffix)] = float(metrics_dict['jobacc2_wtrn_45_acc_jobs_weighted_hh{}'.format(hhsuffix)]) / float(metrics_dict['jobacc2_total_jobs_weighted_hh{}'.format(hhsuffix)])
        metrics_dict['jobacc2_wtrn_30_acc_accessible_job_share_hh{}'.format(hhsuffix)] = float(metrics_dict['jobacc2_wtrn_30_acc_jobs_weighted_hh{}'.format(hhsuffix)]) / float(metrics_dict['jobacc2_total_jobs_weighted_hh{}'.format(hhsuffix)])
        metrics_dict['jobacc2_da_30_acc_accessible_job_share_hh{}'  .format(hhsuffix)] = float(metrics_dict['jobacc2_da_30_acc_jobs_weighted_hh{}'  .format(hhsuffix)]) / float(metrics_dict['jobacc2_total_jobs_weighted_hh{}'.format(hhsuffix)])
        metrics_dict['jobacc2_dat_30_acc_accessible_job_share_hh{}' .format(hhsuffix)] = float(metrics_dict['jobacc2_dat_30_acc_jobs_weighted_hh{}' .format(hhsuffix)]) / float(metrics_dict['jobacc2_total_jobs_weighted_hh{}'.format(hhsuffix)])
        metrics_dict['jobacc2_bike_20_acc_accessible_job_share_hh{}'.format(hhsuffix)] = float(metrics_dict['jobacc2_bike_20_acc_jobs_weighted_hh{}'.format(hhsuffix)]) / float(metrics_dict['jobacc2_total_jobs_weighted_hh{}'.format(hhsuffix)])
        metrics_dict['jobacc2_walk_20_acc_accessible_job_share_hh{}'.format(hhsuffix)] = float(metrics_dict['jobacc2_walk_20_acc_jobs_weighted_hh{}'.format(hhsuffix)]) / float(metrics_dict['jobacc2_total_jobs_weighted_hh{}'.format(hhsuffix)])
 

def tally_goods_movement_delay(iteration, sampleshare, metrics_dict):
    """
    Reads in hwy\iter%ITER%\avgload5period_vehclasses.csv and calculates total vehicle hours of delay on
    roadway links with regfreight != 0

    Also tallys TOTPOP from landuse\tazdata.csv for per-capita delay calculation.

    Adds the following keys to the metrics_dict:
    * goods_delay_vehicle_hours : total vehicle hours of delay on regfreight roadway links
    * goods_delay_total_pop     : total persons
    * goods_delay_vhd_per_person: goods_delay_vehicle_hours/goods_delay_total_pop
    """
    print("Tallying goods movement delay")
    roadvols_df = pandas.read_csv(os.path.join("hwy","iter%d" % iteration, "avgload5period_vehclasses.csv"), sep=",")
    tazdata_df  = pandas.read_csv(os.path.join("landuse", "tazData.csv"), sep=",")

    # filter to just those with freight
    roadvols_df = roadvols_df.loc[roadvols_df.regfreight != 0]

    # calculate the vehicle hours of delay
    total_vehicle_hours_delay = 0
    for timeperiod in ['EA','AM','MD','PM','EV']:
        # vehicle-hours of delay
        roadvols_df['vhd_%s' % timeperiod] = roadvols_df['vol%s_tot' % timeperiod]*(roadvols_df['ctim%s' % timeperiod] - roadvols_df['fft'])/60.0
        total_vehicle_hours_delay += roadvols_df['vhd_%s' % timeperiod].sum()

    # store it
    metrics_dict['goods_delay_vehicle_hours']  = total_vehicle_hours_delay
    metrics_dict['goods_delay_total_pop']      = tazdata_df['TOTPOP'].sum()
    metrics_dict['goods_delay_vhd_per_person'] = total_vehicle_hours_delay/float(tazdata_df['TOTPOP'].sum())

def tally_nonauto_mode_share(iteration, sampleshare, metrics_dict):
    """
    Tallies the non auto mode share for trips, by reading
    main\indivTripData_%ITER%.csv and main\jointTripData_%ITER%.csv

    Adds the following keys to the metrics_dict:
    * nonauto_mode_share_nonauto_trips : total nonauto trips
    * nonauto_mode_share_total_trips   : total trips
    * nonauto_mode_share               : total nonauto trips / total trips

    """
    print("Tallying non auto mode share")

    trips_df = None
    for trip_type in ['indiv', 'joint']:
        filename = os.path.join("main", "%sTripData_%d.csv" % (trip_type, iteration))
        temp_trips_df = pandas.read_table(filename, sep=",")
        print("  Read {} {} trips".format(len(temp_trips_df), trip_type))

        if trip_type == 'indiv':
            # each row is a trip; scale by sampleshare
            temp_trips_df['num_participants'] = 1.0/sampleshare

            trips_df = temp_trips_df
        else:
            # scale by sample share
            temp_trips_df['num_participants'] = temp_trips_df['num_participants']/sampleshare
            trips_df = pandas.concat([trips_df, temp_trips_df], axis=0, sort=True)

    metrics_dict['nonauto_mode_share_walk_trips'   ] = trips_df.loc[trips_df['trip_mode']==7].num_participants.sum()
    metrics_dict['nonauto_mode_share_bike_trips'   ] = trips_df.loc[trips_df['trip_mode']==8].num_participants.sum()
    metrics_dict['nonauto_mode_share_transit_trips'] = trips_df.loc[trips_df['trip_mode']>=9].num_participants.sum()
    metrics_dict['nonauto_mode_share_nonauto_trips'] = trips_df.loc[trips_df['trip_mode']>=7].num_participants.sum()
    metrics_dict['nonauto_mode_share_total_trips'  ] = trips_df.num_participants.sum()

    metrics_dict['nonauto_mode_share_walk'   ] = float(metrics_dict['nonauto_mode_share_walk_trips'   ])/float(metrics_dict['nonauto_mode_share_total_trips'])
    metrics_dict['nonauto_mode_share_bike'   ] = float(metrics_dict['nonauto_mode_share_bike_trips'   ])/float(metrics_dict['nonauto_mode_share_total_trips'])
    metrics_dict['nonauto_mode_share_transit'] = float(metrics_dict['nonauto_mode_share_transit_trips'])/float(metrics_dict['nonauto_mode_share_total_trips'])
    metrics_dict['nonauto_mode_share'        ] = float(metrics_dict['nonauto_mode_share_nonauto_trips'])/float(metrics_dict['nonauto_mode_share_total_trips'])

def tally_road_cost_vmt(iteration, sampleshare, metrics_dict):
    """
    Tallies the operating cost from driving for autos, small trucks and large trucks, as well as the total VMT.

    Adds the following keys to the metrics_dict:
    * road_total_auto_cost_$2000     : total operating cost for autos in $2000
    * road_total_smtr_cost_$2000     : total operating cost for small trucks in $2000
    * road_total_lrtr_cost_$2000     : total operating cost for large trucks in $2000
    * road_vmt_auto                  : VMT by autos
    * road_vmt_smtr                  : VMT by small trucks
    * road_vmt_lrtr                  : VMT by large trucks

    """
    print("Tallying roads cost and vmt")
    roadvols_df = pandas.read_csv(os.path.join("hwy","iter%d" % iteration, "avgload5period_vehclasses.csv"), sep=",")
    # [auto,smtr,lrtr]opc      = total opcost for autos, small trucks and large trucks in 2000 cents per mile

    # keep sums
    road_total_auto_cost    = 0
    road_total_smtr_cost    = 0
    road_total_lrtr_cost    = 0
    auto_vmt = 0
    smtr_vmt = 0
    lrtr_vmt = 0

    for timeperiod in ['EA','AM','MD','PM','EV']:
        # total auto volume for the timeperiod
        roadvols_df['vol%s_auto' % timeperiod] = roadvols_df['vol%s_da'  % timeperiod] + roadvols_df['vol%s_s2'  % timeperiod] + roadvols_df['vol%s_s3'  % timeperiod] + \
                                                 roadvols_df['vol%s_dat' % timeperiod] + roadvols_df['vol%s_s2t' % timeperiod] + roadvols_df['vol%s_s3t' % timeperiod]
        # vmt
        roadvols_df['vmt%s_auto' % timeperiod] = roadvols_df['vol%s_auto' % timeperiod]*roadvols_df['distance']
        roadvols_df['vmt%s_smtr' % timeperiod] = roadvols_df['distance']*(roadvols_df['vol%s_sm' % timeperiod]+roadvols_df['vol%s_smt' % timeperiod])
        roadvols_df['vmt%s_lrtr' % timeperiod] = roadvols_df['distance']*(roadvols_df['vol%s_hv' % timeperiod]+roadvols_df['vol%s_hvt' % timeperiod])

        # auto opcost in $2000
        roadvols_df['autoopc_2000$_%s'      % timeperiod] = 0.01*roadvols_df['autoopc'     ]*roadvols_df['vmt%s_auto' % timeperiod]
        # small truck opcost in $2000
        roadvols_df['smtropc_2000$_%s'      % timeperiod] = 0.01*roadvols_df['smtropc'     ]*roadvols_df['vmt%s_smtr' % timeperiod]
        # large truck opcost in $2000
        roadvols_df['lrtropc_2000$_%s'      % timeperiod] = 0.01*roadvols_df['lrtropc'     ]*roadvols_df['vmt%s_lrtr' % timeperiod]

        road_total_auto_cost    += roadvols_df['autoopc_2000$_%s'      % timeperiod].sum()
        road_total_smtr_cost    += roadvols_df['smtropc_2000$_%s'      % timeperiod].sum()
        road_total_lrtr_cost    += roadvols_df['lrtropc_2000$_%s'      % timeperiod].sum()
        auto_vmt += roadvols_df['vmt%s_auto' % timeperiod].sum()
        smtr_vmt += roadvols_df['vmt%s_smtr' % timeperiod].sum()
        lrtr_vmt += roadvols_df['vmt%s_lrtr' % timeperiod].sum()

    # return it
    metrics_dict['road_total_auto_cost_$2000']    = road_total_auto_cost
    metrics_dict['road_total_smtr_cost_$2000']    = road_total_smtr_cost
    metrics_dict['road_total_lrtr_cost_$2000']    = road_total_lrtr_cost
    metrics_dict['road_vmt_auto']                 = auto_vmt
    metrics_dict['road_vmt_smtr']                 = smtr_vmt
    metrics_dict['road_vmt_lrtr']                 = lrtr_vmt


if __name__ == '__main__':
    pandas.set_option('display.width', 500)
    iteration    = int(os.environ['ITER'])
    sampleshare  = float(os.environ['SAMPLESHARE'])

    metrics_dict = {}
    tally_travel_cost(iteration, sampleshare, metrics_dict)
    tally_access_to_jobs(iteration, sampleshare, metrics_dict)
    tally_access_to_jobs_v2(iteration, sampleshare, metrics_dict)
    tally_goods_movement_delay(iteration, sampleshare, metrics_dict)
    tally_nonauto_mode_share(iteration, sampleshare, metrics_dict)
    tally_road_cost_vmt(iteration, sampleshare, metrics_dict)

    for key in sorted(metrics_dict.keys()):
        print("{:50s} => {}".format(key, metrics_dict[key]))

    out_series = pandas.Series(metrics_dict)
    out_frame  = out_series.to_frame().reset_index()
    out_frame.columns = ['variable_desc', 'value']

    # add the run name... use the current dir
    run_name = os.path.split(os.getcwd())[1]
    out_frame['run_name'] = run_name
    out_frame = out_frame[['run_name','variable_desc','value']]

    out_filename = os.path.join("metrics","scenario_metrics.csv")
    out_frame.to_csv(out_filename, header=False, float_format='%.5f', index=False)
    print("Wrote {}".format(out_filename))
