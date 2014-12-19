
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
   + It will be propagated to CTRAMP\model\ModeChoice.xls,  (for costPerMile)
                              CTRAMP\model\TripModeChoice.xls,
                              CTRAMP\model\accessibility_utility.xls
 * Truck Operating Cost (plus RM, Fuel breakdown)
   + Specify the value in INPUT\params.properties
   + It will be propagated to CTRAMP\scripts\block\hwyParam.block
                              

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
        if numsubs != 1:
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

    # put it into the UECs
    config_uec("%.2f" % auto_opc_perfect)

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
    else:
        config_shadowprice(my_args.iter, replacements)

    # Go ahead and make the replacements
    for filepath,regex_dict in replacements.iteritems():
        replace_in_file(filepath, regex_dict)


