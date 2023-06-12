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
set_output_dir = 'calibration_output/'+last_run_name+'/05_NonMandatoryTourFreq/Comparison/'
if not os.path.exists(set_output_dir):
    os.makedirs(set_output_dir)
    
    
comparison_df_dict={}
hue_order=['Target']
for run_number in [0, total_runs-1, total_runs]:
    if run_number == 0:
        run_name = tm15_reference_run
        hue_order.append('Travel Model 1.5')
    else:   
        run_name = 'main_Run_'+str(run_number)
        
    if os.path.exists(os.path.join(calibration_dir, run_name , '05_NonMandatoryTourFreq')):
        _df = pd.read_excel(os.path.join(calibration_dir, run_name,'05_NonMandatoryTourFreq','NonMandatoryTourFrequency_Summary.xlsx'))
        _df=_df.drop(columns=['dimension_02_name'])
        _df['dimension_02_name']=_df['Tour Purpose'].apply(lambda x: 'Number of '+x+' Tasks')
    else:
        continue
    _df_long=_df.melt(id_vars=['dimension_01_value','dimension_02_name','dimension_02_value'], 
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
comparison_df_wide=comparison_df.reset_index().pivot(index=['dimension_01_value','dimension_02_name','dimension_02_value'], 
                                       columns='variable', values='value').reset_index().fillna(0)

writer = pd.ExcelWriter(os.path.join(set_output_dir,'NonMandatoryTourFrequency_Summary_Comparison.xlsx'), engine='xlsxwriter')
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

comparison_df=comparison_df.rename(columns={'variable':'Legend'})

comparison_df_long=comparison_df[comparison_df['dimension_02_value']!=0]
comparison_df_long=comparison_df_long.fillna(0)
comparison_df_long['value']=100*comparison_df_long['value']

for persontype in comparison_df_long.dimension_01_value.unique():
    _df=comparison_df_long[comparison_df_long['dimension_01_value']==persontype]
    _df['value']=_df['value'].fillna(0)

    sns.set_context("talk",font_scale=1, rc={"lines.linewidth": 2.5})
    sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})

    fig, axes = plt.subplots(1,len(_df.dimension_02_name.unique()))

    for item in range(0,len(_df.dimension_02_name.unique())):

        row_loc = 0
        col_loc = item

        tour_purpose = _df.dimension_02_name.unique()[item]

        _figure_df=_df[_df['dimension_02_name']==tour_purpose]

        sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend', ci=None,ax=axes[col_loc])

        axes[col_loc].figure.set_size_inches(30,10)
        #axes[col_loc].set_title(tour_purpose)
        axes[col_loc].set_xlabel(tour_purpose)
        if row_loc==0 and col_loc==0:
            axes[col_loc].set_ylabel('Share of Households (Percent)')
        else:
            axes[col_loc].set_ylabel('')
        #axes[col_loc].set_ylabel('Share of Persons (Percent)')
        axes[col_loc].set_ylim(0,100)

    fig.suptitle('Share of Persons by Number of Non Mandatory Tours for Person Type: '+persontype)
    fig.savefig(os.path.join(set_output_dir, 'Non Mandatory Tour Frequency by Person Type '+persontype+'.png'))