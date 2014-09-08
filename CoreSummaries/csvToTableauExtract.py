USAGE = """
python csvToTableauExtract.py [--header "colname1,colname2,..."] [--output output.tde] [--append]
  input_dir1 [input_dir2 input_dir3] output_dir summary.csv

  + Pass --header "colname1,colname2,..." to include column names if they're not included
    in the summary.csv
    
  + Pass --output output.tde to specify an output filename to use.  If none is specified,
    summary.tde will be used (the input file name but with s/csv/tde).

  + Pass --append if the data should be appended to the output tde.  If not passed and
    the file exists, the script will error.
    
Loops through the input dirs (one is ok) and reads the summary.csv within.
Convertes them into a Tableau Data Extract.

Adds an additional column to the resulting output, src, which will contain the input file
source of the data.  Also uses pandas.DataFrame.fillna() to replace NAs with zero, since
Tableau doesn't like them.

"""
import csv, datetime, getopt, os, sys
import dataextract as tde

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



if __name__ == '__main__':

    optlist, args = getopt.getopt(sys.argv[1:], "h:o:a", ['header=','output=','append'])
    if len(args) < 3:
        print USAGE
        sys.exit(2)
    
    arg_header          = None
    arg_tde_filename    = None
    arg_append          = False
    unwinding           = False
    for opt,arg in optlist:
        if opt in ('-h', '--header'):
            arg_header = arg.split(",")
        elif opt in ('-o', '--output'):
            arg_tde_filename = arg
        elif opt in ('-a', '--append'):
            arg_append = True
    
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
    tdefile = tde.Extract(tde_fullpath)

    # Define the columns by the first csv
    csvfile = open(os.path.join(csv_dirpaths[0], csv_filename), 'rb')
    csvReader = csv.reader(csvfile, delimiter=",", quotechar='"')
    if arg_header:
        header = arg_header
    else:
        header = csvReader.next()

    # Step 2: Create the tableDef
    tableDef = tde.TableDefinition()
    old_colnames = []
    colnames_to_types = {}
    new_colnames_to_idx = {}
    for col in header:
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
        if new_colname in ['use','name','path id']:
            colnames_to_types[new_colname] = tde.Type.CHAR_STRING
        elif colname in ['a','b','gl','ft','at','owner','mode']:
            colnames_to_types[new_colname] = tde.Type.INTEGER
        else:
            colnames_to_types[new_colname] = tde.Type.DOUBLE

        tableDef.addColumn(new_colname, colnames_to_types[new_colname])
        # other options: tde.Type.DATE,DOUBLE,INTEGER

    if unwinding:
        # add the time period column
        tableDef.addColumn("timeperiod", tde.Type.CHAR_STRING)
        new_colnames_to_idx["timeperiod"] = len(new_colnames_to_idx)
    # add the src column
    tableDef.addColumn("src", tde.Type.CHAR_STRING)
    new_colnames_to_idx["src"] = len(new_colnames_to_idx)
    
    # print "old_colnames = %s" % str(old_colnames)
    # print "new colnames = %s" % str(new_colnames_to_idx)
    # print colnames_to_types
    csvfile.close()
    
    # Step 3: Creat the table in the image of the tableDef
    if arg_append:
        table = tdefile.openTable('Extract')
    else:
        table = tdefile.addTable('Extract', tableDef)

    # Step 4: Loop through the csv grab all the data, put it into rows
    # and insert the rows in the table
    newrow = tde.Row(tableDef)
    for csv_dirpath in csv_dirpaths:
        csv_fullpath = os.path.join(csv_dirpath, csv_filename)
        
        src = os.path.split(csv_fullpath)[0]   # remove the filename part of the path
        src = os.path.split(src)[0]            # remove the 'summary' part of the path
    
        csvfile = open(csv_fullpath, 'rb')
        csvReader = csv.reader(open(csv_fullpath,'rb'), delimiter=",", quotechar='"')
        
        # make sure the header is consistent
        if arg_header:
            header = arg_header
        else:
            header = csvReader.next()
        header = [col.strip() for col in header]
        assert(header == old_colnames)

        csv_lines_read = 0
        tde_lines_written = 0
        for line in csvReader:
            csv_lines_read += 1
            
            timeperiods = ['huh']
            if unwinding: timeperiods = ['EA','AM','MD','PM','EV']
            
            for timeperiod in timeperiods:
                # set the row items    
                for idx in range(len(header)):
                    colname = header[idx].strip() # strip whitespace

                    # straightforward case
                    if colname in new_colnames_to_idx.keys():
                        col_idx = new_colnames_to_idx[colname]

                        try:
                            if colnames_to_types[colname] == tde.Type.CHAR_STRING:
                                newrow.setCharString(col_idx, str(line[idx]))
                            elif colnames_to_types[colname] == tde.Type.INTEGER:
                                if line[idx]=="":
                                    newrow.setInteger(col_idx,0)
                                else:
                                    newrow.setInteger(col_idx, int(line[idx]))
                            elif colnames_to_types[colname] == tde.Type.DOUBLE:
                                newrow.setDouble(col_idx, float(line[idx]))
                            else:
                                raise
                        except:
                            print "exception!  colname=[%s] val=[%s]" % (colname, str(line[idx]))
                            raise
                            
                    # unwind case
                    else:
                        new_colname = unwind_timeperiods[colname][0]
                        col_tp      = unwind_timeperiods[colname][1]
                        col_idx     = new_colnames_to_idx[new_colname]
                        if col_tp == timeperiod:
                            newrow.setDouble(col_idx, float(line[idx]))

                if unwinding:
                    # and the time period
                    newrow.setCharString(new_colnames_to_idx["timeperiod"], timeperiod)
                # and the src
                newrow.setCharString(new_colnames_to_idx["src"], src)
                table.insert(newrow)
                
                tde_lines_written += 1
        
        csvfile.close()
        print "Read  %6d rows from %s" % (csv_lines_read, csv_fullpath)
        
    # Step 5: Close the tde
    tdefile.close()
    print "Wrote %6d rows to   %s" % (tde_lines_written, tde_fullpath)
