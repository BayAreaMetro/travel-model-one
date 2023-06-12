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
scaling_factor = 100/0.005
model_results=args.run_name

#Set Directory
set_model_result_dir = model_results+'/'
set_calibration_target_dir='Calibration Targets/'
set_output_dir = 'calibration_output/'+model_results+'/01_WorkSchoolLocation/'

if not os.path.exists(set_output_dir):
    os.makedirs(set_output_dir)

#Read calibration Target

calib_target = pd.read_csv(os.path.join(set_calibration_target_dir, 'WorkLocationTargets.csv'))

#Read Model Results

person_df = pd.read_csv(os.path.join(set_model_result_dir, 'wsLocResults_1.csv'))

distance_skim = pd.read_csv(os.path.join(set_model_result_dir, 'da_am_skims.csv'))
distance_skim = distance_skim[(distance_skim['dist'].notnull())&(distance_skim['dist']<10000)]

person_df_ws_loc=person_df.merge(distance_skim[['origin','destination','dist']],
                                 how='left',
                                 left_on=['HomeTAZ','WorkLocation'],
                                 right_on=['origin','destination'])

person_df_ws_loc['Intrazonal'] = np.where(person_df_ws_loc['HomeTAZ']==person_df_ws_loc['WorkLocation'],
                                         1,
                                         0)

distance_bin=range(0,111)

person_df_ws_loc['distance_bin']=pd.cut(person_df_ws_loc['dist'], distance_bin)

geo_crosswalk=pd.read_csv(os.path.join(set_model_result_dir,'geo_crosswalk.csv'))

taz_county_dict=dict(zip(geo_crosswalk['TAZ'], geo_crosswalk['COUNTYNAME']))

person_df_ws_loc['county_name']=person_df_ws_loc['HomeTAZ'].map(taz_county_dict)
person_df_ws_loc['Residency'] = person_df_ws_loc['HomeTAZ'].map(taz_county_dict)

def replace_persontype(x):
    if x=='Child too young for school':
        return 'Pre-School'
    elif x=='Retired':
        return  'Non-Working Senior'
    elif x=='Student of driving age':
        return 'Driving Age Student'
    elif x=='Driving age student':
        return 'Driving Age Student'
    elif x=='Student of non-driving age':
        return 'Non-Driving Student'
    elif x=='Non-worker':
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

def inc_group(x):
    if x<20000:
        return 'HHINC<20,000'
    elif x<50000:
        return '20,000<=HHINC<50,000'
    elif x<100000:
        return '50,000<=HHINC<100,000'
    else:
        return 'HHINC>100,000'

person_df_ws_loc['hinc_cat']=person_df_ws_loc['Income'].apply(inc_group)
person_df['hinc_cat']=person_df['Income'].apply(inc_group)

person_df_ws_loc['PersonType']=person_df_ws_loc['PersonType'].apply(replace_persontype)
calib_target['dimension_01_value']=calib_target['dimension_01_value'].apply(replace_persontype)

def create_comparison_df_long(person_df_ws_loc, calib_target, dimension_list, aggregate_column):

    grouped_dimension_01_all=person_df_ws_loc.groupby(dimension_list).agg(Model=(aggregate_column,'mean')).reset_index()

    
    grouped_dimension_01_all['Target']='Mean commute length by person type'

    grouped_dimension_01_extrazonal = person_df_ws_loc[person_df_ws_loc['Intrazonal']!=1].groupby(dimension_list).agg(Model=(aggregate_column,'mean')).reset_index()
    grouped_dimension_01_extrazonal['Target']='Mean commute length by person type (exclude intrazonal)'

    if dimension_list == 'PersonType':
        grouped_dimension_01_all['Target']='Mean commute length by person type'
        grouped_dimension_01_extrazonal['Target']='Mean commute length by person type (exclude intrazonal)'
    else:
        grouped_dimension_01_all['Target']='Mean commute length by residency'
        grouped_dimension_01_extrazonal['Target']='Mean commute length by residency (exclude intrazonal)'

    grouped_model_results = pd.concat([grouped_dimension_01_all, grouped_dimension_01_extrazonal], ignore_index=True)

    if dimension_list == 'PersonType':
            grouped_model_results['dimension_01_name']='Person Type'
            grouped_model_results= grouped_model_results.rename(columns={'PersonType':'dimension_01_value'})
    else:
            grouped_model_results['dimension_01_name']='Residency'
            grouped_model_results= grouped_model_results.rename(columns={'Residency':'dimension_01_value'})

    comparison_df=pd.merge(calib_target, grouped_model_results,
                                left_on=['estimate','dimension_01_name','dimension_01_value'],
                                right_on=['Target', 'dimension_01_name','dimension_01_value'],
                                how='right')

    comparison_df_long=pd.melt(comparison_df, 
                               id_vars=['Target','dimension_01_name','dimension_01_value'],
                               value_vars=['estimate_value','Model']).reset_index()

    comparison_df_long['variable']=np.where(comparison_df_long['variable']=='estimate_value',
                                                'Target',
                                                'Model')

    return comparison_df_long

def create_comparison_df(person_df_ws_loc, calib_target, dimension_list, aggregate_column):

    grouped_dimension_01_all=person_df_ws_loc.groupby(dimension_list).agg(Model=(aggregate_column,'mean')).reset_index()

    
    grouped_dimension_01_all['Target']='Mean commute length by person type'

    grouped_dimension_01_extrazonal = person_df_ws_loc[person_df_ws_loc['Intrazonal']!=1].groupby(dimension_list).agg(Model=(aggregate_column,'mean')).reset_index()
    grouped_dimension_01_extrazonal['Target']='Mean commute length by person type (exclude intrazonal)'

    if dimension_list == 'PersonType':
        grouped_dimension_01_all['Target']='Mean commute length by person type'
        grouped_dimension_01_extrazonal['Target']='Mean commute length by person type (exclude intrazonal)'
    else:
        grouped_dimension_01_all['Target']='Mean commute length by residency'
        grouped_dimension_01_extrazonal['Target']='Mean commute length by residency (exclude intrazonal)'

    grouped_model_results = pd.concat([grouped_dimension_01_all, grouped_dimension_01_extrazonal], ignore_index=True)

    if dimension_list == 'PersonType':
            grouped_model_results['dimension_01_name']='Person Type'
            grouped_model_results= grouped_model_results.rename(columns={'PersonType':'dimension_01_value'})
    else:
            grouped_model_results['dimension_01_name']='Residency'
            grouped_model_results= grouped_model_results.rename(columns={'Residency':'dimension_01_value'})

    comparison_df=pd.merge(calib_target, grouped_model_results,
                                left_on=['estimate','dimension_01_name','dimension_01_value'],
                                right_on=['Target', 'dimension_01_name','dimension_01_value'],
                                how='right')
    comparison_df=comparison_df[['Target','dimension_01_name','dimension_01_value','estimate_name','estimate_value','Model']]
    comparison_df=comparison_df.rename(columns={'Target':'estimate'})

    return comparison_df

########### Get CTPP CC Flow###############

ctpp_data = pd.read_csv(os.path.join(set_calibration_target_dir, 'CTPP Workers CC Flow.csv'))

########### Get CTPP CC Flow###############

##########By Distance Bin

worker_share= person_df_ws_loc[person_df_ws_loc['Intrazonal']!=1].distance_bin.value_counts(normalize=True).to_frame('Model').reset_index()
worker_share['estimate']='Share of commute length by distance bin (exclude intrazonal)'

worker_share['dimension_01_value']=worker_share['index'].astype(str).apply(lambda x: x.replace('(','[').replace(', ','-'))
worker_share['dimension_01_name']='Distance Bin (miles)'
worker_share_comp=pd.merge(calib_target, worker_share,
                            left_on=['estimate','dimension_01_name','dimension_01_value'],
                            right_on=['estimate', 'dimension_01_name','dimension_01_value'],
                            how='inner')

worker_share_comp_melted=pd.melt(worker_share_comp, id_vars=['estimate','dimension_01_name','dimension_01_value'],
                                value_vars=['estimate_value','Model']).reset_index()

worker_share_comp_melted['variable']=np.where(worker_share_comp_melted['variable']=='estimate_value',
                                                'Target',
                                                model_results)

worker_share_comp_melted['upper_limit'] = worker_share_comp_melted['dimension_01_value'].apply(lambda x: x.split('-')[1].replace(']',''))

###########By distance bin and person type

worker_share_persons= person_df_ws_loc[person_df_ws_loc['Intrazonal']!=1].groupby(['PersonType','distance_bin'])['distance_bin'].nunique().to_frame('total').reset_index()
worker_share_persons['total']=worker_share_persons['total'].fillna(0)
worker_share_persons['totals_by_type']=worker_share_persons.groupby(['PersonType'])['total'].transform('sum')

worker_share_persons['Model']=worker_share_persons['total']/worker_share_persons['totals_by_type']

worker_share_persons['dimension_02_value']=worker_share_persons['distance_bin'].astype(str).apply(lambda x: x.replace('(','[').replace(', ','-'))
worker_share_persons['dimension_02_name']='Distance Bin (miles)'

worker_share_persons=worker_share_persons.rename(columns={'PersonType':'dimension_01_value'})
worker_share_persons['dimension_01_name']='Person Type'


worker_share_persons['estimate']='Share of commute length by person type and distance bin (exclude intrazonal)'

worker_share_persons_comp=pd.merge(calib_target, worker_share_persons,
                            left_on=['estimate','dimension_01_name','dimension_01_value','dimension_02_name','dimension_02_value'],
                            right_on=['estimate', 'dimension_01_name','dimension_01_value','dimension_02_name','dimension_02_value'],
                            how='inner')

worker_share_persons_comp_melted=pd.melt(worker_share_persons_comp, id_vars=['estimate','dimension_01_name','dimension_01_value','dimension_02_name','dimension_02_value'],
                                value_vars=['estimate_value','Model']).reset_index()

worker_share_persons_comp_melted['variable']=np.where(worker_share_persons_comp_melted['variable']=='estimate_value',
                                                'Target',
                                                model_results)

worker_share_persons_comp_melted['upper_limit'] = worker_share_persons_comp_melted['dimension_02_value'].apply(lambda x: x.split('-')[1].replace(']','')) 


mean_commute_length = {'estimate':['Mean commute length', 'Mean commute length (exclude intrazonal)'],
                       'Model':[person_df_ws_loc.dist.mean(), person_df_ws_loc[person_df_ws_loc['Intrazonal']!=1].dist.mean()]}

mean_commute_length_df=pd.DataFrame(mean_commute_length)

mean_commute_length_df_comp = pd.merge(calib_target.head(2)[['estimate','estimate_value']],mean_commute_length_df, on='estimate')
mean_commute_length_df_comp_long=pd.melt(mean_commute_length_df_comp, id_vars=['estimate'], value_vars=['estimate_value','Model'])
mean_commute_length_df_comp_long['variable']=np.where(mean_commute_length_df_comp_long['variable']=='estimate_value',
                                                'Target',
                                                model_results)
######### By HH Income Category

hhinc_dist = person_df_ws_loc.groupby('hinc_cat').agg(Avg_Work_Loc_Dist=('dist','mean'))


# Concat Them together

persontype_comparison_long = create_comparison_df_long(person_df_ws_loc, calib_target, 'PersonType','dist')
persontype_comparison_long['variable']=np.where(persontype_comparison_long['variable']=='Model', model_results, persontype_comparison_long['variable'])
residency_comparison_long = create_comparison_df_long(person_df_ws_loc, calib_target, 'Residency','dist')
residency_comparison_long['variable']=np.where(residency_comparison_long['variable']=='Model', model_results, residency_comparison_long['variable'])

persontype_comparison = create_comparison_df(person_df_ws_loc, calib_target, 'PersonType','dist')
residency_comparison = create_comparison_df(person_df_ws_loc, calib_target, 'Residency','dist')

categorized_results = pd.concat([mean_commute_length_df_comp,
                                persontype_comparison,
                                residency_comparison,
                                worker_share_comp,
                                worker_share_persons_comp], ignore_index=True)


categorized_results=categorized_results[['source', 'estimate', 'dimension_01_name', 'dimension_01_value',
       'dimension_02_name', 'dimension_02_value', 'estimate_name',
       'estimate_value', 'Model']]

categorized_results=categorized_results.rename(columns={'estimate_value':'Target','Model':model_results})

writer = pd.ExcelWriter(os.path.join(set_output_dir,'workLocationSummary.xlsx'), engine='xlsxwriter')
categorized_results.to_excel(writer, sheet_name='All', startrow=1, header=False, index=False)

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
(max_row, max_col) = categorized_results.shape

# Make the columns wider for clarity.
worksheet.set_column(0,  max_col - 1, 12)
worksheet.autofilter(0, 0, max_row, max_col - 1)

for col_num, value in enumerate(categorized_results.columns.values):
    worksheet.write(0, col_num, value, header_format)


#############County to County Flow

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

person_df['Origin_County']=person_df['HomeTAZ'].map(taz_county_dict)
person_df['Destination_County'] = person_df['WorkLocation'].map(taz_county_dict)
person_df['School_Destination_County'] = person_df['SchoolLocation'].map(taz_county_dict)

for county in person_df['Origin_County'].unique():

    if county not in county_dict:
        county_dict.remove(county)


ctpp_c_c_flow = pd.crosstab(ctpp_data['RESIDENCE'],
                            ctpp_data['WORKPLACE'],
                            values=ctpp_data['Workers'],
                            aggfunc='sum', 
                            margins=True,
                            margins_name='Total Workers').sort_index(key=lambda x: x.map(county_sorter_index))[county_dict]


school=person_df[person_df['School_Destination_County'].notnull()]
school_c_c_flow= pd.crosstab(school['Origin_County'],
                            school['School_Destination_County'], 
                            values=school['PersonID'], 
                            aggfunc='nunique', 
                            margins=True,
                            margins_name='Total Workers').reset_index()
                            
school_c_c_flow=school_c_c_flow.sort_values(by='Origin_County',key=lambda x: x.map(county_sorter_index)).set_index('Origin_County')[county_dict]

work=person_df[person_df['Destination_County'].notnull()]
work_c_c_flow= pd.crosstab(work['Origin_County'],
                            work['Destination_County'], 
                            values=work['PersonID'], 
                            aggfunc='nunique', 
                            margins=True,
                            margins_name='Total Workers').reset_index()

hhinc_cc_flows={}

for hhinc in person_df.hinc_cat.unique():
    columns=county_dict.copy()
    df=person_df[person_df['hinc_cat']==hhinc]

    hhinc_cc_flow_df = pd.crosstab(df['Origin_County'],
                            df['Destination_County'], 
                            values=df['PersonID'], 
                            aggfunc='nunique', 
                            margins=True,
                            margins_name='Total Workers').reset_index()
    hhinc_cc_flow_df['HINC'] = hhinc
    columns.append('HINC')
    hhinc_cc_flow_df=hhinc_cc_flow_df.sort_values(by='Origin_County',key=lambda x: x.map(county_sorter_index)).set_index('Origin_County')[columns]

    hhinc_cc_flows[hhinc] = hhinc_cc_flow_df

hhinc_cc_flow = pd.concat(hhinc_cc_flows.values(), ignore_index=False)


work_c_c_flow=work_c_c_flow.sort_values(by='Origin_County',key=lambda x: x.map(county_sorter_index)).set_index('Origin_County')[county_dict]

work_c_c_flow.to_csv(os.path.join(set_output_dir,'workLocationSummary_CC_Flow.csv'))

ctpp_c_c_flow.to_excel(writer, sheet_name='Work CC Flow', startrow=1)
work_c_c_flow.to_excel(writer, sheet_name='Work CC Flow', startrow=1, startcol=14)
hhinc_dist.to_csv(os.path.join(set_output_dir,'average_work_location_by_hhinc.csv'))
hhinc_cc_flow.to_csv(os.path.join(set_output_dir,'average_work_cc_flow_by_hhinc.csv'))

scaled_workerflow=scaling_factor * work_c_c_flow.fillna(0)
scaled_workerflow.to_excel(writer, sheet_name='Work CC Flow', startrow=1, startcol=28)
workbook  = writer.book
worksheet = writer.sheets['Work CC Flow']
# Add a header format.
header_format = workbook.add_format({
    'bold': True,
    'text_wrap': True,
    'valign': 'vcenter',
    'align':'center',
    'fg_color': '#D7E4BC',
    'border': 1,
    'font_size':18})
worksheet.merge_range('A1:K1', 'Workplace Location Choice- CTPP', header_format)
worksheet.merge_range('O1:Y1', 'Workplace Location Choice- Model', header_format)
worksheet.merge_range('AC1:AM1', 'Workplace Location Choice- Model (Scaled)', header_format)
# Get the dimensions of the dataframe.
(max_row, max_col) = work_c_c_flow.shape

# Make the columns wider for clarity.
worksheet.set_column(0,  max_col - 1, 12)

school_c_c_flow.to_excel(writer, sheet_name='School CC Flow', startrow=1)
scaled_school_c_c_flow=school_c_c_flow.fillna(0)*20
scaled_school_c_c_flow.to_excel(writer, sheet_name='School CC Flow', startrow=16)
workbook  = writer.book
worksheet = writer.sheets['School CC Flow']
worksheet.merge_range('A1:K1', 'School Location Choice- Model', header_format)
worksheet.merge_range('A15:K15', 'School Location Choice- Model (Scaled)', header_format)
# Get the dimensions of the dataframe.
(max_row, max_col) = school_c_c_flow.shape

# Make the columns wider for clarity.
worksheet.set_column(0,  max_col - 1, 12)
writer.save()

###########Create figures
fig, ax = plt.subplots()
sns.set_context("talk",font_scale=1.5, rc={"lines.linewidth": 2.5})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})

order = ['Full-Time Worker', 'Part-Time Worker','University Student','Driving Age Student',]
persontype_comparison_long=persontype_comparison_long.rename(columns={'variable':'Legend'})
ax= sns.barplot(data=persontype_comparison_long, x='dimension_01_value', y='value', hue = 'Legend',ci=None,order=order, hue_order=['Target', model_results])
ax.figure.set_size_inches(15,10)
ax.set_ylim(0, 21)
ax.set_xlabel('Person Type', fontsize=25)
ax.set_ylabel('Mean Commute Length (Miles)', fontsize=25)
ax.set_title('Mean Commute Length to Work by Person Type', fontsize=30)
plt.xticks(fontsize =20)
plt.yticks(fontsize =20)
plt.legend(loc='upper right')
ax.figure.savefig(os.path.join(set_output_dir, 'Mean Commute Length By PersonType.png'),bbox_inches='tight')

fig, ax = plt.subplots()
residency_comparison_long=residency_comparison_long.rename(columns={'variable':'Legend'})
ax= sns.barplot(data=residency_comparison_long, x='dimension_01_value', y='value', hue = 'Legend',ci=None, hue_order=['Target', model_results], order=county_dict)
ax.figure.set_size_inches(20,10)
ax.set_ylim(0, 21)
ax.set_xlabel('Residence County', fontsize=25)
ax.set_ylabel('Mean Commute Length (Miles)', fontsize=25)
ax.set_title('Mean Commute Length to Work by Residence County', fontsize=30)
plt.legend(loc='upper right')
for tick in ax.get_xticklabels():
    tick.set_rotation(90)
ax.figure.savefig(os.path.join(set_output_dir, 'Mean Commute Length By County.png'),bbox_inches='tight')

mean_commute_length_df_comp_long=mean_commute_length_df_comp_long.rename(columns={'variable':'Legend'})
fig, ax = plt.subplots()
ax= sns.barplot(data=mean_commute_length_df_comp_long, x='estimate', y='value', hue = 'Legend',ci=None, hue_order=['Target', model_results])
ax.figure.set_size_inches(20,10)
ax.set_ylim(0, 21)
ax.set_xlabel('All Work Location')
ax.set_ylabel('Mean Commute Length (Miles)')
ax.set_title('Mean Commute Length to Work', fontsize=30)
plt.legend(loc='upper right')
ax.figure.savefig(os.path.join(set_output_dir, 'All Work Location.png'),bbox_inches='tight')


worker_share_comp_melted=worker_share_comp_melted.rename(columns={'variable':'Legend'})
worker_share_comp_melted['Pct']=worker_share_comp_melted['value']*100
fig, ax = plt.subplots()
ax= sns.lineplot(data=worker_share_comp_melted, 
                x='upper_limit', y='Pct', hue = 'Legend', ci=None,hue_order=['Target', model_results])
ax.figure.set_size_inches(20,10)
ax.set_xlim(0,70)
ax.set_xlabel('Upper Limit of Distance Band (miles)', fontsize=25)
ax.set_ylabel('Percent Share of Commute Length', fontsize=25)
ax.set_title('Work Location Distance from Residence (Excludes Intrazonal)', fontsize=30)
plt.xticks(range(1, 70, 2), fontsize =15)
plt.legend(loc='upper right')
ax.figure.savefig(os.path.join(set_output_dir, 'Work Location Distance from Residence.png'),bbox_inches='tight')