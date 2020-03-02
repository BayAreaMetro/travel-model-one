import os, re, sys

import numpy
import pandas

USAGE = """

  python rollupAccessibilities.py dir1 dir2 dir3 dir4 ...

  Rolls up *\OUTPUT\accessibilities\mandatoryAccessibilities.csv and 
           *\OUTPUT\accessibilities\nonMandatoryAccessibilities.csv

  into single files of the same name in .
"""

if __name__ == '__main__':

    initialized      = False
    mandatory_dfs    = None
    nonmandatory_dfs = None
    for rundir in sys.argv[1:]:
        print "Reading %s" % rundir
        mandatory_df    = pandas.read_table(os.path.join(rundir, "OUTPUT/accessibilities", "mandatoryAccessibilities.csv"), sep=",")
        nonmandatory_df = pandas.read_table(os.path.join(rundir, "OUTPUT/accessibilities", "nonMandatoryAccessibilities.csv"), sep=",")

        colnames = list(mandatory_df.columns.values)
        col_rename = {}
        for colname in colnames:
            if colname in ['destChoiceAlt', 'taz', 'subzone']: continue
            col_rename[colname] = rundir + " " + colname

        mandatory_df.rename(columns=col_rename, inplace=True)
        nonmandatory_df.rename(columns=col_rename, inplace=True)
        # mandatory_df['Project ID']    = rundir
        # nonmandatory_df['Project ID'] = rundir

        if not initialized:
            mandatory_dfs       = mandatory_df
            nonmandatory_dfs    = nonmandatory_df
            initialized         = True
        else:
            mandatory_dfs       = pandas.merge(left=   mandatory_dfs, right=   mandatory_df)
            nonmandatory_dfs    = pandas.merge(left=nonmandatory_dfs, right=nonmandatory_df)
            # mandatory_dfs       = pandas.concat([mandatory_dfs, mandatory_df],
            #                                     axis=0, ignore_index=True)
            # nonmandatory_dfs    = pandas.concat([nonmandatory_dfs, nonmandatory_df],
            #                                     axis=0, ignore_index=True)
            pass

    mandatory_dfs.to_csv("mandatoryAccessibilities.csv", index=False, header=True)
    nonmandatory_dfs.to_csv("nonMandatoryAccessibilities.csv", index=False, header=True)
    print "Wrote mandatoryAccessibilities.csv and nonMandatoryAccessibilities.csv"