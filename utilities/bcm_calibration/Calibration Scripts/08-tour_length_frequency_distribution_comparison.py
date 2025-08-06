import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
sns.set(color_codes=True)
import os
import xlsxwriter
import argparse
from pandas.api.types import CategoricalDtype

parser = argparse.ArgumentParser()
parser.add_argument("--run_number",type=int, help="Model run output file relative location")

args = parser.parse_args()

model_results=args.run_number

calibration_dir = 'calibration_output/'

total_runs = model_results
tm15_reference_run = 'main_Run_TM15'
last_run_name = 'main_Run_'+str(total_runs)
set_output_dir = 'calibration_output/'+last_run_name+'/08_TLFD_Summary/Comparison/'
 
if not os.path.exists(set_output_dir):
    os.makedirs(set_output_dir)   
    
comparison_df_dict={}
distance_comparison_df_dict={}

hue_order=['Target']
for run_number in [0,total_runs-2,total_runs-1,total_runs]:
    if run_number == 0:
        run_name = tm15_reference_run
        hue_order.append('Travel Model 1.5')
    else:   
        run_name = 'main_Run_'+str(run_number)
        
    if os.path.exists(os.path.join(calibration_dir, run_name , '08_TLFD_Summary')):
        _df = pd.read_excel(os.path.join(calibration_dir, run_name,'08_TLFD_Summary','NonMandatoryTourLengthDistributionSummary.xlsx'))
        _df=_df.rename(columns={'average_distance_model':'average_distance_'+run_name})
    else:
        continue
    _df_long=_df.melt(id_vars=['dimension_01_value','dimension_02_value'], 
                      value_vars=['Target',run_name])
    _df_long['variable']=np.where(_df_long['variable']==tm15_reference_run,
                                  'Travel Model 1.5', 
                                  _df_long['variable'])

    _df_dist_long=_df.melt(id_vars=['dimension_01_value','dimension_02_value'], 
                           value_vars=['average_distance_target','average_distance_'+run_name])
    _df_dist_long['variable']=np.where(_df_dist_long['variable']=='average_distance_target',
                                        'Target', 
                                        _df_long['variable'])

    if run_number>0:
        _df_long = _df_long[_df_long['variable']!='Travel Model 1.5']
        _df_long['variable']=_df_long['variable'].apply(lambda x:'BCM Run_'+ x.split('_')[-1])
        _df_long = _df_long[_df_long['variable']!='BCM Run_Target']

        _df_dist_long = _df_dist_long[_df_dist_long['variable']!='Target']
        _df_dist_long['variable']=_df_dist_long['variable'].apply(lambda x:'BCM Run_'+ x.split('_')[-1])

        legend_entry = 'BCM Run_'+ run_name.split('_')[-1]
        hue_order.append(legend_entry)
    comparison_df_dict[run_name] = _df_long
    distance_comparison_df_dict[run_name] = _df_dist_long
    
comparison_df = pd.concat(comparison_df_dict.values(),ignore_index=True)
distance_comparison_df = pd.concat(distance_comparison_df_dict.values(),ignore_index=True)
distance_comparison_df=distance_comparison_df.drop_duplicates(['dimension_01_value','variable','value'])
distance_comparison_df['dimension_02_value']='Average Tour Distance'

comparison_df_all=pd.concat([comparison_df, distance_comparison_df],ignore_index=True)

comparison_df_wide=comparison_df_all.pivot(index=['dimension_01_value','dimension_02_value'], 
                                       columns='variable', values='value').reset_index().fillna(0)
tour_purpose_sort=CategoricalDtype(['Work','School','University','At-Work','Shopping','Escorting','Eat Out','Social','Discretionary','Maintenance'], ordered=True)
dist_bin_sort=CategoricalDtype(['[0-1]','[1-2]','[2-3]','[3-4]','[4-5]','[5-6]','[6-7]','[7-8]','[8-9]','[9-10]','[10-11]','[11-12]','[12-13]'], ordered=True)

comparison_df_wide['dimension_01_value'] = comparison_df_wide['dimension_01_value'].astype(tour_purpose_sort)
comparison_df_wide=comparison_df_wide.sort_values(by=['dimension_01_value','dimension_02_value'])

writer = pd.ExcelWriter(os.path.join(set_output_dir,'TourLengthDistributionSummary.xlsx'), engine='xlsxwriter')

comparison_df_wide.to_excel(writer, sheet_name='All', startrow=1, header=False, index=False)

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
(max_row, max_col) = comparison_df_wide.shape

# Make the columns wider for clarity.
worksheet.set_column(0,  max_col - 1, 12)
worksheet.autofilter(0, 0, max_row, max_col - 1)

for col_num, value in enumerate(comparison_df_wide.columns.values):
    worksheet.write(0, col_num, value, header_format)

writer.save()

###########


sns.set_context("talk",font_scale=1.5, rc={"lines.linewidth": 3.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})

comparison_df['upper_limit'] = comparison_df['dimension_02_value'].apply(lambda x: int(x.split('-')[1].replace(']','')))
comparison_df['Pct']=100*comparison_df['value']

for tour in comparison_df.dimension_01_value.unique():
    fig, ax = plt.subplots()

    _df= comparison_df[comparison_df['dimension_01_value']==tour]


    ax= sns.lineplot(data=_df, 
                    x='upper_limit', y='Pct', hue = 'variable', hue_order=hue_order)
    ax.figure.set_size_inches(20,15)
    ax.set_xlim(0,50)
    ax.set_xlabel('Upper Limit of Distance Band (miles)')
    ax.set_ylabel('Percent Share')
    ax.set_title('Tour Length Frequency for Tour Purpose: '+tour)

    plt.legend(loc='upper right', fontsize=20)

    fig.savefig(os.path.join(set_output_dir, 'Tour Length Distribution for Tour Purpose '+tour+'.png'))


sns.set_context("talk",font_scale=1.5, rc={"lines.linewidth": 3.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})

tour_purpose_sorter = ['Work','School', 'University', 'Discretionary', 'Eat Out', 'Escorting', 'Maintenance',
       'Shopping', 'Social',  'At-Work']
sorter_index= dict(zip(tour_purpose_sorter, range(len(tour_purpose_sorter))))

distance_comparison_df=distance_comparison_df.sort_values(by='dimension_01_value',key=lambda x: x.map(sorter_index))

fig, axes = plt.subplots(2,5)
for item in range(0,5):

    row_loc = 0
    col_loc = item

    tour_purpose = distance_comparison_df['dimension_01_value'].unique()[item]

    _df = distance_comparison_df[distance_comparison_df['dimension_01_value']==tour_purpose]


    sns.barplot(x='dimension_01_value', 
                y='value', 
                data=_df, 
                hue='variable',
                hue_order=hue_order, 
                ci=None,
                ax=axes[row_loc,col_loc])

    axes[row_loc,col_loc].figure.set_size_inches(50,30)
    axes[row_loc,col_loc].set_title('')
    axes[row_loc,col_loc].set_ylim(0, 20)
    axes[row_loc,col_loc].set_xlabel('')
    axes[row_loc,col_loc].set_ylabel('Average Tour Distance (Miles)')

for item in range(5,10):

    row_loc = 1
    col_loc = item-5

    tour_purpose = distance_comparison_df['dimension_01_value'].unique()[item]

    _df = distance_comparison_df[distance_comparison_df['dimension_01_value']==tour_purpose]

    sns.barplot(x='dimension_01_value', 
                y='value', 
                data=_df, 
                hue='variable',
                hue_order=hue_order, 
                ci=None,
                ax=axes[row_loc,col_loc])

    axes[row_loc,col_loc].figure.set_size_inches(50,30)
    axes[row_loc,col_loc].set_title('')
    axes[row_loc,col_loc].set_ylim(0, 20)
    axes[row_loc,col_loc].set_xlabel('')
    axes[row_loc,col_loc].set_ylabel('Average Tour Distance (Miles)')

fig.suptitle('Average Tour Length by Tour Purpose', fontsize=40)
fig.savefig(os.path.join(set_output_dir, 'Average Tour Length by Tour Purpose.png'), bbox_inches='tight')
