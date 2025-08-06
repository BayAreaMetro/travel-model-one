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
set_output_dir = 'calibration_output/'+model_results+'/03_CDAP_Summary/'

if not os.path.exists(set_output_dir):
    os.makedirs(set_output_dir)

#Read calibration Target

calib_target = pd.read_csv(os.path.join(set_calibration_target_dir, 'CDAPTargets.csv'))

#Read Model Results
cdap_results = pd.read_csv(os.path.join(set_model_result_dir, 'cdapResults.csv'))
person_df = pd.read_csv(os.path.join(set_model_result_dir, 'personData_1.csv'))

#Get the geocrosswalk
geo_crosswalk=pd.read_csv(os.path.join(set_model_result_dir,'geo_crosswalk.csv'))

taz_county_dict=dict(zip(geo_crosswalk['TAZ'], geo_crosswalk['COUNTYNAME']))


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

def replace_activitytype(x):
    if x=='H':
        return 'Home'
    elif x=='M':
        return  'Mandatory'
    elif x=='N':
        return 'Non-Mandatory'
    else:
        return x

cdap_results['PersonType']=cdap_results['PersonID'].map(dict(zip(person_df['person_id'], person_df['type'])))
cdap_results['dimension_01_value']=cdap_results.PersonType.apply(replace_persontype)
cdap_results['dimension_02_value']=cdap_results.ActivityString.apply(replace_activitytype)

calib_target['dimension_01_value']=calib_target.dimension_01_value.apply(replace_persontype)

def comparison(cdap_results, calib_target, dimension_01_value,dimension_02_value, aggregate_column):


    cdap_results_grouped=cdap_results.groupby([dimension_01_value,dimension_02_value]).agg(total=(aggregate_column, 'count')).reset_index()

    cdap_results_grouped['Total_Level_01']=cdap_results_grouped.groupby([dimension_01_value])['total'].transform(sum)

    cdap_results_grouped[model_results] = cdap_results_grouped['total']/cdap_results_grouped['Total_Level_01']

    cdap_comparison = pd.merge(calib_target,cdap_results_grouped,
                               left_on=[dimension_01_value,dimension_02_value],
                               right_on=['dimension_01_value','dimension_02_value'])


    return cdap_comparison[['source', 'estimate', 'dimension_01_name', 'dimension_01_value',
       'dimension_02_name', 'dimension_02_value', 'estimate_name',
       'estimate_value', model_results]]

comparison_df = comparison(cdap_results,calib_target,'dimension_01_value','dimension_02_value', 'PersonID' )
comparison_df = comparison_df.rename(columns={'estimate_value':'Target'})
comparison_df_long = comparison_df.melt(id_vars=['dimension_01_value','dimension_02_value'], 
                                        value_vars=['Target',model_results])

# comparison_df_long['variable']=np.where(comparison_df_long['variable']=='estimate_value',
#                                                 'Target',
#                                                 model_results)

comparison_df_long=comparison_df_long.rename(columns={'variable':'Legend'})

writer = pd.ExcelWriter(os.path.join(set_output_dir,'CDAPSummary.xlsx'), engine='xlsxwriter')
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

comparison_df_long = comparison_df.melt(id_vars=['dimension_01_value','dimension_02_value'], 
                                        value_vars=['Target',model_results])

# comparison_df_long['variable']=np.where(comparison_df_long['variable']=='estimate_value',
#                                                 'Target',
#                                                 model_results)

comparison_df_long=comparison_df_long.rename(columns={'variable':'Legend'})

###########Create figures

sns.set_context("talk",font_scale=1.5, rc={"lines.linewidth": 2.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})


for item in comparison_df_long.dimension_02_value.unique():
    _df=comparison_df_long[comparison_df_long['dimension_02_value']==item]
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
                    hue_order=['Target',model_results],
                    ci=None,
                    order=working_order)
    ax.figure.set_size_inches(25,10)
    ax.set_xlabel('Person Type')
    ax.set_ylabel('Share of Persons (Percent)')
    ax.set_title('Share of Persons for Activity Type: '+item)  
    plt.xticks(rotation=90, fontsize=15)  
    ax.figure.savefig(os.path.join(set_output_dir, 'Share of Persons For Activity Type ' +item+'.png'),bbox_inches='tight')

