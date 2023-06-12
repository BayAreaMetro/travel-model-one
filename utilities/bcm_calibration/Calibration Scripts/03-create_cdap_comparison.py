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
set_output_dir = 'calibration_output/'+last_run_name+'/03_CDAP_Summary/Comparison/'
if not os.path.exists(set_output_dir):
    os.makedirs(set_output_dir)
    
    
comparison_df_dict={}
hue_order=['Target']
for run_number in [0,1, total_runs-1, total_runs]:
    if run_number == 0:
        run_name = tm15_reference_run
        hue_order.append('Travel Model 1.5')
    else:   
        run_name = 'main_Run_'+str(run_number)
    if os.path.exists(os.path.join(calibration_dir, run_name , '03_CDAP_Summary')):
        _df = pd.read_excel(os.path.join(calibration_dir, run_name,'03_CDAP_Summary','CDAPSummary.xlsx'))
    else:
        continue
    _df_long=_df.melt(id_vars=['estimate','dimension_01_name','dimension_01_value','dimension_02_name','dimension_02_value'], 
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

if len(hue_order)>3:
    del(hue_order[2:-2])

comparison_df = pd.concat(comparison_df_dict.values(), ignore_index=True)
comparison_df_wide=comparison_df.pivot(index=['estimate','dimension_01_name','dimension_01_value','dimension_02_name','dimension_02_value'], 
                                       columns='variable', values='value').reset_index().fillna(0)

writer = pd.ExcelWriter(os.path.join(set_output_dir,'CDAPSummary_Comparison.xlsx'), engine='xlsxwriter')
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

###########Create figures

sns.set_context("talk",font_scale=1.5, rc={"lines.linewidth": 2.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})


for item in comparison_df.dimension_02_value.unique():
    _df=comparison_df[comparison_df['dimension_02_value']==item]
    _df=_df.rename(columns={'variable':'Legend'})
    _df['value']=100*_df['value']
    order = [ 'Full-Time Worker','Part-Time Worker','University Student','Driving Age Student', 'Non-Driving Student',
       'Non-Working Adult', 'Non-Working Senior', 
       'Pre-School']
    list_2=_df.dimension_01_value.unique()
    working_order=[]
    for value in order:
       if value in list_2:
              working_order.append(value)
    fig, ax = plt.subplots()
    ax= sns.barplot(data=_df, 
                    x='dimension_01_value', 
                    y='value', 
                    hue = 'Legend',
                    ci=None,
                    order=working_order,
                    hue_order=hue_order)
    ax.figure.set_size_inches(25,10)
    ax.set_ylim(0,100)
    ax.set_xlabel('Person Type')
    ax.set_ylabel('Share of Persons (Percent)')
    ax.set_title('Share of Persons for Activity Type: '+item)
    plt.legend(loc='upper right', title='Legend', fontsize=15) 
    plt.xticks(rotation=90) 
    ax.figure.savefig(os.path.join(set_output_dir, 'Share of Persons For Activity Type ' +item+'.png'),bbox_inches='tight')

