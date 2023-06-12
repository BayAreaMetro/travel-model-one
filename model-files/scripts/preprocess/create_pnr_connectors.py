import pandas as pd
import numpy as np
import math
import argparse
import os, sys

model_run_dir = sys.argv[1]


parser = argparse.ArgumentParser()
parser.add_argument("--transit_buffer",type=float, help="Specify maximum distance (in miles) from PNR node to transit stops")

args = parser.parse_args()

buffer_dist =args.transit_buffer


#Remote I/O
nodes_list = pd.read_csv(os.path.join(model_run_dir,'trn/transit_background_nodes.csv'))
transit_nodes = pd.read_csv(os.path.join(model_run_dir,'trn/all_transit_nodes.csv'), names=['Node'])


pnr_nodes = nodes_list[nodes_list['PNR']=='1.0'][['N', 'X', 'Y']]
pnr_nodes['coord'] = pnr_nodes[['X','Y']].values.tolist()

transit_nodes=transit_nodes.drop_duplicates()
transit_stops_ids = transit_nodes[transit_nodes['Node']>0].Node.unique()
transit_stops = nodes_list[nodes_list['N'].isin(transit_stops_ids)][['N','X', 'Y']]

transit_stops['coord'] = transit_stops[['X','Y']].values.tolist()

transit_stops_coords_dict = dict(zip(transit_stops['N'], transit_stops['coord']))
pnr_nodes_coords_dict = dict(zip(pnr_nodes['N'], pnr_nodes['coord']))

list_node_distances = {}

for pnr in pnr_nodes_coords_dict.keys():
    pnr_coord = pnr_nodes_coords_dict.get(pnr)

    distance_list = []
    nodes_within_a_mile = []
    for transit_node in transit_stops_coords_dict.keys():
        transit_node_coord = transit_stops_coords_dict.get(transit_node)

        distance = math.dist(pnr_coord, transit_node_coord)/5280
        
        if distance<buffer_dist:
            nodes_within_a_mile.append(transit_node)
            distance_list.append(distance)

    list_node_distances[pnr] = nodes_within_a_mile


pnr_to_stops = pd.DataFrame(list_node_distances.items(), columns=['PNR','Stop'])
pnr_to_stops = pnr_to_stops.explode('Stop')
pnr_to_stops['PNR']=pnr_to_stops['PNR'].astype(str)
pnr_to_stops['Stop']=pnr_to_stops['Stop'].astype(str)
pnr_to_stops['COL_1'] = 'PNR'
pnr_to_stops['COL_2'] = 'NODE='+pnr_to_stops['PNR']+'-'+pnr_to_stops['Stop']
pnr_to_stops['COL_3'] = 'ZONES=1-6593'

pnr_connector = r'trn\pnr_connectors.txt'

with open (pnr_connector, 'a') as f:

    df_string  = pnr_to_stops[['COL_1','COL_2','COL_3']].to_string(header=False, index=False)
    f.write(df_string)