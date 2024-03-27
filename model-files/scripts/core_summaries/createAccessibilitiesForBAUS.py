USAGE = r"""
  Creates single logsum values for each subzone, to be applied to parcels in the land use model,l using the following steps:
  (1) Calculate the "relative" logsum of each subzone by subtracting the minimum subzone raw logsum value, and then scale
      the logsums using the same parameters used in TM1.5 (0.0134 for mandatory, 0.0175 for non-mandatory).
  (2) Calculate a weighted mandatory and non-mandatory logsum for each subzone using the person shares of accessibility markets.
  (3) Combine mandatory and non-mandatory logsums to create a combination logsum.
  (4) Adjust the combination logsum values downward to keep the values in line with the values used to estimate the BAUS housing 
      price model after TM1 logsum methodology changes.

  Also creates taz-level logsum values specifically for visualizing travel model logsums. The same steps are used as above, after 
  the median of of the subzone raw logsums is assigned as the TAZ raw logsum. 
"""

import os
import pandas as pd


if __name__ == '__main__':

  # run this script in the existing logsum file location with a hard coded year 
  # todo: update input path variable and model_year arg using travel model run setup
  IN_DIR = os.getcwd()
  model_year = 2050 

  # create output subdir in the existing logsum file location, if needed
  OUT_DIR = "combo_logsums"
  if not os.path.exists(OUT_DIR):
    os.mkdir(OUT_DIR)

  # read the existing logsum files using the model run year
  markets_df = pd.read_csv(os.path.join(IN_DIR, "AccessibilityMarkets_%d.csv" % model_year))
  mand_df = pd.read_csv(os.path.join(IN_DIR, "mandatoryAccessibilities_%d.csv" % model_year))
  nonmand_df = pd.read_csv(os.path.join(IN_DIR, "nonMandatoryAccessibilities_%d.csv" % model_year))

  # label markets so they match the accessibility columns
  markets_df['AV'] = markets_df['hasAV'].apply(lambda x: 'AV' if x == 1 else 'noAV')
  markets_df['label'] = (markets_df['incQ_label'] + '_' + markets_df['autoSuff_label'] + '_' + markets_df['AV'])
  markets_df = markets_df.groupby('label').sum()
  # then apply person weights to markets
  markets_df['prop'] = markets_df['num_persons'] / markets_df['num_persons'].sum()
  markets_df = markets_df[['prop']].transpose().reset_index(drop=True)

  # create a subzone table by concatenating taz and subzone
  subzone_df = mand_df.copy()
  subzone_df.loc[subzone_df.subzone == 0, 'subzone'] = 'c'  
  subzone_df.loc[subzone_df.subzone == 1, 'subzone'] = 'a'  
  subzone_df.loc[subzone_df.subzone == 2, 'subzone'] = 'b'  
  subzone_df['taz_subzone'] = subzone_df.taz.astype('str') + subzone_df.subzone

  # weight mandatory and non-mandatory logsums by markets
  # mandatory
  mand = mand_df.copy()
  cols_to_sum = []
  for col in mand.columns[~mand.columns.isin(['destChoiceAlt', 'taz', 'subzone', 'weighted_sum'])]:
    if col in markets_df.columns:
      # calculate the relative logsum and scale by the travel model parameter
      mand[col] = ((mand[col] - mand[col].min()) / .0134) * markets_df.loc[0, col]
      cols_to_sum.append(col)
  subzone_df["mandatory_logsum"] = mand[cols_to_sum].sum(axis=1)
  # non-mandatory
  nonmand = nonmand_df.copy()
  cols_to_sum = []
  for col in nonmand.columns[~nonmand.columns.isin(['destChoiceAlt', 'taz', 'subzone', 'weighted_sum'])]:
    if col in markets_df.columns:
      # calculate the relative logsum and scale by the travel model parameter
      nonmand[col] = ((nonmand[col] - nonmand[col].min()) / .0175) * markets_df.loc[0, col]
      cols_to_sum.append(col)
  subzone_df["nonmandatory_logsum"] = nonmand[cols_to_sum].sum(axis=1)

  # combine mandatory and non-mandatory TAZ columns to create the combo_logsum 
  subzone_df["combo_logsum"] = subzone_df.mandatory_logsum + subzone_df.nonmandatory_logsum
  # shift the values to align with the values from the logsum methodology used in BAUS estimation
  subzone_df["combo_logsum"] = subzone_df["combo_logsum"] - 170
  subzone_df["combo_logsum"].loc[(subzone_df["combo_logsum"] <= 0)] = 1

  # write subzone logsums to file
  subzone_df = subzone_df[['taz', 'taz_subzone', 'mandatory_logsum', 'nonmandatory_logsum', 'combo_logsum']]
  subzone_df.to_csv(os.path.join(OUT_DIR, "subzone_logsums_%d.csv") % model_year)
  
  # repeat the process with TAZ-levels summaries
  mand_taz_df = mand_df.groupby('taz').median()
  nonmand_taz_df = nonmand_df.groupby('taz').median()

  taz_df = mand_taz_df.copy()

  # weight mandatory and non-mandatory logsums by markets
  # mandatory
  cols_to_sum = []
  for col in mand_taz_df.columns[~mand_taz_df.columns.isin(['destChoiceAlt', 'taz', 'subzone', 'weighted_sum'])]:
    if col in markets_df.columns:
      # calculate the relative logsum and scale by the travel model parameter
      mand_taz_df[col] = ((mand_taz_df[col] - mand_taz_df[col].min()) / .0134) * markets_df.loc[0, col]
      cols_to_sum.append(col)
  taz_df["mandatory_logsum"] = mand_taz_df[cols_to_sum].sum(axis=1)
  # non-mandatory
  cols_to_sum = []
  for col in  nonmand_taz_df.columns[~ nonmand_taz_df.columns.isin(['destChoiceAlt', 'taz', 'subzone', 'weighted_sum'])]:
    if col in markets_df.columns:
      # calculate the relative logsum and scale by the travel model parameter
       nonmand_taz_df[col] = ((nonmand_taz_df[col] -  nonmand_taz_df[col].min()) / .0175) * markets_df.loc[0, col]
       cols_to_sum.append(col)
  taz_df["nonmandatory_logsum"] = nonmand_taz_df[cols_to_sum].sum(axis=1)

  # combine mandatory and non-mandatory TAZ columns to create the combo_logsum 
  taz_df["combo_logsum"] = taz_df.mandatory_logsum + taz_df.nonmandatory_logsum
  # shift the values to align with the values from the logsum methodology used in BAUS estimation
  taz_df["combo_logsum"] = taz_df["combo_logsum"] - 170
  taz_df["combo_logsum"].loc[(taz_df["combo_logsum"] <= 0)] = 1

  # write taz logsums to file
  taz_df = taz_df[['mandatory_logsum', 'nonmandatory_logsum', 'combo_logsum']]
  taz_df.to_csv(os.path.join(OUT_DIR, "taz_logsums_%d.csv") % model_year)