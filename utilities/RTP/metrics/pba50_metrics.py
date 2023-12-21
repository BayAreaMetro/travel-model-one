USAGE = """

  python Metrics.py

  Needs access to these box folders and M Drive
    Box/Modeling and Surveys/Urban Modeling/Bay Area UrbanSim 1.5/PBA50/Draft Blueprint runs/
    Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/

  Processes model outputs and creates a single csv with scenario metrics in this folder:
    Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/

  This csv file will have 6 columns:
    1) modelrun ID
    2) metric ID
    3) metric name
    4) year  (note: for metrics that depict change from 2015 to 2050, this value will be 2050)
    5) blueprint type
    6) metric value

"""

import datetime, os, pathlib, sys
import numpy, pandas as pd
from collections import OrderedDict, defaultdict


def calculate_urbansim_highlevelmetrics(runid, dbp, parcel_sum_df, tract_sum_df, county_sum_df, metrics_dict):

    metric_id = "Overall"

    #################### Housing

    # all households
    metrics_dict[runid,metric_id,'TotHH_region',y2,dbp] = parcel_sum_df['tothh_2050'].sum()
    metrics_dict[runid,metric_id,'TotHH_region',y1,dbp] = parcel_sum_df['tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_growth_region',y_diff,dbp] = metrics_dict[runid,metric_id,'TotHH_region',y2,dbp] / metrics_dict[runid,metric_id,'TotHH_region',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] = parcel_sum_df['tothh_2050'].sum() - parcel_sum_df['tothh_2015'].sum()
    # HH growth by county
    for index,row in county_sum_df.iterrows():
        metrics_dict[runid,metric_id,'TotHH_county_%s' % row['county'],y2,dbp] = row['tothh_2050'] 
        metrics_dict[runid,metric_id,'TotHH_county_%s' % row['county'],y1,dbp] = row['tothh_2015']
        metrics_dict[runid,metric_id,'TotHH_county_growth_%s' % row['county'],y_diff,dbp] = row['tothh_2050'] / row['tothh_2015'] - 1
        metrics_dict[runid,metric_id,'TotHH_county_shareofgrowth_%s' % row['county'],y_diff,dbp] = (row['tothh_2050'] - row['tothh_2015']) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] 
        
    # HH Growth in all GGs
    metrics_dict[runid,metric_id,'TotHH_GG',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('GG', na=False), 'tothh_2050'].sum() 
    metrics_dict[runid,metric_id,'TotHH_GG',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('GG', na=False), 'tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'TotHH_GG_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotHH_GG',y2,dbp] / metrics_dict[runid,metric_id,'TotHH_GG',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_GG_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotHH_GG',y2,dbp] - metrics_dict[runid,metric_id,'TotHH_GG',y1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] 
        
    # HH Growth in non GGs
    metrics_dict[runid,metric_id,'TotHH_nonGG',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('GG', na=False)==0, 'tothh_2050'].sum() 
    metrics_dict[runid,metric_id,'TotHH_nonGG',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('GG', na=False)==0, 'tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'TotHH_nonGG_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotHH_nonGG',y2,dbp] / metrics_dict[runid,metric_id,'TotHH_nonGG',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_nonGG_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotHH_nonGG',y2,dbp] - metrics_dict[runid,metric_id,'TotHH_nonGG',y1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] 

    # HH Growth in PDAs
    metrics_dict[runid,metric_id,'TotHH_PDA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pda_id_pba50_fb'].str.contains('non-PDA', na=False)==0, 'tothh_2050'].sum() 
    metrics_dict[runid,metric_id,'TotHH_PDA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pda_id_pba50_fb'].str.contains('non-PDA', na=False)==0, 'tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'TotHH_PDA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotHH_PDA',y2,dbp] / metrics_dict[runid,metric_id,'TotHH_PDA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_PDA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotHH_PDA',y2,dbp] - metrics_dict[runid,metric_id,'TotHH_PDA',y1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] 


    # HH Growth in GGs that are not PDAs
    metrics_dict[runid,metric_id,'TotHH_GG_notPDA',y2,dbp] = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('GG', na=False)) & \
                                                                (parcel_sum_df['pda_id_pba50_fb'].str.contains('non-PDA', na=False)), 'tothh_2050'].sum() 
    metrics_dict[runid,metric_id,'TotHH_GG_notPDA',y1,dbp] = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('GG', na=False)) & \
                                                                (parcel_sum_df['pda_id_pba50_fb'].str.contains('non-PDA', na=False)), 'tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'TotHH_GG_notPDA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotHH_GG_notPDA',y2,dbp] / metrics_dict[runid,metric_id,'TotHH_GG_notPDA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_GG_notPDA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotHH_GG_notPDA',y2,dbp] - metrics_dict[runid,metric_id,'TotHH_GG_notPDA',y1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] 


    # HH Growth in HRAs
    metrics_dict[runid,metric_id,'TotHH_HRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'tothh_2050'].sum() 
    metrics_dict[runid,metric_id,'TotHH_HRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'TotHH_HRA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotHH_HRA',y2,dbp] / metrics_dict[runid,metric_id,'TotHH_HRA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_HRA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotHH_HRA',y2,dbp] - metrics_dict[runid,metric_id,'TotHH_HRA',y1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] 

    # HH Growth in TRAs
    metrics_dict[runid,metric_id,'TotHH_TRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'tothh_2050'].sum() 
    metrics_dict[runid,metric_id,'TotHH_TRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'TotHH_TRA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotHH_TRA',y2,dbp] / metrics_dict[runid,metric_id,'TotHH_TRA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_TRA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotHH_TRA',y2,dbp] - metrics_dict[runid,metric_id,'TotHH_TRA',y1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] 

    # HH Growth in areas that are both HRAs and TRAs
    metrics_dict[runid,metric_id,'TotHH_HRAandTRA',y2,dbp] = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('HRA', na=False)) &\
                                                                (parcel_sum_df['fbpchcat'].str.contains('tra', na=False)) , 'tothh_2050'].sum() 
    metrics_dict[runid,metric_id,'TotHH_HRAandTRA',y1,dbp] = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('HRA', na=False)) &\
                                                                (parcel_sum_df['fbpchcat'].str.contains('tra', na=False)) , 'tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'TotHH_HRAandTRA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotHH_HRAandTRA',y2,dbp] / metrics_dict[runid,metric_id,'TotHH_HRAandTRA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_HRAandTRA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotHH_HRAandTRA',y2,dbp] - metrics_dict[runid,metric_id,'TotHH_HRAandTRA',y1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] 

    # HH Growth in CoCs
    metrics_dict[runid,metric_id,'TotHH_CoC',y2,dbp] = tract_sum_df.loc[tract_sum_df['coc_flag_pba2050']==1, 'tothh_2050'].sum() 
    metrics_dict[runid,metric_id,'TotHH_CoC',y1,dbp] = tract_sum_df.loc[tract_sum_df['coc_flag_pba2050']==1, 'tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'TotHH_CoC_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotHH_CoC',y2,dbp] / metrics_dict[runid,metric_id,'TotHH_CoC',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_CoC_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotHH_CoC',y2,dbp] - metrics_dict[runid,metric_id,'TotHH_CoC',y1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] 

    # HH Growth in check CoCs
    metrics_dict[runid,metric_id,'TotHH_CoC_check',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['coc_flag_pba2050']==1, 'tothh_2050'].sum() 
    metrics_dict[runid,metric_id,'TotHH_CoC_check',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['coc_flag_pba2050']==1, 'tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'TotHH_CoCcheck_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotHH_CoC_check',y2,dbp] / metrics_dict[runid,metric_id,'TotHH_CoC_check',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_CoCcheck_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotHH_CoC_check',y2,dbp] - metrics_dict[runid,metric_id,'TotHH_CoC_check',y1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] 

    # HH Growth in non-CoCs
    metrics_dict[runid,metric_id,'TotHH_nonCoC',y2,dbp] = tract_sum_df.loc[tract_sum_df['coc_flag_pba2050']==0, 'tothh_2050'].sum() 
    metrics_dict[runid,metric_id,'TotHH_nonCoC',y1,dbp] = tract_sum_df.loc[tract_sum_df['coc_flag_pba2050']==0, 'tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'TotHH_nonCoC_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotHH_nonCoC',y2,dbp] / metrics_dict[runid,metric_id,'TotHH_nonCoC',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_nonCoC_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotHH_nonCoC',y2,dbp] - metrics_dict[runid,metric_id,'TotHH_nonCoC',y1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] 


    #################### Jobs


    # all jobs
    metrics_dict[runid,metric_id,'TotJobs_region',y2,dbp] = parcel_sum_df['totemp_2050'].sum()
    metrics_dict[runid,metric_id,'TotJobs_region',y1,dbp] = parcel_sum_df['totemp_2015'].sum()
    metrics_dict[runid,metric_id,'TotJobs_growth_region',y_diff,dbp] = metrics_dict[runid,metric_id,'TotJobs_region',y2,dbp]  / metrics_dict[runid,metric_id,'TotJobs_region',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] = parcel_sum_df['totemp_2050'].sum() - parcel_sum_df['totemp_2015'].sum()
    #Job growth by county
    for index,row in county_sum_df.iterrows():
        metrics_dict[runid,metric_id,'TotJobs_county_%s' % row['county'],y2,dbp] = row['totemp_2050'] 
        metrics_dict[runid,metric_id,'TotJobs_county_%s' % row['county'],y1,dbp] = row['totemp_2015']
        metrics_dict[runid,metric_id,'TotJobs_growth_%s' % row['county'],y_diff,dbp] = row['totemp_2050'] / row['totemp_2015']  - 1
        metrics_dict[runid,metric_id,'TotJobs_county_shareofgrowth_%s' % row['county'],y_diff,dbp] = (row['totemp_2050'] - row['totemp_2015']) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] 


    # Job Growth in all GGs
    metrics_dict[runid,metric_id,'TotJobs_GG',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('GG', na=False), 'totemp_2050'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_GG',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('GG', na=False), 'totemp_2015'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_GG_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotJobs_GG',y2,dbp] / metrics_dict[runid,metric_id,'TotJobs_GG',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_GG_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_GG',y2,dbp] - metrics_dict[runid,metric_id,'TotJobs_GG',y1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] 

    # Job Growth in non GGs
    metrics_dict[runid,metric_id,'TotJobs_nonGG',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('GG', na=False)==0, 'totemp_2050'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_nonGG',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('GG', na=False)==0, 'totemp_2015'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_nonGG_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotJobs_nonGG',y2,dbp] / metrics_dict[runid,metric_id,'TotJobs_nonGG',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_nonGG_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_nonGG',y2,dbp] - metrics_dict[runid,metric_id,'TotJobs_nonGG',y1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] 

    # Job Growth in PDAs
    metrics_dict[runid,metric_id,'TotJobs_PDA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pda_id_pba50_fb'].str.contains('non-PDA', na=False)==0, 'totemp_2050'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_PDA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pda_id_pba50_fb'].str.contains('non-PDA', na=False)==0, 'totemp_2015'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_PDA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotJobs_PDA',y2,dbp] / metrics_dict[runid,metric_id,'TotJobs_PDA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_PDA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_PDA',y2,dbp] - metrics_dict[runid,metric_id,'TotJobs_PDA',y1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] 

    # Job Growth in GGs that are not PDAs
    metrics_dict[runid,metric_id,'TotJobs_GG_notPDA',y2,dbp] = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('GG', na=False)) & \
                                                                (parcel_sum_df['pda_id_pba50_fb'].str.contains('non-PDA', na=False)), 'totemp_2050'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_GG_notPDA',y1,dbp] = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('GG', na=False)) & \
                                                                (parcel_sum_df['pda_id_pba50_fb'].str.contains('non-PDA', na=False)), 'totemp_2015'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_GG_notPDA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotJobs_GG_notPDA',y2,dbp] / metrics_dict[runid,metric_id,'TotJobs_GG_notPDA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_GG_notPDA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_GG_notPDA',y2,dbp] - metrics_dict[runid,metric_id,'TotJobs_GG_notPDA',y1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] 

    # Job Growth in HRAs
    metrics_dict[runid,metric_id,'TotJobs_HRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'totemp_2050'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_HRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'totemp_2015'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_HRA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotJobs_HRA',y2,dbp] / metrics_dict[runid,metric_id,'TotJobs_HRA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_HRA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_HRA',y2,dbp] - metrics_dict[runid,metric_id,'TotJobs_HRA',y1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] 

    # Job Growth in TRAs
    metrics_dict[runid,metric_id,'TotJobs_TRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'totemp_2050'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_TRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'totemp_2015'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_TRA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotJobs_TRA',y2,dbp] / metrics_dict[runid,metric_id,'TotJobs_TRA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_TRA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_TRA',y2,dbp] - metrics_dict[runid,metric_id,'TotJobs_TRA',y1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] 

    # Job Growth in areas that are both HRAs and TRAs
    metrics_dict[runid,metric_id,'TotJobs_HRAandTRA',y2,dbp] = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('HRA', na=False)) &\
                                                                (parcel_sum_df['fbpchcat'].str.contains('tra', na=False)) , 'totemp_2050'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_HRAandTRA',y1,dbp] = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('HRA', na=False)) &\
                                                                (parcel_sum_df['fbpchcat'].str.contains('tra', na=False)) , 'totemp_2015'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_HRAandTRA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotJobs_HRAandTRA',y2,dbp] / metrics_dict[runid,metric_id,'TotJobs_HRAandTRA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_HRAandTRA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_HRAandTRA',y2,dbp] - metrics_dict[runid,metric_id,'TotJobs_HRAandTRA',y1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] 


    # Jobs Growth in CoCs
    metrics_dict[runid,metric_id,'TotJobs_CoC',y2,dbp] = tract_sum_df.loc[tract_sum_df['coc_flag_pba2050']==1, 'totemp_2050'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_CoC',y1,dbp] = tract_sum_df.loc[tract_sum_df['coc_flag_pba2050']==1, 'totemp_2015'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_CoC_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotJobs_CoC',y2,dbp] / metrics_dict[runid,metric_id,'TotJobs_CoC',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_CoC_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_CoC',y2,dbp] - metrics_dict[runid,metric_id,'TotJobs_CoC',y1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] 

    # Jobs Growth in non-CoCs
    metrics_dict[runid,metric_id,'TotJobs_nonCoC',y2,dbp] = tract_sum_df.loc[tract_sum_df['coc_flag_pba2050']==0, 'totemp_2050'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_nonCoC',y1,dbp] = tract_sum_df.loc[tract_sum_df['coc_flag_pba2050']==0, 'totemp_2015'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_nonCoC_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotJobs_nonCoC',y2,dbp] / metrics_dict[runid,metric_id,'TotJobs_nonCoC',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_nonCoC_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_nonCoC',y2,dbp] - metrics_dict[runid,metric_id,'TotJobs_nonCoC',y1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] 


    ############################
    # LIHH
    metrics_dict[runid,metric_id,'LIHH_share_2050',y2,dbp] = (parcel_sum_df['hhq1_2050'].sum() + parcel_sum_df['hhq2_2050'].sum()) / parcel_sum_df['tothh_2050'].sum()
    metrics_dict[runid,metric_id,'LIHH_share_2015',y1,dbp] = (parcel_sum_df['hhq1_2015'].sum() + parcel_sum_df['hhq2_2050'].sum()) / parcel_sum_df['tothh_2015'].sum()
    metrics_dict[runid,metric_id,'LIHH_growth_region',y_diff,dbp] = (parcel_sum_df['hhq1_2050'].sum() + parcel_sum_df['hhq2_2050'].sum()) / (parcel_sum_df['hhq1_2015'].sum() + parcel_sum_df['hhq2_2050'].sum())
    for index,row in county_sum_df.iterrows():
        metrics_dict[runid,metric_id,'LIHH_growth_%s' % row["county"],y_diff,dbp] = row['LIHH_growth']
            


def calculate_tm_highlevelmetrics(runid, dbp, parcel_sum_df, county_sum_df, metrics_dict):

    metric_id = "Overall_TM"

    # TBD

def calculate_normalize_factor_Q1Q2(parcel_sum_df):
    return ((parcel_sum_df['hhq1_2050'].sum() + parcel_sum_df['hhq2_2050'].sum()) / parcel_sum_df['tothh_2050'].sum()) \
                        / ((parcel_sum_df['hhq1_2015'].sum() + parcel_sum_df['hhq2_2015'].sum()) /  parcel_sum_df['tothh_2015'].sum())

def calculate_normalize_factor_Q1(parcel_sum_df):
    return (parcel_sum_df['hhq1_2050'].sum() / parcel_sum_df['tothh_2050'].sum()) \
                        / (parcel_sum_df['hhq1_2015'].sum() /  parcel_sum_df['tothh_2015'].sum())


def calculate_Affordable1_HplusT_costs(runid, year, dbp, tm_scen_metrics_df, tm_auto_owned_df, tm_auto_times_df, tm_travel_cost_df, tm_parking_cost_df, housing_costs_df, metrics_dict):

    metric_id = "A1"

    days_per_year = 300
    UBI_annual = 6000

    # Total number of households
    tm_tot_hh      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_households_inc") == True), 'value'].sum()
    tm_tot_hh_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_households_inc1"),'value'].item()
    tm_tot_hh_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_households_inc2"),'value'].item()

    # Total household income (model outputs are in 2000$, annual), adjusting for UBI for Q1 households
    tm_total_hh_inc      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_hh_inc") == True), 'value'].sum()
    tm_total_hh_inc_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_hh_inc_inc2"),'value'].item()

    if dbp in ["Plus","Alt1","Alt2"] :
        tm_total_hh_inc_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_hh_inc_inc1"),'value'].item() + (UBI_annual * tm_tot_hh_inc1 / inflation_00_20)
    else:
        tm_total_hh_inc_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_hh_inc_inc1"),'value'].item()
    
    tm_total_hh_inc_inc1_noubi = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_hh_inc_inc1"),'value'].item()


    # Total transit fares (model outputs are in 2000$, per day)
    tm_tot_transit_fares      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_transit_fares") == True), 'value'].sum() * days_per_year
    tm_tot_transit_fares_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_transit_fares_inc1"),'value'].item() * days_per_year
    tm_tot_transit_fares_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_transit_fares_inc2"),'value'].item() * days_per_year

    # Total auto op cost (model outputs are in 2000$, per day)
    tm_tot_auto_op_cost      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_auto_cost_inc") == True), 'value'].sum() * days_per_year
    tm_tot_auto_op_cost_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_auto_cost_inc1"),'value'].item() * days_per_year
    tm_tot_auto_op_cost_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_auto_cost_inc2"),'value'].item() * days_per_year

    '''
    if year=="2015":
        # Total auto parking cost (model outputs are in 2000$, per day, in cents)
        tm_travel_cost_df['parking_cost'] = (tm_travel_cost_df.pcost_indiv + tm_travel_cost_df.pcost_joint) *  tm_travel_cost_df.freq
        tm_tot_auto_park_cost      = tm_travel_cost_df.parking_cost.sum() * days_per_year / 100
        tm_tot_auto_park_cost_inc1 = tm_travel_cost_df.loc[(tm_travel_cost_df['incQ'] == 1),'parking_cost'].sum() * days_per_year / 100
        tm_tot_auto_park_cost_inc2 = tm_travel_cost_df.loc[(tm_travel_cost_df['incQ'] == 2),'parking_cost'].sum() * days_per_year / 100
    else:
    '''
    # Total auto parking cost (model outputs are in 2000$, per day, in dollars)
    tm_tot_auto_park_cost      = tm_parking_cost_df.parking_cost.sum() * days_per_year
    tm_tot_auto_park_cost_inc1 = tm_parking_cost_df.loc[(tm_parking_cost_df['incQ'] == 1),'parking_cost'].sum() * days_per_year
    tm_tot_auto_park_cost_inc2 = tm_parking_cost_df.loc[(tm_parking_cost_df['incQ'] == 2),'parking_cost'].sum() * days_per_year


    # Calculating number of autos owned from autos_owned.csv
    tm_auto_owned_df['tot_autos'] = tm_auto_owned_df['autos'] * tm_auto_owned_df['households'] 
    tm_tot_autos_owned      = tm_auto_owned_df['tot_autos'].sum()
    tm_tot_autos_owned_inc1 = tm_auto_owned_df.loc[(tm_auto_owned_df['incQ'] == 1), 'tot_autos'].sum()
    tm_tot_autos_owned_inc2 = tm_auto_owned_df.loc[(tm_auto_owned_df['incQ'] == 2), 'tot_autos'].sum()

    # Total auto ownership cost in 2000$   (total annual cost for all households)
    tm_tot_auto_owner_cost      = tm_tot_autos_owned      * auto_ownership_cost      * inflation_18_20 / inflation_00_20
    tm_tot_auto_owner_cost_inc1 = tm_tot_autos_owned_inc1 * auto_ownership_cost_inc1 * inflation_18_20 / inflation_00_20
    tm_tot_auto_owner_cost_inc2 = tm_tot_autos_owned_inc2 * auto_ownership_cost_inc2 * inflation_18_20 / inflation_00_20

    # Total Transportation Cost (in 2000$) (total annual cost for all households)
    tp_cost      = tm_tot_auto_op_cost      + tm_tot_transit_fares      + tm_tot_auto_owner_cost      + tm_tot_auto_park_cost
    tp_cost_inc1 = tm_tot_auto_op_cost_inc1 + tm_tot_transit_fares_inc1 + tm_tot_auto_owner_cost_inc1 + tm_tot_auto_park_cost_inc1
    tp_cost_inc2 = tm_tot_auto_op_cost_inc2 + tm_tot_transit_fares_inc2 + tm_tot_auto_owner_cost_inc2 + tm_tot_auto_park_cost_inc2

    # Transportation cost % of income
    tp_cost_pct_inc          = tp_cost      / tm_total_hh_inc
    tp_cost_pct_inc_inc1     = tp_cost_inc1 / tm_total_hh_inc_inc1
    tp_cost_pct_inc_inc2     = tp_cost_inc2 / tm_total_hh_inc_inc2
    tp_cost_pct_inc_inc1and2 = (tp_cost_inc1+tp_cost_inc2) / (tm_total_hh_inc_inc1+tm_total_hh_inc_inc2)

    tp_cost_pct_inc_inc1_noubi = tp_cost_inc1 / tm_total_hh_inc_inc1_noubi

    # Transportation costs annual, in 2000$, for all households together
    metrics_dict[runid,metric_id,'transportation_cost_totalHHincome',year,dbp] = tm_total_hh_inc
    metrics_dict[runid,metric_id,'transportation_cost_autoop',year,dbp]        = tm_tot_auto_op_cost
    metrics_dict[runid,metric_id,'transportation_cost_autopark',year,dbp]      = tm_tot_auto_park_cost
    metrics_dict[runid,metric_id,'transportation_cost_transitfare',year,dbp]   = tm_tot_transit_fares
    metrics_dict[runid,metric_id,'transportation_cost_autoown',year,dbp]       = tm_tot_auto_owner_cost
 
    # Transportation cost % of income metrics       
    metrics_dict[runid,metric_id,'transportation_cost_pct_income',year,dbp]      = tp_cost_pct_inc
    metrics_dict[runid,metric_id,'transportation_cost_pct_income_inc1',year,dbp] = tp_cost_pct_inc_inc1
    metrics_dict[runid,metric_id,'transportation_cost_pct_income_inc2',year,dbp] = tp_cost_pct_inc_inc2
    metrics_dict[runid,metric_id,'transportation_cost_pct_income_inc1and2',year,dbp] = tp_cost_pct_inc_inc1and2

    # Transportation cost % of income metrics; split by cost bucket
    metrics_dict[runid,metric_id,'transportation_cost_pct_income_autoop',year,dbp]        = tm_tot_auto_op_cost / tm_total_hh_inc
    metrics_dict[runid,metric_id,'transportation_cost_pct_income_autopark',year,dbp]      = tm_tot_auto_park_cost / tm_total_hh_inc
    metrics_dict[runid,metric_id,'transportation_cost_pct_income_transitfare',year,dbp]   = tm_tot_transit_fares / tm_total_hh_inc
    metrics_dict[runid,metric_id,'transportation_cost_pct_income_autoown',year,dbp]       = tm_tot_auto_owner_cost / tm_total_hh_inc
 

 
    # Add housing costs from Shimon's outputs
    #housing_costs_2050_df = pd.read_csv('C:/Users/ATapase/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/metrics_input_files/2050 Share of Income Spent on Housing.csv')
    #housing_costs_2015_df = pd.read_csv('C:/Users/ATapase/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/metrics_input_files/2015 Share of Income Spent on Housing.csv')
    #housing_costs_2015_df['totcosts'] = housing_costs_2015_df['share_income'] * housing_costs_2015_df['households']
    '''
    if year == "2050":
        metrics_dict[runid,metric_id,'housing_cost_pct_income',year,dbp]          = housing_costs_2050_df['w_all'].sum()
        metrics_dict[runid,metric_id,'housing_cost_pct_income_inc1',year,dbp]     = housing_costs_2050_df['w_q1'].sum()
        metrics_dict[runid,metric_id,'housing_cost_pct_income_inc2',year,dbp]     = housing_costs_2050_df['w_q2'].sum()
        metrics_dict[runid,metric_id,'housing_cost_pct_income_inc1and2',year,dbp] = housing_costs_2050_df['w_q1_q2'].sum()
    elif year == "2015":
        metrics_dict[runid,metric_id,'housing_cost_pct_income',year,dbp]          = housing_costs_2015_df.loc[(housing_costs_2015_df['tenure'].str.contains("Total")), 'totcosts'].sum() / \
                                                                                        housing_costs_2015_df.loc[(housing_costs_2015_df['tenure'].str.contains("Total")), 'households'].sum()
        metrics_dict[runid,metric_id,'housing_cost_pct_income_inc1',year,dbp]     = housing_costs_2015_df.loc[(housing_costs_2015_df['short_name'].str.contains("q1t")), 'share_income'].sum()
        metrics_dict[runid,metric_id,'housing_cost_pct_income_inc2',year,dbp]     = housing_costs_2015_df.loc[(housing_costs_2015_df['short_name'].str.contains("q2t")), 'share_income'].sum()
        metrics_dict[runid,metric_id,'housing_cost_pct_income_inc1and2',year,dbp] = (housing_costs_2015_df.loc[(housing_costs_2015_df['short_name'].str.contains("q1t")), 'totcosts'].sum() + housing_costs_2015_df.loc[(housing_costs_2015_df['short_name'].str.contains("q2t")), 'totcosts'].sum()) / \
                                                                                        (housing_costs_2015_df.loc[(housing_costs_2015_df['short_name'].str.contains("q1t")), 'households'].sum() + housing_costs_2015_df.loc[(housing_costs_2015_df['short_name'].str.contains("q2t")), 'households'].sum())
    '''
    metrics_dict[runid,metric_id,'housing_cost_pct_income',year,dbp]       =  housing_costs_df.loc[((housing_costs_df['year']==int(year)) & (housing_costs_df['blueprint'].str.contains(dbp) == True)), 'w_all'].sum()
    metrics_dict[runid,metric_id,'housing_cost_pct_income_inc1',year,dbp]  =  housing_costs_df.loc[((housing_costs_df['year']==int(year)) & (housing_costs_df['blueprint'].str.contains(dbp) == True)), 'w_q1'].sum()
    metrics_dict[runid,metric_id,'housing_cost_pct_income_inc2',year,dbp]  =  housing_costs_df.loc[((housing_costs_df['year']==int(year)) & (housing_costs_df['blueprint'].str.contains(dbp) == True)), 'w_q2'].sum()
    metrics_dict[runid,metric_id,'housing_cost_pct_income_inc1and2',year,dbp]  =  housing_costs_df.loc[((housing_costs_df['year']==int(year)) & (housing_costs_df['blueprint'].str.contains(dbp) == True)), 'w_q1_q2'].sum()


    # Total H+T Costs pct of income
    metrics_dict[runid,metric_id,'HplusT_cost_pct_income',year,dbp]          = metrics_dict[runid,metric_id,'transportation_cost_pct_income',year,dbp] + \
                                                                                metrics_dict[runid,metric_id,'housing_cost_pct_income',year,dbp]  
    metrics_dict[runid,metric_id,'HplusT_cost_pct_income_inc1',year,dbp]     = metrics_dict[runid,metric_id,'transportation_cost_pct_income_inc1',year,dbp] + \
                                                                                metrics_dict[runid,metric_id,'housing_cost_pct_income_inc1',year,dbp]  
    metrics_dict[runid,metric_id,'HplusT_cost_pct_income_inc2',year,dbp]     = metrics_dict[runid,metric_id,'transportation_cost_pct_income_inc2',year,dbp] + \
                                                                                metrics_dict[runid,metric_id,'housing_cost_pct_income_inc2',year,dbp]  
    metrics_dict[runid,metric_id,'HplusT_cost_pct_income_inc1and2',year,dbp] = metrics_dict[runid,metric_id,'transportation_cost_pct_income_inc1and2',year,dbp] + \
                                                                                metrics_dict[runid,metric_id,'housing_cost_pct_income_inc1and2',year,dbp]  
    
    


    # Tolls & Fares

    # Reading auto times file
    tm_auto_times_df = tm_auto_times_df.sum(level='Income')

    # Calculating Total Tolls per day = bridge tolls + value tolls  (2000$)
    total_tolls       = OrderedDict()
    total_opcost      = OrderedDict()
    total_valuetolls  = OrderedDict()
    total_bridgetolls = OrderedDict()
    for inc_level in range(1,5): 
        total_tolls['inc%d'  % inc_level]        = tm_auto_times_df.loc['inc%d' % inc_level, ['Bridge Tolls', 'Value Tolls']].sum()/100  # cents -> dollars
        total_opcost['inc%d'  % inc_level]       = tm_auto_times_df.loc['inc%d' % inc_level, ['Total Cost']].sum()/100  # cents -> dollars
        total_valuetolls['inc%d'  % inc_level]   = tm_auto_times_df.loc['inc%d' % inc_level, ['Value Tolls']].sum()/100  # cents -> dollars
        total_bridgetolls['inc%d'  % inc_level]  = tm_auto_times_df.loc['inc%d' % inc_level, ['Bridge Tolls']].sum()/100  # cents -> dollars

    total_tolls_allHH        = sum(total_tolls.values())
    total_tolls_inc1and2     = total_tolls['inc1'] + total_tolls['inc2']

    tm_tot_auto_op_cost_fuel_maint   = sum(total_opcost.values())       * days_per_year
    tm_tot_auto_op_cost_valuetolls   = sum(total_valuetolls.values())   * days_per_year
    tm_tot_auto_op_cost_bridgetolls  = sum(total_bridgetolls.values())  * days_per_year
    # this is to make sure the op costs sourced by this script is equal to the op costs calcuated in scenario_metrics.csv
    tm_tot_auto_op_cost_check        = tm_tot_auto_op_cost_fuel_maint + tm_tot_auto_op_cost_valuetolls + tm_tot_auto_op_cost_bridgetolls

    tm_tot_auto_op_cost_fuel_maint_inc1   = total_opcost['inc1']       * days_per_year
    tm_tot_auto_op_cost_valuetolls_inc1   = total_valuetolls['inc1']   * days_per_year
    tm_tot_auto_op_cost_bridgetolls_inc1  = total_bridgetolls['inc1']  * days_per_year
    # this is to make sure the op costs sourced by this script is equal to the op costs calcuated in scenario_metrics.csv
    tm_tot_auto_op_cost_check_inc1        = tm_tot_auto_op_cost_fuel_maint_inc1 + tm_tot_auto_op_cost_valuetolls_inc1 + tm_tot_auto_op_cost_bridgetolls_inc1
    

    # Mean annual transportation cost per household in 2020$

    '''
    # Breakdown of op costs in 2000$   (output is in cents in 2000$)
    tm_tot_auto_op_cost_fuel_maint  = tm_auto_times_df.loc[(tm_auto_times_df['Income'].str.contains("inc") == True), 'Total Cost'].sum()   / 100  * days_per_year
    tm_tot_auto_op_cost_valuetolls  = tm_auto_times_df.loc[(tm_auto_times_df['Income'].str.contains("inc") == True), 'Value Tolls'].sum()  / 100  * days_per_year
    tm_tot_auto_op_cost_bridgetolls = tm_auto_times_df.loc[(tm_auto_times_df['Income'].str.contains("inc") == True), 'Bridge Tolls'].sum() / 100  * days_per_year
    tm_tot_auto_op_cost_check       = tm_tot_auto_op_cost_fuel_maint + tm_tot_auto_op_cost_valuetolls + tm_tot_auto_op_cost_bridgetolls
    '''
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_numHH',year,dbp]       = tm_tot_hh * inflation_00_20

    # All households
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$',year,dbp]             = tp_cost / tm_tot_hh * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoown',year,dbp]     = tm_tot_auto_owner_cost / tm_tot_hh * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop',year,dbp]      = tm_tot_auto_op_cost / tm_tot_hh * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autopark',year,dbp]    = tm_tot_auto_park_cost / tm_tot_hh * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_transitfare',year,dbp] = tm_tot_transit_fares / tm_tot_hh * inflation_00_20

    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_check',year,dbp]         = tm_tot_auto_op_cost_check / tm_tot_hh * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_fuel_maint',year,dbp]    = tm_tot_auto_op_cost_fuel_maint  / tm_tot_hh * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_valuetolls',year,dbp]    = tm_tot_auto_op_cost_valuetolls  / tm_tot_hh * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_bridgetolls',year,dbp]   = tm_tot_auto_op_cost_bridgetolls / tm_tot_hh * inflation_00_20   
    
    # Q1 HHs
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_inc1',year,dbp]             = tp_cost_inc1 / tm_tot_hh_inc1 * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoown_inc1',year,dbp]     = tm_tot_auto_owner_cost_inc1 / tm_tot_hh_inc1 * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_inc1',year,dbp]      = tm_tot_auto_op_cost_inc1 / tm_tot_hh_inc1 * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autopark_inc1',year,dbp]    = tm_tot_auto_park_cost_inc1 / tm_tot_hh_inc1 * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_transitfare_inc1',year,dbp] = tm_tot_transit_fares_inc1 / tm_tot_hh_inc1 * inflation_00_20

    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_check_inc1',year,dbp]         = tm_tot_auto_op_cost_check_inc1 / tm_tot_hh_inc1 * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_fuel_maint_inc1',year,dbp]    = tm_tot_auto_op_cost_fuel_maint_inc1  / tm_tot_hh_inc1 * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_valuetolls_inc1',year,dbp]    = tm_tot_auto_op_cost_valuetolls_inc1  / tm_tot_hh_inc1 * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_bridgetolls_inc1',year,dbp]   = tm_tot_auto_op_cost_bridgetolls_inc1 / tm_tot_hh_inc1 * inflation_00_20   

    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_inc1',year,dbp] = tp_cost_inc1 / tm_tot_hh_inc1 * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_inc2',year,dbp] = tp_cost_inc2 / tm_tot_hh_inc2 * inflation_00_20

    
    
    # Average Daily Tolls per household
    metrics_dict[runid,metric_id,'tolls_per_HH',year,dbp]           = total_tolls_allHH / tm_tot_hh * inflation_00_20
    metrics_dict[runid,metric_id,'tolls_per_inc1and2HH',year,dbp]   = total_tolls_inc1and2 / (tm_tot_hh_inc1+tm_tot_hh_inc2) * inflation_00_20
    metrics_dict[runid,metric_id,'tolls_per_inc1HH',year,dbp]       = total_tolls['inc1'] / tm_tot_hh_inc1 * inflation_00_20

    # Average Daily Fares per Household   (note: transit fares totals calculated above are annual and need to be divided by days_per_year)
    metrics_dict[runid,metric_id,'fares_per_HH',year,dbp]     = tm_tot_transit_fares / tm_tot_hh * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'fares_per_inc1and2HH',year,dbp]   = (tm_tot_transit_fares_inc1 + tm_tot_transit_fares_inc2) / (tm_tot_hh_inc1+tm_tot_hh_inc2) * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'fares_per_inc1HH',year,dbp] = tm_tot_transit_fares_inc1 / tm_tot_hh_inc1 * inflation_00_20 / days_per_year

    

    ####### per trip auto

    # Total auto trips per day (model outputs are in trips, per day)
    tm_tot_auto_trips      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_auto_trips") == True), 'value'].sum()
    tm_tot_auto_trips_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_auto_trips_inc1"),'value'].item() 
    tm_tot_auto_trips_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_auto_trips_inc2"),'value'].item() 
    metrics_dict[runid,metric_id,'trips_total_auto_perday',year,dbp]          = tm_tot_auto_trips
    metrics_dict[runid,metric_id,'trips_total_auto_perday_inc1',year,dbp]     = tm_tot_auto_trips_inc1

    # Average Tolls per trip  (total_tolls_xx is calculated above as per day tolls in 2000 dollars)
    metrics_dict[runid,metric_id,'per_trip_tolls',year,dbp]          = total_tolls_allHH / tm_tot_auto_trips * inflation_00_20
    metrics_dict[runid,metric_id,'per_trip_tolls_inc1and2',year,dbp] = total_tolls_inc1and2 / (tm_tot_auto_trips_inc1+tm_tot_auto_trips_inc2) * inflation_00_20
    metrics_dict[runid,metric_id,'per_trip_tolls_inc1',year,dbp]     = total_tolls['inc1'] / tm_tot_auto_trips_inc1 * inflation_00_20

    # Total auto operating cost per trip (tm_tot_auto_op_cost and tm_tot_auto_park_cost are calculated above as annual costs in 2000 dollars)
    metrics_dict[runid,metric_id,'per_trip_autocost',year,dbp]           = (tm_tot_auto_op_cost + tm_tot_auto_park_cost) / tm_tot_auto_trips * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_park',year,dbp]      = tm_tot_auto_park_cost / tm_tot_auto_trips * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_op',year,dbp]        = tm_tot_auto_op_cost / tm_tot_auto_trips * inflation_00_20 / days_per_year

    metrics_dict[runid,metric_id,'per_trip_autocost_op_check',year,dbp]             = tm_tot_auto_op_cost_check / tm_tot_auto_trips * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_op_fuel_maint',year,dbp]        = tm_tot_auto_op_cost_fuel_maint / tm_tot_auto_trips * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_op_valuetolls',year,dbp]        = tm_tot_auto_op_cost_valuetolls / tm_tot_auto_trips * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_op_bridgetolls',year,dbp]       = tm_tot_auto_op_cost_bridgetolls / tm_tot_auto_trips * inflation_00_20 / days_per_year

    metrics_dict[runid,metric_id,'per_trip_autocost_inc1',year,dbp]  = (tm_tot_auto_op_cost_inc1 + tm_tot_auto_park_cost_inc1) / tm_tot_auto_trips_inc1 * inflation_00_20 / days_per_year 
    metrics_dict[runid,metric_id,'per_trip_autocost_inc1_op',year,dbp]               = tm_tot_auto_op_cost_inc1             / tm_tot_auto_trips_inc1 * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_inc1_op_check',year,dbp]         = tm_tot_auto_op_cost_check_inc1       / tm_tot_auto_trips_inc1 * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_inc1_op_fuel_maint',year,dbp]    = tm_tot_auto_op_cost_fuel_maint_inc1  / tm_tot_auto_trips_inc1 * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_inc1_op_valuetolls',year,dbp]    = tm_tot_auto_op_cost_valuetolls_inc1  / tm_tot_auto_trips_inc1 * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_inc1_op_bridgetolls',year,dbp]   = tm_tot_auto_op_cost_bridgetolls_inc1 / tm_tot_auto_trips_inc1 * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_inc1_park',year,dbp]             = tm_tot_auto_park_cost_inc1           / tm_tot_auto_trips_inc1 * inflation_00_20 / days_per_year

    metrics_dict[runid,metric_id,'per_trip_autocost_inc1and2',year,dbp]  = (tm_tot_auto_op_cost_inc1 + tm_tot_auto_op_cost_inc2 + tm_tot_auto_park_cost_inc1 + tm_tot_auto_park_cost_inc2) / (tm_tot_auto_trips_inc1+tm_tot_auto_trips_inc2) * inflation_00_20  / days_per_year


    ####### per trip transit

    # Total transit trips per day (model outputs are in trips, per day)
    tm_tot_transit_trips            = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_transit_trips") == True), 'value'].sum() 
    tm_tot_transit_trips_inc1       = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_transit_trips_inc1"),'value'].item() 
    tm_tot_transit_trips_inc2       = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_transit_trips_inc2"),'value'].item() 
    metrics_dict[runid,metric_id,'trips_total_transit_perday',year,dbp]          = tm_tot_transit_trips
    metrics_dict[runid,metric_id,'trips_total_transit_perday_inc1',year,dbp]     = tm_tot_transit_trips_inc1

    # Average Fares per trip   (note: transit fares totals calculated above are annual and need to be divided by days_per_year)
    metrics_dict[runid,metric_id,'per_trip_fare',year,dbp]          = tm_tot_transit_fares / tm_tot_transit_trips * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_fare_inc1and2',year,dbp] = (tm_tot_transit_fares_inc1 + tm_tot_transit_fares_inc2) / (tm_tot_transit_trips_inc1+tm_tot_transit_trips_inc2) * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_fare_inc1',year,dbp]     = tm_tot_transit_fares_inc1 / tm_tot_transit_trips_inc1 * inflation_00_20 / days_per_year
        

def calculate_Affordable2_deed_restricted_housing(runid, dbp, parcel_sum_df, metrics_dict):

    metric_id = "A2"

    # These are off model units to be added, source: Mark Shorett
    # notes:
    # 40K units (preservation); these are within urbansim numbers, just not as affordable housing
    # 35K units (production H4 homeless); not in urbansim technically this should be added to all housing totals, but given its so small, we will add it only to the Deed restricted metrics
    # 7K Affordable projects pipeline (production); but this is already within urbansim units, just not as affordable housing
    offmodel_preserved = 40000
    offmodel_homeless  = 35000
    offmodel_pipeline  = 7572

    # note: we need to subtract out preserved_units_2015, because urbansim adds preserved units as a result of PBA strategies between 2010 and 2015
    # this is because  the strategy was not coded to be "smart" and add units only after 2015 - source: Elly
    # Hence we make the adjustment to shift those units to between 2015 to 2050

    # totals for 2050 and 2015
    metrics_dict[runid,metric_id,'deed_restricted_total',y2,dbp]    = parcel_sum_df['deed_restricted_units_2050'].sum() + offmodel_preserved + offmodel_homeless + offmodel_pipeline
    #metrics_dict[runid,metric_id,'deed_restricted_total',y1,dbp]    = parcel_sum_df['deed_restricted_units_2015'].sum()
    metrics_dict[runid,metric_id,'deed_restricted_total',y1,dbp]    = parcel_sum_df['deed_restricted_units_2015'].sum() - parcel_sum_df['preserved_units_2015'].sum()
    metrics_dict[runid,metric_id,'residential_units_total',y2,dbp]  = parcel_sum_df['residential_units_2050'].sum() + offmodel_homeless
    metrics_dict[runid,metric_id,'residential_units_total',y1,dbp]  = parcel_sum_df['residential_units_2015'].sum()
    #metrics_dict[runid,metric_id,'preserved_units_total',y2,dbp]    = parcel_sum_df['preserved_units_2050'].sum() + offmodel_preserved
    #metrics_dict[runid,metric_id,'preserved_units_total',y1,dbp]    = parcel_sum_df['preserved_units_2015'].sum()
    metrics_dict[runid,metric_id,'preserved_units_total',y2,dbp]    = parcel_sum_df['preserved_units_2050'].sum() + offmodel_preserved
    metrics_dict[runid,metric_id,'preserved_units_total',y1,dbp]    = 0
    metrics_dict[runid,metric_id,'deed_restricted_prod_total',y2,dbp]    = metrics_dict[runid,metric_id,'deed_restricted_total',y2,dbp] - metrics_dict[runid,metric_id,'preserved_units_total',y2,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_prod_total',y1,dbp]    = metrics_dict[runid,metric_id,'deed_restricted_total',y1,dbp] - metrics_dict[runid,metric_id,'preserved_units_total',y1,dbp] 
  
    # HRAs
    metrics_dict[runid,metric_id,'deed_restricted_HRA',y2,dbp]      = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'deed_restricted_units_2050'].sum()
    metrics_dict[runid,metric_id,'deed_restricted_HRA',y1,dbp]      = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'deed_restricted_units_2015'].sum() - parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'preserved_units_2015'].sum()
    metrics_dict[runid,metric_id,'residential_units_HRA',y2,dbp]    = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'residential_units_2050'].sum()
    metrics_dict[runid,metric_id,'residential_units_HRA',y1,dbp]    = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'residential_units_2015'].sum()
    metrics_dict[runid,metric_id,'preserved_units_HRA',y2,dbp]      = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'preserved_units_2050'].sum() 
    metrics_dict[runid,metric_id,'preserved_units_HRA',y1,dbp]      = 0
    metrics_dict[runid,metric_id,'deed_restricted_prod_HRA',y2,dbp]    = metrics_dict[runid,metric_id,'deed_restricted_HRA',y2,dbp] - metrics_dict[runid,metric_id,'preserved_units_HRA',y2,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_prod_HRA',y1,dbp]    = metrics_dict[runid,metric_id,'deed_restricted_HRA',y1,dbp] - metrics_dict[runid,metric_id,'preserved_units_HRA',y1,dbp] 
    
    # TRAs
    metrics_dict[runid,metric_id,'deed_restricted_TRA',y2,dbp]      = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'deed_restricted_units_2050'].sum()
    metrics_dict[runid,metric_id,'deed_restricted_TRA',y1,dbp]      = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'deed_restricted_units_2015'].sum() - parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'preserved_units_2015'].sum()
    metrics_dict[runid,metric_id,'residential_units_TRA',y2,dbp]    = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'residential_units_2050'].sum()
    metrics_dict[runid,metric_id,'residential_units_TRA',y1,dbp]    = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'residential_units_2015'].sum()
    metrics_dict[runid,metric_id,'preserved_units_TRA',y2,dbp]      = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'preserved_units_2050'].sum()
    metrics_dict[runid,metric_id,'preserved_units_TRA',y1,dbp]      = 0
    metrics_dict[runid,metric_id,'deed_restricted_prod_TRA',y2,dbp]    = metrics_dict[runid,metric_id,'deed_restricted_TRA',y2,dbp] - metrics_dict[runid,metric_id,'preserved_units_TRA',y2,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_prod_TRA',y1,dbp]    = metrics_dict[runid,metric_id,'deed_restricted_TRA',y1,dbp] - metrics_dict[runid,metric_id,'preserved_units_TRA',y1,dbp] 
     
    # CoCs
    metrics_dict[runid,metric_id,'deed_restricted_CoC',y2,dbp]      = parcel_sum_df.loc[parcel_sum_df['coc_flag_pba2050']==1, 'deed_restricted_units_2050'].sum() + offmodel_preserved
    metrics_dict[runid,metric_id,'deed_restricted_CoC',y1,dbp]      = parcel_sum_df.loc[parcel_sum_df['coc_flag_pba2050']==1, 'deed_restricted_units_2015'].sum() - parcel_sum_df.loc[parcel_sum_df['coc_flag_pba2050']==1, 'preserved_units_2015'].sum()
    metrics_dict[runid,metric_id,'residential_units_CoC',y2,dbp]    = parcel_sum_df.loc[parcel_sum_df['coc_flag_pba2050']==1, 'residential_units_2050'].sum()
    metrics_dict[runid,metric_id,'residential_units_CoC',y1,dbp]    = parcel_sum_df.loc[parcel_sum_df['coc_flag_pba2050']==1, 'residential_units_2015'].sum()
    metrics_dict[runid,metric_id,'preserved_units_CoC',y2,dbp]      = parcel_sum_df.loc[parcel_sum_df['coc_flag_pba2050']==1, 'preserved_units_2050'].sum() + offmodel_preserved
    metrics_dict[runid,metric_id,'preserved_units_CoC',y1,dbp]      = 0
    metrics_dict[runid,metric_id,'deed_restricted_prod_CoC',y2,dbp]    = metrics_dict[runid,metric_id,'deed_restricted_CoC',y2,dbp] - metrics_dict[runid,metric_id,'preserved_units_CoC',y2,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_prod_CoC',y1,dbp]    = metrics_dict[runid,metric_id,'deed_restricted_CoC',y1,dbp] - metrics_dict[runid,metric_id,'preserved_units_CoC',y1,dbp] 
    

    # diff between 2050 and 2015
    metrics_dict[runid,metric_id,'deed_restricted_diff',y_diff,dbp]         = metrics_dict[runid,metric_id,'deed_restricted_total',y2,dbp]  - metrics_dict[runid,metric_id,'deed_restricted_total',y1,dbp] 
    metrics_dict[runid,metric_id,'residential_units_diff',y_diff,dbp]       = metrics_dict[runid,metric_id,'residential_units_total',y2,dbp] - metrics_dict[runid,metric_id,'residential_units_total',y1,dbp] 
    metrics_dict[runid,metric_id,'preserved_units_diff',y_diff,dbp]         = metrics_dict[runid,metric_id,'preserved_units_total',y2,dbp]  -     metrics_dict[runid,metric_id,'preserved_units_total',y1,dbp]  
    metrics_dict[runid,metric_id,'deed_restricted_prod_diff',y_diff,dbp]    = metrics_dict[runid,metric_id,'deed_restricted_prod_total',y2,dbp]  -   metrics_dict[runid,metric_id,'deed_restricted_prod_total',y1,dbp]  

    metrics_dict[runid,metric_id,'deed_restricted_HRA_diff',y_diff,dbp]         = metrics_dict[runid,metric_id,'deed_restricted_HRA',y2,dbp] - metrics_dict[runid,metric_id,'deed_restricted_HRA',y1,dbp]
    metrics_dict[runid,metric_id,'residential_units_HRA_diff',y_diff,dbp]       = metrics_dict[runid,metric_id,'residential_units_HRA',y2,dbp]  - metrics_dict[runid,metric_id,'residential_units_HRA',y1,dbp]
    metrics_dict[runid,metric_id,'preserved_units_HRA_diff',y_diff,dbp]         = metrics_dict[runid,metric_id,'preserved_units_HRA',y2,dbp]  -     metrics_dict[runid,metric_id,'preserved_units_HRA',y1,dbp]  
    metrics_dict[runid,metric_id,'deed_restricted_prod_HRA_diff',y_diff,dbp]    = metrics_dict[runid,metric_id,'deed_restricted_prod_HRA',y2,dbp]  -   metrics_dict[runid,metric_id,'deed_restricted_prod_HRA',y1,dbp]  

    metrics_dict[runid,metric_id,'deed_restricted_TRA_diff',y_diff,dbp]         = metrics_dict[runid,metric_id,'deed_restricted_TRA',y2,dbp] - metrics_dict[runid,metric_id,'deed_restricted_TRA',y1,dbp]
    metrics_dict[runid,metric_id,'residential_units_TRA_diff',y_diff,dbp]       = metrics_dict[runid,metric_id,'residential_units_TRA',y2,dbp]  - metrics_dict[runid,metric_id,'residential_units_TRA',y1,dbp]
    metrics_dict[runid,metric_id,'preserved_units_TRA_diff',y_diff,dbp]         = metrics_dict[runid,metric_id,'preserved_units_TRA',y2,dbp]  -     metrics_dict[runid,metric_id,'preserved_units_TRA',y1,dbp]  
    metrics_dict[runid,metric_id,'deed_restricted_prod_TRA_diff',y_diff,dbp]    = metrics_dict[runid,metric_id,'deed_restricted_prod_TRA',y2,dbp]  -   metrics_dict[runid,metric_id,'deed_restricted_prod_TRA',y1,dbp]  

    metrics_dict[runid,metric_id,'deed_restricted_nonHRA_diff',y_diff,dbp]      = metrics_dict[runid,metric_id,'deed_restricted_diff',y_diff,dbp] - metrics_dict[runid,metric_id,'deed_restricted_HRA_diff',y_diff,dbp]
    metrics_dict[runid,metric_id,'residential_units_nonHRA_diff',y_diff,dbp]    = metrics_dict[runid,metric_id,'residential_units_diff',y_diff,dbp]  - metrics_dict[runid,metric_id,'residential_units_HRA_diff',y_diff,dbp]
    metrics_dict[runid,metric_id,'preserved_units_nonHRA_diff',y_diff,dbp]      = metrics_dict[runid,metric_id,'preserved_units_diff',y_diff,dbp]  -     metrics_dict[runid,metric_id,'preserved_units_HRA_diff',y_diff,dbp]  
    metrics_dict[runid,metric_id,'deed_restricted_prod_nonHRA_diff',y_diff,dbp] = metrics_dict[runid,metric_id,'deed_restricted_prod_diff',y_diff,dbp]  -   metrics_dict[runid,metric_id,'deed_restricted_prod_HRA_diff',y_diff,dbp]  

    metrics_dict[runid,metric_id,'deed_restricted_CoC_diff',y_diff,dbp]         = metrics_dict[runid,metric_id,'deed_restricted_CoC',y2,dbp] - metrics_dict[runid,metric_id,'deed_restricted_CoC',y1,dbp]
    metrics_dict[runid,metric_id,'residential_units_CoC_diff',y_diff,dbp]       = metrics_dict[runid,metric_id,'residential_units_CoC',y2,dbp]  - metrics_dict[runid,metric_id,'residential_units_CoC',y1,dbp]
    metrics_dict[runid,metric_id,'preserved_units_CoC_diff',y_diff,dbp]         = metrics_dict[runid,metric_id,'preserved_units_CoC',y2,dbp]  -     metrics_dict[runid,metric_id,'preserved_units_CoC',y1,dbp]  
    metrics_dict[runid,metric_id,'deed_restricted_prod_CoC_diff',y_diff,dbp]    = metrics_dict[runid,metric_id,'deed_restricted_prod_CoC',y2,dbp]  -   metrics_dict[runid,metric_id,'deed_restricted_prod_CoC',y1,dbp]  

    # metric: deed restricted share of all housing units
    metrics_dict[runid,metric_id,'deed_restricted_pct_all_units',y2,dbp]        = metrics_dict[runid,metric_id,'deed_restricted_total',y2,dbp]  / metrics_dict[runid,metric_id,'residential_units_total',y2,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_pct_all_units',y1,dbp]        = metrics_dict[runid,metric_id,'deed_restricted_total',y1,dbp]  / metrics_dict[runid,metric_id,'residential_units_total',y1,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_pct_CoC_units',y2,dbp]        = metrics_dict[runid,metric_id,'deed_restricted_CoC',y2,dbp]  / metrics_dict[runid,metric_id,'residential_units_CoC',y2,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_pct_CoC_units',y1,dbp]        = metrics_dict[runid,metric_id,'deed_restricted_CoC',y1,dbp]  / metrics_dict[runid,metric_id,'residential_units_CoC',y1,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_pct_HRA_units',y2,dbp]        = metrics_dict[runid,metric_id,'deed_restricted_HRA',y2,dbp]  / metrics_dict[runid,metric_id,'residential_units_HRA',y2,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_pct_HRA_units',y1,dbp]        = metrics_dict[runid,metric_id,'deed_restricted_HRA',y1,dbp]  / metrics_dict[runid,metric_id,'residential_units_HRA',y1,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_pct_TRA_units',y2,dbp]        = metrics_dict[runid,metric_id,'deed_restricted_TRA',y2,dbp]  / metrics_dict[runid,metric_id,'residential_units_TRA',y2,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_pct_TRA_units',y1,dbp]        = metrics_dict[runid,metric_id,'deed_restricted_TRA',y1,dbp]  / metrics_dict[runid,metric_id,'residential_units_TRA',y1,dbp] 
                                        
    # Q1 share of households
    metrics_dict[runid,metric_id,'Q1_shareofHH',y2,dbp]     = parcel_sum_df['hhq1_2050'].sum()  / parcel_sum_df['tothh_2050'].sum()
    metrics_dict[runid,metric_id,'Q1_shareofHH',y1,dbp]     = parcel_sum_df['hhq1_2015'].sum()  / parcel_sum_df['tothh_2015'].sum()
    metrics_dict[runid,metric_id,'Q1_shareofHH_CoC',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['coc_flag_pba2050']==1, 'hhq1_2050'].sum() /  parcel_sum_df.loc[parcel_sum_df['coc_flag_pba2050']==1, 'tothh_2050'].sum() 
    metrics_dict[runid,metric_id,'Q1_shareofHH_CoC',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['coc_flag_pba2050']==1, 'hhq1_2015'].sum() /  parcel_sum_df.loc[parcel_sum_df['coc_flag_pba2050']==1, 'tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'Q1_shareofHH_HRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'hhq1_2050'].sum() /  parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'tothh_2050'].sum() 
    metrics_dict[runid,metric_id,'Q1_shareofHH_HRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'hhq1_2015'].sum() /  parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'tothh_2015'].sum()  

    # metric: deed restricted production % of total new units production: region-wide, HRA and non-HRA
    metrics_dict[runid,metric_id,'deed_restricted_pct_new_units',y_diff,dbp]        = metrics_dict[runid,metric_id,'deed_restricted_prod_diff',y_diff,dbp]          / metrics_dict[runid,metric_id,'residential_units_diff',y_diff,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_pct_new_units_HRA',y_diff,dbp]    = metrics_dict[runid,metric_id,'deed_restricted_prod_HRA_diff',y_diff,dbp]      / metrics_dict[runid,metric_id,'residential_units_HRA_diff',y_diff,dbp]
    metrics_dict[runid,metric_id,'deed_restricted_pct_new_units_TRA',y_diff,dbp]    = metrics_dict[runid,metric_id,'deed_restricted_prod_TRA_diff',y_diff,dbp]      / metrics_dict[runid,metric_id,'residential_units_TRA_diff',y_diff,dbp]
    metrics_dict[runid,metric_id,'deed_restricted_pct_new_units_nonHRA',y_diff,dbp] = metrics_dict[runid,metric_id,'deed_restricted_prod_nonHRA_diff',y_diff,dbp]   / metrics_dict[runid,metric_id,'residential_units_nonHRA_diff',y_diff,dbp]
    metrics_dict[runid,metric_id,'deed_restricted_pct_new_units_CoC',y_diff,dbp]    = metrics_dict[runid,metric_id,'deed_restricted_prod_CoC_diff',y_diff,dbp]      / metrics_dict[runid,metric_id,'residential_units_CoC_diff',y_diff,dbp]

    # Preservation
    # unsubsidized housing AKA naturally occuring housing affordable to Q1 in 2015  =   Q1 housing in 2015 - deed restricted housing in 2015
    metrics_dict[runid,metric_id,'unsubsidized_affordable_housing_total',y1,dbp]    = parcel_sum_df['hhq1_2015'].sum() - metrics_dict[runid,metric_id,'deed_restricted_total',y1,dbp] 
    metrics_dict[runid,metric_id,'unsubsidized_affordable_housing_HRA',y1,dbp]      = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'hhq1_2015'].sum() - metrics_dict[runid,metric_id,'deed_restricted_HRA',y1,dbp] 
    metrics_dict[runid,metric_id,'unsubsidized_affordable_housing_TRA',y1,dbp]      = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'hhq1_2015'].sum() - metrics_dict[runid,metric_id,'deed_restricted_TRA',y1,dbp] 
    metrics_dict[runid,metric_id,'unsubsidized_affordable_housing_nonHRA',y1,dbp]   = metrics_dict[runid,metric_id,'unsubsidized_affordable_housing_total',y1,dbp]  - metrics_dict[runid,metric_id,'unsubsidized_affordable_housing_HRA',y1,dbp]
    metrics_dict[runid,metric_id,'unsubsidized_affordable_housing_CoC',y1,dbp]      = parcel_sum_df.loc[parcel_sum_df['coc_flag_pba2050']==1, 'hhq1_2015'].sum()  - metrics_dict[runid,metric_id,'deed_restricted_CoC',y1,dbp]

    metrics_dict[runid,metric_id,'deed_restricted_preserv_pct_existingQ1_units',y_diff,dbp]        = metrics_dict[runid,metric_id,'preserved_units_diff',y_diff,dbp]        / metrics_dict[runid,metric_id,'unsubsidized_affordable_housing_total',y1,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_preserv_pct_existingQ1_units_HRA',y_diff,dbp]    = metrics_dict[runid,metric_id,'preserved_units_HRA_diff',y_diff,dbp]    / metrics_dict[runid,metric_id,'unsubsidized_affordable_housing_HRA',y1,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_preserv_pct_existingQ1_units_TRA',y_diff,dbp]    = metrics_dict[runid,metric_id,'preserved_units_TRA_diff',y_diff,dbp]    / metrics_dict[runid,metric_id,'unsubsidized_affordable_housing_TRA',y1,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_preserv_pct_existingQ1_units_nonHRA',y_diff,dbp] = metrics_dict[runid,metric_id,'preserved_units_nonHRA_diff',y_diff,dbp] / metrics_dict[runid,metric_id,'unsubsidized_affordable_housing_nonHRA',y1,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_preserv_pct_existingQ1_units_CoC',y_diff,dbp]    = metrics_dict[runid,metric_id,'preserved_units_CoC_diff',y_diff,dbp]    / metrics_dict[runid,metric_id,'unsubsidized_affordable_housing_CoC',y1,dbp]  
   
    
    # Hard-coding at-risk housing preservation metric
    if dbp in ["FBP", "Alt1", "Alt2"]:
        metrics_dict[runid,metric_id,'at_risk_preserv_pct',y_diff,dbp] = 1
    else:
        metrics_dict[runid,metric_id,'at_risk_preserv_pct',y_diff,dbp] = 0


    '''
    print('********************A2 Affordable********************')
    print('Production:')
    print('DR pct of new units                 %s' % dbp,metrics_dict[runid,metric_id,'deed_restricted_pct_new_units',y_diff,dbp] )
    print('DR pct of new units in HRAs         %s' % dbp,metrics_dict[runid,metric_id,'deed_restricted_pct_new_units_HRA',y_diff,dbp] )
    print('DR pct of new units outside of HRAs %s' % dbp,metrics_dict[runid,metric_id,'deed_restricted_pct_new_units_nonHRA',y_diff,dbp])
    print('DR pct of new units in TRAs         %s' % dbp,metrics_dict[runid,metric_id,'deed_restricted_pct_new_units_TRA',y_diff,dbp] )
    print('DR pct of new units in CoCs         %s' % dbp,metrics_dict[runid,metric_id,'deed_restricted_pct_new_units_CoC',y_diff,dbp] )
    print('Preservation:')
    print('DR pct of unsubsidized units                 %s' % dbp,metrics_dict[runid,metric_id,'deed_restricted_preserv_pct_existingQ1_units',y_diff,dbp] )
    print('DR pct of unsubsidized units in HRAs         %s' % dbp,metrics_dict[runid,metric_id,'deed_restricted_preserv_pct_existingQ1_units_HRA',y_diff,dbp] )
    print('DR pct of unsubsidized units outside of HRAs %s' % dbp,metrics_dict[runid,metric_id,'deed_restricted_preserv_pct_existingQ1_units_nonHRA',y_diff,dbp])
    print('DR pct of unsubsidized units in TRAs         %s' % dbp,metrics_dict[runid,metric_id,'deed_restricted_preserv_pct_existingQ1_units_TRA',y_diff,dbp] )
    print('DR pct of unsubsidized units in CoCs         %s' % dbp,metrics_dict[runid,metric_id,'deed_restricted_preserv_pct_existingQ1_units_CoC',y_diff,dbp] )
    '''

def calculate_Connected1_accessibility(runid, year, dbp, tm_scen_metrics_df, metrics_dict):
    
   # Note - these metrics are grabbed directly from metrics_manual.xlsx

    '''
    metric_id = "C1"

    # % of Jobs accessible by 30 min car OR 45 min transit
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_allmodes',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_accessible_job_share"), 'value'].item()
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_allmodes_coc',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_accessible_job_share_coc"), 'value'].item()
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_allmodes_noncoc',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_accessible_job_share_noncoc"), 'value'].item()
                                
    # % of Jobs accessible by 30 min car only
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_drv_only',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_drv_only_acc_accessible_job_share"), 'value'].item() \
        + tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_drv_acc_accessible_job_share"), 'value'].item()

    metrics_dict[runid,metric_id,'pct_jobs_acc_by_drv_only_coc',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_drv_only_acc_accessible_job_share_coc"), 'value'].item() \
        + tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_drv_acc_accessible_job_share_coc"), 'value'].item()
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_drv_only_noncoc',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_drv_only_acc_accessible_job_share_noncoc"), 'value'].item() \
        + tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_drv_acc_accessible_job_share_noncoc"), 'value'].item()
                                
    # % of Jobs accessible by 45 min transit only 
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_trn_only',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_only_acc_accessible_job_share"), 'value'].item() \
        + tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_drv_acc_accessible_job_share"), 'value'].item()

    metrics_dict[runid,metric_id,'pct_jobs_acc_by_trn_only_coc',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_only_acc_accessible_job_share_coc"), 'value'].item() \
        + tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_drv_acc_accessible_job_share_coc"), 'value'].item()

    metrics_dict[runid,metric_id,'pct_jobs_acc_by_trn_only_noncoc',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_only_acc_accessible_job_share_noncoc"), 'value'].item() \
        + tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_drv_acc_accessible_job_share_noncoc"), 'value'].item()
    '''

def calculate_Connected1_proximity(runid, year, dbp, transitproximity_df, metrics_dict):
    
    metric_id = "C1"    

    for area_type in ['Region','CoCs','HRAs','rural','suburban','urban']:
        # households
        metrics_dict[runid,metric_id,'transitproximity_majorstop_shareof_tothh_%s' % area_type,year,dbp]    = transitproximity_df.loc[(transitproximity_df['Service_Level']=="Major_Transit_Stop") \
                                                                                                              & (transitproximity_df['year']==int(year)) & (transitproximity_df['blueprint'].str.contains(dbp)) \
                                                                                                              & (transitproximity_df['area']==area_type), 'tothh_share'].sum()
        metrics_dict[runid,metric_id,'transitproximity_majorstop_shareof_hhq1_%s' % area_type,year,dbp]     = transitproximity_df.loc[(transitproximity_df['Service_Level']=="Major_Transit_Stop") \
                                                                                                              & (transitproximity_df['year']==int(year)) & (transitproximity_df['blueprint'].str.contains(dbp)) \
                                                                                                              & (transitproximity_df['area']==area_type), 'hhq1_share'].sum()
        # jobs
        metrics_dict[runid,metric_id,'transitproximity_majorstop_shareof_totemp_%s' % area_type,year,dbp]       = transitproximity_df.loc[(transitproximity_df['Service_Level']=="Major_Transit_Stop") \
                                                                                                                 & (transitproximity_df['year']==int(year)) & (transitproximity_df['blueprint'].str.contains(dbp)) \
                                                                                                                  & (transitproximity_df['area']==area_type), 'totemp_share'].sum()
        metrics_dict[runid,metric_id,'transitproximity_majorstop_shareof_RETEMPNjobs_%s' % area_type,year,dbp]  = transitproximity_df.loc[(transitproximity_df['Service_Level']=="Major_Transit_Stop") \
                                                                                                                  & (transitproximity_df['year']==int(year)) & (transitproximity_df['blueprint'].str.contains(dbp)) \
                                                                                                                  & (transitproximity_df['area']==area_type), 'RETEMPN_share'].sum()
        metrics_dict[runid,metric_id,'transitproximity_majorstop_shareof_MWTEMPNjobs_%s' % area_type,year,dbp]  = transitproximity_df.loc[(transitproximity_df['Service_Level']=="Major_Transit_Stop") \
                                                                                                                  & (transitproximity_df['year']==int(year)) & (transitproximity_df['blueprint'].str.contains(dbp)) \
                                                                                                                  & (transitproximity_df['area']==area_type), 'MWTEMPN_share'].sum()



def calculate_Connected2_crowding(runid, year, dbp, transit_operator_df, metrics_dict):
    
    metric_id = "C2"

    if "2015" in runid: tm_run_location = tm_run_location_ipa
    else: tm_run_location = tm_run_location_bp
    tm_crowding_df = pd.read_csv(tm_run_location+runid+'/OUTPUT/metrics/transit_crowding_complete.csv')

    tm_crowding_df = tm_crowding_df[['TIME','SYSTEM','ABNAMESEQ','period','load_standcap','AB_VOL']]
    tm_crowding_df = tm_crowding_df.loc[tm_crowding_df['period'] == "AM"]
    tm_crowding_df['time_overcapacity'] = tm_crowding_df.apply (lambda row: row['TIME'] if (row['load_standcap']>1) else 0, axis=1)
    tm_crowding_df['time_crowded'] = tm_crowding_df.apply (lambda row: row['TIME'] if (row['load_standcap']>0.85) else 0, axis=1)
    tm_crowding_df['person_hrs_total'] = tm_crowding_df['TIME'] * tm_crowding_df['AB_VOL']  
    tm_crowding_df['person_hrs_overcap'] = tm_crowding_df['time_overcapacity'] * tm_crowding_df['AB_VOL']  
    tm_crowding_df['person_hrs_crowded'] = tm_crowding_df['time_crowded'] * tm_crowding_df['AB_VOL']  


    tm_crowding_df = pd.merge(left=tm_crowding_df, right=transit_operator_df, left_on="SYSTEM", right_on="SYSTEM", how="left")

    system_crowding_df = tm_crowding_df[['person_hrs_total','person_hrs_overcap','person_hrs_crowded']].groupby(tm_crowding_df['operator']).sum().reset_index()
    system_crowding_df['pct_overcapacity'] = system_crowding_df['person_hrs_overcap'] / system_crowding_df['person_hrs_total'] 
    system_crowding_df['pct_crowded'] = system_crowding_df['person_hrs_crowded'] / system_crowding_df['person_hrs_total'] 

    for index,row in system_crowding_df.iterrows():
        if row['operator'] in ['Shuttle','SFMTA LRT','SFMTA Bus','SamTrans Local','VTA Bus Local','AC Transit Local','Alameda Bus Operators','Contra Costa Bus Operators',\
                               'Solano Bus Operators','Napa Bus Operators','Sonoma Bus Operators','GGT Local','CC AV Shuttle','ReX Express','SamTrans Express','VTA Bus Express',\
                               'AC Transit Transbay','County Connection Express','GGT Express','WestCAT Express','Soltrans Express','FAST Express','VINE Express','SMART Express',\
                               'WETA','Golden Gate Ferry','Hovercraft','VTA LRT','Dumbarton GRT','Oakland/Alameda Gondola','Contra Costa Gondolas','BART','Caltrain',\
                               'Capitol Corridor','Amtrak','ACE','Dumbarton Rail','SMART', 'Valley Link','High-Speed Rail']:
            metrics_dict[runid,metric_id,'crowded_pct_personhrs_AM_%s' % row['operator'],year,dbp] = row['pct_crowded'] 


def calculate_Connected2_hwy_traveltimes(runid, year, dbp, hwy_corridor_links_df, metrics_dict):

    metric_id = "C2"

    if "2015" in runid: tm_run_location = tm_run_location_ipa
    else: tm_run_location = tm_run_location_bp
    tm_loaded_network_df = pd.read_csv(tm_run_location+runid+'/OUTPUT/avgload5period.csv')

    # Keeping essential columns of loaded highway network: node A and B, distance, free flow time, congested time
    tm_loaded_network_df = tm_loaded_network_df.rename(columns=lambda x: x.strip())
    tm_loaded_network_df = tm_loaded_network_df[['a','b','distance','fft','ctimAM']]
    tm_loaded_network_df['link'] = tm_loaded_network_df['a'].astype(str) + "_" + tm_loaded_network_df['b'].astype(str)

    # merging df that has the list of all
    hwy_corridor_links_df = pd.merge(left=hwy_corridor_links_df, right=tm_loaded_network_df, left_on="link", right_on="link", how="left")
    corridor_travel_times_df = hwy_corridor_links_df[['distance','fft','ctimAM']].groupby(hwy_corridor_links_df['route']).sum().reset_index()

    for index,row in corridor_travel_times_df.iterrows():
        metrics_dict[runid,metric_id,'travel_time_AM_%s' % row['route'],year,dbp] = row['ctimAM'] 


def calculate_Connected2_trn_traveltimes(runid, year, dbp, transit_operator_df, metrics_dict):

    metric_id = "C2"

    if "2015" in runid: tm_run_location = tm_run_location_ipa
    else: tm_run_location = tm_run_location_bp
    tm_trn_line_df = pd.read_csv(tm_run_location+runid+'/OUTPUT/trn/trnline.csv')

    # It doesn't really matter which path ID we pick, as long as it is AM
    tm_trn_line_df = tm_trn_line_df.loc[tm_trn_line_df['path id'] == "am_wlk_loc_wlk"]
    tm_trn_line_df = pd.merge(left=tm_trn_line_df, right=transit_operator_df, left_on="mode", right_on="mode", how="left")

    # grouping by transit operator, and summing all line times and distances, to get metric of "time per unit distance", in minutes/mile
    trn_operator_travel_times_df = tm_trn_line_df[['line time','line dist']].groupby(tm_trn_line_df['operator']).sum().reset_index()
    trn_operator_travel_times_df['time_per_dist_AM'] = trn_operator_travel_times_df['line time'] / trn_operator_travel_times_df['line dist']

    # grouping by mode, and summing all line times and distances, to get metric of "time per unit distance", in minutes/mile
    trn_mode_travel_times_df = tm_trn_line_df[['line time','line dist']].groupby(tm_trn_line_df['mode_name']).sum().reset_index()
    trn_mode_travel_times_df['time_per_dist_AM'] = trn_mode_travel_times_df['line time'] / trn_mode_travel_times_df['line dist']

    for index,row in trn_operator_travel_times_df.iterrows():    # for bus only
        if row['operator'] in ['AC Transit Local','AC Transit Transbay','SFMTA Bus','VTA Bus Local','SamTrans Local','GGT Express','SamTrans Express', 'ReX Express']:
            metrics_dict[runid,metric_id,'time_per_dist_AM_%s' % row['operator'],year,dbp] = row['time_per_dist_AM'] 

    for index,row in trn_mode_travel_times_df.iterrows():
        metrics_dict[runid,metric_id,'time_per_dist_AM_%s' % row['mode_name'],year,dbp] = row['time_per_dist_AM'] 


def calculate_Connected2_transit_asset_condition(runid, year, dbp, transit_asset_condition_df, metrics_dict):
    
    metric_id = "C2"                         
                     
    metrics_dict[runid,metric_id,'asset_life_transit_revveh_beyondlife_pct_of_count',year,dbp]      = transit_asset_condition_df.loc[(transit_asset_condition_df['name']=="transit_revveh_beyondlife_pct_of_count")      & (transit_asset_condition_df['year']==int(year)) & (transit_asset_condition_df['blueprint'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'asset_life_transit_nonveh_beyondlife_pct_of_value',year,dbp]      = transit_asset_condition_df.loc[(transit_asset_condition_df['name']=="transit_nonveh_beyondlife_pct_of_value")      & (transit_asset_condition_df['year']==int(year)) & (transit_asset_condition_df['blueprint'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'asset_life_transit_all_beyondlife_pct_of_value',year,dbp]   = transit_asset_condition_df.loc[(transit_asset_condition_df['name']=="transit_allassets_beyondlife_pct_of_value")   & (transit_asset_condition_df['year']==int(year)) & (transit_asset_condition_df['blueprint'].str.contains(dbp)), 'value'].sum()


def calculate_Diverse1_LIHHinHRAs(runid, dbp, parcel_sum_df, tract_sum_df, normalize_factor_Q1Q2, normalize_factor_Q1, metrics_dict):

    metric_id = "D1"

    
    # Share of region's LIHH households that are in HRAs
    metrics_dict[runid,metric_id,'LIHH_total',y2,dbp] = parcel_sum_df['hhq1_2050'].sum() + parcel_sum_df['hhq2_2050'].sum()
    metrics_dict[runid,metric_id,'LIHH_total',y1,dbp] = parcel_sum_df['hhq1_2015'].sum() + parcel_sum_df['hhq2_2015'].sum()
    metrics_dict[runid,metric_id,'LIHH_inHRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'hhq1_2050'].sum() + parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'hhq2_2050'].sum()
    metrics_dict[runid,metric_id,'LIHH_inHRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'hhq1_2015'].sum() + parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'hhq2_2015'].sum()
    metrics_dict[runid,metric_id,'LIHH_shareinHRA',y2,dbp] = metrics_dict[runid,metric_id,'LIHH_inHRA',y2,dbp] / metrics_dict[runid,metric_id,'LIHH_total',y2,dbp]
    metrics_dict[runid,metric_id,'LIHH_shareinHRA',y1,dbp] = metrics_dict[runid,metric_id,'LIHH_inHRA',y1,dbp] / metrics_dict[runid,metric_id,'LIHH_total',y1,dbp]

    # normalizing for overall growth in LIHH
    metrics_dict[runid,metric_id,'LIHH_shareinHRA_normalized',y1,dbp] = metrics_dict[runid,metric_id,'LIHH_shareinHRA',y1,dbp] * normalize_factor_Q1Q2

    # Total number of Households
    # Total HHs in HRAs, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inHRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inHRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'tothh_2050'].sum()
    # Total HHs in TRAs, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inTRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inTRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'tothh_2050'].sum()
    # Total HHs in HRAs only, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inHRAonly',y1,dbp] = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('HRA', na=False)) & \
                                                                                (parcel_sum_df['fbpchcat'].str.contains('tra', na=False) == False), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inHRAonly',y2,dbp] = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('HRA', na=False)) & \
                                                                                (parcel_sum_df['fbpchcat'].str.contains('tra', na=False) == False), 'tothh_2050'].sum()
    # Total HHs in TRAs only, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inTRAonly',y1,dbp] = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('tra', na=False)) & \
                                                                                (parcel_sum_df['fbpchcat'].str.contains('HRA', na=False) == False), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inTRAonly',y2,dbp] = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('tra', na=False)) & \
                                                                                (parcel_sum_df['fbpchcat'].str.contains('HRA', na=False) == False), 'tothh_2050'].sum()
    # Total HHs in HRA/TRAs, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inHRATRA',y1,dbp] = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('tra', na=False)) & \
                                                                                (parcel_sum_df['fbpchcat'].str.contains('HRA', na=False)), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inHRATRA',y2,dbp] = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('tra', na=False)) & \
                                                                                (parcel_sum_df['fbpchcat'].str.contains('HRA', na=False)), 'tothh_2050'].sum()
     # Total HHs in DR Tracts, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inDRTracts',y1,dbp] = tract_sum_df.loc[(tract_sum_df['DispRisk'] == 1), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inDRTracts',y2,dbp] = tract_sum_df.loc[(tract_sum_df['DispRisk'] == 1), 'tothh_2050'].sum()
    # Total HHs in CoC Tracts, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inCoCTracts',y1,dbp] = tract_sum_df.loc[(tract_sum_df['coc_flag_pba2050'] == 1), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inCoCTracts',y2,dbp] = tract_sum_df.loc[(tract_sum_df['coc_flag_pba2050'] == 1), 'tothh_2050'].sum()
    # Total HHs in remainder of region (RoR); i.e. not HRA or TRA or CoC or DR
    metrics_dict[runid,metric_id,'TotHH_inRoR',y1,dbp] = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('HRA', na=False) == False) & \
                                                                                 (parcel_sum_df['fbpchcat'].str.contains('tra', na=False) == False) & \
                                                                                 (parcel_sum_df['fbpchcat'].str.contains('DIS', na=False) == False) & \
                                                                                 (parcel_sum_df['coc_flag_pba2050'] == 0), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inRoR',y2,dbp] = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('HRA', na=False) == False) & \
                                                                                 (parcel_sum_df['fbpchcat'].str.contains('tra', na=False) == False) & \
                                                                                 (parcel_sum_df['fbpchcat'].str.contains('DIS', na=False) == False) & \
                                                                                 (parcel_sum_df['coc_flag_pba2050'] == 0), 'tothh_2050'].sum()


    ########### Tracking movement of Q1 households: Q1 share of Households
    # Share of Households that are Q1, within each geography type in this order:
    # Overall Region; HRAs; TRAs, DR Tracts; CoCs; Rest of Region; and also GGs and TRichGGs

    metrics_dict[runid,metric_id,'Q1HH_shareofRegion',y1,dbp]            = parcel_sum_df['hhq1_2015'].sum()  / parcel_sum_df['tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'Q1HH_shareofRegion_normalized',y1,dbp] = parcel_sum_df['hhq1_2015'].sum()  / parcel_sum_df['tothh_2015'].sum()  * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofRegion',y2,dbp]            = parcel_sum_df['hhq1_2050'].sum()  / parcel_sum_df['tothh_2050'].sum() 

    metrics_dict[runid,metric_id,'Q1HH_shareofHRA',y1,dbp]               = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inHRA',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofHRA_normalized',y1,dbp]    = metrics_dict[runid,metric_id,'Q1HH_shareofHRA',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofHRA',y2,dbp]               = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'hhq1_2050'].sum()  / metrics_dict[runid,metric_id,'TotHH_inHRA',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofTRA',y1,dbp]               = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inTRA',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofTRA_normalized',y1,dbp]    = metrics_dict[runid,metric_id,'Q1HH_shareofTRA',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofTRA',y2,dbp]               = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'hhq1_2050'].sum()  / metrics_dict[runid,metric_id,'TotHH_inTRA',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofHRAonly',y1,dbp]               = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('HRA', na=False)) & (parcel_sum_df['fbpchcat'].str.contains('tra', na=False) == False), 'hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inHRAonly',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofHRAonly_normalized',y1,dbp]    = metrics_dict[runid,metric_id,'Q1HH_shareofHRAonly',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofHRAonly',y2,dbp]               = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('HRA', na=False)) & (parcel_sum_df['fbpchcat'].str.contains('tra', na=False) == False), 'hhq1_2050'].sum()  / metrics_dict[runid,metric_id,'TotHH_inHRAonly',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofTRAonly',y1,dbp]               = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('tra', na=False)) & (parcel_sum_df['fbpchcat'].str.contains('HRA', na=False) == False), 'hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inTRAonly',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofTRAonly_normalized',y1,dbp]    = metrics_dict[runid,metric_id,'Q1HH_shareofTRAonly',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofTRAonly',y2,dbp]               = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('tra', na=False)) & (parcel_sum_df['fbpchcat'].str.contains('HRA', na=False) == False), 'hhq1_2050'].sum()  / metrics_dict[runid,metric_id,'TotHH_inTRAonly',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofHRATRA',y1,dbp]               = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('HRA', na=False)) & (parcel_sum_df['fbpchcat'].str.contains('tra', na=False)), 'hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inHRATRA',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofHRATRA_normalized',y1,dbp]    = metrics_dict[runid,metric_id,'Q1HH_shareofHRATRA',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofHRATRA',y2,dbp]               = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('HRA', na=False)) & (parcel_sum_df['fbpchcat'].str.contains('tra', na=False)), 'hhq1_2050'].sum()  / metrics_dict[runid,metric_id,'TotHH_inHRATRA',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofDRTracts',y1,dbp]                = tract_sum_df.loc[(tract_sum_df['DispRisk'] == 1), 'hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inDRTracts',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofDRTracts_normalized',y1,dbp]     = metrics_dict[runid,metric_id,'Q1HH_shareofDRTracts',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofDRTracts',y2,dbp]                = tract_sum_df.loc[(tract_sum_df['DispRisk'] == 1), 'hhq1_2050'].sum() / metrics_dict[runid,metric_id,'TotHH_inDRTracts',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofCoCTracts',y1,dbp]               = tract_sum_df.loc[(tract_sum_df['coc_flag_pba2050'] == 1), 'hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inCoCTracts',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofCoCTracts_normalized',y1,dbp]    = metrics_dict[runid,metric_id,'Q1HH_shareofCoCTracts',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofCoCTracts',y2,dbp]               = tract_sum_df.loc[(tract_sum_df['coc_flag_pba2050'] == 1), 'hhq1_2050'].sum() / metrics_dict[runid,metric_id,'TotHH_inCoCTracts',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofRoR',y1,dbp]               = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('HRA', na=False) == False) & \
                                                                                 (parcel_sum_df['fbpchcat'].str.contains('tra', na=False) == False) & \
                                                                                 (parcel_sum_df['fbpchcat'].str.contains('DIS', na=False) == False) & \
                                                                                 (parcel_sum_df['coc_flag_pba2050'] == 0), 'hhq1_2015'].sum()      / metrics_dict[runid,metric_id,'TotHH_inRoR',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofRoR_normalized',y1,dbp]    = metrics_dict[runid,metric_id,'Q1HH_shareofRoR',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofRoR',y2,dbp]               = parcel_sum_df.loc[(parcel_sum_df['fbpchcat'].str.contains('HRA', na=False) == False) & \
                                                                                 (parcel_sum_df['fbpchcat'].str.contains('tra', na=False) == False) & \
                                                                                 (parcel_sum_df['fbpchcat'].str.contains('DIS', na=False) == False) & \
                                                                                 (parcel_sum_df['coc_flag_pba2050'] == 0), 'hhq1_2050'].sum()     / metrics_dict[runid,metric_id,'TotHH_inRoR',y2,dbp]


    '''    
    print('********************D1 Diverse********************')
    print('Growth of LIHH share of population (normalize factor))',normalize_factor_Q1Q2 )
    print('LIHH Share in HRA 2050 %s' % dbp,metrics_dict[runid,metric_id,'LIHH_shareinHRA',y2,dbp] )
    print('LIHH Share in HRA 2015 %s' % dbp,metrics_dict[runid,metric_id,'LIHH_shareinHRA_normalized',y1,dbp] )
    print('LIHH Share of HRA 2050 %s' % dbp,metrics_dict[runid,metric_id,'Q1HH_shareofHRA',y2,dbp])
    print('LIHH Share of HRA 2015 %s' % dbp,metrics_dict[runid,metric_id,'Q1HH_shareofHRA_normalized',y1,dbp] )
    '''

def calculate_Diverse2_LIHH_Displacement(runid, dbp, parcel_sum_df, tract_sum_df, TRA_sum_df, normalize_factor_Q1Q2, normalize_factor_Q1, metrics_dict):

    metric_id = "D2"

    # For reference: total number of LIHH in tracts
    metrics_dict[runid,metric_id,'LIHH_inDR',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('DIS', na=False), 'hhq1_2050'].sum()
    metrics_dict[runid,metric_id,'LIHH_inDR',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('DIS', na=False), 'hhq1_2015'].sum()
    metrics_dict[runid,metric_id,'LIHH_inDR_normalized',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('DIS', na=False), 'hhq1_2015'].sum() * normalize_factor_Q1


    '''
    print('********************D2 Diverse********************')
    print('Total Number of LIHH in DR tracts in 2050',metrics_dict[runid,metric_id,'LIHH_inDR',y2,dbp] )
    print('Number of LIHH in DR tracts in 2015',metrics_dict[runid,metric_id,'LIHH_inDR',y1,dbp] )
    print('Number of LIHH in DR tracts in normalized',metrics_dict[runid,metric_id,'LIHH_inDR_normalized',y1,dbp] )
    '''

    ###### Displacement at Tract Level (for Displacement Risk Tracts and CoC Tracts and HRA Tracts)

    # Total number of DR, CoC, HRA Tracts
    metrics_dict[runid,metric_id,'Num_tracts_total',y1,dbp]      = tract_sum_df['tract_id'].nunique()
    metrics_dict[runid,metric_id,'Num_GGtracts_total',y1,dbp]    = tract_sum_df.loc[(tract_sum_df['growth_geo'] == 1), 'tract_id'].nunique()
    metrics_dict[runid,metric_id,'Num_DRtracts_total',y1,dbp]    = tract_sum_df.loc[(tract_sum_df['DispRisk'] == 1), 'tract_id'].nunique()
    metrics_dict[runid,metric_id,'Num_DRGGtracts_total',y1,dbp]  = tract_sum_df.loc[((tract_sum_df['DispRisk'] == 1) & (tract_sum_df['growth_geo'] == 1)), 'tract_id'].nunique()
    metrics_dict[runid,metric_id,'Num_CoCtracts_total',y1,dbp]   = tract_sum_df.loc[(tract_sum_df['coc_flag_pba2050'] == 1), 'tract_id'].nunique()
    metrics_dict[runid,metric_id,'Num_CoCGGtracts_total',y1,dbp] = tract_sum_df.loc[((tract_sum_df['coc_flag_pba2050'] == 1) & (tract_sum_df['growth_geo'] == 1)), 'tract_id'].nunique()
    metrics_dict[runid,metric_id,'Num_HRAtracts_total',y1,dbp]   = tract_sum_df.loc[(tract_sum_df['hra'] == 1), 'tract_id'].nunique()
    metrics_dict[runid,metric_id,'Num_HRAGGtracts_total',y1,dbp] = tract_sum_df.loc[((tract_sum_df['hra'] == 1) & (tract_sum_df['growth_geo'] == 1)), 'tract_id'].nunique()
    metrics_dict[runid,metric_id,'Num_TRAtracts_total',y1,dbp]   = tract_sum_df.loc[(tract_sum_df['tra'] == 1), 'tract_id'].nunique()
    metrics_dict[runid,metric_id,'Num_TRAGGtracts_total',y1,dbp] = tract_sum_df.loc[((tract_sum_df['tra'] == 1) & (tract_sum_df['growth_geo'] == 1)), 'tract_id'].nunique()
 

    for county in ["Alameda", "Contra Costa", "Marin", "Napa", "San Francisco", "San Mateo", "Santa Clara", "Solano", "Sonoma"]:
        metrics_dict[runid,metric_id,'Num_%s_tracts_total' % county,y1,dbp] = tract_sum_df.loc[(tract_sum_df['county'] == county), 'tract_id'].nunique()


    # Calculating share of Q1 households at tract level / we are not going to normalize this since we want to check impacts at neighborhood level
    #tract_sum_df['hhq1_pct_2015_normalized'] = tract_sum_df['hhq1_2015'] / tract_sum_df['tothh_2015'] * normalize_factor_Q1
    tract_sum_df['hhq1_pct_2050'] = tract_sum_df['hhq1_2050'] / tract_sum_df['tothh_2050']
    tract_sum_df['hhq1_pct_2015'] = tract_sum_df['hhq1_2015'] / tract_sum_df['tothh_2015']

    
    # Creating functions to check if rows of a dataframe lost hhq1 share or absolute; applied to tract_summary_df and TRA_summary_df

    def check_losthhq1_share(row,j):
        if (row['hhq1_pct_2015'] == 0): return 0
        #elif ((row['hhq1_pct_2050']/(row['hhq1_pct_2015']* normalize_factor_Q1))<j): return 1
        elif ((row['hhq1_pct_2050']/row['hhq1_pct_2015'])<j): return 1
        else: return 0

    def check_losthhq1_abs(row,j):
        if (row['hhq1_2015'] == 0): return 0
        #elif ((row['hhq1_2050']/(row['hhq1_2015']* normalize_factor_Q1))<j): return 1
        elif ((row['hhq1_2050']/row['hhq1_2015'])<j): return 1

        else: return 0


    # Calculating number of Tracts that Lost LIHH, with "lost" defined as any loss, or 10% loss

    for i in [0, 10]:

        if i == 0:
            j = 1
        else:
            j = 0.9

        # Calculating change in share of LIHH at tract level to check gentrification            
        tract_sum_df['lost_hhq1_%dpct' % i] = tract_sum_df.apply (lambda row: check_losthhq1_share(row,j), axis=1)
                    #(lambda row: 1 if ((row['hhq1_pct_2050']/row['hhq1_pct_2015_normalized'])<j) else 0, axis=1)
                    #(lambda row: 1 if (row['hhq1_pct_2050'] < (row['hhq1_pct_2015']*j)) else 0, axis=1)


        # Calculating absolute change in LIHH at tract level to check true displacement
        tract_sum_df['lost_hhq1_abs_%dpct' % i] = tract_sum_df.apply (lambda row: check_losthhq1_abs(row,j), axis=1)
                    #(lambda row: 1 if (row['hhq1_2050'] < (row['hhq1_2015']*j)) else 0, axis=1)



        ###############################  Gentrification
 
         ######## Gentrification in all tracts 
        # Number or percent of all tracts that lost Q1 households as a share of total HH
        metrics_dict[runid,metric_id,'Num_tracts_lostLIHH_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[(tract_sum_df['lost_hhq1_%dpct' % i] == 1), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_tracts_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_tracts_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_tracts_total',y1,dbp] )
        print('Number of Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_tracts_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_tracts_lostLIHH_%dpct' % i,y_diff,dbp] )
                       
        ######## Gentrification in GG tracts only (using tracts, not actual GG geography)
        # Number or percent of GG tracts that lost Q1 households as a share of total HH
        metrics_dict[runid,metric_id,'Num_GGtracts_lostLIHH_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['growth_geo'] == 1) & (tract_sum_df['lost_hhq1_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_GGtracts_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_GGtracts_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_GGtracts_total',y1,dbp] )
        print('Number of GG Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_GGtracts_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of GG Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_GGtracts_lostLIHH_%dpct' % i,y_diff,dbp] )

        ######## Gentrification in Displacement Risk Tracts
        # Number or percent of DR tracts that lost Q1 households as a share of total HH
        metrics_dict[runid,metric_id,'Num_DRtracts_lostLIHH_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['DispRisk'] == 1) & (tract_sum_df['lost_hhq1_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_DRtracts_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_DRtracts_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_DRtracts_total',y1,dbp] )
        print('Number of DR Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_DRtracts_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of DR Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_DRtracts_lostLIHH_%dpct' % i,y_diff,dbp] )

        ######## Gentrification in Displacement Risk GG Tracts
        # Number or percent of DR GG tracts that lost Q1 households as a share of total HH
        metrics_dict[runid,metric_id,'Num_DRGGtracts_lostLIHH_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['DispRisk'] == 1) & (tract_sum_df['growth_geo'] == 1) & (tract_sum_df['lost_hhq1_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_DRGGtracts_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_DRGGtracts_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_DRGGtracts_total',y1,dbp] )
        print('Number of DR GG Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_DRGGtracts_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of DR GG Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_DRGGtracts_lostLIHH_%dpct' % i,y_diff,dbp] )

        ######## Gentrification in Communities of Concern
        # Number or percent of CoC tracts that lost Q1 households as a share of total HH
        metrics_dict[runid,metric_id,'Num_CoCtracts_lostLIHH_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['coc_flag_pba2050'] == 1) & (tract_sum_df['lost_hhq1_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_CoCtracts_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_CoCtracts_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_CoCtracts_total',y1,dbp] )
        print('Number of CoC Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_CoCtracts_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of CoC Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_CoCtracts_lostLIHH_%dpct' % i,y_diff,dbp] )

        ######## Gentrification in Communities of Concern GG Tracts
        # Number or percent of CoC GG tracts that lost Q1 households as a share of total HH
        metrics_dict[runid,metric_id,'Num_CoCGGtracts_lostLIHH_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['coc_flag_pba2050'] == 1) & (tract_sum_df['growth_geo'] == 1) & (tract_sum_df['lost_hhq1_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_CoCGGtracts_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_CoCGGtracts_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_CoCGGtracts_total',y1,dbp] )
        print('Number of CoC GG Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_CoCGGtracts_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of CoC GG Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_CoCGGtracts_lostLIHH_%dpct' % i,y_diff,dbp] )

        ######## Gentrification in HRAs
        # Number or percent of HRA tracts that lost Q1 households as a share of total HH
        metrics_dict[runid,metric_id,'Num_HRAtracts_lostLIHH_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['hra'] == 1) & (tract_sum_df['lost_hhq1_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_HRAtracts_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_HRAtracts_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_HRAtracts_total',y1,dbp] )
        print('Number of HRA Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_HRAtracts_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of HRA Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_HRAtracts_lostLIHH_%dpct' % i,y_diff,dbp] )

        ######## Gentrification in HRA GG tracts only
        # Number or percent of HRA GG tracts that lost Q1 households as a share of total HH
        metrics_dict[runid,metric_id,'Num_HRAGGtracts_lostLIHH_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['hra'] == 1) & (tract_sum_df['growth_geo'] == 1) & (tract_sum_df['lost_hhq1_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_HRAGGtracts_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_HRAGGtracts_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_HRAGGtracts_total',y1,dbp] )
        print('Number of HRA GG Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_HRAGGtracts_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of HRA GG Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_HRAGGtracts_lostLIHH_%dpct' % i,y_diff,dbp] )

        ######## Gentrification in TRAs
        # Number or percent of TRA tracts that lost Q1 households as a share of total HH
        metrics_dict[runid,metric_id,'Num_TRAtracts_lostLIHH_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['tra'] == 1) & (tract_sum_df['lost_hhq1_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_TRAtracts_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_TRAtracts_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_TRAtracts_total',y1,dbp] )
        print('Number of TRA Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_TRAtracts_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of TRA Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_TRAtracts_lostLIHH_%dpct' % i,y_diff,dbp] )

        ######## Gentrification in TRA GG tracts only
        # Number or percent of TRA GG tracts that lost Q1 households as a share of total HH
        metrics_dict[runid,metric_id,'Num_TRAGGtracts_lostLIHH_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['tra'] == 1) & (tract_sum_df['growth_geo'] == 1) & (tract_sum_df['lost_hhq1_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_TRAGGtracts_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_TRAGGtracts_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_TRAGGtracts_total',y1,dbp] )
        print('Number of TRA GG Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_TRAGGtracts_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of TRA GG Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_TRAGGtracts_lostLIHH_%dpct' % i,y_diff,dbp] )
   
        ######## Gentrification in counties 
        # Number or percent of county tracts that lost Q1 households as a share of total HH
        for county in ["Alameda", "Contra Costa", "Marin", "Napa", "San Francisco", "San Mateo", "Santa Clara", "Solano", "Sonoma"]:
            metrics_dict[runid,metric_id,'Num_%s_tracts_lostLIHH_%dpct' % (county, i),y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['county'] == county) & (tract_sum_df['lost_hhq1_%dpct' % i] == 1)), 'tract_id'].nunique()
            metrics_dict[runid,metric_id,'Pct_%s_tracts_lostLIHH_%dpct' % (county, i),y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_%s_tracts_lostLIHH_%dpct' % (county, i),y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_%s_tracts_total' % county,y1,dbp] )
            print('Number of %s Tracts that lost LIHH (as a share) from 2015 to 2050: ' % county,metrics_dict[runid,metric_id,'Num_%s_tracts_lostLIHH_%dpct' % (county, i),y_diff,dbp] )
            print('Pct of %s Tracts that lost LIHH (as a share) from 2015 to 2050: '% county,metrics_dict[runid,metric_id,'Pct_%s_tracts_lostLIHH_%dpct' % (county, i),y_diff,dbp] )



        ###############################  Displacement

        ######## Displacement in all tracts 
        # Number or percent of all tracts that lost Q1 households in absolute numbers
        metrics_dict[runid,metric_id,'Num_tracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[(tract_sum_df['lost_hhq1_abs_%dpct' % i] == 1), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_tracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_tracts_lostLIHH_abs_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_tracts_total',y1,dbp] )
        print('Number of Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_tracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )
        print('Pct of Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_tracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )
                
        ######## Displacement in GG tracts only (using tracts, not actual GG geography)
        # Number or percent of GG tracts that lost Q1 households in absolute numbers
        metrics_dict[runid,metric_id,'Num_GGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['growth_geo'] == 1) & (tract_sum_df['lost_hhq1_abs_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_GGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_GGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_GGtracts_total',y1,dbp] )
        print('Number of GG Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_GGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )
        print('Pct of GG Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_GGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )
                        
        ######## Displacement in Displacement Risk Tracts
        # Number or percent of DR tracts that lost Q1 households in absolute numbers
        metrics_dict[runid,metric_id,'Num_DRtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['DispRisk'] == 1) & (tract_sum_df['lost_hhq1_abs_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_DRtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_DRtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_DRtracts_total',y1,dbp] )
        print('Number of DR Tracts that lost LIHH from (in absolute numbers) 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_DRtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )
        print('Pct of DR Tracts that lost LIHH from (in absolute numbers) 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_DRtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )

        ######## Displacement in Displacement Risk GG Tracts
        # Number or percent of DR GG tracts that lost Q1 households in absolute numbers
        metrics_dict[runid,metric_id,'Num_DRGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['DispRisk'] == 1) & (tract_sum_df['growth_geo'] == 1)  & (tract_sum_df['lost_hhq1_abs_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_DRGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_DRGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_DRGGtracts_total',y1,dbp] )
        print('Number of DR GG Tracts that lost LIHH from (in absolute numbers) 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_DRGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )
        print('Pct of DR GG Tracts that lost LIHH from (in absolute numbers) 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_DRGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )

        ######## Displacement in Communities of Concern
        # Number or percent of CoC tracts that lost Q1 households in absolute numbers
        metrics_dict[runid,metric_id,'Num_CoCtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['coc_flag_pba2050'] == 1) & (tract_sum_df['lost_hhq1_abs_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_CoCtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_CoCtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_CoCtracts_total',y1,dbp] )
        print('Number of CoC Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_CoCtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )
        print('Pct of CoC Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_CoCtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )

        ######## Displacement in Communities of Concern
        # Number or percent of CoC tracts that lost Q1 households in absolute numbers
        metrics_dict[runid,metric_id,'Num_CoCGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['coc_flag_pba2050'] == 1) & (tract_sum_df['growth_geo'] == 1)  & (tract_sum_df['lost_hhq1_abs_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_CoCGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_CoCGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_CoCGGtracts_total',y1,dbp] )
        print('Number of CoC GG Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_CoCGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )
        print('Pct of CoC GG Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_CoCGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )

        ######## Displacement in HRAs
        # Number or percent of HRA tracts that lost Q1 households in absolute numbers
        metrics_dict[runid,metric_id,'Num_HRAtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['hra'] == 1) & (tract_sum_df['lost_hhq1_abs_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_HRAtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_HRAtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_HRAtracts_total',y1,dbp] )
        print('Number of HRA Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_HRAtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )
        print('Pct of HRA Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_HRAtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )

        ######## Displacement in HRA GG tracts 
        # Number or percent of HRA GG tracts that lost Q1 households in absolute numbers
        metrics_dict[runid,metric_id,'Num_HRAGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['hra'] == 1) & (tract_sum_df['growth_geo'] == 1) & (tract_sum_df['lost_hhq1_abs_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_HRAGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_HRAGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_HRAGGtracts_total',y1,dbp] )
        print('Number of HRA GG Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_HRAGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )
        print('Pct of HRA GG Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_HRAGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )

        ######## Displacement in TRAs
        # Number or percent of TRA tracts that lost Q1 households in absolute numbers
        metrics_dict[runid,metric_id,'Num_TRAtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['tra'] == 1) & (tract_sum_df['lost_hhq1_abs_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_TRAtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_TRAtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_TRAtracts_total',y1,dbp] )
        print('Number of TRA Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_TRAtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )
        print('Pct of TRA Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_TRAtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )

        ######## Displacement in TRA GG tracts 
        # Number or percent of TRA GG tracts that lost Q1 households in absolute numbers
        metrics_dict[runid,metric_id,'Num_TRAGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['tra'] == 1) & (tract_sum_df['growth_geo'] == 1) & (tract_sum_df['lost_hhq1_abs_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_TRAGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_TRAGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_TRAGGtracts_total',y1,dbp] )
        print('Number of TRA GG Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_TRAGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )
        print('Pct of TRA GG Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_TRAGGtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )

        ######## Displacement in counties 
        # Number or percent of county tracts that lost Q1 households in absolute numbers
        for county in ["Alameda", "Contra Costa", "Marin", "Napa", "San Francisco", "San Mateo", "Santa Clara", "Solano", "Sonoma"]:
            metrics_dict[runid,metric_id,'Num_%s_tracts_lostLIHH_abs_%dpct' % (county, i),y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['county'] == county) & (tract_sum_df['lost_hhq1_abs_%dpct' % i] == 1)), 'tract_id'].nunique()
            metrics_dict[runid,metric_id,'Pct_%s_tracts_lostLIHH_abs_%dpct' % (county, i),y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_%s_tracts_lostLIHH_abs_%dpct' % (county, i),y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_%s_tracts_total' % county,y1,dbp] )
            print('Number of %s Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ' % county,metrics_dict[runid,metric_id,'Num_%s_tracts_lostLIHH_abs_%dpct' % (county, i),y_diff,dbp] )
            print('Pct of %s Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: '% county,metrics_dict[runid,metric_id,'Pct_%s_tracts_lostLIHH_abs_%dpct' % (county, i),y_diff,dbp] )


    ##### Calculating displacement risk using the PBA2040 methodology
    # The analysis estimated which zones (i.e., TAZs) gained or lost lower-income households; those zones
    # that lost lower-income households over the time period would be flagged as being at risk of displacement.
    # The share of lower-income households at risk of displacement would be calculated by
    # dividing the number of lower-income households living in TAZs flagged as PDAs, TPAs, or
    # highopportunity areas with an increased risk of displacement by the total number of lower-income
    # households living in TAZs flagged as PDAs, TPAs, or high-opportunity areas in 2040

    # Calculating this first for all DR Risk/CoC/HRA tracts; and next for TRA areas  

    ######## PBA40 Displacement risk in DR Risk/CoC/HRA tracts



    # Q1 only
    #metrics_dict[runid,metric_id,'Num_LIHH_inDRCoCHRAtracts',y1,dbp] = tract_sum_df.loc[((tract_sum_df['DispRisk'] == 1)|(tract_sum_df['coc_flag_pba2050'] == 1)|\
    #                                                                                    (tract_sum_df['hra'] == 1)), 'hhq1_2015'].nunique()
    metrics_dict[runid,metric_id,'Num_LIHH_inDRCoCHRAtracts',y2,dbp] = tract_sum_df.loc[((tract_sum_df['DispRisk'] == 1)|(tract_sum_df['coc_flag_pba2050'] == 1)|\
                                                                                        (tract_sum_df['hra'] == 1)), 'hhq1_2050'].sum()
    # Total number of LIHH in HRA/CoC/DR tracts that lost hhq1
    metrics_dict[runid,metric_id,'Num_LIHH_inDRCoCHRAtracts_disp',y_diff,dbp] = tract_sum_df.loc[(((tract_sum_df['DispRisk'] == 1)|(tract_sum_df['coc_flag_pba2050'] == 1)|\
                                                                                        (tract_sum_df['hra'] == 1)) & (tract_sum_df['lost_hhq1_abs_0pct'] == 1)), 'hhq1_2050'].sum()

    metrics_dict[runid,metric_id,'DispRisk_PBA40_DRCoCHRAtracts',y_diff,dbp] = metrics_dict[runid,metric_id,'Num_LIHH_inDRCoCHRAtracts_disp',y_diff,dbp] / \
                                                                                metrics_dict[runid,metric_id,'Num_LIHH_inDRCoCHRAtracts',y2,dbp]   


    #For both Q1, Q2 - because this is how it was done in PBA40
    metrics_dict[runid,metric_id,'Num_Q1Q2HH_inDRCoCHRAtracts',y2,dbp] = tract_sum_df.loc[((tract_sum_df['DispRisk'] == 1)|(tract_sum_df['coc_flag_pba2050'] == 1)|\
                                                                                        (tract_sum_df['hra'] == 1)), 'hhq1_2050'].sum() + \
                                                                         tract_sum_df.loc[((tract_sum_df['DispRisk'] == 1)|(tract_sum_df['coc_flag_pba2050'] == 1)|\
                                                                                        (tract_sum_df['hra'] == 1)), 'hhq2_2050'].sum() 

    metrics_dict[runid,metric_id,'Num_Q1Q2HH_inDRCoCHRAtracts_disp',y_diff,dbp] = tract_sum_df.loc[(((tract_sum_df['DispRisk'] == 1)|(tract_sum_df['coc_flag_pba2050'] == 1)|\
                                                                                        (tract_sum_df['hra'] == 1)) & (tract_sum_df['lost_hhq1_abs_0pct'] == 1)), 'hhq1_2050'].sum() + \
                                                                                  tract_sum_df.loc[(((tract_sum_df['DispRisk'] == 1)|(tract_sum_df['coc_flag_pba2050'] == 1)|\
                                                                                        (tract_sum_df['hra'] == 1)) & (tract_sum_df['lost_hhq1_abs_0pct'] == 1)), 'hhq2_2050'].sum()

    metrics_dict[runid,metric_id,'DispRisk_PBA40_Q1Q2_DRCoCHRAtracts',y_diff,dbp] = metrics_dict[runid,metric_id,'Num_Q1Q2HH_inDRCoCHRAtracts_disp',y_diff,dbp] / \
                                                                                metrics_dict[runid,metric_id,'Num_Q1Q2HH_inDRCoCHRAtracts',y2,dbp]   



    tract_sum_filename = sum_outputs_filepath / f"summary_output_tract_{dbp}.csv"
    # tract_sum_df.to_csv(tract_sum_filename, header=True, sep=',', index=False)

    SD_sum_df_sum   = tract_sum_df.groupby(["SD"])["tothh_2050","tothh_2015","hhq1_2050", "hhq1_2015","hhq2_2050", "hhq2_2015",\
                                                   "lost_hhq1_0pct", "lost_hhq1_abs_0pct", "lost_hhq1_10pct", "lost_hhq1_abs_10pct",\
                                                   "DispRisk", "coc_flag_pba2050", "hra", "growth_geo"].sum().reset_index()\
                                                   .rename(columns={'lost_hhq1_0pct'     :'num_tracts_lost_hhq1_0pct',\
                                                                    'lost_hhq1_abs_0pct' :'num_tracts_lost_hhq1_abs_0pct',\
                                                                    'lost_hhq1_10pct'    :'num_tracts_lost_hhq1_10pct',\
                                                                    'lost_hhq1_abs_10pct':'num_tracts_lost_hhq1_abs_10pct',\
                                                                    'DispRisk'           :'num_tracts_disprisk',\
                                                                    'coc_flag_pba2050'   :'num_tracts_coc_flag_pba2050',\
                                                                    'hra'                :'num_tracts_hra',\
                                                                    'growth_geo'         :'num_tracts_growth_geo',})
    SD_sum_df_count = tract_sum_df.groupby(["SD"])["tract_id"].count().reset_index().rename(columns={'tract_id':'num_tracts'})
    SD_sum_df = pd.merge(left=SD_sum_df_count, right=SD_sum_df_sum, left_on="SD", right_on="SD", how="left")

    SD_sum_filename = sum_outputs_filepath / f"summary_output_superdistrict_{dbp}.csv"
    # SD_sum_df.to_csv(SD_sum_filename, header=True, sep=',', index=False)



def calculate_Healthy1_HHs_SLRprotected(runid, dbp, parcel_sum_df, metrics_dict):

    # Note - these metrics are grabbed directly from metrics_manual.xlsx
    '''
    metric_id = "H1"

    # Renaming Parcels as "Protected", "Unprotected", and "Unaffected"
    '''
    #Basic
    def label_SLR(row):
        if (row['SLR'] == 12): return 'Unprotected'
        elif (row['SLR'] == 24): return 'Unprotected'
        elif (row['SLR'] == 36): return 'Unprotected'
        elif (row['SLR'] == 100): return 'Protected'
        else: return 'Unaffected'
    parcel_sum_df['SLR_protection'] = parcel_sum_df.apply (lambda row: label_SLR(row), axis=1)
    '''
    def label_SLR(row):
        if ((row['SLR'] == 12) or (row['SLR'] == 24)  or (row['SLR'] == 36)): return 'Unprotected'
        elif row['SLR'] == 100: return 'Protected'
        else: return 'Unaffected'
    parcel_sum_df['SLR_protection'] = parcel_sum_df.apply (lambda row: label_SLR(row), axis=1)

    # Calculating protected households

    # All households
    tothh_2050_affected = parcel_sum_df.loc[(parcel_sum_df['SLR_protection'].str.contains("rotected") == True), 'tothh_2050'].sum()
    tothh_2050_protected = parcel_sum_df.loc[(parcel_sum_df['SLR_protection'].str.contains("Protected") == True), 'tothh_2050'].sum()
    tothh_2015_affected = parcel_sum_df.loc[(parcel_sum_df['SLR_protection'].str.contains("rotected") == True), 'tothh_2015'].sum()
    tothh_2015_protected = parcel_sum_df.loc[(parcel_sum_df['SLR_protection'].str.contains("Protected") == True), 'tothh_2015'].sum()

    # Q1 Households
    hhq1_2050_affected = parcel_sum_df.loc[(parcel_sum_df['SLR_protection'].str.contains("rotected") == True), 'hhq1_2050'].sum()
    hhq1_2050_protected = parcel_sum_df.loc[(parcel_sum_df['SLR_protection'].str.contains("Protected") == True), 'hhq1_2050'].sum()
    hhq1_2015_affected = parcel_sum_df.loc[(parcel_sum_df['SLR_protection'].str.contains("rotected") == True), 'hhq1_2015'].sum()
    hhq1_2015_protected = parcel_sum_df.loc[(parcel_sum_df['SLR_protection'].str.contains("Protected") == True), 'hhq1_2015'].sum()

    # CoC Households

    CoChh_2050_affected = parcel_sum_df.loc[((parcel_sum_df['SLR_protection'].str.contains("rotected") == True) & \
                                             parcel_sum_df['coc_flag_pba2050']==1), 'tothh_2050'].sum()
    CoChh_2050_protected = parcel_sum_df.loc[((parcel_sum_df['SLR_protection'].str.contains("Protected") == True) & \
                                             parcel_sum_df['coc_flag_pba2050']==1), 'tothh_2050'].sum()
    CoChh_2015_affected = parcel_sum_df.loc[((parcel_sum_df['SLR_protection'].str.contains("rotected") == True) & \
                                             parcel_sum_df['coc_flag_pba2050']==1), 'tothh_2015'].sum()
    CoChh_2015_protected = parcel_sum_df.loc[((parcel_sum_df['SLR_protection'].str.contains("Protected") == True) & \
                                             parcel_sum_df['coc_flag_pba2050']==1), 'tothh_2015'].sum()

    metrics_dict[runid,metric_id,'SLR_protected_pct_affected_tothh',y2,dbp] = tothh_2050_protected / tothh_2050_affected
    metrics_dict[runid,metric_id,'SLR_protected_pct_affected_hhq1',y2,dbp] = hhq1_2050_protected / hhq1_2050_affected
    metrics_dict[runid,metric_id,'SLR_protected_pct_affected_CoChh',y2,dbp] = CoChh_2050_protected / CoChh_2050_affected



    print('********************H1 Healthy********************')
    print('Pct of HHs affected by 3ft SLR that are protected in 2050 in %s' % dbp,metrics_dict[runid,metric_id,'SLR_protected_pct_affected_tothh',y2,dbp])
    print('Pct of Q1 HHs affected by 3ft SLR that are protected in 2050 in %s' % dbp,metrics_dict[runid,metric_id,'SLR_protected_pct_affected_hhq1',y2,dbp])
    print('Pct of CoC HHs affected by 3ft SLR that are protected in 2050 in %s' % dbp,metrics_dict[runid,metric_id,'SLR_protected_pct_affected_CoChh',y2,dbp])
    '''
    
    
def calculate_Healthy1_HHs_EQprotected(runid, dbp, parcel_sum_df, metrics_dict):

    # Note - these metrics are grabbed directly from metrics_manual.xlsx
    
    '''
    metric_id = "H1"


    # Reading building codes file, which has info at building level, on which parcels are inundated and protected

    buildings_code = pd.read_csv('C:/Users/ATapase/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/Healthy/buildings_with_eq_code.csv')
    buildings_eq = pd.merge(left=buildings_code[['building_id', 'parcel_id', 'residential_units', 'year_built', 'earthquake_code']], right=parcel_sum_df[['parcel_id','zone_id','tract_id','coc_flag_pba2050','fbpchcat','hhq1_2015','hhq1_2050','tothh_2015','tothh_2050']], left_on="parcel_id", right_on="parcel_id", how="left")
    buildings_eq = pd.merge(left=buildings_eq, right=coc_flag[['tract_id_coc','county_fips']], left_on="tract_id", right_on="tract_id_coc", how="left")
    buildings_cat = pd.read_csv('C:/Users/ATapase/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/Healthy/building_eq_categories.csv')
    buildings_eq = pd.merge(left=buildings_eq, right=buildings_cat, left_on="earthquake_code", right_on="building_eq_code", how="inner")
    buildings_eq.drop(['building_eq_code', 'tract_id_coc'], axis=1, inplace=True)
    buildings_eq['cost_retrofit_total'] = buildings_eq['residential_units'] * buildings_eq['cost_retrofit']

    # Calculated protected households in PLus

    # Number of Units retrofitted
    metrics_dict['H2_eq_num_units_retrofit'] = buildings_eq['residential_units'].sum()
    metrics_dict['H2_eq_num_CoC_units_retrofit'] = buildings_eq.loc[(buildings_eq['coc_flag_pba2050']== 1), 'residential_units'].sum()

    metrics_dict['H2_eq_total_cost_retrofit'] = buildings_eq['cost_retrofit_total'].sum()
    metrics_dict['H2_eq_CoC_cost_retrofit'] = buildings_eq.loc[(buildings_eq['coc_flag_pba2050']== 1), 'cost_retrofit_total'].sum()

    print('Total number of units retrofited',metrics_dict['H2_eq_num_units_retrofit'])
    print('CoC number of units retrofited',metrics_dict['H2_eq_num_CoC_units_retrofit'])

    print('Total cost of retrofit',metrics_dict['H2_eq_total_cost_retrofit'])
    print('CoC cost of retrofit',metrics_dict['H2_eq_CoC_cost_retrofit'])
    '''


def calculate_Healthy1_HHs_WFprotected(runid, dbp, parcel_sum_df, metrics_dict):

    # Note - these metrics are grabbed directly from metrics_manual.xlsx

    metric_id = "H1"

    '''
    # 
    '''


def calculate_Healthy1_safety(runid, year, dbp, tm_taz_input_df, safety_df, metrics_dict):

    metric_id = "H1"
    population = tm_taz_input_df.TOTPOP.sum()
    per_x_people = 100000
    print('population %d' % population)

    fatalities   = safety_df.loc[(safety_df['index']=="N_total_fatalities")     & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    fatalities_m = safety_df.loc[(safety_df['index']=="N_motorist_fatalities")  & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    fatalities_b = safety_df.loc[(safety_df['index']=="N_bike_fatalities")      & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum() 
    fatalities_p = safety_df.loc[(safety_df['index']=="N_ped_fatalities")       & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum() 
    injuries     = safety_df.loc[(safety_df['index']=="N_injuries")             & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum() 
                                                                               
    metrics_dict[runid,metric_id,'fatalities_annual_per_100Kppl_calc',year,dbp]         = float(fatalities)   / float(population / per_x_people)
    metrics_dict[runid,metric_id,'fatalities_auto_annual_per_100Kppl_calc',year,dbp]    = float(fatalities_m) / float(population / per_x_people)
    metrics_dict[runid,metric_id,'fatalities_bike_annual_per_100Kppl_calc',year,dbp]    = float(fatalities_b) / float(population / per_x_people)
    metrics_dict[runid,metric_id,'fatalities_ped_annual_per_100Kppl_calc',year,dbp]     = float(fatalities_p) / float(population / per_x_people)
    metrics_dict[runid,metric_id,'injuries_annual_per_100Kppl_calc',year,dbp]           = float(injuries)     / float(population / per_x_people)

    metrics_dict[runid,metric_id,'fatalities_annual_per_100MVMT',year,dbp]         = safety_df.loc[(safety_df['index']=="N_total_fatalities_per_100M_VMT")     & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'fatalities_auto_annual_per_100MVMT',year,dbp]    = safety_df.loc[(safety_df['index']=="N_motorist_fatalities_per_100M_VMT")  & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'fatalities_bike_annual_per_100MVMT',year,dbp]    = safety_df.loc[(safety_df['index']=="N_bike_fatalities_per_100M_VMT")      & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'fatalities_ped_annual_per_100MVMT',year,dbp]     = safety_df.loc[(safety_df['index']=="N_ped_fatalities_per_100M_VMT")       & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'injuries_annual_per_100MVMT',year,dbp]           = safety_df.loc[(safety_df['index']=="N_injuries_per_100M_VMT")             & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()

    metrics_dict[runid,metric_id,'fatalities_annual_per_100Kppl',year,dbp]         = safety_df.loc[(safety_df['index']=="N_total_fatalities_per_100K_pop")     & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'fatalities_auto_annual_per_100Kppl',year,dbp]    = safety_df.loc[(safety_df['index']=="N_motorist_fatalities_per_100K_pop")  & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'fatalities_bike_annual_per_100Kppl',year,dbp]    = safety_df.loc[(safety_df['index']=="N_bike_fatalities_per_100K_pop")      & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'fatalities_ped_annual_per_100Kppl',year,dbp]     = safety_df.loc[(safety_df['index']=="N_ped_fatalities_per_100K_pop")       & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'injuries_annual_per_100Kppl',year,dbp]           = safety_df.loc[(safety_df['index']=="N_injuries_per_100K_pop")             & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()


def calculate_Healthy1_safety_TAZ(runid, year, dbp, tm_taz_input_df, tm_vmt_metrics_df, metrics_dict):

    metric_id = "H1"

    population        = tm_taz_input_df.TOTPOP.sum()
    population_coc    = tm_taz_input_df.loc[(tm_taz_input_df['taz_coc']==1),'TOTPOP'].sum()
    population_noncoc = tm_taz_input_df.loc[(tm_taz_input_df['taz_coc']==0),'TOTPOP'].sum()
    population_hra    = tm_taz_input_df.loc[(tm_taz_input_df['taz_hra']==1),'TOTPOP'].sum()

 

    per_x_people      = 100000
    days_per_year     = 300

    metrics_dict[runid,metric_id,'fatalities_annual',year,dbp] = float(tm_vmt_metrics_df.loc[:,'Motor Vehicle Fatality'].sum() + \
                                                                           tm_vmt_metrics_df.loc[:,'Walk Fatality'].sum() + \
                                                                           tm_vmt_metrics_df.loc[:,'Bike Fatality'].sum()) * days_per_year                                                         
    metrics_dict[runid,metric_id,'injuries_annual',year,dbp]   = float(tm_vmt_metrics_df.loc[:,'Motor Vehicle Injury'].sum() + \
                                                                           tm_vmt_metrics_df.loc[:,'Walk Injury'].sum() + \
                                                                           tm_vmt_metrics_df.loc[:,'Bike Injury'].sum())  * days_per_year                                                              


    metrics_dict[runid,metric_id,'fatalities_annual_per100K',year,dbp] = float(tm_vmt_metrics_df.loc[:,'Motor Vehicle Fatality'].sum() + \
                                                                           tm_vmt_metrics_df.loc[:,'Walk Fatality'].sum() + \
                                                                           tm_vmt_metrics_df.loc[:,'Bike Fatality'].sum()) / float(population / per_x_people) * days_per_year                                                          
    metrics_dict[runid,metric_id,'injuries_annual_per100K',year,dbp]   = float(tm_vmt_metrics_df.loc[:,'Motor Vehicle Injury'].sum() + \
                                                                           tm_vmt_metrics_df.loc[:,'Walk Injury'].sum() + \
                                                                           tm_vmt_metrics_df.loc[:,'Bike Injury'].sum()) / float(population / per_x_people) * days_per_year



    metrics_dict[runid,metric_id,'fatalities_annual_per100K_nonfwy',year,dbp] = float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway"),'Motor Vehicle Fatality'].sum() + \
                                                                           tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway"),'Walk Fatality'].sum() + \
                                                                           tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway"),'Bike Fatality'].sum()) / float(population / per_x_people) * days_per_year
    metrics_dict[runid,metric_id,'injuries_annual_per100K_nonfwy',year,dbp]   = float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway"),'Motor Vehicle Injury'].sum() + \
                                                                           tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway"),'Walk Injury'].sum() + \
                                                                           tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway"),'Bike Injury'].sum()) / float(population / per_x_people) * days_per_year                                                           


    metrics_dict[runid,metric_id,'fatalities_annual_per100K_nonfwy_coc',year,dbp] =    float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==1),'Motor Vehicle Fatality'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==1),'Walk Fatality'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==1),'Bike Fatality'].sum()) / float(population_coc / per_x_people) * days_per_year     
    metrics_dict[runid,metric_id,'injuries_annual_per100K_nonfwy_coc',year,dbp]   =    float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==1),'Motor Vehicle Injury'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==1),'Walk Injury'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==1),'Bike Injury'].sum()) / float(population_coc / per_x_people) * days_per_year                                                               
  
    metrics_dict[runid,metric_id,'fatalities_annual_per100K_nonfwy_noncoc',year,dbp] = float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==0),'Motor Vehicle Fatality'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==0),'Walk Fatality'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==0),'Bike Fatality'].sum()) / float(population_noncoc / per_x_people) * days_per_year                                                              
    metrics_dict[runid,metric_id,'injuries_annual_per100K_nonfwy_noncoc',year,dbp]   = float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==0),'Motor Vehicle Injury'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==0),'Walk Injury'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==0),'Bike Injury'].sum()) / float(population_noncoc / per_x_people) * days_per_year                                                              

    metrics_dict[runid,metric_id,'fatalities_annual_per100K_nonfwy_hra',year,dbp] = float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_hra']==1),'Motor Vehicle Fatality'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_hra']==1),'Walk Fatality'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_hra']==1),'Bike Fatality'].sum()) / float(population_hra / per_x_people) * days_per_year                                                                
    metrics_dict[runid,metric_id,'injuries_annual_per100K_nonfwy_hra',year,dbp]   = float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_hra']==1),'Motor Vehicle Injury'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_hra']==1),'Walk Injury'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_hra']==1),'Bike Injury'].sum()) / float(population_hra / per_x_people) * days_per_year                                                               
    

    #VMT density per 100K people 
    metrics_dict[runid,metric_id,'VMT_per100K_nonfwy',year,dbp]         =  tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway"),'VMT'].sum()  / float(population / per_x_people)
    metrics_dict[runid,metric_id,'VMT_per100K_nonfwy_coc',year,dbp]     =  tm_vmt_metrics_df.loc[((tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==1)),'VMT'].sum()  / float(population_coc / per_x_people)
    metrics_dict[runid,metric_id,'VMT_per100K_nonfwy_noncoc',year,dbp]  =  tm_vmt_metrics_df.loc[((tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==0)),'VMT'].sum()  / float(population_noncoc / per_x_people)
    metrics_dict[runid,metric_id,'VMT_per100K_nonfwy_hra',year,dbp]     =  tm_vmt_metrics_df.loc[((tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_hra']==1)),'VMT'].sum()  / float(population_hra / per_x_people)


def calculate_Healthy2_GHGemissions(runid, year, dbp, tm_taz_input_df, tm_auto_times_df, emfac_df, metrics_dict):

    # Note - these metrics are grabbed directly from metrics_manual.xlsx
    
    '''
    metric_id = "H2"

    population        = tm_taz_input_df.TOTPOP.sum()

    tm_auto_times_df = tm_auto_times_df.sum(level='Mode')
    dailyVMT = tm_auto_times_df['Vehicle Miles'].sum() - tm_auto_times_df.loc['truck', ['Vehicle Miles']].sum()

    metrics_dict[runid,metric_id,'daily_vmt_per_capita',year,dbp] = dailyVMT / population 

    metrics_dict[runid,metric_id,'daily_vmt_per_capita',"2005","2005"] = emfac_df.loc[(emfac_df['dbp']==2005), 'VMT per capita'].sum() 
    metrics_dict[runid,metric_id,'daily_vmt_per_capita',"2035","2035"] = emfac_df.loc[(emfac_df['dbp']==2035), 'VMT per capita'].sum() 

    metrics_dict["emfac_hardcode",metric_id,'ghg_emissions_lbs_per_capita',"2005","2005"] = emfac_df.loc[(emfac_df['dbp']==2005), 'Total CO2 Emissions Per Capita (lbs)'].sum() 
    metrics_dict["emfac_hardcode",metric_id,'ghg_emissions_lbs_per_capita',"2015","2015"] = emfac_df.loc[(emfac_df['dbp']==2015), 'Total CO2 Emissions Per Capita (lbs)'].sum() 
    metrics_dict["emfac_hardcode",metric_id,'ghg_emissions_lbs_per_capita',"2035","2035"] = emfac_df.loc[(emfac_df['dbp']==2035), 'Total CO2 Emissions Per Capita (lbs)'].sum() 
    metrics_dict["emfac_hardcode",metric_id,'ghg_emissions_lbs_per_capita',"2050","Plus"] = 0

    metrics_dict["emfac_hardcode",metric_id,'ghg_emissions_nonSB375_lbs_per_capita',"2005","2005"] = emfac_df.loc[(emfac_df['dbp']==2005), 'Total CO2 Emissions Per Capita (lbs)'].sum() 
    metrics_dict["emfac_hardcode",metric_id,'ghg_emissions_nonSB375_lbs_per_capita',"2015","2015"] = emfac_df.loc[(emfac_df['dbp']==2015), 'Total CO2 Emissions Per Capita (lbs)'].sum() 
    metrics_dict["emfac_hardcode",metric_id,'ghg_emissions_nonSB375_lbs_per_capita',"2035","2035"] = emfac_df.loc[(emfac_df['dbp']==2035), 'Total CO2 Emissions Per Capita (lbs)'].sum() 
    metrics_dict["emfac_hardcode",metric_id,'ghg_emissions_nonSB375_lbs_per_capita',"2050","Plus"] = 0
    '''

def calculate_Healthy2_PM25emissions(runid, year, dbp, tm_taz_input_df, tm_vmt_metrics_df, metrics_dict):

    # Note - these metrics are grabbed directly from metrics_manual.xlsx
    
    '''
    metric_id = "H2"
    population = tm_taz_input_df.TOTPOP.sum()

    METRIC_TONS_TO_US_TONS      = 1.10231            # Metric tons to US tons
    PM25_ROADDUST               = 0.018522           # Grams of PM2.5 from road dust per vehicle mile
                                                     # Source: CARB - Section 7.  ARB Miscellaneous Processes Methodologies
                                                     #         Paved Road Dust [Revised and updated, March 2018]
                                                     #         https://www.arb.ca.gov/ei/areasrc/fullpdf/full7-9_2018.pdf
    GRAMS_TO_US_TONS            = 0.00000110231131  # Grams to US tons

    ACRES_TO_SQMILE             = 0.0015625


    metrics_dict[runid,metric_id,'PM25',year,dbp] =        tm_vmt_metrics_df.loc[:,'PM2.5_wear'].sum()*METRIC_TONS_TO_US_TONS + \
                                                           tm_vmt_metrics_df.loc[:,'PM2.5_exhaust'].sum()*METRIC_TONS_TO_US_TONS + \
                                                           tm_vmt_metrics_df.loc[:,'VMT'].sum() * PM25_ROADDUST*GRAMS_TO_US_TONS

    urbanarea          = float(tm_taz_input_df['acres_urbanized'].sum()) * ACRES_TO_SQMILE
    
    num_coc      = float(tm_taz_input_df.loc[(tm_taz_input_df['taz_coc']==1),'acres_urbanized'].count()) 
    num_noncoc      = float(tm_taz_input_df.loc[(tm_taz_input_df['taz_coc']==0),'acres_urbanized'].count()) 
    print num_coc
    print num_noncoc
  
    urbanarea_coc      = float(tm_taz_input_df.loc[(tm_taz_input_df['taz_coc']==1),'acres_urbanized'].sum()) * ACRES_TO_SQMILE    
    urbanarea_noncoc   = float(tm_taz_input_df.loc[(tm_taz_input_df['taz_coc']==0),'acres_urbanized'].sum()) * ACRES_TO_SQMILE
    print urbanarea_coc
    print urbanarea_noncoc

    urbanarea_hra      = float(tm_taz_input_df.loc[(tm_taz_input_df['taz_hra']==1),'acres_urbanized'].sum()) * ACRES_TO_SQMILE
    urbanarea_rural    = float(tm_taz_input_df.loc[(tm_taz_input_df['area_type']=="rural"),'acres_urbanized'].sum()) * ACRES_TO_SQMILE
    urbanarea_suburban = float(tm_taz_input_df.loc[(tm_taz_input_df['area_type']=="suburban"),'acres_urbanized'].sum()) * ACRES_TO_SQMILE
    urbanarea_urban    = float(tm_taz_input_df.loc[(tm_taz_input_df['area_type']=="urban"),'acres_urbanized'].sum()) * ACRES_TO_SQMILE
       
    #VMT total
    metrics_dict[runid,metric_id,'VMT',year,dbp]         =  tm_vmt_metrics_df.loc[:,'VMT'].sum() 
    metrics_dict[runid,metric_id,'VMT_fwy',year,dbp]         =  tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="freeway"),'VMT'].sum() 
    metrics_dict[runid,metric_id,'VMT_nonfwy',year,dbp]         =  tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway"),'VMT'].sum() 
    metrics_dict[runid,metric_id,'VMT_nonfwy_coc',year,dbp]     =  tm_vmt_metrics_df.loc[((tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==1)),'VMT'].sum()
    metrics_dict[runid,metric_id,'VMT_nonfwy_noncoc',year,dbp]  =  tm_vmt_metrics_df.loc[((tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==0)),'VMT'].sum()  
    metrics_dict[runid,metric_id,'VMT_nonfwy_hra',year,dbp]     =  tm_vmt_metrics_df.loc[((tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_hra']==1)),'VMT'].sum() 

    #VMT density per sq mile
    metrics_dict[runid,metric_id,'VMT_persqmi_nonfwy',year,dbp]         =  tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway"),'VMT'].sum()  / float(urbanarea)
    metrics_dict[runid,metric_id,'VMT_persqmi_nonfwy_coc',year,dbp]     =  tm_vmt_metrics_df.loc[((tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==1)),'VMT'].sum()  / float(urbanarea_coc)
    metrics_dict[runid,metric_id,'VMT_persqmi_nonfwy_noncoc',year,dbp]  =  tm_vmt_metrics_df.loc[((tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==0)),'VMT'].sum()  / float(urbanarea_noncoc)
    metrics_dict[runid,metric_id,'VMT_persqmi_nonfwy_hra',year,dbp]     =  tm_vmt_metrics_df.loc[((tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_hra']==1)),'VMT'].sum()  / float(urbanarea_hra)
    

    #PM2.5 density Tons per sq mile 
    metrics_dict[runid,metric_id,'PM25_density',year,dbp] =        float(tm_vmt_metrics_df.loc[:,'PM2.5_wear'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                   tm_vmt_metrics_df.loc[:,'PM2.5_exhaust'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                   tm_vmt_metrics_df.loc[:,'VMT'].sum() * PM25_ROADDUST*GRAMS_TO_US_TONS) / urbanarea
    
    metrics_dict[runid,metric_id,'PM25_density_coc',year,dbp] =    float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['taz_coc']==1),'PM2.5_wear'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                    tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['taz_coc']==1),'PM2.5_exhaust'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                    tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['taz_coc']==1),'VMT'].sum() * PM25_ROADDUST*GRAMS_TO_US_TONS) / urbanarea_coc
    
    metrics_dict[runid,metric_id,'PM25_density_noncoc',year,dbp] = float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['taz_coc']==0),'PM2.5_wear'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                    tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['taz_coc']==0),'PM2.5_exhaust'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                    tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['taz_coc']==0),'VMT'].sum() * PM25_ROADDUST*GRAMS_TO_US_TONS)  / urbanarea_noncoc
    metrics_dict[runid,metric_id,'PM25_density_hra',year,dbp]    = float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['taz_hra']==1),'PM2.5_wear'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                    tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['taz_hra']==1),'PM2.5_exhaust'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                    tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['taz_hra']==1),'VMT'].sum() * PM25_ROADDUST*GRAMS_TO_US_TONS) / urbanarea_hra


    metrics_dict[runid,metric_id,'PM25_density_rural',year,dbp] =    float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['area_type']=="rural"),'PM2.5_wear'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['area_type']=="rural"),'PM2.5_exhaust'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['area_type']=="rural"),'VMT'].sum() * PM25_ROADDUST*GRAMS_TO_US_TONS) /  urbanarea_rural
    metrics_dict[runid,metric_id,'PM25_density_suburban',year,dbp] = float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['area_type']=="suburban"),'PM2.5_wear'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['area_type']=="suburban"),'PM2.5_exhaust'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['area_type']=="suburban"),'VMT'].sum() * PM25_ROADDUST*GRAMS_TO_US_TONS) / urbanarea_suburban
    metrics_dict[runid,metric_id,'PM25_density_urban',year,dbp] =    float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['area_type']=="urban"),'PM2.5_wear'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['area_type']=="urban"),'PM2.5_exhaust'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['area_type']=="urban"),'VMT'].sum() * PM25_ROADDUST*GRAMS_TO_US_TONS) / urbanarea_urban
    '''

def calculate_Healthy2_commutemodeshare(runid, year, dbp, commute_mode_share_df, metrics_dict):
    
    # Note - these metrics are grabbed directly from metrics_manual.xlsx

    '''
    metric_id = "H2"
    year = int(year)                              
    
    metrics_dict[runid,metric_id,'Commute_mode_share_sov',year,dbp]          = commute_mode_share_df.loc[(commute_mode_share_df['name']=="Commute_mode_share_sov")         & (commute_mode_share_df['year']==year) & (commute_mode_share_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'Commute_mode_share_hov',year,dbp]          = commute_mode_share_df.loc[(commute_mode_share_df['name']=="Commute_mode_share_hov")         & (commute_mode_share_df['year']==year) & (commute_mode_share_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'Commute_mode_share_taxi_tnc',year,dbp]     = commute_mode_share_df.loc[(commute_mode_share_df['name']=="Commute_mode_share_taxi_tnc")    & (commute_mode_share_df['year']==year) & (commute_mode_share_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'Commute_mode_share_transit',year,dbp]      = commute_mode_share_df.loc[(commute_mode_share_df['name']=="Commute_mode_share_transit")     & (commute_mode_share_df['year']==year) & (commute_mode_share_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'Commute_mode_share_bike',year,dbp]         = commute_mode_share_df.loc[(commute_mode_share_df['name']=="Commute_mode_share_bike")        & (commute_mode_share_df['year']==year) & (commute_mode_share_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'Commute_mode_share_walk',year,dbp]         = commute_mode_share_df.loc[(commute_mode_share_df['name']=="Commute_mode_share_walk")        & (commute_mode_share_df['year']==year) & (commute_mode_share_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'Commute_mode_share_telecommute',year,dbp]  = commute_mode_share_df.loc[(commute_mode_share_df['name']=="Commute_mode_share_telecommute") & (commute_mode_share_df['year']==year) & (commute_mode_share_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    '''

def calculate_Vibrant1_JobsHousing(runid, dbp, county_sum_df, metrics_dict):
    
    metric_id = "V1"
    
    metrics_dict[runid,metric_id,'jobs_housing_ratio_region',y1,dbp] = county_sum_df['totemp_2015'].sum() / county_sum_df['tothh_2015'].sum()
    metrics_dict[runid,metric_id,'jobs_housing_ratio_region',y2,dbp] = county_sum_df['totemp_2050'].sum() / county_sum_df['tothh_2050'].sum()

    for index,row in county_sum_df.iterrows():
        metrics_dict[runid,metric_id,'jobs_housing_ratio_%s' % row['county'],y1,dbp] = row['totemp_2015'] / row['tothh_2015'] 
        metrics_dict[runid,metric_id,'jobs_housing_ratio_%s' % row['county'],y2,dbp] = row['totemp_2050'] / row['tothh_2050'] 


def calculate_Vibrant1_median_commute(runid, year, dbp, tm_commute_df, metrics_dict):
    
    metric_id = "V1"

    tm_commute_df['total_commute_miles'] = tm_commute_df['freq'] * tm_commute_df['distance']
   
    commute_dist_df = tm_commute_df[['incQ','freq','total_commute_miles']].groupby(['incQ']).sum()
        
    metrics_dict[runid,metric_id,'mean_commute_distance',year,dbp] = commute_dist_df['total_commute_miles'].sum() / commute_dist_df['freq'].sum()
    metrics_dict[runid,metric_id,'mean_commute_distance_inc1',year,dbp] = commute_dist_df['total_commute_miles'][1] / commute_dist_df['freq'][1] 
    metrics_dict[runid,metric_id,'mean_commute_distance_inc2',year,dbp] = commute_dist_df['total_commute_miles'][2] / commute_dist_df['freq'][2]
    metrics_dict[runid,metric_id,'mean_commute_distance_inc3',year,dbp] = commute_dist_df['total_commute_miles'][3] / commute_dist_df['freq'][3]
    metrics_dict[runid,metric_id,'mean_commute_distance_inc4',year,dbp] = commute_dist_df['total_commute_miles'][4] / commute_dist_df['freq'][4]


def calculate_Vibrant2_Jobs(runid, dbp, parcel_sum_df, remi_jobs_df, jobs_wagelevel_df, metrics_dict):


    metric_id = 'V2'
    print('********************V2 Vibrant********************')

    # Total Jobs Growth

    '''
    metrics_dict[runid,metric_id,'Total_jobs',y2,dbp] = parcel_sum_df['totemp_2050'].sum()
    metrics_dict[runid,metric_id,'Total_jobs',y1,dbp] = parcel_sum_df['totemp_2015'].sum()
    metrics_dict[runid,metric_id,'Total_jobs_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'Total_jobs',y2,dbp]/metrics_dict[runid,metric_id,'Total_jobs',y1,dbp] - 1
    print('Number of Jobs in 2050 %s' % dbp,metrics_dict[runid,metric_id,'Total_jobs',y2,dbp])
    print('Number of Jobs in 2015 %s' % dbp,metrics_dict[runid,metric_id,'Total_jobs',y1,dbp])
    print('Job Growth from 2015 to 2050 %s' % dbp,metrics_dict[runid,metric_id,'Total_jobs_growth',y_diff,dbp])

    # MWTEMPN jobs
    metrics_dict[runid,metric_id,'Total_MWTEMPN_jobs',y2,dbp] = parcel_sum_df['MWTEMPN_2050'].sum()
    metrics_dict[runid,metric_id,'Total_MWTEMPN_jobs',y1,dbp] = parcel_sum_df['MWTEMPN_2015'].sum()
    metrics_dict[runid,metric_id,'Total_jobs_growth_MWTEMPN',y_diff,dbp] = metrics_dict[runid,metric_id,'Total_MWTEMPN_jobs',y2,dbp]/metrics_dict[runid,metric_id,'Total_MWTEMPN_jobs',y1,dbp] - 1
    print('Number of Total MWTEMPN Jobs 2050 %s' % dbp,metrics_dict[runid,metric_id,'Total_MWTEMPN_jobs',y2,dbp])
    print('Number of Total MWTEMPN Jobs 2015 %s' % dbp,metrics_dict[runid,metric_id,'Total_MWTEMPN_jobs',y1,dbp])
    print('Job Growth Total MWTEMPN from 2015 to 2050 %s' % dbp,metrics_dict[runid,metric_id,'Total_jobs_growth_MWTEMPN',y_diff,dbp])
    '''

    # Jobs from REMI

    remi_jobs_df = pd.merge(left=remi_jobs_df, right=jobs_wagelevel_df, left_on="ind", right_on="ind", how="left")
    metrics_dict[runid,metric_id,'REMI_jobs',y2,dbp] = remi_jobs_df['2050'].sum()
    metrics_dict[runid,metric_id,'REMI_jobs',y1,dbp] = remi_jobs_df['2015'].sum()
    metrics_dict[runid,metric_id,'REMI_jobs_lowwage',y2,dbp]  = remi_jobs_df.loc[remi_jobs_df['wage_level'].str.contains('Low', na=False), '2050'].sum()
    metrics_dict[runid,metric_id,'REMI_jobs_lowwage',y1,dbp]  = remi_jobs_df.loc[remi_jobs_df['wage_level'].str.contains('Low', na=False), '2015'].sum()
    metrics_dict[runid,metric_id,'REMI_jobs_midwage',y2,dbp]  = remi_jobs_df.loc[remi_jobs_df['wage_level'].str.contains('Middle', na=False), '2050'].sum()
    metrics_dict[runid,metric_id,'REMI_jobs_midwage',y1,dbp]  = remi_jobs_df.loc[remi_jobs_df['wage_level'].str.contains('Middle', na=False), '2015'].sum()
    metrics_dict[runid,metric_id,'REMI_jobs_highwage',y2,dbp] = remi_jobs_df.loc[remi_jobs_df['wage_level'].str.contains('High', na=False), '2050'].sum()
    metrics_dict[runid,metric_id,'REMI_jobs_highwage',y1,dbp] = remi_jobs_df.loc[remi_jobs_df['wage_level'].str.contains('High', na=False), '2015'].sum()
    
    metrics_dict[runid,metric_id,'jobgrowth_overall',y_diff,dbp]  = float(metrics_dict[runid,metric_id,'REMI_jobs',y2,dbp])          / float(metrics_dict[runid,metric_id,'REMI_jobs',y1,dbp]) - 1
    metrics_dict[runid,metric_id,'jobgrowth_lowwage',y_diff,dbp]  = float(metrics_dict[runid,metric_id,'REMI_jobs_lowwage',y2,dbp])  / float(metrics_dict[runid,metric_id,'REMI_jobs_lowwage',y1,dbp]) - 1
    metrics_dict[runid,metric_id,'jobgrowth_midwage',y_diff,dbp]  = float(metrics_dict[runid,metric_id,'REMI_jobs_midwage',y2,dbp])  / float(metrics_dict[runid,metric_id,'REMI_jobs_midwage',y1,dbp]) - 1
    metrics_dict[runid,metric_id,'jobgrowth_highwage',y_diff,dbp] = float(metrics_dict[runid,metric_id,'REMI_jobs_highwage',y2,dbp]) / float(metrics_dict[runid,metric_id,'REMI_jobs_highwage',y1,dbp]) - 1
    
    metrics_dict[runid,metric_id,'jobgrowth_annualrate_lowwage',y_diff,dbp]  = (float(metrics_dict[runid,metric_id,'REMI_jobs_lowwage',y2,dbp])  / float(metrics_dict[runid,metric_id,'REMI_jobs_lowwage',y1,dbp]))  ** (1/35) - 1
    metrics_dict[runid,metric_id,'jobgrowth_annualrate_midwage',y_diff,dbp]  = (float(metrics_dict[runid,metric_id,'REMI_jobs_midwage',y2,dbp])  / float(metrics_dict[runid,metric_id,'REMI_jobs_midwage',y1,dbp]))  ** (1/35) - 1
    metrics_dict[runid,metric_id,'jobgrowth_annualrate_highwage',y_diff,dbp] = (float(metrics_dict[runid,metric_id,'REMI_jobs_highwage',y2,dbp]) / float(metrics_dict[runid,metric_id,'REMI_jobs_highwage',y1,dbp])) ** (1/35) - 1
    
    metrics_dict[runid,metric_id,'jobshare_lowwage',y2,dbp]  = float(metrics_dict[runid,metric_id,'REMI_jobs_lowwage',y2,dbp])  / float(metrics_dict[runid,metric_id,'REMI_jobs',y2,dbp])
    metrics_dict[runid,metric_id,'jobshare_lowwage',y1,dbp]  = float(metrics_dict[runid,metric_id,'REMI_jobs_lowwage',y1,dbp])  / float(metrics_dict[runid,metric_id,'REMI_jobs',y1,dbp])
    metrics_dict[runid,metric_id,'jobshare_midwage',y2,dbp]  = float(metrics_dict[runid,metric_id,'REMI_jobs_midwage',y2,dbp])  / float(metrics_dict[runid,metric_id,'REMI_jobs',y2,dbp])
    metrics_dict[runid,metric_id,'jobshare_midwage',y1,dbp]  = float(metrics_dict[runid,metric_id,'REMI_jobs_midwage',y1,dbp])  / float(metrics_dict[runid,metric_id,'REMI_jobs',y1,dbp])
    metrics_dict[runid,metric_id,'jobshare_highwage',y2,dbp] = float(metrics_dict[runid,metric_id,'REMI_jobs_highwage',y2,dbp])  / float(metrics_dict[runid,metric_id,'REMI_jobs',y2,dbp])
    metrics_dict[runid,metric_id,'jobshare_highwage',y1,dbp] = float(metrics_dict[runid,metric_id,'REMI_jobs_highwage',y1,dbp])  / float(metrics_dict[runid,metric_id,'REMI_jobs',y1,dbp])
    

    # Jobs Growth in PPAs
    metrics_dict[runid,metric_id,'PPA_jobs',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('ppa', na=False), 'totemp_2050'].sum()
    metrics_dict[runid,metric_id,'PPA_jobs',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('ppa', na=False), 'totemp_2015'].sum()
    metrics_dict[runid,metric_id,'jobgrowth_PPA',y_diff,dbp]            = float(metrics_dict[runid,metric_id,'PPA_jobs',y2,dbp])/float(metrics_dict[runid,metric_id,'PPA_jobs',y1,dbp]) - 1
    metrics_dict[runid,metric_id,'jobgrowth_annualrate_PPA',y_diff,dbp] = (float(metrics_dict[runid,metric_id,'PPA_jobs',y2,dbp]) / float(metrics_dict[runid,metric_id,'PPA_jobs',y1,dbp])) ** (1/35) - 1
    metrics_dict[runid,metric_id,'jobshare_PPA',y2,dbp] = float(metrics_dict[runid,metric_id,'PPA_jobs',y1,dbp])  / float(metrics_dict[runid,metric_id,'REMI_jobs',y1,dbp])
    metrics_dict[runid,metric_id,'jobshare_PPA',y1,dbp] = float(metrics_dict[runid,metric_id,'PPA_jobs',y1,dbp])  / float(metrics_dict[runid,metric_id,'REMI_jobs',y1,dbp])
       
    '''
    print('Number of Jobs in PPAs 2050 %s' % dbp,metrics_dict[runid,metric_id,'PPA_jobs',y2,dbp])
    print('Number of Jobs in PPAs 2015 %s' % dbp,metrics_dict[runid,metric_id,'PPA_jobs',y1,dbp])
    print('Job Growth in PPAs from 2015 to 2050 %s' % dbp,metrics_dict[runid,metric_id,'jobgrowth_PPA',y_diff,dbp])


    AGREMPN = Agriculture & Natural Resources 
    MWTEMPN = Manufacturing & Wholesale, Transportation & Utilities 
    RETEMPN = Retail 
    FPSEMPN = Financial & Leasing, Professional & Managerial Services 
    HEREMPN = Health & Educational Services 
    OTHEMPN = Construction, Government, Information 
    totemp = total employment

    # Jobs Growth MWTEMPN in PPAs (Manufacturing & Wholesale, Transportation & Utilities)

    metrics_dict[runid,metric_id,'PPA_MWTEMPN_jobs',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('ppa', na=False), 'MWTEMPN_2050'].sum()
    metrics_dict[runid,metric_id,'PPA_MWTEMPN_jobs',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('ppa', na=False), 'MWTEMPN_2015'].sum()
    metrics_dict[runid,metric_id,'jobs_growth_MWTEMPN_PPA',y_diff,dbp] = metrics_dict[runid,metric_id,'PPA_MWTEMPN_jobs',y2,dbp]/metrics_dict[runid,metric_id,'PPA_MWTEMPN_jobs',y1,dbp] - 1
    print('Number of MWTEMPN Jobs in PPAs 2050 %s' % dbp,metrics_dict[runid,metric_id,'PPA_MWTEMPN_jobs',y2,dbp])
    print('Number of MWTEMPN Jobs in PPAs 2015 %s' % dbp,metrics_dict[runid,metric_id,'PPA_MWTEMPN_jobs',y1,dbp])
    print('Job Growth MWTEMPN in PPAs from 2015 to 2050 %s' % dbp,metrics_dict[runid,metric_id,'jobs_growth_MWTEMPN_PPA',y_diff,dbp])
    '''


def calculate_travelmodel_metrics_change(list_tm_runid_blueprintonly, metrics_dict):


    for tm_runid in list_tm_runid_blueprintonly:

        year = tm_runid[:4]
        
        if "Basic" in tm_runid:
            dbp = "Basic"
        elif "Plus" in tm_runid:
            dbp = "Plus"
        #elif "PlusCrossing_01" in tm_runid:
        #    dbp = "Plus_01"  
        #elif  "PlusFixItFirst" in tm_runid:
        #    dbp = "PlusFixItFirst"
        else:
            dbp = "Unknown"

        '''
        metric_id = "A1"

        # Tolls
        metrics_dict[tm_runid,metric_id,'tolls_per_HH_change_2015',year,dbp] = metrics_dict[tm_runid,metric_id,'tolls_per_HH',year,dbp] / metrics_dict[tm_2015_runid,metric_id,'tolls_per_HH',y1,'2015']  - 1
        metrics_dict[tm_runid,metric_id,'tolls_per_HH_change_2050noproject',year,dbp] =  metrics_dict[tm_runid,metric_id,'tolls_per_HH',year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'tolls_per_HH',y2,"NoProject"] - 1
        metrics_dict[tm_runid,metric_id,'tolls_per_LIHH_change_2015',year,dbp] = metrics_dict[tm_runid,metric_id,'tolls_per_LIHH',year,dbp] / metrics_dict[tm_2015_runid,metric_id,'tolls_per_LIHH',y1,'2015']  - 1
        metrics_dict[tm_runid,metric_id,'tolls_per_LIHH_change_2050noproject',year,dbp] =  metrics_dict[tm_runid,metric_id,'tolls_per_LIHH',year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'tolls_per_LIHH',y2,"NoProject"] - 1
        metrics_dict[tm_runid,metric_id,'tolls_per_inc1HH_change_2015',year,dbp] = metrics_dict[tm_runid,metric_id,'tolls_per_inc1HH',year,dbp] / metrics_dict[tm_2015_runid,metric_id,'tolls_per_inc1HH',y1,'2015']  - 1
        metrics_dict[tm_runid,metric_id,'tolls_per_inc1HH_change_2050noproject',year,dbp] =  metrics_dict[tm_runid,metric_id,'tolls_per_inc1HH',year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'tolls_per_inc1HH',y2,"NoProject"] - 1
        # Transit Fares
        metrics_dict[tm_runid,metric_id,'fares_per_HH_change_2015',year,dbp] = metrics_dict[tm_runid,metric_id,'fares_per_HH',year,dbp] / metrics_dict[tm_2015_runid,metric_id,'fares_per_HH',y1,'2015']  - 1
        metrics_dict[tm_runid,metric_id,'fares_per_HH_change_2050noproject',year,dbp] =  metrics_dict[tm_runid,metric_id,'fares_per_HH',year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'fares_per_HH',y2,"NoProject"] - 1
        metrics_dict[tm_runid,metric_id,'fares_per_LIHH_change_2015',year,dbp] = metrics_dict[tm_runid,metric_id,'fares_per_LIHH',year,dbp] / metrics_dict[tm_2015_runid,metric_id,'fares_per_LIHH',y1,'2015']  - 1
        metrics_dict[tm_runid,metric_id,'fares_per_LIHH_change_2050noproject',year,dbp] =  metrics_dict[tm_runid,metric_id,'fares_per_LIHH',year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'fares_per_LIHH',y2,"NoProject"] - 1
        metrics_dict[tm_runid,metric_id,'fares_per_inc1HH_change_2015',year,dbp] = metrics_dict[tm_runid,metric_id,'fares_per_inc1HH',year,dbp] / metrics_dict[tm_2015_runid,metric_id,'fares_per_inc1HH',y1,'2015']  - 1
        metrics_dict[tm_runid,metric_id,'fares_per_inc1HH_change_2050noproject',year,dbp] =  metrics_dict[tm_runid,metric_id,'fares_per_inc1HH',year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'fares_per_inc1HH',y2,"NoProject"] - 1
        '''

        metric_id = "C2"

        # Highway corridor travel times
        for route in ['Antioch_SF','Vallejo_SF','SanJose_SF','Oakland_SanJose','Oakland_SF']:
            metrics_dict[tm_runid,metric_id,'travel_time_AM_change_2015_%s' % route,year,dbp] = metrics_dict[tm_runid,metric_id,'travel_time_AM_%s' % route,year,dbp] / metrics_dict[tm_2015_runid,metric_id,'travel_time_AM_%s' % route,y1,'2015']  - 1
            metrics_dict[tm_runid,metric_id,'travel_time_AM_change_2050noproject_%s' % route,year,dbp] = metrics_dict[tm_runid,metric_id,'travel_time_AM_%s' % route,year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'travel_time_AM_%s' % route,y2,'NoProject']  - 1
        

        # Transit Crowding by operator
        for operator in ['Shuttle','SFMTA LRT','SFMTA Bus','SamTrans Local','VTA Bus Local','AC Transit Local','Alameda Bus Operators','Contra Costa Bus Operators',\
                               'Solano Bus Operators','Napa Bus Operators','Sonoma Bus Operators','GGT Local','CC AV Shuttle','ReX Express','SamTrans Express','VTA Bus Express',\
                               'AC Transit Transbay','County Connection Express','GGT Express','WestCAT Express','Soltrans Express','FAST Express','VINE Express','SMART Express',\
                               'WETA','Golden Gate Ferry','Hovercraft','VTA LRT','Dumbarton GRT','Oakland/Alameda Gondola','Contra Costa Gondolas','BART','Caltrain',\
                               'Capitol Corridor','Amtrak','ACE','Dumbarton Rail','SMART', 'Valley Link','High-Speed Rail']:
            try:
                metrics_dict[tm_runid,metric_id,'crowded_pct_personhrs_AM_change_2015_%s' % operator,year,dbp] = metrics_dict[tm_runid,metric_id,'crowded_pct_personhrs_AM_%s' % operator,year,dbp] / metrics_dict[tm_2015_runid,metric_id,'crowded_pct_personhrs_AM_%s' % operator,y1,'2015']  - 1
            except:
                metrics_dict[tm_runid,metric_id,'crowded_pct_personhrs_AM_change_2015_%s' % operator,year,dbp] = 0
            try:
                metrics_dict[tm_runid,metric_id,'crowded_pct_personhrs_AM_change_2050noproject_%s' % operator,year,dbp] = metrics_dict[tm_runid,metric_id,'crowded_pct_personhrs_AM_%s' % operator,year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'crowded_pct_personhrs_AM_%s' % operator,y2,'NoProject']  - 1
            except:
                metrics_dict[tm_runid,metric_id,'crowded_pct_personhrs_AM_change_2050noproject_%s' % operator,year,dbp] = 0
        

         # Transit travel times by operator (for bus only)
        for operator in ['AC Transit Local','AC Transit Transbay','SFMTA Bus','VTA Bus Local','SamTrans Local','GGT Express','SamTrans Express', 'ReX Express']:
            metrics_dict[tm_runid,metric_id,'time_per_dist_AM_change_2015_%s' % operator,year,dbp] = metrics_dict[tm_runid,metric_id,'time_per_dist_AM_%s' % operator,year,dbp] / metrics_dict[tm_2015_runid,metric_id,'time_per_dist_AM_%s' % operator,y1,'2015']  - 1
            metrics_dict[tm_runid,metric_id,'time_per_dist_AM_change_2050noproject_%s' % operator,year,dbp] = metrics_dict[tm_runid,metric_id,'time_per_dist_AM_%s' % operator,year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'time_per_dist_AM_%s' % operator,y2,'NoProject']  - 1

         # Transit travel times by mode
        for mode_name in ['Local','Express','Ferry','Light Rail','Heavy Rail','Commuter Rail']:
            metrics_dict[tm_runid,metric_id,'time_per_dist_AM_change_2015_%s' % mode_name,year,dbp] = metrics_dict[tm_runid,metric_id,'time_per_dist_AM_%s' % mode_name,year,dbp] / metrics_dict[tm_2015_runid,metric_id,'time_per_dist_AM_%s' % mode_name,y1,'2015']  - 1
            metrics_dict[tm_runid,metric_id,'time_per_dist_AM_change_2050noproject_%s' % mode_name,year,dbp] = metrics_dict[tm_runid,metric_id,'time_per_dist_AM_%s' % mode_name,year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'time_per_dist_AM_%s' % mode_name,y2,'NoProject']  - 1


def parcel_building_output_sum(urbansim_runid):

    #################### creating parcel level df from buildings output

    building_output_2050 = pd.read_csv((urbansim_runid+'_building_data_2050.csv'))
    building_output_2015 = pd.read_csv((urbansim_runid+'_building_data_2015.csv'))

    parcel_building_output_2050 = building_output_2050[['parcel_id','residential_units','deed_restricted_units']].groupby(['parcel_id']).sum()
    parcel_building_output_2015 = building_output_2015[['parcel_id','residential_units','deed_restricted_units']].groupby(['parcel_id']).sum()
    parcel_building_output_2050 = parcel_building_output_2050.add_suffix('_2050')
    parcel_building_output_2015 = parcel_building_output_2015.add_suffix('_2015')
    return pd.merge(left=parcel_building_output_2050, right=parcel_building_output_2015, left_on="parcel_id", right_on="parcel_id", how="left")
    


def calc_pba40urbansim():


    urbansim_runid = 'C:/Users/{}/Box/Modeling and Surveys/Share Data/plan-bay-area-2040/RTP17 UrbanSim Output/r7224c/run7224'.format(os.getenv('USERNAME'))
    runid          = "plan-bay-area-2040/RTP17 UrbanSim Output/r7224c/run7224"
    dbp            = "PBA40"

    metric_id = "Overall"
    year2     = "2040"
    year1     = "2010"
    yeardiff  = "2040"

    parcel_geo_df  = pd.read_csv(parcel_geography_file)


    ################## Creating parcel summary

    hhq_list = ['hhq1','hhq2','hhq3','hhq4']
    emp_list = ['AGREMPN','MWTEMPN','RETEMPN','FPSEMPN','HEREMPN','OTHEMPN']
    
    parcel_output_2040_df = pd.read_csv((urbansim_runid+'_parcel_data_2040.csv'))
    parcel_output_2040_df['tothh'] = parcel_output_2040_df[hhq_list].sum(axis=1, skipna=True)
    parcel_output_2040_df['totemp'] = parcel_output_2040_df[emp_list].sum(axis=1, skipna=True)


    parcel_output_2010_df = pd.read_csv((urbansim_runid+'_parcel_data_2010.csv'))
    parcel_output_2010_df['tothh'] = parcel_output_2010_df[hhq_list].sum(axis=1, skipna=True)
    parcel_output_2010_df['totemp'] = parcel_output_2010_df[emp_list].sum(axis=1, skipna=True)

    # keeping essential columns / renaming columns
    parcel_output_2040_df.drop(['x','y','zoned_du','zoned_du_underbuild', 'zoned_du_underbuild_nodev', 'first_building_type_id'], axis=1, inplace=True)
    parcel_output_2010_df.drop(['x','y','zoned_du','zoned_du_underbuild', 'zoned_du_underbuild_nodev', 'first_building_type_id'], axis=1, inplace=True)
    parcel_output_2040_df = parcel_output_2040_df.add_suffix('_2040')
    parcel_output_2010_df = parcel_output_2010_df.add_suffix('_2010')

    # creating parcel summaries with 2040 and 2010 outputs, and parcel geographic categories 
    parcel_sum_df = pd.merge(left=parcel_output_2040_df, right=parcel_output_2010_df, left_on="parcel_id_2040", right_on="parcel_id_2010", how="left")
    parcel_sum_df = pd.merge(left=parcel_sum_df, right=parcel_geo_df[['fbpchcat','PARCEL_ID']], left_on="parcel_id_2040", right_on="PARCEL_ID", how="left")
    parcel_sum_df.drop(['PARCEL_ID', 'parcel_id_2010'], axis=1, inplace=True)
    parcel_sum_df = parcel_sum_df.rename(columns={'parcel_id_2040': 'parcel_id'})


    #################### Housing

    # all households
    metrics_dict[runid,metric_id,'TotHH_region',year2,dbp] = parcel_sum_df['tothh_2040'].sum()
    metrics_dict[runid,metric_id,'TotHH_region',year1,dbp] = parcel_sum_df['tothh_2010'].sum()
    metrics_dict[runid,metric_id,'TotHH_growth_region',yeardiff,dbp] = metrics_dict[runid,metric_id,'TotHH_region',year2,dbp] / metrics_dict[runid,metric_id,'TotHH_region',year1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_growth_region_number',yeardiff,dbp] = parcel_sum_df['tothh_2040'].sum() - parcel_sum_df['tothh_2010'].sum()

    # HH Growth in HRAs
    metrics_dict[runid,metric_id,'TotHH_HRA',year2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'tothh_2040'].sum() 
    metrics_dict[runid,metric_id,'TotHH_HRA',year1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'tothh_2010'].sum() 
    metrics_dict[runid,metric_id,'TotHH_HRA_growth',yeardiff,dbp] = metrics_dict[runid,metric_id,'TotHH_HRA',year2,dbp] / metrics_dict[runid,metric_id,'TotHH_HRA',year1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_HRA_shareofgrowth',yeardiff,dbp] = (metrics_dict[runid,metric_id,'TotHH_HRA',year2,dbp] - metrics_dict[runid,metric_id,'TotHH_HRA',year1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',yeardiff,dbp] 

    # HH Growth in TRAs
    metrics_dict[runid,metric_id,'TotHH_TRA',year2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'tothh_2040'].sum() 
    metrics_dict[runid,metric_id,'TotHH_TRA',year1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'tothh_2010'].sum() 
    metrics_dict[runid,metric_id,'TotHH_TRA_growth',yeardiff,dbp] = metrics_dict[runid,metric_id,'TotHH_TRA',year2,dbp] / metrics_dict[runid,metric_id,'TotHH_TRA',year1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_TRA_shareofgrowth',yeardiff,dbp] = (metrics_dict[runid,metric_id,'TotHH_TRA',year2,dbp] - metrics_dict[runid,metric_id,'TotHH_TRA',year1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',yeardiff,dbp] 


    #################### Jobs

    # all jobs
    metrics_dict[runid,metric_id,'TotJobs_region',year2,dbp] = parcel_sum_df['totemp_2040'].sum()
    metrics_dict[runid,metric_id,'TotJobs_region',year1,dbp] = parcel_sum_df['totemp_2010'].sum()
    metrics_dict[runid,metric_id,'TotJobs_growth_region',yeardiff,dbp] = metrics_dict[runid,metric_id,'TotJobs_region',year2,dbp]  / metrics_dict[runid,metric_id,'TotJobs_region',year1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_growth_region_number',yeardiff,dbp] = parcel_sum_df['totemp_2040'].sum() - parcel_sum_df['totemp_2010'].sum()

    # Job Growth in HRAs
    metrics_dict[runid,metric_id,'TotJobs_HRA',year2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'totemp_2040'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_HRA',year1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('HRA', na=False), 'totemp_2010'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_HRA_growth',yeardiff,dbp] = metrics_dict[runid,metric_id,'TotJobs_HRA',year2,dbp] / metrics_dict[runid,metric_id,'TotJobs_HRA',year1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_HRA_shareofgrowth',yeardiff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_HRA',year2,dbp] - metrics_dict[runid,metric_id,'TotJobs_HRA',year1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',yeardiff,dbp] 

    # Job Growth in TRAs
    metrics_dict[runid,metric_id,'TotJobs_TRA',year2,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'totemp_2040'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_TRA',year1,dbp] = parcel_sum_df.loc[parcel_sum_df['fbpchcat'].str.contains('tra', na=False), 'totemp_2010'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_TRA_growth',yeardiff,dbp] = metrics_dict[runid,metric_id,'TotJobs_TRA',year2,dbp] / metrics_dict[runid,metric_id,'TotJobs_TRA',year1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_TRA_shareofgrowth',yeardiff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_TRA',year2,dbp] - metrics_dict[runid,metric_id,'TotJobs_TRA',year1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',yeardiff,dbp] 



def calc_urbansim_metrics():

    parcel_geo_df               = pd.read_csv(parcel_geography_file)
    parcel_tract_crosswalk_df   = pd.read_csv(parcel_tract_crosswalk_file)
    parcel_GG_newxwalk_df       = pd.read_csv(parcel_GG_newxwalk_file)

    #parcel_PDA_xwalk_df         = pd.read_csv(parcel_PDA_xwalk_file)
    #parcel_TRA_xwalk_df         = pd.read_csv(parcel_TRA_xwalk_file)
    #parcel_GG_xwalk_df          = pd.read_csv(parcel_GG_crosswalk_file)

    tract_HRA_xwalk_df          = pd.read_csv(tract_HRA_xwalk_file)
    udp_DR_df                   = pd.read_csv(udp_file)
    coc_flag_df                 = pd.read_csv(coc_flag_file)
    #slr_basic                  = pd.read_csv(slr_basic_file)
    #slr_plus                   = pd.read_csv(slr_plus_file)
    remi_jobs_df                = pd.read_csv(remi_jobs_file)
    jobs_wagelevel_df           = pd.read_csv(jobs_wagelevel_file)

    for us_runid in list_us_runid:

        urbansim_runid = str(urbansim_run_location / us_runid)

        if "s20" in urbansim_runid:
            dbp = "NoProject"
        elif "s21" in urbansim_runid:
            dbp = "Basic"
        elif "s22" in urbansim_runid:
            dbp = "Plus"
        elif  "s23" in urbansim_runid:
            dbp = "Plus"
        elif  "s24" in urbansim_runid:
            dbp = "FBP"
        elif  "s25" in urbansim_runid:
            dbp = "NoProject"        
        elif  "s26" in urbansim_runid:
            dbp = "Alt1"              
        elif  "s28" in urbansim_runid:
            dbp = "Alt2"     
        else:
            dbp = "Unknown"

        print("######################")
        print("Starting urbansim metrics data gathering for %s..."% dbp)
        

        # Temporary forcing until we have a Plus run
        #urbansim_runid     = urbansim_run_location + 'Blueprint Basic (s21)/v1.5/run939'
        
        #################### creating parcel level df from buildings output

        #parcel_building_output_sum_df = parcel_building_output_sum(urbansim_runid)


        #################### Creating parcel summary
        print("Creating parcel summaries for %s"% dbp)

        # We want parcel data without UBI effects
        try:
            parcel_output_2050_df = pd.read_csv((urbansim_runid+'_parcel_data_2050_no_UBI.csv'))   # this is for alt1/alt2
        except:
            try: 
                parcel_output_2050_df = pd.read_csv((urbansim_runid+'_parcel_data_2050_add_AH.csv'))   # this is for no project (which does not have UBI) but had some post processing Affordable housing added
            except:
                parcel_output_2050_df = pd.read_csv((urbansim_runid+'_parcel_data_2050.csv'))     # this is for FBP, where the default outputs do not include UBI
        
        try:
            parcel_output_2035_df = pd.read_csv((urbansim_runid+'_parcel_data_2035_no_UBI.csv'))   # this is for alt1/alt2
        except:
            try: 
                parcel_output_2035_df = pd.read_csv((urbansim_runid+'_parcel_data_2035_add_AH.csv'))   # this is for no project (which does not have UBI) but had some post processing Affordable housing added
            except:
                parcel_output_2035_df = pd.read_csv((urbansim_runid+'_parcel_data_2035.csv'))     # this is for FBP, where the default outputs do not include UBI
        '''
        try:
            parcel_output_2050_df = pd.read_csv((urbansim_runid+'_parcel_data_2050_UBI.csv'))
        except:
            try: 
                parcel_output_2050_df = pd.read_csv((urbansim_runid+'_parcel_data_2050_add_AH.csv'))
            except:
                parcel_output_2050_df = pd.read_csv((urbansim_runid+'_parcel_data_2050.csv'))
        '''
        parcel_output_2015_df = pd.read_csv((urbansim_runid+'_parcel_data_2015.csv'))
        # keeping essential columns / renaming columns
        parcel_output_2050_df.drop(['x','y','geom_id','zoned_du','zoned_du_underbuild', 'zoned_du_underbuild_nodev', 'first_building_type'], axis=1, inplace=True)
        parcel_output_2015_df.drop(['x','y','geom_id','zoned_du','zoned_du_underbuild', 'zoned_du_underbuild_nodev', 'first_building_type'], axis=1, inplace=True)
        parcel_output_2050_df = parcel_output_2050_df.add_suffix('_2050')
        parcel_output_2035_df = parcel_output_2035_df.add_suffix('_2035')
        parcel_output_2015_df = parcel_output_2015_df.add_suffix('_2015')

        # creating parcel summaries with 2050 and 2015 outputs, and parcel geographic categories 
        parcel_sum_df = pd.merge(left=parcel_output_2050_df, right=parcel_output_2015_df, left_on="parcel_id_2050", right_on="parcel_id_2015", how="left")
        #parcel_sum_df = pd.merge(left=parcel_sum_df, right=parcel_building_output_sum_df, left_on="parcel_id_2050", right_on="parcel_id", how="left")
        parcel_sum_df = pd.merge(left=parcel_sum_df, right=parcel_geo_df[['fbpchcat','PARCEL_ID','juris_name_full']], left_on="parcel_id_2050", right_on="PARCEL_ID", how="left")
        #parcel_sum_df.drop(['parcel_id_2015','fbpchcat_2015'], axis=1, inplace=True)
        #parcel_sum_df = parcel_sum_df.rename(columns={'parcel_id_2050': 'parcel_id','fbpchcat_2050': 'fbpchcat'})
        try:
            parcel_sum_df.drop(['parcel_id_2015','fbpchcat_2015', 'fbpchcat_2050','PARCEL_ID' ], axis=1, inplace=True)
        except:
            parcel_sum_df.drop(['parcel_id_2015','PARCEL_ID' ], axis=1, inplace=True)
        parcel_sum_df = parcel_sum_df.rename(columns={'parcel_id_2050': 'parcel_id'})


        # creating parcel summaries with 2035 and 2015 outputs, and parcel geographic categories 
        parcel_sum_2035_df = pd.merge(left=parcel_output_2035_df, right=parcel_output_2015_df, left_on="parcel_id_2035", right_on="parcel_id_2015", how="left")
        parcel_sum_2035_df = pd.merge(left=parcel_sum_2035_df, right=parcel_geo_df[['fbpchcat','PARCEL_ID','juris_name_full']], left_on="parcel_id_2035", right_on="PARCEL_ID", how="left")
        try:
            parcel_sum_2035_df.drop(['parcel_id_2015','fbpchcat_2015', 'fbpchcat_2035','PARCEL_ID' ], axis=1, inplace=True)
        except:
            parcel_sum_2035_df.drop(['parcel_id_2015','PARCEL_ID' ], axis=1, inplace=True)
        parcel_sum_2035_df = parcel_sum_2035_df.rename(columns={'parcel_id_2035': 'parcel_id'})



        ################### Create tract summary
        print("Creating tract and county summaries for %s"% dbp)

        parcel_sum_df = pd.merge(left=parcel_sum_df, right=parcel_tract_crosswalk_df[['parcel_id','zone_id','tract_id','county']], left_on="parcel_id", right_on="parcel_id", how="left")
        tract_sum_df = parcel_sum_df.groupby(["tract_id"])["tothh_2050","tothh_2015","totemp_2050","totemp_2015","hhq1_2050", "hhq1_2015","hhq2_2050", "hhq2_2015"].sum().reset_index()

        #### Adding flags at tract level for DR, CoC and HRA
        # Adding displacement risk by tract from UDP
        tract_sum_df = pd.merge(left=tract_sum_df, right=udp_DR_df[['Tract','DispRisk']], left_on="tract_id", right_on="Tract", how="left")
        # Adding CoC flag to tract_sum_df
        tract_sum_df = pd.merge(left=tract_sum_df, right=coc_flag_df[['tract_id','coc_flag_pba2050']], left_on="tract_id", right_on="tract_id", how="left")
        # Adding HRA by tract
        tract_sum_df = pd.merge(left=tract_sum_df, right=tract_HRA_xwalk_df[['tract_id','hra','growth_geo','tra','SD','county']], left_on="tract_id", right_on="tract_id", how="left")
        # Adding CoC and HRA flag to parcel_sum_df as well, cuz, why not
        parcel_sum_df = pd.merge(left=parcel_sum_df, right=coc_flag_df[['tract_id','coc_flag_pba2050']], left_on="tract_id", right_on="tract_id", how="left")
        parcel_sum_df = pd.merge(left=parcel_sum_df, right=tract_HRA_xwalk_df[['tract_id','hra']], left_on="tract_id", right_on="tract_id", how="left")
        parcel_sum_df['hra'].fillna(0, inplace=True)
        
        ################### Create county summary
        county_sum_df = parcel_sum_df.groupby(["county"])["tothh_2050","tothh_2015","hhq1_2050", "hhq1_2015","hhq2_2050", "hhq2_2015","totemp_2050","totemp_2015"].sum().reset_index()
        county_sum_df["LIHH_share_2050"] = (county_sum_df['hhq1_2050'] + county_sum_df['hhq2_2050']) / county_sum_df['tothh_2050']
        county_sum_df["LIHH_share_2015"] = (county_sum_df['hhq1_2015'] + county_sum_df['hhq2_2015']) / county_sum_df['tothh_2015']
        county_sum_df["LIHH_growth"] = (county_sum_df['hhq1_2050'] + county_sum_df['hhq2_2050']) / (county_sum_df['hhq1_2015'] + county_sum_df['hhq2_2015']) - 1

        


        ################### Create Growth Geography summary - summaries by TRAs and PDAs
        print("Creating summary outputs for %s"% dbp)

        parcel_sum_df = pd.merge(left=parcel_sum_df, right=parcel_GG_newxwalk_df, left_on="parcel_id", right_on="PARCEL_ID", how="left")
        parcel_sum_df.drop(['PARCEL_ID'], axis=1, inplace=True)
        parcel_sum_df['juris'].fillna("other", inplace=True)
        parcel_sum_df['pda_id_pba50_fb'].fillna("non-PDA", inplace=True)

        parcel_sum_2035_df = pd.merge(left=parcel_sum_2035_df, right=parcel_GG_newxwalk_df, left_on="parcel_id", right_on="PARCEL_ID", how="left")
        parcel_sum_2035_df.drop(['PARCEL_ID'], axis=1, inplace=True)
        parcel_sum_2035_df['juris'].fillna("other", inplace=True)
        parcel_sum_2035_df['pda_id_pba50_fb'].fillna("non-PDA", inplace=True)

        parcel_sum_df['juris_tra'] = parcel_sum_df['juris'] + parcel_sum_df['fbp_tra_id']
        TRA_sum_df = parcel_sum_df.groupby(['juris_tra'])["tothh_2050","tothh_2015","totemp_2050","totemp_2015","hhq1_2050", "hhq1_2015","hhq2_2050", "hhq2_2015"].sum().reset_index()
        PDA_sum_df = parcel_sum_df.groupby(['pda_id_pba50_fb'])["tothh_2050","tothh_2015","totemp_2050","totemp_2015","hhq1_2050", "hhq1_2015","hhq2_2050", "hhq2_2015"].sum().reset_index()
        GGall_sum_df = parcel_sum_df.groupby(['juris','fbp_tra_id','fbp_tra_cat_id','fbp_hra_id','pda_id_pba50_fb'])["tothh_2050","tothh_2015","totemp_2050","totemp_2015","hhq1_2050", "hhq1_2015","hhq2_2050", "hhq2_2015"].sum().reset_index()

        parcel_sum_2035_df['juris_tra'] = parcel_sum_2035_df['juris'] + parcel_sum_2035_df['fbp_tra_id']        
        TRA_sum_2035_df = parcel_sum_2035_df.groupby(['juris_tra'])["tothh_2035","tothh_2015","totemp_2035","totemp_2015","hhq1_2035", "hhq1_2015","hhq2_2035", "hhq2_2015"].sum().reset_index()
        PDA_sum_2035_df = parcel_sum_2035_df.groupby(['pda_id_pba50_fb'])["tothh_2035","tothh_2015","totemp_2035","totemp_2015","hhq1_2035", "hhq1_2015","hhq2_2035", "hhq2_2015"].sum().reset_index()
        GGall_sum_2035_df = parcel_sum_2035_df.groupby(['juris','fbp_tra_id','fbp_tra_cat_id','fbp_hra_id','pda_id_pba50_fb'])["tothh_2035","tothh_2015","totemp_2035","totemp_2015","hhq1_2035", "hhq1_2015","hhq2_2035", "hhq2_2015"].sum().reset_index()
        
        TRA_sum_filename = sum_outputs_filepath / f"summary_output_TRA_{dbp}.csv"
        # TRA_sum_df.to_csv(TRA_sum_filename, header=True, sep=',', index=False)
        PDA_sum_filename = sum_outputs_filepath / f"summary_output_PDA_{dbp}.csv"
        # PDA_sum_df.to_csv(PDA_sum_filename, header=True, sep=',', index=False)
        GGall_sum_filename = sum_outputs_filepath / f"summary_output_GG_{dbp}.csv"
        # GGall_sum_df.to_csv(GGall_sum_filename, header=True, sep=',', index=False)

        TRA_sum_2035_filename = sum_outputs_filepath / f"summary_output_TRA_2035_{dbp}.csv"
        # TRA_sum_2035_df.to_csv(TRA_sum_2035_filename, header=True, sep=',', index=False)
        PDA_sum_2035_filename = sum_outputs_filepath / f"summary_output_PDA_2035_{dbp}.csv"
        # PDA_sum_2035_df.to_csv(PDA_sum_2035_filename, header=True, sep=',', index=False)
        GGall_sum_2035_filename = sum_outputs_filepath / f"summary_output_GG_2035_{dbp}.csv"
        # GGall_sum_2035_df.to_csv(GGall_sum_2035_filename, header=True, sep=',', index=False)


        ################### Create juris summary
        juris_sum_hra_df = parcel_sum_df.groupby(['juris_name_full','hra'])["tothh_2050","tothh_2015","hhq1_2050", "hhq1_2015"].sum().reset_index()
        juris_sum_hra_filename = sum_outputs_filepath / f"summary_output_juris_hra_{dbp}.csv"
        # juris_sum_hra_df.to_csv(juris_sum_hra_filename, header=True, sep=',', index=False)
        juris_sum_coc_df = parcel_sum_df.groupby(['juris_name_full','coc_flag_pba2050'])["tothh_2050","tothh_2015","hhq1_2050", "hhq1_2015"].sum().reset_index()
        juris_sum_coc_filename = sum_outputs_filepath / f"summary_output_juris_coc_{dbp}.csv"
        # juris_sum_coc_df.to_csv(juris_sum_coc_filename, header=True, sep=',', index=False)

        '''
        ################### Merging SLR data with parcel summary file
        #if "Basic" in dbp:
        #    parcel_sum_df = pd.merge(left=parcel_sum_df, right=slr_basic, left_on="parcel_id", right_on="ParcelID", how="left")
        #    parcel_sum_df = parcel_sum_df.rename(columns={'Basic': 'SLR'})
        #else:
        parcel_sum_df = pd.merge(left=parcel_sum_df, right=slr_plus, left_on="parcel_id", right_on="ParcelID", how="left")
        parcel_sum_df = parcel_sum_df.rename(columns={'SLR_basic': 'SLR'})
        parcel_sum_df.drop(['ParcelID'], axis=1, inplace=True)
        '''

        # Summary by zoning category and output to csv
        zoningcat_sum_df = parcel_sum_df.groupby(["county","fbpchcat"])["tothh_2050","tothh_2015","deed_restricted_units_2050","deed_restricted_units_2015",\
                                                                         "preserved_units_2050","preserved_units_2015","hhq1_2050","hhq1_2015"].sum().reset_index()

        # Creating fields for GG and GG type
        temp = zoningcat_sum_df.fbpchcat.fillna("0")
        zoningcat_sum_df['GG'] = pd.np.where(temp.str==0,"non-GG",
                                 pd.np.where(temp.str.contains("GG"), "GG", "non-GG"))
        zoningcat_sum_df['Category'] = pd.np.where(temp.str==0,"Remainder",
                                       pd.np.where((temp.str.contains("tra") & temp.str.contains("HRA")), "trahra",
                                       pd.np.where(temp.str.contains("tra"), "tra",
                                       pd.np.where(temp.str.contains("HRA"), "hra",
                                       pd.np.where(temp.str.contains("GG"), "other GG", "Remainder")))))

        zoningcat_outcomes_filename = sum_outputs_filepath / "summary_output_zoningcat.csv"
        # zoningcat_sum_df.to_csv(zoningcat_outcomes_filename, header=True, sep=',', index=False)


        normalize_factor_Q1Q2  = calculate_normalize_factor_Q1Q2(parcel_sum_df)
        normalize_factor_Q1    = calculate_normalize_factor_Q1(parcel_sum_df)
        print("normalize_factor_Q1 = %s"% normalize_factor_Q1)
        
        print("Starting urbansim metrics functions...")
        calculate_urbansim_highlevelmetrics(us_runid, dbp, parcel_sum_df, tract_sum_df, county_sum_df, metrics_dict)
        calculate_Affordable2_deed_restricted_housing(us_runid, dbp, parcel_sum_df, metrics_dict)
        calculate_Diverse1_LIHHinHRAs(us_runid, dbp, parcel_sum_df, tract_sum_df, normalize_factor_Q1Q2, normalize_factor_Q1, metrics_dict)
        calculate_Diverse2_LIHH_Displacement(us_runid, dbp, parcel_sum_df, tract_sum_df, TRA_sum_df, normalize_factor_Q1Q2, normalize_factor_Q1, metrics_dict)
        #calculate_Healthy1_HHs_SLRprotected(us_runid, dbp, parcel_sum_df, metrics_dict)
        #calculate_Healthy1_HHs_EQprotected(us_runid, dbp, parcel_sum_df, metrics_dict)
        #calculate_Healthy1_HHs_WFprotected(us_runid, dbp, parcel_sum_df, metrics_dict)
        calculate_Vibrant1_JobsHousing(us_runid, dbp, county_sum_df, metrics_dict)
        calculate_Vibrant2_Jobs(us_runid, dbp, parcel_sum_df, remi_jobs_df, jobs_wagelevel_df, metrics_dict)
        
        # Write parcel summary df to csv
        #parcel_filename = 'C:/Users/{}/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/Metrics_Outputs_FinalBlueprint/summary_output_parcel.csv'.format(os.getenv('USERNAME'))
        #parcel_sum_df.to_csv(parcel_filename, header=True, sep=',', index=False)

def calc_travelmodel_metrics():

    coc_flag_df                 = pd.read_csv(coc_flag_file)
    transit_operator_df         = pd.read_csv(transit_operator_file)
    hwy_corridor_links_df       = pd.read_csv(hwy_corridor_links_file)
    safety_df                   = pd.read_csv(safety_file)
    emfac_df                    = pd.read_csv(emfac_file)
    commute_mode_share_df       = pd.read_csv(commute_mode_share_file)
    transitproximity_df         = pd.read_csv(transitproximity_file)
    transit_asset_condition_df  = pd.read_csv(transit_asset_condition_file)
    housing_costs_df            = pd.read_csv(housing_costs_file)
    taz_coc_xwalk_df            = pd.read_csv(taz_coc_crosswalk_file)
    taz_hra_xwalk_df            = pd.read_csv(taz_hra_crosswalk_file)
    taz_areatype_df             = pd.read_csv(taz_areatype_file)
    taz_urbanizedarea_df        = pd.read_csv(taz_urbanizedarea_file)

    for tm_runid in list_tm_runid:

        year = tm_runid[:4]

        if "NoProject" in tm_runid:
            dbp = "NoProject"
        elif "DBP_Plus" in tm_runid:
            dbp = "DBP"
        elif "FBP_Plus" in tm_runid:
            dbp = "Plus"
        elif "Alt1" in tm_runid:
            dbp = "Alt1"
        elif "Alt2" in tm_runid:
            dbp = "Alt2"            
        elif  "2015" in tm_runid:
            dbp = "2015"
        else:
            dbp = "Unknown"
        
        # Read relevant metrics files
        if "2015" in tm_runid: tm_run_location = tm_run_location_ipa
        else: tm_run_location = tm_run_location_bp
        tm_scen_metrics_df    = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/scenario_metrics.csv',names=["runid", "metric_name", "value"])
        tm_auto_owned_df      = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/autos_owned.csv')
        tm_auto_times_df      = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/auto_times.csv',sep=",", index_col=[0,1])
        tm_travel_cost_df     = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/core_summaries/TravelCost.csv')
        tm_parking_cost_df    = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/parking_costs_tour.csv')       
        tm_commute_df         = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/core_summaries/CommuteByIncomeHousehold.csv')
        tm_taz_input_df       = pd.read_csv(tm_run_location+tm_runid+'/INPUT/landuse/tazData.csv')
        
        tm_vmt_metrics_df    = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/vmt_vht_metrics_by_taz.csv')            
        #tm_vmt_metrics_df    = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/vmt_vht_metrics.csv')            
        tm_vmt_metrics_df = pd.merge(left=tm_vmt_metrics_df, right=taz_coc_xwalk_df, left_on="TAZ1454", right_on="TAZ1454", how="left")
        tm_vmt_metrics_df = pd.merge(left=tm_vmt_metrics_df, right=taz_hra_xwalk_df, left_on="TAZ1454", right_on="TAZ1454", how="left")
        tm_taz_input_df = pd.merge(left=tm_taz_input_df, right=taz_coc_xwalk_df, left_on="ZONE", right_on="TAZ1454", how="left")
        tm_taz_input_df = pd.merge(left=tm_taz_input_df, right=taz_hra_xwalk_df, left_on="ZONE", right_on="TAZ1454", how="left")
        tm_taz_input_df = pd.merge(left=tm_taz_input_df, right=taz_areatype_df, left_on="ZONE", right_on="TAZ1454", how="left")
        tm_taz_input_df = pd.merge(left=tm_taz_input_df, right=taz_urbanizedarea_df, left_on="ZONE", right_on="TAZ1454", how="left")
        
        
        print("Starting travel model functions for %s..."% dbp)
        calculate_Affordable1_HplusT_costs(tm_runid, year, dbp, tm_scen_metrics_df, tm_auto_owned_df, tm_auto_times_df, tm_travel_cost_df, tm_parking_cost_df, housing_costs_df, metrics_dict)
        print("@@@@@@@@@@@@@ A1 Done")
        calculate_Connected1_accessibility(tm_runid, year, dbp, tm_scen_metrics_df, metrics_dict)
        calculate_Connected1_proximity(tm_runid, year, dbp, transitproximity_df, metrics_dict)
        print("@@@@@@@@@@@@@ C1 Done")
        calculate_Connected2_hwy_traveltimes(tm_runid, year, dbp, hwy_corridor_links_df, metrics_dict)
        calculate_Connected2_trn_traveltimes(tm_runid, year, dbp, transit_operator_df, metrics_dict)
        calculate_Connected2_crowding(tm_runid, year, dbp, transit_operator_df, metrics_dict)
        print("@@@@@@@@@@@@@ C2 Done")
        calculate_Connected2_transit_asset_condition(tm_runid, year, dbp, transit_asset_condition_df, metrics_dict)
        calculate_Healthy1_safety(tm_runid, year, dbp, tm_taz_input_df, safety_df, metrics_dict)
        calculate_Healthy1_safety_TAZ(tm_runid, year, dbp, tm_taz_input_df, tm_vmt_metrics_df, metrics_dict)
        print("@@@@@@@@@@@@@ H1 Done")
        calculate_Healthy2_GHGemissions(tm_runid, year, dbp, tm_taz_input_df, tm_auto_times_df, emfac_df, metrics_dict)
        calculate_Healthy2_PM25emissions(tm_runid, year, dbp, tm_taz_input_df, tm_vmt_metrics_df, metrics_dict)
        calculate_Healthy2_commutemodeshare(tm_runid, year, dbp, commute_mode_share_df, metrics_dict)
        print("@@@@@@@@@@@@@ H2 Done")
        calculate_Vibrant1_median_commute(tm_runid, year, dbp, tm_commute_df, metrics_dict)
        print("@@@@@@@@@@@@@ V1 Done")
        print("@@@@@@@@@@@@@%s Done"% dbp)
    
    #calculate_travelmodel_metrics_change(list_tm_runid_blueprintonly, metrics_dict)



if __name__ == '__main__':

    #pd.set_option('display.width', 500)

    # Handle box drives in E: (e.g. for virtual machines)
    USERNAME    = os.getenv('USERNAME')
    BOX_DIR     = pathlib.Path(f"C:/Users/{USERNAME}/Box")
    if USERNAME.lower() in ['lzorn']:
        BOX_DIR = pathlib.Path("E:\Box")

    # Set location of UrbanSim inputs
    urbansim_run_location           = BOX_DIR / "Modeling and Surveys" / "Urban Modeling" / "Bay Area UrbanSim" / "PBA50" 
    us_2050_DBP_NoProject_runid     = 'EIR runs/Baseline Large (s25) runs/NP_v8_FINAL/run314'
    #us_2050_DBP_Basic_runid        = 'Blueprint Basic (s21)/v1.5/run939'
    #us_2050_DBP_runid              = 'Draft Blueprint runs/Blueprint Plus Crossing (s23)/v1.7.1- FINAL DRAFT BLUEPRINT/run98'
    us_2050_FBP_runid               = 'Final Blueprint runs/Final Blueprint (s24)/BAUS v2.25 - FINAL VERSION/run182'
    #us_2050_FBP_runid              = 'Blueprint Basic (s21)/v1.5/run939'
    us_2050_FBP_EIRAlt1_runid       = 'EIR runs/Alt1 (s26) runs/Alt1_v3_test_far_tiers_FINAL_EIR_ALT/run375'
    us_2050_FBP_EIRAlt2_runid       = 'EIR runs/Alt2 (s28) runs/Alt2_v1_FINAL_EIR_ALT/run374'
    list_us_runid = [us_2050_DBP_NoProject_runid,us_2050_FBP_runid, us_2050_FBP_EIRAlt1_runid, us_2050_FBP_EIRAlt2_runid]
    #urbansim_runid = urbansim_run_location + runid
    
    # Set location of Travel model inputs
    tm_run_location_bp                = 'M:/Application/Model One/RTP2021/Blueprint/'
    tm_run_location_ipa               = 'M:/Application/Model One/RTP2021/IncrementalProgress/'
    tm_2015_runid                     = '2015_TM152_IPA_17'
    #tm_2050_DBP_NoProject_runid      = '2050_TM152_DBP_NoProject_08'
    #tm_2050_DBP_runid                = '2050_TM152_DBP_PlusCrossing_08'
    #tm_2050_DBP_PlusFixItFirst_runid = '2050_TM152_DBP_PlusCrossing_01'
    tm_2050_FBP_NoProject_runid       = '2050_TM152_FBP_NoProject_24'
    tm_2050_FBP_runid                 = '2050_TM152_FBP_PlusCrossing_24'
    tm_2050_FBP_EIRAlt1_runid         = '2050_TM152_EIR_Alt1_06'
    tm_2050_FBP_EIRAlt2_runid         = '2050_TM152_EIR_Alt2_05'
    list_tm_runid                     = [tm_2015_runid, tm_2050_FBP_NoProject_runid, tm_2050_FBP_runid, tm_2050_FBP_EIRAlt1_runid, tm_2050_FBP_EIRAlt2_runid]
    #list_tm_runid                     = [tm_2015_runid, tm_2050_FBP_runid]
    list_tm_runid_blueprintonly       = [tm_2050_FBP_runid]

    # Set location of external inputs
    #All files are located in below folder / check sources.txt for sources
    metrics_source_folder         = BOX_DIR / "Horizon and Plan Bay Area 2050" / "Equity and Performance" / "7_Analysis" / "Metrics" / "metrics_input_files"
    parcel_geography_file         = metrics_source_folder / '2021_02_25_parcels_geography.csv'
    parcel_tract_crosswalk_file   = metrics_source_folder / 'parcel_tract_crosswalk.csv'
    parcel_GG_newxwalk_file       = metrics_source_folder / 'parcel_tra_hra_pda_fbp_20210816.csv'
    #parcel_PDA_xwalk_file         = metrics_source_folder / 'pda_id_2020.csv'
    #parcel_TRA_xwalk_file         = metrics_source_folder / 'tra_id_2020_s23.csv'
    #parcel_GG_crosswalk_file      = metrics_source_folder / 'parcel_GG_xwalk.csv'
    tract_HRA_xwalk_file          = metrics_source_folder / 'tract_hra_xwalk.csv'
    taz_coc_crosswalk_file        = metrics_source_folder / 'taz_coc_crosswalk.csv'
    taz_hra_crosswalk_file        = metrics_source_folder / 'taz_hra_crosswalk.csv'
    taz_areatype_file             = metrics_source_folder / 'taz_areatype.csv'
    taz_urbanizedarea_file        = metrics_source_folder / 'taz_urbanizedarea.csv'

    udp_file                      = metrics_source_folder / 'udp_2017results.csv'
    coc_flag_file                 = metrics_source_folder / 'COCs_ACS2018_tbl_TEMP.csv'
    # These are SLR input files into Urbansim, which has info at parcel ID level, on which parcels are inundated and protected
    #slr_basic_file                = metrics_source_folder / 'slr_parcel_inundation_basic.csv'
    #slr_plus_file                 = metrics_source_folder / 'slr_parcel_inundation_plus.csv'
    transit_operator_file         = metrics_source_folder / 'transit_system_lookup.csv'
    hwy_corridor_links_file       = metrics_source_folder / 'maj_corridors_hwy_links.csv'
    
    # Set location of intermediate metric outputs
    # These are for metrics generated by Raleigh, Bobby, James
    intermediate_metrics_source_folder  =  BOX_DIR / "Horizon and Plan Bay Area 2050" / "Equity and Performance" / "7_Analysis" / "Metrics" / \
        "Metrics_Outputs_FinalBlueprint" / "Intermediate Metrics"
    housing_costs_file            = intermediate_metrics_source_folder / 'housing_costs_share_income.csv'         # from Bobby, based on Urbansim outputs only
    transitproximity_file         = intermediate_metrics_source_folder / 'metrics_proximity.csv'                  # from Bobby, based on Urbansim outputs only
    transit_asset_condition_file  = intermediate_metrics_source_folder / 'transit_asset_condition.csv'            # from Raleigh, not based on model outputs
    safety_file                   = intermediate_metrics_source_folder / 'fatalities_injuries_export.csv'         # from Raleigh, based on Travel Model outputs 
    commute_mode_share_file       = intermediate_metrics_source_folder / 'commute_mode_share.csv'                 # from Raleigh, based on Travel Model outputs
    emfac_file                    = intermediate_metrics_source_folder / 'emfac.csv'                              # from James
    remi_jobs_file                = intermediate_metrics_source_folder / 'emp by ind11_s23.csv'                   # from Bobby, based on REMI
    jobs_wagelevel_file           = intermediate_metrics_source_folder / 'jobs_wagelevel.csv'                     # from Bobby, based on REMI

    # All summarized outputs (i.e. by TRA or PDA or tract) will be written to this folder
    sum_outputs_filepath = BOX_DIR / "Horizon and Plan Bay Area 2050" / "Equity and Performance" / "7_Analysis" / "Metrics" / "Metrics_Outputs_FinalBlueprint" / "Summary Outputs"

    '''
        # Script to create parcel_GG_crosswalk_file that is used above

        # Creating parcel / Growth Geography crosswalk file
        parcel_GG_crosswalk_file = 'M:/Data/GIS layers/Blueprint Land Use Strategies/p10_gg_idxed.csv'
        parcel_GG_crosswalk_df = pd.read_csv(parcel_GG_crosswalk_file)

        parcel_GG_crosswalk_df['PDA_ID'] = parcel_growthgeo_crosswalk_df.apply \
        (lambda row: str(row['County_ID']) + "_" + row['Jurisdiction'][0:5] + "_" + str(int(row['idx'])) \
         if (row['idx']>0) else "na", axis=1)

        parcel_GG_crosswalk_df.drop(['geom_id_s', 'ACRES', 'PDA_Change', 'County', 'County_ID','Jurisdiction', 'idx',], axis=1, inplace=True)

        parcel_GG_crosswalk_df.to_csv('C:/Users/ATapase/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/Diverse/parcel_GG_xwalk.csv', sep=',', index=False)
    '''

    # Global Inputs

    inflation_00_20 = 1.53
    inflation_18_20 = 1.04
    # Annual Auto ownership cost in 2018$
    # Source: Consumer Expenditure Survey 2018 (see Box\Horizon and Plan Bay Area 2050\Equity and Performance\7_Analysis\Metrics\Affordable\auto_ownership_costs.xlsx)
    # (includes depreciation, insurance, finance charges, license fees)
    auto_ownership_cost      = 5945
    auto_ownership_cost_inc1 = 2585
    auto_ownership_cost_inc2 = 4224


    metrics_dict = OrderedDict()
    y1        = "2015"
    y2        = "2050"
    y_diff    = "2050"

    # Calculate all metrics

    # Commenting out UrbanSim metrics since those will live in an UrbanSim (or related) repo
    # See Update BAUS metrics for PBA50+: https://app.asana.com/0/0/1206208457681299/f
    #

    print("Starting urbansim data gathering...")
    #calc_pba40urbansim()
    calc_urbansim_metrics()
    print("*****************#####################Completed urbansim_metrics#####################*******************")
    print("Starting travel model data gathering...")
    calc_travelmodel_metrics()
    print("*****************#####################Completed calc_travelmodel_metrics#####################*******************")

    # Write output
    idx = pd.MultiIndex.from_tuples(metrics_dict.keys(), names=['modelrunID','metric','name','year','blueprint'])
    metrics = pd.Series(metrics_dict, index=idx)
    metrics.name = 'value'
    # out_filename = 'C:/Users/{}/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/Metrics_Outputs_FinalBlueprint/metrics.csv'.format(os.getenv('USERNAME'))
    # write it locally for now
    out_filename = 'metrics.csv'
    metrics.to_csv(out_filename, header=True, sep=',')
    
    print("Wrote metrics.csv output")

    
