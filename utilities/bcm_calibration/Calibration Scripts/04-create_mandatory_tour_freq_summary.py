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
set_output_dir = 'calibration_output/'+model_results+'/04_MandatoryTourFreq/'

if not os.path.exists(set_output_dir):
    os.makedirs(set_output_dir)

#Read calibration Target

calib_target = pd.read_csv(os.path.join(set_calibration_target_dir, 'MandatoryTourFrequencyTargets.csv'))


#Read Model Results
household_df = pd.read_csv(os.path.join(set_model_result_dir, 'householdData_1.csv'))

indiv_tour_df = pd.read_csv(os.path.join(set_model_result_dir, 'indivTourData_1.csv'))
person_df=pd.read_csv(os.path.join(set_model_result_dir, 'personData_1.csv'))
person_type = dict(zip(person_df['person_id'], person_df['type']))

def tour_purpose_category(x):
    if x in ['work_med', 'work_very high', 'work_high','work_low','work']:
        return 'Work'
    elif x in ['school_grade','school_high','school','university']:
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
        return 'Work and School'
def replace_persontype(x):
    if x=='Child too young for school':
        return 'Pre-School'
    elif x=='Pre-school':
        return 'Pre-School'
    elif x=='Retired':
        return  'Non-Working Senior'
    elif x=='Non-working senior':
        return  'Non-Working Senior'
    elif x=='Student of driving age':
        return 'Driving Age Student'
    elif x=='Driving age student':
        return 'Driving Age Student'
    elif x=='Student of non-driving age':
        return 'Non-Driving Student'
    elif x=='Non-driving student':
        return 'Non-Driving Student'
    elif x=='Non-worker':
        return 'Non-Working Adult'
    elif x=='Non-working adult':
        return 'Non-Working Adult'
    elif x=='University student':
        return 'University Student'
    elif x=='Part-time worker':
        return 'Part-Time Worker'
    elif x=='Full-time worker':
        return 'Full-Time Worker'
    elif x=='Part-time worker':
        return 'Part-Time Worker'
    else:
        return x
indiv_tour_df['Tour Purpose']=indiv_tour_df['tour_purpose'].apply(tour_purpose_category) 
indiv_tour_df['Person Type']=indiv_tour_df['person_id'].map(person_type)
indiv_tour_df['Person Type']=indiv_tour_df['Person Type'].apply(replace_persontype)
calib_target['dimension_01_value']=calib_target['dimension_01_value'].apply(replace_persontype)
                              
indiv_tour_df['person_id']=indiv_tour_df['person_id'].astype(str)
indiv_tour_df['tour_id']=indiv_tour_df['tour_id'].astype(str)
indiv_tour_df['unique_tour_id']=indiv_tour_df['person_id']+'-'+indiv_tour_df['tour_id']

df = indiv_tour_df[indiv_tour_df['tour_category']=='MANDATORY'].groupby(['person_id','Person Type','Tour Purpose']).agg(Number_of_tours=('unique_tour_id','count')).reset_index()
non_mandatory_wide=df.pivot(index=['person_id','Person Type'], columns='Tour Purpose', values='Number_of_tours').reset_index().fillna(0)
non_mandatory_wide['Work and School'] = non_mandatory_wide['School']*non_mandatory_wide['Work']
calib_target['Tour Purpose']=calib_target['dimension_02_value'].apply(lambda x: x.split(' ')[1])
calib_target['Tour Purpose']=calib_target['Tour Purpose'].apply(tour_purpose_category) 
calib_target['dimension_02_value']=calib_target['dimension_02_value'].apply(lambda x: float(x.split(' ')[0].replace('Work','0')))
sorter=['Number of Work Tours','Number of University Tours','Number of School Tours','Number of Work and School Tours']
sorterIndex = dict(zip(sorter, range(len(sorter))))

non_mandatory_wide_long=pd.melt(non_mandatory_wide, 
                                id_vars=['person_id','Person Type'],
                                value_vars=['School', 'Work','Work and School'],
                                value_name='Number of Tours')
non_mandatory_wide_long_grouped=non_mandatory_wide_long.groupby(['Person Type','Tour Purpose','Number of Tours']).agg({'person_id':'count'}).reset_index()
non_mandatory_wide_long_grouped=non_mandatory_wide_long_grouped[non_mandatory_wide_long_grouped['Number of Tours']!=0]

non_mandatory_wide_long_grouped['Total']=non_mandatory_wide_long_grouped.groupby(['Person Type'])['person_id'].transform(sum)
non_mandatory_wide_long_grouped[model_results]=non_mandatory_wide_long_grouped['person_id']/non_mandatory_wide_long_grouped['Total']

non_mandatory_wide_long_grouped=non_mandatory_wide_long_grouped.rename(columns={'Person Type':'dimension_01_value',
                                                                                'Number of Tours':'dimension_02_value'})

comparison_df=pd.merge(calib_target, non_mandatory_wide_long_grouped[['dimension_01_value','Tour Purpose','dimension_02_value',model_results]],
                        on=['dimension_01_value','Tour Purpose','dimension_02_value'], how='outer')


writer = pd.ExcelWriter(os.path.join(set_output_dir,'SchoolLocationTLFD_Summary.xlsx'), engine='xlsxwriter')
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


comparison_df_long=pd.melt(comparison_df, id_vars=['dimension_01_value','Tour Purpose', 'dimension_02_name','dimension_02_value'],
                            value_vars=['estimate_value', model_results], var_name='Legend')

comparison_df_long['dimension_02_name']=comparison_df_long['Tour Purpose'].apply(lambda x: 'Number of '+x+' Tours')

comparison_df_long=pd.melt(comparison_df, id_vars=['dimension_01_value','Tour Purpose', 'dimension_02_name','dimension_02_value'],
                            value_vars=['estimate_value', model_results], var_name='Legend')

comparison_df_long['dimension_02_name']=comparison_df_long['Tour Purpose'].apply(lambda x: 'Number of '+x+' Tours')
comparison_df_long['Legend']=np.where(comparison_df_long['Legend']==model_results,model_results, 'Target')
comparison_df_long=comparison_df_long[comparison_df_long['dimension_02_value']!=0]
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
sns.barplot(x='dimension_02_value', 
            y='value', 
            data=_figure_df, 
            hue='Legend',
            hue_order=['Target', model_results], 
            ci=None, 
            ax= axes[0])

axes[0].figure.set_size_inches(30,10)
axes[0].set_ylim(0,100)
axes[0].set_xlabel('Number of '+tour_purpose+' Tours', fontsize=20)
axes[0].set_ylabel('Share of Persons (Percent)', fontsize=20)
axes[0].set_xticklabels(axes[0].get_xticks(), fontsize=20)
axes[0].set_yticklabels(axes[0].get_yticks(), fontsize=20)
#plt.legend(loc='upper right', title='Legend', fontsize=15) 

tour_purpose = 'School'

_figure_df=_df[_df['Tour Purpose']==tour_purpose]
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend',hue_order=['Target', model_results], ci=None, ax= axes[1])

axes[1].figure.set_size_inches(30,10)
axes[1].set_ylim(0,100)
axes[1].set_xlabel('Number of '+tour_purpose+' Tours', fontsize=20)
axes[1].set_ylabel('Share of Persons (Percent)', fontsize=20)
axes[1].set_xticklabels(axes[1].get_xticks(), fontsize=20)
axes[1].set_yticklabels(axes[1].get_yticks(), fontsize=20)
#plt.legend(loc='upper right', title='Legend', fontsize=15) 


tour_purpose = 'Work and School'

_figure_df=_df[_df['Tour Purpose']==tour_purpose]
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend',hue_order=['Target', model_results], ci=None, ax= axes[2])

axes[2].figure.set_size_inches(30,10)
axes[2].set_ylim(0,100)
axes[2].set_xlabel('Number of '+tour_purpose+' Tours', fontsize=20)
axes[2].set_ylabel('Share of Persons (Percent)', fontsize=20)
axes[2].set_xticklabels(axes[2].get_xticks(), fontsize=20)
axes[2].set_yticklabels(axes[2].get_yticks(), fontsize=20)
#plt.legend(loc='upper right', title='Legend', fontsize=15) 
fig.suptitle('Share of Persons by Number of Mandatory Tours by Person Type: '+persontype)
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
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend',hue_order=['Target', model_results], ci=None, ax= axes[0])

axes[0].figure.set_size_inches(30,10)
axes[0].set_ylim(0,100)
axes[0].set_xlabel('Number of '+tour_purpose+' Tours', fontsize=20)
axes[0].set_ylabel('Share of Persons (Percent)', fontsize=20)
axes[0].set_xticklabels(axes[0].get_xticks(), fontsize=20)
axes[0].set_yticklabels(axes[0].get_yticks(), fontsize=20)
#plt.legend(loc='upper right', title='Legend', fontsize=15) 

tour_purpose = 'School'

_figure_df=_df[_df['Tour Purpose']==tour_purpose]
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend',hue_order=['Target', model_results], ci=None, ax= axes[1])

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
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend',hue_order=['Target', model_results], ci=None, ax= axes)

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
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend',hue_order=['Target', model_results], ci=None, ax= axes)

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
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend',hue_order=['Target', model_results], ci=None, ax= axes)

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
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend',hue_order=['Target', model_results], ci=None, ax= axes[0])

axes[0].figure.set_size_inches(30,10)
axes[0].set_ylim(0,100)
axes[0].set_xlabel('Number of '+tour_purpose+' Tours', fontsize=20)
axes[0].set_ylabel('Share of Persons (Percent)', fontsize=20)
axes[0].set_xticklabels(axes[0].get_xticks(), fontsize=20)
axes[0].set_yticklabels(axes[0].get_yticks(), fontsize=20)
#plt.legend(loc='upper right', title='Legend', fontsize=15) 

tour_purpose = 'School'

_figure_df=_df[_df['Tour Purpose']==tour_purpose]
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend',hue_order=['Target', model_results], ci=None, ax= axes[1])

axes[1].figure.set_size_inches(30,10)
axes[1].set_ylim(0,100)
axes[1].set_xlabel('Number of '+tour_purpose+' Tours', fontsize=20)
axes[1].set_ylabel('Share of Persons (Percent)', fontsize=20)
axes[1].set_xticklabels(axes[1].get_xticks(), fontsize=20)
axes[1].set_yticklabels(axes[1].get_yticks(), fontsize=20)
#plt.legend(loc='upper right', title='Legend', fontsize=15) 


tour_purpose = 'Work and School'

_figure_df=_df[_df['Tour Purpose']==tour_purpose]
sns.barplot(x='dimension_02_value', y='value', data=_figure_df, hue='Legend',hue_order=['Target', model_results], ci=None, ax= axes[2])

axes[2].figure.set_size_inches(30,10)
axes[2].set_ylim(0,100)
axes[2].set_xlabel('Number of '+tour_purpose+' Tours', fontsize=20)
axes[2].set_ylabel('Share of Persons (Percent)', fontsize=20)
axes[2].set_xticklabels(axes[2].get_xticks(), fontsize=20)
axes[2].set_yticklabels(axes[2].get_yticks(), fontsize=20)
#plt.legend(loc='upper right', title='Legend', fontsize=15) 
fig.suptitle('Share of Persons by Number of Mandatory Tours by Person Type: '+persontype)
fig.savefig(os.path.join(set_output_dir, 'Mandatory Tour Frequency by Person Type '+persontype+'.png'))