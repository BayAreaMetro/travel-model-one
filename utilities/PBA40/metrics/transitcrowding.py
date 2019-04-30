import argparse, copy, csv, logging, os, sys
import pandas as pd
import simpledbf

USAGE="""

This code sources transit outputs by links that are sourced in five files, one for each period.
Based on the volume of trips for each link, and the seating capacity for the link, it calculates a crowding factor.
This crowding factor is applied as a penalty on in-vehicle transit time, which is number of trips * time for each trip.
The penalty on the IVTT is used by CoBRA to calculate the benefit that a project may create by alleviating crowding.

Additionally, if "psuedo lines" are found (which are currently defined as BART lines which start as board-only stops
followed by exit-only stops), then the script allocates those boards, alights and volumes to the actual lines that
they represent.  The pseudo lines must be mapped to actual lines via the PSEUDO_LINE_MAPPING.  This funcionality
may be suppressed with the arg --no_pseudo_move but it is on by default.

transitcrowding.py is run with the proj folder as an argument. eg:
projects root dir\python transitcrowding.py 1_CaltrainMod\\2050_TM150_BF_00_1_CaltrainMod_00

Input:
* TransitSeatCap.csv, containing VEHTYPE, seatcap and standcap

Output:
* [project_dir]\\OUTPUT\\metrics\\transit_crowding_complete.csv
* [project_dir]\\OUTPUT\\metrics\\transit_crowding.csv
* [project_dir]\\OUTPUT\\metrics\\transit_crowding.log -- log file with debug information.

"""

LOG_FILE = "transit_crowding.log"

PSEUDO_LINE_MAPPING = {
    # baseline
    "120_OR_YEL"  :("120_ORANGE-","120_YELLOW[-89]$"), # Orange/Richmond - MacArthur - Yellow/SFO
    "120_OR_YER"  :("120_YELLOW[1]?$","120_ORANGE$"), # Yellow/SFO - MacArthur - Orange/Richmond
    # crossings 3
    "120_BL_PS"   :("120_BLUE-",  "120_GREEN-" ), # Blue/DublinPleasanton - San Antonio - Green/Millbrae
    "120_BL_PSR"  :("120_GREEN$", "120_BLUE$"  ), # Green/Millbrae - San Antonio - Blue/DublinPleasanton
    "120_GREEN_BL":("120_GREEN-", "120_BLUE-"  ), # Green/BerryessaFremont - SanAntonio - Blue/Millbrae
    "120_GREEN_BR":("120_BLUE$",  "120_GREEN$" ), # Blue/MillBrae - San Antonio - Green/BerryessaFremont
    "120_GRN"     :("120_ORANGE$","120_NEW-"   ), # Orange/BerryessaFremont - San Antonio - New/Millbrae
    "120_GRN_R"   :("120_NEW$",   "120_ORANGE-"), # New/Millbrae - San Antonio - Orange/BerryessaFremont
    "120_NEW_PS"  :("120_NEW$",   "120_YELLOW-"), # New/Pittsburg - MacArthur - Yellow/Millbrae (*)
    "120_NEW_PSR" :("120_YELLOW$","120_NEW-"   ), # Yellow/Millbrae - MacArthur - New/Pittsburg (*)
    "120_RED_YEL" :("120_ORANGE-","120_YELLOW-"), # Orange/Richmond - MacArthur - Yellow/Millbrae
    "120_RED_YER" :("120_YELLOW$","120_ORANGE$"), # Yellow/Millbrae - MacArthur - Orange/Richmond
    # crossings 4
    "130_RR_PSEU" :("130_RR_SACR$", "130_RR_F_EXP-", 14648), # RR_Sacr/Martinez - Jack London - Fremont (along easy bay)
    "130_RR_PSEUR":("130_RR_F_EXP$","130_RR_SACR-",  14648), # reverse
}

def find_pseudo_lines(trn_link_df):
    """
    Find lines that look like pseudo lines -- 
    e.g. there's a sequence of board-only stops followed by a sequence of alight-only stops

    Return a list of tuples: [(MODE, NAME, period, seq_last_board, seq_first_exit)]
    """
    # add temp columns
    # seq with brda > 0
    trn_link_df["seq_brda"] = trn_link_df["SEQ"]
    trn_link_df.loc[ trn_link_df["AB_BRDA"] == 0, "seq_brda"] = 0
    # seq with xitb > 0
    trn_link_df["seq_xitb"] = trn_link_df["SEQ"]
    trn_link_df.loc[ trn_link_df["AB_XITB"] == 0, "seq_xitb"] = 100

    line_group = trn_link_df.groupby(by=["MODE","NAME","period"])
    pseudo_lines = []

    for group_id, line in line_group:
        if group_id[0] not in [120, 130]: continue # BART, regional rail only
        if len(line) < 3: continue      # pseudo lines must have board + transfer + exit  

        seq_last_board = line["seq_brda"].max()
        seq_first_exit = line["seq_xitb"].min()

        # board / transfer / exit
        if seq_last_board < seq_first_exit:
            pseudo_line_name = group_id[1]
            # logging.info("Found pseudo line {} (last board: {}  first exit: {})".format(str(group_id), seq_last_board, seq_first_exit))
            # print(line[["A","B","SEQ","AB_BRDA","AB_XITB","seq_brda","seq_xitb"]])

            pseudo_lines.append( (group_id[0], group_id[1], group_id[2], seq_last_board, seq_first_exit) )

    # remove temp columns
    trn_link_df.drop(columns=["seq_brda","seq_xitb"], inplace=True)

    return pseudo_lines

def move_pseudo_line_ridership(trn_link_df, pseudo_lines):
    """
    Moves the ridership from the given pseudo lines to their actual counterparts
    Configuration of those counterparts is in PSEUDO_LINE_MAPPING
    Updates the AB_BRDA, AB_XITB and AB_VOL columns for the actual lines and deletes the pseudo line rows from the table.

    Returns updated trn_link_df.
    """
    # add run_per_hr to make things easier
    trn_link_df["run_per_hr"] = 0.0
    trn_link_df.loc[ trn_link_df["FREQ"] > 0, "run_per_hr" ] = 60.0/trn_link_df["FREQ"]

    orig_cols = list(trn_link_df.columns.values)

    for pseudo_line in pseudo_lines:
        mode_num         = pseudo_line[0]
        pseudo_line_name = pseudo_line[1]
        period           = pseudo_line[2]
        seq_last_board   = pseudo_line[3]
        seq_first_exit   = pseudo_line[4]

        if pseudo_line_name not in PSEUDO_LINE_MAPPING:
            logging.fatal("{} is not configured in PSEUDO_LINE_MAPPING".format(pseudo_line_name))
            sys.exit(2)

        # Look it up in the mapping
        start_line_re = PSEUDO_LINE_MAPPING[pseudo_line_name][0]
        end_line_re   = PSEUDO_LINE_MAPPING[pseudo_line_name][1]

        pseudo_line_df = trn_link_df.loc[ (trn_link_df["NAME"]==pseudo_line_name)&(trn_link_df["period"]==period), 
            ["NAME","SEQ","period","FREQ","run_per_hr","A","B","AB_BRDA","AB_XITB","AB_VOL"]]
        pseudo_run_per_hr = pseudo_line_df["run_per_hr"].mean()

        logging.info("Moving ridership for pseudo line {} period {} run_per_hr {} last board {}/first exit {}".format(
              pseudo_line_name, period, pseudo_run_per_hr, seq_last_board, seq_first_exit))
        logging.info("  Start line regex: {}".format(start_line_re))
        logging.info("  End line regex: {}".format(end_line_re))

        # Multiple possible transfer stops -- see if one is specified
        if seq_last_board < seq_first_exit-1:
            if len(PSEUDO_LINE_MAPPING[pseudo_line_name])>2:
                transfer_stop = PSEUDO_LINE_MAPPING[pseudo_line_name][2]
                seq_last_board = pseudo_line_df.loc[ pseudo_line_df["B"]==transfer_stop].iloc[0]["SEQ"]
                seq_first_exit = pseudo_line_df.loc[ pseudo_line_df["A"]==transfer_stop].iloc[0]["SEQ"]
                logging.debug("Multiple possible transfer stops; PSEUDO_LINE_MAPPING lookup used to determine last board {}/first exit {}".format(seq_last_board, seq_first_exit))
            else:
                logging.fatal("Multiple possible transfer stops; specify the transfer stop in PSEUDO_LINE_MAPPING")

        # preparing for join -- everybody gets off at transfer point and on at transfer point
        pseudo_line_df.loc[ pseudo_line_df["SEQ"] == seq_last_board, "AB_XITB" ] = pseudo_line_df["AB_VOL"]
        pseudo_line_df.loc[ pseudo_line_df["SEQ"] == seq_first_exit, "AB_BRDA" ] = pseudo_line_df["AB_VOL"]

        # create column that contains start_line_re for board stops, end_line_re for exit stops
        pseudo_line_df["name_re"] = ""
        pseudo_line_df.loc[ pseudo_line_df["SEQ"] <= seq_last_board, "name_re"] = start_line_re
        pseudo_line_df.loc[ pseudo_line_df["SEQ"] >= seq_first_exit, "name_re"] = end_line_re
        pseudo_line_df.sort_values(by="SEQ", inplace=True)
        logging.debug("\n{}".format(pseudo_line_df))

        # create column that contains start_line_re if name matches, end_line_re if name matches, "" otherwise
        trn_link_df["name_re"] = ""
        trn_link_df.loc[ trn_link_df["NAME"].str.match(start_line_re)==True, "name_re"] = start_line_re
        trn_link_df.loc[ trn_link_df["NAME"].str.match(  end_line_re)==True, "name_re"] = end_line_re
        
        # join it on the pseudo line
        trn_link_df = pd.merge(left     =trn_link_df,
                               right    =pseudo_line_df[["period","run_per_hr","name_re","A","B","SEQ","AB_BRDA","AB_XITB","AB_VOL"]],
                               on       =["period","name_re","A","B"],
                               how      ="outer",
                               suffixes =["","_pseudo"],
                               indicator=True)

        debug_df = trn_link_df.loc[trn_link_df["_merge"] != "left_only",
              ["NAME","period","SEQ","FREQ","run_per_hr","A","B","AB_BRDA","AB_XITB","AB_VOL",
               "run_per_hr_pseudo","SEQ_pseudo","AB_BRDA_pseudo","AB_XITB_pseudo","AB_VOL_pseudo","_merge"]].sort_values(by="SEQ_pseudo")
        logging.debug("BEFORE\n{}".format(debug_df))

        # count the matches for each link
        match_group = trn_link_df.loc[ trn_link_df["_merge"] != "left_only" ].groupby(["A","B"])
        match_agg_df = match_group.agg({"NAME":"count", "run_per_hr":"sum"})

        logging.debug("match_agg_df:\n{}".format(match_agg_df))

        # check that we found actual links for every pseudo link
        pseudo_link_with_missing_actual = match_agg_df.loc[match_agg_df["NAME"] < 1].reset_index()
        if len(pseudo_link_with_missing_actual) > 0:
            # let a few link slide
            if len(pseudo_link_with_missing_actual) <= 5:
                logging.warn("{} Pseudo links found with no corresponding actual link:\n{}".format(
                             len(pseudo_link_with_missing_actual), pseudo_link_with_missing_actual))
            else:
                logging.fatal("TODO: NAME count < 0 shouldn't happen")
                sys.exit()
        if match_agg_df["NAME"].max() != 1:
            logging.fatal("TODO: NAME count > 1 not implemented")
            sys.exit()

        # check that the actual links have the same runs per hour as the pseudo links
        mismatch_run_per_hr = match_agg_df.loc[ match_agg_df["run_per_hr"] != pseudo_run_per_hr].reset_index()
        mismatch_run_per_hr["run_per_hr_diff"] = mismatch_run_per_hr["run_per_hr"] - pseudo_run_per_hr
        if len(mismatch_run_per_hr) > 0:
            # let a few links slide
            if len(mismatch_run_per_hr) <= 5:
                logging.warn("{} Pseudo links found with mismatching run per hour:\n{}".format(
                             len(mismatch_run_per_hr), mismatch_run_per_hr))
            # more in EA, EV
            elif period in ["EA","EV"]:
                logging.warn("{} Pseudo links found with mismatching run per hour:\n{}".format(len(mismatch_run_per_hr), mismatch_run_per_hr))
            else:
                logging.fatal("Mismatch run_per_hr between pseudo line and matching line\n{}".format(mismatch_run_per_hr))
                sys.exit()

        # add psuedo line boards, exits and volums to other line
        trn_link_df.loc[trn_link_df["_merge"]=="both", "AB_BRDA"] = trn_link_df["AB_BRDA"] + trn_link_df["AB_BRDA_pseudo"]
        trn_link_df.loc[trn_link_df["_merge"]=="both", "AB_XITB"] = trn_link_df["AB_XITB"] + trn_link_df["AB_XITB_pseudo"]
        trn_link_df.loc[trn_link_df["_merge"]=="both", "AB_VOL" ] = trn_link_df["AB_VOL" ] + trn_link_df["AB_VOL_pseudo" ]

        debug_df = trn_link_df.loc[trn_link_df["_merge"] != "left_only",
              ["NAME","period","SEQ","FREQ","run_per_hr","A","B","AB_BRDA","AB_XITB","AB_VOL",
               "run_per_hr_pseudo","SEQ_pseudo","AB_BRDA_pseudo","AB_XITB_pseudo","AB_VOL_pseudo","_merge"]].sort_values(by="SEQ_pseudo")
        logging.debug("AFTER\n{}".format(debug_df))

        # drop the links that are right_only -- those are errors that we're ignoring
        trn_link_df = trn_link_df.loc[ trn_link_df["_merge"] != "right_only" ]
        # done with the pseudo line for this time period -- remove it, and go back to original columns
        trn_link_df = trn_link_df.loc[(trn_link_df["NAME"]!=pseudo_line_name)|(trn_link_df["period"]!=period), orig_cols]

    return trn_link_df


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description = USAGE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('project_dir', type=str, help="Project directory")
    parser.add_argument('--no_pseudo_move', action='store_true', help="Don't move pseudo line ridership into real lines")
    my_args = parser.parse_args()

    # create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(ch)
    # file handler
    fh = logging.FileHandler(os.path.join(my_args.project_dir, "OUTPUT", "metrics", LOG_FILE), mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(fh)

    logging.info("Args: {}".format(my_args))

    # import seat capacities from lookup file
    seatcap_file = "TransitSeatCap.csv"
    transit_seatcap_df = pd.read_csv(seatcap_file)
    transit_seatcap_df.columns=transit_seatcap_df.columns.str.replace('%','pct')
    transit_seatcap_df.rename(columns={"VEHTYPE":"veh_type_updated", "100pctCapacity":"standcap"},inplace=True)
    logging.info("Read {}\n{}".format(seatcap_file, transit_seatcap_df.head()))

    # read the transit files
    all_trn_df = pd.DataFrame()
    for timeperiod in ['AM','EA','EV','MD','PM']:
        trn_file = os.path.join(my_args.project_dir, 'OUTPUT', 'trn', 'trnlink{}_ALLMSA.dbf'.format(timeperiod))
        dbf      = simpledbf.Dbf5(trn_file)
        trn_df   = dbf.to_dataframe()
        trn_df["period"] = timeperiod
        logging.info("Read {} links from {}".format(len(trn_df), trn_file))
        # print(trn_df.head())
        all_trn_df = pd.concat([all_trn_df, trn_df])
    logging.info("Read {} total links".format(len(all_trn_df)))

    # sort by mode, line name, time period, sequence
    all_trn_df.sort_values(by=["MODE","NAME","period","SEQ"], inplace=True)

    pseudo_lines = find_pseudo_lines(all_trn_df)
    if my_args.no_pseudo_move:
        logging.info("Moving pseudo line ridership into actual lines suppressed by argument")
    elif len(pseudo_lines) > 0:
        all_trn_df = move_pseudo_line_ridership(all_trn_df, pseudo_lines)

    # vehicle type overrides
    all_trn_df["veh_type_updated"] = all_trn_df["VEHTYPE"]
    all_trn_df.loc[ all_trn_df["SYSTEM"]=="AC Transit",         "veh_type_updated"] = "AC Plus Bus"
    all_trn_df.loc[ all_trn_df["NAME"].str.contains("30_1AC"),  "veh_type_updated"] = "Motor Articulated Bus"
    all_trn_df.loc[ all_trn_df["NAME"].str.contains("522VTA"),  "veh_type_updated"] = "Motor Articulated Bus"

    all_trn_df.loc[ all_trn_df["NAME"].str.contains("120_EBART"), "veh_type_updated"] = "eBart 1 car"
    all_trn_df.loc[ all_trn_df["NAME"].str.contains("120_EBART") & (all_trn_df["period"]=="AM"), "veh_type_updated"] = "eBart 2 car"
    all_trn_df.loc[ all_trn_df["NAME"].str.contains("120_EBART") & (all_trn_df["period"]=="PM"), "veh_type_updated"] = "eBart 2 car"

    # for crossings projects    
    all_trn_df.loc[ (all_trn_df["veh_type_updated"]=='8 Car BART') & (all_trn_df["period"]=="EA"), "veh_type_updated"] = "5 Car BART RENOVATED"
    all_trn_df.loc[ (all_trn_df["veh_type_updated"]=='8 Car BART') & (all_trn_df["period"]=="MD"), "veh_type_updated"] = "5 Car BART RENOVATED"
    all_trn_df.loc[ (all_trn_df["veh_type_updated"]=='8 Car BART') & (all_trn_df["period"]=="EV"), "veh_type_updated"] = "5 Car BART RENOVATED"
    all_trn_df.loc[ (all_trn_df["veh_type_updated"]=='8 Car BART') & (all_trn_df["period"]=="AM"), "veh_type_updated"] = "10 Car BART RENOVATED"
    all_trn_df.loc[ (all_trn_df["veh_type_updated"]=='8 Car BART') & (all_trn_df["period"]=="PM"), "veh_type_updated"] = "10 Car BART RENOVATED"
    all_trn_df.loc[ all_trn_df["NAME"].str.contains("130_RR"), "veh_type_updated"] = "Caltrain PCBB 10 car"


    # print(all_trn_df.loc[ all_trn_df["VEHTYPE"] != all_trn_df["veh_type_updated"]])
    logging.info("Updated vehicle type for {} links".format(len(all_trn_df.loc[ all_trn_df["VEHTYPE"] != all_trn_df["veh_type_updated"]])))

    # merge with seatcap on updated vehicle type
    all_trn_df = pd.merge(left   = all_trn_df,
                          right  = transit_seatcap_df[["veh_type_updated","seatcap","standcap"]],
                          on     = "veh_type_updated",
                          how    = "left")
    all_trn_df["period_seatcap"] = all_trn_df["PERIODCAP"]/all_trn_df["VEHCAP"]*all_trn_df["seatcap"]  # total seated capacity in time period
    all_trn_df["period_standcap"]= all_trn_df["PERIODCAP"]/all_trn_df["VEHCAP"]*all_trn_df["standcap"] # total seated capacity in time period
    all_trn_df["load_seatcap"]   = all_trn_df["AB_VOL"]/all_trn_df["period_seatcap"]                   # seated load over time period
    all_trn_df["load_standcap"]  = all_trn_df["AB_VOL"]/all_trn_df["period_standcap"]                  # standing load over time period
    all_trn_df["ivtt_hours"]     = all_trn_df["AB_VOL"]*(all_trn_df["TIME"]/100)/60                    # number of trips * time per trip

    # setting default crowding factors
    
    # calculating crowding factors based on methodologies from UK DFT and Metrolinx
    all_trn_df["crowdingfactor_metrolinx"        ] = 1.0

    # temp variable: max(0, AB_VOL-period_seatcap)
    all_trn_df["vol_minus_seatcap"] = all_trn_df["AB_VOL"]-all_trn_df["period_seatcap"]
    all_trn_df.loc[ all_trn_df["vol_minus_seatcap"]<0, "vol_minus_seatcap"] = 0

    all_trn_df.loc[ all_trn_df["AB_VOL"] > all_trn_df["period_seatcap"], "crowdingfactor_metrolinx"] = \
        (((1.0 + (0.1*all_trn_df["load_seatcap"].pow(1.4))) * all_trn_df[["period_seatcap", "AB_VOL"]].min(axis=1)) + \
         ((1.4 + (0.2*all_trn_df["load_seatcap"].pow(3.4))) * all_trn_df["vol_minus_seatcap"])) / all_trn_df["AB_VOL"]

    
    # cf_metrolinx_max2pt5 = min(cf_metrolinx,2.5)
    all_trn_df["crowdingfactor_metrolinx_max2pt5"] = all_trn_df["crowdingfactor_metrolinx"]
    all_trn_df.loc[ all_trn_df["crowdingfactor_metrolinx"] > 2.5, "crowdingfactor_metrolinx_max2pt5"] = 2.5

    all_trn_df["sit"  ] = 1.0
    all_trn_df["stand"] = 1.0
    all_trn_df.loc[ all_trn_df["load_seatcap"] >= 1.0, ["sit","stand"]] = [1.08, 1.50]
    all_trn_df.loc[ all_trn_df["load_seatcap"] >= 1.2, ["sit","stand"]] = [1.23, 1.67]
    all_trn_df.loc[ all_trn_df["load_seatcap"] >= 1.4, ["sit","stand"]] = [1.38, 1.85]
    all_trn_df.loc[ all_trn_df["load_seatcap"] >= 1.6, ["sit","stand"]] = [1.53, 2.02]
    all_trn_df.loc[ all_trn_df["load_seatcap"] >= 1.8, ["sit","stand"]] = [1.68, 2.20]
    all_trn_df.loc[ all_trn_df["load_seatcap"] >= 2.0, ["sit","stand"]] = [1.83, 2.37]

    # cf_ukdft = ((period_seatcap*sit) + ((ab_vol-period_seatcap)*stand)) / ab_vol
    all_trn_df["crowdingfactor_ukdft"] = 1.0
    all_trn_df.loc[ all_trn_df["AB_VOL"] > all_trn_df["period_seatcap"], "crowdingfactor_ukdft"] = \
        ((all_trn_df["period_seatcap"]*all_trn_df["sit"]) + \
         ((all_trn_df["AB_VOL"]-all_trn_df["period_seatcap"])*all_trn_df["stand"])) / all_trn_df["AB_VOL"]
    
    # calculating effective ivtt = ivtt * crowding factor
    all_trn_df["effective_ivtt_ukdft"            ] = all_trn_df["ivtt_hours"]*all_trn_df["crowdingfactor_ukdft"            ]
    all_trn_df["effective_ivtt_metrolinx"        ] = all_trn_df["ivtt_hours"]*all_trn_df["crowdingfactor_metrolinx"        ]
    all_trn_df["effective_ivtt_metrolinx_max2pt5"] = all_trn_df["ivtt_hours"]*all_trn_df["crowdingfactor_metrolinx_max2pt5"]

    all_trn_df["crowding_penalty_hrs_ukdft"            ] = all_trn_df["effective_ivtt_ukdft"]             - all_trn_df["ivtt_hours"]
    all_trn_df["crowding_penalty_hrs_metrolinx"        ] = all_trn_df["effective_ivtt_metrolinx"]         - all_trn_df["ivtt_hours"]
    all_trn_df["crowding_penalty_hrs_metrolinx_max2pt5"] = all_trn_df["effective_ivtt_metrolinx_max2pt5"] - all_trn_df["ivtt_hours"]

    # drop these to be consistent with previous output
    # all_trn_df.drop(columns=["veh_type_updated", "vol_minus_seatcap"], inplace=True)

    # sort by mode, line name, time period, sequence
    all_trn_df = all_trn_df.astype(dtype={"MODE":"int16","PLOT":"int16","COLOR":"int16","STOP_A":"int16","STOP_B":"int16","SEQ":"int16"})
    all_trn_df.sort_values(by=["MODE","NAME","period","SEQ"], inplace=True)

    # writing file with all columns into output\metrics folder of the project
    transit_crowding_filename = os.path.join(my_args.project_dir, 'OUTPUT', 'metrics', "transit_crowding_complete.csv")
    all_trn_df.to_csv(transit_crowding_filename,  header=True, index=False)
    logging.info("Wrote {} lines to {}".format(len(all_trn_df), transit_crowding_filename))

    # writing essential columns into output\metrics folder of the project
    transit_crowding_filename = os.path.join(my_args.project_dir, 'OUTPUT', 'metrics', "transit_crowding.csv")
    all_trn_df[['NAME', 'SYSTEM','SEQ','A','B','AB_BRDA','period','ivtt_hours',\
                'effective_ivtt_ukdft','effective_ivtt_metrolinx', 'effective_ivtt_metrolinx_max2pt5',\
                'crowding_penalty_hrs_ukdft', 'crowding_penalty_hrs_metrolinx', 'crowding_penalty_hrs_metrolinx_max2pt5'
              ]].to_csv(transit_crowding_filename, header=True, index=False)
    logging.info("Wrote {} lines to {}".format(len(all_trn_df), transit_crowding_filename))

