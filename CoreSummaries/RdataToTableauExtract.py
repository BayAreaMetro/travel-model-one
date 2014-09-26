
USAGE = """
python RdataToTableauExtract.py input_dir1 [input_dir2 input_dir3] output_dir summary.rdata

Loops through the input dirs (one is ok) and reads the summary.rdata within.
Convertes them into a Tableau Data Extract.

Adds an additional column to the resulting output, `src`, which will contain the input file
source of the data.  If the file "ScenarioKey.csv" exists in the current working directory,
and it contains a column mapping `src` to `Scenario`, then the first level dir will be used to
add another human readable column name.  (e.g. if '2010_04_ZZZ\blah' is an input dir,
then the mapping needs to map '2010_04_ZZZ' to a scenario name.)

Also uses pandas.DataFrame.fillna() to replace NAs with zero, since Tableau doesn't like them.

Outputs summary.tde (named the same as summary.rdata but with s/rdata/tde) into output_dir.

"""

# rpy2 requires R_HOME to be set (I used C:\Program Files\R\R-3.1.1)
#      and R_USER to be set (I used lzorn)
import csv
import dataextract as tde
import pandas as pd
import pandas.rpy.common as com
from rpy2 import robjects as r
import getopt
import os
import sys
from datetime import datetime

# create a dict for the field maps
# Define type maps
# Caveat: I am not including all of the possibilities here
fieldMap = { 
    'float64' :     tde.Type.DOUBLE,
    'float32' :     tde.Type.DOUBLE,
    'int64' :       tde.Type.DOUBLE,
    'int32' :       tde.Type.DOUBLE,
    'object':       tde.Type.UNICODE_STRING,
    'bool' :        tde.Type.BOOLEAN
}

def read_scenario_key():
    """
    Reads the scenario key from "ScenarioKey.csv"
    Returns dictionary of src -> scenario or None if nothing valid found
    """
    SCENARIO_KEY_FILENAME = "ScenarioKey.csv"
    if not os.path.exists(SCENARIO_KEY_FILENAME):
        print("File [%s] does not exist.  No mapping from src to Scenario." % SCENARIO_KEY_FILENAME)
        return None
    
    csv_reader = csv.DictReader(open(SCENARIO_KEY_FILENAME))
    src_to_scenario = {}
    for row in csv_reader:
        if 'src' not in row:
            print("File [%s] does not have 'src' column: %s.  No mapping from src to Scenario" %
                  (SCENARIO_KEY_FILENAME, str(row)))
            return None
        if 'Scenario' not in row:
            print("File [%s] does not have 'Scenario' column: %s.  No mapping from src to Scenario" %
                  (SCENARIO_KEY_FILENAME, str(row)))
            return None
        src_to_scenario[row['src']] = row['Scenario']
        print("Mapping src [%s] to Scenario [%s]" % (row['src'], row['Scenario']))
    return src_to_scenario
    
def read_rdata(rdata_fullpath, src_to_scenario):
    """
    Returns the pandas DataFrame
    """
    
    # we want forward slashes for R
    rdata_fullpath_forR = rdata_fullpath.replace("\\", "/")
    # print "Loading %s" % rdata_fullpath_forR
    
    # read in the data from the R session with python
    r.r("load('%s')" % rdata_fullpath_forR)
    # check that it's there
    # print "Dimensions are %s" % str(r.r('dim(model_summary)'))
    
    table_df = com.load_data('model_summary')
    # add the new column `src`
    src = os.path.split(rdata_fullpath)[0] # remove the filename part of the path
    (head,tail) = os.path.split(src)       # remove other tails from path
    while head != "":
        src = head
        (head,tail) = os.path.split(src)
    table_df['src'] = src

    # add the new column `Scenario`
    if src_to_scenario:
        if src in src_to_scenario:
            table_df['Scenario'] = src_to_scenario[src]
        else:
            table_df['Scenario'] = 'unknown'

    print "Read %d lines from %s" % (len(table_df), rdata_fullpath)

    # fillna
    for col in table_df.columns:
        nullcount = sum(pd.isnull(table_df[col]))
        if nullcount > 0: print "  Found %5d NA values in column %s" % (nullcount, col)
    table_df = table_df.fillna(0)
    for col in table_df.columns:
        nullcount = sum(pd.isnull(table_df[col]))
        if nullcount > 0: print "  -> Found %5d NA values in column %s" % (nullcount, col)
        return table_df

def write_tde(table_df, tde_fullpath):
    """
    Writes the given pandas dataframe to the Tableau Data Extract given by tde_fullpath
    """
    # Remove it if already exists
    if os.path.exists(tde_fullpath):
        os.remove(tde_fullpath)
    tdefile = tde.Extract(tde_fullpath)

    # define the table definition
    table_def = tde.TableDefinition()
    
    # create a list of column names
    colnames = table_df.columns
    # create a list of column types
    coltypes = table_df.dtypes

    # for each column, add the appropriate info the Table Definition
    for col_idx in range(0, len(colnames)):
        cname = colnames[col_idx]
        ctype = fieldMap[str(coltypes[col_idx])]
        table_def.addColumn(cname, ctype)        

    # create the extract from the Table Definition
    tde_table = tdefile.addTable('Extract', table_def)
    row = tde.Row(table_def)

    for r in range(0, table_df.shape[0]):
        for c in range(0, len(coltypes)):
            if str(coltypes[c]) == 'float64':
                row.setDouble(c, table_df.iloc[r,c])
            elif str(coltypes[c]) == 'float32':
                row.setDouble(c, table_df.iloc[r,c])
            elif str(coltypes[c]) == 'int64':
                row.setDouble(c, table_df.iloc[r,c])   
            elif str(coltypes[c]) == 'int32':
                row.setDouble(c, table_df.iloc[r,c])
            elif str(coltypes[c]) == 'object':
                row.setString(c, table_df.iloc[r,c]) 
            elif str(coltypes[c]) == 'bool':
                row.setBoolean(c, table_df.iloc[r,c])
            else:
                row.setNull(c)
        # insert the row
        tde_table.insert(row)

    tdefile.close()
    print "Wrote %d lines to %s" % (len(table_df), tde_fullpath)

    
if __name__ == '__main__':

    optlist, args = getopt.getopt(sys.argv[1:], "")
    if len(args) < 3:
        print USAGE
        sys.exit(2)
    
    rdata_filename = args[-1]
    if not rdata_filename.endswith(".rdata"):
        print USAGE
        print "Invalid rdata filename [%s]" % rdata_filename
        sys.exit(2)
    
    # input path checking
    for rdata_dirpath in args[:-2]:
        # check it's a path
        if not os.path.isdir(rdata_dirpath):
            print USAGE
            print "Invalid input directory [%s]" % rdata_dirpath
            sys.exit(2)
        # check it has summary.rdata
        if not os.path.isfile(os.path.join(rdata_dirpath, rdata_filename)):
            print USAGE
            print "File doesn't exist: [%s]" % os.path.join(rdata_dirpath, rdata_filename)
            sys.exit(2)
        # print "Valid input rdata_dirpath [%s]" % rdata_dirpath
    
    # output path checking
    tde_dirpath = args[-2]
    if not os.path.isdir(tde_dirpath):
        print USAGE
        print "Invalid output directory [%s]" % tde_dirpath
        sys.exit(2)

    # print "Valid output tde_dirpath [%s]" % tde_dirpath
    tde_filename = rdata_filename.replace(".rdata", ".tde")    
    # print "Will write to [%s]" % os.path.join(tde_dirpath, tde_filename)
    # print
    
    src_to_scenario = read_scenario_key()
    
    # checking done -- do the job
    full_table_df = None
    set_fulltable = False
    for rdata_dirpath in args[:-2]:
        table_df = read_rdata(os.path.join(rdata_dirpath, rdata_filename), src_to_scenario)
        if set_fulltable==False: # it doesn't like checking if a dataFrame is none
            full_table_df = table_df
            set_fulltable = True
        else:
            full_table_df = full_table_df.append(table_df)
    
    write_tde(full_table_df, os.path.join(tde_dirpath, tde_filename))
