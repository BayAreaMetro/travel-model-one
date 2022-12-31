USAGE = """
Processes transit output to tag tansit links/lines to illustrate transit services that run on freeways and
tolled arterials per NextGenFwy Pathway strategies; the result will be used to visualize transit utilizations.

Example call: python tag_transit_on_freeway_arterial.py '2035_TM152_NGF_NP02_BPALTsegmented_03_SimpleTolls01'

Inputs: 
    - model run transit output already converted to shapefile:  
        - network_trn_links.shp
        - network_trn_route_links.shp
        - network_trn_lines.shp
        - quickboards.xls
    - roadway links on freeways and tolled arterials, created by "get_freeway_arterial_links.py"
    - crosswalk among transit line number, system name, and mode category

Outputs: 
    - trn_links_FA_tag_[RUN_ID].shp: links with two new fields - "link_tag" ("freeway", "arterial", "heavy rail", "commuter rail", "non-FA")
                                     and "link_tag_cat" ("FA", "heavy rail", "commuter rail", "non-FA").
    - trn_lines_attrs_[RUN_ID].csv: transit line attributes, including standard model output fields, and additional fields
                                    representing the share of each line (in distance) that runs on freeway/arterial.
    - trn_route_links_FA_tag_[RUN_ID].shp: route_links with "link_tag" and "link_tag_cat" as described above.
    - line_weekly_boardings_[RUN_ID].csv: simplified quickboard, with only "weekly boardings" data for each line.
"""

import pandas as pd
import numpy as np
import geopandas as gpd
import xlrd
# from simpledbf import Dbf5
import argparse, os, sys, logging, time

today = time.strftime("%Y_%m_%d")

if __name__ == '__main__':

    # process one run at a time
    parser = argparse.ArgumentParser(description=USAGE)
    parser.add_argument('run_id', help='Provide the full Run ID')
    args = parser.parse_args()

    ############ I/O based on run_id arg
    ## INPUT
    # 1. freeway and tolled-arterial links, created by "get_freeway_arterial_links.py".
    FREEWAY_ARTERIAL_LINKS_FILE = os.path.join(
        "L:\\Application\\Model_One\\NextGenFwys\\Transit_Utilization", "freeway_arterial_links.csv")

    # 2. model transit output
    RUN_DIR = "L:\\Application\\Model_One\\NextGenFwys\\Scenarios"

    RUN_ID = args.run_id

    TRANSIT_LINKS_RAW_FILES = os.path.join(RUN_DIR, RUN_ID, "OUTPUT", "trn", "trnlink.csv")

    NETWORK_OUTPUT_DIR = os.path.join(RUN_DIR, RUN_ID, "OUTPUT", "shapefile")
    if RUN_ID == "2035_TM152_NGF_NP02_BPALTsegmented_03":
        NETWORK_OUTPUT_DIR = os.path.join(RUN_DIR, RUN_ID, "OUTPUT", "shapefile - no crowding")

    TRN_LINKS_FILE = os.path.join(NETWORK_OUTPUT_DIR, 'network_trn_links.shp')
    TRN_ROUTE_LINKS_FILE = os.path.join(NETWORK_OUTPUT_DIR, 'network_trn_route_links.shp')
    # TRN_STOPS_FILE = os.path.join(NETWORK_OUTPUT_DIR, 'network_trn_stops.shp')
    TRN_LINES_FILE = os.path.join(NETWORK_OUTPUT_DIR, 'network_trn_lines.shp')

    QUICKBOARD_FILE = os.path.join(RUN_DIR, RUN_ID, "OUTPUT", "trn", "quickboards.xls")

    # 3. crosswalk
    # transit line number to Mode crosswalk
    LINE_SYSTEM_MODE_CROSSWALK_FILE = "L:\\Application\\Model_One\\NextGenFwys\\Quickboards_rollup\\system.csv"

    ## OUTPUT
    DATA_OUTPUT_DIR                = "L:\\Application\\Model_One\\NextGenFwys\\Transit_Utilization"
    TRN_LINKS_PROCESSED_FILE       = os.path.join(DATA_OUTPUT_DIR, 'trn_links_FA_tag_{}.shp'.format(RUN_ID))
    TRN_LINES_PROCESSED_FILE       = os.path.join(DATA_OUTPUT_DIR, 'trn_lines_attrs_{}.csv'.format(RUN_ID))
    TRN_ROUTE_LINKS_PROCESSED_FILE = os.path.join(DATA_OUTPUT_DIR, 'trn_route_links_FA_tag_{}.shp'.format(RUN_ID))
    QUICKBOARD_PROCESSED_FILE      = os.path.join(DATA_OUTPUT_DIR, 'line_weekly_boardings_{}.csv'.format(RUN_ID))
    LOG_FILE                       = os.path.join(DATA_OUTPUT_DIR, "tag_transit_FreewayArterial_{}_{}.log".format(RUN_ID, today))

    ############ set up logging
   # create logger
    logger = logging.getLogger(__name__)
    logger.setLevel('DEBUG')

    # console handler
    ch = logging.StreamHandler()
    ch.setLevel('INFO')
    ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(ch)
    # file handler
    fh = logging.FileHandler(LOG_FILE, mode='w')
    fh.setLevel('DEBUG')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(fh)

    logger.info("running tag_transit_on_freeway_arterials.py for: {}".format(RUN_ID))
    logger.info("model output dir: {}".format(os.path.join(RUN_DIR, RUN_ID, "OUTPUT")))
    logger.info("write out files for Tableau visualization at: {}".format(DATA_OUTPUT_DIR))

    ############ Tag transit links that run on freeways and tolled arterials

    ## identify transit links on freeways and tolled arterials

    # load transit links shapefile
    trn_links_gdf = gpd.read_file(TRN_LINKS_FILE)
    logger.info("load {:,} rows of transit links, {:,} unique A+B pair, the following columns: {}".format(
        trn_links_gdf.shape[0],
        trn_links_gdf[["A", "B"]].drop_duplicates().shape[0],
        list(trn_links_gdf)))
    logger.debug(trn_links_gdf.head())

    # dropping connectors, dummy links, and ferry
    logger.info("checking MODE_TYPE: \n{}".format(trn_links_gdf.MODE_TYPE.value_counts(dropna=False)))
    trn_links_gdf = trn_links_gdf.loc[trn_links_gdf.MODE_TYPE.isin(
        ["Local Bus", "Express Bus", "Light Rail", "Commuter Rail", "Heavy Rail"])]
    logger.info(
        "{:,} rows remain after removing connector/transfer/funnel links and ferry links".format(
            trn_links_gdf.shape[0]))

    # load freeway and tolled arterial links file
    freeway_arterial_links_df = pd.read_csv(FREEWAY_ARTERIAL_LINKS_FILE)
    logger.info("merging freeway and arterial links with transit links")
    trn_links_tagged = trn_links_gdf.merge(freeway_arterial_links_df, on=["A", "B"], how="left", indicator=True)
    logger.info("check merging result: \n{}".format(trn_links_tagged["_merge"].value_counts()))

    # highlight 5 sets of links - "freeway", "arterial", "heavy rail", "commuter rail", "non-FA"
    freeway_idx          = (trn_links_tagged["_merge"] == "both") & (trn_links_tagged["link_tag"] == "freeway")
    arterial_tag_idx     = (trn_links_tagged["_merge"] == "both") & (trn_links_tagged["link_tag"] == "arterial")
    heavyRail_tag_idx    = (trn_links_tagged["_merge"] == "left_only") & (trn_links_tagged["MODE_TYPE"] == "Heavy Rail")
    commuterRail_tag_idx = (trn_links_tagged["_merge"] == "left_only") & (trn_links_tagged["MODE_TYPE"] == "Commuter Rail")

    # tag heavy rail, commuter rail and light rail links (links on freeway and arterial are already tagged)
    trn_links_tagged.loc[heavyRail_tag_idx, "link_tag"] = "heavy rail"
    trn_links_tagged.loc[commuterRail_tag_idx, "link_tag"] = "commuter rail"

    # fill na
    trn_links_tagged["link_tag"].fillna("non-FA", inplace=True)

    # also create a more aggregated "tag category" that combines "freeway" and "arterial"
    trn_links_tagged["link_tag_cat"] = "non-FA"
    trn_links_tagged.loc[trn_links_tagged["link_tag"].isin(["freeway", "arterial"]), "link_tag_cat"] = "FA"
    trn_links_tagged.loc[trn_links_tagged["link_tag"].isin(["heavy rail", "commuter rail"]), "link_tag_cat"] = trn_links_tagged["link_tag"]

    # drop "_merge"
    trn_links_tagged.drop(["_merge"], axis=1, inplace=True)

    logger.info(
        "transit links have the following link_tag: \n{}".format(
            trn_links_tagged["link_tag"].value_counts(dropna=False)))

    # TODO: there are inconsistencies between the system name (mode name) and mode type from the two sources. Check why.
    ## add system name to each link based on line name
    trn_links_tagged["MODE"] = trn_links_tagged["MODE"].astype(np.int8)

    # use the crosswalk file to get system name
    system_mode_crosswalk = pd.read_csv(LINE_SYSTEM_MODE_CROSSWALK_FILE)
    trn_links_tagged = pd.merge(
        left=trn_links_tagged,
        right=system_mode_crosswalk, 
        left_on="MODE",
        right_on="ID",
        how="left"
    )
    trn_links_tagged.drop(["ID"], axis=1, inplace=True)
    logger.debug(
        "after adding freeway/arterial tag and system name, trn_links_tagged has {:,} rows: \n{}".format(
            trn_links_tagged.shape[0], trn_links_tagged.head()
        ))

    # add run_id as a column
    trn_links_tagged['run_id'] = RUN_ID

    # # drop fields no longer needed
    # trn_links_tagged.drop(
    #     ['DIST_EA', 'DIST_AM', 'DIST_MD', 'DIST_PM', 'DIST_EV', 'TIME_EA', 'TIME_AM', 'TIME_MD', 'TIME_PM', 'TIME_EV'],
    #     axis=1,
    #     inplace=True)

    # export the shapefile
    trn_links_tagged_gdf = gpd.GeoDataFrame(trn_links_tagged, geometry="geometry")
    trn_links_tagged_gdf.to_file(TRN_LINKS_PROCESSED_FILE)


    ############ Get Line-level info

    ## calculate the share of freeway and arterial segments (by link distance) of each line

    # sum distances by line and tag_cat, for each time period
    # groupby and sum distances
    line_tag_dist_df = trn_links_tagged[["NAME", "A", "B", "link_tag_cat",
                                        "DIST_EA", "DIST_AM", "DIST_MD", "DIST_PM", "DIST_EV"]].copy()
    line_tag_dist_df = line_tag_dist_df.groupby(["NAME", "link_tag_cat"])[[
        'DIST_EA', 'DIST_AM', 'DIST_MD', 'DIST_PM', 'DIST_EV']].sum().reset_index()
    logger.debug(
        "group by line, link_tag_cat, and time-period, {:,} rows: \n{}".format(
            line_tag_dist_df.shape[0], line_tag_dist_df.head()))

    # pivot the dataframe to move tag_cat to columns
    line_tag_dist_df = line_tag_dist_df.pivot_table(index=["NAME"],
                                                    columns=["link_tag_cat"],
                                                    values=["DIST_EA", "DIST_AM", "DIST_MD", "DIST_PM", "DIST_EV"],
                                                    fill_value=0)
    line_tag_dist_df.columns = ['_'.join(col).strip() for col in line_tag_dist_df.columns.values]
    line_tag_dist_df.reset_index(inplace=True)
    logger.debug(
        "after pivoting the table, {:,} row: \n{}".format(
            line_tag_dist_df.shape[0], line_tag_dist_df.head()))

    # separately, sum distances by line, for each time period
    line_dist_df = trn_links_tagged[["NAME", "A", "B", "link_tag_cat",
                                    "DIST_EA", "DIST_AM", "DIST_MD", "DIST_PM", "DIST_EV"]].copy()
    line_dist_df = line_dist_df.groupby(["NAME"])[[
        "DIST_EA", "DIST_AM", "DIST_MD", "DIST_PM", "DIST_EV"]].sum().reset_index()
    logger.debug(
        "group by line and time-period, {:,} rows: \n{}".format(
            line_dist_df.shape[0], line_dist_df.head()))

    # calculate the shares of distances by tag_cat, for each time period
    # merge distance sums by tag_cat and by line only
    line_dist_share_df = pd.merge(line_tag_dist_df,
                                line_dist_df,
                                on=["NAME"],
                                how="outer")
    logger.debug("merging the two dfs, {:,} rows: \n{}".format(line_dist_share_df.shape[0], line_dist_share_df.head()))

    # calculate shares
    for i in ["EA", "AM", "MD", "PM", "EV"]:
        for j in ["non-FA", "FA", "heavy rail", "commuter rail"]:
            line_dist_share_df.loc[
                line_dist_share_df["DIST_" + i] > 0, "share_" + i + "_" + j
            ] = (
                line_dist_share_df["DIST_" + i + "_" + j] / line_dist_share_df["DIST_" + i]
            )

    logger.info(
        "after calculating distance shares, line_df has the following fields: {}".format(list(line_dist_share_df)))

    # adding the shares fields to trn_lines
    # load trn_lines
    logger.info("loading trn_lines.shp from {}".format(TRN_LINES_FILE))
    trn_lines_gdf = gpd.read_file(TRN_LINES_FILE)
    # merge
    share_cols = [col for col in line_dist_share_df.columns if "share" in col]
    trn_lines_with_share_df = pd.merge(
        line_dist_share_df[["NAME"]+ share_cols],
        trn_lines_gdf,
        on="NAME",
        how="left"
    )

    # add run_id as a column
    trn_lines_with_share_df["run_id"] = RUN_ID

    # export the needed fields as csv
    # trn_lines_with_share_gdf = gpd.GeoDataFrame(trn_lines_with_share_df, geometry="geometry")
    trn_lines_with_share_df.drop(["geometry"], axis=1, inplace=True)
    logger.info("exporting {:,} rows of line-level data to {}".format(trn_lines_with_share_df.shape[0], TRN_LINES_PROCESSED_FILE))
    trn_lines_with_share_df.to_csv(TRN_LINES_PROCESSED_FILE, index=False)


    ############ Process route_links data

    # load the data
    trn_route_links_gdf = gpd.read_file(TRN_ROUTE_LINKS_FILE)
    logger.info(
        "load {:,} rows of transit routes, {:,} unique A+B pair, the following columns: {}".format(
            trn_route_links_gdf.shape[0],
            trn_route_links_gdf[['A', 'B']].drop_duplicates().shape[0],
            list(trn_route_links_gdf)))

    logger.debug(trn_route_links_gdf.head())
    logger.info(trn_route_links_gdf.MODE_TYPE.value_counts(dropna=False))
    logger.info(trn_route_links_gdf.OPERATOR_T.value_counts(dropna=False))

    logger.info("merging freeway and arterial links with transit route_links")
    trn_route_links_tagged = trn_route_links_gdf.merge(freeway_arterial_links_df, on=["A", "B"], how="left", indicator=True)
    logger.info("check merging result: \n{}".format(trn_route_links_tagged["_merge"].value_counts()))

    # highlight 5 sets of links - "freeway", "arterial", "heavy rail", "commuter rail", "non-FA"
    freeway_idx          = (trn_route_links_tagged["_merge"] == "both") & (trn_route_links_tagged["link_tag"] == "freeway")
    arterial_tag_idx     = (trn_route_links_tagged["_merge"] == "both") & (trn_route_links_tagged["link_tag"] == "arterial")
    heavyRail_tag_idx    = (trn_route_links_tagged["_merge"] == "left_only") & (trn_route_links_tagged["MODE_TYPE"] == "Heavy Rail")
    commuterRail_tag_idx = (trn_route_links_tagged["_merge"] == "left_only") & (trn_route_links_tagged["MODE_TYPE"] == "Commuter Rail")

    # tag heavy rail, commuter rail and light rail links (links on freeway and arterial are already tagged)
    trn_route_links_tagged.loc[heavyRail_tag_idx,    "link_tag"] = "heavy rail"
    trn_route_links_tagged.loc[commuterRail_tag_idx, "link_tag"] = "commuter rail"

    # fill na
    trn_route_links_tagged["link_tag"].fillna("non-FA", inplace=True)

    # also create a more aggregated "tag category" that combines "freeway" and "arterial"
    trn_route_links_tagged["link_tag_cat"] = "non-FA"
    trn_route_links_tagged.loc[trn_route_links_tagged["link_tag"].isin(["freeway", "arterial"]), "link_tag_cat"] = "FA"
    trn_route_links_tagged.loc[trn_route_links_tagged["link_tag"].isin(["heavy rail", "commuter rail"]), "link_tag_cat"] = trn_links_tagged["link_tag"]

    # drop "_merge"
    trn_route_links_tagged.drop(["_merge"], axis=1, inplace=True)

    logger.info(
        "transit links have the following link_tag: \n{}".format(
            trn_route_links_tagged["link_tag"].value_counts(dropna=False)))

    # add run_id as a column
    trn_route_links_tagged["run_id"] = RUN_ID

    # export
    trn_route_links_tagged.to_file(TRN_ROUTE_LINKS_PROCESSED_FILE)
    logger.info("processed route_links shapefile exported")

    ############ Simplify quickboards
    logger.info("opening {}".format(QUICKBOARD_FILE))
    QUICKBOARD_FILE
    book = xlrd.open_workbook(QUICKBOARD_FILE, encoding_override="utf-8")
    sheet = pd.read_excel(book, engine="xlrd", sheet_name="LineStats", header=0)
    boardings_df = sheet.iloc[2:, 0:2].reset_index()
    boardings_df = boardings_df.iloc[:, 1:3]

    # rename columns
    boardings_df.columns = ["Line_Name", "Weekday_Boardings"]

    # add Run ID tag
    boardings_df["Run_ID"] = RUN_ID

    # add system name and Mode tags
    # first, get model number from line name
    boardings_df["ModeNumber"] = boardings_df["Line_Name"].apply(lambda x: int(x[0 : x.find("_")]))
    boardings_df["ModeNumber"] = boardings_df["ModeNumber"].astype(np.int8)

    # use the crosswalk to get system name and Mode
    boardings_df = pd.merge(
        left=boardings_df,
        right=system_mode_crosswalk, 
        left_on="ModeNumber",
        right_on="ID",
        how="left"
    )
    boardings_df.drop(["ID"], axis=1, inplace=True)

    # export
    boardings_df.to_csv(QUICKBOARD_PROCESSED_FILE, index=False)
