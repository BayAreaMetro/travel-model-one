import pandas as pd
import geopandas as gpd

# a quick script to tally freeway VMT by congested (<35 mph) vs non-congested
# see Asana task https://app.asana.com/1/11860278793487/project/430646376255593/task/1201383752140241/comment/1201391313704587
# run from the model run directory on M: drive

loaded_network = gpd.read_file("./OUTPUT/shapefile/network_links.shp")
loaded_network = loaded_network[[
    'CSPDEA', 'VMTEA',
    'CSPDAM', 'VMTAM',
    'CSPDMD', 'VMTMD',
    'CSPDPM', 'VMTPM',
    'CSPDEV', 'VMTEV',
    'VMT24HR','FT'
]]
loaded_network_fwy = loaded_network.loc[loaded_network['FT'].isin([1,2,8])]
print('loaded_network_fwy header:')
print(loaded_network_fwy.head())

# stack by time period
loaded_network_fwy_stack = pd.DataFrame(columns = ['CSPD', 'VMT', 'tod'])
for i in ['EA', 'AM', 'MD', 'PM', 'EV']:
    links = loaded_network_fwy[['CSPD'+i, 'VMT'+i]].copy()
    links.rename(columns = {'CSPD'+i: 'CSPD',
                            'VMT'+i:  'VMT'}, inplace=True)
    links['tod'] = i
    # print(links.shape[0])
    loaded_network_fwy_stack = pd.concat([loaded_network_fwy_stack, links])

# add tags for congested conditions (speed less than 35 mph)
loaded_network_fwy_stack['cspd_cat'] = 'not_congested'
loaded_network_fwy_stack.loc[
    (loaded_network_fwy_stack.CSPD < 35) & (loaded_network_fwy_stack.CSPD != 0), 'cspd_cat'] = 'congested'
print('loaded_network_fwy stacked with congestion tag header:')
print(loaded_network_fwy_stack.head())

loaded_network_fwy_stack.to_csv("./OUTPUT/metrics/STIP_congested_VMT_by_TOD.csv", index=False)