USAGE=r"""
  visualize_PNRs_by_origin_TAZ.py

  Reads trn\\TransitAssignment.iter3\\am_transit_suplinks_[commuter_rail,express_bus,ferry,heavy_rail,light_rail].dat
  Combines and outputs as a csv, am_transit_suplinks_drive.csv to be used in a tableau to visualize PNRs selected for each origin TAZ.

  Created as part of Asana task:
  "Investigate whether the model correctly penalizes people who park-and-ride at Diridon" (https://app.asana.com/0/1201809392759895/1204093941635973/f)
"""

import re,os,sys
import pandas

ITER            = 3
TIMEPERIOD      = 'am'
SUPLINKS_SUFFIX = ['commuter_rail','express_bus','ferry','heavy_rail','light_rail','knr']
LINE_RE         = re.compile(r"^SUPPLINK N=\s*(?P<orig>\d+)[\-]\s*(?P<dest>\d+) MODE=(?P<mode>\d+) DIST=\s*(?P<dist>\d+) SPEED=\s*(?P<speed>\d+([\.]\d+)?) ONEWAY=(?P<oneway>[YN])$")

if __name__ == '__main__':

    supplinks_df = pandas.DataFrame()
    for suffix in SUPLINKS_SUFFIX:
        supplinks_dict_list = []
        filename = os.path.join("trn", 
                                "TransitAssignment.iter{}".format(ITER),
                                "{}_bus_acclinks_KNR.dat".format(TIMEPERIOD) if suffix == "knr" 
                                    else "{}_transit_suplinks_{}.dat".format(TIMEPERIOD, suffix))
        
        suplinks_fileobj = open(filename, 'r')
        lines_read = 0
        while True:
            line = suplinks_fileobj.readline().strip()
            if line == "": break # eof

            match = LINE_RE.match(line)
            if match==None:
                print("no match for line=[{}]".format(line))
                sys.exit()
                continue
            lines_read += 1

            # convert to dict and store it
            match_dict = match.groupdict()
            match_dict['pnr_mode'] = suffix
            supplinks_dict_list.append(match_dict)

        print("Read {} lines from {}".format(lines_read, filename))

        # convert to dataframe and keep it
        temp_df = pandas.DataFrame.from_records(data=supplinks_dict_list)
        supplinks_df = pandas.concat([supplinks_df, temp_df])

    print("supplinks has {} rows; head:\n{}".format(len(supplinks_df), supplinks_df.head()))
    supplinks_df.to_csv("am_transit_suplinks_drive.csv", index=False)
    print("Wrote am_transit_suplinks_drive.csv")