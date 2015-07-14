
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
 * Auto Operating Cost
   + Specify the value in INPUT\params.properties
   + It will be propagated to CTRAMP\scripts\block\hwyParam.block,
                              CTRAMP\runtime\accessibilities.properties (new!),
                              CTRAMP\runtime\mtcTourBased.properties (new!)
   + It will be propagated to CTRAMP\model\ModeChoice.xls,  (for costPerMile)
                              CTRAMP\model\TripModeChoice.xls,
                              CTRAMP\model\accessibility_utility.xls
 * Truck Operating Cost
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
     * 'MODEL2-A', 'MODEL2-C','MODEL2-D': single machine setup with
        48 Cube Voyager processes available
        48 threads for accessibilities
        24 threads for core
     * 'MAINMODEL': multiple machine setup

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

    match           = re.search("\nAutoOperatingCost[ \t]*=[ \t]*(\S*)[ \t]*", myfile_contents)
    if match == None:
        print "Couldn't find AutoOperatingCost in %s" % params_filename
        sys.exit(2)

    # it's a string
    auto_operating_cost = match.group(1)

    # put it into the CTRAMP\scripts\block\hwyParam.block
    filepath = os.path.join("CTRAMP","scripts","block","hwyParam.block")
    replacements[filepath]["(\nAUTOOPCOST[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % auto_operating_cost

    filepath = os.path.join("CTRAMP","runtime","accessibilities.properties")
    replacements[filepath]["(\nAuto.Operating.Cost[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % auto_operating_cost

    filepath = os.path.join("CTRAMP","runtime","mtcTourBased.properties")
    replacements[filepath]["(\nAuto.Operating.Cost[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % auto_operating_cost

    # put it into the UECs
    config_uec(auto_operating_cost)

    # truck!
    match           = re.search("\TruckOperatingCost[ \t]*=[ \t]*(\S*)[ \t]*", myfile_contents)
    if match == None:
        print "Couldn't find TruckOperatingCost in %s" % params_filename
        sys.exit(2)

    # it's a string
    truck_operating_cost = match.group(1)

    # put it into the CTRAMP\scripts\block\hwyParam.block
    filepath = os.path.join("CTRAMP","scripts","block","hwyParam.block")
    replacements[filepath]["(\nTRUCKOPCOST[ \t]*=[ \t]*)(\S*)"] = r"\g<1>%s" % truck_operating_cost

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
    if hostname == 'MAINMODEL':
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

    elif hostname in ['MODEL2-A','MODEL2-C','MODEL2-D']:
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
    elif iter==3:
        # update input file
        replacements[filepath]["(\n)(#?)(UsualWorkAndSchoolLocationChoice.ShadowPrice.Input.File[ \t]*=[ \t]*)(\S*)"] = \
            r"\g<1>\g<3>main/ShadowPricing_5.csv"

def config_uec(auto_operating_cost):
    auto_op_cost_float = float(auto_operating_cost)
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
        wb.save(filepath)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = USAGE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("--iter",
                        help="Iteration for which to configure.  If not specified, will configure for pre-run.",
                        type=int, choices=[1,2,3])

    my_args = parser.parse_args()
    
    # Figure out the replacements we need to make
    replacements = collections.defaultdict(collections.OrderedDict)
    if my_args.iter == None:
        config_project_dir(replacements)
        config_popsyn_files(replacements)
        config_auto_opcost(replacements)
        config_host_ip(replacements)
        config_distribution(replacements)
    else:
        config_shadowprice(my_args.iter, replacements)

    # Go ahead and make the replacements
    for filepath,regex_dict in replacements.iteritems():
        replace_in_file(filepath, regex_dict)


