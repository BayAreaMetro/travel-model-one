USAGE = r"""
  Creates single accessibility values for each subzone, to be applied to parcels in the land use model, using the following steps:
  (1) Calculate the "relative" logsum of each subzone by subtracting the minimum subzone raw logsum value, and then scale
      the logsums using the same parameters used in TM1.5 (0.0134 for mandatory, 0.0175 for non-mandatory).
  (2) Calculate a weighted mandatory and non-mandatory logsum for each subzone using the person shares of accessibility markets.
  (3) Combine mandatory and non-mandatory logsums to create a combination logsum.
  (4) Adjust the combination logsum values downward to keep the values in line with the values used to estimate the BAUS housing 
      price model after TM1 logsum methodology changes.

  Also creates taz-level logsum values specifically for visualizing travel model logsums. The same steps are used as above, after 
  the median of of the subzone raw logsums is assigned as the TAZ raw logsum. 

  Assumes script is being run from within model run directory.

  Input files:
  1) core_summaries/AccessibilityMarkets.csv
  2) logsums/mandatoryAccessibilities.csv
  3) logsums/nonMandatoryAccessibilities.csv

  Output files:
  1) logsums/subzone_logsums_for_BAUS.csv
  2) logsums/taz_logsums_for_BAUS.csv
"""

import argparse, os, pathlib
import pandas as pd

# see c_ivt in ModeChoice.xls
# note these are actually negative but we don't need that here
IN_VEHICLE_TIME_COEFF_MANDATORY    = 0.01340
IN_VEHICLE_TIME_COEFF_NONMANDATORY = 0.01750

# MAGIc NUMBERS - related to "adjusting the values to keep them in line with the values used to estimate the BAUS
# housing price model after TM1 logsum methodology changes"
# TODO: Re-evaluate this scaling methodology
MAGIC_NUMBER_SUBTRACT     = 170
MAGIC_NUMBER_NEGATIVE_SET = 1


if __name__ == '__main__':
  pd.set_option('display.width', 500)

  parser = argparse.ArgumentParser(
    description = USAGE,
    formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('--rtp',    type=str, choices=['RTP2021','RTP2025'], default='RTP2025')
  parser.add_argument('--suffix', type=str, default='', help="options input/output file suffix")
  my_args = parser.parse_args()
  print(my_args)

  # read the existing logsum files using the model run year
  CORE_SUMMARIES_DIR  = pathlib.Path("core_summaries")
  LOGSUMS_DIR         = pathlib.Path("logsums")

  if my_args.rtp == 'RTP2021':
    CORE_SUMMARIES_DIR  = pathlib.Path(".")
    LOGSUMS_DIR         = pathlib.Path(".")

  markets_df      = pd.read_csv(CORE_SUMMARIES_DIR / f"AccessibilityMarkets{my_args.suffix}.csv")
  mandatory_df    = pd.read_csv(LOGSUMS_DIR / f"mandatoryAccessibilities{my_args.suffix}.csv")
  nonmandatory_df = pd.read_csv(LOGSUMS_DIR / f"nonMandatoryAccessibilities{my_args.suffix}.csv")

  # label markets so they match the accessibility columns
  print("markets_df:\n{}".format(markets_df))
  markets_df['AV'] = markets_df['hasAV'].apply(lambda x: 'AV' if x == 1 else 'noAV')
  markets_df['label'] = (markets_df['incQ_label'] + '_' + markets_df['autoSuff_label'] + '_' + markets_df['AV'])
  # label includes incQ, autos vs workers, AV. e.g., lowInc_autos_ge_workers_AV
  markets_df = markets_df.groupby('label').agg({'num_persons':'sum'})
  # then apply person weights to markets
  markets_df['person_share'] = markets_df['num_persons'] / markets_df['num_persons'].sum()
  print("markets_df:\n{}".format(markets_df))
  market_segments = markets_df.index.to_list()
  print(market_segments)

  # TODO: I'm not sure why the median version would be used here or the value of this in general
  # TODO: For visualization, I think looking at the logsums for each subzone would suffice.
  # repeat the process with TAZ-levels summaries
  taz_mandatory_df    = mandatory_df.groupby('taz').median().reset_index(drop=False)
  taz_nonmandatory_df = nonmandatory_df.groupby('taz').median().reset_index(drop=False)

  # weight mandatory and non-mandatory logsums by markets
  # mandatory
  for market_segment in market_segments:
    print("  Processing market_segment = {}; person_share={}".format(market_segment, markets_df.loc[market_segment, 'person_share']))

    # calculate the relative logsum and scale by the travel model parameter
    mandatory_df[f'{market_segment} scaled']    = \
      ((mandatory_df[market_segment] - mandatory_df[market_segment].min()) / 
       IN_VEHICLE_TIME_COEFF_MANDATORY) * markets_df.loc[market_segment, 'person_share']
    nonmandatory_df[f'{market_segment} scaled'] = \
      ((nonmandatory_df[market_segment] - nonmandatory_df[market_segment].min()) / 
        IN_VEHICLE_TIME_COEFF_NONMANDATORY) * markets_df.loc[market_segment, 'person_share']

    taz_mandatory_df[f'{market_segment} scaled']    = \
      ((taz_mandatory_df[market_segment] - taz_mandatory_df[market_segment].min()) / 
       IN_VEHICLE_TIME_COEFF_MANDATORY) * markets_df.loc[market_segment, 'person_share']
    taz_nonmandatory_df[f'{market_segment} scaled'] = \
      ((taz_nonmandatory_df[market_segment] - taz_nonmandatory_df[market_segment].min()) / 
        IN_VEHICLE_TIME_COEFF_NONMANDATORY) * markets_df.loc[market_segment, 'person_share']    
    
  # sum the scaled logsums weighted by person shares
  market_segments_scaled = [f'{ms} scaled' for ms in market_segments]
  mandatory_df['mandatory_logsum']       = mandatory_df[market_segments_scaled].sum(axis='columns')
  nonmandatory_df['nonmandatory_logsum'] = nonmandatory_df[market_segments_scaled].sum(axis='columns')

  taz_mandatory_df['mandatory_logsum']       = taz_mandatory_df[market_segments_scaled].sum(axis='columns')
  taz_nonmandatory_df['nonmandatory_logsum'] = taz_nonmandatory_df[market_segments_scaled].sum(axis='columns')

  # select just these and join
  mand_nonmand_df = pd.merge(
    left      = mandatory_df[['taz','subzone','destChoiceAlt','mandatory_logsum']],
    right     = nonmandatory_df[['taz','subzone','destChoiceAlt','nonmandatory_logsum']],
    on        = ['taz','subzone','destChoiceAlt'],
    how       = 'outer',
    indicator = True,
    validate = 'one_to_one',
  )
  merge_check = mand_nonmand_df['_merge'].value_counts()
  print(merge_check)
  assert(merge_check['left_only']==0)
  assert(merge_check['right_only']==0)

  # select just these and join -- taz version
  taz_mand_nonmand_df = pd.merge(
    left      = taz_mandatory_df[['taz','mandatory_logsum']],
    right     = taz_nonmandatory_df[['taz','nonmandatory_logsum']],
    on        = ['taz'],
    how       = 'outer',
    indicator = True,
    validate = 'one_to_one',
  )
  merge_check = taz_mand_nonmand_df['_merge'].value_counts()
  print(merge_check)
  assert(merge_check['left_only']==0)
  assert(merge_check['right_only']==0)

  # combine mandatory and non-mandatory TAZ columns to create the combo_logsum 
  mand_nonmand_df["combo_logsum_prescale"] = mand_nonmand_df.mandatory_logsum + mand_nonmand_df.nonmandatory_logsum
  # shift the values to align with the values from the logsum methodology used in BAUS estimation
  mand_nonmand_df["combo_logsum"] = mand_nonmand_df["combo_logsum_prescale"] - MAGIC_NUMBER_SUBTRACT
  mand_nonmand_df.loc[(mand_nonmand_df["combo_logsum"] <= 0), "combo_logsum"] = MAGIC_NUMBER_NEGATIVE_SET

  # taz version
  taz_mand_nonmand_df["combo_logsum_prescale"] = taz_mand_nonmand_df.mandatory_logsum + taz_mand_nonmand_df.nonmandatory_logsum
  # shift the values to align with the values from the logsum methodology used in BAUS estimation
  taz_mand_nonmand_df["combo_logsum"] = taz_mand_nonmand_df["combo_logsum_prescale"] - MAGIC_NUMBER_SUBTRACT
  taz_mand_nonmand_df.loc[(taz_mand_nonmand_df["combo_logsum"] <= 0), "combo_logsum"] = MAGIC_NUMBER_NEGATIVE_SET

  # record subzone to letter version that BAUS uses
  mand_nonmand_df['subzone_letter'] = mand_nonmand_df.subzone.map( {0:'c', 1:'a', 2:'b'})
  mand_nonmand_df['taz_subzone'] = mand_nonmand_df.taz.astype('str') + mand_nonmand_df.subzone_letter
  print("mand_nonmand_df:\n{}".format(mand_nonmand_df))

  # write subzone logsums to file
  mand_nonmand_df = mand_nonmand_df[['taz', 'taz_subzone', 'mandatory_logsum', 'nonmandatory_logsum', 'combo_logsum_prescale', 'combo_logsum']]
  mand_nonmand_df.to_csv(LOGSUMS_DIR / f"subzone_logsums_for_BAUS{my_args.suffix}.csv", index=False)
  print("Wrote {}".format(LOGSUMS_DIR / f"subzone_logsums_for_BAUS{my_args.suffix}.csv"))
  
  # write taz logsums to file
  taz_mand_nonmand_df = taz_mand_nonmand_df[['taz', 'mandatory_logsum', 'nonmandatory_logsum', 'combo_logsum_prescale', 'combo_logsum']]
  taz_mand_nonmand_df.to_csv(LOGSUMS_DIR / f"taz_logsums_for_BAUS{my_args.suffix}.csv", index=False)
  print("Wrote {}".format(LOGSUMS_DIR / f"taz_logsums_for_BAUS{my_args.suffix}.csv"))
  