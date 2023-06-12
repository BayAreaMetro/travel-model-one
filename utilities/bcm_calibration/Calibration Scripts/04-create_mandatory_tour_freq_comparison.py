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
set_output_dir = 'calibration_output/'+last_run_name+'/04_MandatoryTourFreq/Comparison/'
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
        
    if os.path.exists(os.path.join(calibration_dir, run_name , '04_MandatoryTourFreq')):
        _df = pd.read_excel(os.path.join(calibration_dir, run_name,'04_MandatoryTourFreq','SchoolLocationTLFD_Summary.xlsx'))
        _df=_df.drop(columns=['dimension_02_name'])
        _df=_df.rename(columns={'estimate_value':'Target','Tour Purpose':'dimension_02_name'})
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
comparison_df_wide=comparison_df.pivot(index=['dimension_01_value','dimension_02_name','dimension_02_value'], 
                                       columns='variable', values='value').reset_index().fillna(0)

writer = pd.ExcelWriter(os.path.join(set_output_dir,'SchoolLocationTLFD_Summary_Comparison.xlsx'), engine='xlsxwriter')
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


sorter=['Number of Work Tours','Number of University Tours','Number of School Tours','Number of Work and School Tours']
sorterIndex = dict(zip(sorter, range(len(sorter))))

comparison_df['Tour Purpose']=comparison_df['dimension_02_name']
comparison_df['dimension_02_name']=comparison_df['dimension_02_name'].apply(lambda x: 'Number of '+x+' Tours')
comparison_df=comparison_df.rename(columns={'variable':'Legend'})

# comparison_df_long['Legend']=np.where(comparison_df_long['Legend']==model_results,model_results, 'Target')
comparison_df_long=comparison_df[comparison_df['dimension_02_value']!=0]
comparison_df_long=comparison_df_long.fillna(0)
comparison_df_long['value']=100*comparison_df_long['value']


fig, axes = plt.subplots(1,3)

sns.set_context("talk",font_scale=1.5, rc={"lines.linewidth": 2.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})

persontype = 'Driving Age Student'
tour_purpose = 'Work'

_df=comparison_df_long[comparison_df_long['dimension_01_value']==persontype]
_df=_df.sort_values(by=['dimension_02_name'], key=lambda x: x.map(sorterIndex))
_df['dimension_02_value']=_df['dimension_02_value'].astype(str)
_figure_df=_df[_df['Tour Purpose']==tour_purpose]
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend', ci=None, ax= axes[0], hue_order=hue_order)

axes[0].figure.set_size_inches(30,10)
axes[0].set_ylim(0,100)
axes[0].set_xlabel('Number of '+tour_purpose+' Tours', fontsize=20)
axes[0].set_ylabel('Share of Persons (Percent)', fontsize=20)
axes[0].set_xticklabels(axes[0].get_xticks(), fontsize=20)
axes[0].set_yticklabels(axes[0].get_yticks(), fontsize=20)
#plt.legend(loc='upper right', title='Legend', fontsize=15) 

tour_purpose = 'School'

_figure_df=_df[_df['Tour Purpose']==tour_purpose]
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend', ci=None, ax= axes[1], hue_order=hue_order)

axes[1].figure.set_size_inches(30,10)
axes[1].set_ylim(0,100)
axes[1].set_xlabel('Number of '+tour_purpose+' Tours', fontsize=20)
axes[1].set_ylabel('Share of Persons (Percent)', fontsize=20)
axes[1].set_xticklabels(axes[1].get_xticks(), fontsize=20)
axes[1].set_yticklabels(axes[1].get_yticks(), fontsize=20)
#plt.legend(loc='upper right', title='Legend', fontsize=15) 

tour_purpose = 'Work and School'

_figure_df=_df[_df['Tour Purpose']==tour_purpose]
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend', ci=None, ax= axes[2], hue_order=hue_order)

axes[2].figure.set_size_inches(30,10)
axes[2].set_ylim(0,100)
axes[2].set_xlabel('Number of '+tour_purpose+' Tours', fontsize=20)
axes[2].set_ylabel('Share of Persons (Percent)', fontsize=20)
axes[2].set_xticklabels(axes[2].get_xticks(), fontsize=20)
axes[2].set_yticklabels(axes[2].get_yticks(), fontsize=20)
#plt.legend(loc='upper right', title='Legend', fontsize=15) 
fig.suptitle('Share of Persons by Number of Mandatory Tours by Person Type: '+persontype, fontsize=35)
fig.savefig(os.path.join(set_output_dir, 'Mandatory Tour Frequency by Person Type '+persontype+'.png'))


persontype = 'Full-Time Worker'
_df=comparison_df_long[comparison_df_long['dimension_01_value']==persontype]
_df=_df.sort_values(by=['dimension_02_name'], key=lambda x: x.map(sorterIndex))
_df['dimension_02_value']=_df['dimension_02_value'].astype(str)

fig, axes = plt.subplots(1,2)

sns.set_context("talk",font_scale=1.5, rc={"lines.linewidth": 2.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})

tour_purpose = 'Work'

_figure_df=_df[_df['Tour Purpose']==tour_purpose]
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend', ci=None, ax= axes[0], hue_order=hue_order)

axes[0].figure.set_size_inches(30,10)
axes[0].set_ylim(0,100)
axes[0].set_xlabel('Number of '+tour_purpose+' Tours', fontsize=20)
axes[0].set_ylabel('Share of Persons (Percent)', fontsize=20)
axes[0].set_xticklabels(axes[0].get_xticks(), fontsize=20)
axes[0].set_yticklabels(axes[0].get_yticks(), fontsize=20)
#plt.legend(loc='upper right', title='Legend', fontsize=15) 
tour_purpose = 'School'

_figure_df=_df[_df['Tour Purpose']==tour_purpose]
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend', ci=None, ax= axes[1], hue_order=hue_order)

axes[1].figure.set_size_inches(30,10)
axes[1].set_ylim(0,100)
axes[1].set_xlabel('Number of '+tour_purpose+' Tours', fontsize=20)
axes[1].set_ylabel('Share of Persons (Percent)', fontsize=20)
axes[1].set_xticklabels(axes[1].get_xticks(), fontsize=20)
axes[1].set_yticklabels(axes[1].get_yticks(), fontsize=20)
#plt.legend(loc='upper right', title='Legend', fontsize=15) 
fig.suptitle('Share of Persons by Number of Mandatory Tours by Person Type: '+persontype)
fig.savefig(os.path.join(set_output_dir, 'Mandatory Tour Frequency by Person Type '+persontype+'.png'))

persontype = 'Non-Driving Student'
_df=comparison_df_long[comparison_df_long['dimension_01_value']==persontype]
_df=_df.sort_values(by=['dimension_02_name'], key=lambda x: x.map(sorterIndex))
_df['dimension_02_value']=_df['dimension_02_value'].astype(str)

fig, axes = plt.subplots()

sns.set_context("talk",font_scale=1.5, rc={"lines.linewidth": 2.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})


tour_purpose = 'School'

_figure_df=_df[_df['Tour Purpose']==tour_purpose]
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend', ci=None, ax= axes)

axes.figure.set_size_inches(30,10)
axes.set_ylim(0,100)
axes.set_xlabel('Number of '+tour_purpose+' Tours', fontsize=20)
axes.set_ylabel('Share of Persons (Percent)', fontsize=20)
axes.set_xticklabels(axes.get_xticks(), fontsize=20)
axes.set_yticklabels(axes.get_yticks(), fontsize=20)
#plt.legend(loc='upper right', title='Legend', fontsize=15) 
fig.suptitle('Share of Persons by Number of Mandatory Tours by Person Type: '+persontype)
fig.savefig(os.path.join(set_output_dir, 'Mandatory Tour Frequency by Person Type '+persontype+'.png'))


persontype = 'Part-Time Worker'
_df=comparison_df_long[comparison_df_long['dimension_01_value']==persontype]
_df=_df.sort_values(by=['dimension_02_name'], key=lambda x: x.map(sorterIndex))
_df['dimension_02_value']=_df['dimension_02_value'].astype(str)

fig, axes = plt.subplots()

sns.set_context("talk",font_scale=1.5, rc={"lines.linewidth": 2.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})

tour_purpose = 'Work'

_figure_df=_df[_df['Tour Purpose']==tour_purpose]
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend', ci=None, ax= axes, hue_order=hue_order)

axes.figure.set_size_inches(30,10)
axes.set_ylim(0,100)
axes.set_xlabel('Number of '+tour_purpose+' Tours', fontsize=20)
axes.set_ylabel('Share of Persons (Percent)', fontsize=20)
axes.set_xticklabels(axes.get_xticks(), fontsize=20)
axes.set_yticklabels(axes.get_yticks(), fontsize=20)
#plt.legend(loc='upper right', title='Legend', fontsize=15) 
fig.suptitle('Share of Persons by Number of Mandatory Tours by Person Type: '+persontype)
fig.savefig(os.path.join(set_output_dir, 'Mandatory Tour Frequency by Person Type '+persontype+'.png'))


persontype = 'Pre-School'
_df=comparison_df_long[comparison_df_long['dimension_01_value']==persontype]
_df=_df.sort_values(by=['dimension_02_name'], key=lambda x: x.map(sorterIndex))
_df['dimension_02_value']=_df['dimension_02_value'].astype(str)

fig, axes = plt.subplots()

sns.set_context("talk",font_scale=1.5, rc={"lines.linewidth": 2.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})


tour_purpose = 'School'

_figure_df=_df[_df['Tour Purpose']==tour_purpose]
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend', ci=None, ax= axes, hue_order=hue_order)

axes.figure.set_size_inches(30,10)
axes.set_ylim(0,100)
axes.set_xlabel('Number of '+tour_purpose+' Tours', fontsize=20)
axes.set_ylabel('Share of Persons (Percent)', fontsize=20)
axes.set_xticklabels(axes.get_xticks(), fontsize=20)
axes.set_yticklabels(axes.get_yticks(), fontsize=20)
#plt.legend(loc='upper right', title='Legend', fontsize=15) 
fig.suptitle('Share of Persons by Number of Mandatory Tours by Person Type: '+persontype)
fig.savefig(os.path.join(set_output_dir, 'Mandatory Tour Frequency by Person Type '+persontype+'.png'))


persontype = 'University Student'
_df=comparison_df_long[comparison_df_long['dimension_01_value']==persontype]
_df=_df.sort_values(by=['dimension_02_name'], key=lambda x: x.map(sorterIndex))
_df['dimension_02_value']=_df['dimension_02_value'].astype(str)

fig, axes = plt.subplots(1,3)

sns.set_context("talk",font_scale=1.5, rc={"lines.linewidth": 2.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})

tour_purpose = 'Work'

_figure_df=_df[_df['Tour Purpose']==tour_purpose]
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend', ci=None, ax= axes[0], hue_order=hue_order)

axes[0].figure.set_size_inches(30,10)
axes[0].set_ylim(0,100)
axes[0].set_xlabel('Number of '+tour_purpose+' Tours', fontsize=20)
axes[0].set_ylabel('Share of Persons (Percent)', fontsize=20)
axes[0].set_xticklabels(axes[0].get_xticks(), fontsize=20)
axes[0].set_yticklabels(axes[0].get_yticks(), fontsize=20)
#plt.legend(loc='upper right', title='Legend', fontsize=15) 
tour_purpose = 'School'

_figure_df=_df[_df['Tour Purpose']==tour_purpose]
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend', ci=None, ax= axes[1], hue_order=hue_order)

axes[1].figure.set_size_inches(30,10)
axes[1].set_ylim(0,100)
axes[1].set_xlabel('Number of '+tour_purpose+' Tours', fontsize=20)
axes[1].set_ylabel('Share of Persons (Percent)', fontsize=20)
axes[1].set_xticklabels(axes[1].get_xticks(), fontsize=20)
axes[1].set_yticklabels(axes[1].get_yticks(), fontsize=20)
#plt.legend(loc='upper right', title='Legend', fontsize=15) 

tour_purpose = 'Work and School'

_figure_df=_df[_df['Tour Purpose']==tour_purpose]
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend', ci=None, ax= axes[2], hue_order=hue_order)

axes[2].figure.set_size_inches(30,10)
axes[2].set_ylim(0,100)
axes[2].set_xlabel('Number of '+tour_purpose+' Tours', fontsize=20)
axes[2].set_ylabel('Share of Persons (Percent)', fontsize=20)
axes[2].set_xticklabels(axes[2].get_xticks(), fontsize=20)
axes[2].set_yticklabels(axes[2].get_yticks(), fontsize=20)
#plt.legend(loc='upper right', title='Legend', fontsize=15) 
fig.suptitle('Share of Persons by Number of Mandatory Tours by Person Type: '+persontype)
fig.savefig(os.path.join(set_output_dir, 'Mandatory Tour Frequency by Person Type '+persontype+'.png'))