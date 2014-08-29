import csv, datetime, os
import dataextract as tde

# Step 1: Create the Extract file and open the csv
extractfile = r"C:\Users\lzorn\Documents\2010_04_ZZZ\summary\avgload5period.tde"
if os.path.isfile(extractfile):
    os.remove(extractfile)
    
tdefile = tde.Extract(extractfile)

csvReader = csv.reader(open(r"C:\Users\lzorn\Documents\2010_04_ZZZ\avgload5period.csv",'rb'), delimiter=",", quotechar='"')
header = csvReader.next()

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
    else:
        new_colname = colname

    # if the new_colname is already taken care of, we're done
    if new_colname in colnames_to_types.keys():
        continue

    new_colnames_to_idx[new_colname] = len(new_colnames_to_idx)
    # figure out data type
    if new_colname in ['use']:
        colnames_to_types[new_colname] = tde.Type.CHAR_STRING
    elif colname in ['a','b','gl','ft','at']:
        colnames_to_types[new_colname] = tde.Type.INTEGER
    else:
        colnames_to_types[new_colname] = tde.Type.DOUBLE

    tableDef.addColumn(new_colname, colnames_to_types[new_colname])
    # other options: tde.Type.DATE,DOUBLE,INTEGER
# add the time period column
tableDef.addColumn("timeperiod", tde.Type.CHAR_STRING)
new_colnames_to_idx["timeperiod"] = len(new_colnames_to_idx)
print old_colnames
print new_colnames_to_idx

# Step 3: Creat the table in the image of the tableDef
table = tdefile.addTable('Extract', tableDef)

# Step 4: Loop through the csv grab all the data, put it into rows
# and insert the rows in the table
newrow = tde.Row(tableDef)
for line in csvReader:
    for timeperiod in ['EA','AM','MD','PM','EV']:
        # set the row items    
        for idx in range(len(header)):
            colname = header[idx].strip() # strip whitespace

            # straightforward case
            if colname in new_colnames_to_idx.keys():
                col_idx = new_colnames_to_idx[colname]
            
                if colnames_to_types[colname] == tde.Type.CHAR_STRING:
                    newrow.setCharString(col_idx, str(line[idx]))
                elif colnames_to_types[colname] == tde.Type.INTEGER:
                    newrow.setInteger(col_idx, int(line[idx]))
                elif colnames_to_types[colname] == tde.Type.DOUBLE:
                    newrow.setDouble(col_idx, float(line[idx]))
                else:
                    raise
            # unwind case
            else:
                new_colname = unwind_timeperiods[colname][0]
                col_tp      = unwind_timeperiods[colname][1]
                col_idx     = new_colnames_to_idx[new_colname]
                if col_tp == timeperiod:
                    newrow.setDouble(col_idx, float(line[idx]))

        # and the time period
        newrow.setCharString(new_colnames_to_idx["timeperiod"], timeperiod)
        table.insert(newrow)

# Step 5: Close the tde
tdefile.close()
