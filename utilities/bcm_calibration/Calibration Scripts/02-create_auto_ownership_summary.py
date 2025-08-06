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
parser.add_argument("--run_name",type=str, help="Model run output file relative location")

args = parser.parse_args()

model_results=args.run_name

#Set Directory
set_model_result_dir = model_results+'/'
set_calibration_target_dir='Calibration Targets/'
set_output_dir = 'calibration_output/'+model_results+'/02_AutoOwnership/'


if not os.path.exists(set_output_dir):
    os.makedirs(set_output_dir)

#Read calibration Target

calib_target_hhsize = pd.read_csv(os.path.join(set_calibration_target_dir, 'auto_onwership_byHHSize.csv'))

calib_target_workers = pd.read_csv(os.path.join(set_calibration_target_dir, 'auto_onwership_byNum_workers.csv'))

#Read Model Results
household_df = pd.read_csv(os.path.join(set_model_result_dir, 'householdData_1.csv'))

#Get the geocrosswalk
geo_crosswalk=pd.read_csv(os.path.join(set_model_result_dir,'geo_crosswalk.csv'))
taz_county_dict=dict(zip(geo_crosswalk['TAZ'], geo_crosswalk['COUNTYNAME']))

household_df['county_name']=household_df['taz'].map(taz_county_dict)
household_df['household_size']=np.where(household_df['size']>3,
                                        '4+',
                                        household_df['size'])
household_df['household_size']=household_df['household_size'].apply(lambda x: x+' Person HH')

household_df['num_vehicles']=np.where(household_df['autos']>3,
                                     '4+',household_df['autos'])
household_df['num_vehicles']=household_df['num_vehicles'].apply(lambda x: x+' Auto HH')

household_df['num_workers']=np.where(household_df['workers']>2,
                                        '3+',
                                        household_df['workers'])   
household_df['num_workers']=household_df['num_workers'].apply(lambda x: x.split(' ')[0]+' Worker HH')


#Need to cleanup calibration targets
calib_target_hhsize=calib_target_hhsize.rename(columns=str.lower)
calib_target_hhsize['household_size']=calib_target_hhsize['household_size'].apply(lambda x: x.split(' ')[0]+' Person HH')
calib_target_hhsize['num_vehicles']=calib_target_hhsize['num_vehicles'].apply(lambda x: x.split(' ')[0]+' Auto HH')
calib_target_hhsize['Total_Level_01_02']=calib_target_hhsize.groupby(['county_name','household_size'])['num_households'].transform(sum)
calib_target_hhsize['Target']=100*calib_target_hhsize['num_households']/calib_target_hhsize['Total_Level_01_02']
calib_target_hhsize_long=calib_target_hhsize.melt(id_vars=['county_name', 'household_size','num_vehicles'], value_vars=['Target'])
calib_target_hhsize_long=calib_target_hhsize_long.rename(columns={'county_name': 'dimension_01_value',
                                                                  'household_size': 'dimension_02_value',
                                                                  'num_vehicles': 'dimension_03_value'})
calib_target_hhsize_long['dimension_01_name'] = 'county_name'
calib_target_hhsize_long['dimension_02_name'] = 'household_size'
calib_target_hhsize_long['dimension_03_name'] = 'num_vehicles'

calib_target_workers=calib_target_workers.rename(columns=str.lower)
calib_target_workers['num_vehicles']=calib_target_workers['num_vehicles'].apply(lambda x: x.split(' ')[0]+' Auto HH')
calib_target_workers['num_workers']=calib_target_workers['num_workers'].apply(lambda x: x.split(' ')[0]+' Worker HH')
calib_target_workers['Total_Level_01_02']=calib_target_workers.groupby(['county_name','num_workers'])['num_households'].transform(sum)
calib_target_workers['Target']=100*calib_target_workers['num_households']/calib_target_workers['Total_Level_01_02']
calib_target_workers_long=calib_target_workers.melt(id_vars=['county_name', 'num_workers','num_vehicles'], value_vars=['Target'])
calib_target_workers_long=calib_target_workers_long.rename(columns={'county_name': 'dimension_01_value',
                                                                  'num_workers': 'dimension_02_value',
                                                                  'num_vehicles': 'dimension_03_value'})
calib_target_workers_long['dimension_01_name'] = 'county_name'
calib_target_workers_long['dimension_02_name'] = 'num_workers'
calib_target_workers_long['dimension_03_name'] = 'num_vehicles'


def model_summary(household_df, dimension_01_name, dimension_02_name, dimension_03_name, aggregate_column):


    household_grouped=household_df.groupby([dimension_01_name,dimension_02_name,dimension_03_name]).agg(total=(aggregate_column, 'count')).reset_index()

    household_grouped_totals=household_df.groupby([dimension_02_name,dimension_03_name]).agg(total=(aggregate_column, 'count')).reset_index()
    household_grouped_totals[dimension_01_name]='Total'

    auto_ownership_hhsize = pd.concat([household_grouped,household_grouped_totals], ignore_index=True)

    auto_ownership_hhsize['Total_Level_01_02']= auto_ownership_hhsize.groupby([dimension_01_name,dimension_02_name])['total'].transform(sum)
    auto_ownership_hhsize['Model']=100*auto_ownership_hhsize['total']/auto_ownership_hhsize['Total_Level_01_02']

    auto_ownership_hhsize_long=auto_ownership_hhsize.melt(id_vars=[dimension_01_name, dimension_02_name, dimension_03_name], value_vars=['Model'])
    
    auto_ownership_hhsize_long=auto_ownership_hhsize_long.rename(columns={dimension_01_name: 'dimension_01_value',
                                                                          dimension_02_name: 'dimension_02_value',
                                                                          dimension_03_name: 'dimension_03_value'})

    auto_ownership_hhsize_long['dimension_01_name'] = dimension_01_name
    auto_ownership_hhsize_long['dimension_02_name'] = dimension_02_name
    auto_ownership_hhsize_long['dimension_03_name'] = dimension_03_name

    return auto_ownership_hhsize_long[['dimension_01_name','dimension_01_value','dimension_02_name','dimension_02_value','dimension_03_name','dimension_03_value',
    'variable','value']]

model_summary_hhsize_df = model_summary(household_df, 'county_name', 'household_size','num_vehicles', 'hh_id')

model_summary_numworkers_df = model_summary(household_df, 'county_name', 'num_workers','num_vehicles', 'hh_id')

comparison_df = pd.concat([calib_target_hhsize_long,model_summary_hhsize_df, calib_target_workers_long,model_summary_numworkers_df], ignore_index=True)[['dimension_01_name','dimension_01_value','dimension_02_name','dimension_02_value','dimension_03_name','dimension_03_value','variable','value']]

writer = pd.ExcelWriter(os.path.join(set_output_dir,'autoOwnershipSummary.xlsx'), engine='xlsxwriter')

comparison_df_output=pd.pivot(comparison_df,
                              index=['dimension_01_name','dimension_01_value','dimension_02_name','dimension_02_value','dimension_03_name','dimension_03_value'],
                              columns='variable',values='value').reset_index()

comparison_df_output= comparison_df_output.rename(columns={'Model':model_results})

comparison_df_output = comparison_df_output[['dimension_01_name', 'dimension_01_value', 'dimension_02_name',
       'dimension_02_value', 'dimension_03_name', 'dimension_03_value',
       'Target',model_results]]
       
comparison_df_output.to_excel(writer, sheet_name='By HH Size', startrow=1, header=False, index=False)

workbook  = writer.book
worksheet = writer.sheets['By HH Size']
# Add a header format.
header_format = workbook.add_format({
    'bold': True,
    'text_wrap': True,
    'valign': 'top',
    'fg_color': '#D7E4BC',
    'border': 1})

# Get the dimensions of the dataframe.
(max_row, max_col) = comparison_df_output.shape

# Make the columns wider for clarity.
worksheet.set_column(0,  max_col - 1, 12)
worksheet.autofilter(0, 0, max_row, max_col - 1)

for col_num, value in enumerate(comparison_df_output.columns.values):
    worksheet.write(0, col_num, value, header_format)

writer.save()

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
fig, axes = plt.subplots(2,5)

for item in range(0,5):

    row_loc = 0
    col_loc = item

    county_name = hhsize_df['dimension_01_value'].unique()[item]

    _df = hhsize_df[hhsize_df['dimension_01_value']==county_name]

    order = ['0 Auto HH', '1 Auto HH', '2 Auto HH','3 Auto HH', '4+ Auto HH']

    sns.barplot(x='dimension_03_value', y='value', data=_df, hue='variable', ci=None,order=order, ax=axes[row_loc,col_loc])

    axes[row_loc,col_loc].figure.set_size_inches(30,10)
    axes[row_loc,col_loc].set_title('')
    axes[row_loc,col_loc].set_ylim(0, 80)
    axes[row_loc,col_loc].set_xlabel(county_name)

    if row_loc==0 and col_loc==0:
        axes[row_loc,col_loc].set_ylabel('Share of Households (Percent)')
    else:
        axes[row_loc,col_loc].set_ylabel('')
    
    for tick in axes[row_loc,col_loc].get_xticklabels():
        tick.set_rotation(90)
        #tick.set_size(15)

for item in range(5,10):

    row_loc = 1
    col_loc = item-5

    county_name = hhsize_df['dimension_01_value'].unique()[item]

    _df = hhsize_df[hhsize_df['dimension_01_value']==county_name]

    order = ['0 Auto HH', '1 Auto HH', '2 Auto HH','3 Auto HH', '4+ Auto HH']

    sns.barplot(x='dimension_03_value', y='value', data=_df, hue='variable', ci=None,order=order, ax=axes[row_loc,col_loc])

    axes[row_loc,col_loc].figure.set_size_inches(30,10)
    axes[row_loc,col_loc].set_title('')
    axes[row_loc,col_loc].set_xlabel(county_name)
    axes[row_loc,col_loc].set_ylim(0, 80)

    if row_loc==1 and col_loc==0:
        axes[row_loc,col_loc].set_ylabel('Share of Households (Percent)')
    else:
        axes[row_loc,col_loc].set_ylabel('')
    
    #axes[1,0].set_ylabel('Share of Households (Percent)')
    for tick in axes[row_loc,col_loc].get_xticklabels():
        tick.set_rotation(90)
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

    sns.barplot(x='dimension_03_value', y='value', data=_df, hue='variable', ci=None,order=order, ax=axes[col_loc])

    axes[col_loc].figure.set_size_inches(30,10)
    axes[col_loc].set_title('')
    axes[col_loc].set_ylim(0, 80)
    axes[col_loc].set_xlabel(dimension_value)
    if col_loc==0:
        axes[col_loc].set_ylabel('Share of Households (Percent)')
    else:
        axes[col_loc].set_ylabel('')
    axes[0].set_ylabel('Share of Households (Percent)')
    for tick in axes[col_loc].get_xticklabels():
        tick.set_rotation(90)
        #tick.set_size(15)

fig.tight_layout()
fig.suptitle('Auto Ownership By HH Size', y=1)
fig.savefig(os.path.join(set_output_dir, 'Auto Ownership By Household Size.png'))




hhworker_df=comparison_df[comparison_df['dimension_02_name']=='num_workers'].sort_values(by=['dimension_01_value','dimension_02_value','dimension_03_value'])

fig, axes = plt.subplots(1,len(hhworker_df.dimension_02_value.unique()))

for item in range(0,len(hhworker_df.dimension_02_value.unique())):

    row_loc = 0
    col_loc = item

    dimension_value = hhworker_df['dimension_02_value'].unique()[item]

    _df = hhworker_df[hhworker_df['dimension_02_value']==dimension_value]

    order = ['0 Auto HH', '1 Auto HH', '2 Auto HH','3 Auto HH', '4+ Auto HH']

    sns.barplot(x='dimension_03_value', y='value', data=_df, hue='variable', ci=None,order=order, ax=axes[col_loc])

    axes[col_loc].figure.set_size_inches(30,10)
    axes[col_loc].set_title('')
    axes[col_loc].set_ylim(0, 80)
    axes[col_loc].set_xlabel(dimension_value)
    if col_loc==0:
        axes[col_loc].set_ylabel('Share of Households (Percent)')
    else:
        axes[col_loc].set_ylabel('')
    #axes[0].set_ylabel('Share of Households (Percent)')
    for tick in axes[col_loc].get_xticklabels():
        tick.set_rotation(90)
        #tick.set_size(15)

fig.tight_layout()
fig.suptitle('Auto Ownership By HH Workers', y=1)
fig.savefig(os.path.join(set_output_dir, 'Auto Ownership By Household Workers.png'))