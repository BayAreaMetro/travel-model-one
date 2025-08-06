import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
sns.set(color_codes=True)
import os
import glob
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
set_output_dir = 'calibration_output/'+last_run_name+'/02_AutoOwnership/Comparison/'
if not os.path.exists(set_output_dir):
    os.makedirs(set_output_dir)
    
    
comparison_df_dict={}
hue_order=['Target']
for run_number in [0, 1, total_runs-1, total_runs]:
    if run_number == 0:
        run_name = tm15_reference_run
        hue_order.append('Travel Model 1.5')
    else:   
        run_name = 'main_Run_'+str(run_number)
    if os.path.exists(os.path.join(calibration_dir, run_name , '02_AutoOwnership')):
        _df = pd.read_excel(os.path.join(calibration_dir, run_name,'02_AutoOwnership','autoOwnershipSummary.xlsx'))
    else:
        continue
    print(run_name)
    _df_long=_df.melt(id_vars=['dimension_01_name','dimension_01_value','dimension_02_name','dimension_02_value','dimension_03_name','dimension_03_value'], 
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
print(hue_order)
if len(hue_order)>3:
    del(hue_order[2:-2])
print(hue_order)
comparison_df = pd.concat(comparison_df_dict.values(), ignore_index=True)


comparison_df_wide=comparison_df.pivot(index=['dimension_01_name','dimension_01_value','dimension_02_name','dimension_02_value','dimension_03_name','dimension_03_value'], 
                                       columns='variable', values='value').reset_index().fillna(0)

comparison_df_wide.to_csv(os.path.join(set_output_dir, 'autoOwnershipModelSummaryComparison.csv'), index=False)
#Create figures
sns.set_context("talk",font_scale=1, rc={"lines.linewidth": 2.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})
county_dict=['San Francisco',
             'San Mateo',
             'Santa Clara',
             'Alameda',
             'Contra Costa',
             'Solano',
             'Napa',
             'Sonoma',
             'Marin','San Joaquin']

county_sorter_index = dict(zip(county_dict, range(len(county_dict))))
hhsize_df=comparison_df[comparison_df['dimension_02_name']=='household_size'].sort_values(by=['dimension_01_value'], key=lambda x: x.map(county_sorter_index))

# for run_number in range(max(1,total_runs-5), total_runs+1):
#     run_name = 'main_Run_'+str(run_number)
#     hue_order.append(run_name)
fig, axes = plt.subplots(2,5)

for item in range(0,5):

    row_loc = 0
    col_loc = item

    county_name = hhsize_df['dimension_01_value'].unique()[item]

    _df = hhsize_df[hhsize_df['dimension_01_value']==county_name]

    order = ['0 Auto HH', '1 Auto HH', '2 Auto HH','3 Auto HH', '4+ Auto HH']

    sns.barplot(x='dimension_03_value', 
                y='value', 
                data=_df, 
                hue='variable',
                hue_order=hue_order, 
                ci=None,
                order=order, 
                ax=axes[row_loc,col_loc])

    axes[row_loc,col_loc].figure.set_size_inches(30,10)
    axes[row_loc,col_loc].set_title('')
    axes[row_loc,col_loc].set_ylim(0, 100)
    axes[row_loc,col_loc].set_xlabel(county_name)

    if row_loc==0 and col_loc==0:
        axes[row_loc,col_loc].set_ylabel('Share of Households (Percent)')
    else:
        axes[row_loc,col_loc].set_ylabel('')
    #axes[0,0].set_ylabel('Share of Households (Percent)')
    for tick in axes[row_loc,col_loc].get_xticklabels():
        tick.set_rotation(45)
        #tick.set_size(15)

for item in range(5,10):

    row_loc = 1
    col_loc = item-5

    county_name = hhsize_df['dimension_01_value'].unique()[item]

    _df = hhsize_df[hhsize_df['dimension_01_value']==county_name]

    order = ['0 Auto HH', '1 Auto HH', '2 Auto HH','3 Auto HH', '4+ Auto HH']

    sns.barplot(x='dimension_03_value', 
                y='value', 
                data=_df, 
                hue='variable',
                hue_order=hue_order, 
                ci=None,
                order=order, 
                ax=axes[row_loc,col_loc])

    axes[row_loc,col_loc].figure.set_size_inches(30,10)
    axes[row_loc,col_loc].set_title('')
    axes[row_loc,col_loc].set_xlabel(county_name)
    axes[row_loc,col_loc].set_ylim(0, 100)

    if row_loc==1 and col_loc==0:
        axes[row_loc,col_loc].set_ylabel('Share of Households (Percent)')
    else:
        axes[row_loc,col_loc].set_ylabel('')
    #axes[1,0].set_ylabel('Share of Households (Percent)')
    for tick in axes[row_loc,col_loc].get_xticklabels():
        tick.set_rotation(45)
        #tick.set_size(15)


fig.tight_layout()
fig.suptitle('Auto Ownership By County', y=1)
fig.savefig(os.path.join(set_output_dir, 'Auto Ownership By County.png'))


fig, axes = plt.subplots(1,len(hhsize_df.dimension_02_value.unique()))
hhsize_df=comparison_df[(comparison_df['dimension_02_name']=='household_size')&(comparison_df['dimension_01_value']=='Total')]

for item in range(0,len(hhsize_df['dimension_02_value'].unique())):

    row_loc = 0
    col_loc = item

    dimension_value = hhsize_df['dimension_02_value'].unique()[item]

    _df = hhsize_df[hhsize_df['dimension_02_value']==dimension_value]

    order = ['0 Auto HH', '1 Auto HH', '2 Auto HH','3 Auto HH', '4+ Auto HH']

    sns.barplot(x='dimension_03_value', 
                y='value', 
                data=_df, 
                hue='variable',
                hue_order=hue_order, 
                ci=None,
                order=order, 
                ax=axes[col_loc])

    axes[col_loc].figure.set_size_inches(30,10)
    axes[col_loc].set_title('')
    axes[col_loc].set_ylim(0, 100)
    axes[col_loc].set_xlabel(dimension_value)
    if col_loc==0:
        axes[col_loc].set_ylabel('Share of Households (Percent)')
    else:
        axes[col_loc].set_ylabel('')
    #axes[0].set_ylabel('Share of Households (Percent)')
    for tick in axes[col_loc].get_xticklabels():
        tick.set_rotation(45)
        #tick.set_size(15)

fig.tight_layout()
fig.suptitle('Auto Ownership By HH Size',   y=1)
fig.savefig(os.path.join(set_output_dir, 'Auto Ownership By Household Size.png'))




hhworker_df=comparison_df[comparison_df['dimension_02_name']=='num_workers'].sort_values(by=['dimension_01_value','dimension_02_value','dimension_03_value'])

fig, axes = plt.subplots(1,len(hhworker_df.dimension_02_value.unique()))

for item in range(0,len(hhworker_df.dimension_02_value.unique())):

    row_loc = 0
    col_loc = item

    dimension_value = hhworker_df['dimension_02_value'].unique()[item]

    _df = hhworker_df[hhworker_df['dimension_02_value']==dimension_value]

    order = ['0 Auto HH', '1 Auto HH', '2 Auto HH','3 Auto HH', '4+ Auto HH']

    sns.barplot(x='dimension_03_value', 
                y='value', 
                data=_df, 
                hue='variable', 
                hue_order=hue_order, 
                ci=None,
                order=order, 
                ax=axes[col_loc])

    axes[col_loc].figure.set_size_inches(30,10)
    axes[col_loc].set_title('')
    axes[col_loc].set_ylim(0, 100)
    axes[col_loc].set_xlabel(dimension_value)
    if col_loc==0:
        axes[col_loc].set_ylabel('Share of Households (Percent)')
    else:
        axes[col_loc].set_ylabel('')
    #axes[0].set_ylabel('Share of Households (Percent)')
    for tick in axes[col_loc].get_xticklabels():
        tick.set_rotation(45)
        #tick.set_size(15)

fig.tight_layout()
fig.suptitle('Auto Ownership By HH Workers', y=1)
fig.savefig(os.path.join(set_output_dir, 'Auto Ownership By Household Workers.png'))