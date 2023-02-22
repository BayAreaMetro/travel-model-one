USAGE = r"""

This script makes some runtime configuration changes in order to try to simplify
changes that need to be made at runtime.

If no iteration is specified, then these include:
 * Project Directory
   + Assumed to be the current working directory
   + Propagated to CTRAMP\\runtime\\accessibilities.properties,
                   CTRAMP\\runtime\\mtcTourBased.properties
 * Synthesized households and persons files
   + Assumed to be INPUT\\popsyn\\hhFile.* and INPUT\\popsyn\\personFile.*
   + Propagated to CTRAMP\\runtime\\mtcTourBased.properties
 * Auto Operating Costs
   + Specify the values in INPUT\\params.properties
   + It will be propagated to CTRAMP\\scripts\\block\\hwyParam.block,
                              CTRAMP\\runtime\\accessibilities.properties (new!),
                              CTRAMP\\runtime\\mtcTourBased.properties (new!)
   + It will be propagated to CTRAMP\\model\\ModeChoice.xls,  (for costPerMile)
                              CTRAMP\\model\\TripModeChoice.xls,
                              CTRAMP\\model\\accessibility_utility.xls
 * Truck Operating Cost
   + Specify the value in INPUT\\params.properties
   + It will be propagated to CTRAMP\\scripts\\block\\hwyParam.block
 * Truck Trip Distribution gravity LOS term part from tolled time
   + Specify the value in INPUT\\params.properties
   + It will be propagated to CTRAMP\\scripts\\block\\hwyParam.block
 * Telecommute constant
   + It will be propagated to CTRAMP\\model\\CoordinatedDailyActivityPattern.xls
 * Means Based Tolling (Q1 and Q2) factors
   + They will be propagated to CTRAMP\\scripts\\block\\hwyParam.block
                                CTRAMP\\runtime\\mtcTourBased.properties
 * Means Based Fare (Q1 and Q2) factors
   + They will be propagated to CTRAMP\\scripts\\block\\trnParam.block
                                CTRAMP\\runtime\\mtcTourBased.properties
 * HSR Interregional trips disable flag
   + It will be propagated to CTRAMP\\scripts\\block\\trnParam.block
 * Host IP - where the household manager, matrix manager and JPPF Server run
   + Assumed to be the HOST_IP_ADDRESS in the environment
   + Assumed that this script is running on this host IP (this is verified)
   + It will be propagated to CTRAMP\\runtime\\JavaOnly_runMain.cmd
                              CTRAMP\\runtime\\JavaOnly_runNode[0-4].cmd
                              CTRAMP\\runtime\\config\\jppf-clientDistributed.properties
                              CTRAMP\\runtime\\config\\jppf-clientLocal.properties
                              CTRAMP\\runtime\\config\\jppf-driver.properties
                              CTRAMP\\runtime\\config\\jppf-node[0-4].properties
                              CTRAMP\\runtime\\mtcTourBased.properties
 * Distribution
   + Based on hostname.
     * 'MODEL2-A', 'MODEL2-C','MODEL2-D','PORMDLPPW01','PORMDLPPW02','Model3-a','Model3-b': single machine setup with
        48 Cube Voyager processes available
        48 threads for accessibilities
        24 threads for core
     * 'mainmodel': multiple machine setup

If an iteration is specified, then the following UsualWorkAndSchoolLocationChoice
lines are set in CTRAMP\\runtime\\mtcTourBased.properties:

  Iteration 1:
    # ShadowPrice.Input.File          = (blank)
    ShadowPricing.MaximumIterations = 4
  Iteration 2:
    ShadowPrice.Input.File          = main/ShadowPricing_3.csv
    ShadowPricing.MaximumIterations = 2
  Iteration 3:
    ShadowPrice.Input.File          = main/ShadowPricing_5.csv
    ShadowPricing.MaximumIterations = 2
  Iteration n:
    ShadowPrice.Input.File          = main/ShadowPricing_2n-1.csv
    ShadowPricing.MaximumIterations = 2
  logsums: same as Iteration 3
"""

import argparse
import collections
import glob
import os
import re
import shutil
import socket
import sys

import xlrd
import xlwt
import xlutils.copy

def replace_in_file(filepath, regex_dict):
    """
    Copies `filepath` to `filepath.original`
    Opens `filepath.original` and reads it, writing a new version to `filepath`.
    The new version is the same as the old, except that the regexes in the regex_dict keys
    are replaced by the corresponding values.
    """
    shutil.move(filepath, "%s.original" % filepath)
    print("Updating {}".format(filepath))

    # read the contents
    myfile = open("%s.original" % filepath, 'r')
    file_contents = myfile.read()
    myfile.close()

    # do the regex subs
    for pattern,newstr in regex_dict.items():
        (file_contents, numsubs) = re.subn(pattern,newstr,file_contents,flags=re.IGNORECASE)
        print("  Made {} sub for {}".format(numsubs, newstr))
        # Fail on failure
        if numsubs < 1:
            print("  SUBSITUTION NOT MADE -- Fatal error")
            print("  pattern = [{}]".format(pattern))
            sys.exit(2)

    # write the result
    myfile = open(filepath, 'w')
    myfile.write(file_contents)
    myfile.close()

def append_to_file(filepath, append_str):
    """
    Copies `filepath` to `filepath.original`
    Opens `filepath.original` and reads it, writing a new version to `filepath`.
    The new version is the same as the old, with the lines in append_dict added
    """
    shutil.move(filepath, "%s.original" % filepath)
    print("Updating {}".format(filepath))

    # read the contents
    myfile = open("%s.original" % filepath, 'r')
    file_contents = myfile.read()
    myfile.close()

    # write the result
    myfile = open(filepath, 'w')
    myfile.write(file_contents)
    myfile.write(append_str)
    myfile.close()

def config_project_dir(for_logsums, replacements):
    """
    See USAGE for details.

    Replacements = { filepath -> regex_dict }
    """
    project_dir = os.getcwd()
    project_dir = project_dir.replace("\\","/") # we want backwards slashes
    project_dir = project_dir + "/"             # trailing backwards slash

    filepath    = os.path.join("CTRAMP","runtime","accessibilities.properties")
    replacements[filepath] = collections.OrderedDict()
    # Simple regex: .  = any character not a newline
    #               \S = non-whitespace character
    replacements[filepath]["(\nProject.Directory[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % project_dir

    filepath    = os.path.join("CTRAMP","runtime","mtcTourBased.properties")
    if for_logsums:
        filepath    = os.path.join("CTRAMP","runtime","logsums.properties")
    replacements[filepath]["(\nProject.Directory[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % project_dir

def config_popsyn_files(replacements):
    """
    See USAGE for details.

    Replacements = { filepath -> regex_dict }
    """
    hhfiles   = glob.glob( os.path.join("INPUT", "popsyn", "hhFile.*") )
    # there should be only one
    assert(len(hhfiles) == 1)
    hhfile   = hhfiles[0]
    hhfile   = hhfile.replace("\\","/")     # we want backwards slashes
    hhfile   = hhfile.replace("INPUT/","")  # strip input

    perfiles = glob.glob( os.path.join("INPUT", "popsyn", "personFile.*") )
    assert(len(perfiles) == 1)
    perfile  = perfiles[0]
    perfile  = perfile.replace("\\","/")     # we want backwards slashes
    perfile  = perfile.replace("INPUT/", "") # strip input

    filepath = os.path.join("CTRAMP","runtime","mtcTourBased.properties")
    replacements[filepath]["(\nPopulationSynthesizer.InputToCTRAMP.HouseholdFile[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % hhfile
    replacements[filepath]["(\nPopulationSynthesizer.InputToCTRAMP.PersonFile[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % perfile

def config_mobility_params(params_filename, params_contents, for_logsums, replacements):
    """
    See USAGE for details.

    Replacements = { filepath -> regex_dict }
    """
    # get parameters - see examples in congig directory

    modelYear = int(os.environ["MODEL_YEAR"])

    BikeInfra_CIVT_Mult      = float(get_property(params_filename, params_contents, "Bike_Infra_C_IVT_Multiplier"))

    SharingPrefFactor        = float(get_property(params_filename, params_contents, "Sharing_Preferences_factor"))

    MeansBasedTollsQ1Factor  = float(get_property(params_filename, params_contents, "Means_Based_Tolling_Q1Factor"))
    MeansBasedTollsQ2Factor  = float(get_property(params_filename, params_contents, "Means_Based_Tolling_Q2Factor"))
    MeansBasedFareQ1Factor   = float(get_property(params_filename, params_contents, "Means_Based_Fare_Q1Factor"))
    MeansBasedFareQ2Factor   = float(get_property(params_filename, params_contents, "Means_Based_Fare_Q2Factor"))

    # cordon
    MeansBasedCordonTollsQ1Factor  = float(get_property(params_filename, params_contents, "Means_Based_Cordon_Tolling_Q1Factor"))
    MeansBasedCordonTollsQ2Factor  = float(get_property(params_filename, params_contents, "Means_Based_Cordon_Tolling_Q2Factor"))
    MeansBasedCordonFareQ1Factor   = float(get_property(params_filename, params_contents, "Means_Based_Cordon_Fare_Q1Factor"))
    MeansBasedCordonFareQ2Factor   = float(get_property(params_filename, params_contents, "Means_Based_Cordon_Fare_Q2Factor"))

    Adjust_TNCsingle_TourMode = float(get_property(params_filename, params_contents, "Adjust_TNCsingle_TourMode"))
    Adjust_TNCshared_TourMode = float(get_property(params_filename, params_contents, "Adjust_TNCshared_TourMode"))
    Adjust_TNCsingle_TripMode = float(get_property(params_filename, params_contents, "Adjust_TNCsingle_TripMode"))
    Adjust_TNCshared_TripMode = float(get_property(params_filename, params_contents, "Adjust_TNCshared_TripMode"))

    avShare                   = float(get_property(params_filename, params_contents, "Mobility.AV.Share"))
    pBoostAutosLTDrivers      = float(get_property(params_filename, params_contents, "Mobility.AV.ProbabilityBoost.AutosLTDrivers"))
    pBoostAutosGEDrivers      = float(get_property(params_filename, params_contents, "Mobility.AV.ProbabilityBoost.AutosGEDrivers"))
    avIVTFactor               = float(get_property(params_filename, params_contents, "Mobility.AV.IVTFactor"))
    avparkCostFactor          = float(get_property(params_filename, params_contents, "Mobility.AV.ParkingCostFactor"))
    avCPMFactor               = float(get_property(params_filename, params_contents, "Mobility.AV.CostPerMileFactor"))
    avTermTimeFactor          = float(get_property(params_filename, params_contents, "Mobility.AV.TerminalTimeFactor"))
    tncIVTFactor              = float(get_property(params_filename, params_contents, "Mobility.TNC.shared.IVTFactor"))

    taxiBaseFare              = float(get_property(params_filename, params_contents, "taxi.baseFare"))
    taxiCPMile                = float(get_property(params_filename, params_contents, "taxi.costPerMile"))
    taxiCPMin                 = float(get_property(params_filename, params_contents, "taxi.costPerMinute"))

    tncSingleBaseFare         = float(get_property(params_filename, params_contents, "TNC.single.baseFare"))
    tncSingleCPMile           = float(get_property(params_filename, params_contents, "TNC.single.costPerMile"))
    tncSingleCPMin            = float(get_property(params_filename, params_contents, "TNC.single.costPerMinute"))
    tncSingleMinCost          = float(get_property(params_filename, params_contents, "TNC.single.costMinimum"))

    tncSharedBaseFare         = float(get_property(params_filename, params_contents, "TNC.shared.baseFare"))
    tncSharedCPMile           = float(get_property(params_filename, params_contents, "TNC.shared.costPerMile"))
    tncSharedCPMin            = float(get_property(params_filename, params_contents, "TNC.shared.costPerMinute"))
    tncSharedMinCost          = float(get_property(params_filename, params_contents, "TNC.shared.costMinimum"))

    tncSingleMeanWaitTime     = get_property(params_filename, params_contents, "TNC.single.waitTime.mean")
    tncSingleSDWaitTime       = get_property(params_filename, params_contents, "TNC.single.waitTime.sd")

    tncSharedMeanWaitTime     = get_property(params_filename, params_contents, "TNC.shared.waitTime.mean")
    tncSharedSDWaitTime       = get_property(params_filename, params_contents, "TNC.shared.waitTime.sd")

    taxiMeanWaitTime          = get_property(params_filename, params_contents, "Taxi.waitTime.mean")
    taxiSDWaitTime            = get_property(params_filename, params_contents, "Taxi.waitTime.sd")

    taxiDaShare               = float(get_property(params_filename, params_contents, "Taxi.da.share"))
    taxiS2Share               = float(get_property(params_filename, params_contents, "Taxi.s2.share"))
    taxiS3Share               = float(get_property(params_filename, params_contents, "Taxi.s3.share"))

    tncSingleDaShare          = float(get_property(params_filename, params_contents, "TNC.single.da.share"))
    tncSingleS2Share          = float(get_property(params_filename, params_contents, "TNC.single.s2.share"))
    tncSingleS3Share          = float(get_property(params_filename, params_contents, "TNC.single.s3.share"))

    tncSharedDaShare          = float(get_property(params_filename, params_contents, "TNC.shared.da.share"))
    tncSharedS2Share          = float(get_property(params_filename, params_contents, "TNC.shared.s2.share"))
    tncSharedS3Share          = float(get_property(params_filename, params_contents, "TNC.shared.s3.share"))

    # Pass the data to mtcTourBased.properties or logsums.properties
    filepath = os.path.join("CTRAMP","runtime","mtcTourBased.properties")
    if for_logsums:
        filepath = os.path.join("CTRAMP","runtime","logsums.properties")

    replacements[filepath]["(\nModel_Year[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%d" % modelYear

    replacements[filepath]["(\nBike_Infra_C_IVT_Multiplier[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % BikeInfra_CIVT_Mult

    replacements[filepath]["(\nSharing_Preferences_factor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % SharingPrefFactor

    replacements[filepath]["(\nMeans_Based_Tolling_Q1Factor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % MeansBasedTollsQ1Factor
    replacements[filepath]["(\nMeans_Based_Tolling_Q2Factor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % MeansBasedTollsQ2Factor
    replacements[filepath]["(\nMeans_Based_Fare_Q1Factor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % MeansBasedFareQ1Factor
    replacements[filepath]["(\nMeans_Based_Fare_Q2Factor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % MeansBasedFareQ2Factor

    replacements[filepath]["(\nMeans_Based_Cordon_Tolling_Q1Factor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % MeansBasedCordonTollsQ1Factor
    replacements[filepath]["(\nMeans_Based_Cordon_Tolling_Q2Factor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % MeansBasedCordonTollsQ2Factor
    replacements[filepath]["(\nMeans_Based_Cordon_Fare_Q1Factor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % MeansBasedCordonFareQ1Factor
    replacements[filepath]["(\nMeans_Based_Cordon_Fare_Q2Factor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % MeansBasedCordonFareQ2Factor

    replacements[filepath]["(\nAdjust_TNCsingle_TourMode[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % Adjust_TNCsingle_TourMode
    replacements[filepath]["(\nAdjust_TNCshared_TourMode[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % Adjust_TNCshared_TourMode
    replacements[filepath]["(\nAdjust_TNCsingle_TripMode[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % Adjust_TNCsingle_TripMode
    replacements[filepath]["(\nAdjust_TNCshared_TripMode[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % Adjust_TNCshared_TripMode

    replacements[filepath]["(\nMobility.AV.Share[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % avShare
    replacements[filepath]["(\nMobility.AV.ProbabilityBoost.AutosLTDrivers[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % pBoostAutosLTDrivers
    replacements[filepath]["(\nMobility.AV.ProbabilityBoost.AutosGEDrivers[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % pBoostAutosGEDrivers
    replacements[filepath]["(\nMobility.AV.IVTFactor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % avIVTFactor
    replacements[filepath]["(\nMobility.AV.ParkingCostFactor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % avparkCostFactor
    replacements[filepath]["(\nMobility.AV.CostPerMileFactor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % avCPMFactor
    replacements[filepath]["(\nMobility.AV.TerminalTimeFactor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % avTermTimeFactor
    replacements[filepath]["(\nMobility.TNC.shared.IVTFactor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % tncIVTFactor


    replacements[filepath]["(\ntaxi.baseFare[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % taxiBaseFare
    replacements[filepath]["(\ntaxi.costPerMile[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % taxiCPMile
    replacements[filepath]["(\ntaxi.costPerMinute[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % taxiCPMin

    replacements[filepath]["(\nTNC.single.baseFare[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % tncSingleBaseFare
    replacements[filepath]["(\nTNC.single.costPerMile[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % tncSingleCPMile
    replacements[filepath]["(\nTNC.single.costPerMinute[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % tncSingleCPMin
    replacements[filepath]["(\nTNC.single.costMinimum[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % tncSingleMinCost

    replacements[filepath]["(\nTNC.shared.baseFare[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % tncSharedBaseFare
    replacements[filepath]["(\nTNC.shared.costPerMile[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % tncSharedCPMile
    replacements[filepath]["(\nTNC.shared.costPerMinute[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % tncSharedCPMin
    replacements[filepath]["(\nTNC.shared.costMinimum[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % tncSharedMinCost

    replacements[filepath]["(\nTNC.single.waitTime.mean[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % tncSingleMeanWaitTime
    replacements[filepath]["(\nTNC.single.waitTime.sd[ \t]*=[ \t]*)(\S*)"] =    r"\g<1>%s" % tncSingleSDWaitTime

    replacements[filepath]["(\nTNC.shared.waitTime.mean[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % tncSharedMeanWaitTime
    replacements[filepath]["(\nTNC.shared.waitTime.sd[ \t]*=[ \t]*)(\S*)"] =    r"\g<1>%s" % tncSharedSDWaitTime

    replacements[filepath]["(\nTaxi.waitTime.mean[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % taxiMeanWaitTime
    replacements[filepath]["(\nTaxi.waitTime.sd[ \t]*=[ \t]*)(\S*)"] =   r"\g<1>%s" % taxiSDWaitTime

    occ_file  = open("taxi_tnc_occ_factors.csv", "w")
    occ_file.write('1,%5.2f,%5.2f,%5.2f\n' % (taxiDaShare,tncSingleDaShare,tncSharedDaShare))
    occ_file.write('2,%5.2f,%5.2f,%5.2f\n' % (taxiS2Share,tncSingleS2Share,tncSharedS2Share))
    occ_file.write('3,%5.2f,%5.2f,%5.2f\n' % (taxiS3Share,tncSingleS3Share,tncSharedS3Share))
    occ_file.close()

def get_property(properties_file_name, properties_file_contents, propname):
    """
    Return the string for this property.
    Exit if not found.
    """
    match           = re.search("\n%s[ \t]*=[ \t]*(\S*)[ \t]*" % propname, properties_file_contents)
    if match == None:
        print("Couldn't find {} in {}".format(propname, properties_file_name))
        sys.exit(2)
    return match.group(1)

def config_auto_opcost(params_filename, params_contents, for_logsums, replacements):
    """
    See USAGE for details.

    Replacements = { filepath -> regex_dict }
    """
    # find the auto operating cost
    auto_opc = float(get_property(params_filename, params_contents, "AutoOpCost"))

    # put them into the CTRAMP\scripts\block\hwyParam.block
    filepath = os.path.join("CTRAMP","scripts","block","hwyParam.block")
    replacements[filepath]["(\nAUTOOPC[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % auto_opc

    filepath = os.path.join("CTRAMP","runtime","accessibilities.properties")
    replacements[filepath]["(\nAuto.Operating.Cost[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % auto_opc

    filepath = os.path.join("CTRAMP","runtime","mtcTourBased.properties")
    if for_logsums:
        filepath = os.path.join("CTRAMP","runtime","logsums.properties")
    replacements[filepath]["(\nAuto.Operating.Cost[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % auto_opc

    # put it into the UECs
    config_uec("%.2f" % auto_opc)

    # small truck
    filepath = os.path.join("CTRAMP","scripts","block","hwyParam.block")
    smtr_opc        = get_property(params_filename, params_contents, "SmTruckOpCost")
    replacements[filepath]["(\nSMTROPC[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % smtr_opc

    # large truck
    lrtr_opc        = get_property(params_filename, params_contents, "LrTruckOpCost")
    replacements[filepath]["(\nLRTROPC[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % lrtr_opc

    # bus
    bus_opc         = get_property(params_filename, params_contents, "BusOpCost")
    replacements[filepath]["(\nBUSOPC[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % bus_opc

    # TruckTripDistribution gravity LOS term - tolled time part
    truck_distrib_LOS_toll_part = get_property(params_filename, params_contents, "TRUCK_DISTRIB_LOS_TOLL_PART")
    replacements[filepath]["(\nTRUCK_DISTRIB_LOS_TOLL_PART[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % truck_distrib_LOS_toll_part

    # AV impacts on road capacity - represented by adjusting passenger car equivalents (PCEs) by facility type
    av_pcefac_ft01   = float(get_property(params_filename, params_contents, "AV_PCE_FAC_FT01"))
    av_pcefac_ft02   = float(get_property(params_filename, params_contents, "AV_PCE_FAC_FT02"))
    av_pcefac_ft03   = float(get_property(params_filename, params_contents, "AV_PCE_FAC_FT03"))
    av_pcefac_ft04   = float(get_property(params_filename, params_contents, "AV_PCE_FAC_FT04"))
    av_pcefac_ft05   = float(get_property(params_filename, params_contents, "AV_PCE_FAC_FT05"))
    av_pcefac_ft06   = float(get_property(params_filename, params_contents, "AV_PCE_FAC_FT06"))
    av_pcefac_ft07   = float(get_property(params_filename, params_contents, "AV_PCE_FAC_FT07"))
    av_pcefac_ft08   = float(get_property(params_filename, params_contents, "AV_PCE_FAC_FT08"))
    av_pcefac_ft09   = float(get_property(params_filename, params_contents, "AV_PCE_FAC_FT09"))
    av_pcefac_ft10   = float(get_property(params_filename, params_contents, "AV_PCE_FAC_FT10"))

    OwnedAV_zpv      = float(get_property(params_filename, params_contents, "OwnedAV_ZPV_fac"))
    TNC_zpv          = float(get_property(params_filename, params_contents, "TNC_ZPV_fac"))

    MeansBasedTollsQ1Factor  = float(get_property(params_filename, params_contents, "Means_Based_Tolling_Q1Factor"))
    MeansBasedTollsQ2Factor  = float(get_property(params_filename, params_contents, "Means_Based_Tolling_Q2Factor"))
    MeansBasedFareQ1Factor   = float(get_property(params_filename, params_contents, "Means_Based_Fare_Q1Factor"))
    MeansBasedFareQ2Factor   = float(get_property(params_filename, params_contents, "Means_Based_Fare_Q2Factor"))
    HSRInterregionalDisable  =   int(get_property(params_filename, params_contents, "HSR_Interregional_Disable"))

    # put the av pce factors into the CTRAMP\scripts\block\hwyParam.block
    filepath = os.path.join("CTRAMP","scripts","block","hwyParam.block")
    replacements[filepath]["(\nAV_PCE_FT01[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % av_pcefac_ft01
    replacements[filepath]["(\nAV_PCE_FT02[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % av_pcefac_ft02
    replacements[filepath]["(\nAV_PCE_FT03[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % av_pcefac_ft03
    replacements[filepath]["(\nAV_PCE_FT04[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % av_pcefac_ft04
    replacements[filepath]["(\nAV_PCE_FT05[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % av_pcefac_ft05
    replacements[filepath]["(\nAV_PCE_FT06[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % av_pcefac_ft06
    replacements[filepath]["(\nAV_PCE_FT07[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % av_pcefac_ft07
    replacements[filepath]["(\nAV_PCE_FT08[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % av_pcefac_ft08
    replacements[filepath]["(\nAV_PCE_FT09[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % av_pcefac_ft09
    replacements[filepath]["(\nAV_PCE_FT10[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % av_pcefac_ft10

    replacements[filepath]["(\nOwnedAV_ZPV_factor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % OwnedAV_zpv
    replacements[filepath]["(\nTNC_ZPV_factor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % TNC_zpv

    replacements[filepath]["(\nMeans_Based_Tolling_Q1Factor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % MeansBasedTollsQ1Factor
    replacements[filepath]["(\nMeans_Based_Tolling_Q2Factor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % MeansBasedTollsQ2Factor

    # put the means based fare discount factors into CTRAMP\scripts\block\trnParam.block
    filepath = os.path.join("CTRAMP","scripts","block","trnParam.block")
    replacements[filepath]["(\nMeans_Based_Fare_Q1Factor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % MeansBasedFareQ1Factor
    replacements[filepath]["(\nMeans_Based_Fare_Q2Factor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % MeansBasedFareQ2Factor
    replacements[filepath]["(\nHSR_Interregional_Disable[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%d"   % HSRInterregionalDisable

def config_logsums(replacements, append):
    filepath = os.path.join("CTRAMP","runtime","logsums.properties")

    # households and persons
    replacements[filepath]["(\nPopulationSynthesizer.InputToCTRAMP.HouseholdFile[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % "logsums/accessibilities_dummy_households.csv"
    replacements[filepath]["(\nPopulationSynthesizer.InputToCTRAMP.PersonFile[ \t]*=[ \t]*)(\S*)"]    = r"\g<1>%s" % "logsums/accessibilities_dummy_persons.csv"

    # turn off some submodels
    replacements[filepath]["(\nRunModel.AutoOwnership[ \t]*=[ \t]*)(\S*)"]                                      = r"\g<1>false"
    replacements[filepath]["(\nRunModel.FreeParking[ \t]*=[ \t]*)(\S*)"]                                        = r"\g<1>false"
    replacements[filepath]["(\nRunModel.CoordinatedDailyActivityPattern[ \t]*=[ \t]*)(\S*)"]                    = r"\g<1>false"
    replacements[filepath]["(\nRunModel.IndividualMandatoryTourFrequency[ \t]*=[ \t]*)(\S*)"]                   = r"\g<1>false"
    replacements[filepath]["(\nRunModel.MandatoryTourDepartureTimeAndDuration[ \t]*=[ \t]*)(\S*)"]              = r"\g<1>false"
    replacements[filepath]["(\nRunModel.MandatoryTourModeChoice[ \t]*=[ \t]*)(\S*)"]                            = r"\g<1>false"
    replacements[filepath]["(\nRunModel.JointTourFrequency[ \t]*=[ \t]*)(\S*)"]                                 = r"\g<1>false"
    replacements[filepath]["(\nRunModel.JointTourLocationChoice[ \t]*=[ \t]*)(\S*)"]                            = r"\g<1>false"
    replacements[filepath]["(\nRunModel.JointTourDepartureTimeAndDuration[ \t]*=[ \t]*)(\S*)"]                  = r"\g<1>false"
    replacements[filepath]["(\nRunModel.JointTourModeChoice[ \t]*=[ \t]*)(\S*)"]                                = r"\g<1>false"
    replacements[filepath]["(\nRunModel.IndividualNonMandatoryTourFrequency[ \t]*=[ \t]*)(\S*)"]                = r"\g<1>false"
    replacements[filepath]["(\nRunModel.IndividualNonMandatoryTourDepartureTimeAndDuration[ \t]*=[ \t]*)(\S*)"] = r"\g<1>false"
    replacements[filepath]["(\nRunModel.IndividualNonMandatoryTourModeChoice[ \t]*=[ \t]*)(\S*)"]               = r"\g<1>false"
    replacements[filepath]["(\nRunModel.AtWorkSubTourFrequency[ \t]*=[ \t]*)(\S*)"]                             = r"\g<1>false"
    replacements[filepath]["(\nRunModel.AtWorkSubTourDepartureTimeAndDuration[ \t]*=[ \t]*)(\S*)"]              = r"\g<1>false"
    replacements[filepath]["(\nRunModel.AtWorkSubTourModeChoice[ \t]*=[ \t]*)(\S*)"]                            = r"\g<1>false"
    replacements[filepath]["(\nRunModel.StopFrequency[ \t]*=[ \t]*)(\S*)"]                                      = r"\g<1>false"
    replacements[filepath]["(\nRunModel.StopLocation[ \t]*=[ \t]*)(\S*)"]                                       = r"\g<1>false"

    # sample size
    replacements[filepath]["(\nUsualWorkAndSchoolLocationChoice.SampleOfAlternatives.SampleSize[ \t]*=[ \t]*)(\S*)"]         = r"\g<1>4362"
    replacements[filepath]["(\nJointTourLocationChoice.SampleOfAlternatives.SampleSize[ \t]*=[ \t]*)(\S*)"]                  = r"\g<1>30"
    replacements[filepath]["(\nIndividualNonMandatoryTourLocationChoice.SampleOfAlternatives.SampleSize[ \t]*=[ \t]*)(\S*)"] = r"\g<1>4362"
    replacements[filepath]["(\nAtWorkSubtourLocationChoice.SampleOfAlternatives.SampleSize[ \t]*=[ \t]*)(\S*)"]              = r"\g<1>30"

    # use logsums from base run
    replacements[filepath]["(\nUsualWorkAndSchoolLocationChoice.ShadowPrice.Input.File[ \t]*=[ \t]*)(\S*)"]          = r"\g<1>logsums/ShadowPricing_7.csv"
    replacements[filepath]["(\nUsualWorkAndSchoolLocationChoice.ShadowPricing.MaximumIterations[ \t]*=[ \t]*)(\S*)"] = r"\g<1>1"
    replacements[filepath]["(\nUsualWorkAndSchoolLocationChoice.ShadowPricing.OutputFile[ \t]*=[ \t]*)(\S*)"]        = r"\g<1>logsums/ShadowPricing.csv"
    replacements[filepath]["(\nUsualWorkAndSchoolLocationChoice.SizeTerms.OutputFile[ \t]*=[ \t]*)(\S*)"]            = r"\g<1>logsums/DestinationChoiceSizeTerms.csv"

    replacements[filepath]["(\nResults.HouseholdDataFile[ \t]*=[ \t]*)(\S*)"]     = r"\g<1>logsums/householdData.csv"
    replacements[filepath]["(\nResults.PersonDataFile[ \t]*=[ \t]*)(\S*)"]        = r"\g<1>logsums/personData.csv"
    replacements[filepath]["(\nResults.IndivTourDataFile[ \t]*=[ \t]*)(\S*)"]     = r"\g<1>logsums/indivTourData.csv"
    replacements[filepath]["(\nResults.JointTourDataFile[ \t]*=[ \t]*)(\S*)"]     = r"\g<1>logsums/jointTourData.csv"
    replacements[filepath]["(\nResults.IndivTripDataFile[ \t]*=[ \t]*)(\S*)"]     = r"\g<1>logsums/indivTripData.csv"
    replacements[filepath]["(\nResults.JointTripDataFile[ \t]*=[ \t]*)(\S*)"]     = r"\g<1>logsums/jointTripData.csv"
    replacements[filepath]["(\nResults.WriteDataToDatabase[ \t]*=[ \t]*)(\S*)"]   = r"\g<1>false"

    append[filepath] = "\n#-- Logsum input files for recreating skipped model choices\n" + \
                       "Accessibilities.HouseholdDataFile = logsums/accessibilities_dummy_model_households.csv\n" + \
                       "Accessibilities.PersonDataFile = logsums/accessibilities_dummy_model_persons.csv\n" + \
                       "Accessibilities.IndivTourDataFile = logsums/accessibilities_dummy_indivTours.csv\n"

def config_host_ip(for_logsums, replacements):
    """
    See USAGE for details.

    Replacements = { filepath -> regex_dict }
    """
    host_ip_address = os.environ['HOST_IP_ADDRESS']

    # verify that the host IP address relevant to this machine
    ips_here        = socket.gethostbyname_ex(socket.gethostname())[-1]
    if host_ip_address not in ips_here:
        print("FATAL: HOST_IP_ADDRESS {} does not match the IP addresses for this machine {}".format(host_ip_address, str(ips_here)))
        sys.exit(2)

    # CTRAMP\runtime\JavaOnly_runMain.cmd and CTRAMP\runtime\JavaOnly_runNode*.cmd
    filenames = ["JavaOnly_runMain.cmd"]
    for nodenum in range(5): filenames.append("JavaOnly_runNode%d.cmd" % nodenum)
    for filename in filenames:
        filepath = os.path.join("CTRAMP","runtime",filename)
        replacements[filepath]["(\nset HOST_IP=)(\S*)"] = r"\g<1>%s" % host_ip_address

    # driver number
    last_number = host_ip_address.split(".")[-1]
    driver      = 'driver%s' % last_number
    for filename in ['jppf-clientDistributed.properties','jppf-clientLocal.properties']:
        filepath = os.path.join("CTRAMP","runtime","config",filename)
        replacements[filepath]["(\njppf.drivers[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % driver
        replacements[filepath]["(\n)(driver[0-9]+\.)"] = r"\g<1>%s." % driver

    # server host
    filenames = ['jppf-clientDistributed.properties',
                 'jppf-clientLocal.properties',
                 'jppf-driver.properties']
    for nodenum in range(5): filenames.append("jppf-node%d.properties" % nodenum)
    for filename in filenames:
        filepath = os.path.join("CTRAMP","runtime","config",filename)
        replacements[filepath]["(jppf.server.host[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % host_ip_address

    # management host
    filepath = os.path.join("CTRAMP","runtime","config",'jppf-clientDistributed.properties')
    replacements[filepath]["(jppf.management.host[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % host_ip_address

    # put it into mtcTourBased.properties or logsums.properties
    if for_logsums:
        # do for logsums.properties
        filepath = os.path.join("CTRAMP","runtime","logsums.properties")
        replacements[filepath]["(\nRunModel.HouseholdServerAddress[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % host_ip_address
        replacements[filepath]["(\nRunModel.MatrixServerAddress[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % host_ip_address

    else:
        filepath = os.path.join("CTRAMP","runtime","mtcTourBased.properties")
        replacements[filepath]["(\nRunModel.HouseholdServerAddress[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % host_ip_address
        replacements[filepath]["(\nRunModel.MatrixServerAddress[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % host_ip_address

def config_distribution(replacements):
    """
    See USAGE for details.

    Replacements = { filepath -> regex_dict }
    """
    hostname = socket.gethostname()
    if hostname == 'mainmodel':
        # accessibilities
        filepath = os.path.join("CTRAMP","runtime","accessibilities.properties")
        replacements[filepath]["(\nnum.acc.threads[ \t]*=[ \t]*)(\S*)"] = r"\g<1>14"

        # CORE
        filenames = []
        for nodenum in range(5): filenames.append("jppf-node%d.properties" % nodenum)
        for filename in filenames:
            filepath = os.path.join("CTRAMP","runtime","config",filename)
            replacements[filepath]["(\nprocessing.threads[ \t]*=[ \t]*)(\S*)"] = r"\g<1>12"

        # hwyassign
        print("Copying HwyIntraStep_64.block to HwyIntraStep.block")
        shutil.copy2(os.path.join("CTRAMP","scripts","block","HwyIntraStep_64.block"),
                     os.path.join("CTRAMP","scripts","block","HwyIntraStep.block"))

    elif hostname in ['MODEL2-A','MODEL2-B','MODEL2-C','MODEL2-D','PORMDLPPW01','PORMDLPPW02','Model3-a','Model3-b'] or hostname.startswith("WIN-"):
        # accessibilities: 48 logical processors
        filepath = os.path.join("CTRAMP","runtime","accessibilities.properties")
        replacements[filepath]["(\nnum.acc.threads[ \t]*=[ \t]*)(\S*)"] = r"\g<1>48"

        # CORE: use half for JPPF nodes - 48 didn't seem to take
        filenames = []
        for nodenum in range(5): filenames.append("jppf-node%d.properties" % nodenum)
        for filename in filenames:
            filepath = os.path.join("CTRAMP","runtime","config",filename)
            replacements[filepath]["(\nprocessing.threads[ \t]*=[ \t]*)(\S*)"] = r"\g<1>24"

        # hwyassign
        print("Copying HwyIntraStep_48.block to HwyIntraStep.block")
        shutil.copy2(os.path.join("CTRAMP","scripts","block","HwyIntraStep_48.block"),
                     os.path.join("CTRAMP","scripts","block","HwyIntraStep.block"))

    else:
        raise Exception("RuntimeConfiguration.py does not recognize hostname [%s] for distribution configuration" % hostname)

# def config_distribution(replacements):
#     """
#     See USAGE for details.

#     Replacements = { filepath -> regex_dict }
#     """
#     hostname = socket.gethostname()
#     if hostname == 'mainmodel':
#         # accessibilities
#         filepath = os.path.join("CTRAMP","runtime","accessibilities.properties")
#         replacements[filepath]["(\nnum.acc.threads[ \t]*=[ \t]*)(\S*)"] = r"\g<1>14"

#         # CORE
#         filenames = []
#         for nodenum in range(5): filenames.append("jppf-node%d.properties" % nodenum)
#         for filename in filenames:
#             filepath = os.path.join("CTRAMP","runtime","config",filename)
#             replacements[filepath]["(\nprocessing.threads[ \t]*=[ \t]*)(\S*)"] = r"\g<1>12"

#         # hwyassign
#         print("Copying HwyIntraStep_64.block to HwyIntraStep.block")
#         shutil.copy2(os.path.join("CTRAMP","scripts","block","HwyIntraStep_64.block"),
#                      os.path.join("CTRAMP","scripts","block","HwyIntraStep.block"))

#     elif hostname in ['MODEL2-A','MODEL2-B','MODEL2-C','MODEL2-D','PORMDLPPW01','PORMDLPPW02','Model3-a'] or hostname.startswith("WIN-"):
#         # accessibilities: 48 logical processors
#         filepath = os.path.join("CTRAMP","runtime","accessibilities.properties")
#         replacements[filepath]["(\nnum.acc.threads[ \t]*=[ \t]*)(\S*)"] = r"\g<1>48"

#         # CORE: use half for JPPF nodes - 48 didn't seem to take
#         filenames = []
#         for nodenum in range(5): filenames.append("jppf-node%d.properties" % nodenum)
#         for filename in filenames:
#             filepath = os.path.join("CTRAMP","runtime","config",filename)
#             replacements[filepath]["(\nprocessing.threads[ \t]*=[ \t]*)(\S*)"] = r"\g<1>24"

#         # hwyassign
#         print("Copying HwyIntraStep_48.block to HwyIntraStep.block")
#         shutil.copy2(os.path.join("CTRAMP","scripts","block","HwyIntraStep_48.block"),
#                      os.path.join("CTRAMP","scripts","block","HwyIntraStep.block"))

#     else:
        raise Exception("RuntimeConfiguration.py does not recognize hostname [%s] for distribution configuration" % hostname)

def config_shadowprice(iter, replacements):
    """
    See USAGE for details.

    Replacements = { filepath -> regex_dict }
    """
    filepath = os.path.join("CTRAMP","runtime","mtcTourBased.properties")
    if iter==1:
        # 4 iterations, no input file -- comment it out
        replacements[filepath]["(\n)(#?)(UsualWorkAndSchoolLocationChoice.ShadowPrice.Input.File[ \t]*=[ \t]*)(\S*)"] = \
            r"\g<1>#\g<3>\g<4>"
        replacements[filepath]["(\nUsualWorkAndSchoolLocationChoice.ShadowPricing.MaximumIterations[ \t]*=[ \t]*)(\S*)"] = \
            r"\g<1>4"
    elif iter==2:
        # update to 2 iterations and add input file
        replacements[filepath]["(\n)(#?)(UsualWorkAndSchoolLocationChoice.ShadowPrice.Input.File[ \t]*=[ \t]*)(\S*)"] = \
            r"\g<1>\g<3>main/ShadowPricing_3.csv"
        replacements[filepath]["(\nUsualWorkAndSchoolLocationChoice.ShadowPricing.MaximumIterations[ \t]*=[ \t]*)(\S*)"] = \
            r"\g<1>2"
    else:
        # update input file
        replacements[filepath]["(\n)(#?)(UsualWorkAndSchoolLocationChoice.ShadowPrice.Input.File[ \t]*=[ \t]*)(\S*)"] = \
            r"\g<1>\g<3>main/ShadowPricing_%d.csv" % (2*iter-1)

def config_uec(auto_operating_cost):
    auto_op_cost_float = float(auto_operating_cost)

    for bookname in ["ModeChoice.xls","TripModeChoice.xls","accessibility_utility.xls"]:
        filepath = os.path.join("CTRAMP","model",bookname)
        shutil.move(filepath, "%s.original" % filepath)

        print("Updating {}".format(filepath))
        rb = xlrd.open_workbook("%s.original" % filepath, formatting_info=True, on_demand=True)
        wb = xlutils.copy.copy(rb)
        for sheet_num in range(rb.nsheets):
            rs = rb.get_sheet(sheet_num)
            for rownum in range(rs.nrows):
                # print(rs.cell(rownum,1))
                if rs.cell(rownum,1).value=='costPerMile':
                    print("  Sheet '{}': replacing costPerMile '{}' -> {:.2f}".format(
                        rs.name, rs.cell(rownum,4).value, auto_op_cost_float))
                    wb.get_sheet(sheet_num).write(rownum,4,auto_op_cost_float,
                                                  xlwt.easyxf("align: horiz left"))
                # print(rs.cell(rownum,1))

        wb.save(filepath)


# define a function to put the telecommute constant into the Coordinated Daily Activity Pattern excel file
def config_cdap(params_filename, params_contents):

    # read the telecommute constant from the properties file
    TelecommuteConstant_FT = float(get_property(params_filename, params_contents, "Telecommute_constant_FT"))
    TelecommuteConstant_PT = float(get_property(params_filename, params_contents, "Telecommute_constant_PT"))

    for bookname in ["CoordinatedDailyActivityPattern.xls"]:
        filepath = os.path.join("CTRAMP","model",bookname)
        shutil.move(filepath, "%s.original" % filepath)

        print("Updating {}".format(filepath))
        rb = xlrd.open_workbook("%s.original" % filepath, formatting_info=True, on_demand=True)
        wb = xlutils.copy.copy(rb)
        for sheet_num in range(rb.nsheets):
            rs = rb.get_sheet(sheet_num)
            for rownum in range(rs.nrows):
                # print(rs.cell(rownum,1))
                if rs.cell(rownum,2).value=='Simulate telecommuting by reducing mandatory patterns - global_FT':
                    print("  Sheet '{}': replacing telecommute constant '{}' -> {:.2f}".format(
                        rs.name, rs.cell(rownum,6).value, TelecommuteConstant_FT))
                    wb.get_sheet(sheet_num).write(rownum,6, TelecommuteConstant_FT, xlwt.easyxf("align: horiz right"))
                if rs.cell(rownum,2).value=='Simulate telecommuting by reducing mandatory patterns - global_PT':
                    print("  Sheet '{}': replacing telecommute constant '{}' -> {:.2f}".format(
                        rs.name, rs.cell(rownum,6).value, TelecommuteConstant_PT))
                    wb.get_sheet(sheet_num).write(rownum,6, TelecommuteConstant_PT, xlwt.easyxf("align: horiz right"))                    
        wb.save(filepath)

def config_freeparking(params_filename, params_contents):
    """
    Transfer Free_Parking_Eligibility_OnOff to FreeParkingEligibility UECs
    """

    # read the telecommute constant from the properties file
    Free_Parking_Eligibility_OnOff = float(get_property(params_filename, params_contents, "Free_Parking_Eligibility_OnOff"))

    for bookname in ["FreeParkingEligibility.xls"]:
        filepath = os.path.join("CTRAMP","model",bookname)
        shutil.move(filepath, "%s.original" % filepath)

        print("Updating {}".format(filepath))
        rb = xlrd.open_workbook("%s.original" % filepath, formatting_info=True, on_demand=True)
        wb = xlutils.copy.copy(rb)
        for sheet_num in range(rb.nsheets):
            rs = rb.get_sheet(sheet_num)
            for rownum in range(rs.nrows):
                # print(rs.cell(rownum,1))
                if rs.cell(rownum,2).value=='Free parking eligibility OnOff dummy':
                    print("  Sheet '{}': replacing Free parking eligibility OnOff dummy '{}' -> {:.4f}".format(
                        rs.name, rs.cell(rownum,6).value, Free_Parking_Eligibility_OnOff))
                    wb.get_sheet(sheet_num).write(rownum,6, Free_Parking_Eligibility_OnOff, xlwt.easyxf("align: horiz right"))
        wb.save(filepath)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = USAGE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("--iter",
                        help="Iteration for which to configure.  If not specified, will configure for pre-run.",
                        type=int, choices=[1,2,3,4,5])
    parser.add_argument("--logsums", help="Configure for logsums.", action='store_true')

    my_args = parser.parse_args()

    # read INPUT\params.properties
    params_filename = os.path.join("INPUT", "params.properties")
    myfile          = open( params_filename, 'r' )
    params_contents = myfile.read()
    myfile.close()
    print("Read {} lines from {}".format(len(params_contents), params_filename))

    # Figure out the replacements we need to make
    replacements = collections.defaultdict(collections.OrderedDict)
    append       = collections.defaultdict(collections.OrderedDict)
    if my_args.logsums:
       # reconfigure host ip places so logsums doesn't nec need to be run on same machine as model core
        config_host_ip(True, replacements)
        config_project_dir(True, replacements)
        # copy properties file to logsums file
        shutil.copyfile(os.path.join("CTRAMP","runtime","mtcTourBased.properties"),
                        os.path.join("CTRAMP","runtime","logsums.properties"))
        config_logsums(replacements, append)
        config_mobility_params(params_filename, params_contents, True, replacements)
        config_auto_opcost(params_filename, params_contents, True, replacements)
    elif my_args.iter == None:
        config_project_dir(False, replacements)
        config_popsyn_files(replacements)
        config_mobility_params(params_filename, params_contents, False, replacements)
        config_auto_opcost(params_filename, params_contents, False, replacements)
        config_host_ip(False, replacements)
        config_distribution(replacements)
        config_cdap(params_filename, params_contents)
        config_freeparking(params_filename, params_contents)
    else:
        config_shadowprice(my_args.iter, replacements)

    # Go ahead and make the replacements
    for filepath,regex_dict in replacements.items():
        replace_in_file(filepath, regex_dict)

    # append
    for filepath,append_str in append.items():
        append_to_file(filepath, append_str)
