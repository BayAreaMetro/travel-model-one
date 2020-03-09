USAGE = """

  This script:

  * Reads all_BC_config.xlsx, which should have a worksheet titled BC_config, containing
    one BC_config.csv per row, plus the additional column "Folder Name"
  * Writes the relevant BC_config.csv (if updated) into the [project_folder]\BC_config.csv
  * Writes the relevant BC_config.csv (if updated) into the [project_folder]\OUTPUT\metrics\BC_config.csv
  * Writes a RunCobra.bat file to the local dir for running the actual cobra

"""
import argparse, difflib, os, shutil, sys
import pandas

COBRA_CONFIG_COLUMNS = [
    "Project ID",
    "Project Name",
    "County",
    "Project Type",
    "Project Mode",
    "Capital Costs (millions of $2017)",
    "Annual O&M Costs (millions of $2017)",
    "Farebox Recovery Ratio",
    "Life of Project (years)",
    "base_dir",
    "Compare"]

ALL_METRICS_DIR = "all_metrics"
BATCH_FILE      = "RunCobra.bat"

def save_if_diffs(config_lines, old_file):
    """
    """
    do_write = False
    if os.path.exists(old_file):
        # read the existing
        bc_config_orig = open(old_file, "r")
        bc_config_lines_orig = bc_config_orig.readlines()
        bc_config_orig.close()
        for idx in range(len(bc_config_lines_orig)): bc_config_lines_orig[idx] = bc_config_lines_orig[idx].strip()

        print "Checking if different from previous file [%s]" % old_file
        different = False

        for line in difflib.context_diff(bc_config_lines_orig, bc_config_lines, fromfile=old_file, tofile='BC_config_new.csv'):
            print line
            different = True

        if different:
            print
            print
            print "Differences found => "
            print "  Moving previous file [%s] to [%s.bak]" % (old_file, old_file)
            shutil.move(old_file, "%s.bak" % old_file)
            do_write = True
    else:
        # if it doesn't exist, write this for sure
        do_write = True

    if do_write:
        print "  Writing new file %s" % old_file
        # write it to [project_folder]\BC_config_new.csv
        bc_config_new = open(old_file, "wb")
        for line in bc_config_lines: bc_config_new.write("%s\r\n" % line)
        bc_config_new.close()

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description = USAGE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('cobra_workbook', metavar='all_BC_config.xlsx',
                        type=str, help="Name or path of the excel workbook containing the cobra configuration.")
    my_args = parser.parse_args()

    # read the cobra config
    cobra_config_df = pandas.read_excel(my_args.cobra_workbook, sheetname="BC_config")
    assert("Folder Name" in list(cobra_config_df.columns))

    cobra_batch_lines = ['set COBRA_DIR=%CD%',
                         "",
                         "mkdir %s" % ALL_METRICS_DIR]

    # For each project
    for row in cobra_config_df.iterrows():
        print "====== Processing %s ======" % row[1]["Folder Name"]
        bc_config_lines = []
        for column in COBRA_CONFIG_COLUMNS:

            # no need to write nan for empty
            if column == "base_dir" and pandas.isnull(row[1][column]): continue

            bc_config_lines.append("%s,%s" % (column, str(row[1][column])))

        save_if_diffs(bc_config_lines, os.path.join(row[1]["Folder Name"], "BC_config.csv"))
        save_if_diffs(bc_config_lines, os.path.join(row[1]["Folder Name"], "OUTPUT", "metrics", "BC_config.csv"))

        cobra_batch_lines.append('python "%%COBRA_DIR%%\RunResults.py" "%s" %s' % (os.path.join(row[1]["Folder Name"], "OUTPUT", "metrics"), ALL_METRICS_DIR))

    # write the batch dir
    cobra_batch_lines.append("")
    cobra_batch_lines.append(":rollup")
    cobra_batch_lines.append("cd %s" % ALL_METRICS_DIR)
    cobra_batch_lines.append('python "%%COBRA_DIR%%\\rollupAllProjects.py"' % ())
    cobra_batch_lines.append("cd ..")
    print "========================"
    batch_file = open(BATCH_FILE, "wb")
    for line in cobra_batch_lines: batch_file.write("%s\r\n" % line)
    batch_file.close()
    print "Wrote %s" % BATCH_FILE

