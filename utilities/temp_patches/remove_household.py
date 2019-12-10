USAGE = """

  Script to remove a single household from the synthesized household and population files.

  Run in the popsyn directory
  Doesn't do backup -- assumes original is in INPUT\popsyn

  Creates/appends to remove_household.log

"""

import argparse, datetime, os, shutil
import pandas

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument("household_id", help="Household id to remove", type=int)
    args = parser.parse_args()

    file_list = sorted(os.listdir("."))
    try:
        file_list.remove("remove_household.log")
    except:
        pass

    log_file = open("remove_household.log", "a")

    now = datetime.datetime.now()
    log_file.write(now.strftime("%Y-%m-%d %H:%M:%S") + "\n")

    # assume file list has hhfile and persfile
    assert(len(file_list) == 2)

    hh_filename   = file_list[0]
    pers_filename = file_list[1]

    assert(hh_filename.startswith("hh"))
    assert(pers_filename.startswith("pers"))

    households_df  = pandas.read_csv(hh_filename)
    households_len = len(households_df)
    print("Read {} lines from {}".format(households_len, hh_filename))
    print(households_df.head())
    log_file.write("Read {} lines from {}\n".format(households_len, hh_filename))
    log_file.write(str(households_df.head()) + "\n")

    households_df = households_df.loc[ households_df.HHID != args.household_id]
    print("Removed household with id {}; new len is {}".format(args.household_id, len(households_df)))
    log_file.write("Removed household with id {}; new len is {}\n".format(args.household_id, len(households_df)))

    # save it
    households_df.to_csv(hh_filename, header=True, index=False)

    persons_df  = pandas.read_csv(pers_filename)
    persons_len = len(persons_df)
    print("Read {} lines from {}".format(persons_len, hh_filename))
    print(persons_df.head())
    log_file.write("Read {} lines from {}\n".format(persons_len, hh_filename))
    log_file.write(str(persons_df.head()) + "\n")

    persons_df = persons_df.loc[ persons_df.HHID != args.household_id]
    print("Removed household with id {}; new len is {}".format(args.household_id, len(persons_df)))
    log_file.write("Removed household with id {}; new len is {}\n".format(args.household_id, len(persons_df)))

    # save it
    persons_df.to_csv(pers_filename, header=True, index=False)

    log_file.write("\n\n")
    log_file.close()
