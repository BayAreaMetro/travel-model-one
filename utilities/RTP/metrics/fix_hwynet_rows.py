import argparse, csv, shutil, sys

USAGE = """
 python fix_hwynet_rows.py hwynet.csv

 Simple script to look for malformed hwynet.csv by counting commas on each line and fixing rows with too many...

 If issue is found, moves hwynet.csv to hwynet_bad.csv and writes fixed hwynet.csv

 The problem should be fixed in the source network but this enables hwynet.py to run.
"""
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument("net_csv",  metavar="avgload5period_vehclasses.csv", help="Loaded network export with vehicle classes")
    args = parser.parse_args()

    print("Reading {}".format(args.net_csv))
    new_rows   = []
    fixed_rows = 0

    csv_file = open(args.net_csv, 'rb')
    csv_reader = csv.reader(csv_file, delimiter=',')
    col_count = -1
    for row in csv_reader:
        if col_count < 0:
            col_count = len(row)
            print("column count: {}".format(col_count))
            new_rows.append(row)
            continue

        # N columns after cityname are bad -- delete those
        if len(row) > col_count:
            print("=== Found bad row: {}".format(row))
            row = row[:10] + row[48:]
            fixed_rows += 1
            print("=== Fixed row: {}".format(row))
            new_rows.append(row)
        else:
            new_rows.append(row)

    csv_file.close()

    if fixed_rows == 0:
        print("No bad rows found -- nothing to do")
        sys.exit(0)

    # copy the file to bak
    bak_file = args.net_csv[:-4] + "_bak.csv"
    print("Moving {} to {}".format(args.net_csv, bak_file))
    shutil.move(args.net_csv, bak_file)

    print("Writing {} with {} fixed rows out of {}".format(args.net_csv, fixed_rows, len(new_rows)))
    csv_file = open(args.net_csv, "wb")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerows(new_rows)
    csv_file.close()

