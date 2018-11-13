
USAGE = r"""

This script makes some runtime configuration changes in order to try to simplify
changes that need to be made at runtime.

If no iteration is specified, then these include:
 * Project Directory
   + Assumed to be the current working directory
   + Propagated to CTRAMP\runtime\accessibilities.properties,
                   CTRAMP\runtime\mtcTourBased.properties
 * Synthesized households and persons files
   + Assumed to be INPUT\popsyn\hhFile.* and INPUT\popsyn\personFile.*
   + Propagated to CTRAMP\runtime\mtcTourBased.properties
 * Auto Operating Costs
   + Specify the values in INPUT\params.properties
   + It will be propagated to CTRAMP\scripts\block\hwyParam.block,
                              CTRAMP\runtime\accessibilities.properties (new!),
                              CTRAMP\runtime\mtcTourBased.properties (new!)
   + It will be propagated to CTRAMP\model\ModeChoice.xls,  (for costPerMile and AV IVT multiplier)
                              CTRAMP\model\TripModeChoice.xls,
                              CTRAMP\model\accessibility_utility.xls
 * Truck Operating Cost (plus RM, Fuel breakdown)
   + Specify the value in INPUT\params.properties
   + It will be propagated to CTRAMP\scripts\block\hwyParam.block
 * Host IP - where the household manager, matrix manager and JPPF Server run
   + Assumed to be the HOST_IP_ADDRESS in the environment
   + Assumed that this script is running on this host IP (this is verified)
   + It will be propagated to CTRAMP\runtime\JavaOnly_runMain.cmd
                              CTRAMP\runtime\JavaOnly_runNode[0-4].cmd
                              CTRAMP\runtime\config\jppf-clientDistributed.properties
                              CTRAMP\runtime\config\jppf-clientLocal.properties
                              CTRAMP\runtime\config\jppf-driver.properties
                              CTRAMP\runtime\config\jppf-node[0-4].properties
                              CTRAMP\runtime\mtcTourBased.properties
 * Distribution
   + Based on hostname.
     * 'MODEL2-A', 'MODEL2-C','MODEL2-D','PORMDLPPW01','PORMDLPPW02': single machine setup with
        48 Cube Voyager processes available
        48 threads for accessibilities
        24 threads for core
     * 'mainmodel': multiple machine setup

If an iteration is specified, then the following UsualWorkAndSchoolLocationChoice
lines are set in CTRAMP\runtime\mtcTourBased.properties:

  Iteration 1:
    ShadowPrice.Input.File          = (blank)
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
    print "Updating %s" % filepath

    # read the contents
    myfile = open("%s.original" % filepath, 'r')
    file_contents = myfile.read()
    myfile.close()

    # do the regex subs
    for pattern,newstr in regex_dict.iteritems():
        (file_contents, numsubs) = re.subn(pattern,newstr,file_contents,flags=re.IGNORECASE)
        print "  Made %d sub for %s" % (numsubs, newstr)
        # Fail on failure
        if numsubs < 1:
            print "  SUBSITUTION NOT MADE -- Fatal error"
            print "  pattern = [%s]" % pattern
            sys.exit(2)

    # write the result
    myfile = open(filepath, 'w')
    myfile.write(file_contents)
    myfile.close()

def config_project_dir(replacements):
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

def config_mobility_params(replacements):
    """
    See USAGE for details.

    Replacements = { filepath -> regex_dict }
    """
    params_filename = os.path.join("INPUT", "params.properties")
    myfile          = open( params_filename, 'r' )
    myfile_contents = myfile.read()
    myfile.close()
    # get parameters
    # Mobility.AV.Share = 0.0
    # Mobility.AV.ProbabilityBoost.AutosLTDrivers = 1.2
    # Mobility.AV.ProbabilityBoost.AutosGEDrivers = 1.1
    # Mobility.AV.IVTFactor = 0.5
    # Mobility.AV.ParkingCostFactor = 0.0
    # Mobility.AV.CostPerMileFactor = 0.5
    # Mobility.AV.TerminalTimeFactor = 0.0
    # 
    # taxi.baseFare = 2.20
    # taxi.costPerMile = 2.30
    # taxi.costPerMinute = 0.10
    # TNC.baseFare = 2.20
    # TNC.costPerMile = 1.33
    # TNC.costPerMinute = 0.24
    # TNC.costMinimum = 7.20
    # 
    # TNC.waitTime.mean =  10.3, 8.5,  8.4, 6.3, 4.7
    # TNC.waitTime.sd =     4.1, 4.1,  4.1, 4.1, 4.1
    # Taxi.waitTime.mean = 26.5, 17.3,13.3, 9.5, 5.5
    # Taxi.waitTime.sd =    6.4,  6.4, 6.4, 6.4, 6.4
    #
    avShare   = float(get_property(params_filename, myfile_contents, "Mobility.AV.Share"))
    pBoostAutosLTDrivers = float(get_property(params_filename, myfile_contents, "Mobility.AV.ProbabilityBoost.AutosLTDrivers"))
    pBoostAutosGEDrivers = float(get_property(params_filename, myfile_contents, "Mobility.AV.ProbabilityBoost.AutosGEDrivers"))
    avIVTFactor  = float(get_property(params_filename, myfile_contents, "Mobility.AV.IVTFactor")) 
    avparkCostFactor  = float(get_property(params_filename, myfile_contents, "Mobility.AV.ParkingCostFactor")) 
    avCPMFactor = float(get_property(params_filename, myfile_contents, "Mobility.AV.CostPerMileFactor"))  
    avTermTimeFactor = float(get_property(params_filename, myfile_contents, "Mobility.AV.TerminalTimeFactor"))  

    taxiBaseFare = float(get_property(params_filename, myfile_contents, "taxi.baseFare")) 
    taxiCPMile = float(get_property(params_filename, myfile_contents, "taxi.costPerMile")) 
    taxiCPMin = float(get_property(params_filename, myfile_contents, "taxi.costPerMinute")) 
    tncBaseFare = float(get_property(params_filename, myfile_contents, "TNC.baseFare")) 
    tncCPMile = float(get_property(params_filename, myfile_contents, "TNC.costPerMile")) 
    tncCPMin = float(get_property(params_filename, myfile_contents, "TNC.costPerMinute"))     
    tncMinCost = float(get_property(params_filename, myfile_contents, "TNC.costMinimum"))  

    tncMeanWaitTime = get_property(params_filename, myfile_contents, "TNC.waitTime.mean") 
    tncSDWaitTime = get_property(params_filename, myfile_contents, "TNC.waitTime.sd")
    taxiMeanWaitTime = get_property(params_filename, myfile_contents, "Taxi.waitTime.mean")     
    taxiSDWaitTime = get_property(params_filename, myfile_contents, "Taxi.waitTime.sd")

    filepath = os.path.join("CTRAMP","runtime","mtcTourBased.properties")
    replacements[filepath]["(\nMobility.AV.Share[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % avShare
    replacements[filepath]["(\nMobility.AV.ProbabilityBoost.AutosLTDrivers[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % pBoostAutosLTDrivers
    replacements[filepath]["(\nMobility.AV.ProbabilityBoost.AutosGEDrivers[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % pBoostAutosGEDrivers
    replacements[filepath]["(\nMobility.AV.IVTFactor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % avIVTFactor
    replacements[filepath]["(\nMobility.AV.ParkingCostFactor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % avparkCostFactor
    replacements[filepath]["(\nMobility.AV.CostPerMileFactor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % avCPMFactor
    replacements[filepath]["(\nMobility.AV.TerminalTimeFactor[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % avTermTimeFactor
    replacements[filepath]["(\ntaxi.baseFare[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % taxiBaseFare
    replacements[filepath]["(\ntaxi.costPerMile[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % taxiCPMile
    replacements[filepath]["(\ntaxi.costPerMinute[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % taxiCPMin
    replacements[filepath]["(\nTNC.baseFare[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % tncBaseFare
    replacements[filepath]["(\nTNC.costPerMile[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % tncCPMile
    replacements[filepath]["(\nTNC.costPerMinute[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % tncCPMin
    replacements[filepath]["(\nTNC.costMinimum[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % tncMinCost
    replacements[filepath]["(\nTNC.waitTime.mean[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % tncMeanWaitTime
    replacements[filepath]["(\nTNC.waitTime.sd[ \t]*=[ \t]*)(\S*)"] =    r"\g<1>%s" % tncSDWaitTime
    replacements[filepath]["(\nTaxi.waitTime.mean[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % taxiMeanWaitTime
    replacements[filepath]["(\nTaxi.waitTime.sd[ \t]*=[ \t]*)(\S*)"] =   r"\g<1>%s" % taxiSDWaitTime

def get_property(properties_file_name, properties_file_contents, propname):
    """
    Return the string for this property.
    Exit if not found.
    """
    match           = re.search("\n%s[ \t]*=[ \t]*(\S*)[ \t]*" % propname, properties_file_contents)
    if match == None:
        print "Couldn't find %s in %s" % (propname, properties_file_name)
        sys.exit(2)
    return match.group(1)

def config_auto_opcost(replacements):
    """
    See USAGE for details.

    Replacements = { filepath -> regex_dict }
    """
    # find the auto operating cost
    params_filename = os.path.join("INPUT", "params.properties")
    myfile          = open( params_filename, 'r' )
    myfile_contents = myfile.read()
    myfile.close()

    auto_opc_perfect_rm   = float(get_property(params_filename, myfile_contents, "AutoOpCost_perfect_RM"))
    auto_opc_perfect_fuel = float(get_property(params_filename, myfile_contents, "AutoOpCost_perfect_Fuel"))

    # put them into the CTRAMP\scripts\block\hwyParam.block
    filepath = os.path.join("CTRAMP","scripts","block","hwyParam.block")
    replacements[filepath]["(\nAUTOOPC_PER_RM[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % auto_opc_perfect_rm
    replacements[filepath]["(\nAUTOOPC_PER_FU[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % auto_opc_perfect_fuel

    # total auto operating cost on perfect pavement
    auto_opc_perfect = auto_opc_perfect_rm + auto_opc_perfect_fuel

    filepath = os.path.join("CTRAMP","runtime","accessibilities.properties")
    replacements[filepath]["(\nAuto.Operating.Cost[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % auto_opc_perfect

    filepath = os.path.join("CTRAMP","runtime","mtcTourBased.properties")
    replacements[filepath]["(\nAuto.Operating.Cost[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % auto_opc_perfect

    # AV impacts on perceived in-vehicle travel time
    av_ivt_factor   = float(get_property(params_filename, myfile_contents, "AV_IVT_FAC"))

    # put it into the UECs
    config_uec("%.2f" % auto_opc_perfect,"%.2f" % av_ivt_factor)

    # auto operating cost freeway adjustments
    auto_opc_adjust_rm   = get_property(params_filename, myfile_contents, "AutoOpCost_fwyadj_RM")
    auto_opc_adjust_fuel = get_property(params_filename, myfile_contents, "AutoOpCost_fwyadj_Fuel")

    filepath = os.path.join("CTRAMP","scripts","block","hwyParam.block")
    replacements[filepath]["(\nAUTOOPC_FWY_RM[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % auto_opc_adjust_rm
    replacements[filepath]["(\nAUTOOPC_FWY_FU[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % auto_opc_adjust_fuel

    # small truck
    smtr_opc_perfect_rm   = get_property(params_filename, myfile_contents, "SmTruckOpCost_perfect_RM")
    smtr_opc_perfect_fuel = get_property(params_filename, myfile_contents, "SmTruckOpCost_perfect_Fuel")
    smtr_opc_adjust_rm    = get_property(params_filename, myfile_contents, "SmTruckOpCost_fwyadj_RM")
    smtr_opc_adjust_fuel  = get_property(params_filename, myfile_contents, "SmTruckOpCost_fwyadj_Fuel")
    replacements[filepath]["(\nSMTROPC_PER_RM[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % smtr_opc_perfect_rm
    replacements[filepath]["(\nSMTROPC_PER_FU[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % smtr_opc_perfect_fuel
    replacements[filepath]["(\nSMTROPC_FWY_RM[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % smtr_opc_adjust_rm
    replacements[filepath]["(\nSMTROPC_FWY_FU[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % smtr_opc_adjust_fuel

    # large truck
    lrtr_opc_perfect_rm   = get_property(params_filename, myfile_contents, "LrTruckOpCost_perfect_RM")
    lrtr_opc_perfect_fuel = get_property(params_filename, myfile_contents, "LrTruckOpCost_perfect_Fuel")
    lrtr_opc_adjust_rm    = get_property(params_filename, myfile_contents, "LrTruckOpCost_fwyadj_RM")
    lrtr_opc_adjust_fuel  = get_property(params_filename, myfile_contents, "LrTruckOpCost_fwyadj_Fuel")
    replacements[filepath]["(\nLRTROPC_PER_RM[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % lrtr_opc_perfect_rm
    replacements[filepath]["(\nLRTROPC_PER_FU[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % lrtr_opc_perfect_fuel
    replacements[filepath]["(\nLRTROPC_FWY_RM[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % lrtr_opc_adjust_rm
    replacements[filepath]["(\nLRTROPC_FWY_FU[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % lrtr_opc_adjust_fuel

    # bus
    bus_opc_perfect_rm   = get_property(params_filename, myfile_contents, "BusOpCost_perfect_RM")
    bus_opc_perfect_fuel = get_property(params_filename, myfile_contents, "BusOpCost_perfect_Fuel")
    bus_opc_adjust_rm    = get_property(params_filename, myfile_contents, "BusOpCost_fwyadj_RM")
    bus_opc_adjust_fuel  = get_property(params_filename, myfile_contents, "BusOpCost_fwyadj_Fuel")
    replacements[filepath]["(\nBUSOPC_PER_RM[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % bus_opc_perfect_rm
    replacements[filepath]["(\nBUSOPC_PER_FU[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % bus_opc_perfect_fuel
    replacements[filepath]["(\nBUSOPC_FWY_RM[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % bus_opc_adjust_rm
    replacements[filepath]["(\nBUSOPC_FWY_FU[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % bus_opc_adjust_fuel


    # AV impacts on road capacity - represented by adjusting passenger car equivalents (PCEs) by facility type
    av_pcefac_ft01   = float(get_property(params_filename, myfile_contents, "AV_PCE_FAC_FT01"))
    av_pcefac_ft02   = float(get_property(params_filename, myfile_contents, "AV_PCE_FAC_FT02"))
    av_pcefac_ft03   = float(get_property(params_filename, myfile_contents, "AV_PCE_FAC_FT03"))
    av_pcefac_ft04   = float(get_property(params_filename, myfile_contents, "AV_PCE_FAC_FT04"))
    av_pcefac_ft05   = float(get_property(params_filename, myfile_contents, "AV_PCE_FAC_FT05"))
    av_pcefac_ft06   = float(get_property(params_filename, myfile_contents, "AV_PCE_FAC_FT06"))
    av_pcefac_ft07   = float(get_property(params_filename, myfile_contents, "AV_PCE_FAC_FT07"))
    av_pcefac_ft08   = float(get_property(params_filename, myfile_contents, "AV_PCE_FAC_FT08"))
    av_pcefac_ft09   = float(get_property(params_filename, myfile_contents, "AV_PCE_FAC_FT09"))
    av_pcefac_ft10   = float(get_property(params_filename, myfile_contents, "AV_PCE_FAC_FT10"))

    sharing   = float(get_property(params_filename, myfile_contents, "Sharing_Preferences"))

    # put the av pce factors into the CTRAMP\scripts\block\hwyParam.block
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

    replacements[filepath]["(\nSharingPref[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%.2f" % sharing

def config_host_ip(replacements):
    """
    See USAGE for details.

    Replacements = { filepath -> regex_dict }
    """
    host_ip_address = os.environ['HOST_IP_ADDRESS']

    # verify that the host IP address relevant to this machine
    ips_here        = socket.gethostbyname_ex(socket.gethostname())[-1]
    if host_ip_address not in ips_here:
        print "FATAL: HOST_IP_ADDRESS %s does not match the IP addresses for this machine %s" % (host_ip_address, str(ips_here))
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
        replacements[filepath]["(\n)(driver1\.)"] = r"\g<1>%s." % driver

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

    # put it into mtcTourBased.properties
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
        print "Copying HwyIntraStep_64.block to HwyIntraStep.block"
        shutil.copy2(os.path.join("CTRAMP","scripts","block","HwyIntraStep_64.block"),
                     os.path.join("CTRAMP","scripts","block","HwyIntraStep.block"))

    elif hostname in ['MODEL2-A','MODEL2-B','MODEL2-C','MODEL2-D','PORMDLPPW01','PORMDLPPW02']:
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
        print "Copying HwyIntraStep_48.block to HwyIntraStep.block"
        shutil.copy2(os.path.join("CTRAMP","scripts","block","HwyIntraStep_48.block"),
                     os.path.join("CTRAMP","scripts","block","HwyIntraStep.block"))

    else:
        raise Exception("RuntimeConfiguration.py does not recognize hostname [%s] for distribution configuration" % hostname)

def config_host_ip(replacements):
    """
    See USAGE for details.

    Replacements = { filepath -> regex_dict }
    """
    host_ip_address = os.environ['HOST_IP_ADDRESS']

    # verify that the host IP address relevant to this machine
    ips_here        = socket.gethostbyname_ex(socket.gethostname())[-1]
    if host_ip_address not in ips_here:
        print "FATAL: HOST_IP_ADDRESS %s does not match the IP addresses for this machine %s" % (host_ip_address, str(ips_here))
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

    # put it into mtcTourBased.properties
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
        print "Copying HwyIntraStep_64.block to HwyIntraStep.block"
        shutil.copy2(os.path.join("CTRAMP","scripts","block","HwyIntraStep_64.block"),
                     os.path.join("CTRAMP","scripts","block","HwyIntraStep.block"))

    elif hostname in ['MODEL2-A','MODEL2-B','MODEL2-C','MODEL2-D','PORMDLPPW01','PORMDLPPW02']:
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
        print "Copying HwyIntraStep_48.block to HwyIntraStep.block"
        shutil.copy2(os.path.join("CTRAMP","scripts","block","HwyIntraStep_48.block"),
                     os.path.join("CTRAMP","scripts","block","HwyIntraStep.block"))

    else:
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

def config_uec(auto_operating_cost, av_ivtt_factor):
    auto_op_cost_float = float(auto_operating_cost)
    av_ivt_factor_float = float(av_ivtt_factor)
    for bookname in ["ModeChoice.xls","TripModeChoice.xls","accessibility_utility.xls"]:
        filepath = os.path.join("CTRAMP","model",bookname)
        shutil.move(filepath, "%s.original" % filepath)

        print "Updating %s" % filepath
        rb = xlrd.open_workbook("%s.original" % filepath, formatting_info=True, on_demand=True)
        wb = xlutils.copy.copy(rb)
        for sheet_num in range(rb.nsheets):
            rs = rb.get_sheet(sheet_num)
            for rownum in range(rs.nrows):
                # print rs.cell(rownum,1)
                if rs.cell(rownum,1).value=='costPerMile':
                    print "  Sheet '%s': replacing costPerMile '%s' -> %.2f" % \
                        (rs.name, rs.cell(rownum,4).value, auto_op_cost_float)
                    wb.get_sheet(sheet_num).write(rownum,4,auto_op_cost_float,
                                                  xlwt.easyxf("align: horiz left"))
                if rs.cell(rownum,1).value=='c_ivt':
                    print "  Sheet '%s': replacing c_ivt '%s' -> %.2f" % \
                        (rs.name, rs.cell(rownum,4).value, rs.cell(rownum,4).value*av_ivt_factor_float)
                    wb.get_sheet(sheet_num).write(rownum,4,rs.cell(rownum,4).value*av_ivt_factor_float,
                                                  xlwt.easyxf("align: horiz left"))

        wb.save(filepath)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = USAGE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("--iter",
                        help="Iteration for which to configure.  If not specified, will configure for pre-run.",
                        type=int, choices=[1,2,3,4,5])

    my_args = parser.parse_args()

    # Figure out the replacements we need to make
    replacements = collections.defaultdict(collections.OrderedDict)
    if my_args.iter == None:
        config_project_dir(replacements)
        config_popsyn_files(replacements)
        config_mobility_params(replacements)
        config_auto_opcost(replacements)
        config_host_ip(replacements)
        config_distribution(replacements)
    else:
        config_shadowprice(my_args.iter, replacements)

    # Go ahead and make the replacements
    for filepath,regex_dict in replacements.iteritems():
        replace_in_file(filepath, regex_dict)
