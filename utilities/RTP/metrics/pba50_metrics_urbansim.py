USAGE = """

  python pba50_metrics_urbansim.py

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

import datetime, os, sys
import numpy, pandas as pd
from collections import OrderedDict, defaultdict

def calculate_urbansim_highlevelmetrics(runid, dbp, parcel_sum_df, county_sum_df, metrics_dict):

    metric_id = "Overall"

    # all households
    metrics_dict[runid,metric_id,'tot_households_2050',y2,dbp] = parcel_sum_df['tothh_2050'].sum()
    metrics_dict[runid,metric_id,'tot_households_2015',y1,dbp] = parcel_sum_df['tothh_2015'].sum()
    metrics_dict[runid,metric_id,'hh_growth_region',y_diff,dbp] = (parcel_sum_df['tothh_2050'].sum() / parcel_sum_df['tothh_2015'].sum())
    for index,row in county_sum_df.iterrows():
        metrics_dict[runid,metric_id,'hh_growth_%s' % row['county'],y_diff,dbp] = row['tothh_growth'] 

    # LIHH
    metrics_dict[runid,metric_id,'LIHH_share_2050',y2,dbp] = (parcel_sum_df['hhq1_2050'].sum() + parcel_sum_df['hhq2_2050'].sum()) / parcel_sum_df['tothh_2050'].sum()
    metrics_dict[runid,metric_id,'LIHH_share_2015',y1,dbp] = (parcel_sum_df['hhq1_2015'].sum() + parcel_sum_df['hhq2_2050'].sum()) / parcel_sum_df['tothh_2015'].sum()
    metrics_dict[runid,metric_id,'LIHH_growth_region',y_diff,dbp] = (parcel_sum_df['hhq1_2050'].sum() + parcel_sum_df['hhq2_2050'].sum()) / (parcel_sum_df['hhq1_2015'].sum() + parcel_sum_df['hhq2_2050'].sum())
    for index,row in county_sum_df.iterrows():
        metrics_dict[runid,metric_id,'LIHH_growth_%s' % row["county"],y_diff,dbp] = row['LIHH_growth']
            
    # all jobs
    metrics_dict[runid,metric_id,'tot_jobs_2050',y2,dbp] = parcel_sum_df['totemp_2050'].sum()
    metrics_dict[runid,metric_id,'tot_jobs_2015',y1,dbp] = parcel_sum_df['totemp_2015'].sum()
    metrics_dict[runid,metric_id,'jobs_growth_region',y_diff,dbp] = (parcel_sum_df['totemp_2050'].sum() / parcel_sum_df['totemp_2015'].sum())
    for index,row in county_sum_df.iterrows():
        metrics_dict[runid,metric_id,'jobs_growth_%s' % row["county"],y_diff,dbp] = row['totemp_growth']

def calculate_normalize_factor_Q1Q2(parcel_sum_df):
    return ((parcel_sum_df['hhq1_2050'].sum() + parcel_sum_df['hhq2_2050'].sum()) / parcel_sum_df['tothh_2050'].sum()) \
                        / ((parcel_sum_df['hhq1_2015'].sum() + parcel_sum_df['hhq2_2015'].sum()) /  parcel_sum_df['tothh_2015'].sum())

def calculate_normalize_factor_Q1(parcel_sum_df):
    return (parcel_sum_df['hhq1_2050'].sum() / parcel_sum_df['tothh_2050'].sum()) \
                        / (parcel_sum_df['hhq1_2015'].sum() /  parcel_sum_df['tothh_2015'].sum())

def calculate_Affordable2_deed_restricted_housing(runid, dbp, parcel_sum_df, metrics_dict):

    metric_id = "A2"

    # totals for 2050 and 2015
    metrics_dict[runid,metric_id,'deed_restricted_total',y2,dbp] = parcel_sum_df['deed_restricted_units_2050'].sum()
    metrics_dict[runid,metric_id,'deed_restricted_total',y1,dbp] = parcel_sum_df['deed_restricted_units_2015'].sum()
    metrics_dict[runid,metric_id,'residential_units_total',y2,dbp] = parcel_sum_df['residential_units_2050'].sum()
    metrics_dict[runid,metric_id,'residential_units_total',y1,dbp] = parcel_sum_df['residential_units_2015'].sum()
    metrics_dict[runid,metric_id,'deed_restricted_HRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'deed_restricted_units_2050'].sum()
    metrics_dict[runid,metric_id,'deed_restricted_HRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'deed_restricted_units_2015'].sum()
    metrics_dict[runid,metric_id,'residential_units_HRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'residential_units_2050'].sum()
    metrics_dict[runid,metric_id,'residential_units_HRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'residential_units_2015'].sum()

    # diff between 2050 and 2015
    metrics_dict[runid,metric_id,'deed_restricted_diff',y_diff,dbp] = metrics_dict[runid,metric_id,'deed_restricted_total',y2,dbp]  - metrics_dict[runid,metric_id,'deed_restricted_total',y1,dbp] 
    metrics_dict[runid,metric_id,'residential_units_diff',y_diff,dbp] = metrics_dict[runid,metric_id,'residential_units_total',y2,dbp] - metrics_dict[runid,metric_id,'residential_units_total',y1,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_HRA_diff',y_diff,dbp] = metrics_dict[runid,metric_id,'deed_restricted_HRA',y2,dbp] - metrics_dict[runid,metric_id,'deed_restricted_HRA',y1,dbp]
    metrics_dict[runid,metric_id,'residential_units_HRA_diff',y_diff,dbp] = metrics_dict[runid,metric_id,'residential_units_HRA',y2,dbp]  - metrics_dict[runid,metric_id,'residential_units_HRA',y1,dbp]
    metrics_dict[runid,metric_id,'deed_restricted_nonHRA_diff',y_diff,dbp] = metrics_dict[runid,metric_id,'deed_restricted_diff',y_diff,dbp] - metrics_dict[runid,metric_id,'deed_restricted_HRA_diff',y_diff,dbp]
    metrics_dict[runid,metric_id,'residential_units_nonHRA_diff',y_diff,dbp] = metrics_dict[runid,metric_id,'residential_units_diff',y_diff,dbp]  - metrics_dict[runid,metric_id,'residential_units_HRA_diff',y_diff,dbp]

    # metric: deed restricted % of total units: overall, HRA and non-HRA
    metrics_dict[runid,metric_id,'deed_restricted_pct_new_units',y_diff,dbp] = metrics_dict[runid,metric_id,'deed_restricted_diff',y_diff,dbp] / metrics_dict[runid,metric_id,'residential_units_diff',y_diff,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_pct_new_units_HRA',y_diff,dbp] = metrics_dict[runid,metric_id,'deed_restricted_HRA_diff',y_diff,dbp]/metrics_dict[runid,metric_id,'residential_units_HRA_diff',y_diff,dbp]
    metrics_dict[runid,metric_id,'deed_restricted_pct_new_units_nonHRA',y_diff,dbp] = metrics_dict[runid,metric_id,'deed_restricted_nonHRA_diff',y_diff,dbp]/metrics_dict[runid,metric_id,'residential_units_nonHRA_diff',y_diff,dbp]

    print('********************A2 Affordable********************')
    print('DR pct of new units %s' % dbp,metrics_dict[runid,metric_id,'deed_restricted_pct_new_units',y_diff,dbp] )
    print('DR pct of new units in HRAs %s' % dbp,metrics_dict[runid,metric_id,'deed_restricted_pct_new_units_HRA',y_diff,dbp] )
    print('DR pct of new units outside of HRAs %s' % dbp,metrics_dict[runid,metric_id,'deed_restricted_pct_new_units_nonHRA',y_diff,dbp])

    # Forcing preservation metrics
    metrics_dict[runid,metric_id,'preservation_affordable_housing',y_diff,dbp] = 1


def calculate_Diverse1_LIHHinHRAs(runid, dbp, parcel_sum_df, tract_sum_df, GG_sum_df, normalize_factor_Q1Q2, normalize_factor_Q1, metrics_dict):

    metric_id = "D1"

    # Share of region's LIHH households that are in HRAs
    metrics_dict[runid,metric_id,'LIHH_total',y2,dbp] = parcel_sum_df['hhq1_2050'].sum() + parcel_sum_df['hhq2_2050'].sum()
    metrics_dict[runid,metric_id,'LIHH_total',y1,dbp] = parcel_sum_df['hhq1_2015'].sum() + parcel_sum_df['hhq2_2015'].sum()
    metrics_dict[runid,metric_id,'LIHH_inHRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'hhq1_2050'].sum() + parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'hhq2_2050'].sum()
    metrics_dict[runid,metric_id,'LIHH_inHRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'hhq1_2015'].sum() + parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'hhq2_2015'].sum()
    metrics_dict[runid,metric_id,'LIHH_shareinHRA',y2,dbp] = metrics_dict[runid,metric_id,'LIHH_inHRA',y2,dbp] / metrics_dict[runid,metric_id,'LIHH_total',y2,dbp]
    metrics_dict[runid,metric_id,'LIHH_shareinHRA',y1,dbp] = metrics_dict[runid,metric_id,'LIHH_inHRA',y1,dbp] / metrics_dict[runid,metric_id,'LIHH_total',y1,dbp]

    # normalizing for overall growth in LIHH
    metrics_dict[runid,metric_id,'LIHH_shareinHRA_normalized',y1,dbp] = metrics_dict[runid,metric_id,'LIHH_shareinHRA',y1,dbp] * normalize_factor_Q1Q2

    # Total number of Households
    # Total HHs in HRAs, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inHRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inHRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'tothh_2050'].sum()
    # Total HHs in DR Tracts, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inDRTracts',y1,dbp] = tract_sum_df.loc[(tract_sum_df['DispRisk'] == 1), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inDRTracts',y2,dbp] = tract_sum_df.loc[(tract_sum_df['DispRisk'] == 1), 'tothh_2050'].sum()
    # Total HHs in CoC Tracts, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inCoCTracts',y1,dbp] = tract_sum_df.loc[(tract_sum_df['coc_flag_pba2050'] == 1), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inCoCTracts',y2,dbp] = tract_sum_df.loc[(tract_sum_df['coc_flag_pba2050'] == 1), 'tothh_2050'].sum()
    # Total HHs in GGs, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inGGs',y1,dbp] = GG_sum_df['tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inGGs',y2,dbp] = GG_sum_df['tothh_2050'].sum()
    # Total HHs in Transit Rich GGs, in 2015 and 2050
    GG_TRich_sum_df = GG_sum_df[GG_sum_df['Designation']=="Transit-Rich"]
    metrics_dict[runid,metric_id,'TotHH_inTRichGGs',y1,dbp] = GG_TRich_sum_df['tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inTRichGGs',y2,dbp] = GG_TRich_sum_df['tothh_2050'].sum()


    ########### Tracking movement of Q1 households: Q1 share of Households
    # Share of Households that are Q1, within each geography type in this order:
    # Overall Region; HRAs; DR Tracts; CoCs; PDAs; TRAs

    metrics_dict[runid,metric_id,'Q1HH_shareofRegion',y1,dbp]            = parcel_sum_df['hhq1_2015'].sum()  / parcel_sum_df['tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'Q1HH_shareofRegion_normalized',y1,dbp] = parcel_sum_df['hhq1_2015'].sum()  / parcel_sum_df['tothh_2015'].sum()  * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofRegion',y2,dbp]            = parcel_sum_df['hhq1_2050'].sum()  / parcel_sum_df['tothh_2050'].sum() 

    metrics_dict[runid,metric_id,'Q1HH_shareofHRA',y1,dbp]               = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inHRA',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofHRA_normalized',y1,dbp]    = metrics_dict[runid,metric_id,'Q1HH_shareofHRA',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofHRA',y2,dbp]               = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'hhq1_2050'].sum()  / metrics_dict[runid,metric_id,'TotHH_inHRA',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofDRTracts',y1,dbp]                = tract_sum_df.loc[(tract_sum_df['DispRisk'] == 1), 'hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inDRTracts',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofDRTracts_normalized',y1,dbp]     = metrics_dict[runid,metric_id,'Q1HH_shareofDRTracts',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofDRTracts',y2,dbp]                = tract_sum_df.loc[(tract_sum_df['DispRisk'] == 1), 'hhq1_2050'].sum() / metrics_dict[runid,metric_id,'TotHH_inDRTracts',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofCoCTracts',y1,dbp]               = tract_sum_df.loc[(tract_sum_df['coc_flag_pba2050'] == 1), 'hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inCoCTracts',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofCoCTracts_normalized',y1,dbp]    = metrics_dict[runid,metric_id,'Q1HH_shareofCoCTracts',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofCoCTracts',y2,dbp]               = tract_sum_df.loc[(tract_sum_df['coc_flag_pba2050'] == 1), 'hhq1_2050'].sum() / metrics_dict[runid,metric_id,'TotHH_inCoCTracts',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofGGs',y1,dbp]                     = GG_sum_df['hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inGGs',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofGGs_normalized',y1,dbp]          = metrics_dict[runid,metric_id,'Q1HH_shareofGGs',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofGGs',y2,dbp]                     = GG_sum_df['hhq1_2050'].sum() / metrics_dict[runid,metric_id,'TotHH_inGGs',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofTRichGGs',y1,dbp]                = GG_TRich_sum_df['hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inTRichGGs',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofTRichGGs_normalized',y1,dbp]     = metrics_dict[runid,metric_id,'Q1HH_shareofTRichGGs',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofTRichGGs',y2,dbp]                = GG_TRich_sum_df['hhq1_2050'].sum() / metrics_dict[runid,metric_id,'TotHH_inTRichGGs',y2,dbp]



    '''
    print('********************D1 Diverse********************')
    print('Growth of LIHH share of population (normalize factor))',normalize_factor_Q1Q2 )
    print('LIHH Share in HRA 2050 %s' % dbp,metrics_dict[runid,metric_id,'LIHH_shareinHRA',y2,dbp] )
    print('LIHH Share in HRA 2015 %s' % dbp,metrics_dict[runid,metric_id,'LIHH_shareinHRA_normalized',y1,dbp] )
    print('LIHH Share of HRA 2050 %s' % dbp,metrics_dict[runid,metric_id,'LIHH_shareofHRA',y2,dbp])
    print('LIHH Share of HRA 2015 %s' % dbp,metrics_dict[runid,metric_id,'LIHH_shareofHRA_normalized',y1,dbp] )
    '''

def calculate_Diverse2_LIHH_Displacement(runid, dbp, parcel_sum_df, tract_sum_df, GG_sum_df, normalize_factor_Q1Q2, metrics_dict):

    metric_id = "D2"


    # For reference: total number of LIHH in tracts
    metrics_dict[runid,metric_id,'LIHH_inDR',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('DR', na=False), 'hhq1_2050'].sum()
    metrics_dict[runid,metric_id,'LIHH_inDR',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('DR', na=False), 'hhq1_2015'].sum()
    metrics_dict[runid,metric_id,'LIHH_inDR_normalized',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('DR', na=False), 'hhq1_2015'].sum() * normalize_factor_Q1Q2

    print('********************D2 Diverse********************')
    print('Total Number of LIHH in DR tracts in 2050',metrics_dict[runid,metric_id,'LIHH_inDR',y2,dbp] )
    print('Number of LIHH in DR tracts in 2015',metrics_dict[runid,metric_id,'LIHH_inDR',y1,dbp] )
    print('Number of LIHH in DR tracts in normalized',metrics_dict[runid,metric_id,'LIHH_inDR_normalized',y1,dbp] )


    ###### Displacement at Tract Level (for Displacement Risk Tracts and CoC Tracts)

    # Total number of DR and CoC Tracts
    metrics_dict[runid,metric_id,'Num_DRtracts_total',y1,dbp] = tract_sum_df.loc[(tract_sum_df['DispRisk'] == 1), 'tract_id'].nunique()
    metrics_dict[runid,metric_id,'Num_CoCtracts_total',y1,dbp] = tract_sum_df.loc[(tract_sum_df['coc_flag_pba2050'] == 1), 'tract_id'].nunique()

    # Calculating tracts that lost Households
    tract_sum_df['hhq1_pct_2015_normalized'] = tract_sum_df['hhq1_2015'] / tract_sum_df['tothh_2015'] * normalize_factor_Q1Q2
    tract_sum_df['hhq1_pct_2050'] = tract_sum_df['hhq1_2050'] / tract_sum_df['tothh_2050']


    # Calculating number of Tracts that Lost LIHH as a proportion of total HH, with "lost" defined as any loss, or 10% loss

    for i in [0, 10]:

        if i == 0:
            j = 1
        else:
            j = 0.9
            
        tract_sum_df['lost_hhq1_%dpct' % i] = tract_sum_df.apply \
                    (lambda row: 1 if ((row['hhq1_pct_2050']/row['hhq1_pct_2015_normalized'])<j) else 0, axis=1)

        ######## Displacement from Displacement Risk Tracts

        # Number or percent of DR tracts that lost Q1 households as a proportion of total HH
        metrics_dict[runid,metric_id,'Num_DRtracts_lostLIHH_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['DispRisk'] == 1) & (tract_sum_df['lost_hhq1_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_DRtracts_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_DRtracts_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_DRtracts_total',y1,dbp] )
        print('Number of DR Tracts that lost LIHH from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_DRtracts_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of DR Tracts that lost LIHH from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_DRtracts_lostLIHH_%dpct' % i,y_diff,dbp] )


        ######## Displacement from Communities of Concern

        # Number or percent of CoC tracts that lost Q1 households as a proportion of total HH
        metrics_dict[runid,metric_id,'Num_CoCtracts_lostLIHH_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['coc_flag_pba2050'] == 1) & (tract_sum_df['lost_hhq1_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_CoCtracts_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_CoCtracts_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_CoCtracts_total',y1,dbp] )
        print('Number of CoC Tracts that lost LIHH from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_CoCtracts_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of CoC Tracts that lost LIHH from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_CoCtracts_lostLIHH_%dpct' % i,y_diff,dbp] )


    ######## Displacement from Growth Geographies

    # Calculating PDAs that lost inc1 Households
    GG_sum_df['hhq1_pct_2015'] = GG_sum_df['hhq1_2015'] / GG_sum_df['tothh_2015'] 
    GG_sum_df['hhq1_pct_2015_normalized'] = GG_sum_df['hhq1_pct_2015'] * normalize_factor_Q1Q2
    GG_sum_df['hhq1_pct_2050'] = GG_sum_df['hhq1_2050'] / GG_sum_df['tothh_2050']

    # Total number of GGs
    metrics_dict[runid,metric_id,'Num_GGs_total',y1,dbp] = GG_sum_df['PDA_ID'].nunique()
    # Total number of Transit Rich GGs
    GG_TRich_sum_df = GG_sum_df[GG_sum_df['Designation']=="Transit-Rich"]
    metrics_dict[runid,metric_id,'Num_GGs_TRich_total',y1,dbp] = GG_TRich_sum_df['PDA_ID'].nunique()

    # Calculating number of GGs that Lost LIHH as a proportion of total HH, with "lost" defined as any loss, or 10% loss
    def check_GG_losthhq1(row,j):
        if (row['hhq1_pct_2015_normalized'] == 0): return 0
        elif ((row['hhq1_pct_2050']/row['hhq1_pct_2015_normalized'])<j): return 1
        else: return 0

    for i in [0, 10]:
        if i == 0:
            j = 1
        else:
            j = 0.9
        GG_sum_df['lost_hhq1_%dpct' % i] = GG_sum_df.apply (lambda row: check_GG_losthhq1(row,j), axis=1)
        GG_TRich_sum_df['lost_hhq1_%dpct' % i] = GG_TRich_sum_df.apply (lambda row: check_GG_losthhq1(row,j), axis=1)

        # Number or percent of GGs that lost Q1 households as a proportion of total HH
        metrics_dict[runid,metric_id,'Num_GG_lostLIHH_%dpct' % i,y_diff,dbp] = GG_sum_df.loc[(GG_sum_df['lost_hhq1_%dpct' % i] == 1), 'PDA_ID'].nunique()
        metrics_dict[runid,metric_id,'Pct_GG_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_GG_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_GGs_total',y1,dbp])
        print('Number of GGs that lost LIHH from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_GG_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of GGs that lost LIHH from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_GG_lostLIHH_%dpct' % i,y_diff,dbp] )

        # Number or percent of Transit Rich GGs that lost Q1 households as a proportion of total HH
        metrics_dict[runid,metric_id,'Num_GG_TRich_lostLIHH_%dpct' % i,y_diff,dbp] = GG_TRich_sum_df.loc[(GG_TRich_sum_df['lost_hhq1_%dpct' % i] == 1), 'PDA_ID'].nunique()
        metrics_dict[runid,metric_id,'Pct_GG_TRich_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_GG_TRich_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_GGs_TRich_total',y1,dbp])
        print('Number of Transit Rich GGs that lost LIHH from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_GG_TRich_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of Transit Rich GGs that lost LIHH from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_GG_TRich_lostLIHH_%dpct' % i,y_diff,dbp] )


def calculate_Healthy1_HHs_SLRprotected(runid, dbp, parcel_sum_df, metrics_dict):

    metric_id = "H1"

    # Renaming Parcels as "Protected", "Unprotected", and "Unaffected"

    #Basic
    def label_SLR(row):
        if (row['SLR'] == 12): return 'Unprotected'
        elif (row['SLR'] == 24): return 'Unprotected'
        elif (row['SLR'] == 36): return 'Unprotected'
        elif (row['SLR'] == 100): return 'Protected'
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


def calculate_Healthy1_HHs_EQprotected(runid, dbp, parcel_sum_df, metrics_dict):

    metric_id = "H1"

    '''
    # Reading building codes file, which has info at building level, on which parcels are inundated and protected

    buildings_code = pd.read_csv('C:/Users/ATapase/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/Healthy/buildings_with_eq_code.csv')
    buildings_eq = pd.merge(left=buildings_code[['building_id', 'parcel_id', 'residential_units', 'year_built', 'earthquake_code']], right=parcel_sum_df[['parcel_id','zone_id','tract_id','coc_flag_pba2050','pba50chcat','hhq1_2015','hhq1_2050','tothh_2015','tothh_2050']], left_on="parcel_id", right_on="parcel_id", how="left")
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

    metric_id = "H1"

    '''
    # 
    '''

def calculate_Healthy2_HHs_WFprotected(runid, dbp, parcel_sum_df, metrics_dict):

    metric_id = "H2"
    

    '''
    # 
    '''

def calculate_Vibrant2_Jobs(runid, dbp, parcel_sum_df, metrics_dict):


    metric_id = 'V2'
    print('********************V2 Vibrant********************')

    # Total Jobs Growth

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


    # Jobs Growth in PPAs

    metrics_dict[runid,metric_id,'PPA_jobs',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('ppa', na=False), 'totemp_2050'].sum()
    metrics_dict[runid,metric_id,'PPA_jobs',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('ppa', na=False), 'totemp_2015'].sum()
    metrics_dict[runid,metric_id,'jobs_growth_PPA',y_diff,dbp] = metrics_dict[runid,metric_id,'PPA_jobs',y2,dbp]/metrics_dict[runid,metric_id,'PPA_jobs',y1,dbp] - 1
    print('Number of Jobs in PPAs 2050 %s' % dbp,metrics_dict[runid,metric_id,'PPA_jobs',y2,dbp])
    print('Number of Jobs in PPAs 2015 %s' % dbp,metrics_dict[runid,metric_id,'PPA_jobs',y1,dbp])
    print('Job Growth in PPAs from 2015 to 2050 %s' % dbp,metrics_dict[runid,metric_id,'jobs_growth_PPA',y_diff,dbp])

    '''
    AGREMPN = Agriculture & Natural Resources 
    MWTEMPN = Manufacturing & Wholesale, Transportation & Utilities 
    RETEMPN = Retail 
    FPSEMPN = Financial & Leasing, Professional & Managerial Services 
    HEREMPN = Health & Educational Services 
    OTHEMPN = Construction, Government, Information 
    totemp = total employment
    '''
    # Jobs Growth MWTEMPN in PPAs (Manufacturing & Wholesale, Transportation & Utilities)

    metrics_dict[runid,metric_id,'PPA_MWTEMPN_jobs',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('ppa', na=False), 'MWTEMPN_2050'].sum()
    metrics_dict[runid,metric_id,'PPA_MWTEMPN_jobs',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('ppa', na=False), 'MWTEMPN_2015'].sum()
    metrics_dict[runid,metric_id,'jobs_growth_MWTEMPN_PPA',y_diff,dbp] = metrics_dict[runid,metric_id,'PPA_MWTEMPN_jobs',y2,dbp]/metrics_dict[runid,metric_id,'PPA_MWTEMPN_jobs',y1,dbp] - 1
    print('Number of MWTEMPN Jobs in PPAs 2050 %s' % dbp,metrics_dict[runid,metric_id,'PPA_MWTEMPN_jobs',y2,dbp])
    print('Number of MWTEMPN Jobs in PPAs 2015 %s' % dbp,metrics_dict[runid,metric_id,'PPA_MWTEMPN_jobs',y1,dbp])
    print('Job Growth MWTEMPN in PPAs from 2015 to 2050 %s' % dbp,metrics_dict[runid,metric_id,'jobs_growth_MWTEMPN_PPA',y_diff,dbp])


def parcel_building_output_sum(urbansim_runid):

    #################### creating parcel level df from buildings output

    building_output_2050 = pd.read_csv((urbansim_runid+'_building_data_2050.csv'))
    building_output_2015 = pd.read_csv((urbansim_runid+'_building_data_2010.csv'))

    parcel_building_output_2050 = building_output_2050[['parcel_id','residential_units','deed_restricted_units']].groupby(['parcel_id']).sum()
    parcel_building_output_2015 = building_output_2015[['parcel_id','residential_units','deed_restricted_units']].groupby(['parcel_id']).sum()
    parcel_building_output_2050 = parcel_building_output_2050.add_suffix('_2050')
    parcel_building_output_2015 = parcel_building_output_2015.add_suffix('_2015')
    return pd.merge(left=parcel_building_output_2050, right=parcel_building_output_2015, left_on="parcel_id", right_on="parcel_id", how="left")
    

def calc_urbansim_metrics():

    parcel_geo_df               = pd.read_csv(parcel_geography_file)
    parcel_tract_crosswalk_df  = pd.read_csv(parcel_tract_crosswalk_file)
    parcel_GG_xwalk_df          = pd.read_csv(parcel_GG_crosswalk_file)
    udp_DR_df                   = pd.read_csv(udp_file)
    coc_flag_df                 = pd.read_csv(coc_flag_file)
    slr_basic                   = pd.read_csv(slr_basic_file)
    slr_plus                    = pd.read_csv(slr_plus_file)

    for us_runid in list_us_runid:

        urbansim_runid = urbansim_run_location + us_runid

        if "s20" in urbansim_runid:
            dbp = "NoProject"
        elif "s21" in urbansim_runid:
            dbp = "Basic"
        elif "s22" in urbansim_runid:
            dbp = "Plus"
        elif  "s23" in urbansim_runid:
            dbp = "Plus"
        else:
            dbp = "Unknown"

        # Temporary forcing until we have a Plus run
        #urbansim_runid     = urbansim_run_location + 'Blueprint Basic (s21)/v1.5/run939'
        
        #################### creating parcel level df from buildings output

        parcel_building_output_sum_df = parcel_building_output_sum(urbansim_runid)


        #################### Creating parcel summary

        parcel_output_2050_df = pd.read_csv((urbansim_runid+'_parcel_data_2050.csv'))
        parcel_output_2015_df = pd.read_csv((urbansim_runid+'_parcel_data_2015.csv'))
        # keeping essential columns / renaming columns
        parcel_output_2050_df.drop(['x','y','zoned_du','zoned_du_underbuild', 'zoned_du_underbuild_nodev', 'first_building_type'], axis=1, inplace=True)
        parcel_output_2015_df.drop(['x','y','zoned_du','zoned_du_underbuild', 'zoned_du_underbuild_nodev', 'first_building_type'], axis=1, inplace=True)
        parcel_output_2050_df = parcel_output_2050_df.add_suffix('_2050')
        parcel_output_2015_df = parcel_output_2015_df.add_suffix('_2015')

        # creating parcel summaries with 2050 and 2015 outputs, and parcel geographic categories 
        parcel_sum_df = pd.merge(left=parcel_output_2050_df, right=parcel_output_2015_df, left_on="parcel_id_2050", right_on="parcel_id_2015", how="left")
        parcel_sum_df = pd.merge(left=parcel_sum_df, right=parcel_building_output_sum_df, left_on="parcel_id_2050", right_on="parcel_id", how="left")
        parcel_sum_df = pd.merge(left=parcel_sum_df, right=parcel_geo_df[['pba50chcat','PARCEL_ID']], left_on="parcel_id_2050", right_on="PARCEL_ID", how="left")
        parcel_sum_df.drop(['PARCEL_ID', 'parcel_id_2015'], axis=1, inplace=True)
        parcel_sum_df = parcel_sum_df.rename(columns={'parcel_id_2050': 'parcel_id'})


        ################### Create tract summary
        parcel_sum_df = pd.merge(left=parcel_sum_df, right=parcel_tract_crosswalk_df[['parcel_id','zone_id','tract_id','county']], left_on="parcel_id", right_on="parcel_id", how="left")
        tract_sum_df = parcel_sum_df.groupby(["tract_id"])["tothh_2050","tothh_2015","hhq1_2050", "hhq1_2015"].sum().reset_index()

        # Adding displacement risk by tract from UDP
        tract_sum_df = pd.merge(left=tract_sum_df, right=udp_DR_df[['Tract','DispRisk']], left_on="tract_id", right_on="Tract", how="left")

        # Adding county fips to tract id
        import math
        def fips_tract_coc(row):
            return row["county_fips"]*(10**(int(math.log10(row["tract"]))+1)) + row["tract"]  
        # Adding CoC flag to tract_sum_df
        coc_flag_df['tract_id_coc'] = coc_flag_df.apply (lambda row: fips_tract_coc(row), axis=1)
        tract_sum_df = pd.merge(left=tract_sum_df, right=coc_flag_df[['tract_id_coc','coc_flag_pba2050']], left_on="tract_id", right_on="tract_id_coc", how="left")

        # Adding CoC flag to parcel_sum_df
        parcel_sum_df = pd.merge(left=parcel_sum_df, right=coc_flag_df[['tract_id_coc','coc_flag_pba2050']], left_on="tract_id", right_on="tract_id_coc", how="left")
        parcel_sum_df.drop(['tract_id_coc'], axis=1, inplace=True)



        ################### Create county summary
        county_sum_df = parcel_sum_df.groupby(["county"])["tothh_2050","tothh_2015","hhq1_2050", "hhq1_2015","hhq2_2050", "hhq2_2015","totemp_2050","totemp_2015"].sum().reset_index()
        county_sum_df["tothh_growth"] = county_sum_df['tothh_2050'] / county_sum_df['tothh_2015']
        county_sum_df["totemp_growth"] = county_sum_df['totemp_2050'] / county_sum_df['totemp_2015']
        county_sum_df["LIHH_share_2050"] = (county_sum_df['hhq1_2050'] + county_sum_df['hhq2_2050']) / county_sum_df['tothh_2050']
        county_sum_df["LIHH_share_2015"] = (county_sum_df['hhq1_2015'] + county_sum_df['hhq2_2015']) / county_sum_df['tothh_2015']
        county_sum_df["LIHH_growth"] = (county_sum_df['hhq1_2050'] + county_sum_df['hhq2_2050']) / (county_sum_df['hhq1_2015'] + county_sum_df['hhq2_2015'])


        ################### Create Growth Geography summary
        parcel_sum_df = pd.merge(left=parcel_sum_df, right=parcel_GG_xwalk_df[['PARCEL_ID','PDA_ID','Designation']], left_on="parcel_id", right_on="PARCEL_ID", how="left")
        parcel_sum_df.drop(['PARCEL_ID',], axis=1, inplace=True)
        GG_sum_df = parcel_sum_df.groupby(['Designation','PDA_ID'])["tothh_2050","tothh_2015","hhq1_2050", "hhq1_2015"].sum().reset_index()
        GG_sum_df = GG_sum_df[(GG_sum_df['PDA_ID']!="na") & (GG_sum_df['Designation']!="Removed")]
        GG_type_sum_df = GG_sum_df.groupby(['Designation'])["tothh_2050","tothh_2015","hhq1_2050", "hhq1_2015"].sum().reset_index()


        # Merging SLR data with parcel summary file
        if "Basic" in dbp:
            parcel_sum_df = pd.merge(left=parcel_sum_df, right=slr_basic, left_on="parcel_id", right_on="ParcelID", how="left")
            parcel_sum_df = parcel_sum_df.rename(columns={'Basic': 'SLR'})
        else:
            parcel_sum_df = pd.merge(left=parcel_sum_df, right=slr_plus, left_on="parcel_id", right_on="ParcelID", how="left")
            parcel_sum_df = parcel_sum_df.rename(columns={'SLR_basic': 'SLR'})
        #parcel_sum_df.drop(['ParcelID_x', 'ParcelID_y'], axis=1, inplace=True)


        normalize_factor_Q1Q2  = calculate_normalize_factor_Q1Q2(parcel_sum_df)
        normalize_factor_Q1    = calculate_normalize_factor_Q1(parcel_sum_df)

        calculate_urbansim_highlevelmetrics(us_runid, dbp, parcel_sum_df, county_sum_df, metrics_dict)
        calculate_Affordable2_deed_restricted_housing(us_runid, dbp, parcel_sum_df, metrics_dict)
        calculate_Diverse1_LIHHinHRAs(us_runid, dbp, parcel_sum_df, tract_sum_df, GG_sum_df, normalize_factor_Q1Q2, normalize_factor_Q1, metrics_dict)
        calculate_Diverse2_LIHH_Displacement(us_runid, dbp, parcel_sum_df, tract_sum_df, GG_sum_df, normalize_factor_Q1Q2, metrics_dict)
        #calculate_Healthy1_HHs_SLRprotected(us_runid, dbp, parcel_sum_df, metrics_dict)
        #calculate_Healthy1_HHs_EQprotected(us_runid, dbp, parcel_sum_df, metrics_dict)
        #calculate_Healthy1_HHs_WFprotected(us_runid, dbp, parcel_sum_df, metrics_dict)
        calculate_Vibrant2_Jobs(us_runid, dbp, parcel_sum_df, metrics_dict)

if __name__ == '__main__':

    #pd.set_option('display.width', 500)


    # Set UrbanSim inputs
    urbansim_run_location = 'C:/Users/{}/Box/Modeling and Surveys/Urban Modeling/Bay Area UrbanSim 1.5/PBA50/Draft Blueprint runs/'.format(os.getenv('USERNAME'))
    #us_2050_DBP_NoProject_runid = 'Blueprint Basic (s21)/v1.5/run939'
    #us_2050_DBP_Basic_runid     = 'Blueprint Basic (s21)/v1.5/run939'
    us_2050_DBP_Plus_runid         = 'Blueprint Plus Crossing (s23)/v1.5.3/run70'
    #us_2050_DBP_Plus_runid         = 'Blueprint Basic (s21)/v1.5/run939'
    list_us_runid = [us_2050_DBP_Plus_runid]
    #urbansim_runid = urbansim_run_location + runid

      # Set external inputs
    metrics_source_folder         = 'C:/Users/{}/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/metrics_files/'.format(os.getenv('USERNAME'))
    parcel_geography_file         = metrics_source_folder + '2020_04_17_parcels_geography.csv'
    parcel_tract_crosswalk_file   = metrics_source_folder + 'parcel_tract_crosswalk.csv'
    parcel_GG_crosswalk_file      = metrics_source_folder + 'parcel_GG_xwalk.csv'
    udp_file                      = metrics_source_folder + 'udp_2017results.csv'
    coc_flag_file                 = metrics_source_folder + 'COCs_ACS2018_tbl_TEMP.csv'
    # These are SLR input files into Urbansim, which has info at parcel ID level, on which parcels are inundated and protected
    slr_basic_file                = metrics_source_folder + 'slr_parcel_inundation_basic.csv'
    slr_plus_file                 = metrics_source_folder + 'slr_parcel_inundation_plus.csv'


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

    metrics_dict = OrderedDict()
    y1        = "2015"
    y2        = "2050"
    y_diff    = "2050"

    # Calculate all metrics
    print("Starting metrics functions...")
    calc_urbansim_metrics()
    print("*****************#####################Completed urbansim_metrics#####################*******************")

    # Write output
    idx = pd.MultiIndex.from_tuples(metrics_dict.keys(), names=['modelrunID','metric','name','year','blueprint'])
    metrics = pd.Series(metrics_dict, index=idx)
    metrics.name = 'value'
    out_filename = 'C:/Users/{}/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/metrics_urbansim.csv'.format(os.getenv('USERNAME'))
    metrics.to_csv(out_filename, header=True, sep=',', float_format='%.9f')
    
    print("Wrote {}".format(out_filename))