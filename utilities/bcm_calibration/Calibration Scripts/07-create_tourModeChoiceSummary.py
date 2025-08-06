import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
sns.set(color_codes=True)
import os
import xlsxwriter
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--run_name",type=str, help="Model run output file relative location")

args = parser.parse_args()

model_results=args.run_name

#Set Directory
set_model_result_dir = model_results+'/'
set_calibration_target_dir='Calibration Targets/'
set_output_dir = 'calibration_output/'+model_results+'/07_TourModeChoice/'

if not os.path.exists(set_output_dir):
    os.makedirs(set_output_dir)

print('created output directory')
#Read calibration Target

calib_target = pd.read_csv(os.path.join(set_calibration_target_dir, 'TourModeChoice_Targets.csv'))
calib_target['Tour Purpose']=calib_target['estimate'].apply(lambda x: x.split(' by ')[0].split(' of ')[1])
calib_target['Tour Purpose']=np.where(calib_target['Tour Purpose']=='Social/Visit tours',
                                      'Social tours',
                                      calib_target['Tour Purpose'])

#Read Model Results
household_df = pd.read_csv(os.path.join(set_model_result_dir, 'householdData_1.csv'))

indiv_tour_df = pd.read_csv(os.path.join(set_model_result_dir, 'indivTourData_1.csv'))
person_df=pd.read_csv(os.path.join(set_model_result_dir, 'personData_1.csv'))
person_type = person_df[['person_id','type']]

mode_dict={1:'Drive Alone',
            2:'Drive Alone',
            3:'Shared 2 Free',
            4:'Shared 2 Free',
            5:'Shared 3 Free',
            6:'Shared 3 Free',
            7:'Walk',
            8:'Bike',
            9:'Walk-Transit',
            10:'Walk-Transit',
            11:'Walk-Transit',
            12:'Walk-Transit',
            13:'Walk-Transit',
            14:'PNR-Transit',
            15:'PNR-Transit',
            16:'PNR-Transit',
            17:'PNR-Transit',
            18:'PNR-Transit',
            19:'Taxi',
            20:'TNC',
            21:'TNC-Shared'}

def tour_purpose_category(x):
    if x in ['work_med', 'work_very high', 'work_high','work_low']:
        return 'Work tours'
    elif x in ['school_grade','school_high']:
        return 'School tours'
    elif x in ['atwork_eat','atwork_maint','atwork_business']:
        return 'At-Work tours'
    elif x == 'shopping':
        return 'Shopping tours'
    elif x in ['escort_no kids','escort_kids']:
        return 'Escorting tours'
    elif x=='university':
        return 'University tours'
    elif x=='eatout':
        return 'Eat Out tours'
    elif x=='social':
        return 'Social tours'
    elif x=='othdiscr':
        return 'Discretionary tours'
    elif x=='othmaint':
        return 'Maintenance tours'
    else:
        return None
def auto_sufficiency(df):
    if df['autos']==0:
        return 'Zero-Auto'
    elif df['autos']<df['workers']:
        return 'Insufficient'
    else:
        return 'Sufficient'
household_df['Auto Sufficiency']=household_df.apply(auto_sufficiency, axis=1)
auto_sufficiency_dict=dict(zip(household_df['hh_id'], household_df['Auto Sufficiency']))

indiv_tour_df['Tour Mode']=indiv_tour_df['tour_mode'].map(mode_dict)
indiv_tour_df['Tour Purpose']=indiv_tour_df['tour_purpose'].apply(tour_purpose_category) 
indiv_tour_df['Auto Suficiency']=indiv_tour_df['hh_id'].map(auto_sufficiency_dict)
indiv_tour_df['person_id']=indiv_tour_df['person_id'].astype(str)
indiv_tour_df['tour_id']=indiv_tour_df['tour_id'].astype(str)
indiv_tour_df['unique_tour_id']=indiv_tour_df['person_id']+'-'+indiv_tour_df['tour_id']

def model_summary(tour_df, dimension_01_name, dimension_02_name, dimension_03_name, aggregate_column):


    tour_df_grouped=tour_df.groupby([dimension_01_name,dimension_02_name,dimension_03_name]).agg(total=(aggregate_column, 'count')).reset_index()

    # tour_df_grouped_totals=tour_df.groupby([dimension_01_name,dimension_03_name]).agg(total=(aggregate_column, 'count')).reset_index()
    # tour_df_grouped_totals[dimension_02_name]='All Persons'

    model_summary = tour_df_grouped

    model_summary['Total_Level_01_02']= model_summary.groupby([dimension_01_name,dimension_02_name])['total'].transform(sum)
    model_summary['Model']=model_summary['total']/model_summary['Total_Level_01_02']

    model_summary_long=model_summary.melt(id_vars=[dimension_01_name, dimension_02_name, dimension_03_name], value_vars=['Model'], value_name='Model')
    
    model_summary_long=model_summary_long.rename(columns={dimension_01_name: 'Tour Purpose',
                                                                          dimension_02_name: 'dimension_01_value',
                                                                          dimension_03_name: 'dimension_02_value'})


    return model_summary_long[['Tour Purpose','dimension_01_value','dimension_02_value','variable','Model']]

tour_mode_choice_summary= model_summary(indiv_tour_df, 'Tour Purpose', 'Auto Suficiency','Tour Mode', 'unique_tour_id')  
comparison_df = pd.merge(calib_target, 
                        tour_mode_choice_summary, 
                        on=['Tour Purpose','dimension_01_value','dimension_02_value'], how='outer')
comparison_df=comparison_df.rename(columns={'estimate_value':'Target'})
comparison_df=comparison_df[['source', 
                             'estimate', 
                             'Tour Purpose',
                             'dimension_01_name', 
                             'dimension_01_value',
                             'dimension_02_name', 
                             'dimension_02_value', 
                             'estimate_name', 
                             'Target', 
                             'Model']] 

writer = pd.ExcelWriter(os.path.join(set_output_dir,'TourModeChoiceSummary.xlsx'), engine='xlsxwriter')
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

comparison_df_long=pd.melt(comparison_df, id_vars=['Tour Purpose', 'dimension_01_value','dimension_02_name','dimension_02_value','estimate_name'],
                            value_vars=['Target', 'Model'], var_name='Legend')

sns.set_context("talk",font_scale=1.5, rc={"lines.linewidth": 2.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})

for tour in comparison_df_long['Tour Purpose'].unique():

    _df = comparison_df_long[(comparison_df_long['Tour Purpose']==tour)]
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