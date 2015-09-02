import os
import openmatrix as omx
import orca
from activitysim import skim

""" 
Configure the skim injectables
"""

# Method to open omx files
@orca.injectable()
def omx_file(file_name_with_path):
	return(omx.openFile(file_name_with_path))

# Open each of the skims (file names are defined in the notebook)
@orca.injectable()
def am_hwy_skim_matrix(am_hwy_skim_file_name):
	return omx_file(am_hwy_skim_file_name)

@orca.injectable()
def am_trn_skim_matrix(am_trn_skim_file_name):
	return omx_file(am_trn_skim_file_name)

# Read table methods
@orca.injectable()
def am_hwy_sov_dist(am_hwy_skim_matrix):
	return skim.Skim(am_hwy_skim_matrix['DISTDA'], offset = -1)

@orca.injectable()
def am_hwy_sov_time(am_hwy_skim_matrix):
	return skim.Skim(am_hwy_skim_matrix['TIMEDA'], offset = -1)

@orca.injectable()
def am_trn_ivt(am_trn_skim_matrix):
	return skim.Skim(am_trn_skim_matrix['ivt'], offset = -1)

@orca.injectable()
def am_trn_iwait(am_trn_skim_matrix):
	return skim.Skim(am_trn_skim_matrix['iwait'], offset = -1)

# Build the skims object
@orca.injectable()
def skims():
	skims = skim.Skims()
	skims['am_hwy_sov_dist'] = orca.get_injectable('am_hwy_sov_dist')
	skims['am_hwy_sov_time'] = orca.get_injectable('am_hwy_sov_time')
	skims['am_trn_ivt']      = orca.get_injectable('am_trn_ivt')
	skims['am_trn_iwait']    = orca.get_injectable('am_trn_iwait')
	return skims

