USAGE = r"""

  Updates parking cost per parking strategy

  See PBA50 Tasks: 
    En9 - Expand Transportation Demand Management Initiatives (https://app.asana.com/0/403262763383022/1188775845203320/f)
    Develop regional parking policy model inputs (https://app.asana.com/0/0/1191058546872345/f)
  And PBA50+ Tasks:
    T5 parking pricing (https://app.asana.com/0/0/1206396214159345/f)
    Update 'TAZ_intersect_GG_TRA.xlsx" for parking strategies (https://app.asana.com/0/1204085012544660/1206586796423943/f)
    Final Blueprint: https://app.asana.com/0/1204959680579890/1208629862862979

  https://github.com/BayAreaMetro/modeling-website/wiki/TazData

"""

import argparse, logging, os, sys
import numpy, pandas

LOG_FILE                  = "updateParkingCostForParkingStrategy.log"
TAZ_GG_TRA_FILE           = "M:\\Application\\Model One\\RTP2025\\INPUT_DEVELOPMENT\\parking_strategy\\taz1454_GGnonPPA_TRA_crosswalk_FBP.csv"
PCT_AREA_THRESHOLD        = 0.20
BASE_PARKING_MIN_COST     = 25.0 # 2000 cents
STRATEGY_PARKING_INCREASE = 1.25 # multiplier

if __name__ == '__main__':
    pandas.options.display.width = 500
    pandas.options.display.max_rows = 1000

    # create logger
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

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    # parser.add_argument("model_year", help="Model year")
    parser.add_argument("original_tazdata", help="Original tazdata.csv file")
    parser.add_argument("output_tazdata",   help="Output tazdata.csv file with modified parking costs")
    args = parser.parse_args()
    logging.debug(args)

    # Read the information corresponding TAZs to GG / GG+TRAs
    taz_GG_TRA_df = pandas.read_csv(TAZ_GG_TRA_FILE)
    logging.info("Read {} lines from {}\n{}".format(
                 len(taz_GG_TRA_df), TAZ_GG_TRA_FILE, taz_GG_TRA_df.head()))

    # Read the tazdata inputs
    tazdata_df = pandas.read_csv(args.original_tazdata)
    tazdata_cols = tazdata_df.columns.values
    logging.info("Read {} lines from {}; head:\n{} columns={}".format(
                 len(tazdata_df), args.original_tazdata, tazdata_df.head(), tazdata_cols))

    # Join tazdata to taz_GG_TRA to determine which TAZs are affected
    tazdata_df = pandas.merge(
        left    =tazdata_df,
        right   =taz_GG_TRA_df,
        how     ="left",
        left_on =["ZONE"],
        right_on=["TAZ1454"],
        validate='one_to_one')
    logging.info("tazdata_df(len={}).head:\n{}".format(len(tazdata_df), tazdata_df.head()))

    # base or strategy: apply BASE_PARKING_MIN_COST to TAZs in GG (determined by threshold)
    logging.info("Applying minimum parking price of {} to GG".format(BASE_PARKING_MIN_COST))
    tazdata_df.loc[ (tazdata_df.pct_area_within_GGnonPPA >= PCT_AREA_THRESHOLD)&(tazdata_df[ "PRKCST"]<BASE_PARKING_MIN_COST),  "PRKCST"] = BASE_PARKING_MIN_COST
    tazdata_df.loc[ (tazdata_df.pct_area_within_GGnonPPA >= PCT_AREA_THRESHOLD)&(tazdata_df["OPRKCST"]<BASE_PARKING_MIN_COST), "OPRKCST"] = BASE_PARKING_MIN_COST

    # strategy only: apply STRATEGY_PARKING_INCREASE to TAZs in GG+TRA (determined by threshold)
    logging.info("Applying strategy parking increase of {}".format(STRATEGY_PARKING_INCREASE))
    tazdata_df.loc[ tazdata_df.pct_area_within_GGnonPPA_TRA >= PCT_AREA_THRESHOLD,  "PRKCST"] = tazdata_df[ "PRKCST"]*STRATEGY_PARKING_INCREASE
    tazdata_df.loc[ tazdata_df.pct_area_within_GGnonPPA_TRA >= PCT_AREA_THRESHOLD, "OPRKCST"] = tazdata_df["OPRKCST"]*STRATEGY_PARKING_INCREASE

    # output full version for debug
    debug_file = args.output_tazdata.replace(".csv", ".debug.csv")
    tazdata_df.to_csv(debug_file, index=False)
    logging.info("Wrote debug output to {}".format(debug_file))

    # output file with original tazdata columns
    tazdata_df.to_csv(args.output_tazdata, columns=tazdata_cols, index=False)
    logging.info("Wrote tazdata with updated parking pricing to {}".format(args.output_tazdata))
