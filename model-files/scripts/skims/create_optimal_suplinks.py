import pandas as pd
import numpy as np
import os
import sys
pd.set_option('display.max_colwidth', 255)

model_run_dir           = sys.argv[0]
timeperiod              = sys.argv[1]
number_of_links         = int(sys.argv[2])

supplink_filename       = os.path.join("{}_transit_suplinks.dat".format(timeperiod))
wlklink_filename        = os.path.join("{}_transit_suplinks_wlk.dat".format(timeperiod))
drvlink_filename        = os.path.join("{}_transit_suplinks_drv.dat".format(timeperiod))
knr_filename            = os.path.join("{}_bus_acclinks_KNR.dat".format(timeperiod))

supplink_file=pd.read_csv(supplink_filename, sep='=', names=['type','link-mode','mode-dist','dist-speed','speed-oneway','oneway'])

for col in supplink_file.columns:
    supplink_file[col]=supplink_file[col].astype(str)
    supplink_file[col]=supplink_file[col].apply(lambda x: x.strip())

supplink_file['oneway']=np.where(supplink_file['dist-speed']=='0 ONEWAY',supplink_file['speed-oneway'],supplink_file['oneway'])
supplink_file['speed-oneway']=np.where(supplink_file['dist-speed']=='0 ONEWAY',' ONEWAY',supplink_file['speed-oneway'])
supplink_file['dist-speed']=np.where(supplink_file['dist-speed']=='0 ONEWAY','0 ',supplink_file['dist-speed'])

supplink_file['link']=supplink_file['link-mode'].apply(lambda x: x.split(' MODE')[0])
supplink_file['mode']=supplink_file['mode-dist'].apply(lambda x: int(x.split(' DIST')[0]))
supplink_file['dist']=supplink_file['dist-speed'].apply(lambda x: int(x.split(' ')[0]))
supplink_file['speed']=supplink_file['speed-oneway'].apply(lambda x: x.split(' ')[0])

supplink_file=supplink_file[['type','link','mode','dist','speed','oneway']]

all_drive_links=supplink_file[supplink_file['mode'].isin([2,7])]
all_walk_links=supplink_file[~supplink_file['mode'].isin([2,7])]
knr_links=supplink_file[supplink_file['mode'].isin([1,6])]

all_drive_links['origin']=all_drive_links['link'].apply(lambda x: int(x.split('-')[0]))
all_drive_links['destination']=all_drive_links['link'].apply(lambda x: int(x.split('-')[1]))

all_drive_access_links=all_drive_links[all_drive_links['origin']<6594].sort_values(by=['origin','mode','dist'])
all_drive_egress_links=all_drive_links[all_drive_links['origin']>6593].sort_values(by=['destination','mode','dist'])


selected_drive_access_links = all_drive_access_links.groupby(['origin','mode'], as_index=False).apply(lambda x: x.head(number_of_links)).reset_index()
selected_drive_egress_links = all_drive_egress_links.groupby(['destination','mode'], as_index=False).apply(lambda x: x.head(number_of_links)).reset_index()

selected_drive_links=pd.concat([selected_drive_access_links, selected_drive_egress_links], ignore_index=True)

knr_links['mode']=knr_links['mode'].apply(lambda x: x+1)
knr_links['speed']=20


for col in selected_drive_links.columns:
    selected_drive_links[col]=selected_drive_links[col].astype(str)
for col in all_walk_links.columns:
    all_walk_links[col]=all_walk_links[col].astype(str)
for col in knr_links.columns:
    knr_links[col]=knr_links[col].astype(str)

selected_drive_links['text'] = np.where(selected_drive_links['speed']!='',
                                        selected_drive_links['type']+'= '+selected_drive_links['link']+' MODE='+selected_drive_links['mode']+' DIST='+selected_drive_links['dist']+' SPEED='+
                                            selected_drive_links['speed']+' ONEWAY='+selected_drive_links['oneway'],
                                        selected_drive_links['type']+'= '+selected_drive_links['link']+' MODE='+selected_drive_links['mode']+' DIST='+selected_drive_links['dist']+' ONEWAY='+selected_drive_links['oneway'])

all_walk_links['text'] = np.where(all_walk_links['speed']!='',
                                        all_walk_links['type']+'= '+all_walk_links['link']+' MODE='+all_walk_links['mode']+' DIST='+all_walk_links['dist']+' SPEED='+
                                            all_walk_links['speed']+' ONEWAY='+all_walk_links['oneway'],
                                        all_walk_links['type']+'= '+all_walk_links['link']+' MODE='+all_walk_links['mode']+' DIST='+all_walk_links['dist']+' ONEWAY='+all_walk_links['oneway'])

knr_links['text'] = np.where(knr_links['speed']!='',
                                        knr_links['type']+'= '+knr_links['link']+' MODE='+knr_links['mode']+' DIST='+knr_links['dist']+' SPEED='+
                                            knr_links['speed']+' ONEWAY='+knr_links['oneway'],
                                        knr_links['type']+'= '+knr_links['link']+' MODE='+knr_links['mode']+' DIST='+knr_links['dist']+' ONEWAY='+knr_links['oneway'])



with open (wlklink_filename, 'w') as f:

    df_string  = all_walk_links[['text']].to_string(header=False, index=False)
    f.write(df_string)

print "Wrote walk links for {} period".format(timeperiod)

with open (drvlink_filename, 'w') as f:

    df_string  = selected_drive_links[['text']].to_string(header=False, index=False)
    f.write(df_string)
print "Wrote drive links for {} period".format(timeperiod)
with open (knr_filename, 'w') as f:

    df_string  = knr_links[['text']].to_string(header=False, index=False)
    f.write(df_string)
print "Wrote KNR links for {} period".format(timeperiod)