import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
sns.set(color_codes=True)
import os
import glob
import xlsxwriter
import argparse
import math


parser = argparse.ArgumentParser()
parser.add_argument("--run_name",type=str, help="Model run output file relative location")

args = parser.parse_args()

model_results=args.run_name

#Set Directory
set_model_result_dir = model_results+'/'
set_calibration_target_dir='Calibration Targets/'
set_output_dir = 'calibration_output/'+model_results+'/06_TourTOD/'


if not os.path.exists(set_output_dir):
    os.makedirs(set_output_dir)

calib_target = pd.read_csv(os.path.join(set_calibration_target_dir, 'TourTOD_Targets_Hourly.csv'))

all_person_calib_target = pd.read_csv(os.path.join(set_calibration_target_dir, 'NumberofTours_byTOD_Targets_Hourly.csv'))

calib_target_all_persons = all_person_calib_target.groupby(['estimate','dimension_02_name','dimension_02_value']).agg(number_of_tours=('estimate_value','sum'))


calib_target_all_persons['Total']=calib_target_all_persons.groupby('estimate')['number_of_tours'].transform('sum')

calib_target_all_persons['estimate_value']=calib_target_all_persons['number_of_tours']/calib_target_all_persons['Total']

calib_target_all_persons['dimension_01_value']='All Persons'

calib_target_all_persons=calib_target_all_persons.reset_index()

def time_bin(x):
    if x ==12:
        end_time = '12:00 pm'   
    elif x <12:
        end_time = str(x).split('.')[0]+':00 am'
    elif x==24:
        end_time = '12:00 am'
    else:
        end_time = str(x-12).split('.')[0]+':00 pm'

    return end_time

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


def model_summary(tour_df, dimension_01_name, dimension_02_name, dimension_03_name, aggregate_column):


    tour_df_grouped=tour_df.groupby([dimension_01_name,dimension_02_name,dimension_03_name]).agg(total=(aggregate_column, 'count')).reset_index()

    tour_df_grouped_totals=tour_df.groupby([dimension_01_name,dimension_03_name]).agg(total=(aggregate_column, 'count')).reset_index()
    tour_df_grouped_totals[dimension_02_name]='All Persons'

    model_summary = pd.concat([tour_df_grouped,tour_df_grouped_totals], ignore_index=True)

    model_summary['Total_Level_01_02']= model_summary.groupby([dimension_01_name,dimension_02_name])['total'].transform(sum)
    model_summary['Model']=model_summary['total']/model_summary['Total_Level_01_02']

    # model_summary_long=model_summary.melt(id_vars=[dimension_01_name, dimension_02_name, dimension_03_name], value_vars=['Model'], value_name='Model')
    
    model_summary=model_summary.rename(columns={dimension_01_name: 'Tour Purpose',
                                                        dimension_02_name: 'dimension_01_value',
                                                        dimension_03_name: 'dimension_02_value'})


    return model_summary

#Read Model Results
household_df = pd.read_csv(os.path.join(set_model_result_dir, 'householdData_1.csv'))
indiv_tour_df = pd.read_csv(os.path.join(set_model_result_dir, 'indivTourData_1.csv'))
person_df=pd.read_csv(os.path.join(set_model_result_dir, 'personData_1.csv'))
person_type = person_df[['person_id','type']]
person_type['PersonType']=person_df['type'].apply(replace_persontype)
person_type_dict = dict(zip(person_type['person_id'],person_type['PersonType']))

indiv_tour_df['PersonType']=indiv_tour_df['person_id'].map(person_type_dict)
indiv_tour_df['Duration']=indiv_tour_df['end_hour']-indiv_tour_df['start_hour']+1
indiv_tour_df['person_id']=indiv_tour_df['person_id'].astype(str)
indiv_tour_df['tour_id']=indiv_tour_df['tour_id'].astype(str)
indiv_tour_df['unique_tour_id']=indiv_tour_df['person_id']+'-'+indiv_tour_df['tour_id']



indiv_tour_df['Tour Purpose']=indiv_tour_df['tour_purpose'].apply(tour_purpose_category)
indiv_tour_df['Departure Time-of-day Category']=indiv_tour_df['start_hour'].apply(time_bin)
indiv_tour_df['Arrival Time-of-day Category']=indiv_tour_df['end_hour'].apply(time_bin)
person_type['PersonType']=person_df['type'].apply(replace_persontype)

calib_target['Tour Purpose']=calib_target['estimate'].apply(lambda x: x.split(' by ')[0].split(' of ')[1])
calib_target['Tour Purpose']=np.where(calib_target['Tour Purpose']=='Social/Visit tours',
                                      'Social tours',
                                      calib_target['Tour Purpose']) 
calib_target['dimension_01_value']=calib_target['dimension_01_value'].apply(replace_persontype)

calib_target_all_persons['Tour Purpose']=calib_target_all_persons['estimate'].apply(lambda x: x.split(' by ')[0].split(' of ')[1])
calib_target_all_persons['Tour Purpose']=np.where(calib_target_all_persons['Tour Purpose']=='Social/Visit tours',
                                                  'Social tours',
                                                  calib_target_all_persons['Tour Purpose'])

calib_target_all=pd.concat([calib_target, calib_target_all_persons], ignore_index=True)

time_period_target = calib_target_all[calib_target_all['dimension_02_name'].isin(['Departure Time-of-day Category','Arrival Time-of-day Category'])]
time_period_target['dimension_02_value']=time_period_target['dimension_02_value'].apply(lambda x: x.split(' to ')[0])

time_period_target_grouped=time_period_target.groupby(['estimate',
                                                       'Tour Purpose',
                                                       'dimension_01_value',
                                                       'dimension_02_name', 
                                                       'dimension_02_value']).agg(Target=('estimate_value','sum')).reset_index()

duration_target = calib_target_all[~calib_target_all['dimension_02_name'].isin(['Departure Time-of-day Category','Arrival Time-of-day Category'])]
duration_target['dimension_02_value']=duration_target['dimension_02_value'].astype(float).apply(lambda x: math.ceil(x))
duration_target_grouped = duration_target.groupby([ 'estimate',
                                                    'Tour Purpose',
                                                    'dimension_01_value',
                                                    'dimension_02_name', 
                                                    'dimension_02_value']).agg(Target=('estimate_value','sum')).reset_index()


model_summary_departure_df = model_summary(indiv_tour_df, 'Tour Purpose', 'PersonType','Departure Time-of-day Category', 'unique_tour_id')
departure_target=time_period_target_grouped[time_period_target_grouped['dimension_02_name']=='Departure Time-of-day Category']

model_summary_departure_df_comparison = pd.merge(departure_target, 
                                             model_summary_departure_df, 
                                             on=['Tour Purpose','dimension_01_value','dimension_02_value'], how='outer')
model_summary_departure_df_comparison['Model']=model_summary_departure_df_comparison['Model'].fillna(0)
model_summary_departure_df_comparison['dimension_02_name']=model_summary_departure_df_comparison['dimension_02_name'].fillna('Departure Time-of-day Category')  
  


model_summary_arrival_df = model_summary(indiv_tour_df, 'Tour Purpose', 'PersonType','Arrival Time-of-day Category', 'unique_tour_id')
arrival_target=time_period_target_grouped[time_period_target_grouped['dimension_02_name']=='Arrival Time-of-day Category']
model_summary_arrival_df_comparison = pd.merge(arrival_target, 
                                             model_summary_arrival_df, 
                                             on=['Tour Purpose','dimension_01_value','dimension_02_value'], how='outer')
model_summary_arrival_df_comparison['Model']=model_summary_arrival_df_comparison['Model'].fillna(0)
model_summary_arrival_df_comparison['dimension_02_name']=model_summary_arrival_df_comparison['dimension_02_name'].fillna('Arrival Time-of-day Category')  



model_summary_duration_df = model_summary(indiv_tour_df, 'Tour Purpose', 'PersonType','Duration', 'unique_tour_id')

model_summary_duration_df_comparison = pd.merge(duration_target_grouped, 
                                             model_summary_duration_df, 
                                             on=['Tour Purpose','dimension_01_value','dimension_02_value'], how='outer')
model_summary_duration_df_comparison['Model']=model_summary_duration_df_comparison['Model'].fillna(0)
model_summary_duration_df_comparison['dimension_02_name']=model_summary_duration_df_comparison['dimension_02_name'].fillna('Duration in Hours')  


comparison_df = pd.concat([model_summary_departure_df_comparison,
                           model_summary_arrival_df_comparison, model_summary_duration_df_comparison], ignore_index=True)
                     
comparison_df=comparison_df[['estimate', 
                             'Tour Purpose',
                             'dimension_01_value',
                             'dimension_02_name', 
                             'dimension_02_value', 
                             'Target', 
                             'Model']]

comparison_df=comparison_df.rename(columns={'Model':model_results})
comparison_df_long=pd.melt(comparison_df, id_vars=['Tour Purpose', 'dimension_01_value','dimension_02_name','dimension_02_value'],
                            value_vars=['Target', model_results], var_name='Legend')

writer = pd.ExcelWriter(os.path.join(set_output_dir,'TourTODSummary.xlsx'), engine='xlsxwriter')
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


comparison_df = pd.concat([model_summary_departure_df_comparison,
                           model_summary_arrival_df_comparison], ignore_index=True)

comparison_df_long=pd.melt(comparison_df, id_vars=['Tour Purpose', 'dimension_01_value','dimension_02_name','dimension_02_value'],
                            value_vars=['Target', 'Model'], var_name='Legend')

#############Create tour level summary

departure_target_grouped=departure_target[departure_target['dimension_01_value']=='All Persons'][['Tour Purpose','dimension_02_value','Target']]

tour_df_grouped=indiv_tour_df.groupby(['Tour Purpose','Departure Time-of-day Category']).agg(total=('unique_tour_id', 'count')).reset_index()

tour_df_grouped['Total Tours by Purpose']= tour_df_grouped.groupby('Tour Purpose')['total'].transform(sum)
tour_df_grouped['Model']=tour_df_grouped['total']/tour_df_grouped['Total Tours by Purpose']
tour_df_grouped=tour_df_grouped.rename(columns={'Departure Time-of-day Category':'dimension_02_value'})

model_summary_departure = pd.merge(departure_target_grouped, tour_df_grouped, 
                        on=['Tour Purpose','dimension_02_value'],
                        how='outer')
model_summary_departure_long=model_summary_departure.melt(id_vars=['Tour Purpose','dimension_02_value'], 
                                        value_vars=['Target','Model'])

model_summary_departure_long['Estimate']='Departure TOD'
model_summary_departure_long=model_summary_departure_long.rename(columns={'variable':'Legend'})

arrival_target_grouped=arrival_target[arrival_target['dimension_01_value']=='All Persons'][['Tour Purpose','dimension_02_value','Target']]

tour_df_grouped=indiv_tour_df.groupby(['Tour Purpose','Arrival Time-of-day Category']).agg(total=('unique_tour_id', 'count')).reset_index()

tour_df_grouped['Total Tours by Purpose']= tour_df_grouped.groupby('Tour Purpose')['total'].transform(sum)
tour_df_grouped['Model']=tour_df_grouped['total']/tour_df_grouped['Total Tours by Purpose']
tour_df_grouped=tour_df_grouped.rename(columns={'Arrival Time-of-day Category':'dimension_02_value'})

model_summary_arrival = pd.merge(arrival_target_grouped, tour_df_grouped, 
                        on=['Tour Purpose','dimension_02_value'],
                        how='outer')
model_summary_arrival_long=model_summary_arrival.melt(id_vars=['Tour Purpose','dimension_02_value'], 
                                        value_vars=['Target','Model'])

model_summary_arrival_long['Estimate']='Arrival TOD'
model_summary_arrival_long=model_summary_arrival_long.rename(columns={'variable':'Legend'})

model_summary_all = pd.concat([model_summary_departure_long, model_summary_arrival_long], ignore_index=True)

model_summary_all.to_excel(writer, sheet_name='TourLevelSummary', startrow=1, header=False, index=False)

workbook  = writer.book
worksheet = writer.sheets['TourLevelSummary']
# Add a header format.
header_format = workbook.add_format({
    'bold': True,
    'text_wrap': True,
    'valign': 'top',
    'fg_color': '#D7E4BC',
    'border': 1})

# Get the dimensions of the dataframe.
(max_row, max_col) = model_summary_all.shape

# Make the columns wider for clarity.
worksheet.set_column(0,  max_col - 1, 12)
worksheet.autofilter(0, 0, max_row, max_col - 1)

for col_num, value in enumerate(model_summary_all.columns.values):
    worksheet.write(0, col_num, value, header_format)

writer.save()

###########Create figures

duration_long=model_summary_duration_df_comparison.melt(id_vars=['Tour Purpose', 
                                                                 'dimension_01_value',
                                                                 'dimension_02_name',
                                                                 'dimension_02_value'],
                            value_vars=['Target', 'Model'], var_name='Legend')
sns.set_context("talk",font_scale=1, rc={"lines.linewidth": 2.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})

for tour in duration_long['Tour Purpose'].unique():
    duration_dir = set_output_dir+'/'+tour+'/duration/'
    if not os.path.exists(duration_dir):
        os.makedirs(duration_dir)
    for persontype in duration_long['dimension_01_value'].unique():
        _df = duration_long[(duration_long['Tour Purpose']==tour)&(duration_long['dimension_01_value']==persontype)]
        _df['value']=_df['value'].fillna(0)
        _df['value']=100*_df['value']

        fig, ax = plt.subplots()

        ax=sns.lineplot(data=_df,
                        x='dimension_02_value',
                        y='value',
                        hue='Legend')

        ax.figure.set_size_inches(15,10)
        ax.set_title('Share of Tours by Duration, Tour Purpose ' + tour+ ' Person Type ' + persontype)
        ax.set_xlabel('Duration (Hours)')
        ax.set_ylabel('Share of Tours (Percentage)')
        ax.figure.savefig(os.path.join(duration_dir, 'Share of Tours by Duration For Tour Purpose '+ tour+ ' Person Type ' + persontype+'.png'),bbox_inches='tight')

sns.set_context("talk",font_scale=1, rc={"lines.linewidth": 2.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})

for tour in duration_long['Tour Purpose'].unique():
    _df = duration_long[(duration_long['Tour Purpose']==tour)&(duration_long['dimension_01_value']=='All Persons')]
    _df['value']=_df['value'].fillna(0)
    _df['value']=100*_df['value']

    fig, ax = plt.subplots()

    ax=sns.lineplot(data=_df,
                    x='dimension_02_value',
                    y='value',
                    hue='Legend')

    ax.figure.set_size_inches(15,10)
    ax.set_title('Share of Tours by Duration, Tour Purpose: ' + tour)
    ax.set_xlabel('Duration (Hours)')
    ax.set_ylabel('Share of Tours (Percentage)')
    ax.figure.savefig(os.path.join(set_output_dir, 'Duration_'+ tour+'.png'),bbox_inches='tight')


sorter=['12:00 am', '1:00 am', '2:00 am', '3:00 am','4:00 am','5:00 am','6:00 am', '7:00 am', '8:00 am',
       '9:00 am','10:00 am','11:00 am','12:00 pm', '1:00 pm', '2:00 pm', '3:00 pm', 
       '4:00 pm','5:00 pm', '6:00 pm','7:00 pm', '8:00 pm', '9:00 pm','10:00 pm','11:00 pm']
sorterIndex = dict(zip(sorter, range(len(sorter))))
departure_long=comparison_df_long[comparison_df_long['dimension_02_name']=='Departure Time-of-day Category']
sns.set_context("talk",font_scale=1, rc={"lines.linewidth": 3})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})

for tour in departure_long['Tour Purpose'].unique():
    departure_dir = set_output_dir+'/'+tour+'/departure/'
    if not os.path.exists(departure_dir):
        os.makedirs(departure_dir)
    for persontype in departure_long['dimension_01_value'].unique():
        _df = departure_long[(departure_long['Tour Purpose']==tour)&(departure_long['dimension_01_value']==persontype)]
        _df['value']=_df['value'].fillna(0)
        tp_available = _df.dimension_02_value.unique()

        unavailable_tp=[]

        for tp in sorter:
            if tp not in tp_available:
                    unavailable_tp.append(tp)
        unavailable_tp_df=pd.DataFrame(unavailable_tp, columns=['dimension_02_value'])
        unavailable_tp_df['value']=0
        unavailable_tp_df['Legend']='Model'
        _df_all = pd.concat([_df, unavailable_tp_df], ignore_index=True)
        _df_all=_df_all.sort_values(by='dimension_02_value',key=lambda x: x.map(sorterIndex))
        _df_all['value']=100*_df_all['value']

        fig, ax = plt.subplots()

        ax=sns.lineplot(data=_df_all,
                        x='dimension_02_value',
                        y='value',
                        hue='Legend',
                        hue_order=['Target','Model'])

        ax.figure.set_size_inches(30,10)
        ax.set_ylim(0, math.ceil(_df_all['value'].max()+5))
        ax.set_title('Share of Tours by Departure Time, Tour Purpose ' + tour+ ' Person Type ' + persontype)
        ax.set_xlabel('Departure Time')
        ax.set_ylabel('Share of Tours (Percentage)')
        plt.xticks(['1:00 am','3:00 am', '5:00 am','7:00 am','9:00 am','11:00 am','1:00 pm',
                    '3:00 pm','5:00 pm', '7:00 pm','9:00 pm','11:00 pm'], fontsize=15, rotation=90)
        plt.legend(loc='upper right', fontsize=15)
        plt.xlim('1:00 am', '11:00 pm')
        ax.figure.savefig(os.path.join(departure_dir, 'Share of Tours by Departure Time For Tour Purpose '+ tour+ ' Person Type ' + persontype+'.png'),bbox_inches='tight')

arrival_long=comparison_df_long[comparison_df_long['dimension_02_name']=='Arrival Time-of-day Category']
sns.set_context("talk",font_scale=1, rc={"lines.linewidth": 3})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})

for tour in arrival_long['Tour Purpose'].unique():
    arrival_dir = set_output_dir+'/'+tour+'/arrival/'
    if not os.path.exists(arrival_dir):
        os.makedirs(arrival_dir)
    for persontype in arrival_long['dimension_01_value'].unique():
        _df = arrival_long[(arrival_long['Tour Purpose']==tour)&(arrival_long['dimension_01_value']==persontype)]
        _df['value']=_df['value'].fillna(0)
        tp_available = _df.dimension_02_value.unique()

        unavailable_tp=[]

        for tp in sorter:
            if tp not in tp_available:
                    unavailable_tp.append(tp)
        unavailable_tp_df=pd.DataFrame(unavailable_tp, columns=['dimension_02_value'])
        unavailable_tp_df['value']=0
        unavailable_tp_df['Legend']='Model'
        _df_all = pd.concat([_df, unavailable_tp_df], ignore_index=True)
        _df_all=_df_all.sort_values(by='dimension_02_value',key=lambda x: x.map(sorterIndex))
        _df_all['value']=100*_df_all['value']

        fig, ax = plt.subplots()

        ax=sns.lineplot(data=_df_all,
                        x='dimension_02_value',
                        y='value',
                        hue='Legend',
                        hue_order=['Target','Model'])

        ax.figure.set_size_inches(30,10)
        ax.set_ylim(0, math.ceil(_df_all['value'].max()+5))
        ax.set_title('Share of Tours by Arrival Time, Tour Purpose ' + tour+ ' Person Type ' + persontype, fontsize=25)
        ax.set_xlabel('Arrival Time')
        ax.set_ylabel('Share of Tours (Percentage)')
        
        plt.xticks(['1:00 am','3:00 am', '5:00 am','7:00 am','9:00 am','11:00 am','1:00 pm','3:00 pm','5:00 pm', 
                    '7:00 pm','9:00 pm','11:00 pm'], fontsize=15, rotation=90)
        plt.legend(loc='upper right', fontsize=15)
        plt.xlim('1:00 am', '11:00 pm')
        ax.figure.savefig(os.path.join(arrival_dir, 'Share of Tours by Arrival Time For Tour Purpose '+ tour+ ' Person Type ' + persontype+'.png'),bbox_inches='tight')




sns.set_context("talk",font_scale=12, rc={"lines.linewidth": 3})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})
departure_long = model_summary_all[model_summary_all['Estimate']=='Departure TOD']

for tour in departure_long['Tour Purpose'].unique():
    departure_dir = set_output_dir
    _df = departure_long[(departure_long['Tour Purpose']==tour)]
    _df['value']=_df['value'].fillna(0)
    tp_available = _df.dimension_02_value.unique()

    unavailable_tp=[]

    for tp in sorter:
        if tp not in tp_available:
                unavailable_tp.append(tp)
    unavailable_tp_df=pd.DataFrame(unavailable_tp, columns=['dimension_02_value'])
    unavailable_tp_df['value']=0
    unavailable_tp_df['Legend']='Model'
    _df_all = pd.concat([_df, unavailable_tp_df], ignore_index=True)
    _df_all=_df_all.sort_values(by='dimension_02_value',key=lambda x: x.map(sorterIndex))
    _df_all['value']=100*_df_all['value']

    fig, ax = plt.subplots()

    ax=sns.lineplot(data=_df_all,
                    x='dimension_02_value',
                    y='value',
                    hue='Legend',
                    hue_order=['Target','Model'])

    ax.figure.set_size_inches(30,10)
    ax.set_ylim(0, math.ceil(_df_all['value'].max()+5))
    ax.set_title('Share of Tours by Departure Time, Tour Purpose ' + tour)
    ax.set_xlabel('Departure Time')
    ax.set_ylabel('Share of Tours (Percentage)')
    plt.xticks(['12:00 am', '6:00 am','9:00 am','12:00 pm','4:00 pm','7:00 pm', '11:00 pm'], fontsize=15, rotation=90)
    ax.figure.savefig(os.path.join(departure_dir, 'Departure_'+ tour+'.png'),bbox_inches='tight')

arrival_long=model_summary_all[model_summary_all['Estimate']=='Arrival TOD']
sns.set_context("paper",font_scale=2, rc={"lines.linewidth": 3})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})

for tour in arrival_long['Tour Purpose'].unique():
    arrival_dir = set_output_dir
    _df = arrival_long[(arrival_long['Tour Purpose']==tour)]
    _df['value']=_df['value'].fillna(0)
    tp_available = _df.dimension_02_value.unique()

    unavailable_tp=[]

    for tp in sorter:
        if tp not in tp_available:
                unavailable_tp.append(tp)
    unavailable_tp_df=pd.DataFrame(unavailable_tp, columns=['dimension_02_value'])
    unavailable_tp_df['value']=0
    unavailable_tp_df['Legend']='Model'
    _df_all = pd.concat([_df, unavailable_tp_df], ignore_index=True)
    _df_all=_df_all.sort_values(by='dimension_02_value',key=lambda x: x.map(sorterIndex))
    _df_all['value']=100*_df_all['value']

    fig, ax = plt.subplots()

    ax=sns.lineplot(data=_df_all,
                    x='dimension_02_value',
                    y='value',
                    hue='Legend',
                    hue_order=['Target','Model'])

    ax.figure.set_size_inches(30,10)
    ax.set_ylim(0, math.ceil(_df_all['value'].max()+5))
    ax.set_title('Share of Tours by Arrival Time, Tour Purpose ' + tour)
    ax.set_xlabel('Arrival Time')
    ax.set_ylabel('Share of Tours (Percentage)')
    plt.xticks(['12:00 am', '6:00 am','9:00 am','12:00 pm','4:00 pm','7:00 pm', '11:00 pm'], fontsize=15, rotation=90)
    ax.figure.savefig(os.path.join(arrival_dir, 'Arrival_'+ tour+'.png'),bbox_inches='tight')