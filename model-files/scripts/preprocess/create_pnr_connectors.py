import pandas as pd
import numpy as np
import math
import os, sys

model_run_dir = sys.argv[0]

print model_run_dir

buffer_dist = 0.125


#Remote I/O
nodes_list = pd.read_csv('../transit_background_nodes.csv')
transit_nodes = pd.read_csv('../all_transit_nodes.csv', names=['Node'])


pnr_nodes = nodes_list[nodes_list['PNR'].isin([1.0, '1.0'])][['N', 'X', 'Y']]
pnr_nodes['coord'] = pnr_nodes[['X','Y']].values.tolist()

transit_nodes=transit_nodes.drop_duplicates()
transit_stops_ids = transit_nodes[transit_nodes['Node']>0].Node.unique()
transit_stops = nodes_list[nodes_list['N'].isin(transit_stops_ids)][['N','X', 'Y']]

transit_stops['coord'] = transit_stops[['X','Y']].values.tolist()

transit_stops_coords_dict = dict(zip(transit_stops['N'], transit_stops['coord']))
pnr_nodes_coords_dict = dict(zip(pnr_nodes['N'], pnr_nodes['coord']))

list_node_distances = {}

for pnr in pnr_nodes_coords_dict.keys():
    pnr_xcoord = pnr_nodes_coords_dict.get(pnr)[0]
    pnr_ycoord = pnr_nodes_coords_dict.get(pnr)[1]

    distance_list = []
    nodes_within_a_mile = []
    for transit_node in transit_stops_coords_dict.keys():
        transit_node_xcoord = transit_stops_coords_dict.get(transit_node)[0]
        transit_node_ycoord = transit_stops_coords_dict.get(transit_node)[1]

        distance = ((transit_node_ycoord-pnr_ycoord)**2 + (transit_node_xcoord-pnr_xcoord)**2)**0.5/5280
        #math.dist(pnr_coord, transit_node_coord)/5280
        
        if distance<buffer_dist:
            nodes_within_a_mile.append(transit_node)
            distance_list.append(distance)

    list_node_distances[pnr] = nodes_within_a_mile


pnr_to_stops = pd.DataFrame(list_node_distances.items(), columns=['PNR','Stop'])
pnr_to_stops = pnr_to_stops.set_index(['PNR'])['Stop'].apply(pd.Series).stack().reset_index(level=0).rename(columns={0:'Stop'})
pnr_to_stops['PNR']=pnr_to_stops['PNR'].astype(str)
pnr_to_stops['Stop']=pnr_to_stops['Stop'].apply(lambda x: str(x).replace('.0',''))
pnr_to_stops['COL_1'] = 'PNR'
pnr_to_stops['COL_2'] = 'NODE='+pnr_to_stops['PNR']+'-'+pnr_to_stops['Stop']
pnr_to_stops['COL_3'] = 'ZONES=1-6593'
pnr_to_stops=pnr_to_stops[pnr_to_stops['PNR']!=pnr_to_stops['Stop']]
pnr_connector = r'../pnr_connectors.txt'

with open (pnr_connector, 'w') as f:

    df_string  = pnr_to_stops[['COL_1','COL_2','COL_3']].to_string(header=False, index=False)
    f.write(df_string)