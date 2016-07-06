
USAGE = """
python dataToTableauExtract.py [--append] [--timeperiod code] [--join join.csv] [--output output.tde] 
  input_dir1 [input_dir2 input_dir3] output_dir summary.(rdata|dbf)

  + Pass --output output.tde to specify an output filename to use.  If none is specified,
    summary.tde will be used (the input file name but with s/csv/tde).

  + Pass --join join.csv to join the data to a csv.  Will join on common column names.

  + Pass --append if the data should be appended to the output tde.  If not passed and
    the file exists, the script will error

Loops through the input dirs (one is ok) and reads the summary.(rdata|dbf) within.
Converts them into a Tableau Data Extract.

Adds an additional column to the resulting output, `src`, which will contain the input file
source of the data.  If the file "ScenarioKey.csv" exists in the current working directory,
and it contains a column mapping `src` to `Scenario`, then the first level dir will be used to
add another human readable column name.  (e.g. if '2010_04_ZZZ\\blah' is an input dir,
then the mapping needs to map '2010_04_ZZZ' to a scenario name.)

Also uses pandas.DataFrame.fillna() to replace NAs with zero, since Tableau doesn't like them.

Outputs summary.tde (named the same as the input file but with tde as the suffix) into output_dir.

"""

# rpy2 requires R_HOME to be set (I used C:\Program Files\R\R-3.1.1)
#      and R_USER to be set (I used lzorn)
import csv
import dataextract as tde
import pandas
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
    
def read_rdata(rdata_fullpath):
    """
    Returns the pandas DataFrame
    """
    from rpy2.robjects import pandas2ri, r
    pandas2ri.activate()

    # we want forward slashes for R
    rdata_fullpath_forR = rdata_fullpath.replace("\\", "/")
    print "Loading %s" % rdata_fullpath_forR
    
    # read in the data from the R session with python
    r['load'](rdata_fullpath_forR)
    # check that it's there
    table_df = pandas2ri.ri2py(r['model_summary'])

    # fillna
    for col in table_df.columns:
        nullcount = sum(pandas.isnull(table_df[col]))
        if nullcount > 0: print "  Found %5d NA values in column %s" % (nullcount, col)
    table_df = table_df.fillna(0)
    for col in table_df.columns:
        nullcount = sum(pandas.isnull(table_df[col]))
        if nullcount > 0: print "  -> Found %5d NA values in column %s" % (nullcount, col)
    
    print "Read %d lines from %s" % (len(table_df), rdata_fullpath)
    return table_df

def read_dbf(dbf_fullpath):
    """
    Returns the pandas DataFrame
    """
    import pysal
    dbfin = pysal.open(dbf_fullpath)
    vars = dbfin.header
    data = dict([(var, dbfin.by_col(var)) for var in vars])

    table_df = pandas.DataFrame(data)

    print "Read %d lines from %s" % (len(table_df), dbf_fullpath)

    return table_df

def write_tde(table_df, tde_fullpath, arg_append):
    """
    Writes the given pandas dataframe to the Tableau Data Extract given by tde_fullpath
    """
    if arg_append and not os.path.isfile(tde_fullpath):
        print "Couldn't append -- file doesn't exist"
        arg_append = False

    # Remove it if already exists
    if not arg_append and os.path.exists(tde_fullpath):
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
    if arg_append:
        tde_table = tdefile.openTable('Extract')
    else:
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

    optlist, args = getopt.getopt(sys.argv[1:], "o:at:j:",['output=','append','timeperiod=','join='])

    data_filename       = args[-1]
    arg_tde_filename    = None
    arg_append          = False
    arg_timeperiod      = None    
    arg_join            = []
    for opt,arg in optlist:
        if opt in ('-o', '--output'):
            arg_tde_filename = arg
        elif opt in ('-a', '--append'):
            arg_append = True
        elif opt in ('-t', '--timeperiod'):
            arg_timeperiod = arg
        elif opt in ('-j', '--join'):
            arg_join.append(arg)

    if len(args) < 3:
        print USAGE
        print sys.argv
        sys.exit(2)
    

    if not data_filename.endswith(".rdata") and not data_filename.endswith(".dbf"):
        print USAGE
        print "Invalid data filename [%s]" % data_filename
        sys.exit(2)
    
    # input path checking
    for data_dirpath in args[:-2]:
        # check it's a path
        if not os.path.isdir(data_dirpath):
            print USAGE
            print "Invalid input directory [%s]" % data_dirpath
            sys.exit(2)
        # check it has summary.data
        if not os.path.isfile(os.path.join(data_dirpath, data_filename)):
            print USAGE
            print "File doesn't exist: [%s]" % os.path.join(data_dirpath, data_filename)
            sys.exit(2)
        # print "Valid input data_dirpath [%s]" % data_dirpath
    
    # output path checking
    tde_dirpath = args[-2]
    if not os.path.isdir(tde_dirpath):
        print USAGE
        print "Invalid output directory [%s]" % tde_dirpath
        sys.exit(2)

    # print "Valid output tde_dirpath [%s]" % tde_dirpath
    if arg_tde_filename:
        tde_filename = arg_tde_filename
    else:
        tde_filename = data_filename[:data_filename.rfind(".")] + ".tde"
    # print "Will write to [%s]" % os.path.join(tde_dirpath, tde_filename)
    # print
    
    src_to_scenario = read_scenario_key()

    # checking done -- do the job
    full_table_df = None
    set_fulltable = False
    for data_dirpath in args[:-2]:
        data_fullpath = os.path.join(data_dirpath, data_filename)
        if data_filename.endswith(".rdata"):
            table_df = read_rdata(data_fullpath)
        else:
            table_df = read_dbf(data_fullpath)

        # read join table
        for join_table_file in arg_join:
            join_df = pandas.read_csv(join_table_file)
            # hack -- the csvs have lowercase 'mode' but the dbfs have uppercase
            if 'MODE' in table_df.columns and 'mode' in join_df.columns:
                join_df.rename(columns={'mode':'MODE'}, inplace=True)
            table_df = pandas.merge(table_df, join_df, how='left')

        # add the new column `src`
        src = os.path.split(data_fullpath)[0] # remove the filename part of the path
        (head,tail) = os.path.split(src)      # remove one more dir from path (e.g. core_summaries)
        src = head
        (head,tail) = os.path.split(src)      # src is tail now
        # this is a bit of a hack... figure out a better way
        if tail != "OUTPUT":
            src = tail
        else:
            (head,tail) = os.path.split(head)
            src=tail
        table_df['src'] = src
        print "  - src is [%s]" % src

        # add the new column `Scenario`
        if src_to_scenario:
            scenario = 'unknown'
            if src in src_to_scenario:
                scenario = src_to_scenario[src]
            print "  - Scenario is [%s]" % scenario
            table_df['Scenario'] = scenario

        # add time period
        if arg_timeperiod:
            table_df['timeperiod'] = arg_timeperiod
            print "  - timeperiod is [%s]" % arg_timeperiod

        if set_fulltable==False: # it doesn't like checking if a dataFrame is none
            full_table_df = table_df
            set_fulltable = True
        else:
            full_table_df = full_table_df.append(table_df)
        print "Full table has length %d" % len(full_table_df)
        
        # This takes too long... Just forget it
        # AutoTripsVMT_personsHomeWork.rdata shouldn't be done
        if len(full_table_df) > 5000000:
            print "Table is too long.  Skipping"
            sys.exit(0)
    
    write_tde(full_table_df, os.path.join(tde_dirpath, tde_filename), arg_append)
