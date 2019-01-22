USAGE = """
python csvToTableauExtract.py [--header "colname1,colname2,..."] [--output output.tde] [--join join.csv] [--append]
  input_dir1 [input_dir2 input_dir3] output_dir summary.csv

  + Pass --header "colname1,colname2,..." to include column names if they're not included
    in the summary.csv
    
  + Pass --output output.tde to specify an output filename to use.  If none is specified,
    summary.tde will be used (the input file name but with s/csv/tde).

  + Pass --join join.csv to join the data to a csv.  Will join on common column names.
  
  + Pass --append if the data should be appended to the output tde.  If not passed and
    the file exists, the script will error.
    
Loops through the input dirs (one is ok) and reads the summary.csv within.
Convertes them into a Tableau Data Extract.

Adds an additional column to the resulting output, `src`, which will contain the input file
source of the data.  If the file "ScenarioKey.csv" exists in the current working directory,
and it contains a column mapping `src` to `Scenario`, then the first level dir will be used to
add another human readable column name.  (e.g. if '2010_04_ZZZ\blah' is an input dir,
then the mapping needs to map '2010_04_ZZZ' to a scenario name.)

Also uses pandas.DataFrame.fillna() to replace NAs with zero, since Tableau doesn't like them.

Modified to latest Tableau python API as of 2/15/18

"""
import csv, datetime, itertools, getopt, os, sys
import pandas
from tableausdk import * 
from tableausdk.Extract import * 

ExtractAPI.initialize()

# create a dict for the field maps
# Define type maps
# Caveat: I am not including all of the possibilities here
fieldMap = { 
     'float64' :     Type.DOUBLE,
     'float32' :     Type.DOUBLE,
     'int64' :       Type.DOUBLE,
     'int32' :       Type.DOUBLE,
     'object':       Type.UNICODE_STRING,
     'bool' :        Type.BOOLEAN
 }

unwind_timeperiods = {'cspdEA':['cspd','EA'],
                      'cspdAM':['cspd','AM'],
                      'cspdMD':['cspd','MD'],
                      'cspdPM':['cspd','PM'],
                      'cspdEV':['cspd','EV'],
                      'volEA_tot':['vol_tot','EA'],
                      'volAM_tot':['vol_tot','AM'],
                      'volMD_tot':['vol_tot','MD'],
                      'volPM_tot':['vol_tot','PM'],
                      'volEV_tot':['vol_tot','EV'],
                      'ctimEA':['ctim','EA'],
                      'ctimAM':['ctim','AM'],
                      'ctimMD':['ctim','MD'],
                      'ctimPM':['ctim','PM'],
                      'ctimEV':['ctim','EV'],
                      'vcEA':['vc','EA'],
                      'vcAM':['vc','AM'],
                      'vcMD':['vc','MD'],
                      'vcPM':['vc','PM'],
                      'vcEV':['vc','EV'],
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

if __name__ == '__main__':

    optlist, args = getopt.getopt(sys.argv[1:], "h:o:j:a", ['header=','output=','join=','append'])
    if len(args) < 3:
        print USAGE
        sys.exit(2)
    
    arg_header          = None
    arg_tde_filename    = None
    arg_append          = False
    arg_join            = []
    unwinding           = False
    for opt,arg in optlist:
        if opt in ('-h', '--header'):
            arg_header = arg.split(",")
        elif opt in ('-o', '--output'):
            arg_tde_filename = arg
        elif opt in ('-a', '--append'):
            arg_append = True
        elif opt in ('-j', '--join'):
            arg_join.append(arg)
    
    csv_filename = args[-1]
    if not csv_filename.endswith(".csv"):
        print USAGE
        print "Invalid csv filename [%s]" % csv_filename
        sys.exit(2)
    
    # input path checking
    csv_dirpaths = args[:-2]
    for csv_dirpath in csv_dirpaths:
        # check it's a path
        if not os.path.isdir(csv_dirpath):
            print USAGE
            print "Invalid input directory [%s]" % csv_dirpath
            sys.exit(2)
        # check it has summary.csv
        if not os.path.isfile(os.path.join(csv_dirpath, csv_filename)):
            print USAGE
            print "File doesn't exist: [%s]" % os.path.join(csv_dirpath, csv_filename)
            sys.exit(2)
        # print "Valid input csv_dirpath [%s]" % csv_dirpath
    
    # output path checking
    tde_dirpath = args[-2]
    if not os.path.isdir(tde_dirpath):
        print USAGE
        print "Invalid output directory [%s]" % tde_dirpath
        sys.exit(2)

    src_to_scenario = read_scenario_key()

    # print "Valid output tde_dirpath [%s]" % tde_dirpath
    if arg_tde_filename:
        tde_filename = arg_tde_filename
    else:
        tde_filename = csv_filename.replace(".csv", ".tde")    
    # print "Will write to [%s]" % os.path.join(tde_dirpath, tde_filename)
    # print
  
  
    # Step 1: Create the Extract file and open the csv
    tde_fullpath = os.path.join(tde_dirpath, tde_filename)
    # if the file doesn't exist, revoke the append
    if arg_append and not os.path.isfile(tde_fullpath):
        print "Couldn't append -- file doesn't exist."
        arg_append = False
    if not arg_append and os.path.isfile(tde_fullpath):
        os.remove(tde_fullpath)    
    new_extract = Extract(tde_fullpath)

    # Define the columns by the first csv
    table_df = pandas.read_csv(os.path.join(csv_dirpaths[0], csv_filename), names=arg_header)
    for join_table_file in arg_join:
        join_df = pandas.read_csv(join_table_file)
        table_df = pandas.merge(table_df, join_df, how='left')

    # Step 2: Create the tableDef
    table_definition = TableDefinition()
    old_colnames = []
    colnames_to_types = {}
    new_colnames_to_idx = {}
    for (col,dtype) in itertools.izip(table_df.columns, table_df.dtypes):
        colname = col.strip() # strip whitespace
        old_colnames.append(colname)

        # unwinding this?
        if colname in unwind_timeperiods.keys():
            new_colname = unwind_timeperiods[colname][0]
            unwinding = True
        else:
            new_colname = colname

        # if the new_colname is already taken care of, we're done
        if new_colname in colnames_to_types.keys():
            continue

        new_colnames_to_idx[new_colname] = len(new_colnames_to_idx)
        # figure out data type
        colnames_to_types[new_colname] = fieldMap[str(dtype)]
        table_definition.addColumn(new_colname, colnames_to_types[new_colname])

    if unwinding:
        # add the time period column
        table_definition.addColumn("timeperiod", Type.UNICODE_STRING)
        new_colnames_to_idx["timeperiod"] = len(new_colnames_to_idx)
    # add the src column
    table_definition.addColumn("src", Type.UNICODE_STRING)
    new_colnames_to_idx["src"] = len(new_colnames_to_idx)
    table_definition.addColumn("Scenario", Type.UNICODE_STRING)
    new_colnames_to_idx["Scenario"] = len(new_colnames_to_idx)
    
    # print "old_colnames = %s" % str(old_colnames)
    # print "new colnames = %s" % str(new_colnames_to_idx)
    # print colnames_to_types
    
    # Step 3: Creat the table in the image of the tableDef
    if arg_append:
        new_table = new_extract.openTable('Extract')
    else:
        new_table = new_extract.addTable('Extract', table_definition)

    # Step 4: Loop through the csv grab all the data, put it into rows
    # and insert the rows in the table
    new_row = Row(table_definition)
    for csv_dirpath in csv_dirpaths:
        csv_fullpath = os.path.join(csv_dirpath, csv_filename)

        # add the new column `src`
        src = os.path.split(csv_fullpath)[0] # remove the filename part of the path
        tail = ""
        while tail in ["", "trn", "iter3", "hwy", "OUTPUT"]:
            (src,tail) = os.path.split(src)      # remove one more dir from path (e.g. core_summaries)
        print "tail=[%s] src=[%s]" % (tail,src)
        src = tail
        table_df['src'] = src
        print "  - src is [%s]" % src

        scenario = 'unknown'
        # add the new column `Scenario`
        if src_to_scenario and src in src_to_scenario:
            scenario = src_to_scenario[src]
    
        table_df = pandas.read_csv(csv_fullpath, names=arg_header)
        for join_table_file in arg_join:
            join_df = pandas.read_csv(join_table_file)
            table_df = pandas.merge(table_df, join_df, how='left')
        
        # fillna - tableau doesn't like them
        for col in table_df.columns:
            nullcount = sum(pandas.isnull(table_df[col]))
            if nullcount > 0: print "  Found %5d NA values in column %s" % (nullcount, col)
        table_df = table_df.fillna(0)
        for col in table_df.columns:
            nullcount = sum(pandas.isnull(table_df[col]))
            if nullcount > 0: print "  -> Found %5d NA values in column %s" % (nullcount, col)
                
        # make sure the header is consistent
        header = [col.strip() for col in table_df.columns]
        # if header != old_colnames:
        #     print header
        #     print old_colnames
        # assert(header == old_colnames)

        csv_lines_read = 0
        tde_lines_written = 0
        for count, line in table_df.iterrows():
            csv_lines_read += 1
            
            timeperiods = ['huh']
            if unwinding: timeperiods = ['EA','AM','MD','PM','EV']
            
            for timeperiod in timeperiods:
                # set the row items    
                for idx in range(len(table_df.columns)):
                    orig_colname = table_df.columns[idx]
                    colname = orig_colname.strip() # strip whitespace

                    # straightforward case
                    if colname in new_colnames_to_idx.keys():
                        col_idx = new_colnames_to_idx[colname]

                        try:
                            if colnames_to_types[colname] == Type.UNICODE_STRING:
                                new_row.setString(col_idx, str(line[orig_colname]))
                            elif colnames_to_types[colname] == Type.INTEGER:
                                new_row.setInteger(col_idx, int(line[orig_colname]))
                            elif colnames_to_types[colname] == Type.DOUBLE:
                                new_row.setDouble(col_idx, float(line[orig_colname]))
                            else:
                                raise
                        except:
                            print "line = ", line
                            print "exception!  colname=[%s] val=[%s]" % (colname, str(line[orig_colname]))
                            raise
                            
                    # unwind case
                    else:
                        new_colname = unwind_timeperiods[colname][0]
                        col_tp      = unwind_timeperiods[colname][1]
                        col_idx     = new_colnames_to_idx[new_colname]
                        if col_tp == timeperiod:
                            new_row.setDouble(col_idx, float(line[orig_colname]))

                if unwinding:
                    # and the time period
                    new_row.setString(new_colnames_to_idx["timeperiod"], timeperiod)
                # and the src
                new_row.setString(new_colnames_to_idx["src"], src)
                new_row.setString(new_colnames_to_idx["Scenario"], scenario)
                new_table.insert(new_row)
                
                tde_lines_written += 1
        
        print "Read  %6d rows from %s" % (csv_lines_read, csv_fullpath)
        
    # Step 5: Close the tde
    new_extract.close()
    print "Wrote %6d rows to   %s" % (tde_lines_written, tde_fullpath)
	
ExtractAPI.cleanup()	
