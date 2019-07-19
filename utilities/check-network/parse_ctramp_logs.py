USAGE = r"""
  Parses ctramp log and outputs trace information into csv files for debugging

  e.g. python parse_ctramp_logs.py event-node0-tourDCMan.log

  Note: python2 won't work because of the regex
  It errors out with: 

      File "X:\travel-model-one-master\utilities\check-network\parse_ctramp_logs.py", line 20, in <module>
        UTILITY_RE     = re.compile("{}{}".format(DATE_LOG_TYPE_RE_TXT, FULL_UTILITY_RE_TXT))
      File "C:\Python27\lib\re.py", line 194, in compile
        return _compile(pattern, flags)
      File "C:\Python27\lib\re.py", line 249, in _compile
        p = sre_compile.compile(pattern, flags)
      File "C:\Python27\lib\sre_compile.py", line 583, in compile
        "sorry, but this version only supports 100 named groups"
    AssertionError: sorry, but this version only supports 100 named groups

    Python3 works, however.

"""

import argparse, re, sys
import numpy, pandas

NUM_TAZ      = 1454
NUM_SUBZONES = 3
NUM_DEST_ALT = NUM_TAZ*NUM_SUBZONES

# start of every log line
DATE_LOG_TYPE_RE_TXT  = "^(\d\d-\w\w\w-\d\d\d\d \d\d:\d\d:\d\d, INFO, )"

# marks the start of what we're looking for in the work location choice log
USUAL_WORK_LOC_RE_TXT = "(Utility Expressions for Usual Location Choice Model for[:] Purpose=(\w+) for HH=(\d+), PersonNum=(\d+), PersonType=([ A-Za-z\-]+), TourNum=(\d+))"

# utility expression for one term - coefficient x variable
UTILITY_RE_TXT        = "(\s+([\.\-0-9]+) [*]\s+(([\.\-0-9]+e[+-]\d\d)|NaN|Infinity))"
# utility expression for all terms - expression number  (coefficient x variable)xNUM_DEST_ALT
FULL_UTILITY_RE_TXT   = "(\d+)" + UTILITY_RE_TXT*NUM_DEST_ALT
UTILITY_RE            = re.compile("{}{}".format(DATE_LOG_TYPE_RE_TXT, FULL_UTILITY_RE_TXT))

# utility express for total utility
TOTAL_UTIL_RE_TXT     = "(\s+(([\.\-0-9]+e[+-]\d\d)|NaN|Infinity))"
# utility expression for all terms
TOTAL_UTILITY_RE_TXT  = "(Alt Utility)" + TOTAL_UTIL_RE_TXT*NUM_DEST_ALT
TOTAL_UTILITY_RE      = re.compile("{}{}".format(DATE_LOG_TYPE_RE_TXT, TOTAL_UTILITY_RE_TXT))

def read_destination_choice_lines(file_object, type_str, purpose, hh, persnum, ptype, tournum):
    """
    Read the destination choice utilities from the file_object
    Saves as destchoice_[type_str]_hh[hh]_pers[persnum].csv
    """
    output_filename = "destchoice_{}_hh{}_pers{}.csv".format(type_str, hh, persnum)
    # from DestinationChoice.xls UEC, Work
    ROW_NAMES = {
        1 : "token, num dest choice segments",
        2 : "token, dest taz",
        3 : "token, mode choice logsum",
        4 : "token, DC SOA correction",
        5 : "token, size var, low inc FTW",
        6 : "token, size var, med inc FTW",
        7 : "token, size var, high inc FTW",
        8 : "token, size var, vhigh inc FTW",
        9 : "token, orig county",
        10: "token, dest county",
        11: "token, hhinc",
        12: "token, low inc",
        13: "token, med inc",
        14: "token, high inc",
        15: "token, vhigh inc",
        16: "token, distance",
        17: "DC SOA correction",
        18: "distance, 0 to 1 mile",
        19: "distance, 1 to 2 miles",
        20: "distance, 2 to 5 miles",
        21: "distance, 5 to 15 miles",
        22: "distance, 15+ miles",
        23: "mode choice logsum",
        24: "size var, low inc FTW",
        25: "size var, med inc FTW",
        26: "size var, high inc FTW",
        27: "size var, vhigh inc FTW",
        28: "no attr, low inc FTW",
        29: "no attr, med inc FTW",
        30: "no attr, high inc FTW",
        31: "no attr, vhigh inc FTW",
        32: "distance, 0 to 5 mi, high+ income",
        33: "distance, 5+ mi, high+ income",
        34: "SF to SF",
        35: "SF to San Mateo",
        36: "SF to Santa Clara",
        37: "San Mateo to Santa Clara",
        38: "San Mateo to Alameda",
        39: "Santa Clara to SF",
        40: "Santa Clara to Santa Clara"
    }
    # 10-Jul-2019 18:40:30, INFO, *******************************************************************************************
    # 10-Jul-2019 18:40:30, INFO, For each model expression, 'coeff * expressionValue' pairs are listed for each available alternative.  At the end, total utility is listed.
    # 10-Jul-2019 18:40:30, INFO, The last line shows total utility for each available alternative.
    # 10-Jul-2019 18:40:31, INFO, Exp                               1                             2                             3                             4                             5
    # 10-Jul-2019 18:40:36, INFO, -----------------------------------------------------------------------------------------------------------------------------------------------------------
    # 10-Jul-2019 18:40:36, INFO, 1           0.00000 *   3.00000e+00       0.00000 *   3.00000e+00       0.00000 *   3.00000e+00       0.00000 *   3.00000e+00       0.00000 *   3.00000e+00

    # read 5 lines that we don't care about
    for lines_read in range(1,6):
        line = file_object.readline().strip()

    row_alt_dicts = []

    # read utiltities
    for utils_read in range(1,41):
        line     = file_object.readline().strip()
        match    = UTILITY_RE.match(line)

        # print(match.groups())
        # ('08-Jul-2019 18:31:21, INFO, ', '1', '           0.00000 *   3.00000e+00', '0.00000', '3.00000e+00', '3.00000e+00', 
        #                                       '       0.00000 *   3.00000e+00', '0.00000', '3.00000e+00', '3.00000e+00',
        #                                       '       0.00000 *   3.00000e+00', '0.00000', '3.00000e+00', '3.00000e+00')
        #  1 = date/log/type
        #  2 = row number
        #  3 = coefficient x variable 1
        #  4 = coefficient 1
        #  5 = variable 1 (numeric or NaN)
        #  6 = variable 1 (numeric)
        #  7 = coefficient x variable 2
        #  8 = coefficient 2
        #  9 = variable 2 (numeric or NaN)
        # 10 = variable 2 (numeric)

        # print(match.group(0))
        row_num   = int(match.group(2)) # row number
        row_descr = ROW_NAMES[row_num]

        full_idx  = 3  # coefficient x variable
        for dest_alt in range(1,NUM_DEST_ALT+1):
            # print("row_num {} dest_alt {} full=[{}] coeff={} var={}".format(row_num, dest_alt, match.group(full_idx), match.group(full_idx+1), match.group(full_idx+2)))

            row_alt_dict = {}
            row_alt_dict["row num"        ] = row_num
            row_alt_dict["row description"] = row_descr
            row_alt_dict["dest alt"       ] = dest_alt
            # https://github.com/BayAreaMetro/travel-model-one/blob/master/core/models/ctramp/src/java/com/pb/models/ctramp/TazDataHandler.java#L464            row_alt_dict["dest alt"       ] = dest_alt 
            row_alt_dict["dest taz"       ] = int((dest_alt-1)/NUM_SUBZONES + 1)
            # https://github.com/BayAreaMetro/travel-model-one/blob/master/core/models/ctramp/src/java/com/pb/models/ctramp/TazDataHandler.java#L480
            row_alt_dict["dest subzone"   ] = int(dest_alt - (row_alt_dict["dest taz"]-1)*NUM_SUBZONES - 1)
            row_alt_dict["coefficient"    ] = float(match.group(full_idx+1))
            row_alt_dict["variable"       ] = match.group(full_idx+2)
            if row_alt_dict["variable"] == "Infinity":
                row_alt_dict["variable"] = numpy.Infinity
            elif row_alt_dict["variable"] == "NaN":
                row_alt_dict["variable"] = numpy.NaN
            else:
                row_alt_dict["variable"] = float(row_alt_dict["variable"])

            row_alt_dicts.append(row_alt_dict)

            full_idx += 4 # go to next alt

    # 12-Jul-2019 18:19:15, INFO, 40         -0.04500 *   0.00000e+00      -0.04500 *   0.00000e+00      -0.04500 *           NaN      -0.04500 *           NaN      -0.04500 *   0.00000e+00
    # 12-Jul-2019 18:19:15, INFO, -----------------------------------------------------------------------------------------------------------------------------------------------------------
    # 12-Jul-2019 18:19:15, INFO, Alt Utility            -1.00624e+03                   5.85899e+00                           NaN                           NaN                   5.86802e+00
    
    # read 1 more lines that we don't care about, the dashes
    line     = file_object.readline().strip()
    assert("----------------------------" in line)
    lines_read += 1

    # total utility
    line     = file_object.readline().strip()
    match    = TOTAL_UTILITY_RE.match(line)
    # print(match.groups())
    #  1 = date/log/type
    #  2 = Alt Utility
    #  3 = TOTAL_UTIL_RE_TXT alt1, spaces plus num or Nan
    #  4 = number or Nan
    #  5 = number
    #  6 = TOTAL_UTIL_RE_TXT alt2, spaces plus num or Nan
    #  7 = number or Nan
    #  8 = number
    full_idx = 3 # TOTAL_UTIL_RE_TXT
    for dest_alt in range(1,NUM_DEST_ALT+1):
        row_alt_dict = {}
        row_alt_dict["row num"        ] = -1
        row_alt_dict["row description"] = "Total Utility"
        row_alt_dict["dest alt"       ] = dest_alt
        # https://github.com/BayAreaMetro/travel-model-one/blob/master/core/models/ctramp/src/java/com/pb/models/ctramp/TazDataHandler.java#L464            row_alt_dict["dest alt"       ] = dest_alt 
        row_alt_dict["dest taz"       ] = int((dest_alt-1)/NUM_SUBZONES + 1)
        # https://github.com/BayAreaMetro/travel-model-one/blob/master/core/models/ctramp/src/java/com/pb/models/ctramp/TazDataHandler.java#L480
        row_alt_dict["dest subzone"   ] = int(dest_alt - (row_alt_dict["dest taz"]-1)*NUM_SUBZONES - 1)
        row_alt_dict["coefficient"    ] = 1.0
        row_alt_dict["variable"       ] = match.group(full_idx+1)
        if row_alt_dict["variable"] == "Infinity":
            row_alt_dict["variable"] = numpy.Infinity
        elif row_alt_dict["variable"] == "NaN":
            row_alt_dict["variable"] = numpy.NaN
        else:
            row_alt_dict["variable"] = float(row_alt_dict["variable"])
        
        row_alt_dicts.append(row_alt_dict)

        full_idx += 3 # go to next alt

    df = pandas.DataFrame.from_records(row_alt_dicts)
    print("head: \n{}".format(df.head()))
    df.to_csv(output_filename, index=False)
    print("Wrote {}".format(output_filename))

    return lines_read + utils_read

if __name__ == '__main__':
    pandas.options.display.width = 1000
    pandas.options.display.max_columns = 100

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument("log_file",  metavar="event-node0-something.log", help="Log file to parse")

    args = parser.parse_args()


    line_re           = re.compile("{}(.*)$".format(DATE_LOG_TYPE_RE_TXT))
    usual_work_loc_re = re.compile("{}{}".format(DATE_LOG_TYPE_RE_TXT, USUAL_WORK_LOC_RE_TXT))

    print("Reading {}".format(args.log_file))
    log_fo = open(args.log_file, 'r')
    lines_read = 0

    while True:
        line = log_fo.readline().strip()
        # check for eof
        if line == "": break

        lines_read += 1

        match = usual_work_loc_re.match(line)
        if match:

            purpose = match.group(3)
            hh      = match.group(4)
            persnum = match.group(5)
            ptype   = match.group(6)
            tournum = match.group(7)
            print("Found Usual Work Location Choice info for purose={} hh={} persnum={} ptype={} tournum={}".format(purpose, hh, persnum, ptype, tournum))

            # read the rest of the relevant lines
            lines_read += read_destination_choice_lines(log_fo, "UsualWorkLocChoice", purpose, hh, persnum, ptype, tournum)

        else:
            match = line_re.match(line)

            if lines_read <= 10:
               print(match.group(2))

        # end for line in log file object
    log_fo.close()


