'''
USAGE:
    Temporary script that creates necessary inputs to create IX trip matrices.
    Creates ixDaily2015_totals.csv and the ixex_config.csv
    ixDaily2015_totals.csv is created from the total trips obtained from the converted ix trip matrix. 
    ixex_config.csv comes from the original ixex_config.dbf and the iz_ez_ext.dat file
'''
import pandas as pd
import numpy as np

total_trips=pd.read_csv('nonres/ixDaily2015_total_trips.csv', names=['origin','destination','matrix','total'])

ext_zone_prod = total_trips[total_trips['origin']>6593].groupby(['origin'])['total'].sum().reset_index()
ext_zone_prod=ext_zone_prod.rename(columns={'total':'PROD'})
ext_zone_attr = total_trips[total_trips['destination']>6593].groupby(['destination'])['total'].sum().reset_index()
ext_zone_attr=ext_zone_attr.rename(columns={'total':'ATTR'})

ext_zone=pd.merge(ext_zone_prod, ext_zone_attr, left_on=['origin'], right_on=['destination'])
ext_zone=ext_zone.rename(columns={'origin':'EXT_ZONE'}).drop(columns=['destination'])

ext_zone.to_csv('nonres/ixDaily2015_totals.csv', index=False)

ixex_config_original=pd.read_csv('nonres/tm15/ixex_config.csv')
iz_ez_map=pd.read_csv('main/IZ_OZ_PCT_EXT.dat', sep='\t',names=['iz','ez','col_pct','row_pct'])
iz_ez_map=iz_ez_map[iz_ez_map['iz']>1454][['iz','ez']]
ixex_config_new=pd.merge(ixex_config_original, iz_ez_map, left_on='EXT_ZONE', right_on=['iz'], how='left').drop(columns='EXT_ZONE')
ixex_config_new=ixex_config_new.rename(columns={'ez':"EXT_ZONE"})[ixex_config_original.columns]
ixex_config_new=ixex_config_new.sort_values(by=['EXT_ZONE'], ascending=True)
ixex_config_new=ixex_config_new.drop_duplicates(['EXT_ZONE'])
ixex_config_new=ixex_config_new[ixex_config_new['EXT_ZONE'].notnull()]
ixex_config_new['EXT_ZONE']=ixex_config_new['EXT_ZONE'].astype(str)

ixex_config_new.to_csv('nonres/ixex_config.csv', index=False)