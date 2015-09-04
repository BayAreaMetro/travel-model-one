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

# Open each of the skims (file names are defined in settings.yaml)
@orca.injectable()
def am_hwy_skim_matrix(settings):
	return omx_file(os.path.join(settings['work_dir'], settings['skim_dir'], settings['am_hwy_skim_file_name']))

@orca.injectable()
def am_trn_skim_matrix(settings):
	return omx_file(os.path.join(settings['work_dir'], settings['skim_dir'], settings['am_trn_skim_file_name']))

@orca.injectable()
def nonmot_skim_matrix(settings):
	return omx_file(os.path.join(settings['work_dir'], settings['skim_dir'], settings['nonmot_skim_file_name']))

# Read table methods
@orca.injectable()
def am_sov_dist(am_hwy_skim_matrix):
	return skim.Skim(am_hwy_skim_matrix['DISTDA'], offset = -1)

@orca.injectable()
def am_sov_time(am_hwy_skim_matrix):
	return skim.Skim(am_hwy_skim_matrix['TIMEDA'], offset = -1)

@orca.injectable()
def am_sov_bridge(am_hwy_skim_matrix):
	return skim.Skim(am_hwy_skim_matrix['BTOLLDA'], offset = -1)

@orca.injectable()
def am_trn_ivt(am_trn_skim_matrix):
	return skim.Skim(am_trn_skim_matrix['ivt'], offset = -1)

@orca.injectable()
def am_trn_wait(am_trn_skim_matrix):
	return skim.Skim(am_trn_skim_matrix['wait'], offset = -1)

@orca.injectable()
def am_trn_fare(am_trn_skim_matrix):
	return skim.Skim(am_trn_skim_matrix['fare'], offset = -1)

@orca.injectable()
def walk_dist(nonmot_skim_matrix):
	return skim.Skim(nonmot_skim_matrix['DISTWALK'], offset = -1)

@orca.injectable()
def bike_dist(nonmot_skim_matrix):
	return skim.Skim(nonmot_skim_matrix['DISTBIKE'], offset = -1)

# Build the skims object
@orca.injectable()
def skims():
	skims = skim.Skims()
	skims['am_sov_dist']   = orca.get_injectable('am_sov_dist')
	skims['am_sov_time']   = orca.get_injectable('am_sov_time')
	skims['am_sov_bridge'] = orca.get_injectable('am_sov_bridge')
	skims['am_trn_ivt']    = orca.get_injectable('am_trn_ivt')
	skims['am_trn_wait']   = orca.get_injectable('am_trn_wait')
	skims['am_trn_fare']   = orca.get_injectable('am_trn_fare')
	skims['walk_dist']     = orca.get_injectable('walk_dist')
	skims['bike_dist']     = orca.get_injectable('bike_dist')
	return skims

