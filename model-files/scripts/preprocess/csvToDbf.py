USAGE="""

Quick script to convert csv to dbf file since Cube is unfriendly about csvs.

Goes through file twice, the first time to figure out types.

Try assuming ints, then floats, then strings.

"""
import dbfpy3
import argparse,collections,csv,os,sys

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument("input_csv",  metavar="input.csv",   help="Input csv file to convert")
    parser.add_argument("output_dbf", metavar="output.dbf",  help="Output dbf file")

    args = parser.parse_args()

    csvfile   = open(args.input_csv)
    csvreader = csv.reader(csvfile)
    columns   = collections.OrderedDict()  # colname => [dbf_colname, "C", len1, len2]
    col_list  = []
    for row in csvreader:
        # header row
        if len(columns) == 0:
            col_list = row
            for colname in row:
                dbf_colname = colname[:10].upper()
                if len(colname) > 10: print("Truncating column {} to {}".format(colname, dbf_colname))
                columns[colname] = ["N", dbf_colname, 10] # try int first
            continue

        # subsequent rows
        for col_idx in range(len(row)):
            colname = col_list[col_idx]
            dbf_colname = columns[colname][1]

            # do we think it's an int?  try it
            if columns[colname][0] == "N" and len(columns[colname])==3:
                try:
                    val_int = int(row[col_idx])
                except:
                    # upgrade to float
                    columns[colname].append(5)

            # do we think it's a float? try it
            if columns[colname][0] == "N" and len(columns[colname])==4:
                try:
                    val_float = float(row[col_idx])
                except:
                    # upgrade to string
                    columns[colname] = ["C", dbf_colname, 1]

            # do we think it's a string? make sure it's long enough
            if columns[colname][0] == "C":
                columns[colname][2] = max(columns[colname][2], len(row[col_idx])+2)
    csvfile.close()
    print("Read {} and determined dbf columns:".format(args.input_csv))

    # create the dbf
    new_dbf = dbfpy3.dbf.Dbf(args.output_dbf, new=True)

    for col in columns.keys():
        # print("Adding field {} : {}".format(col, columns[col]))
        new_dbf.add_field(columns[col])

    csvfile   = open(args.input_csv)
    csvreader = csv.reader(csvfile)
    header    = False
    for row in csvreader:
        # skip header
        if not header:
            header = True
            continue

        rec = new_dbf.new()
        for col_idx in range(len(row)):
            colname = col_list[col_idx]
            if columns[colname][0] == "N" and len(columns[colname]) == 3:
                rec[ columns[colname][1] ] = int(row[col_idx])
            elif columns[colname][0] == "N":
                rec[ columns[colname][1] ] = float(row[col_idx])
            else:
                rec[ columns[colname][1] ] = row[col_idx]
        # print("rec={}".format(rec))
        new_dbf.append(rec)

    csvfile.close()
    print(new_dbf)
    new_dbf.close()

    print("Wrote {}".format(args.output_dbf))
