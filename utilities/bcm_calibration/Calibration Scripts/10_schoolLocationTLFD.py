import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
sns.set(color_codes=True)
import os
import glob
import xlsxwriter
import math 

import argparse

#Set Directory
parser = argparse.ArgumentParser()
parser.add_argument("--run_name",type=str, help="Model run output file relative location")

args = parser.parse_args()

model_results=args.run_name

set_model_result_dir = '../data/'+model_results+'/'
set_calibration_target_dir='../data/calibration targets/'
set_output_dir = '../output/08_TLFD_Summary/'+model_results+'/'
if not os.path.exists(set_output_dir):
    os.makedirs(set_output_dir)
#Read calibration Target

calib_target = pd.read_csv(os.path.join(set_calibration_target_dir, 'SchoolandUniversityTourTLFD_Targets.csv'))
calib_target['dimension_02_value']=calib_target['dimension_02_value'].apply(lambda x: int(x.split('-')[1].replace(']','')))
calib_target=calib_target.rename(columns={'estimate_value':'Target'})
#Read Model Results

person_df = pd.read_csv(os.path.join(set_model_result_dir, 'wsLocResults_1.csv'))

# distance_skim = pd.read_csv(os.path.join(set_model_result_dir, 'da_am_skims.csv'))
# distance_skim = distance_skim[(distance_skim['dist'].notnull())&(distance_skim['dist']<10000)]

distance_skim = pd.read_csv(os.path.join(set_model_result_dir, 'da_am_skims.csv'))
distance_skim = distance_skim[(distance_skim['da'].notnull())&(distance_skim['da']<10000)]

# person_df_ws_loc=person_df.merge(distance_skim[['origin','destination','dist']],
#                                  how='left',
#                                  left_on=['HomeTAZ','SchoolLocation'],
#                                  right_on=['origin','destination'])
person_df_ws_loc=person_df.merge(distance_skim[['orig','dest','da']],
                                 how='left',
                                 left_on=['HomeTAZ','SchoolLocation'],
                                 right_on=['orig','dest'])

geo_crosswalk=pd.read_csv(os.path.join(set_model_result_dir,'tazData.csv'))

county_dict={1:'San Francisco',
             2:'San Mateo',
             3:'Santa Clara',
             4:'Alameda',
             5:	'Contra Costa',
             6:	'Solano',
             7:	'Napa',
             8:	'Sonoma',
             9:	'Marin'}

geo_crosswalk['COUNTYNAME']=geo_crosswalk['COUNTY'].map(county_dict)
taz_county_dict=dict(zip(geo_crosswalk['ZONE'], geo_crosswalk['COUNTYNAME']))

# geo_crosswalk=pd.read_csv(os.path.join(set_model_result_dir,'geo_crosswalk.csv'))
# bcm_taz_seq=pd.read_csv(os.path.join(set_model_result_dir,'bcmtaz_seq.csv'))

# county_dict={1:'San Francisco',
#              2:'San Mateo',
#              3:'Santa Clara',
#              4:'Alameda',
#              5:	'Contra Costa',
#              6:	'Solano',
#              7:	'Napa',
#              8:	'Sonoma',
#              9:	'Marin',
#              10	:'San Joaquin'}

# geo_crosswalk['COUNTYNAME']=geo_crosswalk['COUNTY'].map(county_dict)
# geo_crosswalk['TAZSEQ']=geo_crosswalk['BCMTAZ'].map(dict(zip(bcm_taz_seq['BCMTAZ'], bcm_taz_seq['TAZSEQ'])))
# taz_county_dict=dict(zip(geo_crosswalk['TAZSEQ'], geo_crosswalk['COUNTYNAME']))

person_df_ws_loc['Origin_County']=person_df_ws_loc['HomeTAZ'].map(taz_county_dict)
person_df_ws_loc['School_Destination_County'] = person_df_ws_loc['SchoolLocation'].map(taz_county_dict)

school_univ_tours = person_df_ws_loc[(person_df_ws_loc['SchoolLocation']!=0)&(person_df_ws_loc['PersonType']!='Child too young for school')]

def tour_purpose(x):
    if x in ['Student of non-driving age', 'Student of driving age']:
        return 'School'
    elif x =='University student':
        return 'University'
    else:
        return None

school_univ_tours['dimension_01_value']=school_univ_tours['PersonType'].apply(tour_purpose)
#school_univ_tours['dimension_02_value']=school_univ_tours['dist'].apply(lambda x: math.ceil(x))
school_univ_tours['dimension_02_value']=school_univ_tours['da'].apply(lambda x: math.ceil(x))

school_univ_tours_grouped = school_univ_tours.groupby(['dimension_01_value','dimension_02_value']).agg(Share=('dimension_02_value','count')).reset_index()
school_univ_tours_grouped['Total']=school_univ_tours_grouped.groupby('dimension_01_value')['Share'].transform('sum')
school_univ_tours_grouped['Model']=school_univ_tours_grouped['Share']/school_univ_tours_grouped['Total']

comparison_df = pd.merge(calib_target, school_univ_tours_grouped[['dimension_01_value','dimension_02_value','Model']],
                         on=['dimension_01_value','dimension_02_value'], how='left')

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

comparison_df_long=pd.melt(comparison_df, id_vars=['dimension_01_name', 'dimension_01_value','dimension_02_name','dimension_02_value','estimate_name'],
                            value_vars=['Target', 'Model'], var_name='Legend')

sns.set_context("paper",font_scale=3, rc={"lines.linewidth": 3})
sns.set_style("whitegrid",{"axes.facecolor": ".95",'grid.color': '.6'})
comparison_df_long['Pct']=comparison_df_long['value']*100
df= comparison_df_long[comparison_df_long['dimension_01_value']=='School']

ax= sns.lineplot(data=df, 
                x='dimension_02_value', y='Pct', hue = 'Legend', hue_order=['Target','Model'], ci=False)
ax.figure.set_size_inches(30,20)
ax.set_xlim(0,60)
ax.set_xlabel('Upper Limit of Distance Band (miles)', fontsize=30)
ax.set_ylabel('Percent Share of Commute Length', fontsize=30)
ax.set_title('School Location Distance from Residence', fontsize=40)
ax.figure.savefig(os.path.join(set_output_dir, 'School Location Distance from Residence.png'),bbox_inches='tight')


df= comparison_df_long[comparison_df_long['dimension_01_value']=='University']

ax= sns.lineplot(data=df, 
                x='dimension_02_value', y='Pct', hue = 'Legend', hue_order=['Target','Model'], ci=False)
ax.figure.set_size_inches(30,20)
ax.set_xlim(0,60)
ax.set_xlabel('Upper Limit of Distance Band (miles)', fontsize=30)
ax.set_ylabel('Percent Share of Commute Length', fontsize=30)
ax.set_title('University Location Distance from Residence', fontsize=40)
ax.figure.savefig(os.path.join(set_output_dir, 'University Location Distance from Residence.png'),bbox_inches='tight')