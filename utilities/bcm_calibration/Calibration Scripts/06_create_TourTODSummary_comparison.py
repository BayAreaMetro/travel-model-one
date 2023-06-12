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
set_output_dir = 'calibration_output/'+last_run_name+'/06_TourTOD/Comparison/'
 
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
        
    if os.path.exists(os.path.join(calibration_dir, run_name , '06_TourTOD')):
        _df = pd.read_excel(os.path.join(calibration_dir, run_name,'06_TourTOD','TourTODSummary.xlsx'))
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

###########
comparison_df=comparison_df.rename(columns={'variable':'Legend'})

departure_long=comparison_df[(comparison_df['dimension_02_name']=='Departure Time-of-day Category')&
                             (comparison_df['dimension_01_value']=='All Persons')]

arrival_long=comparison_df[(comparison_df['dimension_02_name']=='Arrival Time-of-day Category')&
                           (comparison_df['dimension_01_value']=='All Persons')]

duration_long=comparison_df[(comparison_df['dimension_02_name']=='Duration in Hours')&
                           (comparison_df['dimension_01_value']=='All Persons')]
sns.set_context("talk",font_scale=1, rc={"lines.linewidth": 2.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})

for tour in duration_long['Tour Purpose'].unique():

    _df = duration_long[(duration_long['Tour Purpose']==tour)&(duration_long['dimension_01_value']=='All Persons')]

    _df['value']=100*_df['value']

    fig, ax = plt.subplots()

    ax=sns.lineplot(data=_df,
                    x='dimension_02_value',
                    y='value',
                    hue='Legend',
                    hue_order=hue_order)

    ax.figure.set_size_inches(15,10)
    ax.set_title('Share of Tours by Duration, Tour Purpose ' + tour)
    ax.set_xlabel('Duration (Hours)', fontsize=25)
    ax.set_ylabel('Share of Tours (Percentage)', fontsize=25)
    ax.figure.savefig(os.path.join(set_output_dir, 'Duration_'+ tour+'.png'),bbox_inches='tight')


sorter=['12:00 am', '1:00 am', '2:00 am', '3:00 am','4:00 am','5:00 am','6:00 am', '7:00 am', '8:00 am',
       '9:00 am','10:00 am','11:00 am','12:00 pm', '1:00 pm', '2:00 pm', '3:00 pm', 
       '4:00 pm','5:00 pm', '6:00 pm','7:00 pm', '8:00 pm', '9:00 pm','10:00 pm','11:00 pm']
sorterIndex = dict(zip(sorter, range(len(sorter))))

sns.set_context("paper",font_scale=2.5, rc={"lines.linewidth": 3})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})
for tour in departure_long['Tour Purpose'].unique():
    _arrival_df=arrival_long[(arrival_long['Tour Purpose']==tour)]
    _df = departure_long[(departure_long['Tour Purpose']==tour)]
    max_share_arrival = int(100* _arrival_df.value.max())
    max_share_departure = int(100* _df.value.max())
    _df['value']=100*_df['value']

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
    # _df_all['value']=_df_all['value'].fillna(0)

    fig, ax = plt.subplots()
    print(tour)
    ax=sns.lineplot(data=_df_all,
                    x='dimension_02_value',
                    y='value',
                    hue='Legend',
                    hue_order=hue_order)

    ax.figure.set_size_inches(30,10)
    ax.set_yticks(range(0, max(max_share_arrival,max_share_departure)+5, 5))
    ax.set_ylim(0, max(max_share_arrival,max_share_departure)+5)
    ax.set_title('Share of Tours by Departure Time, Tour Purpose ' + tour+ ' for All Person Types')
    ax.set_xlabel('Departure Time', fontsize=25)
    ax.set_ylabel('Share of Tours (Percentage)', fontsize=25)
    #ax.set_xticklabels(['1:00 am','3:00 am', '5:00 am','7:00 am','9:00 am','11:00 am','1:00 pm','3:00 pm','5:00 pm', '7:00 pm','9:00 pm','11:00 pm'])
    plt.xticks(['1:00 am','3:00 am', '5:00 am','7:00 am','9:00 am','11:00 am','1:00 pm','3:00 pm','5:00 pm', 
                '7:00 pm','9:00 pm','11:00 pm'], fontsize=15, rotation=90)
    plt.legend(loc='upper right', fontsize=15)
    plt.xlim('1:00 am', '11:00 pm')
    ax.figure.savefig(os.path.join(set_output_dir, tour+ '_Departure.png'),bbox_inches='tight')

sns.set_context("paper",font_scale=2.5, rc={"lines.linewidth": 3})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})
for tour in arrival_long['Tour Purpose'].unique():

    _df=arrival_long[(arrival_long['Tour Purpose']==tour)]
    departure_df = departure_long[(departure_long['Tour Purpose']==tour)]
    max_share_arrival = int(100* _df.value.max())
    max_share_departure = int(100* departure_df.value.max())
    _df['value']=100*_df['value']

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
    # _df_all['value']=_df_all['value'].fillna(0)

    fig, ax = plt.subplots()

    ax=sns.lineplot(data=_df_all,
                    x='dimension_02_value',
                    y='value',
                    hue='Legend',ci=False,
                    hue_order=hue_order)

    ax.figure.set_size_inches(30,10)
    ax.set_yticks(range(0, max(max_share_arrival,max_share_departure)+5, 5))
    ax.set_ylim(0, max(max_share_arrival,max_share_departure)+5)
    ax.set_title('Share of Tours by Arrival Time, Tour Purpose ' + tour+ ' for All Person Types')
    ax.set_xlabel('Arrival Time', fontsize=25)
    ax.set_ylabel('Share of Tours (Percentage)' , fontsize=25)
    #ax.set_xticklabels(['1:00 am','3:00 am', '5:00 am','7:00 am','9:00 am','11:00 am','1:00 pm','3:00 pm','5:00 pm', '7:00 pm','9:00 pm','11:00 pm'])
    plt.xticks(['1:00 am','3:00 am', '5:00 am','7:00 am','9:00 am','11:00 am',
                '1:00 pm','3:00 pm','5:00 pm', '7:00 pm','9:00 pm','11:00 pm'], fontsize=15, rotation=90)
    plt.legend(loc='upper right', fontsize=15)
    plt.xlim('1:00 am', '11:00 pm')
    ax.figure.savefig(os.path.join(set_output_dir, tour+ '_Arrival.png'),bbox_inches='tight')