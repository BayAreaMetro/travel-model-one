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
set_calibration_target_dir='Calibration Targets/'
total_runs = model_results
tm15_reference_run = 'main_Run_TM15'
last_run_name = 'main_Run_'+str(total_runs)
set_output_dir = 'calibration_output/'+last_run_name+'/01_WorkSchoolLocation/Comparison/'
if not os.path.exists(set_output_dir):
    os.makedirs(set_output_dir)
    
    
comparison_df_dict={}
dist_by_hhinc={}
hue_order=['Target']
for run_number in [0, total_runs-1, total_runs]:
    if run_number == 0:
        run_name = tm15_reference_run
        hue_order.append('Travel Model 1.5')
    else:   
        run_name = 'main_Run_'+str(run_number)
    if os.path.exists(os.path.join(calibration_dir, run_name , '01_WorkSchoolLocation')):
        _df = pd.read_excel(os.path.join(calibration_dir, run_name,'01_WorkSchoolLocation','workLocationSummary.xlsx'))
        _hhinc_df = pd.read_csv(os.path.join(calibration_dir, run_name,'01_WorkSchoolLocation','average_work_location_by_hhinc.csv'))
        _hhinc_df['Run'] = 'BCM Run_'+ run_name.split('_')[-1]
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

work_cc_flow_dict={}
school_cc_flow_dict={}

county_dict=['San Francisco',
             'San Mateo',
             'Santa Clara',
             'Alameda',
             'Contra Costa',
             'Solano',
             'Napa',
             'Sonoma',
             'Marin',
             'San Joaquin']

county_sorter_index = dict(zip(county_dict, range(len(county_dict))))

ctpp_data = pd.read_csv(os.path.join(set_calibration_target_dir, 'CTPP Workers CC Flow.csv'))
ctpp_c_c_flow = pd.crosstab(ctpp_data['RESIDENCE'],
                            ctpp_data['WORKPLACE'],
                            values=ctpp_data['Workers'],
                            aggfunc='sum').sort_index(key=lambda x: x.map(county_sorter_index))[county_dict]
ctpp_c_c_flow['Source']='CTPP'
work_cc_flow_dict['Target'] = ctpp_c_c_flow
for run_number in [0, total_runs-1, total_runs]:
    if run_number == 0:
        run_name = tm15_reference_run
    else:   
        run_name = 'main_Run_'+str(run_number)
    if os.path.exists(os.path.join(calibration_dir, run_name , '01_WorkSchoolLocation')):
        cc_flow = pd.read_csv(os.path.join(calibration_dir, run_name,'01_WorkSchoolLocation','workLocationSummary_CC_Flow.csv'))
        cc_flow['Run'] = 'BCM Run_'+ run_name.split('_')[-1]
        # _df_work=_df_work.reset_index()
        # _df_school = pd.read_excel(os.path.join(calibration_dir, run_name,'01_WorkSchoolLocation','workLocationSummary.xlsx'), sheet_name='School CC Flow', skiprows=16)
        # _df_school['Source'] = run_name
        # _df_school=_df_school.reset_index()
    else:
        continue
        
    work_cc_flow_dict[run_name] = cc_flow
    # school_cc_flow_dict[run_name] = _df_school

work_cc_flow_df = pd.concat(work_cc_flow_dict.values(), ignore_index=True)
# school_cc_flow_df = pd.concat(school_cc_flow_dict.values(), ignore_index=True)

comparison_df = pd.concat(comparison_df_dict.values(), ignore_index=True)
comparison_df_wide=comparison_df.pivot(index=['estimate','dimension_01_name','dimension_01_value','dimension_02_name','dimension_02_value'], 
                                       columns='variable', values='value').reset_index().fillna(0)

writer = pd.ExcelWriter(os.path.join(set_output_dir,'workLocationSummary_Comparison.xlsx'), engine='xlsxwriter')
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



work_cc_flow_df.to_excel(writer, sheet_name='Work CC Flow', startrow=0)

workbook  = writer.book
worksheet = writer.sheets['Work CC Flow']
# Add a header format.
header_format = workbook.add_format({
    'bold': True,
    'text_wrap': True,
    'valign': 'top',
    'fg_color': '#D7E4BC',
    'border': 1})

# Get the dimensions of the dataframe.
(max_row, max_col) = work_cc_flow_df.shape

# Make the columns wider for clarity.
worksheet.set_column(0,  max_col - 1, 12)
worksheet.autofilter(0, 0, max_row, max_col - 1)

# school_cc_flow_df.to_excel(writer, sheet_name='School CC Flow', startrow=0)

# workbook  = writer.book
# worksheet = writer.sheets['School CC Flow']
# # Add a header format.
# header_format = workbook.add_format({
#     'bold': True,
#     'text_wrap': True,
#     'valign': 'top',
#     'fg_color': '#D7E4BC',
#     'border': 1})

# # Get the dimensions of the dataframe.
# (max_row, max_col) = school_cc_flow_df.shape

# # Make the columns wider for clarity.
# worksheet.set_column(0,  max_col - 1, 12)
# worksheet.autofilter(0, 0, max_row, max_col - 1)

# for col_num, value in enumerate(work_c_c_flow.columns.values):
#     worksheet.write(0, col_num, value, header_format)
# for row_num, value in enumerate(work_c_c_flow.index.values):
#     worksheet.write(row_num, 0, value, header_format)
writer.save()

###########
###########Create figures
fig, ax = plt.subplots()
sns.set_context("talk",font_scale=1.5, rc={"lines.linewidth": 2.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})

order = ['Full-Time Worker', 'Part-Time Worker','University Student','Driving Age Student',]
persontype_comparison_long=comparison_df[comparison_df['estimate']=='Mean commute length by person type'].rename(columns={'variable':'Legend'})
ax= sns.barplot(data=persontype_comparison_long, x='dimension_01_value', y='value', hue = 'Legend',ci=None,order=order, hue_order=hue_order)
ax.figure.set_size_inches(15,10)
ax.set_ylim(0, 21)
ax.set_xlabel('Person Type',  fontsize=25)
ax.set_ylabel('Mean Commute Length (Miles)', fontsize=25)
ax.set_title('Mean Commute Length to Work by Person Type', fontsize=30)
plt.xticks(fontsize =20)
plt.yticks(fontsize =20)
plt.legend(loc='upper right')
ax.figure.savefig(os.path.join(set_output_dir, 'Mean Commute Length By PersonType.png'),bbox_inches='tight')

fig, ax = plt.subplots()
residency_comparison_long=comparison_df[comparison_df['dimension_01_name']=='Residency'].rename(columns={'variable':'Legend'})
ax= sns.barplot(data=residency_comparison_long, x='dimension_01_value', y='value', hue = 'Legend',ci=None, hue_order=hue_order, order=county_dict)
ax.figure.set_size_inches(20,10)
ax.set_ylim(0, 21)
ax.set_xlabel('Residence County')
ax.set_ylabel('Mean Commute Length (Miles)')
ax.set_title('Mean Commute Length to Work by Residence County', fontsize=30)
plt.legend(loc='upper right')
for tick in ax.get_xticklabels():
    tick.set_rotation(90)
ax.figure.savefig(os.path.join(set_output_dir, 'Mean Commute Length By County.png'),bbox_inches='tight')

mean_commute_length_df_comp_long=comparison_df[comparison_df['dimension_01_name'].isnull()].rename(columns={'variable':'Legend'})
fig, ax = plt.subplots()
ax= sns.barplot(data=mean_commute_length_df_comp_long, x='estimate', y='value', hue = 'Legend',ci=None, hue_order=hue_order)
ax.figure.set_size_inches(20,10)
ax.set_ylim(0, 21)
ax.set_xlabel('All Work Location')
ax.set_ylabel('Mean Commute Length (Miles)')
plt.legend(loc='upper right')
ax.set_title('Mean Commute Length to Work', fontsize=30)

ax.figure.savefig(os.path.join(set_output_dir, 'All Work Location.png'),bbox_inches='tight')


worker_share_comp_melted=comparison_df[comparison_df['dimension_01_name']=='Distance Bin (miles)'].rename(columns={'variable':'Legend'})
worker_share_comp_melted['upper_limit']=worker_share_comp_melted['dimension_01_value'].apply(lambda x: int(x.split('-')[1].replace(']','')))
worker_share_comp_melted['Pct']=worker_share_comp_melted['value']*100
fig, ax = plt.subplots()
ax= sns.lineplot(data=worker_share_comp_melted, 
                x='upper_limit', y='Pct', hue = 'Legend', ci=None, hue_order=hue_order)
ax.figure.set_size_inches(20,10)
ax.set_xlim(0,70)
ax.set_xlabel('Upper Limit of Distance Band (miles)', fontsize=25)
ax.set_ylabel('Percent Share of Commute Length', fontsize=25)
ax.set_title('Work Location Distance from Residence (Excludes Intrazonal)', fontsize=30)
plt.xticks(range(1, 70, 2), fontsize =15)
plt.legend(loc='upper right')
ax.figure.savefig(os.path.join(set_output_dir, 'Work Location Distance from Residence.png'),bbox_inches='tight')