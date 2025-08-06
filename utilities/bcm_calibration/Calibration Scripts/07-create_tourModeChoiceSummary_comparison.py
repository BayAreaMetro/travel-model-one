import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
sns.set(color_codes=True)
import os
import xlsxwriter
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--run_number",type=int, help="Model run output file relative location")

args = parser.parse_args()

model_results=args.run_number

calibration_dir = 'calibration_output/'

total_runs = model_results
tm15_reference_run = 'main_Run_TM15'
last_run_name = 'main_Run_'+str(total_runs)
set_output_dir = 'calibration_output/'+last_run_name+'/07_TourModeChoice/Comparison/'
 
if not os.path.exists(set_output_dir):
    os.makedirs(set_output_dir)   
    
comparison_df_dict={}
hue_order=['Target']
for run_number in [0,total_runs-1,total_runs]:
    if run_number == 0:
        run_name = tm15_reference_run
        hue_order.append('Travel Model 1.5')
    else:   
        run_name = 'main_Run_'+str(run_number)
        
    if os.path.exists(os.path.join(calibration_dir, run_name , '07_TourModeChoice')):
        _df = pd.read_excel(os.path.join(calibration_dir, run_name,'07_TourModeChoice','TourModeChoiceSummary.xlsx'))
        _df=_df.rename(columns={'Model':run_name})
    else:
        continue
    _df_long=_df.melt(id_vars=['Tour Purpose','dimension_01_value','dimension_02_name','dimension_02_value'], 
                      value_vars=['Target',run_name])
    _df_long['variable']=np.where(_df_long['variable']==tm15_reference_run,
                                  'Travel Model 1.5', 
                                  _df_long['variable'])
    if run_number>0:
        _df_long = _df_long[_df_long['variable']!='Target']
        _df_long['variable']=_df_long['variable'].apply(lambda x:'BCM Run_'+ x.split('_')[-1])
        legend_entry = 'BCM Run_'+ run_name.split('_')[-1]
        hue_order.append(legend_entry)
    comparison_df_dict[run_name] = _df_long
    
comparison_df = pd.concat(comparison_df_dict.values(), ignore_index=True)


comparison_df_wide=comparison_df.reset_index().pivot(index=['Tour Purpose','dimension_01_value','dimension_02_name','dimension_02_value'], 
                                       columns='variable', values='value').reset_index().fillna(0)

writer = pd.ExcelWriter(os.path.join(set_output_dir,'TourTODSummary_Comparison.xlsx'), engine='xlsxwriter')
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
sns.set_context("talk",font_scale=1.5, rc={"lines.linewidth": 2.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})

comparison_df=comparison_df.rename(columns={'variable':'Legend'})
for tour in comparison_df['Tour Purpose'].unique():

    _df = comparison_df[(comparison_df['Tour Purpose']==tour)]
    _df['value']=100*_df['value']
    _df['value']=_df['value'].fillna(0)

    fig, axes = plt.subplots(1,3)

    zero_auto=_df[_df['dimension_01_value']=='Zero-Auto']
    order = ['Drive Alone', 'Shared 2 Free', 'Shared 3 Free', 'Walk','Bike',
        'Walk-Transit', 'PNR-Transit','KNR-Transit','School Bus', 'Taxi',  'TNC', 'TNC-Shared' 'Other']

    sns.barplot(x='dimension_02_value', y='value', data=zero_auto, hue='Legend', ci=None,order=order, ax=axes[0])

    axes[0].figure.set_size_inches(50,10)
    axes[0].set_title('Zero-Auto Households')
    axes[0].set_xlabel('Tour Mode')
    axes[0].set_ylabel('Share of Tours (Percentage)')
    axes[0].set_ylim(0, 80)
    axes[0].legend(loc='upper right', fontsize=25)
    for tick in axes[0].get_xticklabels():
        tick.set_rotation(90)
        #tick.set_size(25)

    insufficient_auto=_df[_df['dimension_01_value']=='Insufficient']
    order = ['Drive Alone', 'Shared 2 Free', 'Shared 3 Free', 'Walk','Bike',
        'Walk-Transit', 'PNR-Transit','KNR-Transit','School Bus', 'Taxi',  'TNC', 'TNC-Shared' 'Other']

    sns.barplot(x='dimension_02_value', y='value', data=insufficient_auto, hue='Legend', ci=None,order=order, ax=axes[1])

    axes[1].figure.set_size_inches(50,10)
    axes[1].set_title('Auto Insufficient Households')
    axes[1].set_xlabel('Tour Mode')
    axes[1].set_ylabel('')
    axes[1].set_ylim(0, 80)
    axes[1].legend(loc='upper right', fontsize=25)
    for tick in axes[1].get_xticklabels():
        tick.set_rotation(90)
        #tick.set_size(25)

    sufficient_auto=_df[_df['dimension_01_value']=='Sufficient']
    order = ['Drive Alone', 'Shared 2 Free', 'Shared 3 Free', 'Walk','Bike',
        'Walk-Transit', 'PNR-Transit','KNR-Transit','School Bus', 'Taxi',  'TNC', 'TNC-Shared' 'Other']

    sns.barplot(x='dimension_02_value', y='value', data=sufficient_auto, hue='Legend', ci=None,order=order, ax=axes[2])

    axes[2].figure.set_size_inches(50,10)
    axes[2].set_title('Auto Sufficient Households')
    axes[2].set_xlabel('Tour Mode')
    axes[2].set_ylabel('')
    axes[2].set_ylim(0, 80)
    axes[2].legend(loc='upper right', fontsize=25)
    for tick in axes[2].get_xticklabels():
        tick.set_rotation(90)
        #tick.set_size(25)

    fig.suptitle('Tour Mode Choice by Household Auto Sufficiency for '+tour.split(' ')[0]+' Tours', fontsize=40)
    fig.savefig(os.path.join(set_output_dir, 'Tour Mode Choice by Household Auto Sufficiency for '+tour.split(' ')[0]+' Tours'+'.png'),bbox_inches='tight')