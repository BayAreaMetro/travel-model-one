
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

def config_shadowprice(iter, replacements):
    """
    See USAGE for details.

    Replacements = { filepath -> regex_dict }
    """
    filepath = os.path.join("CTRAMP","runtime","mtcTourBased.properties")
    if iter==1:
        # 4 iterations, no input file
        replacements[filepath]["(\nUsualWorkAndSchoolLocationChoice.ShadowPrice.Input.File[ \t]*=[ \t]*)(\S*)"] = \
            r"\g<1>"        
        replacements[filepath]["(\nUsualWorkAndSchoolLocationChoice.ShadowPricing.MaximumIterations[ \t]*=[ \t]*)(\S*)"] = \
            r"\g<1>4"
    elif iter==2:
        # update to 2 iterations and add input file
        replacements[filepath]["(\nUsualWorkAndSchoolLocationChoice.ShadowPrice.Input.File[ \t]*=[ \t]*)(\S*)"] = \
            r"\g<1>main/ShadowPricing_3.csv"        
        replacements[filepath]["(\nUsualWorkAndSchoolLocationChoice.ShadowPricing.MaximumIterations[ \t]*=[ \t]*)(\S*)"] = \
            r"\g<1>2"
    elif iter==3:
        # update input file
        replacements[filepath]["(\nUsualWorkAndSchoolLocationChoice.ShadowPrice.Input.File[ \t]*=[ \t]*)(\S*)"] = \
            r"\g<1>main/ShadowPricing_5.csv"

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

