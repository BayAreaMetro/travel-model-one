import pandas as pd
import numpy as np
import math
import os, sys

model_run_dir = sys.argv[0]


buffer_dist = 0.125


#Remote I/O
nodes_list = pd.read_csv('../transit_background_nodes.csv')
transit_nodes = pd.read_csv('../all_transit_nodes.csv', names=['Node'])

zone_seq = pd.read_csv('../../hwy/complete_network_zone_seq.csv')
int_zone = zone_seq[zone_seq['EXTSEQ']==0].TAZSEQ.max()

if os.path.isfile('../pnr_connectors.txt'):
    print "File created in 0th iteration"
else:
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
    pnr_to_stops['COL_3'] = 'ZONES=1-'+str(int_zone)
    # pnr_to_stops=pnr_to_stops[pnr_to_stops['PNR']!=pnr_to_stops['Stop']]
    pnr_connector = r'../pnr_connectors.txt'
    with open (pnr_connector, 'w') as f:

        df_string  = pnr_to_stops[['COL_1','COL_2','COL_3']].to_string(header=False, index=False)
        f.write(df_string)

    print "Creating PNR Node to Transit Stop Correspondence and Transit Mode Served Database"

    with open('../transitOriginalAM.lin', "r") as f:
        lines = f.readlines()

        all_line_links = pd.DataFrame()
        curr_line = None
        line_node_seq = None

        for txt in lines:
            if txt.startswith("LINE NAME="):
                # store the current line name
                curr_line = txt.split("\"")[1]
                # reset line_node_seq as an empty list
                line_node_seq = []

            
            usera2 = txt.find(' USERA2')
            mode = txt.find(' MODE')
            first_node= txt.find(' N=')

            if usera2!=-1:
                value_usera2 = txt.split('=')[1].replace('"', '').replace(',', '').strip()

            if mode!=-1:
                value_mode = int(txt.split('=')[1].replace('"', '').replace(',', '').strip())

            if first_node!=-1:
                value_first_node = int(txt.split('=')[1].replace('"', '').replace(',', '').strip())
                line_node_seq.append(value_first_node)

            # add to node sequence if the first item of txt after split by "," and remove whitespace is digit
            if txt.strip().split(",")[0].replace("-", "").isdigit():
                node = int(txt.strip().split(",")[0])

                if node>0: line_node_seq.append(node)

            if curr_line and txt == "\n":
                line_links = pd.DataFrame({"line": curr_line, "node": line_node_seq, "usera2":value_usera2, "mode_code":value_mode})
                # add to all_line_links
                all_line_links = pd.concat([all_line_links, line_links]).reset_index(drop=True)

        all_line_links["node"] = all_line_links["node"].astype(int)
        all_line_links=all_line_links.drop_duplicates(['mode_code','node'])
        all_line_links.to_csv('../all_transit_stops.csv', index=False)

        for col in ['PNR','Stop']:
            pnr_to_stops[col]=pnr_to_stops[col].astype(int)


        pnr_to_stops['pnr_coord_X']=pnr_to_stops['PNR'].map(dict(zip(pnr_nodes['N'], pnr_nodes['X'])))
        pnr_to_stops['pnr_coord_Y']=pnr_to_stops['PNR'].map(dict(zip(pnr_nodes['N'], pnr_nodes['Y'])))
        pnr_to_stops['stop_coord_X']=pnr_to_stops['Stop'].map(dict(zip(transit_stops['N'], transit_stops['X'])))
        pnr_to_stops['stop_coord_Y']=pnr_to_stops['Stop'].map(dict(zip(transit_stops['N'], transit_stops['Y'])))

        pnr_to_stops['transit_mode']=pnr_to_stops['Stop'].map(dict(zip(all_line_links['node'], all_line_links['usera2'])))

        pnr_to_stops['distance'] = ((pnr_to_stops['stop_coord_Y']-pnr_to_stops['pnr_coord_Y'])**2+(pnr_to_stops['stop_coord_X']-pnr_to_stops['pnr_coord_X'])**2)**0.5/5280

        pnr_to_stops_grouped = pnr_to_stops.groupby(['transit_mode','Stop'], as_index=False).apply(lambda x: x.head(2)).reset_index().sort_values(by=['PNR','transit_mode','distance'])

        pnr_to_stops_grouped[['PNR','Stop','transit_mode','distance']].to_csv("../PNR_STOP.csv", index=False)