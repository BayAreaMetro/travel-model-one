import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
sns.set(color_codes=True)
import os
import glob
import xlsxwriter
import argparse
import math
import textwrap
from pandas.api.types import CategoricalDtype

parser = argparse.ArgumentParser()
parser.add_argument("--run_name",type=str, help="Model run output file relative location")

args = parser.parse_args()

model_results=args.run_name

#Set Directory
set_model_result_dir = model_results+'/'
set_calibration_target_dir='Calibration Targets/'
set_output_dir = 'calibration_output/'+model_results+'/08_TLFD_Summary/'

if not os.path.exists(set_output_dir):
    os.makedirs(set_output_dir)

#Read calibration Target

calib_target = pd.read_csv(os.path.join(set_calibration_target_dir, 'NonMandTourTLFD_Targets.csv'))
calib_target['dimension_01_value']=np.where(calib_target['dimension_01_value']=='Social/Visit',
                                            'Social',
                                            calib_target['dimension_01_value'])

calib_target_school_univ= pd.read_csv(os.path.join(set_calibration_target_dir, 'SchoolandUniversityTourTLFD_Targets.csv'))
calib_target_work = pd.read_csv(os.path.join(set_calibration_target_dir, 'WorkLocationTargets.csv'))
calib_target_work=calib_target_work[calib_target_work['estimate']=='Share of commute length by distance bin (exclude intrazonal)']
calib_target_work=calib_target_work.drop(columns='dimension_02_value')
calib_target_work=calib_target_work.rename(columns={'dimension_01_value':'dimension_02_value'})
calib_target_work['dimension_01_value']='Work'

calib_target_all=pd.concat([calib_target, calib_target_school_univ, calib_target_work], ignore_index=True)

avg_tour_length_target = pd.read_csv(os.path.join(set_calibration_target_dir, 'AverageTourDistance_summary.csv'))
avg_tour_length_target['tour_purpose']=np.where(avg_tour_length_target['tour_purpose']=='Social/Visit',
                                                'Social',
                                                avg_tour_length_target['tour_purpose'])

avg_tour_length_target_dict=dict(zip(avg_tour_length_target['tour_purpose'], avg_tour_length_target['average_distance']))
calib_target_all['average_distance_target']=calib_target_all['dimension_01_value'].map(avg_tour_length_target_dict)


#Read Model Results

indiv_tour_df = pd.read_csv(os.path.join(set_model_result_dir, 'indivTourData_1.csv'))

distance_skim = pd.read_csv(os.path.join(set_model_result_dir, 'da_am_skims.csv'))
distance_skim = distance_skim[(distance_skim['dist'].notnull())&(distance_skim['dist']<10000)]


def tour_purpose_category(x):
    if x in ['work_med', 'work_very high', 'work_high','work_low']:
        return 'Work'
    elif x in ['school_grade','school_high']:
        return 'School'
    elif x in ['atwork_eat','atwork_maint','atwork_business']:
        return 'At-Work'
    elif x == 'shopping':
        return 'Shopping'
    elif x in ['escort_no kids','escort_kids']:
        return 'Escorting'
    elif x=='university':
        return 'University'
    elif x=='eatout':
        return 'Eat Out'
    elif x=='social':
        return 'Social'
    elif x=='othdiscr':
        return 'Discretionary'
    elif x=='othmaint':
        return 'Maintenance'
    else:
        return None

tour_purpose_sort=CategoricalDtype(['Work','School','University','At-Work','Shopping','Escorting','Eat Out','Social','Discretionary','Maintenance'], ordered=True)
indiv_tour_df['Tour Purpose']=indiv_tour_df['tour_purpose'].apply(tour_purpose_category) 
indiv_tour_df['person_id']=indiv_tour_df['person_id'].astype(str)
indiv_tour_df['tour_id']=indiv_tour_df['tour_id'].astype(str)
indiv_tour_df['unique_tour_id']=indiv_tour_df['person_id']+'-'+indiv_tour_df['tour_id']


person_df_ws_loc=indiv_tour_df.merge(distance_skim[['origin','destination','dist']],
                                 how='left',
                                 left_on=['orig_taz','dest_taz'],
                                 right_on=['origin','destination'])


distance_bin=range(0,150)

# person_df_ws_loc['distance_bin']=pd.cut(person_df_ws_loc['dist'], distance_bin)
# person_df_ws_loc['distance_bin']=person_df_ws_loc['distance_bin'].astype(str)
person_df_ws_loc['upper_limit'] = person_df_ws_loc['dist'].apply(lambda x: math.ceil(x))
 
calib_target_all['upper_limit'] = calib_target_all['dimension_02_value'].apply(lambda x: int(x.split('-')[1].replace(']','')))
tour_length_avg =  person_df_ws_loc.groupby('Tour Purpose').agg(average_distance_model = ('dist','mean')).reset_index()


avg_tour_length_dict= dict(zip(tour_length_avg['Tour Purpose'],tour_length_avg['average_distance_model']))

person_share= person_df_ws_loc.groupby(['Tour Purpose','upper_limit']).agg(Unique_Tours=('unique_tour_id','nunique')).reset_index()
person_share['Total_Tours']=person_share.groupby('Tour Purpose')['Unique_Tours'].transform(sum)
person_share[model_results]=person_share['Unique_Tours']/person_share['Total_Tours']
person_share=person_share.rename(columns={'Tour Purpose':'dimension_01_value'})
person_share_comp=pd.merge(calib_target_all, person_share,
                            left_on=['dimension_01_value','upper_limit'],
                            right_on=['dimension_01_value','upper_limit'],
                            how='inner')

person_share_comp=person_share_comp.rename(columns={'estimate_value':'Target'})
person_share_comp['average_distance_model']=person_share_comp['dimension_01_value'].map(avg_tour_length_dict)
person_share_comp['dimension_01_value'] = person_share_comp['dimension_01_value'].astype(tour_purpose_sort)
person_share_comp=person_share_comp.sort_values(by=['dimension_01_value','upper_limit'])
comparison_df=person_share_comp[['source', 'estimate', 'dimension_01_name', 'dimension_01_value',
                                 'dimension_02_name', 'dimension_02_value', 'estimate_name','average_distance_target','average_distance_model',
                                 'Target',model_results]]

writer = pd.ExcelWriter(os.path.join(set_output_dir,'NonMandatoryTourLengthDistributionSummary.xlsx'), engine='xlsxwriter')
comparison_df.to_excel(writer, sheet_name='All', startrow=1, header=False, index=False)

workbook  = writer.book
worksheet = writer.sheets['All']
# Add a header format.
header_format = workbook.add_format({
    'bold': True,
    'text_wrap': True,
    'valign': 'top',
    'fg_color': '#D7E4BC',
    'border': 1})

# Get the dimensions of the dataframe.
(max_row, max_col) = comparison_df.shape

# Make the columns wider for clarity.
worksheet.set_column(0,  max_col - 1, 12)
worksheet.autofilter(0, 0, max_row, max_col - 1)

for col_num, value in enumerate(comparison_df.columns.values):
    worksheet.write(0, col_num, value, header_format)

writer.save()

comparison_df_long=pd.melt(person_share_comp, id_vars=['dimension_01_value','upper_limit','average_distance_target','average_distance_model'],
                            value_vars=['Target', model_results], var_name='Legend')

comparison_df_long['upper_limit']=comparison_df_long['upper_limit'].astype(int)
comparison_df_long=comparison_df_long.sort_values(by=['dimension_01_value','upper_limit'])
comparison_df_long['Pct']=100*comparison_df_long['value']

sns.set_context("talk",font_scale=1.5, rc={"lines.linewidth": 3.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})
props = dict(boxstyle='round', alpha=1,facecolor='white',edgecolor='black')

for tour in comparison_df_long.dimension_01_value.unique():
    fig, ax = plt.subplots()

    _df= comparison_df_long[comparison_df_long['dimension_01_value']==tour]
    avg_dist_target = _df['average_distance_target'].mean()
    avg_dist_model = _df['average_distance_model'].mean()

    ax= sns.lineplot(data=_df, 
                    x='upper_limit', y='Pct', hue = 'Legend', hue_order=['Target',model_results])
    ax.figure.set_size_inches(20,15)
    ax.set_xlim(0,50)
    ax.set_xlabel('Upper Limit of Distance Band (miles)')
    ax.set_ylabel('Percent Share')
    ax.set_title('Tour Length Frequency for Tour Purpose: '+tour)
    textstr = 'Average Tour Distance (Target) = %.1f miles \n Average Tour DIstance (Model) = %.1f miles' % (avg_dist_target, avg_dist_model)
    
    ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=20,
            verticalalignment='top', bbox=props)
    plt.legend(loc='upper right', fontsize=20)

    fig.savefig(os.path.join(set_output_dir, 'Tour Length Distribution for Tour Purpose '+tour+'.png'))