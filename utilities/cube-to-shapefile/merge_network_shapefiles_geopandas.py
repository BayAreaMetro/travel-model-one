import geopandas as gpd
import pandas as pd
import os, logging, time

today = time.strftime('%Y_%m_%d')

# TODO: make the following inputs use-defined args
M_dir = r'M:\Application\Model One\RTP2025\INPUT_DEVELOPMENT\Networks'
network_versions = ['v16']
years = [2023, 2025]
scens = ['Blueprint', 'Baseline']

# LOG_FILE = os.path.join(M_dir, 'network_comparison', 'merge_networks_{}.log'.format(today))

# # set up logging
# logger = logging.getLogger()
# logger.setLevel(logging.DEBUG)
# # console handler
# ch = logging.StreamHandler()
# ch.setLevel(logging.INFO)
# ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
# logger.addHandler(ch)
# # file handler
# fh = logging.FileHandler(LOG_FILE, mode='w')
# fh.setLevel(logging.DEBUG)
# fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
# logger.addHandler(fh)

network_links_list = []
network_trn_lines_list = []
network_trn_route_links_list = []
network_trn_stops_list = []
tolls_list = []

# loop through versions and year
for version in network_versions:
    for year in years:
        for scen in scens:
            print('network version: {}, year: {}, scenario : {}'.format(version, year, scen))
            network_dir = os.path.join(M_dir, 'BlueprintNetworks_{}'.format(str(version)), 'net_{}_{}'.format(str(year), scen))
            print('network_dir: {}'.format(network_dir))

            # TODO: add script to handle cases when a year or scen is not available

            network_links = gpd.read_file(os.path.join(network_dir, 'shapefiles', 'network_links.shp'))
            network_links['version'] = version + '_' + str(year) + '_' + scen
            print(network_links.head())
            network_links_list.append(network_links)
            
            network_trn_lines = gpd.read_file(os.path.join(network_dir, 'shapefiles', 'network_trn_lines.shp'))
            network_trn_lines['version'] = version + '_' + str(year) + '_' + scen
            print(network_trn_lines.head())
            network_trn_lines_list.append(network_trn_lines)

            network_trn_route_links = gpd.read_file(os.path.join(network_dir, 'shapefiles', 'network_trn_route_links.shp'))
            network_trn_route_links['version'] = version + '_' + str(year) + '_' + scen
            print(network_trn_route_links.head())
            network_trn_route_links_list.append(network_trn_route_links)

            network_trn_stops = gpd.read_file(os.path.join(network_dir, 'shapefiles', 'network_trn_stops.shp'))
            network_trn_stops['version'] = version + '_' + str(year) + '_' + scen
            print(network_trn_stops.head())
            network_trn_stops_list.append(network_trn_stops)

            tolls = pd.read_csv(os.path.join(network_dir, 'hwy', 'tolls.csv'))
            tolls['version'] = version + '_' + str(year) + '_' + scen
            print(tolls.head())
            tolls_list.append(tolls)


network_links_comp = pd.concat(network_links_list)
network_trn_lines_comp = pd.concat(network_trn_lines_list)
network_trn_route_links_comp = pd.concat(network_trn_route_links_list)
network_trn_stops_comp = pd.concat(network_trn_stops_list)
tolls_comp = pd.concat(tolls_list)

network_links_comp.to_file(os.path.join(M_dir, 'network_comparison', 'network_links_comp.shp'))
network_trn_lines_comp.to_file(os.path.join(M_dir, 'network_comparison', 'network_trn_lines_comp.shp'))
network_trn_route_links_comp.to_file(os.path.join(M_dir, 'network_comparison', 'network_trn_route_links_comp.shp'))
network_trn_stops_comp.to_file(os.path.join(M_dir, 'network_comparison', 'network_trn_stops_comp.shp'))
tolls_comp.to_csv(os.path.join(M_dir, 'network_comparison', 'tolls.csv'), index=False)
