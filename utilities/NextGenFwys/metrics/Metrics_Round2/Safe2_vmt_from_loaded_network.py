USAGE = """

  python Safe2_vmt_from_loaded_network.py

  Run this from the model run dir.
  Processes model outputs and creates a single csv with scenario metrics, called metrics\Change_in_vmt_from_loaded_network_XX.csv
  
  This file will have the following columns:
    'Freeway/Non-Freeway',
    'EPC/Non-EPC',
    'Tolled/Non-tolled Facilities',
    'Model Run ID',
    'Metric ID',
    'Intermediate/Final', 
    'Facility Type Definition',
    'Metric Description',
    'County', 
    'Revenue Facilities',
    'value'
    
  Metrics are:
    1) Safe 2: Change in vehicle miles travelled on freeway and adjacent non-freeway facilities

"""

import os
import pandas as pd
import argparse
import logging
import numpy

# paths
TM1_GIT_DIR             = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
NGFS_MODEL_RUNS_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "ModelRuns_Round2.xlsx")
NGFS_SCENARIOS          = "L:\\Application\\Model_One\\NextGenFwys_Round2\\Scenarios"
NGFS_TOLLCLASS_FILE     = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "TOLLCLASS_Designations.xlsx")

# These calculations are complex enough that a debug log file would be helpful to track what's happening
LOG_FILE                = "Safe2_vmt_from_loaded_network.log" # in the cwd
LOGGER                  = None # will initialize in main     

# EPC lookup file - indicates whether a TAZ is designated as an EPC in PBA2050+
NGFS_EPC_TAZ_FILE    = "M:\\Application\\Model One\\RTP2025\\INPUT_DEVELOPMENT\\metrics\\metrics_01\\taz1454_epcPBA50plus_2024_02_23.csv"
NGFS_EPC_TAZ_DF      = pd.read_csv(NGFS_EPC_TAZ_FILE)

def calculate_Safe2_vmt_from_loaded_network(tm_run_id: str) -> pd.DataFrame:
    """ Calculates Safety 2: Change in vehicle miles travelled (VMT) on freeway and non-freeway facilities
    Additionally, calculates VMT segmented by different categories (households by income, non-houehold and trucks)
    and VMT segmented by whether or not the links are located in Equity Priority Communities (EPC) TAZS.

    Args:
        tm_run_id (str): Travel model run ID
    
    Returns:
        pd.DataFrame: with columns including
          Metric ID          = 'Safe2'
          Model Run ID        = tm_run_id
          Intermediate/Final = final
        Metrics return:
          Freeway/Non-Freeway              Facility Type Definition                                    Metric Description
          Household/Non-Household           inc[1234]                              VMT|VHT  (category breakdown)
          Non-Household          air|ix|zpv_tnc                         VMT|VHT
          Truck                  truck                                  VMT|VHT
          Freeway|Non-Freeway    Freeway|Arterial|Collector|Expressway  VMT|VHT  (facility type breakdown)
          Freeway|Non-Freeway    EPCs|Non-EPCs|Region                   VMT|VHT  (EPC/non-EPC breakdown)

    Notes: Uses
    * avgload5period.csv (for facility type breakdown)
    * vmt_vht_metrics_by_taz.csv (for EPC/non-EPC breakdown)
    """
    METRIC_ID = 'Safe 2'
    LOGGER.info("Calculating {} for {}".format(METRIC_ID, tm_run_id))

    loaded_network_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "avgload5period.csv")
    loaded_network_df = pd.read_csv(loaded_network_file)
    loaded_network_df.rename(columns=lambda x: x.strip(), inplace=True)
    LOGGER.info("  Read {:,} rows from {}".format(len(loaded_network_df), loaded_network_file))
    LOGGER.debug("  Columns:".format(list(loaded_network_df.columns)))
    LOGGER.debug("loaded_network_df =\n{}".format(loaded_network_df))

    # load network_links_TAZ.csv as lookup df to use for equity metric:
    #     --> calculate VMT for arterial road links in EPCs vs region
    #         --> tolled aerterials within EPCs 
    # load network link to TAZ lookup file

    tm_network_links_taz_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "shapefile", "network_links_TAZ.csv")
    tm_network_links_taz_df = pd.read_csv(tm_network_links_taz_file)[['A', 'B', 'TAZ1454', 'linktaz_share']]
    LOGGER.info("  Read {:,} rows from {}".format(len(tm_network_links_taz_df), tm_network_links_taz_file))
    # join to epc lookup table
    tm_network_links_with_epc_df = pd.merge(
        left=tm_network_links_taz_df,
        right=NGFS_EPC_TAZ_DF,
        left_on="TAZ1454",
        right_on="TAZ1454",
        how='left')
    tm_network_links_with_epc_df = tm_network_links_with_epc_df.sort_values('linktaz_share', ascending=False).drop_duplicates(['A', 'B']).sort_index()
    LOGGER.debug("tm_network_links_with_epc_df =\n{}".format(tm_network_links_with_epc_df))
    
    loaded_network_df = pd.merge(left= loaded_network_df, right= tm_network_links_with_epc_df, left_on= ['a','b'], right_on= ['A', 'B'], how='left')
    LOGGER.debug("loaded_network_df =\n{}".format(loaded_network_df))
    
    # join to tolled minor group freeway links lookup table 
    loaded_network_df = pd.merge(left=loaded_network_df, right=TOLLED_FWY_MINOR_GROUP_LINKS_DF, how='left', left_on=['a','b'], right_on=['a','b'])

    # compute Fwy and Non_Fwy VMT
    loaded_network_df['Total VMT'] = \
        (loaded_network_df['volEA_tot']+
         loaded_network_df['volAM_tot']+
         loaded_network_df['volMD_tot']+
         loaded_network_df['volPM_tot']+
         loaded_network_df['volEV_tot'])*loaded_network_df['distance']
        
    loaded_network_df['EA VMT'] = \
        (loaded_network_df['volEA_tot'])*loaded_network_df['distance']
        
    loaded_network_df['AM VMT'] = \
        (loaded_network_df['volAM_tot'])*loaded_network_df['distance']
        
    loaded_network_df['MD VMT'] = \
        (loaded_network_df['volMD_tot'])*loaded_network_df['distance']
        
    loaded_network_df['PM VMT'] = \
        (loaded_network_df['volPM_tot'])*loaded_network_df['distance']
        
    loaded_network_df['EV VMT'] = \
        (loaded_network_df['volEV_tot'])*loaded_network_df['distance']
                    
    loaded_network_df['VHT'] = (\
        (loaded_network_df['ctimEA']*loaded_network_df['volEA_tot']) + \
        (loaded_network_df['ctimAM']*loaded_network_df['volAM_tot']) + \
        (loaded_network_df['ctimMD']*loaded_network_df['volMD_tot']) + \
        (loaded_network_df['ctimPM']*loaded_network_df['volPM_tot']) + \
        (loaded_network_df['ctimEV']*loaded_network_df['volEV_tot']))/60.0
    
    # https://github.com/BayAreaMetro/modeling-website/wiki/MasterNetworkLookupTables#facility-type-ft
    ft_to_grouping_key_df = pd.DataFrame(columns=['ft','Freeway/Non-Freeway','Facility Type Definition'], data=[
        ( 1, 'Freeway',    'Freeway'   ), # freeway-to-freeway connector
        ( 2, 'Freeway',    'Freeway'   ), # freeway
        ( 3, 'Non-Freeway','Expressway'), # expressway
        ( 4, 'Non-Freeway','Collector' ), # collector
        ( 5, 'Freeway',    'Freeway'   ), # freeway ramp
        ( 6, 'Non-Freeway','Other'     ), # dummy link --> include VMT from FT==6 links because they’re a proxy for VMT on roads not included in the model network.
        ( 7, 'Non-Freeway','Arterial'  ), # major arterial
        ( 8, 'Freeway',    'Freeway'   ), # managed freeway
        ( 9, None,          None       ), # special facility
        (10, None,          None       )  # toll plaza
    ])
    # NOTE: this is inconsistent with the vmt_vht_metrics.csv road_type for 'non-freeway' which includes
    # ft [1,2,3,5,8] as 'freeway' and all others as 'non-freeway'
    # https://github.com/BayAreaMetro/travel-model-one/blob/78fb93e881348f794e3423f3a987753a0eef1255/utilities/RTP/metrics/hwynet.py#L334

    LOGGER.debug("  Using facility type categories:\n{}".format(ft_to_grouping_key_df))
    loaded_network_df = pd.merge(left=loaded_network_df, right=ft_to_grouping_key_df, on='ft', how='left')

    # Recode
    loaded_network_df['EPC/Non-EPC'] = 'Non-EPCs'
    loaded_network_df.loc[ loaded_network_df.taz_epc == 1, 'EPC/Non-EPC'] = 'EPCs'

    # identify tolled arterial links 
    loaded_network_df['Tolled/Non-tolled Facilities'] = 'Non-tolled facilities'
    loaded_network_df.loc[loaded_network_df.tollclass > 700000, 'Tolled/Non-tolled Facilities'] = 'Tolled facilities'
    loaded_network_df.loc[(loaded_network_df.tollclass > 10) & (loaded_network_df.tollclass < 3000), 'Tolled/Non-tolled Facilities'] = 'Express Lanes'

    # add field for County using TAZ
    # reference: https://github.com/BayAreaMetro/modeling-website/wiki/TazData
    loaded_network_df['County'] = 'NA'
    loaded_network_df.loc[(loaded_network_df.TAZ1454 > 0) & (loaded_network_df.TAZ1454 < 191), 'County'] = 'San Francisco'
    loaded_network_df.loc[(loaded_network_df.TAZ1454 > 190) & (loaded_network_df.TAZ1454 < 347), 'County'] = 'San Mateo'
    loaded_network_df.loc[(loaded_network_df.TAZ1454 > 346) & (loaded_network_df.TAZ1454 < 715), 'County'] = 'Santa Clara'
    loaded_network_df.loc[(loaded_network_df.TAZ1454 > 714) & (loaded_network_df.TAZ1454 < 1040), 'County'] = 'Alameda'
    loaded_network_df.loc[(loaded_network_df.TAZ1454 > 1039) & (loaded_network_df.TAZ1454 < 1211), 'County'] = 'Contra Costa'
    loaded_network_df.loc[(loaded_network_df.TAZ1454 > 1210) & (loaded_network_df.TAZ1454 < 1291), 'County'] = 'Solano'
    loaded_network_df.loc[(loaded_network_df.TAZ1454 > 1290) & (loaded_network_df.TAZ1454 < 1318), 'County'] = 'Napa'
    loaded_network_df.loc[(loaded_network_df.TAZ1454 > 1317) & (loaded_network_df.TAZ1454 < 1404), 'County'] = 'Sonoma'
    loaded_network_df.loc[(loaded_network_df.TAZ1454 > 1403) & (loaded_network_df.TAZ1454 < 1455), 'County'] = 'Marin'
    
    # add field for ALT, EL, Bridges, Cordons using TAZ
    loaded_network_df['Revenue Facilities'] = 'NA'
    loaded_network_df.loc[(loaded_network_df.tollclass > 0) & (loaded_network_df.tollclass < 9), 'Revenue Facilities'] = 'Bridge Tolls'
    loaded_network_df.loc[(loaded_network_df.tollclass > 8) & (loaded_network_df.tollclass < 37), 'Revenue Facilities'] = 'Cordon Tolls'
    loaded_network_df.loc[(loaded_network_df.tollclass > 36) & (loaded_network_df.tollclass < 700000), 'Revenue Facilities'] = 'Express Lane Tolls'
    loaded_network_df.loc[(loaded_network_df.tollclass > 699999) & (loaded_network_df.tollclass < 900000), 'Revenue Facilities'] = 'All Lane Tolling'    
    loaded_network_df.loc[(loaded_network_df.tollclass > 899999) & (loaded_network_df.tollclass < 1000000), 'Revenue Facilities'] = 'All Lane Tolling'    
    
    # fill empty collumns of DF with a string to retain all values in the DF
    loaded_network_df.grouping = loaded_network_df.grouping.fillna('NA')
    loaded_network_df.grouping_dir = loaded_network_df.grouping_dir.fillna('NA')

    ft_metrics_df = loaded_network_df.groupby(by=['Freeway/Non-Freeway','Facility Type Definition', 'EPC/Non-EPC', 'Tolled/Non-tolled Facilities', 'County', 'Revenue Facilities', 'grouping', 'grouping_dir','tollclass']).agg({'Total VMT':'sum', \
                                                                                                                                                                                               'VHT':'sum', \
                                                                                                                                                                                               'EA VMT':'sum', \
                                                                                                                                                                                               'AM VMT':'sum', \
                                                                                                                                                                                               'MD VMT':'sum', \
                                                                                                                                                                                               'PM VMT':'sum',\
                                                                                                                                                                                               'EV VMT':'sum'}).reset_index()
    LOGGER.debug("ft_metrics_df:\n{}".format(ft_metrics_df))

    # put it together, move to long form and return
    metrics_df = ft_metrics_df
    metrics_df = metrics_df.melt(id_vars=['Freeway/Non-Freeway','Facility Type Definition','EPC/Non-EPC', 'Tolled/Non-tolled Facilities', 'County', 'Revenue Facilities', 'grouping', 'grouping_dir', 'tollclass'], var_name='Metric Description')
    metrics_df['Model Run ID'] = tm_run_id
    metrics_df['Metric ID'] = METRIC_ID
    metrics_df['Intermediate/Final'] = 'final'
    metrics_df['Year'] = tm_run_id[:4]
    LOGGER.debug("metrics_df for Safe 2:\n{}".format(metrics_df))

    return metrics_df

def determine_tolled_minor_group_links(tm_run_id: str, fwy_or_arterial: str) -> pd.DataFrame:
    """ Given a travel model run ID, reads the loaded network and the tollclass designations,
    and returns a table that will be used to define which links belong to which tollclass minor grouping.

    If fwy_or_arterial == "fwy",      tm_run_id should be a Pathway 1 model run, and this will return tolled freeway links
    If fwy_or_arterial == "arterial", tm_run_id should be a Pathway 2 model run, and this will return arterial freeway links

    This replaces 'Input Files\\a_b_with_minor_groupings.csv' because this uses the model network information directly

    Args:
        tm_run_id (str):      travel model run ID (should be Pathway 1 or 2)
        fwy_or_arterial(str): one of "fwy" or "arterial"

    Returns:
        pd.DataFrame: mapping from links to tollclass minor groupings.  Columns:
        a (int):              link A node
        b (int):              link B node
        grouping (str):       minor grouping without direction, e.g. EastBay_68024980, EastBay_880680, etc.
        grouping_dir (str):   either AM or PM for the grouping
    """
    if fwy_or_arterial not in ["fwy","arterial"]: raise ValueError

    LOGGER.info("=== determine_tolled_minor_group_links({}, {}) ===".format(tm_run_id, fwy_or_arterial))
    loaded_roadway_network = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "avgload5period_vehclasses.csv")
    tm_loaded_network_df = pd.read_csv(loaded_roadway_network, 
                                       usecols=['a','b','tollclass','ft'],
                                       dtype={'a':numpy.int64, 'b':numpy.int64, 'tollclass':numpy.int64},
                                       na_values=[''])
    LOGGER.info("  Read {:,} rows from {}".format(len(tm_loaded_network_df), loaded_roadway_network))

    # read toll class groupings
    tollclass_df = pd.read_excel(NGFS_TOLLCLASS_FILE)
    LOGGER.info("  Read {:,} rows from {}".format(len(tollclass_df), NGFS_TOLLCLASS_FILE))
    # select NextGenFwy tollclasses where 'Grouping minor' exists
    tollclass_df = tollclass_df.loc[(tollclass_df.project == 'NextGenFwy') & pd.notna(tollclass_df['Grouping minor'])]

    # See TOLLCLASS_Designations.xlsx workbook, Readme - numbering convention
    if fwy_or_arterial == "fwy":
        tollclass_df = tollclass_df.loc[tollclass_df.tollclass > 900000]
    elif fwy_or_arterial == "arterial":
        tollclass_df = tollclass_df.loc[(tollclass_df.tollclass > 700000) & 
                                        (tollclass_df.tollclass < 900000)]

    LOGGER.info("  Filtered to {:,} rows for project=='NextGenFwy' with notna 'Grouping minor' and tollclass appropriate to {}".format(
        len(tollclass_df), fwy_or_arterial))
    # LOGGER.info("  Grouping minor: {}".format(sorted(tollclass_df['Grouping minor'].to_list())))

    # add to loaded roadway network -- INNER JOIN
    grouping_df = pd.merge(
        left=tm_loaded_network_df,
        right=tollclass_df[['tollclass','Grouping minor']],
        on=['tollclass'],
        how='inner'
    )
    # remove rows with 'Minor grouping' that doesn't end in AM or PM
    grouping_df = grouping_df.loc[
        grouping_df['Grouping minor'].str.endswith('_AM') |
        grouping_df['Grouping minor'].str.endswith('_PM')
    ]

    # log the facility type summary
    LOGGER.debug("  Tolled {} facility types:\n{}".format(fwy_or_arterial, grouping_df['ft'].value_counts()))

    # split 'Grouping minor' to 'grouping' (now without direction) and 'grouping_dir'
    grouping_df['grouping_dir'] = grouping_df['Grouping minor'].str[-2:]
    grouping_df['grouping']     = grouping_df['Grouping minor'].str[:-3]
    grouping_df.drop(columns=['Grouping minor','tollclass','ft'], inplace=True)
    LOGGER.debug("  Returning {:,} links:\n{}".format(len(grouping_df), grouping_df))
    return grouping_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip_if_exists", action="store_true", help="Use this option to skip creating metrics files if one exists already")
    args = parser.parse_args()

    pd.options.display.width = 500 # redirect output to file so this will be readable
    pd.options.display.max_columns = 100
    pd.options.display.max_rows = 500
    pd.options.mode.chained_assignment = None  # default='warn'

    # set up logging
    # create logger
    LOGGER = logging.getLogger(__name__)
    LOGGER.setLevel('DEBUG')

    # console handler
    ch = logging.StreamHandler()
    ch.setLevel('INFO')
    ch.setFormatter(logging.Formatter('%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    LOGGER.addHandler(ch)
    # file handler -- append if skip_if_exists is passed
    fh = logging.FileHandler(LOG_FILE, mode='a' if args.skip_if_exists else 'w')
    fh.setLevel('DEBUG')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    LOGGER.addHandler(fh)

    LOGGER.debug("args = {}".format(args))

    current_runs_df = pd.read_excel(NGFS_MODEL_RUNS_FILE, sheet_name='all_runs', usecols=['project','year','directory','run_set','category','short_name','status'])
    current_runs_df = current_runs_df.loc[ current_runs_df['status'] == 'current']
    # only process metrics for 2035 model runs 
    current_runs_df = current_runs_df.loc[ current_runs_df['year'] == 2035]
    # # TODO: delete later after NP10 runs are completed
    # current_runs_df = current_runs_df.loc[ (current_runs_df['directory'].str.contains('NP10') == False)]

    LOGGER.info("current_runs_df: \n{}".format(current_runs_df))

    current_runs_list = current_runs_df['directory'].to_list()
            
    # find the last pathway 1 run, since we'll use that to determine which links are in the fwy minor groupings
    pathway1_runs = current_runs_df.loc[ current_runs_df['category'].str.startswith("Pathway 1")]
    PATHWAY1_SCENARIO_RUN_ID = pathway1_runs['directory'].tolist()[-1] # take the last one
    LOGGER.info("=> PATHWAY1_SCENARIO_RUN_ID = {}".format(PATHWAY1_SCENARIO_RUN_ID))
    TOLLED_FWY_MINOR_GROUP_LINKS_DF = determine_tolled_minor_group_links(PATHWAY1_SCENARIO_RUN_ID, "fwy")
    # TOLLED_FWY_MINOR_GROUP_LINKS_DF.to_csv("TOLLED_FWY_MINOR_GROUP_LINKS.csv", index=False)

    for tm_run_id in current_runs_list:
        out_filename = os.path.join(os.getcwd(),"Change_in_vmt_from_loaded_network_{}.csv".format(tm_run_id))

        if args.skip_if_exists and os.path.exists(out_filename):
            LOGGER.info("Skipping {} -- {} exists".format(tm_run_id, out_filename))
            continue

        LOGGER.info("Processing run {}".format(tm_run_id))

        # results will be stored here
        metrics_df = pd.DataFrame()

        metrics_df = calculate_Safe2_vmt_from_loaded_network(tm_run_id)
        LOGGER.info("@@@@@@@@@@@@@ Done")

        metrics_df.to_csv(out_filename, float_format='%.5f', index=False) #, header=False
        LOGGER.info("Wrote {}".format(out_filename))

        # for testing, stop here
        # sys.exit()