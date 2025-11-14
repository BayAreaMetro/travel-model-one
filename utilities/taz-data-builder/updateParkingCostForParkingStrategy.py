USAGE = r"""

  Updates parking cost per parking strategy

  See PBA50 Tasks: 
    En9 - Expand Transportation Demand Management Initiatives (https://app.asana.com/0/403262763383022/1188775845203320/f)
    Develop regional parking policy model inputs (https://app.asana.com/0/0/1191058546872345/f)
  And PBA50+ Tasks:
    T5 parking pricing (https://app.asana.com/0/0/1206396214159345/f)
    Update 'TAZ_intersect_GG_TRA.xlsx" for parking strategies (https://app.asana.com/0/1204085012544660/1206586796423943/f)
    Final Blueprint: https://app.asana.com/0/1204959680579890/1208629862862979
    EIR Alt 2 - use TOC-based parking pricing input: https://app.asana.com/1/11860278793487/project/1203667963226596/task/1210228686240804?focus=true

  https://github.com/BayAreaMetro/modeling-website/wiki/TazData

"""

import argparse, logging, os, sys
import pandas

LOG_FILE                  = "updateParkingCostForParkingStrategy.log"
# for Blueprint
TAZ_GG_TRA_FILE           = "M:\\Application\\Model One\\RTP2025\\INPUT_DEVELOPMENT\\parking_strategy\\taz1454_GGnonPPA_TRA_crosswalk_FBP.csv"
# for EIR Alt2 (focused landuse in TOC)
TAZ_GG_TOC_FILE           = "M:\\Application\\Model One\\RTP2025\\INPUT_DEVELOPMENT\\parking_strategy\\taz1454_GGnonPPA_TOC_crosswalk_EIR2.csv"
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
    # parser.add_argument("scenario", choices=["FBP","EIR_Alt2"], default="FBP")
    parser.add_argument("scenario", default="FBP")
    args = parser.parse_args()
    logging.debug(args)

    if args.scenario == "FBP":
       TAZ_GG_FILE = TAZ_GG_TRA_FILE
       PCT_WITHIN_STRAT_MULT_COL = "pct_area_within_GGnonPPA_TRA"
    elif args.scenario == "EIR_Alt2":
       TAZ_GG_FILE = TAZ_GG_TOC_FILE
       PCT_WITHIN_STRAT_MULT_COL = "pct_area_within_GGnonPPA_TOC"
    else:
      #  raise Exception(f"scenario {args.scenario} not supported")
      logging.warning(f"Scenario {args.scenario} not supported, parking cost update will not be applied")
    
    # Read the tazdata inputs
    tazdata_df = pandas.read_csv(args.original_tazdata)
    tazdata_cols = tazdata_df.columns.values
    logging.info(f"Read { len(tazdata_df):,} lines from {args.original_tazdata}; head:\n{tazdata_df.head()} columns={tazdata_cols}")
    
    if args.scenario in ["FBP","EIR_Alt2"]:

      # Read the information corresponding TAZs to GG / GG+TRAs or GG+TOCs
      taz_GG_df = pandas.read_csv(TAZ_GG_FILE)
      logging.info(f"Read {len(taz_GG_df):,} lines from {TAZ_GG_FILE}\n{taz_GG_df.head()}")

      # Join tazdata to taz_GG_TRA to determine which TAZs are affected
      tazdata_df = pandas.merge(
          left    =tazdata_df,
          right   =taz_GG_df,
          how     ="left",
          left_on =["ZONE"],
          right_on=["TAZ1454"],
          validate='one_to_one')
      logging.info(f"tazdata_df(len={len(tazdata_df)}).head:\n{tazdata_df.head()}")

      # base or strategy: apply BASE_PARKING_MIN_COST to TAZs in GG (determined by threshold)
      logging.info(f"Applying minimum parking price of {BASE_PARKING_MIN_COST} to GG")
      tazdata_df.loc[ (tazdata_df.pct_area_within_GGnonPPA >= PCT_AREA_THRESHOLD)&(tazdata_df[ "PRKCST"]<BASE_PARKING_MIN_COST),  "PRKCST"] = BASE_PARKING_MIN_COST
      tazdata_df.loc[ (tazdata_df.pct_area_within_GGnonPPA >= PCT_AREA_THRESHOLD)&(tazdata_df["OPRKCST"]<BASE_PARKING_MIN_COST), "OPRKCST"] = BASE_PARKING_MIN_COST

      # strategy only: apply STRATEGY_PARKING_INCREASE to TAZs in GG+TRA (determined by threshold)
      logging.info(f"Applying strategy parking increase of {STRATEGY_PARKING_INCREASE} to {PCT_WITHIN_STRAT_MULT_COL}")
      tazdata_df.loc[ tazdata_df[PCT_WITHIN_STRAT_MULT_COL] >= PCT_AREA_THRESHOLD,  "PRKCST"] = tazdata_df[ "PRKCST"]*STRATEGY_PARKING_INCREASE
      tazdata_df.loc[ tazdata_df[PCT_WITHIN_STRAT_MULT_COL] >= PCT_AREA_THRESHOLD, "OPRKCST"] = tazdata_df["OPRKCST"]*STRATEGY_PARKING_INCREASE

      # output full version for debug
      debug_file = args.output_tazdata.replace(".csv", ".debug.csv")
      tazdata_df.to_csv(debug_file, index=False)
      logging.info("Wrote debug output to {}".format(debug_file))

    # output file with original tazdata columns
    tazdata_df.to_csv(args.output_tazdata, columns=tazdata_cols, index=False)
    logging.info("Wrote tazdata with updated parking pricing to {}".format(args.output_tazdata))
