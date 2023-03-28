
def calculate_top_level_metrics(tm_runid, year, tm_vmt_metrics_df, tm_auto_times_df, tm_transit_times_df, tm_commute_df, tm_loaded_network_df, vmt_hh_df,tm_scen_metrics_df, metrics_dict):
    DESCRIPTION = """
    top level metrics that are not part of the 10 metrics, that will give us overall understanding of the pathway, such as:
    - vmt (this is metric 10 but, repeated as a top level metric)
    - auto trips overall
    - auto trips by income level
    - transit trips overall
    - transit trips by income level
    - auto commute trips in peak hours
    - transit commute trips in off peak hours
    - auto commute trips in peak hours
    - transit commute trips in off peak hours
    - freeway delay
    - toll revenues from new tolling (ie exclude any express lane or bridge toll revenues)
        - freeways
        - arterials
        - cordons
    - toll revenues Q1 (ie exclude any express lane or bridge toll revenues)
        - freeways
        - arterials
        - cordons
    - toll revenues Q2 (ie exclude any express lane or bridge toll revenues)
        - freeways
        - arterials
        - cordons
    """
    REVENUE_METHODOLOGY_AND_ASSUMPTIONS = """
    toll revenues - from Value Tolls field in auto times --> this is daily revenue in $2000 cents
    260 days a year
    convert cents to dollars
    adjust $2000 to $2023 for YOE revenue in 2023 using CPI index
    adjust $2023 to $2035 and beyond to $2050 using inflation factor 1.03
    your output variables should be
    annual revenue
    total 15 year revenue (2035-2050)
    each of those split by four income level and other (i.e. ix/air/truck)
    """
    metric_id = 'overall'

    # calculate vmt (as calculated in pba50_metrics.py)
    metrics_dict[tm_runid, metric_id,'top_level','VMT','daily_total_vmt',year] = tm_auto_times_df.loc[:,'Vehicle Miles'].sum()
    # # calculate hh vmt 
    # metrics_dict[tm_runid, metric_id,'top_level','VMT','daily_household_vmt',year] = (vmt_hh_df.loc[:,'vmt'] * vmt_hh_df.loc[:,'freq']).sum()

    # calculate auto trips (as calculated in scenarioMetrics.py)
    auto_trips_overall = 0
    auto_times_summed = tm_auto_times_df.copy().groupby('Income').agg('sum')
    for inc_level in range(1,5):
        metrics_dict[tm_runid, metric_id,'top_level','Trips', 'Daily_total_auto_trips_inc%d' % inc_level, year] = auto_times_summed.loc['inc%d' % inc_level, 'Daily Person Trips']
        metrics_dict[tm_runid, metric_id,'top_level','VMT', 'Daily_total_auto_VMT_inc%d' % inc_level, year] = auto_times_summed.loc['inc%d' % inc_level, 'Vehicle Miles']
        # total auto trips
        auto_trips_overall += auto_times_summed.loc['inc%d' % inc_level, 'Daily Person Trips']
    metrics_dict[tm_runid, metric_id,'top_level','Trips', 'Daily_total_auto_trips_overall', year] = auto_trips_overall
    # calculate vmt and trip breakdown to understand what's going on
    for auto_times_mode in ['truck', 'ix', 'air', 'zpv_tnc']:
        metrics_dict[tm_runid, metric_id,'top_level','Trips', 'Daily_{}_trips'.format(auto_times_mode), year] = tm_auto_times_df.copy().loc[(tm_auto_times_df['Mode'].str.contains(auto_times_mode) == True), 'Daily Person Trips'].sum()
        metrics_dict[tm_runid, metric_id,'top_level','VMT', 'Daily_{}_vmt'.format(auto_times_mode), year] = tm_auto_times_df.copy().loc[(tm_auto_times_df['Mode'].str.contains(auto_times_mode) == True), 'Vehicle Miles'].sum()

    # compute Fwy and Non_Fwy VMT
    vmt_df = tm_loaded_network_df.copy()
    vmt_df['total_vmt'] = (vmt_df['distance']*(vmt_df['volEA_tot']+vmt_df['volAM_tot']+vmt_df['volMD_tot']+vmt_df['volPM_tot']+vmt_df['volEV_tot']))
    fwy_vmt_df = vmt_df.copy().loc[(vmt_df['ft'] == 1)|(vmt_df['ft'] == 2)|(vmt_df['ft'] == 8)]
    arterial_vmt_df = vmt_df.copy().loc[(vmt_df['ft'] == 7)]
    expressway_vmt_df = vmt_df.copy().loc[(vmt_df['ft'] == 3)]
    collector_vmt_df = vmt_df.copy().loc[(vmt_df['ft'] == 4)]
    metrics_dict[tm_runid, metric_id,'top_level','VMT', 'Daily_fwy_vmt', year] = fwy_vmt_df.loc[:,'total_vmt'].sum()
    metrics_dict[tm_runid, metric_id,'top_level','VMT', 'Daily_arterial_vmt', year] = arterial_vmt_df.loc[:,'total_vmt'].sum()
    metrics_dict[tm_runid, metric_id,'top_level','VMT', 'Daily_expressway_vmt', year] = expressway_vmt_df.loc[:,'total_vmt'].sum()
    metrics_dict[tm_runid, metric_id,'top_level','VMT', 'Daily_collector_vmt', year] = collector_vmt_df.loc[:,'total_vmt'].sum()

    # calculate transit trips (as calculated in scenarioMetrics.py)
    transit_trips_overall = 0
    transit_times_summed = tm_transit_times_df.copy().groupby('Income').agg('sum')
    for inc_level in range(1,5):
        metrics_dict[tm_runid, metric_id,'top_level','Trips','Daily_total_transit_trips_inc%d' % inc_level, year] = transit_times_summed.loc['_no_zpv_inc%d' % inc_level, 'Daily Trips']
        transit_trips_overall += transit_times_summed.loc['_no_zpv_inc%d' % inc_level, 'Daily Trips']
    metrics_dict[tm_runid, metric_id,'top_level','Trips', 'Daily_total_transit_trips_overall', year] = transit_trips_overall

    # calculate auto and transit commute trips (similar to PBA2050 [\metrics development\diverse] Healthy: commute mode share)
    # simplify modes
    tm_commute_df.loc[(tm_commute_df['tour_mode'] == 1)|(tm_commute_df['tour_mode'] == 2),'mode'] = 'sov'
    tm_commute_df.loc[(tm_commute_df['tour_mode'] == 3)|(tm_commute_df['tour_mode'] == 4)|(tm_commute_df['tour_mode'] == 5)|(tm_commute_df['tour_mode'] == 6),'mode'] = 'hov'
    tm_commute_df.loc[(tm_commute_df['tour_mode'] == 20)|(tm_commute_df['tour_mode'] == 21),'mode'] = 'tnc'
    tm_commute_df.loc[(tm_commute_df['tour_mode'] == 19),'mode'] = 'taxi'
    tm_commute_df.loc[(tm_commute_df['tour_mode'] == 9)|(tm_commute_df['tour_mode'] == 10)|(tm_commute_df['tour_mode'] == 11)|(tm_commute_df['tour_mode'] == 12)|(tm_commute_df['tour_mode'] == 13)|(tm_commute_df['tour_mode'] == 14)|(tm_commute_df['tour_mode'] == 15)|(tm_commute_df['tour_mode'] == 16)|(tm_commute_df['tour_mode'] == 17)|(tm_commute_df['tour_mode'] == 18),'mode'] = 'transit'
    tm_commute_df.loc[(tm_commute_df['tour_mode'] == 7),'mode'] = 'walk'
    tm_commute_df.loc[(tm_commute_df['tour_mode'] == 8),'mode'] = 'bike'

    # pick out df of auto and transit trips
    commute_auto_trips = tm_commute_df.copy().loc[(tm_commute_df['mode'] == 'sov')]
    commute_transit_trips = tm_commute_df.copy().loc[(tm_commute_df['mode'] == 'transit')]

    # calculate trips and percentages
    auto_peak_trips = commute_auto_trips.copy().loc[(commute_auto_trips['timeCodeHwNum'] == 2)|(commute_auto_trips['timeCodeHwNum'] == 4),'freq'].sum()
    auto_offpeak_trips = commute_auto_trips.copy().loc[(commute_auto_trips['timeCodeHwNum'] == 3),'freq'].sum()
    transit_peak_trips = commute_transit_trips.copy().loc[(commute_transit_trips['timeCodeHwNum'] == 2)|(commute_transit_trips['timeCodeHwNum'] == 4),'freq'].sum()
    transit_offpeak_trips = commute_transit_trips.copy().loc[(commute_transit_trips['timeCodeHwNum'] == 3),'freq'].sum()
    total_auto_trips = auto_peak_trips + auto_offpeak_trips
    total_transit_trips = transit_peak_trips + transit_offpeak_trips
    peak_percent_of_total_auto_trips = (auto_peak_trips)/total_auto_trips
    offpeak_percent_of_total_auto_trips = (auto_offpeak_trips)/total_auto_trips
    peak_percent_of_total_transit_trips = (transit_peak_trips)/total_transit_trips
    offpeak_percent_of_total_transit_trips = (transit_offpeak_trips)/total_transit_trips
    # enter metrics into dict
    metrics_dict[tm_runid, metric_id,'top_level','Auto Commute Trips', 'daily_auto_peak_trips', year] = auto_peak_trips
    metrics_dict[tm_runid, metric_id,'top_level','Auto Commute Trips', 'daily_auto_offpeak_trips', year] = auto_offpeak_trips
    metrics_dict[tm_runid, metric_id,'top_level','Auto Commute Trips', 'daily_auto_total_trips', year] = total_auto_trips
    metrics_dict[tm_runid, metric_id,'top_level','Auto Commute Trips', 'peak_percent_of_total_auto_trips', year] = peak_percent_of_total_auto_trips
    metrics_dict[tm_runid, metric_id,'top_level','Auto Commute Trips', 'offpeak_percent_of_total_auto_trips', year] = offpeak_percent_of_total_auto_trips

    metrics_dict[tm_runid, metric_id,'top_level','Transit Commute Trips', 'daily_transit_peak_trips', year] = transit_peak_trips
    metrics_dict[tm_runid, metric_id,'top_level','Transit Commute Trips', 'daily_transit_offpeak_trips', year] = transit_offpeak_trips
    metrics_dict[tm_runid, metric_id,'top_level','Transit Commute Trips', 'daily_transit_total_trips', year] = total_transit_trips
    metrics_dict[tm_runid, metric_id,'top_level','Transit Commute Trips', 'peak_percent_of_total_transit_trips', year] = peak_percent_of_total_transit_trips
    metrics_dict[tm_runid, metric_id,'top_level','Transit Commute Trips', 'offpeak_percent_of_total_transit_trips', year] = offpeak_percent_of_total_transit_trips

    # calculate freeway delay:
    # MTC calculates two measures of delay 
    # - congested delay, or delay that occurs when speeds are below 35 miles per hour, 
    # and total delay, or delay that occurs when speeds are below the posted speed limit.
    # https://www.vitalsigns.mtc.ca.gov/time-spent-congestion#:~:text=To%20illustrate%2C%20if%201%2C000%20vehicles,hours%20%3D%204.76%20vehicle%20hours%5D.
    fwy_network_df = tm_loaded_network_df.copy().loc[(tm_loaded_network_df['ft'] == 1)|(tm_loaded_network_df['ft'] == 2)|(tm_loaded_network_df['ft'] == 8)]

    EA_nonzero_spd_network_df = fwy_network_df.copy().loc[(fwy_network_df['cspdEA'] > 0)]
    EA_total_delay = (EA_nonzero_spd_network_df['distance'] * EA_nonzero_spd_network_df['volEA_tot'] * ((1/EA_nonzero_spd_network_df['cspdEA']).replace(numpy.inf, 0) - (1/EA_nonzero_spd_network_df['ffs']).replace(numpy.inf, 0))).sum()
    AM_nonzero_spd_network_df = fwy_network_df.copy().loc[(fwy_network_df['cspdAM'] > 0)]
    AM_total_delay = (AM_nonzero_spd_network_df['distance'] * AM_nonzero_spd_network_df['volAM_tot'] * ((1/AM_nonzero_spd_network_df['cspdAM']).replace(numpy.inf, 0) - (1/AM_nonzero_spd_network_df['ffs']).replace(numpy.inf, 0))).sum()
    MD_nonzero_spd_network_df = fwy_network_df.copy().loc[(fwy_network_df['cspdMD'] > 0)]
    MD_total_delay = (MD_nonzero_spd_network_df['distance'] * MD_nonzero_spd_network_df['volMD_tot'] * ((1/MD_nonzero_spd_network_df['cspdMD']).replace(numpy.inf, 0) - (1/MD_nonzero_spd_network_df['ffs']).replace(numpy.inf, 0))).sum()
    PM_nonzero_spd_network_df = fwy_network_df.copy().loc[(fwy_network_df['cspdPM'] > 0)]
    PM_total_delay = (PM_nonzero_spd_network_df['distance'] * PM_nonzero_spd_network_df['volPM_tot'] * ((1/PM_nonzero_spd_network_df['cspdPM']).replace(numpy.inf, 0) - (1/PM_nonzero_spd_network_df['ffs']).replace(numpy.inf, 0))).sum()
    EV_nonzero_spd_network_df = fwy_network_df.copy().loc[(fwy_network_df['cspdEV'] > 0)]
    EV_total_delay = (EV_nonzero_spd_network_df['distance'] * EV_nonzero_spd_network_df['volEV_tot'] * ((1/EV_nonzero_spd_network_df['cspdEV']).replace(numpy.inf, 0) - (1/EV_nonzero_spd_network_df['ffs']).replace(numpy.inf, 0))).sum()
    metrics_dict[tm_runid, metric_id,'top_level','Freeway Delay', 'daily_total_freeway_delay_veh_hrs', year] = EA_total_delay + AM_total_delay + MD_total_delay + PM_total_delay + EV_total_delay
    # calculate congested delay
    # only keep the links where the speeds  under 35 mph
    EA_speeds_below_35_df = fwy_network_df.copy().loc[(fwy_network_df['cspdEA'] < 35)]
    AM_speeds_below_35_df = fwy_network_df.copy().loc[(fwy_network_df['cspdAM'] < 35)]
    MD_speeds_below_35_df = fwy_network_df.copy().loc[(fwy_network_df['cspdMD'] < 35)]
    PM_speeds_below_35_df = fwy_network_df.copy().loc[(fwy_network_df['cspdPM'] < 35)]
    EV_speeds_below_35_df = fwy_network_df.copy().loc[(fwy_network_df['cspdEV'] < 35)]

    EA_congested_delay = (EA_speeds_below_35_df['distance'] * EA_speeds_below_35_df['volEA_tot'] * ((1/EA_speeds_below_35_df['cspdEA']).replace(numpy.inf, 0) - (1/35))).sum()
    AM_congested_delay = (AM_speeds_below_35_df['distance'] * AM_speeds_below_35_df['volAM_tot'] * ((1/AM_speeds_below_35_df['cspdAM']).replace(numpy.inf, 0) - (1/35))).sum()
    MD_congested_delay = (MD_speeds_below_35_df['distance'] * MD_speeds_below_35_df['volMD_tot'] * ((1/MD_speeds_below_35_df['cspdMD']).replace(numpy.inf, 0) - (1/35))).sum()
    PM_congested_delay = (PM_speeds_below_35_df['distance'] * PM_speeds_below_35_df['volPM_tot'] * ((1/PM_speeds_below_35_df['cspdPM']).replace(numpy.inf, 0) - (1/35))).sum()
    EV_congested_delay = (EV_speeds_below_35_df['distance'] * EV_speeds_below_35_df['volEV_tot'] * ((1/EV_speeds_below_35_df['cspdEV']).replace(numpy.inf, 0) - (1/35))).sum()
    metrics_dict[tm_runid, metric_id,'top_level','Freeway Delay', 'daily_congested_freeway_delay_veh_hrs', year] = EA_congested_delay + AM_congested_delay + MD_congested_delay + PM_congested_delay + EV_congested_delay

    # calculate toll revenues
    # cpi index data: https://data.bls.gov/pdq/SurveyOutputServlet
    cpi_index_2023 = 299.170
    cpi_index_2000 = 172.2
    adjustment_2000_to_2023 = 1 + (cpi_index_2023 - cpi_index_2000)/cpi_index_2000
    revenue_days_per_year = 260
    inflation_factor = 1.03

    tm_loaded_network_df_copy = tm_loaded_network_df.copy()
    network_with_tolls = tm_loaded_network_df_copy.loc[(tm_loaded_network_df_copy['TOLLCLASS'] > 1000)| (tm_loaded_network_df_copy['TOLLCLASS'] == 99)] 
    EA_total_tolls = (network_with_tolls['volEA_tot'] * network_with_tolls['TOLLEA_DA']).sum()/100
    AM_total_tolls = (network_with_tolls['volAM_tot'] * network_with_tolls['TOLLAM_DA']).sum()/100
    MD_total_tolls = (network_with_tolls['volMD_tot'] * network_with_tolls['TOLLMD_DA']).sum()/100
    PM_total_tolls = (network_with_tolls['volPM_tot'] * network_with_tolls['TOLLPM_DA']).sum()/100
    EV_total_tolls = (network_with_tolls['volEV_tot'] * network_with_tolls['TOLLEV_DA']).sum()/100
    daily_toll_rev_2000_dollars = EA_total_tolls + AM_total_tolls + MD_total_tolls + PM_total_tolls + EV_total_tolls
    daily_toll_rev_2023_dollars = daily_toll_rev_2000_dollars * adjustment_2000_to_2023
    annual_toll_rev_2023_dollars = daily_toll_rev_2023_dollars * revenue_days_per_year
    annual_toll_rev_2035_dollars = annual_toll_rev_2023_dollars*inflation_factor**(2035-2023)
    # compute sum of geometric series for year of expenditure value
    fifteen_year_toll_rev_2050_dollars = (annual_toll_rev_2035_dollars * (1- inflation_factor**15))/(1 - inflation_factor)
    
    metrics_dict[tm_runid, metric_id,'top_level','Toll Revenues', 'Daily_toll_revenues_from_new_tolling_2000$', year] = daily_toll_rev_2000_dollars
    metrics_dict[tm_runid, metric_id,'top_level','Toll Revenues', 'Daily_toll_revenues_from_new_tolling_2035$', year] = annual_toll_rev_2035_dollars/260
    metrics_dict[tm_runid, metric_id,'top_level','Toll Revenues', 'Annual_toll_revenues_from_new_tolling_2035$', year] = annual_toll_rev_2035_dollars
    metrics_dict[tm_runid, metric_id,'top_level','Toll Revenues', '15_yr_toll_revenues_from_new_tolling_YOE$', year] = fifteen_year_toll_rev_2050_dollars

    # NEED HELP FROM FMS TEAM --> RE: INCOME ASSIGNMENT
    # calculate toll revenues by income quartile (calculation from scenarioMetrics.py)
    toll_revenues_overall = 0
    if 'Path3' in tm_runid:
        toll_revenue_column = 'Cordon Tolls'
    else:
        toll_revenue_column = 'Value Tolls'
    for inc_level in range(1,5):
        tm_tot_hh_incgroup = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_households_inc%d" % inc_level),'value'].item()
        metrics_dict[tm_runid, metric_id,'top_level','Tolls', 'Daily_approximate_toll_values_per_inc%dHH_(ie_includes_express_lane_revenues)_2000$' % inc_level, year] = (auto_times_summed.loc['inc%d' % inc_level, toll_revenue_column]/100)/tm_tot_hh_incgroup
        toll_revenues_overall += auto_times_summed.loc['inc%d' % inc_level, toll_revenue_column]/100
    # use as a check for calculated value above. should be in the same ballpark. calculate ratio and use for links?
    metrics_dict[tm_runid, metric_id,'top_level','Toll Revenues', 'Daily_approximate_toll_revenues_(ie_includes_express_lane_revenues)_2000$', year] = toll_revenues_overall


def calculate_change_between_run_and_base(tm_runid, tm_runid_base, year, metric_id, metrics_dict):
    #function to compare two runs and enter difference as a metric in dictionary
    metrics_dict_series = pd.Series(metrics_dict)
    metrics_dict_df  = metrics_dict_series.to_frame().reset_index()
    metrics_dict_df.columns = ['modelrun_id','metric_id','intermediate/final','key','metric_desc','year','value']
    #     make a list of the metrics from the run of interest to iterate through and calculate a difference with
    metrics_list = metrics_dict_df.copy().loc[(metrics_dict_df['modelrun_id'].str.contains(tm_runid) == True)]
    metrics_list = metrics_list.loc[(metrics_dict_df['metric_id'].str.contains(metric_id) == True)]['metric_desc']
    # iterate through the list
    # add in grouping field
    key = 'Change'
    for metric in metrics_list:
        if (('_AM' in metric)):
            temp = metric.split('_AM')[0]
            key = temp.split('travel_time_')[-1]
        elif ('across_key_corridors' in metric):
            key = 'Average Across Corridors'

        val_run = metrics_dict_df.copy().loc[(metrics_dict_df['modelrun_id'].str.contains(tm_runid) == True)].loc[(metrics_dict_df['metric_desc'].str.contains(metric) == True)].iloc[0]['value']
        val_base = metrics_dict_df.copy().loc[(metrics_dict_df['modelrun_id'].str.contains(tm_runid_base) == True)].loc[(metrics_dict_df['metric_desc'].str.contains(metric) == True)].iloc[0]['value']
        metrics_dict[tm_runid, metric_id,'extra',key,'change_in_{}'.format(metric),year] = (val_run-val_base)
        metrics_dict[tm_runid, metric_id,'extra',key,'pct_change_in_{}'.format(metric),year] = ((val_run-val_base)/val_base)



def calculate_Affordable1_transportation_costs(tm_runid, year, tm_scen_metrics_df, tm_auto_owned_df, tm_travel_cost_df, tm_auto_times_df, metrics_dict):
    # 1) Transportation costs as a share of household income
    
    # pulled from pba50_metrics.py
    # https://github.com/BayAreaMetro/travel-model-one/blob/594ee4c4df8ac044cdd3db68fae90879c0aff14d/utilities/RTP/metrics/pba50_metrics.py
    metric_id = "Affordable 1"

    days_per_year = 300

    # Total number of households
    tm_tot_hh      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_households_inc") == True), 'value'].sum()
    tm_tot_hh_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_households_inc1"),'value'].item()
    tm_tot_hh_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_households_inc2"),'value'].item()

    # Total household income (model outputs are in 2000$, annual)
    tm_total_hh_inc      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_hh_inc") == True), 'value'].sum()
    tm_total_hh_inc_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_hh_inc_inc1"),'value'].item()
    tm_total_hh_inc_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_hh_inc_inc2"),'value'].item()

    # Total transit fares (model outputs are in 2000$, per day)
    tm_tot_transit_fares      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_transit_fares") == True), 'value'].sum() * days_per_year
    tm_tot_transit_fares_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_transit_fares_inc1"),'value'].item() * days_per_year
    tm_tot_transit_fares_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_transit_fares_inc2"),'value'].item() * days_per_year

    # Total auto op cost (model outputs are in 2000$, per day)
    tm_tot_auto_op_cost      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_auto_cost_inc") == True), 'value'].sum() * days_per_year
    tm_tot_auto_op_cost_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_auto_cost_inc1"),'value'].item() * days_per_year
    tm_tot_auto_op_cost_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_auto_cost_inc2"),'value'].item() * days_per_year

    # Total auto parking cost (model outputs are in 2000$, per day, in cents)
    #tm_travel_cost_df['park_cost'] = (tm_travel_cost_df['pcost_indiv']+tm_travel_cost_df['pcost_joint']) * tm_travel_cost_df['freq']
    tm_tot_auto_park_cost      = (tm_travel_cost_df.pcost_indiv.sum() + tm_travel_cost_df.pcost_joint.sum()) * days_per_year / 100
    tm_tot_auto_park_cost_inc1 = (tm_travel_cost_df.loc[(tm_travel_cost_df['incQ'] == 1),'pcost_indiv'].sum() + tm_travel_cost_df.loc[(tm_travel_cost_df['incQ'] == 1),'pcost_joint'].sum()) * days_per_year / 100
    tm_tot_auto_park_cost_inc2 = (tm_travel_cost_df.loc[(tm_travel_cost_df['incQ'] == 2),'pcost_indiv'].sum() + tm_travel_cost_df.loc[(tm_travel_cost_df['incQ'] == 2),'pcost_joint'].sum()) * days_per_year / 100

    # Calculating number of autos owned from autos_owned.csv
    tm_auto_owned_df['tot_autos'] = tm_auto_owned_df['autos'] * tm_auto_owned_df['households'] 
    tm_tot_autos_owned      = tm_auto_owned_df['tot_autos'].sum()
    tm_tot_autos_owned_inc1 = tm_auto_owned_df.loc[(tm_auto_owned_df['incQ'] == 1), 'tot_autos'].sum()
    tm_tot_autos_owned_inc2 = tm_auto_owned_df.loc[(tm_auto_owned_df['incQ'] == 2), 'tot_autos'].sum()

    # Total auto ownership cost in 2000$
    tm_tot_auto_owner_cost      = tm_tot_autos_owned      * auto_ownership_cost      * inflation_18_20 / inflation_00_20
    tm_tot_auto_owner_cost_inc1 = tm_tot_autos_owned_inc1 * auto_ownership_cost_inc1 * inflation_18_20 / inflation_00_20
    tm_tot_auto_owner_cost_inc2 = tm_tot_autos_owned_inc2 * auto_ownership_cost_inc2 * inflation_18_20 / inflation_00_20

    # Total Transportation Cost (in 2000$)
    tp_cost      = tm_tot_auto_op_cost      + tm_tot_transit_fares      + tm_tot_auto_owner_cost      + tm_tot_auto_park_cost
    tp_cost_inc1 = tm_tot_auto_op_cost_inc1 + tm_tot_transit_fares_inc1 + tm_tot_auto_owner_cost_inc1 + tm_tot_auto_park_cost_inc1
    tp_cost_inc2 = tm_tot_auto_op_cost_inc2 + tm_tot_transit_fares_inc2 + tm_tot_auto_owner_cost_inc2 + tm_tot_auto_park_cost_inc2
    
    # Transportation cost % of income
    tp_cost_pct_inc          = tp_cost      / tm_total_hh_inc
    tp_cost_pct_inc_inc1     = tp_cost_inc1 / tm_total_hh_inc_inc1
    tp_cost_pct_inc_inc2     = tp_cost_inc2 / tm_total_hh_inc_inc2
    tp_cost_pct_inc_inc1and2 = (tp_cost_inc1+tp_cost_inc2) / (tm_total_hh_inc_inc1+tm_total_hh_inc_inc2)


    # Transportation cost % of income metrics       
    metrics_dict[tm_runid,metric_id,'final','Transportation Costs','transportation_cost_pct_income',year]      = tp_cost_pct_inc
    metrics_dict[tm_runid,metric_id,'final','Transportation Costs','transportation_cost_pct_income_inc1',year] = tp_cost_pct_inc_inc1
    metrics_dict[tm_runid,metric_id,'final','Transportation Costs','transportation_cost_pct_income_inc2',year] = tp_cost_pct_inc_inc2
    metrics_dict[tm_runid,metric_id,'final','Transportation Costs','transportation_cost_pct_income_inc1and2',year] = tp_cost_pct_inc_inc1and2

    # Tolls (intermediate metric)
    
    # Reading auto times file
    tm_auto_times_df = tm_auto_times_df.copy().groupby('Income').agg('sum')

    # Calculating Total Tolls per day = bridge tolls + value tolls  (2000$)
    total_tolls = OrderedDict()
    for inc_level in range(1,5): 
        total_tolls['inc%d'  % inc_level] = tm_auto_times_df.loc['inc%d' % inc_level, ['Bridge Tolls', 'Value Tolls']].sum()/100  # cents -> dollars
    total_tolls_allHH = sum(total_tolls.values())
    total_tolls_LIHH = total_tolls['inc1'] + total_tolls['inc2']
    
    # Average Daily Tolls per household
    metrics_dict[tm_runid,metric_id,'intermediate','Toll Costs','toll_cost_pct_income',year]     = total_tolls_allHH / tm_total_hh_inc
    metrics_dict[tm_runid,metric_id,'intermediate','Toll Costs','toll_cost_pct_income_inc1',year] = total_tolls['inc1'] / tm_total_hh_inc_inc1
    metrics_dict[tm_runid,metric_id,'intermediate','Toll Costs','toll_cost_pct_income_inc2',year] = total_tolls['inc2'] / tm_total_hh_inc_inc2
    metrics_dict[tm_runid,metric_id,'intermediate','Toll Costs','toll_cost_pct_income_inc1and2',year]     = total_tolls_LIHH / (tm_total_hh_inc_inc1+tm_total_hh_inc_inc2)



def calculate_auto_travel_time(tm_runid,metric_id, year,network,metrics_dict):
    sum_of_weights = 0 #sum of weights (vmt of corridor) to be used for weighted average 
    total_weighted_travel_time = 0 #sum for numerator
    n = 0 #counter for simple average 
    total_travel_time = 0 #numerator for simple average 

    for i in minor_groups:
        #     add minor ampm ctim to metric dict
        minor_group_am_df = network.loc[network['Grouping minor_AMPM'] == i+'_AM']
        minor_group_am = sum_grouping(minor_group_am_df,'AM')
        
        # vmt to be used for weighted averages
        # create df to pull vmt from to use for weighted average
        # for simplicity of calculation, always using the base run VMT
        index_a_b = minor_group_am_df.copy()[['a_b']]
        network_for_vmt_df = tm_loaded_network_df_base.copy().merge(index_a_b, on='a_b', how='right')
        vmt_minor_grouping_AM = (network_for_vmt_df['volAM_tot'] * network_for_vmt_df['distance']).sum()

        # check for length //can remove later
        length_of_grouping = (minor_group_am_df['distance']).sum()
        metrics_dict[tm_runid_base,metric_id,'extra',i,'%s' % i + '_length',year] = length_of_grouping

        metrics_dict[tm_runid_base,metric_id,'extra',i,'%s' % i + '_AM_vmt',year] = vmt_minor_grouping_AM

        # add travel times to metric dict
        metrics_dict[tm_runid,metric_id,'extra',i,'travel_time_%s' % i + '_AM',year] = minor_group_am
        # weighted AM,PM travel times (by vmt)
        weighted_AM_travel_time_by_vmt = minor_group_am * vmt_minor_grouping_AM



def calculate_Affordable2_ratio_time_cost(tm_runid, year, tm_loaded_network_df, network_links, metrics_dict):
    # 2) Ratio of value of auto travel time savings to incremental toll costs

    # borrow from pba metrics calculate_Connected2_hwy_traveltimes(), but only for corridor disaggregation (and maybe commercial vs private vehicle. need to investigate income cat further)
    # make sure to run after the comparison functions have been run, as this takes them as inputs from the metrics dict
    # takes Reliable 1 metric inputs
    # will need to compute a new average across corridors, since we are only interested in the AM period
    metric_id = 'Affordable 2'
  
    network_with_nonzero_tolls = tm_loaded_network_df.copy().loc[(tm_loaded_network_df['TOLLCLASS'] > 1000) | (tm_loaded_network_df['TOLLCLASS'] == 99)]
    network_with_nonzero_tolls = tm_loaded_network_df.copy().loc[(tm_loaded_network_df['USEAM'] == 1)]
    network_with_nonzero_tolls['sum of tolls'] = network_with_nonzero_tolls['TOLLAM_DA'] + network_with_nonzero_tolls['TOLLAM_LRG'] + network_with_nonzero_tolls['TOLLAM_S3']
    # check if run has all lane tolling, if not return 0 for this metric 
    if (network_with_nonzero_tolls['sum of tolls'].sum() == 0):
        metrics_dict[tm_runid, metric_id,'final','Private Auto: All Households','average_ratio_auto_time_savings_to_toll_costs_across_corridors_weighted_by_vmt',year] = 0
        metrics_dict[tm_runid, metric_id,'final','Private Auto: Very Low Income Households','average_ratio_auto_time_savings_to_toll_costs_across_corridors_inc1_weighted_by_vmt',year] = 0
        metrics_dict[tm_runid, metric_id,'final','Private Auto: Very Low Income Households','average_ratio_auto_time_savings_to_toll_costs_across_corridors_inc2_weighted_by_vmt',year] = 0
        metrics_dict[tm_runid, metric_id,'final','Commercial Vehicle','average_ratio_truck_time_savings_to_toll_costs_across_corridors_weighted_by_vmt',year] = 0
        metrics_dict[tm_runid, metric_id,'final','High Occupancy Vehicle','average_ratio_hov_time_savings_to_toll_costs_across_corridors_weighted_by_vmt',year] = 0
        return
    network_with_nonzero_tolls = network_with_nonzero_tolls.loc[(network_with_nonzero_tolls['sum of tolls'] > 0)]
    index_a_b = network_with_nonzero_tolls.copy()[['a_b']]
    network_with_nonzero_tolls_base = tm_loaded_network_df_base.copy().merge(index_a_b, on='a_b', how='right')
    calculate_auto_travel_time(tm_runid,metric_id, year,network_with_nonzero_tolls,metrics_dict)
    calculate_auto_travel_time(tm_runid_base,metric_id, year,network_with_nonzero_tolls_base,metrics_dict)
    # ----calculate difference between runs----

    # run comparisons
    calculate_change_between_run_and_base(tm_runid, tm_runid_base, year, 'Affordable 2', metrics_dict)

    metrics_dict_series = pd.Series(metrics_dict)
    metrics_dict_df  = metrics_dict_series.to_frame().reset_index()
    metrics_dict_df.columns = ['modelrun_id','metric_id','intermediate/final','key','metric_desc','year','value']
    corridor_vmt_df = metrics_dict_df.copy().loc[(metrics_dict_df['metric_desc'].str.contains('_AM_vmt') == True)&(metrics_dict_df['metric_desc'].str.contains('change') == False)]
    # simplify df to relevant model run
    metrics_dict_df = metrics_dict_df.copy().loc[(metrics_dict_df['modelrun_id'].str.contains(tm_runid) == True)]
    #make a list of the metrics from the run of interest to iterate through and calculate numerator of ratio with
    metrics_list = metrics_dict_df.loc[(metrics_dict_df['metric_desc'].str.startswith('change_in_travel_time_') == True)&(metrics_dict_df['metric_desc'].str.contains('_AM') == True)&(metrics_dict_df['metric_desc'].str.contains('vmt') == False)]['metric_desc'] 

    # the list of metrics should have the name of the corridor. split on 'change_in_avg' and pick the end part. if empty, will be final ratio, use this for other disaggregations
    # total tolls and time savings variables to be used for average
    # for weighted average
    sum_of_weighted_ratio_auto_time_savings_to_toll_costs = 0
    sum_of_weighted_ratio_truck_time_savings_to_toll_costs = 0
    sum_of_weighted_ratio_hov_time_savings_to_toll_costs = 0
    sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc1 = 0
    sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc2 = 0

    # for simple average
    sum_of_ratio_auto_time_savings_to_toll_costs = 0
    sum_of_ratio_auto_time_savings_to_toll_costs_inc1 = 0
    sum_of_ratio_auto_time_savings_to_toll_costs_inc2 = 0
    sum_of_ratio_truck_time_savings_to_toll_costs = 0
    sum_of_ratio_hov_time_savings_to_toll_costs = 0

    sum_of_weights = 0 #sum of weights (length of corridor) to be used for weighted average 
    n = 0 #counter to serve as denominator 
    # iterate through list
    for metric in metrics_list:
        minor_grouping_corridor = metric.split('travel_time_')[1]

        # calculate average vmt
        minor_grouping_vmt = corridor_vmt_df.loc[corridor_vmt_df['metric_desc'] == (minor_grouping_corridor + '_vmt')].iloc[0]['value']
        # simplify df to relevant metric
        metric_row = metrics_dict_df.loc[(metrics_dict_df['metric_desc'].str.contains(metric) == True)]
        if (minor_grouping_vmt == 0): #check to make sure there is traffic on the link
            time_savings_minutes = 0
            time_savings_in_hours = 0
        else:
            time_savings_minutes = metric_row.iloc[0]['value']
            time_savings_in_hours = time_savings_minutes/60
        # ____will need to restructure this whole section to include all the calculations here 
        # ____as done for denominator because there is a need to filter the df by toll class and tolls paid
        # ____consider including a call to change_in function here. first define the metrics needed

        # define key for grouping field, consistent with section above
        key = minor_grouping_corridor.split('_AM')[0]

        # private auto numerator: travel time savings
        priv_auto_travel_time_savings_minor_grouping = time_savings_in_hours * private_auto_vot
        metrics_dict[tm_runid, metric_id,'extra',key,'auto_time_savings_minutes_{}_'.format(minor_grouping_corridor),year] = time_savings_minutes 
        metrics_dict[tm_runid, metric_id,'extra',key,'auto_time_savings_hours_{}'.format(minor_grouping_corridor),year] = time_savings_in_hours
        metrics_dict[tm_runid, metric_id,'intermediate',key,'monetized_value_of_auto_time_savings_{}_2020$'.format(minor_grouping_corridor),year] = priv_auto_travel_time_savings_minor_grouping

        # calculate the denominator, incremental toll costs (for PA CV and HOV), by filtering for the links on the corridor and summing across them
        DA_incremental_toll_costs_minor_grouping = network_with_nonzero_tolls.loc[(network_with_nonzero_tolls['Grouping minor_AMPM'].str.contains(minor_grouping_corridor) == True), 'TOLLAM_DA'].sum()/100 #filter and sum across links
        LRG_incremental_toll_costs_minor_grouping = network_with_nonzero_tolls.loc[(network_with_nonzero_tolls['Grouping minor_AMPM'].str.contains(minor_grouping_corridor) == True), 'TOLLAM_LRG'].sum()/100 #filter and sum across links
        S3_incremental_toll_costs_minor_grouping = network_with_nonzero_tolls.loc[(network_with_nonzero_tolls['Grouping minor_AMPM'].str.contains(minor_grouping_corridor) == True), 'TOLLAM_S3'].sum()/100 #filter and sum across links
        DA_incremental_toll_costs_inc1_minor_grouping = (DA_incremental_toll_costs_minor_grouping * inc1_discounts_credits_rebates)
        DA_incremental_toll_costs_inc2_minor_grouping = (DA_incremental_toll_costs_minor_grouping * inc2_discounts_credits_rebates)
        metrics_dict[tm_runid, metric_id,'intermediate',key,'auto_toll_costs_{}_2000$'.format(minor_grouping_corridor),year] = DA_incremental_toll_costs_minor_grouping
        metrics_dict[tm_runid, metric_id,'intermediate',key,'auto_toll_costs_{}_inc1_2000$'.format(minor_grouping_corridor),year] = DA_incremental_toll_costs_inc1_minor_grouping
        metrics_dict[tm_runid, metric_id,'intermediate',key,'auto_toll_costs_{}_inc2_2000$'.format(minor_grouping_corridor),year] = DA_incremental_toll_costs_inc2_minor_grouping
        metrics_dict[tm_runid, metric_id,'intermediate',key,'truck_toll_costs_{}_2000$'.format(minor_grouping_corridor),year] = LRG_incremental_toll_costs_minor_grouping
        metrics_dict[tm_runid, metric_id,'intermediate',key,'hov_toll_costs_{}_2000$'.format(minor_grouping_corridor),year] = S3_incremental_toll_costs_minor_grouping

        if (DA_incremental_toll_costs_minor_grouping == 0):
            priv_auto_ratio_time_savings_to_toll_costs_minor_grouping = 0
            priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc1 = 0
            priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc2 = 0
            comm_veh_ratio_time_savings_to_toll_costs_minor_grouping = 0
            hov_ratio_time_savings_to_toll_costs_minor_grouping = 0
        else:
            # calculate ratios for overall + inc groups and enter into metrics dict 
            priv_auto_ratio_time_savings_to_toll_costs_minor_grouping = priv_auto_travel_time_savings_minor_grouping/DA_incremental_toll_costs_minor_grouping
            priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc1 = priv_auto_travel_time_savings_minor_grouping/DA_incremental_toll_costs_inc1_minor_grouping
            priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc2 = priv_auto_travel_time_savings_minor_grouping/DA_incremental_toll_costs_inc2_minor_grouping

            comm_veh_ratio_time_savings_to_toll_costs_minor_grouping = (time_savings_in_hours * commercial_vehicle_vot)/LRG_incremental_toll_costs_minor_grouping
            hov_ratio_time_savings_to_toll_costs_minor_grouping = priv_auto_travel_time_savings_minor_grouping/S3_incremental_toll_costs_minor_grouping

        if S3_incremental_toll_costs_minor_grouping == 0: #make the ratio 0 if there is no cost to drive
            hov_ratio_time_savings_to_toll_costs_minor_grouping = 0
 

        metrics_dict[tm_runid, metric_id,'final',key,'ratio_auto_time_savings_to_toll_costs_{}'.format(minor_grouping_corridor),year] = priv_auto_ratio_time_savings_to_toll_costs_minor_grouping
        metrics_dict[tm_runid, metric_id,'final',key,'ratio_auto_time_savings_to_toll_costs_{}_inc1'.format(minor_grouping_corridor),year] = priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc1
        metrics_dict[tm_runid, metric_id,'final',key,'ratio_auto_time_savings_to_toll_costs_{}_inc2'.format(minor_grouping_corridor),year] = priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc2

        # ----sum up the ratio of tolls and time savings across the corridors for weighted average

        # ----calculate average vmt, multiply time savings by it?

        sum_of_weighted_ratio_auto_time_savings_to_toll_costs = sum_of_weighted_ratio_auto_time_savings_to_toll_costs + priv_auto_ratio_time_savings_to_toll_costs_minor_grouping * minor_grouping_vmt
        sum_of_weighted_ratio_truck_time_savings_to_toll_costs = sum_of_weighted_ratio_truck_time_savings_to_toll_costs + comm_veh_ratio_time_savings_to_toll_costs_minor_grouping * minor_grouping_vmt
        sum_of_weighted_ratio_hov_time_savings_to_toll_costs = sum_of_weighted_ratio_hov_time_savings_to_toll_costs + hov_ratio_time_savings_to_toll_costs_minor_grouping * minor_grouping_vmt
        sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc1 = sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc1 + priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc1 * minor_grouping_vmt
        sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc2 = sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc2 + priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc2 * minor_grouping_vmt
        
        sum_of_ratio_auto_time_savings_to_toll_costs += priv_auto_ratio_time_savings_to_toll_costs_minor_grouping
        sum_of_ratio_auto_time_savings_to_toll_costs_inc1 += priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc1
        sum_of_ratio_auto_time_savings_to_toll_costs_inc2 += priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc2
        sum_of_ratio_truck_time_savings_to_toll_costs += comm_veh_ratio_time_savings_to_toll_costs_minor_grouping
        sum_of_ratio_hov_time_savings_to_toll_costs += hov_ratio_time_savings_to_toll_costs_minor_grouping

        #----sum of weights (vmt of corridor) to be used for weighted average
        sum_of_weights = sum_of_weights + minor_grouping_vmt
        # for corrdior simple average calc
        n = n+1

    # ----commented out to clear clutter. use for debugging
    # metrics_dict[tm_runid, metric_id,'intermediate','Private Auto','sum_of_ratio_auto_time_savings_to_toll_costs_weighted_by_vmt',year] = sum_of_weighted_ratio_auto_time_savings_to_toll_costs
    # metrics_dict[tm_runid, metric_id,'intermediate','Private Auto','sum_of_ratio_auto_time_savings_to_toll_costs_inc1_weighted_by_vmt',year] = sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc1
    # metrics_dict[tm_runid, metric_id,'intermediate','Private Auto','sum_of_ratio_auto_time_savings_to_toll_costs_inc2_weighted_by_vmt',year] = sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc2
    # metrics_dict[tm_runid, metric_id,'intermediate','Commercial Vehicle','sum_of_ratio_truck_time_savings_to_toll_costs_weighted_by_vmt',year] = sum_of_weighted_ratio_truck_time_savings_to_toll_costs
    # metrics_dict[tm_runid, metric_id,'intermediate','High Occupancy Vehicle','sum_of_ratio_hov_time_savings_to_toll_costs_weighted_by_vmt',year] = sum_of_weighted_ratio_hov_time_savings_to_toll_costs


    metrics_dict[tm_runid, metric_id,'final','Private Auto: All Households','average_ratio_auto_time_savings_to_toll_costs_across_corridors_weighted_by_vmt',year] = sum_of_weighted_ratio_auto_time_savings_to_toll_costs/sum_of_weights
    metrics_dict[tm_runid, metric_id,'final','Private Auto: Very Low Income Households','average_ratio_auto_time_savings_to_toll_costs_across_corridors_inc1_weighted_by_vmt',year] = sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc1/sum_of_weights
    metrics_dict[tm_runid, metric_id,'final','Private Auto: Very Low Income Households','average_ratio_auto_time_savings_to_toll_costs_across_corridors_inc2_weighted_by_vmt',year] = sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc2/sum_of_weights
    metrics_dict[tm_runid, metric_id,'final','Commercial Vehicle','average_ratio_truck_time_savings_to_toll_costs_across_corridors_weighted_by_vmt',year] = sum_of_weighted_ratio_truck_time_savings_to_toll_costs/sum_of_weights
    metrics_dict[tm_runid, metric_id,'final','High Occupancy Vehicle','average_ratio_hov_time_savings_to_toll_costs_across_corridors_weighted_by_vmt',year] = sum_of_weighted_ratio_hov_time_savings_to_toll_costs/sum_of_weights

    metrics_dict[tm_runid, metric_id,'final','Private Auto: All Households','simple_average_ratio_auto_time_savings_to_toll_costs_across_corridors',year] = sum_of_ratio_auto_time_savings_to_toll_costs/n
    metrics_dict[tm_runid, metric_id,'final','Private Auto: Very Low Income Households','simple_average_ratio_auto_time_savings_to_toll_costs_across_corridors_inc1',year] = sum_of_ratio_auto_time_savings_to_toll_costs_inc1/n
    metrics_dict[tm_runid, metric_id,'final','Private Auto: Very Low Income Households','simple_average_ratio_auto_time_savings_to_toll_costs_across_corridors_inc2',year] = sum_of_ratio_auto_time_savings_to_toll_costs_inc2/n
    metrics_dict[tm_runid, metric_id,'final','Commercial Vehicle','simple_average_ratio_truck_time_savings_to_toll_costs_across_corridors',year] = sum_of_ratio_truck_time_savings_to_toll_costs/n
    metrics_dict[tm_runid, metric_id,'final','High Occupancy Vehicle','simple_average_ratio_hov_time_savings_to_toll_costs_across_corridors',year] = sum_of_ratio_hov_time_savings_to_toll_costs/n


def calculate_Efficient1_ratio_travel_time(tm_runid, year, tm_od_tt_with_cities_df, metrics_dict):
    # 3) Ratio of travel time by transit vs. auto between  representative origin-destination pairs
    
    metric_id = 'Efficient 1'
    
    #     filter for timeperiod: AM Peak
    od_tt_am_with_cities_df = tm_od_tt_with_cities_df.loc[(tm_od_tt_with_cities_df['timeperiod_label'].str.contains("AM Peak") == True)]
    # filter for transit trips
    od_tt_am_with_cities_transit_df = od_tt_am_with_cities_df.loc[(od_tt_am_with_cities_df['trip_mode'] == 9)|(od_tt_am_with_cities_df['trip_mode'] == 10)|(od_tt_am_with_cities_df['trip_mode'] == 11)|(od_tt_am_with_cities_df['trip_mode'] == 12)|(od_tt_am_with_cities_df['trip_mode'] == 13)|(od_tt_am_with_cities_df['trip_mode'] == 14)|(od_tt_am_with_cities_df['trip_mode'] == 15)|(od_tt_am_with_cities_df['trip_mode'] == 16)|(od_tt_am_with_cities_df['trip_mode'] == 17)|(od_tt_am_with_cities_df['trip_mode'] == 18)]
    # filter for auto trips (da, s2, s3, taxi, tnc)
    od_tt_am_with_cities_auto_df = od_tt_am_with_cities_df.loc[(od_tt_am_with_cities_df['trip_mode'] == 1)|(od_tt_am_with_cities_df['trip_mode'] == 2)|(od_tt_am_with_cities_df['trip_mode'] == 3)|(od_tt_am_with_cities_df['trip_mode'] == 4)|(od_tt_am_with_cities_df['trip_mode'] == 5)|(od_tt_am_with_cities_df['trip_mode'] == 6)|(od_tt_am_with_cities_df['trip_mode'] == 19)|(od_tt_am_with_cities_df['trip_mode'] == 20)|(od_tt_am_with_cities_df['trip_mode'] == 21)]

    #  calcuate average across OD pairs
    n = 0 #counter to serve as denominator 
    sum_of_ratios = 0 #sum for numerator
    #     iterate through origin destination pairs and calculate metrics: average transit travel time, average auto travel time, ratio of the two
    #     input metrics into table
    for od in OD_pairs:
        avg_tt_transit_ORIG_DEST = od_tt_am_with_cities_transit_df.loc[(od_tt_am_with_cities_transit_df['CITY'].str.contains(od[0]) == True)].loc[(od_tt_am_with_cities_transit_df['CITY_dest'].str.contains(od[1]) == True), 'avg_travel_time_in_mins'].mean()
        avg_tt_auto_ORIG_DEST = od_tt_am_with_cities_auto_df.loc[(od_tt_am_with_cities_auto_df['CITY'].str.contains(od[0]) == True)].loc[(od_tt_am_with_cities_auto_df['CITY_dest'].str.contains(od[1]) == True), 'avg_travel_time_in_mins'].mean()
        metrics_dict[tm_runid, metric_id,'extra','{}_{}'.format(od[0],od[1]),'travel_time_transit_{}_{}'.format(od[0],od[1]),year]      = avg_tt_transit_ORIG_DEST
        metrics_dict[tm_runid, metric_id,'extra','{}_{}'.format(od[0],od[1]),'travel_time__auto_{}_{}'.format(od[0],od[1]),year]      = avg_tt_auto_ORIG_DEST
        transit_auto_ratio = avg_tt_transit_ORIG_DEST/avg_tt_auto_ORIG_DEST
        if math.isnan(transit_auto_ratio) ==True:
            transit_auto_ratio = 0
        metrics_dict[tm_runid, metric_id,'intermediate','{}_{}'.format(od[0],od[1]),'ratio_travel_time_transit_auto_{}_{}'.format(od[0],od[1]),year]      = transit_auto_ratio
        n = n+1
        sum_of_ratios = sum_of_ratios + transit_auto_ratio
    # add average across od pairs to metric dict
    metrics_dict[tm_runid, metric_id,'final','Average across 10 O-D pairs','ratio_travel_time_transit_auto_across_pairs',year]      = sum_of_ratios/n




def calculate_Efficient2_commute_mode_share(tm_runid, year, tm_commute_df, metrics_dict):    
    # 4) Transit, walk and bike mode share of commute trips during peak hours
    
    # borrow from prep_for_telecommute_excel.R
    # location \Box\Horizon and Plan Bay Area 2050\Equity and Performance\7_Analysis\Metrics\Metrics Development\Connected\prep_for_telecommute_excel.R
    metric_id = 'Efficient 2'
    # calculate auto and transit commute trips (similar to PBA2050 [\metrics development\diverse] Healthy: commute mode share)
    # simplify modes
    peak_commute_df = tm_commute_df.copy().loc[(tm_commute_df['timeCodeHwNum'] == 2)|(tm_commute_df['timeCodeHwNum'] == 4)]
    total_peak_trips = peak_commute_df.copy().loc[:,'freq'].sum()
    peak_commute_df.loc[(peak_commute_df['tour_mode'] == 1)|(peak_commute_df['tour_mode'] == 2),'mode'] = 'sov'
    peak_commute_df.loc[(peak_commute_df['tour_mode'] == 3)|(peak_commute_df['tour_mode'] == 4)|(peak_commute_df['tour_mode'] == 5)|(peak_commute_df['tour_mode'] == 6),'mode'] = 'hov'
    peak_commute_df.loc[(peak_commute_df['tour_mode'] == 20)|(peak_commute_df['tour_mode'] == 21),'mode'] = 'tnc'
    peak_commute_df.loc[(peak_commute_df['tour_mode'] == 19),'mode'] = 'taxi'
    peak_commute_df.loc[(peak_commute_df['tour_mode'] == 9)|(peak_commute_df['tour_mode'] == 10)|(peak_commute_df['tour_mode'] == 11)|(peak_commute_df['tour_mode'] == 12)|(peak_commute_df['tour_mode'] == 13)|(peak_commute_df['tour_mode'] == 14)|(peak_commute_df['tour_mode'] == 15)|(peak_commute_df['tour_mode'] == 16)|(peak_commute_df['tour_mode'] == 17)|(peak_commute_df['tour_mode'] == 18),'mode'] = 'transit'
    peak_commute_df.loc[(peak_commute_df['tour_mode'] == 7),'mode'] = 'walk'
    peak_commute_df.loc[(peak_commute_df['tour_mode'] == 8),'mode'] = 'bike'

    peak_commute_summed = peak_commute_df.copy().groupby('mode').agg('sum')
    for type_of_mode in ['sov', 'hov', 'tnc', 'taxi', 'transit', 'walk', 'bike']:
        metrics_dict[tm_runid, metric_id,'final','{} Mode Share'.format(type_of_mode),'{}_peak_hour_commute_trips' .format(type_of_mode), year] = peak_commute_summed.loc['{}'.format(type_of_mode), 'freq']
        metrics_dict[tm_runid, metric_id,'intermediate','{} Mode Share'.format(type_of_mode),'{}_peak_hour_mode_share_of_commute_trips'.format(type_of_mode), year] = peak_commute_summed.loc['{}'.format(type_of_mode), 'freq']/total_peak_trips

    metrics_dict[tm_runid, metric_id,'final','Daily Total Commute Trips During Peak Hours', 'Daily_total_peak_hour_commute_trips', year] = total_peak_trips


def sum_grouping(network_df,period): #sum congested time across selected toll class groupings
    return network_df['ctim'+period].sum()



def calculate_travel_time_and_return_weighted_sum_across_corridors(tm_runid, year, tm_loaded_network_df, metrics_dict):
  # Keeping essential columns of loaded highway network: node A and B, distance, free flow time, congested time
  metric_id = 'Reliable 1'

  tm_ab_ctim_df = tm_loaded_network_df.copy().loc[(tm_loaded_network_df['USEAM'] == 1)]
  tm_ab_ctim_df = tm_ab_ctim_df.copy()[['Grouping minor_AMPM','a_b','ctimAM','ctimPM', 'distance','volEA_tot', 'volAM_tot', 'volMD_tot', 'volPM_tot', 'volEV_tot']]  

  # create df for parallel arterials  
  tm_parallel_arterials_df = tm_ab_ctim_df.copy().merge(parallel_arterials_links, on='a_b', how='left')
  
  #  calcuate average across corridors
  sum_of_weights = 0 #sum of weights (vmt of corridor) to be used for weighted average 
  total_weighted_travel_time = 0 #sum for numerator
  n = 0 #counter for simple average 
  total_travel_time = 0 #numerator for simple average 

  # for parallel arterials
  sum_of_weights_parallel_arterial = 0 #sum of weights (vmt of corridor) to be used for weighted average 
  total_weighted_travel_time_parallel_arterial = 0 #sum for numerator
  total_travel_time_parallel_arterial = 0 #numerator for simple average 

  for i in minor_groups:
    #     add minor ampm ctim to metric dict
    minor_group_am_df = tm_ab_ctim_df.copy().loc[tm_ab_ctim_df['Grouping minor_AMPM'] == i+'_AM']
    minor_group_pm_df = tm_ab_ctim_df.copy().loc[tm_ab_ctim_df['Grouping minor_AMPM'] == i+'_PM']
    minor_group_am = sum_grouping(minor_group_am_df,'AM')
    minor_group_pm = sum_grouping(minor_group_pm_df,'PM')

    # add in extra metric for length of grouping
    length_of_grouping = (minor_group_am_df['distance']).sum()
    metrics_dict[tm_runid,metric_id,'extra',i,'%s' % i + '_AM_length',year] = length_of_grouping
    length_of_grouping = (minor_group_pm_df['distance']).sum()
    metrics_dict[tm_runid,metric_id,'extra',i,'%s' % i + '_PM_length',year] = length_of_grouping


    # for parallel arterials
    minor_group_am_parallel_arterial_df = tm_parallel_arterials_df.copy().loc[(tm_parallel_arterials_df['Parallel_Corridor'].str.contains(i+'_AM') == True)]
    minor_group_pm_parallel_arterial_df = tm_parallel_arterials_df.copy().loc[(tm_parallel_arterials_df['Parallel_Corridor'].str.contains(i+'_PM') == True)]
    minor_group_am_parallel_arterial = sum_grouping(minor_group_am_parallel_arterial_df,'AM')
    minor_group_pm_parallel_arterial = sum_grouping(minor_group_pm_parallel_arterial_df,'PM')

    # add in extra metric for length of grouping (parallel arterials)
    length_of_grouping = (minor_group_am_parallel_arterial_df['distance']).sum()
    metrics_dict[tm_runid,metric_id,'extra',i,'%s' % i + '_AM_parallel_arterial_length',year] = length_of_grouping
    length_of_grouping = (minor_group_pm_parallel_arterial_df['distance']).sum()
    metrics_dict[tm_runid,metric_id,'extra',i,'%s' % i + '_PM_parallel_arterial_length',year] = length_of_grouping
    
    # vmt to be used for weighted averages
    index_a_b = minor_group_am_df.copy()[['a_b']]
    network_for_vmt_df_AM = tm_loaded_network_df_base.copy().merge(index_a_b, on='a_b', how='right')
    index_a_b = minor_group_pm_df.copy()[['a_b']]
    network_for_vmt_df_PM = tm_loaded_network_df_base.copy().merge(index_a_b, on='a_b', how='right')
    vmt_minor_grouping_AM = network_for_vmt_df_AM['volAM_tot'].sum()
    vmt_minor_grouping_PM = network_for_vmt_df_PM['volPM_tot'].sum()
    # will use avg vmt for simplicity
    am_pm_avg_vmt = numpy.mean([vmt_minor_grouping_AM,vmt_minor_grouping_PM])

    # [for parallel arterials] vmt to be used for weighted averages
    index_a_b = minor_group_am_parallel_arterial_df.copy()[['a_b']]
    network_for_vmt_df_AM_parallel_arterial = tm_loaded_network_df_base.copy().merge(index_a_b, on='a_b', how='right')
    index_a_b = minor_group_am_parallel_arterial_df.copy()[['a_b']]
    network_for_vmt_df_PM_parallel_arterial = tm_loaded_network_df_base.copy().merge(index_a_b, on='a_b', how='right')
    vmt_minor_grouping_AM_parallel_arterial = network_for_vmt_df_AM_parallel_arterial['volAM_tot'].sum()
    vmt_minor_grouping_PM_parallel_arterial = network_for_vmt_df_PM_parallel_arterial['volPM_tot'].sum()
    # will use avg vmt for simplicity
    am_pm_avg_vmt_parallel_arterial = numpy.mean([vmt_minor_grouping_AM_parallel_arterial,vmt_minor_grouping_PM_parallel_arterial])

    # __commented out to reduce clutter - not insightful - can reveal for debugging
    # metrics_dict[tm_runid,metric_id,'intermediate',i,'%s' % i + '_AM_vmt',year] = vmt_minor_grouping_AM
    # metrics_dict[tm_runid,metric_id,'intermediate',i,'%s' % i + '_PM_vmt',year] = vmt_minor_grouping_PM

    # add travel times to metric dict
    metrics_dict[tm_runid,metric_id,'extra',i,'Freeway_travel_time_%s' % i + '_AM',year] = minor_group_am
    metrics_dict[tm_runid,metric_id,'extra',i,'Freeway_travel_time_%s' % i + '_PM',year] = minor_group_pm
    # weighted AM,PM travel times (by vmt)
    weighted_AM_travel_time_by_vmt = minor_group_am * am_pm_avg_vmt
    weighted_PM_travel_time_by_vmt = minor_group_pm * am_pm_avg_vmt

     # [for parallel arterials] add travel times to metric dict
    metrics_dict[tm_runid,metric_id,'extra',i,'Parallel_Arterial_travel_time_%s' % i + '_AM',year] = minor_group_am_parallel_arterial
    metrics_dict[tm_runid,metric_id,'extra',i,'Parallel_Arterial_travel_time_%s' % i + '_PM',year] = minor_group_pm_parallel_arterial
    # [for parallel arterials] weighted AM,PM travel times (by vmt)
    weighted_AM_travel_time_by_vmt_parallel_arterial = minor_group_am_parallel_arterial * am_pm_avg_vmt_parallel_arterial
    weighted_PM_travel_time_by_vmt_parallel_arterial = minor_group_pm_parallel_arterial * am_pm_avg_vmt_parallel_arterial

    # __commented out to reduce clutter - not insightful - can reveal for debugging
    # metrics_dict[tm_runid,metric_id,'intermediate',i,'travel_time_%s' % i + '_AM_weighted_by_vmt',year] = weighted_AM_travel_time_by_vmt
    # metrics_dict[tm_runid,metric_id,'intermediate',i,'travel_time_%s' % i + '_PM_weighted_by_vmt',year] = weighted_PM_travel_time_by_vmt

    #     add average ctim for each minor grouping to metric dict
    avgtime = numpy.mean([minor_group_am,minor_group_pm])
    metrics_dict[tm_runid,metric_id,'intermediate',i,'Freeway_avg_travel_time_%s' % i,year] = avgtime
    avgtime_weighted_by_vmt = numpy.mean([weighted_AM_travel_time_by_vmt,weighted_PM_travel_time_by_vmt])

    # [for parallel arterials] add average ctim for each minor grouping to metric dict
    avgtime_parallel_arterial = numpy.mean([minor_group_am_parallel_arterial,minor_group_pm_parallel_arterial])
    metrics_dict[tm_runid,metric_id,'intermediate',i,'Parallel_Arterial_avg_travel_time_%s' % i,year] = avgtime_parallel_arterial
    avgtime_weighted_by_vmt_parallel_arterial = numpy.mean([weighted_AM_travel_time_by_vmt_parallel_arterial,weighted_PM_travel_time_by_vmt_parallel_arterial])

    # __commented out to reduce clutter - not insightful - can reveal for debugging
    # metrics_dict[tm_runid,metric_id,'final',i,'avg_travel_time_%s_weighted_by_vmt' % i,year] = avgtime_weighted_by_vmt
    
    # for corrdior average calc
    sum_of_weights = sum_of_weights + am_pm_avg_vmt
    total_weighted_travel_time = total_weighted_travel_time + (avgtime_weighted_by_vmt)
    n += 1
    total_travel_time += avgtime

    # [for parallel arterials]
    sum_of_weights_parallel_arterial += am_pm_avg_vmt_parallel_arterial
    total_weighted_travel_time_parallel_arterial += avgtime_weighted_by_vmt_parallel_arterial
    total_travel_time_parallel_arterial += avgtime_parallel_arterial

  return [sum_of_weights, total_weighted_travel_time, n, total_travel_time, sum_of_weights_parallel_arterial, total_weighted_travel_time_parallel_arterial, total_travel_time_parallel_arterial]



def calculate_Reliable1_change_travel_time(tm_runid, year, tm_loaded_network_df, metrics_dict):    
    # 5) Change in peak hour travel time on key freeway corridors and parallel arterials

    # borrowed from pba metrics calculate_Connected2_hwy_traveltimes()
    metric_id = 'Reliable 1'

    # calculate travel times on each cprridor for both runs
    this_run_metric = calculate_travel_time_and_return_weighted_sum_across_corridors(tm_runid, year, tm_loaded_network_df, metrics_dict)
    base_run_metric = calculate_travel_time_and_return_weighted_sum_across_corridors(tm_runid_base, year, tm_loaded_network_df_base, metrics_dict)
    # find the change in thravel time for each corridor
    calculate_change_between_run_and_base(tm_runid, tm_runid_base, year, 'Reliable 1', metrics_dict)

    change_in_travel_time_weighted = this_run_metric[1] - base_run_metric[1]
    change_in_parallel_arterial_travel_time_weighted = this_run_metric[5] - base_run_metric[5]

    sum_of_weights = this_run_metric[0]
    sum_of_weights_parallel_arterial = this_run_metric[4]

    total_travel_time = this_run_metric[3] - base_run_metric[3]
    total_travel_time_parallel_arterial = this_run_metric[6] - base_run_metric[6]

    n = this_run_metric[2]

    # add average across corridors to metric dict
    metrics_dict[tm_runid, metric_id,'final','Freeways','Fwy_avg_peak_hour_travel_time_across_key_corridors_weighted_by_vmt',year]      = change_in_travel_time_weighted/sum_of_weights
    metrics_dict[tm_runid, metric_id,'final','Freeways','Fwy_simple_avg_peak_hour_travel_time_across_key_corridors',year]      = total_travel_time/n
    # parallel arterials
    metrics_dict[tm_runid, metric_id,'final','Parallel Arterials','Parallel_Arterial_avg_peak_hour_travel_time_across_key_corridors_weighted_by_vmt',year]      = change_in_parallel_arterial_travel_time_weighted/sum_of_weights_parallel_arterial
    metrics_dict[tm_runid, metric_id,'final','Parallel Arterials','Parallel_Arterial_simple_avg_peak_hour_travel_time_across_key_corridors',year]      = total_travel_time_parallel_arterial/n
    



def calculate_Reliable2_ratio_peak_nonpeak(tm_runid, year, tm_od_travel_times_df, metrics_dict):    
    # 6) Ratio of travel time during peak hours vs. non-peak hours between representative origin-destination pairs 

    metric_id = 'Reliable2'

    tm_od_travel_times_df = tm_od_travel_times_df.copy().loc[(tm_od_travel_times_df['trip_mode'] == 1)|(tm_od_travel_times_df['trip_mode'] == 2)|(tm_od_travel_times_df['trip_mode'] == 3)|(tm_od_travel_times_df['trip_mode'] == 4)|(tm_od_travel_times_df['trip_mode'] == 5)|(tm_od_travel_times_df['trip_mode'] == 6)|(tm_od_travel_times_df['trip_mode'] == 19)|(tm_od_travel_times_df['trip_mode'] == 20)|(tm_od_travel_times_df['trip_mode'] == 21)]
    tm_od_travel_times_df = tm_od_travel_times_df.loc[(tm_od_travel_times_df['avg_travel_time_in_mins'] > 0)]

    od_tt_peak_df = tm_od_travel_times_df.loc[(tm_od_travel_times_df['timeperiod_label'].str.contains("AM Peak") == True)|(tm_od_travel_times_df['timeperiod_label'].str.contains("PM Peak") == True)]
    od_tt_nonpeak_df = tm_od_travel_times_df.loc[(tm_od_travel_times_df['timeperiod_label'].str.contains("Midday") == True)]

     #  calcuate average across corridors
    n = 0 #counter to serve as denominator 
    total_travel_time = 0 #sum for numerator


    #     iterate through Origin Destination pairs, calculate metrics: average peak travel time, average nonpeak travel time, ratio of the two
    #     enter metrics into dictionary
    for od in OD_pairs:
        avg_tt_peak_ORIG_DEST = od_tt_peak_df.loc[(od_tt_peak_df['CITY'].str.contains(od[0]) == True)].loc[(od_tt_peak_df['CITY_dest'].str.contains(od[1]) == True), 'avg_travel_time_in_mins'].mean()
        avg_tt_nonpeak_ORIG_DEST = od_tt_nonpeak_df.loc[(od_tt_nonpeak_df['CITY'].str.contains(od[0]) == True)].loc[(od_tt_nonpeak_df['CITY_dest'].str.contains(od[1]) == True), 'avg_travel_time_in_mins'].mean()
        metrics_dict[tm_runid,metric_id,'extra','{}_{}'.format(od[0],od[1]),'avg_travel_time_peak_{}_{}'.format(od[0],od[1]),year]      = avg_tt_peak_ORIG_DEST
        metrics_dict[tm_runid,metric_id,'extra','{}_{}'.format(od[0],od[1]),'avg_travel_time__nonpeak_{}_{}'.format(od[0],od[1]),year]      = avg_tt_nonpeak_ORIG_DEST
        metrics_dict[tm_runid,metric_id,'intermediate','{}_{}'.format(od[0],od[1]),'ratio_avg_travel_time_peak_nonpeak_{}_{}'.format(od[0],od[1]),year]      = avg_tt_peak_ORIG_DEST/avg_tt_nonpeak_ORIG_DEST
        # for od average calc
        n = n+1
        total_travel_time = total_travel_time + (avg_tt_peak_ORIG_DEST/avg_tt_nonpeak_ORIG_DEST)

    # add average across corridors to metric dict
    metrics_dict[tm_runid, metric_id,'final','Average across 10 O-D pairs','ratio_travel_time_peak_nonpeak_across_pairs',year]      = total_travel_time/n




def calculate_Reparative1_dollar_revenues_revinvested(tm_runid, year, tm_scen_metrics_df, tm_auto_owned_df, tm_travel_cost_df, metrics_dict):
    # 7) Absolute dollar amount of new revenues generated that is reinvested in freeway adjacent communities

    # off model?
    metric_id = 'Reparative 1'



def calculate_Reparative2_ratio_revenues_revinvested(tm_runid, year, tm_scen_metrics_df, tm_auto_owned_df, tm_travel_cost_df, metrics_dict):
    # 8) Ratio of new revenues paid for by low-income populations to revenues reinvested toward low-income populations

    # off model?
    metric_id = 'Reparative 2'



def adjust_fatalities_exp_speed(row, type_of_fatality):    
    # adjust fatalities based on exponents and speed. 
    # if fatalities/injuries are higher because speeds are higher in run than NP, use pmin function to replace with originally calculated FBP fatalities/injuries before VZ adjustment (do not let fatalities/injuries increase due to VZ adjustment calculation)
    N_type_fatalities = row[type_of_fatality]
    if N_type_fatalities==0 :
        return 0
    else:
        return numpy.minimum(N_type_fatalities*(row['Avg_speed']/row['Avg_reduced_speed'])**row['fatality_exponent'], N_type_fatalities)



def calculate_fatalitites(run_id, loaded_network_df, collision_rates_df, tm_loaded_network_df_base):
    NOTE_ON_FT_AND_AT = """
    FT is reclassified to -1 because the link is a dummy link (FT=6) and/or because lanes <=0. 
    FT is reclassified to -1 so that the join with fatality and injury rates doesn't match with anything
    and those links don't have any fatalities or injuries, so they are effectively filtered out.
    there is a travel model script to estimate fatalities in R
    https://github.com/BayAreaMetro/travel-model-one/blob/12962d73a5842b71b2439016e65d00b979af8f92/utilities/RTP/metrics/hwynet.py
    """
    modified_network_df = loaded_network_df.copy()
    modified_network_df['ft_collision'] = modified_network_df['ft']
    modified_network_df['at_collision'] = modified_network_df['at']
    modified_network_df.loc[modified_network_df['ft_collision'] == 1,'ft_collision'] = 2
    modified_network_df.loc[modified_network_df['ft_collision'] == 8,'ft_collision'] = 2
    modified_network_df.loc[modified_network_df['ft_collision'] == 6,'ft_collision'] = -1 #ignore ft 6 (dummy links) and lanes <= 0 by replacing the ft with -1, which won't match with anything
    modified_network_df.loc[modified_network_df['lanes'] <= 0,'ft_collision'] = -1
    modified_network_df.loc[modified_network_df['ft_collision'] > 4,'ft_collision'] = 4
    modified_network_df.loc[modified_network_df['at_collision'] < 3,'at_collision'] = 3
    modified_network_df.loc[modified_network_df['at_collision'] > 4,'at_collision'] = 4
    # ____confirm this is ok with FMS team and Anup______
    # filter for desired ft and remove links where all speeds are 0 <-- not sure if this is an error in the network
    modified_network_df = modified_network_df.loc[modified_network_df['ft_collision'] != -1]
    modified_network_df = modified_network_df.loc[modified_network_df['cspdAM'] != 0]

    modified_network_df = modified_network_df.merge(collision_rates_df,how='left',left_on=['ft_collision','at_collision'],right_on=['ft','at'])
        
    # calculate fatalities and injuries as they would be calculated without the speed reduction
    modified_network_df['annual_VMT'] = N_days_per_year * (modified_network_df['volEA_tot'] + modified_network_df['volAM_tot'] + modified_network_df['volMD_tot'] + modified_network_df['volPM_tot'] + modified_network_df['volEV_tot']) * modified_network_df['distance']
    
    modified_network_df['Avg_speed'] = (modified_network_df['cspdEA'] + modified_network_df['cspdAM'] + modified_network_df['cspdMD'] + modified_network_df['cspdPM'] + modified_network_df['cspdEV']) / 5
    modified_network_df['N_motorist_fatalities'] = modified_network_df['annual_VMT'] / 1000000 * modified_network_df['Motor Vehicle Fatality']
    modified_network_df['N_ped_fatalities'] = modified_network_df['annual_VMT'] / 1000000 * modified_network_df['Walk Fatality']
    modified_network_df['N_bike_fatalities'] = modified_network_df['annual_VMT'] / 1000000 * modified_network_df['Bike Fatality']
    modified_network_df['N_total_fatalities'] = modified_network_df['N_motorist_fatalities'] + modified_network_df['N_ped_fatalities'] + modified_network_df['N_bike_fatalities']

    if ('2015' not in run_id)&('2035_TM152_NGF_NP07_TollCalibrated02' not in run_id):
        # join average speed on each link in no project
        # calculate average speed
        tm_loaded_network_df_base['Avg_reduced_speed'] = (tm_loaded_network_df_base['cspdEA'] + tm_loaded_network_df_base['cspdAM'] + tm_loaded_network_df_base['cspdMD'] + tm_loaded_network_df_base['cspdPM'] + tm_loaded_network_df_base['cspdEV']) / 5
        tm_loaded_network_df_base['a_b'] = tm_loaded_network_df_base['a'].astype(str) + "_" + tm_loaded_network_df_base['b'].astype(str)
        base_network_avg_speed_df = tm_loaded_network_df_base[['a_b', 'Avg_reduced_speed']]
        # merge DFs on 'a_b'
        modified_network_df = modified_network_df.merge(base_network_avg_speed_df, on='a_b', how='left')
        # add attributes for fatality reduction exponent based on ft
        # exponents and methodology sourced from here: https://www.toi.no/getfile.php?mmfileid=13206 (table S1)
        # methodology cited in this FHWA resource: https://www.fhwa.dot.gov/publications/research/safety/17098/003.cfm
        # modified_network_df['fatality_exponent'] = 0
        modified_network_df.loc[(modified_network_df['ft_collision'] == 1) | (modified_network_df['ft_collision'] == 2) | (modified_network_df['ft_collision'] == 3) | (modified_network_df['ft_collision'] == 5) | (modified_network_df['ft_collision'] == 6) | (modified_network_df['ft_collision'] == 8),'fatality_exponent'] = 4.6
        modified_network_df.loc[(modified_network_df['ft_collision'] == 4) | (modified_network_df['ft_collision'] == 7),'fatality_exponent'] = 3
    
        modified_network_df['N_motorist_fatalities_after'] = modified_network_df.apply(lambda row: adjust_fatalities_exp_speed(row,'N_motorist_fatalities'), axis = 1)
        modified_network_df['N_ped_fatalities_after'] = modified_network_df.apply(lambda row: adjust_fatalities_exp_speed(row,'N_ped_fatalities'), axis = 1)
        modified_network_df['N_bike_fatalities_after'] = modified_network_df.apply(lambda row: adjust_fatalities_exp_speed(row,'N_bike_fatalities'), axis = 1)
        modified_network_df['N_total_fatalities_after'] = modified_network_df['N_motorist_fatalities_after'] + modified_network_df['N_ped_fatalities_after'] + modified_network_df['N_bike_fatalities_after']
        modified_network_df['tm_run_id'] = tm_runid
        # sum the metrics
        return modified_network_df.groupby('tm_run_id').agg({'N_motorist_fatalities': ['sum'],'N_motorist_fatalities_after': ['sum'],'N_bike_fatalities': ['sum'],'N_bike_fatalities_after': ['sum'],'N_ped_fatalities': ['sum'],'N_ped_fatalities_after': ['sum'],'N_total_fatalities': ['sum'],'N_total_fatalities_after': ['sum']})
    else:
        modified_network_df['tm_run_id'] = tm_runid
        return modified_network_df.groupby('tm_run_id').agg({'N_motorist_fatalities': ['sum'],'N_bike_fatalities': ['sum'],'N_ped_fatalities': ['sum'],'N_total_fatalities': ['sum']})




def calculate_Safe1_fatalities_freewayss_nonfreeways(tm_runid, year, tm_loaded_network_df, metrics_dict):
    # 9) Annual number of estimated fatalities on freeways and non-freeway facilities

    # borrow from VZ_safety_calc_correction_v2.R
    # location \Box\Horizon and Plan Bay Area 2050\Equity and Performance\7_Analysis\Metrics\Metrics Development\Healthy\Fatalities Injuries
    
    NOTE_ON_CORRECTIONS = """
    the model does not do a great job with estimating fatalities. 
    the ratio of observed to calculated scales the modeled fatalities so that the modeled data matches observed data 
    (for example, if we know there were 400 fatalities in 2015 but the model says there were 200, the scaling factor would be x2. 
    that scaling factor should be kept in future years so that the magnitude is correct.
    the speed restrictions correction accounts for the fact that the likelihood of fatality or injury depends on the speed,
    but the model just calculates fatalities and injuries as a function of VMT and facility type (irrespective of speed). 
    we used research on the relationship between speed change and fatality rate to adjust fatalities and injuries down based on the PBA strategy to reduce speed limits on freeways and local streets.
    you should keep that adjustment if you change the speeds, consistent with PBA50.
    If you don't reduce speeds, don't keep the adjustment
    """
    metric_id = 'Safe 1'

    fatality_df = calculate_fatalitites(tm_runid, tm_loaded_network_df, collision_rates_df, tm_loaded_network_df_base)
    fatality_df_2015 = calculate_fatalitites(runid_2015, loaded_network_2015_df, collision_rates_df, tm_loaded_network_df_base)

    # ______calculate fatalities for freeway and non-freeway________
    fwy_network_df = tm_loaded_network_df.copy().loc[(tm_loaded_network_df['ft'] != 7)|(tm_loaded_network_df['ft'] != 4)|(tm_loaded_network_df['ft'] != 3)|(tm_loaded_network_df['ft'] != 6)]
    nonfwy_network_df = tm_loaded_network_df.copy().loc[(tm_loaded_network_df['ft'] == 7)|(tm_loaded_network_df['ft'] == 4)|(tm_loaded_network_df['ft'] == 3)]
    fwy_network_df_base = tm_loaded_network_df_base.copy().loc[(tm_loaded_network_df_base['ft'] != 7)|(tm_loaded_network_df_base['ft'] != 4)|(tm_loaded_network_df_base['ft'] != 3)|(tm_loaded_network_df_base['ft'] != 6)]
    nonfwy_network_df_base = tm_loaded_network_df_base.copy().loc[(tm_loaded_network_df_base['ft'] == 7)|(tm_loaded_network_df_base['ft'] == 4)|(tm_loaded_network_df_base['ft'] == 3)]
    fwy_fatality_df = calculate_fatalitites(tm_runid, fwy_network_df, collision_rates_df, fwy_network_df_base)
    nonfwy_fatality_df = calculate_fatalitites(tm_runid, nonfwy_network_df, collision_rates_df, nonfwy_network_df_base)
    
    # separate into variables for this run
    # output df has columns for each fatality type + 'after' which indicates that a correction was made for speed reductions in the scenario run

    # check for base run
    if '2035_TM152_NGF_NP07_TollCalibrated02' in tm_runid:
        N_motorist_fatalities_after = fatality_df[('N_motorist_fatalities','sum')][0]
        N_ped_fatalities_after = fatality_df[('N_ped_fatalities','sum')][0]
        N_bike_fatalities_after = fatality_df[('N_bike_fatalities','sum')][0]
        # calculate and enter FWY AND NONFWY into metrics dict
        N_fwy_motorist_fatalities_after = fwy_fatality_df[('N_motorist_fatalities','sum')][0]
        N_nonfwy_motorist_fatalities_after = nonfwy_fatality_df[('N_motorist_fatalities','sum')][0]
    else:

        # N_motorist_fatalities = fatality_df[('N_motorist_fatalities','sum')][0]
        N_motorist_fatalities_after = fatality_df[('N_motorist_fatalities_after','sum')][0]
        # N_ped_fatalities = fatality_df[('N_ped_fatalities','sum')][0]
        N_ped_fatalities_after = fatality_df[('N_ped_fatalities_after','sum')][0]
        # N_bike_fatalities = fatality_df[('N_bike_fatalities','sum')][0]
        N_bike_fatalities_after = fatality_df[('N_bike_fatalities_after','sum')][0]
        # N_total_fatalities = fatality_df[('N_total_fatalities','sum')][0]
        # N_total_fatalities_after = fatality_df[('N_total_fatalities_after','sum')][0]

        # calculate and enter FWY AND NONFWY into metrics dict
        N_fwy_motorist_fatalities_after = fwy_fatality_df[('N_motorist_fatalities_after','sum')][0]
        N_nonfwy_motorist_fatalities_after = nonfwy_fatality_df[('N_motorist_fatalities_after','sum')][0]

    # separate into variables for 2015 run
    N_motorist_fatalities_15 = fatality_df_2015[('N_motorist_fatalities','sum')][0]
    N_ped_fatalities_15 = fatality_df_2015[('N_ped_fatalities','sum')][0]
    N_bike_fatalities_15 = fatality_df_2015[('N_bike_fatalities','sum')][0]
    # N_total_fatalities_15 = fatality_df_2015[('N_total_fatalities','sum')][0]
    
    # calculate and enter into metrics dict
    N_motorist_fatalities_corrected = N_motorist_fatalities_after*(Obs_N_motorist_fatalities_15/N_motorist_fatalities_15)
    N_ped_fatalities_corrected = N_ped_fatalities_after*(Obs_N_ped_fatalities_15/N_ped_fatalities_15)
    N_bike_fatalities_corrected = N_bike_fatalities_after*(Obs_N_bike_fatalities_15/N_bike_fatalities_15)
    N_total_fatalities_corrected = N_motorist_fatalities_corrected + N_ped_fatalities_corrected + N_bike_fatalities_corrected
    
    metrics_dict[tm_runid,metric_id,'intermediate','Mode','annual_number_of_motorist_fatalities_corrected',year] = N_motorist_fatalities_corrected
    metrics_dict[tm_runid,metric_id,'intermediate','Mode','annual_number_of_pedestrian_fatalities_corrected',year] = N_ped_fatalities_corrected
    metrics_dict[tm_runid,metric_id,'intermediate','Mode','annual_number_of_bicycle_fatalities_corrected',year] = N_bike_fatalities_corrected
    metrics_dict[tm_runid,metric_id,'intermediate','Mode','annual_number_of_total_fatalities_corrected',year] = N_total_fatalities_corrected

    
    N_fwy_motorist_fatalities_corrected = N_fwy_motorist_fatalities_after*(Obs_N_motorist_fatalities_15/N_motorist_fatalities_15)
    metrics_dict[tm_runid,metric_id,'final','Freeway Facilities','annual_number_of_fwy_motorist_fatalities_corrected',year] = N_fwy_motorist_fatalities_corrected

    N_nonfwy_motorist_fatalities_corrected = N_nonfwy_motorist_fatalities_after*(Obs_N_motorist_fatalities_15/N_motorist_fatalities_15)
    metrics_dict[tm_runid,metric_id,'final','Non-Freeway Facilities','annual_number_of_nonfwy_motorist_fatalities_corrected',year] = N_nonfwy_motorist_fatalities_corrected




def calculate_Safe2_change_in_vmt(tm_runid, year, tm_loaded_network_df, metrics_dict):
    # 10) Change in vehicle miles travelled on freeway and adjacent non-freeway facilities

    # borrow from scenarioMetrics.py
    # https://github.com/BayAreaMetro/travel-model-one/blob/28188e99c0d20dd0efad45a17a6b74b36df9a95a/utilities/RTP/metrics/scenarioMetrics.py
    # follow same process, but filter by FT
    #     includes av - autanomous vehicles
    
    metric_id = 'Safe 2'

    fwy_vmt = 0
    nonfwy_vmt = 0

    #     filter for fwy and nonfwy facilities
    fwy_network_df = tm_loaded_network_df.copy().loc[(tm_loaded_network_df['ft'] != 7)|(tm_loaded_network_df['ft'] != 4)|(tm_loaded_network_df['ft'] != 3)|(tm_loaded_network_df['ft'] != 6)]
    nonfwy_network_df = tm_loaded_network_df.copy().loc[(tm_loaded_network_df['ft'] == 7)|(tm_loaded_network_df['ft'] == 4)|(tm_loaded_network_df['ft'] == 3)]

    for timeperiod in ['EA','AM','MD','PM','EV']:
        # vmt
        fwy_network_df['vmt%s_tot' % timeperiod] = fwy_network_df['vol%s_tot' % timeperiod]*fwy_network_df['distance']
        nonfwy_network_df['vmt%s_tot' % timeperiod] = nonfwy_network_df['vol%s_tot' % timeperiod]*nonfwy_network_df['distance']

       # total vmt for all timeperiods
        fwy_vmt += fwy_network_df['vmt%s_tot' % timeperiod].sum()
        nonfwy_vmt += nonfwy_network_df['vmt%s_tot' % timeperiod].sum()

    # return it

    metrics_dict[tm_runid, metric_id, 'final','Freeway Facilities','annual_fwy_vmt', year] = fwy_vmt * N_days_per_year
    metrics_dict[tm_runid, metric_id, 'final','Adjacent Non-Freeway Facilities','annual_nonfwy_vmt', year] = nonfwy_vmt * N_days_per_year




import datetime, os, sys
import numpy, pandas as pd
from collections import OrderedDict, defaultdict
from dbfread import DBF
import math
import csv
pd.options.mode.chained_assignment = None  # default='warn'

# add a line do load this list directly from ModelRuns.xlsx

# all current runs
# runs = ['2015_TM152_NGF_05',\
#   '2035_TM152_FBP_Plus_24',\
#   '2035_TM152_FBP_Plus_24_rerunTM1.5.2.5',\
#   '2035_TM152_NGF_NP07_Path1a_05_SimpleTolls01',\
#   '2035_TM152_NGF_NP07_Path1b_02_SimpleTolls01',\
#   '2035_TM152_NGF_NP07_Path1b_01_LowestTolls03',\
#   '2035_TM152_NGF_NP07_Path1b_01_HighestTolls02',\
#   '2035_TM152_NGF_NP07_Path1b_01_UniformTolls03',\
#   '2035_TM152_NGF_NP07_Path2b_wP1bStaticTolls_01',\
#   '2035_TM152_NGF_NP07_Path3a_04',\
#   '2035_TM152_NGF_NP07_Path3b_04',\
#   '2035_TM152_NGF_NP07_Path4_02']

# missing runs
runs = ['2035_TM152_FBP_Plus_24',  '2035_TM152_FBP_Plus_24_rerunTM1.5.2.5',  '2035_TM152_NGF_NP07_Path1a_05_SimpleTolls01',  '2035_TM152_NGF_NP07_Path1b_02_SimpleTolls01',  '2035_TM152_NGF_NP07_Path1b_01_LowestTolls03',  '2035_TM152_NGF_NP07_Path1b_01_HighestTolls02',  '2035_TM152_NGF_NP07_Path1b_01_UniformTolls03',  '2035_TM152_NGF_NP07_Path2b_wP1bStaticTolls_01',  '2035_TM152_NGF_NP07_Path3a_04',  '2035_TM152_NGF_NP07_Path3b_04',  '2035_TM152_NGF_NP07_Path4_02']

# ________Global Inputs_________

inflation_00_20 = 1.53
inflation_18_20 = 1.04
# Annual Auto ownership cost in 2018$
# Source: Consumer Expenditure Survey 2018 (see Box\Horizon and Plan Bay Area 2050\Equity and Performance\7_Analysis\Metrics\Affordable\auto_ownership_costs.xlsx)
# (includes depreciation, insurance, finance charges, license fees)
auto_ownership_cost      = 5945
auto_ownership_cost_inc1 = 2585
auto_ownership_cost_inc2 = 4224

# sourced from USDOT Benefit-Cost Analysis Guidance  in 2020 dollars
# chrome-extension://efaidnbmnnnibpcajpcglclefindmkaj/https://www.transportation.gov/sites/dot.gov/files/2022-03/Benefit%20Cost%20Analysis%20Guidance%202022%20Update%20%28Final%29.pdf
private_auto_vot = 17.8
commercial_vehicle_vot = 32

y1        = "2015"
y2        = "2035"
y_diff    = "2035"

# assumptions for fatalities
N_days_per_year = 300 # assume 300 days per year (outputs are for one day)
Obs_N_motorist_fatalities_15 = 301
Obs_N_ped_fatalities_15 = 127
Obs_N_bike_fatalities_15 = 27
Obs_N_motorist_injuries_15 = 1338
Obs_N_ped_injuries_15 = 379
Obs_N_bike_injuries_15 = 251
Obs_injuries_15 = 1968

# define transit modes
transit_modes = [9,10,11,12,13,14,15,16,17,18]
auto_modes = [1,2,3,4,5,6]

# define origin destination pairs
OD_pairs = [['OAKLAND','SAN FRANCISCO'],['VALLEJO','SAN FRANCISCO'],['ANTIOCH','SAN FRANCISCO'],['ANTIOCH','OAKLAND'],['SAN JOSE','SAN FRANCISCO'],['OAKLAND','PALO ALTO'],['OAKLAND','SAN JOSE'],['LIVERMORE','SAN JOSE'],['FAIRFIELD','DUBLIN'],['SANTA ROSA','SAN FRANCISCO']]
# load lookup file for a city's TAZs
taz_cities_df = pd.read_csv('C:\\Users\\jalatorre\\Box\\NextGen Freeways Study\\07 Tasks\\05_GoalsandMetrics\\Metrics\\Metrics Tableau Development 2022\\taz_with_cities.csv')

# load minor groupings, to be merged with loaded network
minor_links_df = pd.read_csv('C:\\Users\\jalatorre\\Box\\NextGen Freeways Study\\07 Tasks\\07_AnalysisRound1\\202302 Metrics Scripting\\Input Files\\a_b_with_minor_groupings.csv')

# list for iteration
minor_groups = minor_links_df['Grouping minor'].unique()[1:] #exclude 'other' and NaN
minor_groups = numpy.delete(minor_groups, 2)

# load lookup file for parallel arterial links
parallel_arterials_links = pd.read_csv('C:\\Users\\jalatorre\\Box\\NextGen Freeways Study\\07 Tasks\\07_AnalysisRound1\\202302 Metrics Scripting\\Input Files\\ParallelArterialLinks.csv')
parallel_arterials_links['a_b'] = parallel_arterials_links['A'].astype(str) + "_" + parallel_arterials_links['B'].astype(str)

# define base run inputs
# # base year run for comparisons (no project)
# ______load no project network to use for speed comparisons in vmt corrections______
tm_run_location_base = "L:\\Application\\Model_One\\NextGenFwys\\Scenarios\\2035_TM152_NGF_NP07_TollCalibrated02"
tm_runid_base = tm_run_location_base.split('\\')[-1]
# ______define the base run inputs for "change in" comparisons______
tm_scen_metrics_df_base = pd.read_csv(tm_run_location_base+'/OUTPUT/metrics/scenario_metrics.csv',names=["runid", "metric_name", "value"])
tm_auto_owned_df_base = pd.read_csv(tm_run_location_base+'/OUTPUT/metrics/autos_owned.csv')
tm_travel_cost_df_base = pd.read_csv(tm_run_location_base+'/OUTPUT/core_summaries/TravelCost.csv')
tm_auto_times_df_base = pd.read_csv(tm_run_location_base+'/OUTPUT/metrics/auto_times.csv',sep=",")#, index_col=[0,1])
tm_od_travel_times_df_base = pd.read_csv(tm_run_location_base+'/OUTPUT/core_summaries/ODTravelTime_byModeTimeperiod_reduced_file.csv')
tm_od_tt_with_cities_df_base = tm_od_travel_times_df_base.merge(taz_cities_df, left_on='orig_taz', right_on='taz1454', how='left', suffixes = ["",'_orig']).merge(taz_cities_df, left_on='dest_taz', right_on='taz1454', how='left', suffixes = ["",'_dest'])
tm_loaded_network_df_base = pd.read_csv(tm_run_location_base+'/OUTPUT/avgload5period.csv')
tm_loaded_network_df_base = tm_loaded_network_df_base.rename(columns=lambda x: x.strip())
# merging df that has the list of minor segments with loaded network - for corridor analysis
tm_loaded_network_df_base['a_b'] = tm_loaded_network_df_base['a'].astype(str) + "_" + tm_loaded_network_df_base['b'].astype(str)
network_links_dbf_base = pd.read_csv(tm_run_location_base + '\\OUTPUT\\shapefile\\network_links_reduced_file.csv')
tm_loaded_network_df_base = tm_loaded_network_df_base.copy().merge(network_links_dbf_base.copy(), on='a_b', how='left')
tm_loaded_network_df_base = tm_loaded_network_df_base.merge(minor_links_df, on='a_b', how='left')

# load vmt_vht_metrics.csv for vmt calc
tm_vmt_metrics_df_base = pd.read_csv(tm_run_location_base + '/OUTPUT/metrics/vmt_vht_metrics.csv', sep=",", index_col=[0,1])
# load transit_times_by_mode_income.csv
tm_transit_times_df_base = pd.read_csv(tm_run_location_base + '/OUTPUT/metrics/transit_times_by_mode_income.csv', sep=",", index_col=[0,1])
# load CommuteByIncomeHousehold.csv
tm_commute_df_base = pd.read_csv(tm_run_location_base+'/OUTPUT/core_summaries/CommuteByIncomeByTPHousehold.csv')
# load VehicleMilesTraveled_households.csv
vmt_hh_df_base = pd.read_csv(tm_run_location_base+'/OUTPUT/core_summaries/VehicleMilesTraveled_households.csv')

for run in runs:
  USAGE = """

    python ngfs_metrics.py

    Run this from the model run dir.
    Processes model outputs and creates a single csv with scenario metrics, called metrics\scenario_metrics.csv
    
    This file will have 3 columns:
      1) scenario ID
      2) metric description
      3) metric value
      
    Metrics are:
      1) Transportation costs as a share of household income
      2) Ratio of value of auto travel time savings to incremental toll costs
      3) Ratio of travel time by transit vs. auto between  representative origin-destination pairs
      4) Transit, walk and bike mode share of commute trips during peak hours
      5) Change in peak hour travel time on key freeway corridors and parallel arterials
      6) Ratio of travel time during peak hours vs. non-peak hours between representative origin-destination pairs 
      7) Absolute dollar amount of new revenues generated that is reinvested in freeway adjacent communities
      8) Ratio of new revenues paid for by low-income populations to revenues reinvested toward low-income populations
      9) Annual number of estimated fatalities on freeways and non-freeway facilities
      10) Change in vehicle miles travelled on freeway and adjacent non-freeway facilities

      """

  # ______run______
  # add the run name... use the current dir
  # tm_run_location = os.getcwd()
  # tm_runid = os.path.split(os.getcwd())[1]

  # #temporary run location for testing purposes
  tm_run_location = "L:\\Application\\Model_One\\NextGenFwys\\Scenarios\\" + run
  tm_runid = tm_run_location.split('\\')[-1]

  # metric dict input: year
  year = tm_runid[:4]
  # manually calculated sums for discounts, credits, and rebates
  # adjust later
  if ('1b' in tm_runid) | ('2b' in tm_runid) | ('3b' in tm_runid): #how to include discounts for persons with disabilities?
    inc1_discounts_credits_rebates = .5
    inc2_discounts_credits_rebates = 1
  else:
    inc1_discounts_credits_rebates = 1
    inc2_discounts_credits_rebates = 1

  # ______define the inputs_______
  tm_scen_metrics_df = pd.read_csv(tm_run_location+'/OUTPUT/metrics/scenario_metrics.csv',names=["runid", "metric_name", "value"])
  tm_auto_owned_df = pd.read_csv(tm_run_location+'/OUTPUT/metrics/autos_owned.csv')
  tm_travel_cost_df = pd.read_csv(tm_run_location+'/OUTPUT/core_summaries/TravelCost.csv')
  tm_auto_times_df = pd.read_csv(tm_run_location+'/OUTPUT/metrics/auto_times.csv',sep=",")#, index_col=[0,1])
  tm_od_travel_times_df = pd.read_csv(tm_run_location+'/OUTPUT/core_summaries/ODTravelTime_byModeTimeperiod_reduced_file.csv')
  tm_od_tt_with_cities_df = tm_od_travel_times_df.merge(taz_cities_df, left_on='orig_taz', right_on='taz1454', how='left', suffixes = ["",'_orig']).merge(taz_cities_df, left_on='dest_taz', right_on='taz1454', how='left', suffixes = ["",'_dest'])
  tm_loaded_network_df = pd.read_csv(tm_run_location+'/OUTPUT/avgload5period.csv')
  tm_loaded_network_df = tm_loaded_network_df.rename(columns=lambda x: x.strip())
  # ----merging df that has the list of minor segments with loaded network - for corridor analysis
  tm_loaded_network_df['a_b'] = tm_loaded_network_df['a'].astype(str) + "_" + tm_loaded_network_df['b'].astype(str)
  tm_loaded_network_df = tm_loaded_network_df.merge(minor_links_df, on='a_b', how='left')
  # ----import network links file from reduced dbf as a dataframe to merge with loaded network and get toll rates
  network_links_dbf = pd.read_csv(tm_run_location + '\\OUTPUT\\shapefile\\network_links_reduced_file.csv')
  tm_loaded_network_df = tm_loaded_network_df.copy().merge(network_links_dbf.copy(), on='a_b', how='left')

  # load collisionLookup table
  if tm_runid == '2035_TM152_FBP_Plus_24_rerunTM1.5.2.5':
    collision_rates_df = pd.read_csv(tm_run_location + '/INPUT_032023_161232/metrics/collisionLookup.csv')
  elif tm_runid == '2035_TM152_NGF_NP07_Path4_02':
    collision_rates_df = pd.read_csv(tm_run_location + '/INPUT_032123_160659/metrics/collisionLookup.csv')
  else:
    collision_rates_df = pd.read_csv(tm_run_location + '/INPUT/metrics/collisionLookup.csv')
  # load vmt_vht_metrics.csv for vmt calc
  tm_vmt_metrics_df = pd.read_csv(tm_run_location + '/OUTPUT/metrics/vmt_vht_metrics.csv', sep=",", index_col=[0,1])
  # load transit_times_by_mode_income.csv
  tm_transit_times_df = pd.read_csv(tm_run_location + '/OUTPUT/metrics/transit_times_by_mode_income.csv', sep=",", index_col=[0,1])
  # load CommuteByIncomeHousehold.csv
  tm_commute_df = pd.read_csv(tm_run_location+'/OUTPUT/core_summaries/CommuteByIncomeByTPHousehold.csv')
  # load VehicleMilesTraveled_households.csv
  vmt_hh_df = pd.read_csv(tm_run_location+'/OUTPUT/core_summaries/VehicleMilesTraveled_households.csv')


  # ______load 2015 network to use for speed comparisons in vmt corrections______
  run_2015_location = "L:\\Application\\Model_One\\NextGenFwys\\Scenarios\\2015_TM152_NGF_05"
  runid_2015 = run_2015_location.split('\\')[-1]
  loaded_network_2015_df = pd.read_csv(run_2015_location+'/OUTPUT/avgload5period.csv')
  loaded_network_2015_df = loaded_network_2015_df.rename(columns=lambda x: x.strip())

  metrics_dict = {}
  calculate_Affordable1_transportation_costs(tm_runid, year, tm_scen_metrics_df, tm_auto_owned_df, tm_travel_cost_df, tm_auto_times_df, metrics_dict)
  # print("@@@@@@@@@@@@@ A1 Done")
  calculate_Affordable2_ratio_time_cost(tm_runid, year, tm_loaded_network_df, network_links_dbf, metrics_dict)
  # print("@@@@@@@@@@@@@ A2 Done")
  calculate_Efficient1_ratio_travel_time(tm_runid, year, tm_od_tt_with_cities_df, metrics_dict)
  # print("@@@@@@@@@@@@@ E1 Done")
  calculate_Efficient2_commute_mode_share(tm_runid, year, tm_commute_df, metrics_dict)
  calculate_Reliable1_change_travel_time(tm_runid, year, tm_loaded_network_df, metrics_dict)
  # print("@@@@@@@@@@@@@ R1 Done")
  calculate_Reliable2_ratio_peak_nonpeak(tm_runid, year, tm_od_tt_with_cities_df, metrics_dict) #add tm_metric_id to all?
  # print("@@@@@@@@@@@@@ R2 Done")
  calculate_Safe1_fatalities_freewayss_nonfreeways(tm_runid, year, tm_loaded_network_df, metrics_dict)
  # print("@@@@@@@@@@@@@ S1 Done")
  calculate_Safe2_change_in_vmt(tm_runid, year, tm_loaded_network_df, metrics_dict)
  # print("@@@@@@@@@@@@@ S2 Done")

  # -----------run base for comparisons---------------

  calculate_Safe2_change_in_vmt(tm_runid_base, year, tm_loaded_network_df_base, metrics_dict)
  # print("@@@@@@@@@@@@@ S2 Done")

  # -----------run comparisons---------------
  calculate_change_between_run_and_base(tm_runid, tm_runid_base, year, 'Safe 2', metrics_dict)

  # -----------base runs--------------------
  calculate_Affordable1_transportation_costs(tm_runid_base, year, tm_scen_metrics_df_base, tm_auto_owned_df_base, tm_travel_cost_df_base, tm_auto_times_df_base, metrics_dict)
  # print("@@@@@@@@@@@@@ A1 Done")
  calculate_Efficient1_ratio_travel_time(tm_runid_base, year, tm_od_tt_with_cities_df_base, metrics_dict)
  # print("@@@@@@@@@@@@@ E1 Done")
  calculate_Efficient2_commute_mode_share(tm_runid_base, year, tm_commute_df_base, metrics_dict)
  calculate_Reliable2_ratio_peak_nonpeak(tm_runid_base, year, tm_od_tt_with_cities_df_base, metrics_dict) #add tm_metric_id to all?
  # print("@@@@@@@@@@@@@ R2 Done")
  calculate_Safe1_fatalities_freewayss_nonfreeways(tm_runid_base, year, tm_loaded_network_df_base, metrics_dict)
  # print("@@@@@@@@@@@@@ S1 Done")
  # run function to calculate top level metrics
  calculate_top_level_metrics(tm_runid, year, tm_vmt_metrics_df, tm_auto_times_df, tm_transit_times_df, tm_commute_df, tm_loaded_network_df, vmt_hh_df,tm_scen_metrics_df, metrics_dict)  # calculate for base run too
  calculate_top_level_metrics(tm_runid_base, year, tm_vmt_metrics_df_base, tm_auto_times_df_base, tm_transit_times_df_base, tm_commute_df_base, tm_loaded_network_df_base, vmt_hh_df_base,tm_scen_metrics_df_base, metrics_dict)
  
  # _________output table__________
  out_series = pd.Series(metrics_dict)
  out_frame  = out_series.to_frame().reset_index()
  out_frame.columns = ['modelrun_id','metric_id','intermediate/final','key','metric_desc','year','value']
  # print out table

  out_filename = os.path.join(os.getcwd(),"ngfs_metrics_{}.csv".format(tm_runid))
  out_frame.to_csv(out_filename, float_format='%.5f', index=False) #, header=False
  print("Wrote {}".format(out_filename))



