USAGE = """

  python top_level_metrics_toll_revenues.py

  Run this from the model run dir.
  Processes model outputs and creates csvs for the relevant metric for every relevant scenario, called metrics\\top_level_metrics_toll_revenues_XX.csv
  
  Input Files:
    network_links.DBF: Roadway network information containing attributes like facility type, volume, and toll class designations.
    avgload5period_vehclasses.csv: Roadway network information containing attributes like facility type, volume, and toll class designations.
    network_links_TAZ.csv: Lookup table linking network links to Traffic Analysis Zones (TAZ) for geographic analysis.
    TOLLCLASS_Designations.xlsx: Excel file defining toll class designations used for categorizing toll facilities.
    taz1454_epcPBA50plus_2024_02_23.csv: Lookup file indicating Equity Priority Communitiy (EPC) designation for TAZs, used for classification.
  
  The generated CSV will contain the following columns:
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
    'Grouping',
    'value',
    'TOLLCLASS',
    'USEAM'
    
  Metrics are:
    1) Toll Revenues: toll revenues from new tolling (ie exclude any express lane or bridge toll revenues)
        - freeways
        - arterials
"""

import os
import pandas as pd
import argparse
import logging
import numpy
import simpledbf

# paths
TM1_GIT_DIR             = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
NGFS_MODEL_RUNS_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "ModelRuns_Round2.xlsx")
NGFS_SCENARIOS          = "L:\\Application\\Model_One\\NextGenFwys_Round2\\Scenarios"
NGFS_TOLLCLASS_FILE     = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "TOLLCLASS_Designations.xlsx")

# These calculations are complex enough that a debug log file would be helpful to track what's happening
LOG_FILE                = "top_level_metrics_toll_revenues.log" # in the cwd
LOGGER                  = None # will initialize in main     

# EPC lookup file - indicates whether a TAZ is designated as an EPC in PBA2050+
NGFS_EPC_TAZ_FILE    = "M:\\Application\\Model One\\RTP2025\\INPUT_DEVELOPMENT\\metrics\\metrics_01\\taz1454_epcPBA50plus_2024_02_23.csv"
NGFS_EPC_TAZ_DF      = pd.read_csv(NGFS_EPC_TAZ_FILE)

# source: https://github.com/BayAreaMetro/modeling-website/wiki/InflationAssumptions
INFLATION_FACTOR = 1.03
INFLATION_00_23 = (327.06 / 180.20) * INFLATION_FACTOR
INFLATION_00_20 = 300.08 / 180.20
REVENUE_DAYS_PER_YEAR = 260

def top_level_metrics_toll_revenues(tm_run_id: str) -> pd.DataFrame:
    """ Calculates top-level metrics (which are not part of the 10 metrics)
    These metrics are designed to give us overall understanding of the pathway, such as:

    - toll revenues from new tolling (ie exclude any express lane or bridge toll revenues)
        - freeways
        - arterials

    Args:
        tm_run_id (str): Travel model run ID
        [todo fill these in]
    
    Returns:
        pandas.DataFrame: with columns a subset of METRICS_COLUMNS, including 
          metric_id   = 'Toll Revenues'
          modelrun_id = tm_run_id
        Metrics returned:
          key                       intermediate/final    metric_desc
          [commute]_[mode]_[pkop]   top_level             trips
          [commute]_[mode]_[pkop]   top_level             trips
          [pkop]                    top_level             [mode]_commute_peak-vs-offpeak_share
          [pkop]                    top_level             [mode]_noncommute_peak-vs-offpeak_share
          [mode]                    top_level             [pkop]_[commute]_mode_share
        where [mode] is one of auto|transit|active, 
              [pkop] is one of peak|offpeak, and 
              [commute] is one of commute|noncommute
          TODO: add others
    """
    REVENUE_METHODOLOGY_AND_ASSUMPTIONS = """
    toll revenues - from Value Tolls field in auto times --> this is daily revenue in $2000 cents
    260 days a year
    convert cents to dollars
    adjust $2000 to $2023 for YOE revenue in 2023 using CPI index
    adjust $2023 to $2035 and beyond to $2050 using inflation factor 1.03
    your output variables should be
    annual revenue
    total 16 year revenue (2035-2050)
    each of those split by four income level and other (i.e. ix/air/truck)
    """

    # calculate toll revenues
    
    METRIC_ID = 'Toll Revenues'
    LOGGER.info("Calculating {} for {}".format(METRIC_ID, tm_run_id))

    loaded_network_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "shapefile", "network_links.DBF")
    LOGGER.info("Reading {}".format(loaded_network_file))
    network_links_dbf = simpledbf.Dbf5(loaded_network_file)
    loaded_network_df = network_links_dbf.to_dataframe()[['A', 'B', 'FT', 'USEAM',  'TOLLCLASS', \
                                                                         'VOLEA_DAT', \
                                                                         'VOLAM_DAT', \
                                                                         'VOLMD_DAT', \
                                                                         'VOLPM_DAT', \
                                                                         'VOLEV_DAT', \
                                                                         'VOLEA_TOT', \
                                                                         'VOLAM_TOT', \
                                                                         'VOLMD_TOT', \
                                                                         'VOLPM_TOT', \
                                                                         'VOLEV_TOT', \
                                                                         'TOLLEA_DA', \
                                                                         'TOLLAM_DA', \
                                                                         'TOLLMD_DA', \
                                                                         'TOLLPM_DA', \
                                                                         'TOLLEV_DA']]
    loaded_network_df.rename(columns=lambda x: x.strip(), inplace=True)
    LOGGER.info("  Read {:,} rows from {}".format(len(loaded_network_df), loaded_network_file))
    LOGGER.debug("  Columns: {}".format(list(loaded_network_df.columns)))
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
    
    loaded_network_df = pd.merge(left= loaded_network_df, right= tm_network_links_with_epc_df, left_on= ['A','B'], right_on= ['A', 'B'], how='left')
    LOGGER.debug("loaded_network_df =\n{}".format(loaded_network_df))
    
    # join to tolled minor group freeway links lookup table 
    loaded_network_df = pd.merge(left=loaded_network_df, right=TOLLED_FWY_MINOR_GROUP_LINKS_DF, how='left', left_on=['A','B'], right_on=['a','b'])
    
    for time_period in ['EA', 'AM', 'MD', 'PM', 'EV']:
        # volume for all lane tolling vs EL
        if any(x in tm_run_id for x in ['Path4', 'Path5', 'Path6']):
            # Drive Alone Tolled volume:
            VOL_string = 'VOL{}_DAT'.format(time_period)
        else:
            # All Lane Tolling string:
            VOL_string = 'VOL{}_TOT'.format(time_period)
            
        loaded_network_df['Daily {} Toll Revenue (2000$)'.format(time_period)] = (loaded_network_df[VOL_string]) * loaded_network_df['TOLL{}_DA'.format(time_period)] / 100
        loaded_network_df['Daily {} Toll Revenue (2020$)'.format(time_period)] = loaded_network_df['Daily {} Toll Revenue (2000$)'.format(time_period)] * INFLATION_00_20
        loaded_network_df['Daily {} Toll Revenue (2023$)'.format(time_period)] = loaded_network_df['Daily {} Toll Revenue (2000$)'.format(time_period)] * INFLATION_00_23
        loaded_network_df['Daily {} Toll Revenue (2035$)'.format(time_period)] = loaded_network_df['Daily {} Toll Revenue (2023$)'.format(time_period)] * INFLATION_FACTOR**(2035-2023)
        
    loaded_network_df['Daily Toll Revenue (2000$)'] = \
            (loaded_network_df['Daily EA Toll Revenue (2000$)']+
            loaded_network_df['Daily AM Toll Revenue (2000$)']+
            loaded_network_df['Daily MD Toll Revenue (2000$)']+
            loaded_network_df['Daily PM Toll Revenue (2000$)']+
            loaded_network_df['Daily EV Toll Revenue (2000$)'])
            
    loaded_network_df['Daily Toll Revenue (2020$)'] = loaded_network_df['Daily Toll Revenue (2000$)'] * INFLATION_00_20
    loaded_network_df['Daily Toll Revenue (2023$)'] = loaded_network_df['Daily Toll Revenue (2000$)'] * INFLATION_00_23
    loaded_network_df['Daily Toll Revenue (2035$)'] = loaded_network_df['Daily Toll Revenue (2023$)'] * INFLATION_FACTOR**(2035-2023)
            
    loaded_network_df['Annual Toll Revenue (2000$)'] = loaded_network_df['Daily Toll Revenue (2000$)'] * REVENUE_DAYS_PER_YEAR        
    loaded_network_df['Annual Toll Revenue (2020$)'] = loaded_network_df['Annual Toll Revenue (2000$)'] * INFLATION_00_20
    loaded_network_df['Annual Toll Revenue (2023$)'] = loaded_network_df['Annual Toll Revenue (2000$)'] * INFLATION_00_23
    loaded_network_df['Annual Toll Revenue (2035$)'] = loaded_network_df['Annual Toll Revenue (2023$)'] * INFLATION_FACTOR**(2035-2023)
    loaded_network_df['Sixteen Year Toll Revenue (YOE$)'] = (loaded_network_df['Annual Toll Revenue (2035$)'] * (1- INFLATION_FACTOR**15))/(1 - INFLATION_FACTOR)                    
    
    # https://github.com/BayAreaMetro/modeling-website/wiki/MasterNetworkLookupTables#facility-type-ft
    ft_to_grouping_key_df = pd.DataFrame(columns=['FT','Freeway/Non-Freeway','Facility Type Definition'], data=[
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
    loaded_network_df = pd.merge(left=loaded_network_df, right=ft_to_grouping_key_df, on='FT', how='left')

    # Recode
    loaded_network_df['EPC/Non-EPC'] = 'Non-EPCs'
    loaded_network_df.loc[ loaded_network_df.taz_epc == 1, 'EPC/Non-EPC'] = 'EPCs'

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
    loaded_network_df.loc[(loaded_network_df.TOLLCLASS > 0) & (loaded_network_df.TOLLCLASS < 9), 'Revenue Facilities'] = 'Bridge Tolls'
    loaded_network_df.loc[(loaded_network_df.TOLLCLASS > 8) & (loaded_network_df.TOLLCLASS < 37), 'Revenue Facilities'] = 'Cordon Tolls'
    loaded_network_df.loc[(loaded_network_df.TOLLCLASS > 36) & (loaded_network_df.TOLLCLASS < 700000), 'Revenue Facilities'] = 'Express Lane Tolls'
    loaded_network_df.loc[(loaded_network_df.TOLLCLASS > 699999) & (loaded_network_df.TOLLCLASS < 900000), 'Revenue Facilities'] = 'All Lane Tolling'    
    loaded_network_df.loc[(loaded_network_df.TOLLCLASS > 899999) & (loaded_network_df.TOLLCLASS < 1000000), 'Revenue Facilities'] = 'All Lane Tolling'    
    loaded_network_df.loc[(loaded_network_df.TOLLCLASS > 1000000) , 'Revenue Facilities'] = 'Express Lane Tolls'
    # fill empty collumns of DF with a string to retain al values in the DF
    loaded_network_df.grouping = loaded_network_df.grouping.fillna('NA')
    loaded_network_df.grouping_dir = loaded_network_df.grouping_dir.fillna('NA')
    
    LOGGER.debug("  Columns: {}".format(list(loaded_network_df.columns)))
    LOGGER.debug("loaded_network_df =\n{}".format(loaded_network_df))
    
    # loaded_network_df.to_csv("test.csv", index=False)

    ft_metrics_df = loaded_network_df.groupby(by=['Freeway/Non-Freeway','Facility Type Definition', 'EPC/Non-EPC', 'County', 'Revenue Facilities', 'grouping', 'grouping_dir', 'TOLLCLASS', 'USEAM']).agg({'Sixteen Year Toll Revenue (YOE$)':'sum', \
                                                                                                                                                                                               'Daily EA Toll Revenue (2000$)':'sum', \
                                                                                                                                                                                               'Daily EA Toll Revenue (2020$)':'sum', \
                                                                                                                                                                                               'Daily EA Toll Revenue (2023$)':'sum', \
                                                                                                                                                                                               'Daily EA Toll Revenue (2035$)':'sum', \
                                                                                                                                                                                               'Daily AM Toll Revenue (2000$)':'sum', \
                                                                                                                                                                                               'Daily AM Toll Revenue (2020$)':'sum', \
                                                                                                                                                                                               'Daily AM Toll Revenue (2023$)':'sum', \
                                                                                                                                                                                               'Daily AM Toll Revenue (2035$)':'sum', \
                                                                                                                                                                                               'Daily MD Toll Revenue (2000$)':'sum', \
                                                                                                                                                                                               'Daily MD Toll Revenue (2020$)':'sum', \
                                                                                                                                                                                               'Daily MD Toll Revenue (2023$)':'sum', \
                                                                                                                                                                                               'Daily MD Toll Revenue (2035$)':'sum', \
                                                                                                                                                                                               'Daily PM Toll Revenue (2000$)':'sum', \
                                                                                                                                                                                               'Daily PM Toll Revenue (2020$)':'sum', \
                                                                                                                                                                                               'Daily PM Toll Revenue (2023$)':'sum', \
                                                                                                                                                                                               'Daily PM Toll Revenue (2035$)':'sum', \
                                                                                                                                                                                               'Daily EV Toll Revenue (2000$)':'sum', \
                                                                                                                                                                                               'Daily EV Toll Revenue (2020$)':'sum', \
                                                                                                                                                                                               'Daily EV Toll Revenue (2023$)':'sum', \
                                                                                                                                                                                               'Daily EV Toll Revenue (2035$)':'sum', \
                                                                                                                                                                                               'Daily Toll Revenue (2000$)':'sum', \
                                                                                                                                                                                               'Daily Toll Revenue (2020$)':'sum', \
                                                                                                                                                                                               'Daily Toll Revenue (2023$)':'sum', \
                                                                                                                                                                                               'Daily Toll Revenue (2035$)':'sum', \
                                                                                                                                                                                               'Annual Toll Revenue (2000$)':'sum', \
                                                                                                                                                                                               'Annual Toll Revenue (2020$)':'sum', \
                                                                                                                                                                                               'Annual Toll Revenue (2023$)':'sum', \
                                                                                                                                                                                               'Annual Toll Revenue (2035$)':'sum'}).reset_index()
    LOGGER.debug("ft_metrics_df:\n{}".format(ft_metrics_df))

    # move to long form and return
    metrics_df = ft_metrics_df.melt(id_vars=['Freeway/Non-Freeway','Facility Type Definition','EPC/Non-EPC', 'County', 'Revenue Facilities', 'grouping', 'grouping_dir', 'TOLLCLASS', 'USEAM'], var_name='Metric Description')
    metrics_df['Model Run ID'] = tm_run_id
    metrics_df['Metric ID'] = METRIC_ID
    metrics_df['Intermediate/Final'] = 'final'
    metrics_df['Year'] = tm_run_id[:4]
    LOGGER.debug("metrics_df for Toll Revenues:\n{}".format(metrics_df))

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
    # current_runs_df = current_runs_df.loc[ (current_runs_df['directory'].str.contains('Path') == True)]

    LOGGER.info("current_runs_df: \n{}".format(current_runs_df))

    current_runs_list = current_runs_df['directory'].to_list()
    
    # find the last pathway 1 run, since we'll use that to determine which links are in the fwy minor groupings
    pathway1_runs = current_runs_df.loc[ current_runs_df['category'].str.startswith("P1")]
    PATHWAY1_SCENARIO_RUN_ID = pathway1_runs['directory'].tolist()[-1] # take the last one
    LOGGER.info("=> PATHWAY1_SCENARIO_RUN_ID = {}".format(PATHWAY1_SCENARIO_RUN_ID))
    TOLLED_FWY_MINOR_GROUP_LINKS_DF = determine_tolled_minor_group_links(PATHWAY1_SCENARIO_RUN_ID, "fwy")
    # TOLLED_FWY_MINOR_GROUP_LINKS_DF.to_csv("TOLLED_FWY_MINOR_GROUP_LINKS.csv", index=False)

    for tm_run_id in current_runs_list:
        out_filename = os.path.join(os.getcwd(),"top_level_metrics_toll_revenues_{}.csv".format(tm_run_id))

        if args.skip_if_exists and os.path.exists(out_filename):
            LOGGER.info("Skipping {} -- {} exists".format(tm_run_id, out_filename))
            continue

        LOGGER.info("Processing run {}".format(tm_run_id))

        # results will be stored here
        metrics_df = pd.DataFrame()
        
        # run function to calculate toll revenues
        metrics_df = top_level_metrics_toll_revenues(tm_run_id)
        LOGGER.info("@@@@@@@@@@@@@ Done")

        metrics_df.to_csv(out_filename, float_format='%.5f', index=False) #, header=False
        LOGGER.info("Wrote {}".format(out_filename))

        # for testing, stop here
        # sys.exit()