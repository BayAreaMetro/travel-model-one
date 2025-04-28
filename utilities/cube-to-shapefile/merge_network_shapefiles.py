USAGE = """

Merge (e.g. concatenate) network shapefiles from two different directories into a single shapefile via geopandas.
Assumes that the shapefiles have the same fields.

"""
import geopandas as gpd
import pandas as pd
import argparse, logging, pathlib, time


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument('--output_dir', default='network_comparison_FinalBlueprint')
    parser.add_argument('--years', type=int, nargs='+') # 1 or more required
    parser.add_argument('--baseline_version', type=str, required=True, nargs='+')
    parser.add_argument('--blueprint_version', type=str, required=True, nargs='+')
    args = parser.parse_args()

    network_versions = list(set(args.baseline_version + args.blueprint_version))
    M_dir = pathlib.Path('M:\\Application\\Model One\\RTP2025\\INPUT_DEVELOPMENT\\Networks')
    network_comparison_dir = M_dir / args.output_dir   # outputdir

    # make this if it doesn't exist
    network_comparison_dir.mkdir(exist_ok=True)

    TODAY_STR = time.strftime('%Y_%m_%d')
    LOG_FILE = network_comparison_dir / f'merge_networks_{TODAY_STR}.log'

    # set up logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(ch)
    # file handler
    fh = logging.FileHandler(LOG_FILE, mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(fh)

    # keep geoDataFrames for each version/year/scenario in this list
    network_links_list = []
    network_trn_lines_list = []
    network_trn_route_links_list = []
    network_trn_stops_list = []
    tolls_list = []
    ferryfare_list = []


    # loop through versions and year
    for version in network_versions:
        for year in args.years:
            for scen in  ['Blueprint', 'Baseline']:
                # only handle requested baseline or blueprint network versions
                if (scen == 'Baseline') and (version not in args.baseline_version): continue
                if (scen == 'Blueprint') and (version not in args.blueprint_version): continue

                logging.info(f'network version: {version}, year: {year}, scenario: {scen}')

                network_dir = M_dir / f'BlueprintNetworks_{version}' / f'net_{year}_{scen}'
                shapefile_dir = network_dir / 'shapefiles'
                logging.info(f'network_dir: {network_dir}')

                if not network_dir.exists():
                    logging.warning(f'network version: {version}, year: {year}, scenario: {scen} does not exist.')
                    continue

                if not shapefile_dir.exists():
                    logging.warning(f'{shapefile_dir} not yet created.')
                    continue

                network_links = gpd.read_file(shapefile_dir / 'network_links.shp')
                network_links['version'] = f'{version}_{year}_{scen}'
                logging.debug(f'network_links.head()=\n{network_links.head()}')
                network_links_list.append(network_links)
                
                network_trn_lines = gpd.read_file(shapefile_dir / 'network_trn_lines.shp')
                network_trn_lines['version'] = f'{version}_{year}_{scen}'
                logging.debug(f'network_trn_lines.head()=\n{network_trn_lines.head()}')
                network_trn_lines_list.append(network_trn_lines)

                network_trn_route_links = gpd.read_file(shapefile_dir / 'network_trn_route_links.shp')
                network_trn_route_links['version'] = f'{version}_{year}_{scen}'
                logging.debug(f'network_trn_route_links.head()=\n{network_trn_route_links.head()}')
                network_trn_route_links_list.append(network_trn_route_links)

                network_trn_stops = gpd.read_file(shapefile_dir / 'network_trn_stops.shp')
                network_trn_stops['version'] = f'{version}_{year}_{scen}'
                logging.debug(f'network_trn_stops.head()=\n{network_trn_stops.head()}')
                network_trn_stops_list.append(network_trn_stops)

                tolls = pd.read_csv(network_dir / 'hwy' / 'tolls.csv')
                tolls['version'] = f'{version}_{year}_{scen}'
                logging.debug(f'tolls.head()=\n{tolls.head()}')
                tolls_list.append(tolls)

                ferry_fares = pd.read_csv(network_dir / 'trn' / 'Ferry.far', comment=';', sep='\s+', dtype=int, 
                                          names=['from_node','to_node','fare'])
                ferry_fares['version'] = f'{version}_{year}_{scen}'
                logging.debug(f'ferry_fares.head()=\n{ferry_fares.head()}')
                # according to cube documentation, these are implicitly bi-directional if direction isn't specified, which it isn't
                # so add the reverse
                ferry_fares_reverse = ferry_fares.copy()
                ferry_fares_reverse.rename(columns={'from_node':'to_node','to_node':'from_node'}, inplace=True)
                logging.debug(f'ferry_fares_reverse.head()=\n{ferry_fares_reverse.head()}')

                ferryfare_list.append(pd.concat([ferry_fares,ferry_fares_reverse]))

    network_links_comp = pd.concat(network_links_list)
    network_trn_lines_comp = pd.concat(network_trn_lines_list)
    network_trn_route_links_comp = pd.concat(network_trn_route_links_list)
    network_trn_stops_comp = pd.concat(network_trn_stops_list)
    tolls_comp = pd.concat(tolls_list)
    ferry_fares_comp = pd.concat(ferryfare_list)

    # write them
    network_links_comp.to_file(network_comparison_dir / 'network_links_comp.shp')
    logger.info(f"Wrote {len(network_links_comp):,} rows to {network_comparison_dir / 'network_links_comp.shp'}")

    network_trn_lines_comp.to_file(network_comparison_dir /'network_trn_lines_comp.shp')
    logger.info(f"Wrote {len(network_trn_lines_comp):,} rows to {network_comparison_dir / 'network_trn_lines_comp.shp'}")

    network_trn_route_links_comp.to_file(network_comparison_dir / 'network_trn_route_links_comp.shp')
    logger.info(f"Wrote {len(network_trn_route_links_comp):,} rows to {network_comparison_dir / 'network_trn_route_links_comp.shp'}")

    network_trn_stops_comp.to_file(network_comparison_dir / 'network_trn_stops_comp.shp')
    logger.info(f"Wrote {len(network_trn_stops_comp):,} rows to {network_comparison_dir / 'network_trn_stops_comp.shp'}")

    tolls_comp.to_csv(network_comparison_dir / 'tolls.csv', index=False)
    logger.info(f"Wrote {len(tolls_comp):,} rows to {network_comparison_dir / 'tolls.csv'}")

    ferry_fares_comp.to_csv(network_comparison_dir / 'ferry_fares.csv', index=False)
    logger.info(f"Wrote {len(ferry_fares_comp):,} rows to {network_comparison_dir / 'ferry_fares.csv'}")
