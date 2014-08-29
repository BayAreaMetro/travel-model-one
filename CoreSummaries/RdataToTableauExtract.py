
USAGE = """
python RdataToTableauExtract.py summary.rdata summary.tde

Extracts the summary table in summary.rdata to the Tableau Data Extract file, summary.tde

"""

# rpy2 requires R_HOME to be set (I used C:\Program Files\R\R-3.1.1)
#      and R_USER to be set (I used lzorn)
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

def read_rdata(rdata_fullpath):
    """
    Returns the pandas DataFrame
    """
    
    # we want forward slashes for R
    rdata_fullpath_forR = rdata_fullpath.replace("\\", "/")
    print "Loading %s" % rdata_fullpath_forR
    
    # read in the data from the R session with python
    r.r("load('%s')" % rdata_fullpath_forR)
    # check that it's there
    print "Dimensions are %s" % str(r.r('dim(active_summary)'))
    
    table_df = com.load_data('active_summary')
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
    print "Wrote %s" % tde_fullpath

    
if __name__ == '__main__':

    optlist, args = getopt.getopt(sys.argv[1:], "")
    if len(args) < 2:
        print USAGE
        sys.exit(2)

    if len(args) > 2:
        print "Concat not implemented yet"
        sys.exit(2)
    
    for rdata_fullpath in args[:-1]:
        if not rdata_fullpath.endswith(".rdata"):
            print "Invalid rdata file [%s]" % rdata_fullpath
            sys.exit(2)
        table_df = read_rdata(rdata_fullpath)
        
    tde_fullpath = args[-1]
    if not tde_fullpath.endswith(".tde"):
        print "Invalid tde file [%s]" % tde_fullpath
        sys.exit(2)
    print tde_fullpath
    
    write_tde(table_df, tde_fullpath)

"""
TODO: clean this up
RUN_NAME_SET = os.environ['RUN_NAME_SET']
RUN_NAMES = RUN_NAME_SET.split()
print "RUN_NAMES = ", str(RUN_NAMES)

ROOT_DIR = r"C:\Users\lzorn\Documents"

run_name = RUN_NAMES[0]
summary_dir = os.path.join(ROOT_DIR, run_name, "summary")
        
# Read the data file
try:
    summary_files = os.listdir(summary_dir)
except:
    # This always causes an exception although it still seems to work... Move on.
    pass

print summary_files
    
for summary_file in summary_files:
    
    if not summary_file.endswith(".rdata"):
        continue
        # pass
        
    print "Extracting from %s" % summary_file
    # read in the data from the R session within python
    rdata_fullpath = os.path.join(summary_dir, summary_file)
    
    # Create the Tableau Data Extract for just this summary
    tde_fullpath = rdata_fullpath.replace(".rdata", ".tde")
    sys.exit(0)
"""