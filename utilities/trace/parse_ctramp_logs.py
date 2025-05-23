USAGE = r"""
  Parses ctramp log and outputs trace information into csv files for debugging

  e.g. python parse_ctramp_logs.py base|build event-node0-tourDCMan.log

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

import argparse, re, os, shutil, pathlib, sys
import numpy, pandas

NUM_TAZ      = 1454
NUM_SUBZONES = 3
NUM_DEST_ALT = NUM_TAZ*NUM_SUBZONES
NUM_MC_ALT   = 21

# start of every log line
DATE_LOG_TYPE_RE_TXT  = r"^(\d\d-\w\w\w-\d\d\d\d \d\d:\d\d:\d\d, (?P<log_level>DEBUG|INFO), )"

# marks the start of what we're looking for in the work location choice log
TOURDC_RE_TXT         = "(Utility Expressions for (Usual Location Choice Model for:|Individual Non-Mandatory Tour Destination Choice Model,) Purpose=([ A-Za-z\-_]+) for HH=(\d+), PersonNum=(\d+), PersonType=([ A-Za-z\-]+), Tour(Num|Id)=(\d+))"
#                         Utility Expressions for Individual Non-Mandatory Tour Destination Choice Model, Purpose=shopping for HH=47127, PersonNum=2, PersonType=Part-time worker, TourId=0.

# marks the start of the Tour Mode Choice lines
# Note: I'm sure a regex could be devised to work for both but I'm not testing the logsum case so I'm breaking that for now
TOURMC_RE_TXT         = r"(?P<full_line>Utility Expressions for(?P<nonm> Individual Non-Mandatory| INDIVIDUAL_NON_MANDATORY| MANDATORY)? Tour Mode Choice (?P<modeltype>Logsum calculation|Model) for(?P<purpose>:|([ A-Za-z\-_]+) Location Choice) (?P<attrs>.*))$"
# TOURMC_RE_TXT         = "(Utility Expressions for( Individual Non-Mandatory)? Tour Mode Choice Logsum calculation for ([ A-Za-z\-_]+) Location Choice   HH=(\d+), PersonNum=(\d+), PersonType=([ A-Za-z\-]+),( TourId=\d+[,])? destTaz=(\d+) destWalkSubzone=(\d+))"
#  logsum lines in work location choice log:
#                         Utility Expressions for Individual Non-Mandatory    Tour Mode Choice Logsum calculation for shopping Location Choice   HH=47127, PersonNum=2, PersonType=Part-time worker, TourId=0, destTaz=1254 destWalkSubzone=1
#  lines in tourMcMan.log:
#                         Utility Expressions for MANDATORY Tour Mode Choice Model for: Purpose=work_very high, Orig=3, OrigSubZ=1, Dest=15, DestSubZ=1    HH=264, PersonNum=1, PersonType=Full-time worker, TourId=0
#  lines in tourMcNonMan.log:
#                         Utility Expressions for INDIVIDUAL_NON_MANDATORY Tour Mode Choice Model for: Purpose=eatout, Orig=2, OrigSubZ=1, Dest=16, DestSubZ=1    HH=88, PersonNum=3, PersonType=University student, TourId=2

# marks the start of the Trip Mode Choice lines in trip mode choice log
TRIPMC_RE_TXT         = r"(?P<full_line>Utility Expressions for Trip Mode Choice Model for (?P<attrs>.*).)$"
TRIPMC_ORIGDEST_RE_TXT= "(\s+(orig|origWalkSegment|dest|destWalkSegment|direction): \s+(\d+|inbound|outbound))"

# marks the start of the Work-From-Home lines in the cdap log
WFH_RE_TXT         = r"(?P<full_line>Utility Expressions for Work-From-Home Choice (?P<attrs>.*))$"

# utility expression for one term - coefficient x variable
UTILITY_RE_TXT        = "(\s+([\.\-0-9]+) [*]\s+(([\.\-0-9]+e[+-]\d\d)|NaN|Infinity))"
# utility expression for all terms - expression number  (coefficient x variable)xNUM_DEST_ALT
FULL_UTILITY_RE_TXT   = "(\d+)" + UTILITY_RE_TXT*NUM_DEST_ALT
UTILITY_RE            = re.compile("{}{}".format(DATE_LOG_TYPE_RE_TXT, FULL_UTILITY_RE_TXT))
# utility expression for tour mc terms - expression number  (coefficient x variable)NUM_MC_ALT
MC_UTILITY_RE_TXT     = "(\d+)" + UTILITY_RE_TXT*NUM_MC_ALT
MC_UTILITY_RE         = re.compile("{}{}".format(DATE_LOG_TYPE_RE_TXT, MC_UTILITY_RE_TXT))
# utility expression for WFH
NUM_WFH_ALT           = 2
WFH_UTILITY_RE_TXT    = "(\d+)" + UTILITY_RE_TXT*NUM_WFH_ALT
WFH_UTILITY_RE        = re.compile("{}{}".format(DATE_LOG_TYPE_RE_TXT, WFH_UTILITY_RE_TXT))

# utility express for total utility
TOTAL_UTIL_RE_TXT     = "(\s+(([\.\-0-9]+e[+-]\d\d)|NaN|Infinity))"
# utility expression for all terms
TOTAL_UTILITY_RE_TXT  = "(Alt Utility)" + TOTAL_UTIL_RE_TXT*NUM_DEST_ALT
TOTAL_UTILITY_RE      = re.compile("{}{}".format(DATE_LOG_TYPE_RE_TXT, TOTAL_UTILITY_RE_TXT))
# utility expression for all mode choice terms
MC_TOTAL_UTILITY_RE_TXT = "(Alt Utility)" + TOTAL_UTIL_RE_TXT*NUM_MC_ALT
MC_TOTAL_UTILITY_RE     = re.compile("{}{}".format(DATE_LOG_TYPE_RE_TXT, MC_TOTAL_UTILITY_RE_TXT))
# utiliyt expression for all WFH choice terms
WFH_TOTAL_UTILITY_RE_TXT = "(Alt Utility)" + TOTAL_UTIL_RE_TXT*NUM_WFH_ALT
WFH_TOTAL_UTILITY_RE     = re.compile("{}{}".format(DATE_LOG_TYPE_RE_TXT, WFH_TOTAL_UTILITY_RE_TXT))

def read_tour_mode_choice_logsum_lines(file_object, type_str, attr_dict, base_or_build, log_file):
    """
    Read tour mode choice logsum utilities from the file_object
    """
    print(f"read_tour_mode_choice_logsum_lines with {type_str=} {base_or_build=}")
    for attr_key in attr_dict.keys():
        print(f"  {attr_key} => {attr_dict[attr_key]}")
    #if destTaz > 25:
    #    return (0, pandas.DataFrame())

    # from ModeChoice.xls UEC, Work
    WORK_ROW_NAMES = {
        1: "token, terminalTime",
        2: "token, freeParkingAllowed",
        3: "token, freeParkingAvailable",
        4: "token, hourlyParkingCost",
        5: "token, destTopology",
        6: "token, destCounty",
        7: "token, origCounty",
        8: "token, valueOfTime",
        9: "token, autos",
        10: "token, workers",
        11: "token, hhSize",
        12: "token, hhIncomeQ1",
        13: "token, hhIncomeQ2",
        14:	"token, hhIncomePercentOfPoverty",
        15:	"token, hhUnderPovertyThreshold",
        16: "token, age",
        17: "token, timeOutbound",
        18: "token, timeInBound",
        19: "token, tourDuration",
        20: "token, tourCategoryJoint",
        21: "token, numberOfParticipantsInJointTour",
        22: "token, tourCategorySubtour",
        23: "token, workTourModeIsSOV",
        24: "token, workTourModeIsBike",
        25: "token, destZoneAreaType",
        26: "token, originDensityIndex",
        27: "token, densityIndex",
        28: "token, zonalShortWalkOrig",
        29: "token, zonalLongWalkOrig",
        30: "token, zonalShortWalkDest",
        31: "token, zonalLongWalkDest",
        32: "token, c_ivt",
        33: "token, c_ivt_lrt",
        34: "token, c_ivt_ferry",
        35: "token, c_ivt_exp",
        36: "token, c_ivt_hvy",
        37: "token, c_ivt_com",
        38: "token, c_walkTimeShort",
        39: "token, c_walkTimeLong",
        40: "token, c_bikeTimeShort",
        41: "token, c_bikeTimeLong",
        42: "token, c_cost",
        43: "token, c_shortiWait",
        44: "token, c_longiWait",
        45: "token, c_wacc",
        46: "token, c_wegr",
        47: "token, c_waux",
        48: "token, c_dtim",
        49: "token, c_xwait",
        50: "token, c_dacc_ratio",
        51: "token, c_xfers_wlk",
        52: "token, c_xfers_drv",
        53: "token, c_drvtrn_distpen_0",
        54: "token, c_drvtrn_distpen_max",
        55: "token, c_topology_walk",
        56: "token, c_topology_bike",
        57: "token, c_topology_trn",
        58: "token, c_densityIndex",
        59: "token, c_age1619_da",
        60: "token, c_age010_trn",
        61: "token, c_age16p_sr",
        62: "token, c_hhsize1_sr",
        63: "token, c_hhsize2_sr",
        64: "token, costPerMile",
        65: "token, costShareSr2",
        66: "token, costShareSr3",
        67: "token, waitThresh",
        68: "token, walkThresh",
        69: "token, shortWalk",
        70: "token, longWalk",
        71: "token, walkSpeed",
        72: "token, bikeThresh",
        73: "token, bikeSpeed",
        74: "token, maxCbdAreaTypeThresh",
        75: "token, indivTour",
        76: "token, upperEA",
        77: "token, upperAM",
        78: "token, upperMD",
        79: "token, upperPM",
        80: "token, zeroAutoHh",
        81: "token, autoDeficientHh",
        82: "token, autoSufficientHh",
        83: "token, shortWalkMax",
        84: "token, longWalkMax",
        85: "token, walkTransitOrig",
        86: "token, walkTransitDest",
        87: "token, walkTransitAvailable",
        88: "token, driveTransitAvailable",
        89: "token, originWalkTime",
        90: "token, originWalkTime",
        91: "token, destinationWalkTime",
        92: "token, destinationWalkTime",
        93: "token, cbdDummy",
        94: "token, dailyParkingCost",
        95: "token, costInitialTaxi",
        96: "token, costPerMileTaxi",
        97: "token, costPerMinuteTaxi",
        98: "token, costInitialSingleTNC",
        99: "token, costPerMileSingleTNC",
        100: "token, costPerMinuteSingleTNC",
        101: "token, costMinimumSingleTNC",
        102: "token, costInitialSharedTNC",
        103: "token, costPerMileSharedTNC",
        104: "token, costPerMinuteSharedTNC",
        105: "token, costMinimumSharedTNC",
        106: "token, totalWaitTaxi",
        107: "token, totalWaitSingleTNC",
        108: "token, totalWaitSharedTNC",
        109: "token, autoIVTFactorAV",
        110: "token, autoParkingCostFactorAV",
        111: "token, autoCostPerMileFactorAV",
        112: "token, autoTerminalTimeFactorAV",
        113: "token, sharedTNCIVTFactor",
        114: "token, useAV",
        115: "token, autoIVTFactor",
        116: "token, autoParkingCostFactor",
        117: "token, autoCPMFactor",
        118: "token, autoTermTimeFactor",
        119: "token, outPeriod",
        120: "token, outPeriod",
        121: "token, outPeriod",
        122: "token, outPeriod",
        123: "token, outPeriod",
        124: "token, inPeriod",
        125: "token, inPeriod",
        126: "token, inPeriod",
        127: "token, inPeriod",
        128: "token, inPeriod",
        129: "token, destCordon",
        130: "token, destCordonPrice",
        131: "token, origCordon",
        132: "token, origCordonPrice",
        133: "token, sovOut",
        134: "token, sovIn",
        135: "token, sovAvailable",
        136: "token, sovtollAvailable",
        137: "token, hov2Out",
        138: "token, hov2In",
        139: "token, hov2Available",
        140: "token, hov2tollAvailable",
        141: "token, hov3Out",
        142: "token, hov3In",
        143: "token, hov3Available",
        144: "token, hov3tollAvailable",
        145: "token, walkLocalAvailable",
        146: "token, walkLrfAvailable",
        147: "token, walkExpressAvailable",
        148: "token, walkHeavyRailAvailable",
        149: "token, walkCommuterAvailable",
        150: "token, driveLocalAvailable",
        151: "token, driveLrfAvailable",
        152: "token, driveExpressAvailable",
        153: "token, driveHeavyRailAvailable",
        154: "token, driveCommuterAvailable",
        155: "token, walkFerryAvailable",
        156: "token, driveFerryAvailable",
        157: "Drive alone - Unavailable",
        158: "Drive alone - Unavailable for zero auto households",
        159: "Drive alone - Unavailable for persons less than 16",
        160: "Drive alone - Unavailable for joint tours",
        161: "Drive alone - Unavailable if didn't drive to work",
        162: "Drive alone - In-vehicle time",
        163: "Drive alone - Terminal time",
        164: "Drive alone - Operating cost ",
        165: "Drive alone - Parking cost ",
        166: "Drive alone - Bridge toll ",
        167: "Drive alone - Person is between 16 and 19 years old",
        168: "Drive alone toll - Unavailable",
        169: "Drive alone toll - Unavailable for zero auto households",
        170: "Drive alone toll - Unavailable for persons less than 16",
        171: "Drive alone toll - Unavailable for joint tours",
        172: "Drive alone toll - Unavailable if didn't drive to work",
        173: "Drive alone toll - In-vehicle time",
        174: "Drive alone toll - Terminal time",
        175: "Drive alone toll - Operating cost ",
        176: "Drive alone toll - Parking cost ",
        177: "Drive alone toll - Bridge toll ",
        178: "Drive alone toll - Value toll ",
        179: "Drive alone toll - Person is between 16 and 19 years old",
        180: "Shared ride 2 - Unavailable",
        181: "Shared ride 2 - Unavailable based on party size",
        182: "Shared ride 2 - In-vehicle time",
        183: "Shared ride 2 - Terminal time",
        184: "Shared ride 2 - Operating cost ",
        185: "Shared ride 2 - Parking cost ",
        186: "Shared ride 2 - Bridge toll ",
        187: "Shared ride 2 - One person household",
        188: "Shared ride 2 - Two person household",
        189: "Shared ride 2 - Person is 16 years old or older",
        190: "Shared ride 2 toll - Unavailable",
        191: "Shared ride 2 toll - Unavailable based on party size",
        192: "Shared ride 2 toll - In-vehicle time",
        193: "Shared ride 2 toll - Terminal time",
        194: "Shared ride 2 toll - Operating cost ",
        195: "Shared ride 2 toll - Parking cost ",
        196: "Shared ride 2 toll - Bridge toll ",
        197: "Shared ride 2 toll - Value toll ",
        198: "Shared ride 2 toll - One person household",
        199: "Shared ride 2 toll - Two person household",
        200: "Shared ride 2 toll - Person is 16 years old or older",
        201: "Shared ride 3+ - Unavailable",
        202: "Shared ride 3+ - In-vehicle time",
        203: "Shared ride 3+ - Terminal time",
        204: "Shared ride 3+ - Operating cost ",
        205: "Shared ride 3+ - Parking cost ",
        206: "Shared ride 3+ - Bridge toll ",
        207: "Shared ride 3+ - One person household",
        208: "Shared ride 3+ - Two person household",
        209: "Shared ride 3+ - Person is 16 years old or older",
        210: "Shared ride 3+ toll - Unavailable",
        211: "Shared ride 3+ toll - In-vehicle time",
        212: "Shared ride 3+ - Terminal time",
        213: "Shared ride 3+ toll - Operating cost ",
        214: "Shared ride 3+ toll - Parking cost ",
        215: "Shared ride 3+ toll - Bridge toll ",
        216: "Shared ride 3+ toll - Value toll ",
        217: "Shared ride 3+ toll - One person household",
        218: "Shared ride 3+ toll - Two person household",
        219: "Shared ride 3+ toll - Person is 16 years old or older",
        220: "Walk - Time up to 2 miles",
        221: "Walk - Time beyond 2 of a miles",
        222: "Walk - Destination zone densityIndex",
        223: "Walk - Topology",
        224: "Bike - Unavailable if didn't bike to work",
        225: "Bike - Time up to 2 miles",
        226: "Bike - Time beyond 2 of a miles",
        227: "Bike - Destination zone densityIndex",
        228: "Bike - Topology",
        229: "Walk to Local - Unavailable",
        230: "Walk to Local - In-vehicle time",
        231: "Walk to Local - Short iwait time",
        232: "Walk to Local - Long iwait time",
        233: "Walk to Local - transfer wait time",
        234: "Walk to Local - number of transfers",
        235: "Walk to Local - Walk access time",
        236: "Walk to Local - Walk egress time",
        237: "Walk to Local - Walk other time",
        238: "Walk to Local - Fare ",
        239: "Walk to Local - Destination zone densityIndex",
        240: "Walk to Local - Topology",
        241: "Walk to Local - Person is less than 10 years old",
        242: "Walk to Light rail/Ferry - Unavailable",
        243: "Walk to Light rail/Ferry - In-vehicle time",
        244: "Walk to Light rail/Ferry - In-vehicle time on Light Rail (incremental w/ ivt)",
        245: "Walk to Light rail/Ferry - In-vehicle time on Ferry (incremental w/ keyivt)",
        246: "Walk to Light rail/Ferry - Short iwait time",
        247: "Walk to Light rail/Ferry - Long iwait time",
        248: "Walk to Light rail/Ferry - transfer wait time",
        249: "Walk to Light rail/Ferry - number of transfers",
        250: "Walk to Light rail/Ferry - Walk access time",
        251: "Walk to Light rail/Ferry - Walk egress time",
        252: "Walk to Light rail/Ferry - Walk other time",
        253: "Walk to Light rail/Ferry - Fare ",
        254: "Walk to Light rail/Ferry - Destination zone densityIndex",
        255: "Walk to Light rail/Ferry - Topology",
        256: "Walk to Light rail/Ferry - Person is less than 10 years old",
        257: "Walk to Express bus - Unavailable",
        258: "Walk to Express bus - In-vehicle time",
        259: "Walk to Express bus - In-vehicle time on Express bus (incremental w/ ivt)",
        260: "Walk to Express bus - Short iwait time",
        261: "Walk to Express bus - Long iwait time",
        262: "Walk to Express bus - transfer wait time",
        263: "Walk to Express bus - number of transfers",
        264: "Walk to Express bus - Walk access time",
        265: "Walk to Express bus - Walk egress time",
        266: "Walk to Express bus - Walk other time",
        267: "Walk to Express bus - Fare ",
        268: "Walk to Express bus - Destination zone densityIndex",
        269: "Walk to Express bus - Topology",
        270: "Walk to Express bus - Person is less than 10 years old",
        271: "Walk to heavy rail - Unavailable",
        272: "Walk to heavy rail - In-vehicle time",
        273: "Walk to heavy rail - In-vehicle time on heavy rail (incremental w/ ivt)",
        274: "Walk to heavy rail - Short iwait time",
        275: "Walk to heavy rail - Long iwait time",
        276: "Walk to heavy rail - transfer wait time",
        277: "Walk to heavy rail - number of transfers",
        278: "Walk to heavy rail - Walk access time",
        279: "Walk to heavy rail - Walk egress time",
        280: "Walk to heavy rail - Walk other time",
        281: "Walk to heavy rail - Fare ",
        282: "Walk to heavy rail - Destination zone densityIndex",
        283: "Walk to heavy rail - Topology",
        284: "Walk to heavy rail - Person is less than 10 years old",
        285: "Walk to Commuter rail - Unavailable",
        286: "Walk to Commuter rail - In-vehicle time",
        287: "Walk to Commuter rail - In-vehicle time on commuter rail (incremental w/ ivt)",
        288: "Walk to Commuter rail - Short iwait time",
        289: "Walk to Commuter rail - Long iwait time",
        290: "Walk to Commuter rail - transfer wait time",
        291: "Walk to Commuter rail - number of transfers",
        292: "Walk to Commuter rail - Walk access time",
        293: "Walk to Commuter rail - Walk egress time",
        294: "Walk to Commuter rail - Walk other time",
        295: "Walk to Commuter rail - Fare ",
        296: "Walk to Commuter rail - Destination zone densityIndex",
        297: "Walk to Commuter rail - Topology",
        298: "Walk to Commuter rail - Person is less than 10 years old",
        299: "Drive to Local - Unavailable",
        300: "Drive to Local - Unavailable for zero auto households",
        301: "Drive to Local - Unavailable for persons less than 16",
        302: "Drive to Local - In-vehicle time",
        303: "Drive to Local - Short iwait time",
        304: "Drive to Local - Long iwait time",
        305: "Drive to Local - transfer wait time",
        306: "Drive to Local - number of transfers",
        307: "Drive to Local - Drive time",
        308: "Drive to Local - Walk access time (at attraction end)",
        309: "Drive to Local - Walk egress time (at attraction end)",
        310: "Drive to Local - Walk other time",
        311: "Drive to Local - Fare and operating cost ",
        312: "Drive to Local - Ratio of drive access distance to OD distance",
        313: "Drive to Local  - Destination zone densityIndex",
        314: "Drive to Local  - Topology",
        315: "Drive to Local  - Person is less than 10 years old",
        316: "Drive to Light rail/Ferry - Unavailable",
        317: "Drive to Light rail/Ferry - Unavailable for zero auto households",
        318: "Drive to Light rail/Ferry - Unavailable for persons less than 16",
        319: "Drive to Light rail/Ferry - In-vehicle time",
        320: "Drive to Light rail/Ferry - In-vehicle time on Light Rail (incremental w/ ivt)",
        321: "Drive to Light rail/Ferry - In-vehicle time on Ferry (incremental w/ keyivt)",
        322: "drive to Light rail/Ferry - Short iwait time",
        323: "drive to Light rail/Ferry - Long iwait time",
        324: "drive to Light rail/Ferry - transfer wait time",
        325: "drive to Light rail/Ferry - number of transfers",
        326: "Drive to Light rail/Ferry - Drive time",
        327: "Drive to Light rail/Ferry - Walk access time (at attraction end)",
        328: "Drive to Light rail/Ferry - Walk egress time (at attraction end)",
        329: "Drive to Light rail/Ferry - Walk other time",
        330: "Drive to Light rail/Ferry - Fare and operating cost ",
        331: "Drive to Light rail/Ferry - Ratio of drive access distance to OD distance",
        332: "Drive to Light rail/Ferry  - Destination zone densityIndex",
        333: "Drive to Light rail/Ferry  - Topology",
        334: "Drive to Light rail/Ferry  - Person is less than 10 years old",
        335: "Drive to Express bus - Unavailable",
        336: "Drive to Express bus - Unavailable for zero auto households",
        337: "Drive to Express bus - Unavailable for persons less than 16",
        338: "Drive to Express bus - In-vehicle time",
        339: "Drive to Express bus - In-vehicle time on Express bus (incremental w/ ivt)",
        340: "drive to Express bus - Short iwait time",
        341: "drive to Express bus - Long iwait time",
        342: "drive to Express bus - transfer wait time",
        343: "drive to Express bus - number of transfers",
        344: "Drive to Express bus - Drive time",
        345: "Drive to Express bus - Walk access time (at attraction end)",
        346: "Drive to Express bus - Walk egress time (at attraction end)",
        347: "Drive to Express bus - Walk other time",
        348: "Drive to Express bus - Fare and operating cost ",
        349: "Drive to Express bus - Ratio of drive access distance to OD distance",
        350: "Drive to Express bus  - Destination zone densityIndex",
        351: "Drive to Express bus  - Topology",
        352: "Drive to Express bus  - Person is less than 10 years old",
        353: "Drive to heavy rail - Unavailable",
        354: "Drive to heavy rail - Unavailable for zero auto households",
        355: "Drive to heavy rail - Unavailable for persons less than 16",
        356: "Drive to heavy rail - In-vehicle time",
        357: "Drive to heavy rail - In-vehicle time on heavy rail (incremental w/ ivt)",
        358: "drive to heavy rail - Short iwait time",
        359: "drive to heavy rail - Long iwait time",
        360: "drive to heavy rail - transfer wait time",
        361: "drive to heavy rail - number of transfers",
        362: "Drive to heavy rail - Drive time",
        363: "Drive to heavy rail - Walk access time (at attraction end)",
        364: "Drive to heavy rail - Walk egress time (at attraction end)",
        365: "Drive to heavy rail - Walk other time",
        366: "Drive to heavy rail - Fare and operating cost ",
        367: "Drive to heavy rail - Ratio of drive access distance to OD distance",
        368: "Drive to heavy rail  - Destination zone densityIndex",
        369: "Drive to heavy rail  - Topology",
        370: "Drive to heavy rail  - Person is less than 10 years old",
        371: "Drive to Commuter rail - Unavailable",
        372: "Drive to Commuter rail - Unavailable for zero auto households",
        373: "Drive to Commuter rail - Unavailable for persons less than 16",
        374: "Drive to Commuter rail - In-vehicle time",
        375: "Drive to Commuter rail - In-vehicle time on commuter rail (incremental w/ ivt)",
        376: "drive to Commuter rail - Short iwait time",
        377: "drive to Commuter rail - Long iwait time",
        378: "drive to Commuter rail - transfer wait time",
        379: "drive to Commuter rail - number of transfers",
        380: "Drive to Commuter rail - Drive time",
        381: "Drive to Commuter rail - Walk access time (at attraction end)",
        382: "Drive to Commuter rail - Walk egress time (at attraction end)",
        383: "Drive to Commuter rail - Walk other time",
        384: "Drive to Commuter rail - Fare and operating cost ",
        385: "Drive to Commuter rail - Ratio of drive access distance to OD distance",
        386: "Drive to Commuter rail  - Destination zone densityIndex",
        387: "Drive to Commuter rail  - Topology",
        388: "Drive to Commuter rail - Person is less than 10 years old",
        389: "Taxi - In-vehicle time",
        390: "Taxi - Wait time",
        391: "Taxi - Tolls",
        392: "Taxi - Bridge toll",
        393: "Taxi - Fare",
        394: "TNC Single - In-vehicle time",
        395: "TNC Single - Wait time",
        396: "TNC Single - Tolls",
        397: "TNC Single - Bridge toll",
        398: "TNC Single - Cost",
        399: "TNC Shared - In-vehicle time",
        400: "TNC Shared - Wait time",
        401: "TNC Shared - Tolls",
        402: "TNC Shared - Bridge toll",
        403: "TNC Shared - Cost",
        404: "Walk - Alternative-specific constant - Zero auto",
        405: "Walk - Alternative-specific constant - Auto deficient",
        406: "Walk - Alternative-specific constant - Auto sufficient",
        407: "Bike - Alternative-specific constant - Zero auto",
        408: "Bike - Alternative-specific constant - Auto deficient",
        409: "Bike - Alternative-specific constant - Auto sufficient",
        410: "Shared ride 2 - Alternative-specific constant - Zero auto",
        411: "Shared ride 2 - Alternative-specific constant - Auto deficient",
        412: "Shared ride 2 - Alternative-specific constant - Auto sufficient",
        413: "Shared ride 3+ - Alternative-specific constant - Zero auto",
        414: "Shared ride 3+ - Alternative-specific constant - Auto deficient",
        415: "Shared ride 3+ - Alternative-specific constant - Auto sufficient",
        416: "Walk to Transit - Alternative-specific constant - Zero auto",
        417: "Walk to Transit - Alternative-specific constant - Auto deficient",
        418: "Walk to Transit - Alternative-specific constant - Auto sufficient",
        419: "Drive to Transit  - Alternative-specific constant - Zero auto",
        420: "Drive to Transit  - Alternative-specific constant - Auto deficient",
        421: "Drive to Transit  - Alternative-specific constant - Auto sufficient",
        422: "Taxi - Alternative-specific constant - Zero auto",
        423: "Taxi - Alternative-specific constant - Auto deficient",
        424: "Taxi - Alternative-specific constant - Auto sufficient",
        425: "TNC-Single - Alternative-specific constant - Zero auto",
        426: "TNC-Single - Alternative-specific constant - Auto deficient",
        427: "TNC-Single - Alternative-specific constant - Auto sufficient",
        428: "TNC-Shared - Alternative-specific constant - Zero auto",
        429: "TNC-Shared - Alternative-specific constant - Auto deficient",
        430: "TNC-Shared - Alternative-specific constant - Auto sufficient",
        431: "Walk - Alternative-specific constant - Joint Tours",
        432: "Walk - Alternative-specific constant - Joint Tours",
        433: "Walk - Alternative-specific constant - Joint Tours",
        434: "Bike - Alternative-specific constant - Joint Tours",
        435: "Bike - Alternative-specific constant - Joint Tours",
        436: "Bike - Alternative-specific constant - Joint Tours",
        437: "Shared ride 2 - Alternative-specific constant - Joint Tours",
        438: "Shared ride 2 - Alternative-specific constant - Joint Tours",
        439: "Shared ride 2 - Alternative-specific constant - Joint Tours",
        440: "Shared ride 3+ - Alternative-specific constant - Joint Tours",
        441: "Shared ride 3+ - Alternative-specific constant - Joint Tours",
        442: "Shared ride 3+ - Alternative-specific constant - Joint Tours",
        443: "Walk to Transit - Alternative-specific constant - Joint Tours",
        444: "Walk to Transit - Alternative-specific constant - Joint Tours",
        445: "Walk to Transit - Alternative-specific constant - Joint Tours",
        446: "Drive to Transit  - Alternative-specific constant - Joint Tours",
        447: "Drive to Transit  - Alternative-specific constant - Joint Tours",
        448: "Drive to Transit  - Alternative-specific constant - Joint Tours",
        449: "Taxi - Alternative-specific constant - Zero auto - Joint Tours",
        450: "Taxi - Alternative-specific constant - Auto deficient - Joint Tours",
        451: "Taxi - Alternative-specific constant - Auto sufficient - Joint Tours",
        452: "TNC-Single - Alternative-specific constant - Zero auto - Joint Tours",
        453: "TNC-Single - Alternative-specific constant - Auto deficient - Joint Tours",
        454: "TNC-Single - Alternative-specific constant - Auto sufficient - Joint Tours",
        455: "TNC-Shared - Alternative-specific constant - Zero auto - Joint Tours",
        456: "TNC-Shared - Alternative-specific constant - Auto deficient - Joint Tours",
        457: "TNC-Shared - Alternative-specific constant - Auto sufficient - Joint Tours",
        458: "Local bus",
        459: "Light rail - Alternative-specific constant (walk access)",
        460: "Light rail - Alternative-specific constant (drive access)",
        461: "Ferry - Alternative-specific constant (walk access)",
        462: "Ferry - Alternative-specific constant (drive access)",
        463: "Express bus - Alternative-specific constant",
        464: "Heavy rail - Alternative-specific constant ",
        465: "Commuter rail - Alternative-specific constant ",
        466: "Walk to Transit - CBD dummy",
        467: "Drive to Transit  - CBD dummy",
        468: "Walk to Transit - San Francisco dummy",
        469: "Drive to Transit - San Francisco dummy",
        470: "Walk to Transit - Within SF dummy",
        471: "Drive to Transit - Within SF dummy",
        472: "Walk to Transit - from San Francisco dummy",
        473: "Drive to Transit - from San Francisco dummy",
        474: "Drive to Transit - distance penalty",
        475: "Walk not available for long distances",
        476: "Bike not available for long distances",
        477: "Transit hesitance - local bus",
        478: "Transit hesitance - walk to light rail",
        479: "Transit hesitance - drive to light rail",
        480: "Transit hesitance - walk to ferry",
        481: "Transit hesitance - drive to ferry",
        482: "Transit hesitance - express bus",
        483: "Transit hesitance - heavy rail",
        484: "Transit hesitance - commuter rail",
        485: "Rail hesitance - heavy rail",
        486: "Rail hesitance - commuter rail",
        487: "TNC single adjustment",
        488: "TNC shared adjustment",
        489: "PBA50 Blueprint bike infra constant",
    }

    UNIVERSITY_ROW_NAMES = {
        1:  "token, terminalTime",
        2:  "token, freeParkingAllowed",
        3:  "token, freeParkingAvailable",
        4:  "token, hourlyParkingCost",
        5:  "token, destTopology",
        6:  "token, destCounty",
        7:  "token, origCounty",
        8:  "token, valueOfTime",
        9:  "token, autos",
        10: "token, workers",
        11: "token, hhSize",
        12: "token, hhIncomeQ1",
        13: "token, hhIncomeQ2",
        14: "token, age",
        15: "token, timeOutbound",
        16: "token, timeInbound",
        17: "token, tourDuration",
        18: "token, tourCategoryJoint",
        19: "token, numberOfParticipantsInJointTour",
        20: "token, tourCategorySubtour",
        21: "token, workTourModeIsSOV",
        22: "token, workTourModeIsBike",
        23: "token, destZoneAreaType",
        24: "token, originDensityIndex",
        25: "token, densityIndex",
        26: "token, zonalShortWalkOrig",
        27: "token, zonalLongWalkOrig",
        28: "token, zonalShortWalkDest",
        29: "token, zonalLongWalkDest",
        30: "token, c_ivt",
        31: "token, c_ivt_lrt",
        32: "token, c_ivt_ferry",
        33: "token, c_ivt_exp",
        34: "token, c_ivt_hvy",
        35: "token, c_ivt_com",
        36: "token, c_walkTimeShort",
        37: "token, c_walkTimeLong",
        38: "token, c_bikeTimeShort",
        39: "token, c_bikeTimeLong",
        40: "token, c_cost",
        41: "token, c_shortiWait",
        42: "token, c_longiWait",
        43: "token, c_wacc",
        44: "token, c_wegr",
        45: "token, c_waux",
        46: "token, c_dtim",
        47: "token, c_xwait",
        48: "token, c_dacc_ratio",
        49: "token, c_xfers_wlk",
        50: "token, c_xfers_drv",
        51: "token, c_drvtrn_distpen_0",
        52: "token, c_drvtrn_distpen_max",
        53: "token, c_topology_walk",
        54: "token, c_topology_bike",
        55: "token, c_topology_trn",
        56: "token, c_densityIndex",
        57: "token, c_age1619_da",
        58: "token, c_age010_trn",
        59: "token, c_age16p_sr",
        60: "token, c_hhsize1_sr",
        61: "token, c_hhsize2_sr",
        62: "token, costPerMile",
        63: "token, costShareSr2",
        64: "token, costShareSr3",
        65: "token, waitThresh",
        66: "token, walkThresh",
        67: "token, shortWalk",
        68: "token, longWalk",
        69: "token, walkSpeed",
        70: "token, bikeThresh",
        71: "token, bikeSpeed",
        72: "token, maxCbdAreaTypeThresh",
        73: "token, indivTour",
        74: "token, upperEA",
        75: "token, upperAM",
        76: "token, upperMD",
        77: "token, upperPM",
        78: "token, zeroAutoHh",
        79: "token, autoDeficientHh",
        80: "token, autoSufficientHh",
        81: "token, shortWalkMax",
        82: "token, longWalkMax",
        83: "token, walkTransitOrig",
        84: "token, walkTransitDest",
        85: "token, walkTransitAvailable",
        86: "token, driveTransitAvailable",
        87: "token, originWalkTime",
        88: "token, originWalkTime",
        89: "token, destinationWalkTime",
        90: "token, destinationWalkTime",
        91: "token, cbdDummy",
        92: "token, dailyParkingCost",
        93: "token, costInitialTaxi",
        94: "token, costPerMileTaxi",
        95: "token, costPerMinuteTaxi",
        96: "token, costInitialSingleTNC",
        97: "token, costPerMileSingleTNC",
        98: "token, costPerMinuteSingleTNC",
        99: "token, costMinimumSingleTNC",
        100:"token, costInitialSharedTNC",
        101:"token, costPerMileSharedTNC",
        102:"token, costPerMinuteSharedTNC",
        103:"token, costMinimumSharedTNC",
        104:"token, totalWaitTaxi",
        105:"token, totalWaitSingleTNC",
        106:"token, totalWaitSharedTNC",
        107:"token, autoIVTFactorAV",
        108:"token, autoParkingCostFactorAV",
        109:"token, autoCostPerMileFactorAV",
        110:"token, autoTerminalTimeFactorAV",
        111:"token, sharedTNCIVTFactor",
        112:"token, useAV",
        113:"token, autoIVTFactor",
        114:"token, autoParkingCostFactor",
        115:"token, autoCPMFactor",
        116:"token, autoTermTimeFactor",
        117:"token, outPeriod",
        118:"token, outPeriod",
        119:"token, outPeriod",
        120:"token, outPeriod",
        121:"token, outPeriod",
        122:"token, inPeriod",
        123:"token, inPeriod",
        124:"token, inPeriod",
        125:"token, inPeriod",
        126:"token, inPeriod",
        127:"token, destCordon",
        128:"token, destCordonPrice",
        129:"token, origCordon",
        130:"token, origCordonPrice",
        131:"token, sovOut",
        132:"token, sovIn",
        133:"token, sovAvailable",
        134:"token, sovtollAvailable",
        135:"token, hov2Out",
        136:"token, hov2In",
        137:"token, hov2Available",
        138:"token, hov2tollAvailable",
        139:"token, hov3Out",
        140:"token, hov3In",
        141:"token, hov3Available",
        142:"token, hov3tollAvailable",
        143:"token, walkLocalAvailable",
        144:"token, walkLrfAvailable",
        145:"token, walkExpressAvailable",
        146:"token, walkHeavyRailAvailable",
        147:"token, walkCommuterAvailable",
        148:"token, driveLocalAvailable",
        149:"token, driveLrfAvailable",
        150:"token, driveExpressAvailable",
        151:"token, driveHeavyRailAvailable",
        152:"token, driveCommuterAvailable",
        153:"token, walkFerryAvailable",
        154:"token, driveFerryAvailable",
        155:"Drive alone - Unavailable",
        156:"Drive alone - Unavailable for zero auto households",
        157:"Drive alone - Unavailable for persons less than 16",
        158:"Drive alone - Unavailable for joint tours",
        159:"Drive alone - Unavailable if didn't drive to work",
        160:"Drive alone - In-vehicle time",
        161:"Drive alone - Terminal time",
        162:"Drive alone - Operating cost ",
        163:"Drive alone - Parking cost ",
        164:"Drive alone - Bridge toll ",
        165:"Drive alone - Person is between 16 and 19 years old",
        166:"Drive alone toll - Unavailable",
        167:"Drive alone toll - Unavailable for zero auto households",
        168:"Drive alone toll - Unavailable for persons less than 16",
        169:"Drive alone toll - Unavailable for joint tours",
        170:"Drive alone toll - Unavailable if didn't drive to work",
        171:"Drive alone toll - In-vehicle time",
        172:"Drive alone toll - Terminal time",
        173:"Drive alone toll - Operating cost ",
        174:"Drive alone toll - Parking cost ",
        175:"Drive alone toll - Bridge toll ",
        176:"Drive alone toll - Value toll ",
        177:"Drive alone toll - Person is between 16 and 19 years old",
        178:"Shared ride 2 - Unavailable",
        179:"Shared ride 2 - Unavailable based on party size",
        180:"Shared ride 2 - In-vehicle time",
        181:"Shared ride 2 - Terminal time",
        182:"Shared ride 2 - Operating cost ",
        183:"Shared ride 2 - Parking cost ",
        184:"Shared ride 2 - Bridge toll ",
        185:"Shared ride 2 - One person household",
        186:"Shared ride 2 - Two person household",
        187:"Shared ride 2 - Person is 16 years old or older",
        188:"Shared ride 2 toll - Unavailable",
        189:"Shared ride 2 toll - Unavailable based on party size",
        190:"Shared ride 2 toll - In-vehicle time",
        191:"Shared ride 2 toll - Terminal time",
        192:"Shared ride 2 toll - Operating cost ",
        193:"Shared ride 2 toll - Parking cost ",
        194:"Shared ride 2 toll - Bridge toll ",
        195:"Shared ride 2 toll - Value toll ",
        196:"Shared ride 2 toll - One person household",
        197:"Shared ride 2 toll - Two person household",
        198:"Shared ride 2 toll - Person is 16 years old or older",
        199:"Shared ride 3+ - Unavailable",
        200:"Shared ride 3+ - In-vehicle time",
        201:"Shared ride 3+ - Terminal time",
        202:"Shared ride 3+ - Operating cost ",
        203:"Shared ride 3+ - Parking cost ",
        204:"Shared ride 3+ - Bridge toll ",
        205:"Shared ride 3+ - One person household",
        206:"Shared ride 3+ - Two person household",
        207:"Shared ride 3+ - Person is 16 years old or older",
        208:"Shared ride 3+ toll - Unavailable",
        209:"Shared ride 3+ toll - In-vehicle time",
        210:"Shared ride 3+ - Terminal time",
        211:"Shared ride 3+ toll - Operating cost ",
        212:"Shared ride 3+ toll - Parking cost ",
        213:"Shared ride 3+ toll - Bridge toll ",
        214:"Shared ride 3+ toll - Value toll ",
        215:"Shared ride 3+ toll - One person household",
        216:"Shared ride 3+ toll - Two person household",
        217:"Shared ride 3+ toll - Person is 16 years old or older",
        218:"Walk - Time up to 2 miles",
        219:"Walk - Time beyond 2 of a miles",
        220:"Walk - Destination zone densityIndex",
        221:"Walk - Topology",
        222:"Bike - Unavailable if didn't bike to work",
        223:"Bike - Time up to 2 miles",
        224:"Bike - Time beyond 2 of a miles",
        225:"Bike - Destination zone densityIndex",
        226:"Bike - Topology",
        227:"Walk to Local - Unavailable",
        228:"Walk to Local - In-vehicle time",
        229:"Walk to Local - Short iwait time",
        230:"Walk to Local - Long iwait time",
        231:"Walk to Local - transfer wait time",
        232:"Walk to Local - number of transfers",
        233:"Walk to Local - Walk access time",
        234:"Walk to Local - Walk egress time",
        235:"Walk to Local - Walk other time",
        236:"Walk to Local - Fare ",
        237:"Walk to Local - Destination zone densityIndex",
        238:"Walk to Local - Topology",
        239:"Walk to Local - Person is less than 10 years old",
        240:"Walk to Light rail/Ferry - Unavailable",
        241:"Walk to Light rail/Ferry - In-vehicle time",
        242:"Walk to Light rail/Ferry - In-vehicle time on Light Rail (incremental w/ ivt)",
        243:"Walk to Light rail/Ferry - In-vehicle time on Ferry (incremental w/ keyivt)",
        244:"Walk to Light rail/Ferry - Short iwait time",
        245:"Walk to Light rail/Ferry - Long iwait time",
        246:"Walk to Light rail/Ferry - transfer wait time",
        247:"Walk to Light rail/Ferry - number of transfers",
        248:"Walk to Light rail/Ferry - Walk access time",
        249:"Walk to Light rail/Ferry - Walk egress time",
        250:"Walk to Light rail/Ferry - Walk other time",
        251:"Walk to Light rail/Ferry - Fare ",
        252:"Walk to Light rail/Ferry - Destination zone densityIndex",
        253:"Walk to Light rail/Ferry - Topology",
        254:"Walk to Light rail/Ferry - Person is less than 10 years old",
        255:"Walk to Express bus - Unavailable",
        256:"Walk to Express bus - In-vehicle time",
        257:"Walk to Express bus - In-vehicle time on Express bus (incremental w/ ivt)",
        258:"Walk to Express bus - Short iwait time",
        259:"Walk to Express bus - Long iwait time",
        260:"Walk to Express bus - transfer wait time",
        261:"Walk to Express bus - number of transfers",
        262:"Walk to Express bus - Walk access time",
        263:"Walk to Express bus - Walk egress time",
        264:"Walk to Express bus - Walk other time",
        265:"Walk to Express bus - Fare ",
        266:"Walk to Express bus - Destination zone densityIndex",
        267:"Walk to Express bus - Topology",
        268:"Walk to Express bus - Person is less than 10 years old",
        269:"Walk to heavy rail - Unavailable",
        270:"Walk to heavy rail - In-vehicle time",
        271:"Walk to heavy rail - In-vehicle time on heavy rail (incremental w/ ivt)",
        272:"Walk to heavy rail - Short iwait time",
        273:"Walk to heavy rail - Long iwait time",
        274:"Walk to heavy rail - transfer wait time",
        275:"Walk to heavy rail - number of transfers",
        276:"Walk to heavy rail - Walk access time",
        277:"Walk to heavy rail - Walk egress time",
        278:"Walk to heavy rail - Walk other time",
        279:"Walk to heavy rail - Fare ",
        280:"Walk to heavy rail - Destination zone densityIndex",
        281:"Walk to heavy rail - Topology",
        282:"Walk to heavy rail - Person is less than 10 years old",
        283:"Walk to Commuter rail - Unavailable",
        284:"Walk to Commuter rail - In-vehicle time",
        285:"Walk to Commuter rail - In-vehicle time on commuter rail (incremental w/ ivt)",
        286:"Walk to Commuter rail - Short iwait time",
        287:"Walk to Commuter rail - Long iwait time",
        288:"Walk to Commuter rail - transfer wait time",
        289:"Walk to Commuter rail - number of transfers",
        290:"Walk to Commuter rail - Walk access time",
        291:"Walk to Commuter rail - Walk egress time",
        292:"Walk to Commuter rail - Walk other time",
        293:"Walk to Commuter rail - Fare ",
        294:"Walk to Commuter rail - Destination zone densityIndex",
        295:"Walk to Commuter rail - Topology",
        296:"Walk to Commuter rail - Person is less than 10 years old",
        297:"Drive to Local - Unavailable",
        298:"Drive to Local - Unavailable for zero auto households",
        299:"Drive to Local - Unavailable for persons less than 16",
        300:"Drive to Local - In-vehicle time",
        301:"Drive to Local - Short iwait time",
        302:"Drive to Local - Long iwait time",
        303:"Drive to Local - transfer wait time",
        304:"Drive to Local - number of transfers",
        305:"Drive to Local - Drive time",
        306:"Drive to Local - Walk access time (at attraction end)",
        307:"Drive to Local - Walk egress time (at attraction end)",
        308:"Drive to Local - Walk other time",
        309:"Drive to Local - Fare and operating cost ",
        310:"Drive to Local - Ratio of drive access distance to OD distance",
        311:"Drive to Local  - Destination zone densityIndex",
        312:"Drive to Local  - Topology",
        313:"Drive to Local  - Person is less than 10 years old",
        314:"Drive to Light rail/Ferry - Unavailable",
        315:"Drive to Light rail/Ferry - Unavailable for zero auto households",
        316:"Drive to Light rail/Ferry - Unavailable for persons less than 16",
        317:"Drive to Light rail/Ferry - In-vehicle time",
        318:"Drive to Light rail/Ferry - In-vehicle time on Light Rail (incremental w/ ivt)",
        319:"Drive to Light rail/Ferry - In-vehicle time on Ferry (incremental w/ keyivt)",
        320:"drive to Light rail/Ferry - Short iwait time",
        321:"drive to Light rail/Ferry - Long iwait time",
        322:"drive to Light rail/Ferry - transfer wait time",
        323:"drive to Light rail/Ferry - number of transfers",
        324:"Drive to Light rail/Ferry - Drive time",
        325:"Drive to Light rail/Ferry - Walk access time (at attraction end)",
        326:"Drive to Light rail/Ferry - Walk egress time (at attraction end)",
        327:"Drive to Light rail/Ferry - Walk other time",
        328:"Drive to Light rail/Ferry - Fare and operating cost ",
        329:"Drive to Light rail/Ferry - Ratio of drive access distance to OD distance",
        330:"Drive to Light rail/Ferry  - Destination zone densityIndex",
        331:"Drive to Light rail/Ferry  - Topology",
        332:"Drive to Light rail/Ferry  - Person is less than 10 years old",
        333:"Drive to Express bus - Unavailable",
        334:"Drive to Express bus - Unavailable for zero auto households",
        335:"Drive to Express bus - Unavailable for persons less than 16",
        336:"Drive to Express bus - In-vehicle time",
        337:"Drive to Express bus - In-vehicle time on Express bus (incremental w/ ivt)",
        338:"drive to Express bus - Short iwait time",
        339:"drive to Express bus - Long iwait time",
        340:"drive to Express bus - transfer wait time",
        341:"drive to Express bus - number of transfers",
        342:"Drive to Express bus - Drive time",
        343:"Drive to Express bus - Walk access time (at attraction end)",
        344:"Drive to Express bus - Walk egress time (at attraction end)",
        345:"Drive to Express bus - Walk other time",
        346:"Drive to Express bus - Fare and operating cost ",
        347:"Drive to Express bus - Ratio of drive access distance to OD distance",
        348:"Drive to Express bus  - Destination zone densityIndex",
        349:"Drive to Express bus  - Topology",
        350:"Drive to Express bus  - Person is less than 10 years old",
        351:"Drive to heavy rail - Unavailable",
        352:"Drive to heavy rail - Unavailable for zero auto households",
        353:"Drive to heavy rail - Unavailable for persons less than 16",
        354:"Drive to heavy rail - In-vehicle time",
        355:"Drive to heavy rail - In-vehicle time on heavy rail (incremental w/ ivt)",
        356:"drive to heavy rail - Short iwait time",
        357:"drive to heavy rail - Long iwait time",
        358:"drive to heavy rail - transfer wait time",
        359:"drive to heavy rail - number of transfers",
        360:"Drive to heavy rail - Drive time",
        361:"Drive to heavy rail - Walk access time (at attraction end)",
        362:"Drive to heavy rail - Walk egress time (at attraction end)",
        363:"Drive to heavy rail - Walk other time",
        364:"Drive to heavy rail - Fare and operating cost ",
        365:"Drive to heavy rail - Ratio of drive access distance to OD distance",
        366:"Drive to heavy rail  - Destination zone densityIndex",
        367:"Drive to heavy rail  - Topology",
        368:"Drive to heavy rail  - Person is less than 10 years old",
        369:"Drive to Commuter rail - Unavailable",
        370:"Drive to Commuter rail - Unavailable for zero auto households",
        371:"Drive to Commuter rail - Unavailable for persons less than 16",
        372:"Drive to Commuter rail - In-vehicle time",
        373:"Drive to Commuter rail - In-vehicle time on commuter rail (incremental w/ ivt)",
        374:"drive to Commuter rail - Short iwait time",
        375:"drive to Commuter rail - Long iwait time",
        376:"drive to Commuter rail - transfer wait time",
        377:"drive to Commuter rail - number of transfers",
        378:"Drive to Commuter rail - Drive time",
        379:"Drive to Commuter rail - Walk access time (at attraction end)",
        380:"Drive to Commuter rail - Walk egress time (at attraction end)",
        381:"Drive to Commuter rail - Walk other time",
        382:"Drive to Commuter rail - Fare and operating cost ",
        383:"Drive to Commuter rail - Ratio of drive access distance to OD distance",
        384:"Drive to Commuter rail  - Destination zone densityIndex",
        385:"Drive to Commuter rail  - Topology",
        386:"Drive to Commuter rail - Person is less than 10 years old",
        387:"Taxi - In-vehicle time",
        388:"Taxi - Wait time",
        389:"Taxi - Tolls",
        390:"Taxi - Bridge toll",
        391:"Taxi - Fare",
        392:"TNC Single - In-vehicle time",
        393:"TNC Single - Wait time",
        394:"TNC Single - Tolls",
        395:"TNC Single - Bridge toll",
        396:"TNC Single - Cost",
        397:"TNC Shared - In-vehicle time",
        398:"TNC Shared - Wait time",
        399:"TNC Shared - Tolls",
        400:"TNC Shared - Bridge toll",
        401:"TNC Shared - Cost",
        402:"Walk - Alternative-specific constant - Zero auto",
        403:"Walk - Alternative-specific constant - Auto deficient",
        404:"Walk - Alternative-specific constant - Auto sufficient",
        405:"Bike - Alternative-specific constant - Zero auto",
        406:"Bike - Alternative-specific constant - Auto deficient",
        407:"Bike - Alternative-specific constant - Auto sufficient",
        408:"Shared ride 2 - Alternative-specific constant - Zero auto",
        409:"Shared ride 2 - Alternative-specific constant - Auto deficient",
        410:"Shared ride 2 - Alternative-specific constant - Auto sufficient",
        411:"Shared ride 3+ - Alternative-specific constant - Zero auto",
        412:"Shared ride 3+ - Alternative-specific constant - Auto deficient",
        413:"Shared ride 3+ - Alternative-specific constant - Auto sufficient",
        414:"Walk to Transit - Alternative-specific constant - Zero auto",
        415:"Walk to Transit - Alternative-specific constant - Auto deficient",
        416:"Walk to Transit - Alternative-specific constant - Auto sufficient",
        417:"Drive to Transit  - Alternative-specific constant - Zero auto",
        418:"Drive to Transit  - Alternative-specific constant - Auto deficient",
        419:"Drive to Transit  - Alternative-specific constant - Auto sufficient",
        420:"Taxi - Alternative-specific constant - Zero auto",
        421:"Taxi - Alternative-specific constant - Auto deficient",
        422:"Taxi - Alternative-specific constant - Auto sufficient",
        423:"TNC-Single - Alternative-specific constant - Zero auto",
        424:"TNC-Single - Alternative-specific constant - Auto deficient",
        425:"TNC-Single - Alternative-specific constant - Auto sufficient",
        426:"TNC-Shared - Alternative-specific constant - Zero auto",
        427:"TNC-Shared - Alternative-specific constant - Auto deficient",
        428:"TNC-Shared - Alternative-specific constant - Auto sufficient",
        429:"Walk - Alternative-specific constant - Joint Tours",
        430:"Walk - Alternative-specific constant - Joint Tours",
        431:"Walk - Alternative-specific constant - Joint Tours",
        432:"Bike - Alternative-specific constant - Joint Tours",
        433:"Bike - Alternative-specific constant - Joint Tours",
        434:"Bike - Alternative-specific constant - Joint Tours",
        435:"Shared ride 2 - Alternative-specific constant - Joint Tours",
        436:"Shared ride 2 - Alternative-specific constant - Joint Tours",
        437:"Shared ride 2 - Alternative-specific constant - Joint Tours",
        438:"Shared ride 3+ - Alternative-specific constant - Joint Tours",
        439:"Shared ride 3+ - Alternative-specific constant - Joint Tours",
        440:"Shared ride 3+ - Alternative-specific constant - Joint Tours",
        441:"Walk to Transit - Alternative-specific constant - Joint Tours",
        442:"Walk to Transit - Alternative-specific constant - Joint Tours",
        443:"Walk to Transit - Alternative-specific constant - Joint Tours",
        444:"Drive to Transit  - Alternative-specific constant - Joint Tours",
        445:"Drive to Transit  - Alternative-specific constant - Joint Tours",
        446:"Drive to Transit  - Alternative-specific constant - Joint Tours",
        447:"Taxi - Alternative-specific constant - Zero auto - Joint Tours",
        448:"Taxi - Alternative-specific constant - Auto deficient - Joint Tours",
        449:"Taxi - Alternative-specific constant - Auto sufficient - Joint Tours",
        450:"TNC-Single - Alternative-specific constant - Zero auto - Joint Tours",
        451:"TNC-Single - Alternative-specific constant - Auto deficient - Joint Tours",
        452:"TNC-Single - Alternative-specific constant - Auto sufficient - Joint Tours",
        453:"TNC-Shared - Alternative-specific constant - Zero auto - Joint Tours",
        454:"TNC-Shared - Alternative-specific constant - Auto deficient - Joint Tours",
        455:"TNC-Shared - Alternative-specific constant - Auto sufficient - Joint Tours",
        456:"Local bus",
        457:"Light rail - Alternative-specific constant (walk access)",
        458:"Light rail - Alternative-specific constant (drive access)",
        459:"Ferry - Alternative-specific constant (walk access)",
        460:"Ferry - Alternative-specific constant (drive access)",
        461:"Express bus - Alternative-specific constant",
        462:"Heavy rail - Alternative-specific constant ",
        463:"Commuter rail - Alternative-specific constant ",
        464:"Walk to Transit - to CBD dummy",
        465:"Drive to Transit - to CBD dummy",
        466:"Walk to Transit - to San Francisco dummy",
        467:"Drive to Transit - to San Francisco dummy",
        468:"Walk to Transit - Within SF dummy",
        469:"Drive to Transit - Within SF dummy",
        470:"Walk to Transit - from San Francisco dummy",
        471:"Drive to Transit - from San Francisco dummy",
        472:"Drive to Transit - distance penalty",
        473:"Walk not available for long distances",
        474:"Bike not available for long distances",
        475:"Transit hesitance - local bus",
        476:"Transit hesitance - walk to light rail",
        477:"Transit hesitance - drive to light rail",
        478:"Transit hesitance - walk to ferry",
        479:"Transit hesitance - drive to ferry",
        480:"Transit hesitance - express bus",
        481:"Transit hesitance - heavy rail",
        482:"Transit hesitance - commuter rail",
        483:"Rail hesitance - heavy rail",
        484:"Rail hesitance - commuter rail",
        485:"TNC single adjustment",
        486:"TNC shared adjustment",
        487:"PBA50 Blueprint bike infra constant",
    }

    # from ModeChoice.xls UEC, Shopping
    SHOPPING_ROW_NAMES = {
        1  : "token, terminalTime",
        2  : "token, freeParkingAllowed",
        3  : "token, freeParkingAvailable",
        4  : "token, hourlyParkingCost",
        5  : "token, destTopology",
        6  : "token, destCounty",
        7  : "token, origCounty",
        8  : "token, valueOfTime",
        9  : "token, autos",
        10 : "token, workers",
        11 : "token, hhSize",
        12 : "token, hhIncomeQ1",
        13 : "token, hhIncomeQ2",
        14 : "token, hhIncomePercentOfPoverty",
        15 : "token, hhUnderPovertyThreshold",
        16 : "token, age",
        17 : "token, timeOutbound",
        18 : "token, timeInbound",
        19 : "token, tourDuration",
        20 : "token, tourCategoryJoint",
        21 : "token, numberOfParticipantsInJointTour",
        22 : "token, tourCategorySubtour",
        23 : "token, workTourModeIsSOV",
        24 : "token, workTourModeIsBike",
        25 : "token, destZoneAreaType",
        26 : "token, originDensityIndex",
        27 : "token, densityIndex",
        28 : "token, zonalShortWalkOrig",
        29 : "token, zonalLongWalkOrig",
        30 : "token, zonalShortWalkDest",
        31 : "token, zonalLongWalkDest",
        32 : "token, c_ivt",
        33 : "token, c_ivt_lrt",
        34 : "token, c_ivt_ferry",
        35 : "token, c_ivt_exp",
        36 : "token, c_ivt_hvy",
        37 : "token, c_ivt_com",
        38 : "token, c_walkTimeShort",
        39 : "token, c_walkTimeLong",
        40 : "token, c_bikeTimeShort",
        41 : "token, c_bikeTimeLong",
        42 : "token, c_cost",
        43 : "token, c_shortiWait",
        44 : "token, c_longiWait",
        45 : "token, c_wacc",
        46 : "token, c_wegr",
        47 : "token, c_waux",
        48 : "token, c_dtim",
        49 : "token, c_xwait",
        50 : "token, c_dacc_ratio",
        51 : "token, c_xfers_wlk",
        52 : "token, c_xfers_drv",
        53 : "token, c_drvtrn_distpen_0",
        54 : "token, c_drvtrn_distpen_max",
        55 : "token, c_topology_walk",
        56 : "token, c_topology_bike",
        57 : "token, c_topology_trn",
        58 : "token, c_densityIndex",
        59 : "token, c_age1619_da",
        60 : "token, c_age010_trn",
        61 : "token, c_age16p_sr",
        62 : "token, c_hhsize1_sr",
        63 : "token, c_hhsize2_sr",
        64 : "token, costPerMile",
        65 : "token, costShareSr2",
        66 : "token, costShareSr3",
        67 : "token, waitThresh",
        68 : "token, walkThresh",
        69 : "token, shortWalk",
        70 : "token, longWalk",
        71 : "token, walkSpeed",
        72 : "token, bikeThresh",
        73 : "token, bikeSpeed",
        74 : "token, maxCbdAreaTypeThresh",
        75 : "token, indivTour",
        76 : "token, upperEA",
        77 : "token, upperAM",
        78 : "token, upperMD",
        79 : "token, upperPM",
        80 : "token, zeroAutoHh",
        81 : "token, autoDeficientHh",
        82 : "token, autoSufficientHh",
        83 : "token, shortWalkMax",
        84 : "token, longWalkMax",
        85 : "token, walkTransitOrig",
        86 : "token, walkTransitDest",
        87 : "token, walkTransitAvailable",
        88 : "token, driveTransitAvailable",
        89 : "token, originWalkTime",
        90 : "token, originWalkTime",
        91 : "token, destinationWalkTime",
        92 : "token, destinationWalkTime",
        93 : "token, cbdDummy",
        94 : "token, dailyParkingCost",
        95 : "token, costInitialTaxi",
        96 : "token, costPerMileTaxi",
        97 : "token, costPerMinuteTaxi",
        98 : "token, costInitialSingleTNC",
        99 : "token, costPerMileSingleTNC",
        100: "token, costPerMinuteSingleTNC",
        101: "token, costMinimumSingleTNC",
        102: "token, costInitialSharedTNC",
        103: "token, costPerMileSharedTNC",
        104: "token, costPerMinuteSharedTNC",
        105: "token, costMinimumSharedTNC",
        106: "token, totalWaitTaxi",
        107: "token, totalWaitSingleTNC",
        108: "token, totalWaitSharedTNC",
        109: "token, autoIVTFactorAV",
        110: "token, autoParkingCostFactorAV",
        111: "token, autoCostPerMileFactorAV",
        112: "token, autoTerminalTimeFactorAV",
        113: "token, sharedTNCIVTFactor",
        114: "token, useAV",
        115: "token, autoIVTFactor",
        116: "token, autoParkingCostFactor",
        117: "token, autoCPMFactor",
        118: "token, autoTermTimeFactor",
        119: "token, outPeriod",
        120: "token, outPeriod",
        121: "token, outPeriod",
        122: "token, outPeriod",
        123: "token, outPeriod",
        124: "token, inPeriod",
        125: "token, inPeriod",
        126: "token, inPeriod",
        127: "token, inPeriod",
        128: "token, inPeriod",
        129: "token, destCordon",
        130: "token, destCordonPrice",
        131: "token, origCordon",
        132: "token, origCordonPrice",
        133: "token, sovOut",
        134: "token, sovIn",
        135: "token, sovAvailable",
        136: "token, sovtollAvailable",
        137: "token, hov2Out",
        138: "token, hov2In",
        139: "token, hov2Available",
        140: "token, hov2tollAvailable",
        141: "token, hov3Out",
        142: "token, hov3In",
        143: "token, hov3Available",
        144: "token, hov3tollAvailable",
        145: "token, walkLocalAvailable",
        146: "token, walkLrfAvailable",
        147: "token, walkExpressAvailable",
        148: "token, walkHeavyRailAvailable",
        149: "token, walkCommuterAvailable",
        150: "token, driveLocalAvailable",
        151: "token, driveLrfAvailable",
        152: "token, driveExpressAvailable",
        153: "token, driveHeavyRailAvailable",
        154: "token, driveCommuterAvailable",
        155: "token, walkFerryAvailable",
        156: "token, driveFerryAvailable",
        157: "Drive alone - Unavailable",
        158: "Drive alone - Unavailable for zero auto households",
        159: "Drive alone - Unavailable for persons less than 16",
        160: "Drive alone - Unavailable for joint tours",
        161: "Drive alone - Unavailable if didn't drive to work",
        162: "Drive alone - In-vehicle time",
        163: "Drive alone - Terminal time",
        164: "Drive alone - Operating cost ",
        165: "Drive alone - Parking cost ",
        166: "Drive alone - Bridge toll ",
        167: "Drive alone - Person is between 16 and 19 years old",
        168: "Drive alone toll - Unavailable",
        169: "Drive alone toll - Unavailable for zero auto households",
        170: "Drive alone toll - Unavailable for persons less than 16",
        171: "Drive alone toll - Unavailable for joint tours",
        172: "Drive alone toll - Unavailable if didn't drive to work",
        173: "Drive alone toll - In-vehicle time",
        174: "Drive alone toll - Terminal time",
        175: "Drive alone toll - Operating cost ",
        176: "Drive alone toll - Parking cost ",
        177: "Drive alone toll - Bridge toll ",
        178: "Drive alone toll - Value toll ",
        179: "Drive alone toll - Person is between 16 and 19 years old",
        180: "Shared ride 2 - Unavailable",
        181: "Shared ride 2 - Unavailable based on party size",
        182: "Shared ride 2 - In-vehicle time",
        183: "Shared ride 2 - Terminal time",
        184: "Shared ride 2 - Operating cost ",
        185: "Shared ride 2 - Parking cost ",
        186: "Shared ride 2 - Bridge toll ",
        187: "Shared ride 2 - One person household",
        188: "Shared ride 2 - Two person household",
        189: "Shared ride 2 - Person is 16 years old or older",
        190: "Shared ride 2 toll - Unavailable",
        191: "Shared ride 2 toll - Unavailable based on party size",
        192: "Shared ride 2 toll - In-vehicle time",
        193: "Shared ride 2 toll - Terminal time",
        194: "Shared ride 2 toll - Operating cost ",
        195: "Shared ride 2 toll - Parking cost ",
        196: "Shared ride 2 toll - Bridge toll ",
        197: "Shared ride 2 toll - Value toll ",
        198: "Shared ride 2 toll - One person household",
        199: "Shared ride 2 toll - Two person household",
        200: "Shared ride 2 toll - Person is 16 years old or older",
        201: "Shared ride 3+ - Unavailable",
        202: "Shared ride 3+ - In-vehicle time",
        203: "Shared ride 3+ - Terminal time",
        204: "Shared ride 3+ - Operating cost ",
        205: "Shared ride 3+ - Parking cost ",
        206: "Shared ride 3+ - Bridge toll ",
        207: "Shared ride 3+ - One person household",
        208: "Shared ride 3+ - Two person household",
        209: "Shared ride 3+ - Person is 16 years old or older",
        210: "Shared ride 3+ toll - Unavailable",
        211: "Shared ride 3+ toll - In-vehicle time",
        212: "Shared ride 3+ - Terminal time",
        213: "Shared ride 3+ toll - Operating cost ",
        214: "Shared ride 3+ toll - Parking cost ",
        215: "Shared ride 3+ toll - Bridge toll ",
        216: "Shared ride 3+ toll - Value toll ",
        217: "Shared ride 3+ toll - One person household",
        218: "Shared ride 3+ toll - Two person household",
        219: "Shared ride 3+ toll - Person is 16 years old or older",
        220: "Walk - Time up to 2 miles",
        221: "Walk - Time beyond 2 of a miles",
        222: "Walk - Destination zone densityIndex",
        223: "Walk - Topology",
        224: "Bike - Unavailable if didn't bike to work",
        225: "Bike - Time up to 2 miles",
        226: "Bike - Time beyond 2 of a miles",
        227: "Bike - Destination zone densityIndex",
        228: "Bike - Topology",
        229: "Walk to Local - Unavailable",
        230: "Walk to Local - In-vehicle time",
        231: "Walk to Local - Short iwait time",
        232: "Walk to Local - Long iwait time",
        233: "Walk to Local - transfer wait time",
        234: "Walk to Local - number of transfers",
        235: "Walk to Local - Walk access time",
        236: "Walk to Local - Walk egress time",
        237: "Walk to Local - Walk other time",
        238: "Walk to Local - Fare ",
        239: "Walk to Local - Destination zone densityIndex",
        240: "Walk to Local - Topology",
        241: "Walk to Local - Person is less than 10 years old",
        242: "Walk to Light rail/Ferry - Unavailable",
        243: "Walk to Light rail/Ferry - In-vehicle time",
        244: "Walk to Light rail/Ferry - In-vehicle time on Light Rail (incremental w/ ivt)",
        245: "Walk to Light rail/Ferry - In-vehicle time on Ferry (incremental w/ keyivt)",
        246: "Walk to Light rail/Ferry - Short iwait time",
        247: "Walk to Light rail/Ferry - Long iwait time",
        248: "Walk to Light rail/Ferry - transfer wait time",
        249: "Walk to Light rail/Ferry - number of transfers",
        250: "Walk to Light rail/Ferry - Walk access time",
        251: "Walk to Light rail/Ferry - Walk egress time",
        252: "Walk to Light rail/Ferry - Walk other time",
        253: "Walk to Light rail/Ferry - Fare ",
        254: "Walk to Light rail/Ferry - Destination zone densityIndex",
        255: "Walk to Light rail/Ferry - Topology",
        256: "Walk to Light rail/Ferry - Person is less than 10 years old",
        257: "Walk to Express bus - Unavailable",
        258: "Walk to Express bus - In-vehicle time",
        259: "Walk to Express bus - In-vehicle time on Express bus (incremental w/ ivt)",
        260: "Walk to Express bus - Short iwait time",
        261: "Walk to Express bus - Long iwait time",
        262: "Walk to Express bus - transfer wait time",
        263: "Walk to Express bus - number of transfers",
        264: "Walk to Express bus - Walk access time",
        265: "Walk to Express bus - Walk egress time",
        266: "Walk to Express bus - Walk other time",
        267: "Walk to Express bus - Fare ",
        268: "Walk to Express bus - Destination zone densityIndex",
        269: "Walk to Express bus - Topology",
        270: "Walk to Express bus - Person is less than 10 years old",
        271: "Walk to heavy rail - Unavailable",
        272: "Walk to heavy rail - In-vehicle time",
        273: "Walk to heavy rail - In-vehicle time on heavy rail (incremental w/ ivt)",
        274: "Walk to heavy rail - Short iwait time",
        275: "Walk to heavy rail - Long iwait time",
        276: "Walk to heavy rail - transfer wait time",
        277: "Walk to heavy rail - number of transfers",
        278: "Walk to heavy rail - Walk access time",
        279: "Walk to heavy rail - Walk egress time",
        280: "Walk to heavy rail - Walk other time",
        281: "Walk to heavy rail - Fare ",
        282: "Walk to heavy rail - Destination zone densityIndex",
        283: "Walk to heavy rail - Topology",
        284: "Walk to heavy rail - Person is less than 10 years old",
        285: "Walk to Commuter rail - Unavailable",
        286: "Walk to Commuter rail - In-vehicle time",
        287: "Walk to Commuter rail - In-vehicle time on commuter rail (incremental w/ ivt)",
        288: "Walk to Commuter rail - Short iwait time",
        289: "Walk to Commuter rail - Long iwait time",
        290: "Walk to Commuter rail - transfer wait time",
        291: "Walk to Commuter rail - number of transfers",
        292: "Walk to Commuter rail - Walk access time",
        293: "Walk to Commuter rail - Walk egress time",
        294: "Walk to Commuter rail - Walk other time",
        295: "Walk to Commuter rail - Fare ",
        296: "Walk to Commuter rail - Destination zone densityIndex",
        297: "Walk to Commuter rail - Topology",
        298: "Walk to Commuter rail - Person is less than 10 years old",
        299: "Drive to Local - Unavailable",
        300: "Drive to Local - Unavailable for zero auto households",
        301: "Drive to Local - Unavailable for persons less than 16",
        302: "Drive to Local - In-vehicle time",
        303: "Drive to Local - Short iwait time",
        304: "Drive to Local - Long iwait time",
        305: "Drive to Local - transfer wait time",
        306: "Drive to Local - number of transfers",
        307: "Drive to Local - Drive time",
        308: "Drive to Local - Walk access time (at attraction end)",
        309: "Drive to Local - Walk egress time (at attraction end)",
        310: "Drive to Local - Walk other time",
        311: "Drive to Local - Fare and operating cost ",
        312: "Drive to Local - Ratio of drive access distance to OD distance",
        313: "Drive to Local  - Destination zone densityIndex",
        314: "Drive to Local  - Topology",
        315: "Drive to Local  - Person is less than 10 years old",
        316: "Drive to Light rail/Ferry - Unavailable",
        317: "Drive to Light rail/Ferry - Unavailable for zero auto households",
        318: "Drive to Light rail/Ferry - Unavailable for persons less than 16",
        319: "Drive to Light rail/Ferry - In-vehicle time",
        320: "Drive to Light rail/Ferry - In-vehicle time on Light Rail (incremental w/ ivt)",
        321: "Drive to Light rail/Ferry - In-vehicle time on Ferry (incremental w/ keyivt)",
        322: "drive to Light rail/Ferry - Short iwait time",
        323: "drive to Light rail/Ferry - Long iwait time",
        324: "drive to Light rail/Ferry - transfer wait time",
        325: "drive to Light rail/Ferry - number of transfers",
        326: "Drive to Light rail/Ferry - Drive time",
        327: "Drive to Light rail/Ferry - Walk access time (at attraction end)",
        328: "Drive to Light rail/Ferry - Walk egress time (at attraction end)",
        329: "Drive to Light rail/Ferry - Walk other time",
        330: "Drive to Light rail/Ferry - Fare and operating cost ",
        331: "Drive to Light rail/Ferry - Ratio of drive access distance to OD distance",
        332: "Drive to Light rail/Ferry  - Destination zone densityIndex",
        333: "Drive to Light rail/Ferry  - Topology",
        334: "Drive to Light rail/Ferry  - Person is less than 10 years old",
        335: "Drive to Express bus - Unavailable",
        336: "Drive to Express bus - Unavailable for zero auto households",
        337: "Drive to Express bus - Unavailable for persons less than 16",
        338: "Drive to Express bus - In-vehicle time",
        339: "Drive to Express bus - In-vehicle time on Express bus (incremental w/ ivt)",
        340: "drive to Express bus - Short iwait time",
        341: "drive to Express bus - Long iwait time",
        342: "drive to Express bus - transfer wait time",
        343: "drive to Express bus - number of transfers",
        344: "Drive to Express bus - Drive time",
        345: "Drive to Express bus - Walk access time (at attraction end)",
        346: "Drive to Express bus - Walk egress time (at attraction end)",
        347: "Drive to Express bus - Walk other time",
        348: "Drive to Express bus - Fare and operating cost ",
        349: "Drive to Express bus - Ratio of drive access distance to OD distance",
        350: "Drive to Express bus  - Destination zone densityIndex",
        351: "Drive to Express bus  - Topology",
        352: "Drive to Express bus  - Person is less than 10 years old",
        353: "Drive to heavy rail - Unavailable",
        354: "Drive to heavy rail - Unavailable for zero auto households",
        355: "Drive to heavy rail - Unavailable for persons less than 16",
        356: "Drive to heavy rail - In-vehicle time",
        357: "Drive to heavy rail - In-vehicle time on heavy rail (incremental w/ ivt)",
        358: "drive to heavy rail - Short iwait time",
        359: "drive to heavy rail - Long iwait time",
        360: "drive to heavy rail - transfer wait time",
        361: "drive to heavy rail - number of transfers",
        362: "Drive to heavy rail - Drive time",
        363: "Drive to heavy rail - Walk access time (at attraction end)",
        364: "Drive to heavy rail - Walk egress time (at attraction end)",
        365: "Drive to heavy rail - Walk other time",
        366: "Drive to heavy rail - Fare and operating cost ",
        367: "Drive to heavy rail - Ratio of drive access distance to OD distance",
        368: "Drive to heavy rail  - Destination zone densityIndex",
        369: "Drive to heavy rail  - Topology",
        370: "Drive to heavy rail  - Person is less than 10 years old",
        371: "Drive to Commuter rail - Unavailable",
        372: "Drive to Commuter rail - Unavailable for zero auto households",
        373: "Drive to Commuter rail - Unavailable for persons less than 16",
        374: "Drive to Commuter rail - In-vehicle time",
        375: "Drive to Commuter rail - In-vehicle time on commuter rail (incremental w/ ivt)",
        376: "drive to Commuter rail - Short iwait time",
        377: "drive to Commuter rail - Long iwait time",
        378: "drive to Commuter rail - transfer wait time",
        379: "drive to Commuter rail - number of transfers",
        380: "Drive to Commuter rail - Drive time",
        381: "Drive to Commuter rail - Walk access time (at attraction end)",
        382: "Drive to Commuter rail - Walk egress time (at attraction end)",
        383: "Drive to Commuter rail - Walk other time",
        384: "Drive to Commuter rail - Fare and operating cost ",
        385: "Drive to Commuter rail - Ratio of drive access distance to OD distance",
        386: "Drive to Commuter rail  - Destination zone densityIndex",
        387: "Drive to Commuter rail  - Topology",
        388: "Drive to Commuter rail - Person is less than 10 years old",
        389: "Taxi - In-vehicle time",
        390: "Taxi - Wait time",
        391: "Taxi - Tolls",
        392: "Taxi - Bridge toll",
        393: "Taxi - Fare",
        394: "TNC Single - In-vehicle time",
        395: "TNC Single - Wait time",
        396: "TNC Single - Tolls",
        397: "TNC Single - Bridge toll",
        398: "TNC Single - Cost",
        399: "TNC Shared - In-vehicle time",
        400: "TNC Shared - Wait time",
        401: "TNC Shared - Tolls",
        402: "TNC Shared - Bridge toll",
        403: "TNC Shared - Cost",
        404: "Walk - Alternative-specific constant - Zero auto",
        405: "Walk - Alternative-specific constant - Auto deficient",
        406: "Walk - Alternative-specific constant - Auto sufficient",
        407: "Bike - Alternative-specific constant - Zero auto",
        408: "Bike - Alternative-specific constant - Auto deficient",
        409: "Bike - Alternative-specific constant - Auto sufficient",
        410: "Shared ride 2 - Alternative-specific constant - Zero auto",
        411: "Shared ride 2 - Alternative-specific constant - Auto deficient",
        412: "Shared ride 2 - Alternative-specific constant - Auto sufficient",
        413: "Shared ride 3+ - Alternative-specific constant - Zero auto",
        414: "Shared ride 3+ - Alternative-specific constant - Auto deficient",
        415: "Shared ride 3+ - Alternative-specific constant - Auto sufficient",
        416: "Walk to Transit - Alternative-specific constant - Zero auto",
        417: "Walk to Transit - Alternative-specific constant - Auto deficient",
        418: "Walk to Transit - Alternative-specific constant - Auto sufficient",
        419: "Drive to Transit  - Alternative-specific constant - Zero auto",
        420: "Drive to Transit  - Alternative-specific constant - Auto deficient",
        421: "Drive to Transit  - Alternative-specific constant - Auto sufficient",
        422: "Taxi - Alternative-specific constant - Zero auto",
        423: "Taxi - Alternative-specific constant - Auto deficient",
        424: "Taxi - Alternative-specific constant - Auto sufficient",
        425: "TNC-Single - Alternative-specific constant - Zero auto",
        426: "TNC-Single - Alternative-specific constant - Auto deficient",
        427: "TNC-Single - Alternative-specific constant - Auto sufficient",
        428: "TNC-Shared - Alternative-specific constant - Zero auto",
        429: "TNC-Shared - Alternative-specific constant - Auto deficient",
        430: "TNC-Shared - Alternative-specific constant - Auto sufficient",
        431: "Walk - Alternative-specific constant - Joint Tours",
        432: "Walk - Alternative-specific constant - Joint Tours",
        433: "Walk - Alternative-specific constant - Joint Tours",
        434: "Bike - Alternative-specific constant - Joint Tours",
        435: "Bike - Alternative-specific constant - Joint Tours",
        436: "Bike - Alternative-specific constant - Joint Tours",
        437: "Shared ride 2 - Alternative-specific constant - Joint Tours",
        438: "Shared ride 2 - Alternative-specific constant - Joint Tours",
        439: "Shared ride 2 - Alternative-specific constant - Joint Tours",
        440: "Shared ride 3+ - Alternative-specific constant - Joint Tours",
        441: "Shared ride 3+ - Alternative-specific constant - Joint Tours",
        442: "Shared ride 3+ - Alternative-specific constant - Joint Tours",
        443: "Walk to Transit - Alternative-specific constant - Joint Tours",
        444: "Walk to Transit - Alternative-specific constant - Joint Tours",
        445: "Walk to Transit - Alternative-specific constant - Joint Tours",
        446: "Drive to Transit  - Alternative-specific constant - Joint Tours",
        447: "Drive to Transit  - Alternative-specific constant - Joint Tours",
        448: "Drive to Transit  - Alternative-specific constant - Joint Tours",
        449: "Taxi - Alternative-specific constant - Zero auto - Joint Tours",
        450: "Taxi - Alternative-specific constant - Auto deficient - Joint Tours",
        451: "Taxi - Alternative-specific constant - Auto sufficient - Joint Tours",
        452: "TNC-Single - Alternative-specific constant - Zero auto - Joint Tours",
        453: "TNC-Single - Alternative-specific constant - Auto deficient - Joint Tours",
        454: "TNC-Single - Alternative-specific constant - Auto sufficient - Joint Tours",
        455: "TNC-Shared - Alternative-specific constant - Zero auto - Joint Tours",
        456: "TNC-Shared - Alternative-specific constant - Auto deficient - Joint Tours",
        457: "TNC-Shared - Alternative-specific constant - Auto sufficient - Joint Tours",
        458: "Local bus",
        459: "Light rail - Alternative-specific constant (walk access)",
        460: "Light rail - Alternative-specific constant (drive access)",
        461: "Ferry - Alternative-specific constant (walk access)",
        462: "Ferry - Alternative-specific constant (drive access)",
        463: "Express bus - Alternative-specific constant",
        464: "Heavy rail - Alternative-specific constant ",
        465: "Commuter rail - Alternative-specific constant ",
        466: "Walk to Transit - CBD dummy",
        467: "Drive to Transit  - CBD dummy",
        468: "Walk to Transit - San Francisco dummy",
        469: "Drive to Transit - San Francisco dummy",
        470: "Walk to Transit - Within SF dummy",
        471: "Drive to Transit - Within SF dummy",
        472: "Walk to Transit - from San Francisco dummy",
        473: "Drive to Transit - from San Francisco dummy",
        474: "Drive to Transit - distance penalty",
        475: "Walk not available for long distances",
        476: "Bike not available for long distances",
        477: "Transit hesitance - local bus",
        478: "Transit hesitance - walk to light rail",
        479: "Transit hesitance - drive to light rail",
        480: "Transit hesitance - walk to ferry",
        481: "Transit hesitance - drive to ferry",
        482: "Transit hesitance - express bus",
        483: "Transit hesitance - heavy rail",
        484: "Transit hesitance - commuter rail",
        485: "Rail hesitance - heavy rail",
        486: "Rail hesitance - commuter rail",
        487: "TNC single adjustment",
        488: "TNC shared adjustment",
        489: "PBA50 Blueprint bike infra constant",
    }
    # 06-Aug-2019 09:24:58, INFO, *******************************************************************************************
    # 06-Aug-2019 09:24:58, INFO, For each model expression, 'coeff * expressionValue' pairs are listed for each available alternative.  At the end, total utility is listed.
    # 06-Aug-2019 09:24:58, INFO, The last line shows total utility for each available alternative.
    # 06-Aug-2019 09:24:58, INFO, Exp                               1                             2                             3                             4                             5                             6                             7                             8                             9                            10                            11                            12                            13                            14                            15                            16                            17                            18                            19                            20                            21
    # 06-Aug-2019 09:24:58, INFO, --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 06-Aug-2019 09:24:58, INFO, 1           0.00000 *   5.76907e+00       0.00000 *   5.76907e+00       0.00000 *   5.76907e+00       0.00000 *   5.76907e+00       0.00000 *   5.7

    if attr_dict['Purpose'].startswith("work"):
        print("Parsing for Work")
        ROW_NAMES = WORK_ROW_NAMES
    elif attr_dict['Purpose'].startswith('university'):
        print("Parsing for university")
        ROW_NAMES = UNIVERSITY_ROW_NAMES
    elif type_str == "NonMandLocChoice":
        ROW_NAMES = SHOPPING_ROW_NAMES
    else:
        print("read_tour_mode_choice_logsum_lines() doesn't handle purpose {}".format(attr_dict['Purpose']))
        return(100, pandas.DataFrame())
    

    # read 5 lines that we don't care about
    for lines_read in range(1,6):
        line = file_object.readline().strip()
        # print("{}   {}".format(lines_read, line[:30]))

    row_alt_dicts = []

    # read utiltities
    for utils_read in range(1,len(ROW_NAMES)+1):
        line     = file_object.readline().strip()
        # print("parsing line: [{}]".format(line))
        match    = MC_UTILITY_RE.match(line)
        row_num   = int(match.group(3)) # row number
        row_descr = ROW_NAMES[row_num]
        # print("row_num = {}, utils_read = {}".format(row_num, utils_read))

        full_idx  = 4  # coefficient x variable
        for mode_alt in range(1, NUM_MC_ALT+1):
            row_alt_dict = attr_dict.copy() # start with these keys
            row_alt_dict["row num"        ] = row_num
            row_alt_dict["row description"] = row_descr
            row_alt_dict["mode alt"       ] = mode_alt
            row_alt_dict["coefficient"    ] = float(match.group(full_idx+1))
            row_alt_dict["variable"       ] = match.group(full_idx+2)
            if row_alt_dict["variable"] == "Infinity":
                row_alt_dict["variable"] = numpy.Infinity
            elif row_alt_dict["variable"] == "NaN":
                row_alt_dict["variable"] = numpy.nan
            else:
                row_alt_dict["variable"] = float(row_alt_dict["variable"])

            row_alt_dicts.append(row_alt_dict)

            full_idx += 4 # go to next alt
    # 06-Aug-2019 09:24:58, INFO, 476         0.00000 *   2.01000e-01       0.00000 *           NaN       0.00000 *   2.01000e-01       0.00000 *           NaN
    # 06-Aug-2019 09:24:58, INFO, -----------------------------------------------------------------------------------------------------------------------------------
    # 06-Aug-2019 09:24:58, INFO, Alt Utility            -3.14411e+00                           NaN                  -4.22511e+00                           NaN                  -4.69850e+00                           NaN                           NaN                           NaN                           NaN                           NaN                           NaN                           NaN                           NaN                  -4.36949e+00                           NaN                           NaN                           NaN                           NaN                  -8.65800e+00                  -9.48385e+00                  -1.11842e+01

    # read 1 more lines that we don't care about, the dashes
    line     = file_object.readline().strip()
    assert("----------------------------" in line)
    lines_read += 1

    # total utility
    line     = file_object.readline().strip()
    match    = MC_TOTAL_UTILITY_RE.match(line)

    # handle inconsistent keys
    if ('destTaz' in attr_dict) and ('Dest' not in attr_dict): 
        attr_dict['Dest'] = attr_dict['destTaz']
        del attr_dict['destTaz']
    if ('destWalkSubzone' in attr_dict) and ('DestSubZest' not in attr_dict): 
        attr_dict['DestSubZ'] = attr_dict['destWalkSubzone']
        del attr_dict['destWalkSubzone']

    if attr_dict['Dest'] == "1" and attr_dict['DestSubZ'] == "0":
        print(match.groups())

    full_idx = 4 # TOTAL_UTIL_RE_TXT
    for mode_alt in range(1,NUM_MC_ALT+1):
        row_alt_dict = attr_dict.copy()
        row_alt_dict["row num"        ] = -1
        row_alt_dict["row description"] = "Total Utility"
        row_alt_dict["mode alt"       ] = mode_alt
        row_alt_dict["coefficient"    ] = 1.0
        row_alt_dict["variable"       ] = match.group(full_idx+1)
        if row_alt_dict["variable"] == "Infinity":
            row_alt_dict["variable"] = numpy.Infinity
        elif row_alt_dict["variable"] == "NaN":
            row_alt_dict["variable"] = numpy.nan
        else:
            row_alt_dict["variable"] = float(row_alt_dict["variable"])
        # print(row_alt_dict["variable"])

        row_alt_dicts.append(row_alt_dict)

        full_idx += 3 # go to next alt

    df = pandas.DataFrame.from_records(row_alt_dicts)
    print(f" => returning {len(df):,} rows")

    # to keep reasonable, drop everything with coefficient == 0
    # df = df.loc[ df.coefficient != 0]
    # drop alternative specific constants
    # df = df.loc[ (df["row num"] < 396)|(df["row num"] > 463)]

    if attr_dict['Dest'] == "1" and attr_dict['DestSubZ'] == "0":
        print("head: \n{}".format(df.head(NUM_MC_ALT)))
        print("tail: \n{}".format(df.tail(NUM_MC_ALT)))

    return (lines_read + utils_read, df)


def read_trip_mode_choice_lines(file_object, type_str, attr_dict, base_or_build, log_file):

    # from TripModeChoice.xls UEC, Work
    WORK_ROW_NAMES = {
        1:  "token, c_ivt",
        2:  "token, c_ivt_lrt",
        3:  "token, c_ivt_ferry",
        4:  "token, c_ivt_exp",
        5:  "token, c_ivt_hvy",
        6:  "token, c_ivt_com",
        7:  "token, c_shortiWait",
        8:  "token, c_longiWait",
        9:  "token, c_wacc",
        10: "token, c_wegr",
        11: "token, c_waux",
        12: "token, c_dtim",
        13: "token, c_xfers_wlk",
        14: "token, c_xfers_drv",
        15: "token, c_xwait",
        16: "token, c_walkTimeShort",
        17: "token, c_walkTimeLong",
        18: "token, c_bikeTimeShort",
        19: "token, c_bikeTimeLong",
        20: "token, vot",
        21: "token, c_cost",
        22: "token, c_dacc_ratio",
        23: "token, c_topology_walk",
        24: "token, c_topology_bike",
        25: "token, c_topology_trn",
        26: "token, c_densityIndex",
        27: "token, c_originDensityIndex",
        28: "token, c_originDensityIndexMax",
        29: "token, c_age1619_da",
        30: "token, c_age010_trn",
        31: "token, c_age16p_sr",
        32: "token, c_hhsize1_sr",
        33: "token, c_hhsize2_sr",
        34: "token, freeParkingAllowed",
        35: "token, costPerMile",
        36: "token, costShareSr2",
        37: "token, costShareSr3",
        38: "token, waitThresh",
        39: "token, walkThresh",
        40: "token, walkSpeed",
        41: "token, bikeThresh",
        42: "token, bikeSpeed",
        43: "token, shortWalk",
        44: "token, longWalk",
        45: "token, maxCbdAreaTypeThresh",
        46: "token, upperEA",
        47: "token, upperAM",
        48: "token, upperMD",
        49: "token, upperPM",
        50: "token, autos",
        51: "token, workers",
        52: "token, hhSize",
        53: "token, hhIncomeQ1",
        54: "token, hhIncomeQ2",
        55: "token, age",
        56: "token, timeOfDay",
        57: "token, destZoneAreaType",
        58: "token, zonalShortWalkOrig",
        59: "token, zonalLongWalkOrig",
        60: "token, zonalShortWalkDest",
        61: "token, zonalLongWalkDest",
        62: "token, jointTour",
        63: "token, numberOfParticipantsInJointTour",
        64: "token, indivTour",
        65: "token, subtour",
        66: "token, tourMode",
        67: "token, tourModeIsSOV",
        68: "token, tourModeIsAuto",
        69: "token, tourModeIsWalk",
        70: "token, tourModeIsBike",
        71: "token, tourModeIsWalkTransit",
        72: "token, tourModeIsDriveTransit",
        73: "token, tourModeIsRideHail",
        74: "token, freeParkingAvailable",
        75: "token, inbound",
        76: "token, outbound",
        77: "token, stopIsFirst",
        78: "token, stopIsLast",
        79: "token, originTerminalTime",
        80: "token, originTerminalTime",
        81: "token, destTerminalTime",
        82: "token, destTerminalTime",
        83: "token, totalTerminalTime",
        84: "token, originHourlyParkingCost",
        85: "token, destHourlyParkingCost",
        86: "token, tourDuration",
        87: "token, originDuration",
        88: "token, originDuration",
        89: "token, originDuration",
        90: "token, destDuration",
        91: "token, destDuration",
        92: "token, destDuration",
        93: "token, originParkingCost",
        94: "token, destParkingCost",
        95: "token, totalParkingCost",
        96: "token, tripTopology",
        97: "token, originDensityIndex",
        98: "token, originDensityApplied",
        99: "token, densityIndex",
        100: "token, shortWalkMax",
        101: "token, longWalkMax",
        102: "token, zeroAutoHh",
        103: "token, autoDeficientHh",
        104: "token, autoSufficientHh",
        105: "token, cbdDummy",
        106: "token, costInitialTaxi",
        107: "token, costPerMileTaxi",
        108: "token, costPerMinuteTaxi",
        109: "token, costInitialSingleTNC",
        110: "token, costPerMileSingleTNC",
        111: "token, costPerMinuteSingleTNC",
        112: "token, costMinimumSingleTNC",
        113: "token, costInitialSharedTNC",
        114: "token, costPerMileSharedTNC",
        115: "token, costPerMinuteSharedTNC",
        116: "token, costMinimumSharedTNC",
        117: "token, autoIVTFactorAV",
        118: "token, autoParkingCostFactorAV",
        119: "token, autoCostPerMileFactorAV",
        120: "token, autoTerminalTimeFactorAV",
        121: "token, sharedTNCIVTFactor",
        122: "token, useAV",
        123: "token, autoIVTFactor",
        124: "token, autoParkingCostFactor",
        125: "token, autoCPMFactor",
        126: "token, autoTermTimeFactor",
        127: "token, tripPeriod",
        128: "token, tripPeriod",
        129: "token, tripPeriod",
        130: "token, tripPeriod",
        131: "token, tripPeriod",
        132: "token, destCordon",
        133: "token, destCordonPrice",
        134: "token, origCordon",
        135: "token, walkTransitOrig",
        136: "token, walkTransitDest",
        137: "token, walkTransitAvailable",
        138: "token, driveTransitAvailable",
        139: "token, driveTransitAvailable",
        140: "token, originWalkTime",
        141: "token, originWalkTime",
        142: "token, destinationWalkTime",
        143: "token, destinationWalkTime",
        144: "token, sovAvailable",
        145: "token, hov2Available",
        146: "token, hov3Available",
        147: "token, sovtollAvailable",
        148: "token, hov2tollAvailable",
        149: "token, hov3tollAvailable",
        150: "token, walkLocalAvailable",
        151: "token, walkLrfAvailable",
        152: "token, walkExpressAvailable",
        153: "token, walkHeavyRailAvailable",
        154: "token, walkCommuterAvailable",
        155: "token, driveLocalAvailableOutbound",
        156: "token, driveLrfAvailableOutbound",
        157: "token, driveExpressAvailableOutbound",
        158: "token, driveHeavyRailAvailableOutbound",
        159: "token, driveCommuterAvailableOutbound",
        160: "token, driveLocalAvailableInbound",
        161: "token, driveLrfAvailableInbound",
        162: "token, driveExpressAvailableInbound",
        163: "token, driveHeavyRailAvailableInbound",
        164: "token, driveCommuterAvailableInbound",
        165: "token, walkFerryAvailable",
        166: "token, driveFerryAvailable",
        167: "token, driveFerryAvailable",
        168: "Drive alone - Unavailable",
        169: "Drive alone - Unavailable for zero auto households",
        170: "Drive alone - Unavailable for persons less than 16",
        171: "Drive alone - Unavailable for joint tours",
        172: "Drive alone - Unavailable if didn't drive to work",
        173: "Drive alone - In-vehicle time",
        174: "Drive alone - Terminal time",
        175: "Drive alone - Operating cost ",
        176: "Drive alone - Parking cost ",
        177: "Drive alone - Bridge toll ",
        178: "Drive alone - Person is between 16 and 19 years old",
        179: "Drive alone toll - Unavailable",
        180: "Drive alone toll - Unavailable for zero auto households",
        181: "Drive alone toll - Unavailable for persons less than 16",
        182: "Drive alone toll - Unavailable for joint tours",
        183: "Drive alone toll - Unavailable if didn't drive to work",
        184: "Drive alone toll - In-vehicle time",
        185: "Drive alone toll - Terminal time",
        186: "Drive alone toll - Operating cost ",
        187: "Drive alone toll - Parking cost ",
        188: "Drive alone toll - Bridge toll ",
        189: "Drive alone toll - Value toll ",
        190: "Drive alone toll - Person is between 16 and 19 years old",
        191: "Shared ride 2 - Unavailable",
        192: "Shared ride 2 - Unavailable based on party size",
        193: "Shared ride 2 - In-vehicle time",
        194: "Shared ride 2 - Terminal time",
        195: "Shared ride 2 - Operating cost ",
        196: "Shared ride 2 - Parking cost ",
        197: "Shared ride 2 - Bridge toll ",
        198: "Shared ride 2 - One person household",
        199: "Shared ride 2 - Two person household",
        200: "Shared ride 2 - Person is 16 years old or older",
        201: "Shared ride 2 toll - Unavailable",
        202: "Shared ride 2 toll - Unavailable based on party size",
        203: "Shared ride 2 toll - In-vehicle time",
        204: "Shared ride 2 toll - Terminal time",
        205: "Shared ride 2 toll - Operating cost ",
        206: "Shared ride 2 toll - Parking cost ",
        207: "Shared ride 2 toll - Bridge toll ",
        208: "Shared ride 2 toll - Value toll ",
        209: "Shared ride 2 toll - One person household",
        210: "Shared ride 2 toll - Two person household",
        211: "Shared ride 2 toll - Person is 16 years old or older",
        212: "Shared ride 3+ - Unavailable",
        213: "Shared ride 3+ - In-vehicle time",
        214: "Shared ride 3+ - Terminal time",
        215: "Shared ride 3+ - Operating cost ",
        216: "Shared ride 3+ - Parking cost ",
        217: "Shared ride 3+ - Bridge toll ",
        218: "Shared ride 3+ - One person household",
        219: "Shared ride 3+ - Two person household",
        220: "Shared ride 3+ - Person is 16 years old or older",
        221: "Shared ride 3+ toll - Unavailable",
        222: "Shared ride 3+ toll - In-vehicle time",
        223: "Shared ride 3+ toll - Terminal time",
        224: "Shared ride 3+ toll - Operating cost ",
        225: "Shared ride 3+ toll - Parking cost ",
        226: "Shared ride 3+ toll - Bridge toll ",
        227: "Shared ride 3+ toll - Value toll ",
        228: "Shared ride 3+ toll - One person household",
        229: "Shared ride 3+ toll - Two person household",
        230: "Shared ride 3+ toll - Person is 16 years old or older",
        231: "Walk - Time up to 1 mile",
        232: "Walk - Time beyond 1 mile",
        233: "Walk - Destination zone densityIndex",
        234: "Walk - Topology",
        235: "Bike - Unavailable if didn't bike to work",
        236: "Bike - Time up to 6 miles",
        237: "Bike - Time beyond 6 of a miles",
        238: "Bike - Destination zone densityIndex",
        239: "Bike - Topology",
        240: "Walk to Local - Unavailable",
        241: "Walk to Local - In-vehicle time",
        242: "Walk to Local - Short iwait time",
        243: "Walk to Local - Long iwait time",
        244: "Walk to Local - transfer wait time",
        245: "Walk to Local - number of transfers",
        246: "Walk to Local - Walk access time",
        247: "Walk to Local - Walk egress time",
        248: "Walk to Local - Walk other time",
        249: "Walk to Local - Fare ",
        250: "Walk to Local - Destination zone densityIndex",
        251: "Walk to Local - Topology",
        252: "Walk to Local - Person is less than 10 years old",
        253: "Walk to Light rail/Ferry - Unavailable",
        254: "Walk to Light rail/Ferry - In-vehicle time",
        255: "Walk to Light rail/Ferry - In-vehicle time on Light Rail (incremental w/ ivt)",
        256: "Walk to Light rail/Ferry - In-vehicle time on Ferry (incremental w/keyivt)",
        257: "Walk to Lrf - Short iwait time",
        258: "Walk to Lrf - Long iwait time",
        259: "Walk to Lrf - transfer wait time",
        260: "Walk to Lrf - number of transfers",
        261: "Walk to Light rail/Ferry - Walk access time",
        262: "Walk to Light rail/Ferry - Walk egress time",
        263: "Walk to Light rail/Ferry - Walk other time",
        264: "Walk to Light rail/Ferry - Fare ",
        265: "Walk to Light rail/Ferry - Destination zone densityIndex",
        266: "Walk to Light rail/Ferry - Topology",
        267: "Walk to Light rail/Ferry - Person is less than 10 years old",
        268: "Walk to Express bus - Unavailable",
        269: "Walk to Express bus - In-vehicle time",
        270: "Walk to Express bus - In-vehicle time on Express bus (incremental w/ ivt)",
        271: "Walk to Express - Short iwait time",
        272: "Walk to Express - Long iwait time",
        273: "Walk to Express - transfer wait time",
        274: "Walk to Express - number of transfers",
        275: "Walk to Express bus - Walk access time",
        276: "Walk to Express bus - Walk egress time",
        277: "Walk to Express bus - Walk other time",
        278: "Walk to Express bus - Fare ",
        279: "Walk to Express bus - Destination zone densityIndex",
        280: "Walk to Express bus - Topology",
        281: "Walk to Express bus - Person is less than 10 years old",
        282: "Walk to heavy rail - Unavailable",
        283: "Walk to heavy rail - In-vehicle time",
        284: "Walk to heavy rail - In-vehicle time on heavy rail (incremental w/ ivt)",
        285: "Walk to HeavyRail - Short iwait time",
        286: "Walk to HeavyRail - Long iwait time",
        287: "Walk to HeavyRail - transfer wait time",
        288: "Walk to HeavyRail - number of transfers",
        289: "Walk to heavy rail - Walk access time",
        290: "Walk to heavy rail - Walk egress time",
        291: "Walk to heavy rail - Walk other time",
        292: "Walk to heavy rail - Fare ",
        293: "Walk to heavy rail - Destination zone densityIndex",
        294: "Walk to heavy rail - Topology",
        295: "Walk to heavy rail - Person is less than 10 years old",
        296: "Walk to Commuter rail - Unavailable",
        297: "Walk to Commuter rail - In-vehicle time",
        298: "Walk to Commuter rail - In-vehicle time on commuter rail (incremental w/ ivt)",
        299: "Walk to Commuter - Short iwait time",
        300: "Walk to Commuter - Long iwait time",
        301: "Walk to Commuter - transfer wait time",
        302: "Walk to Commuter - number of transfers",
        303: "Walk to Commuter - Walk access time",
        304: "Walk to Commuter - Walk egress time",
        305: "Walk to Commuter - Walk other time",
        306: "Walk to Commuter rail - Fare ",
        307: "Walk to Commuter rail - Destination zone densityIndex",
        308: "Walk to Commuter rail - Topology",
        309: "Walk to Commuter rail - Person is less than 10 years old",
        310: "Drive to Local - Unavailable (outbound)",
        311: "Drive to Local - Unavailable for zero auto households (outbound)",
        312: "Drive to Local - Unavailable for persons less than 16 (outbound)",
        313: "Drive to Local - In-vehicle time (outbound)",
        314: "drive to Local - Short iwait time (outbound)",
        315: "drive to Local - Long iwait time (outbound)",
        316: "drive to Local - transfer wait time (outbound)",
        317: "drive to Local - number of transfers (outbound)",
        318: "Drive to Local - Drive time (outbound)",
        319: "Drive to Local - Walk egress time (outbound)",
        320: "Drive to Local - Walk other time (outbound)",
        321: "Drive to Local - Fare and operating cost (outbound)",
        322: "Drive to Local - Ratio of drive access distance to OD distance (outbound)",
        323: "Drive to Local  - Destination zone densityIndex (outbound)",
        324: "Drive to Local  - Topology (outbound)",
        325: "Drive to Local  - Person is less than 10 years old (outbound)",
        326: "Drive to Local - Unavailable (inbound)",
        327: "Drive to Local - Unavailable for zero auto households (inbound)",
        328: "Drive to Local - Unavailable for persons less than 16 (inbound)",
        329: "Drive to Local - In-vehicle time (inbound)",
        330: "drive to Local - Short iwait time (inbound)",
        331: "drive to Local - Long iwait time (inbound)",
        332: "drive to Local - transfer wait time (inbound)",
        333: "drive to Local - number of transfers (inbound)",
        334: "Drive to Local - Drive time (inbound)",
        335: "Drive to Local - Walk access time (inbound)",
        336: "Drive to Local - Walk other time (inbound)",
        337: "Drive to Local - Fare and operating cost (inbound)",
        338: "Drive to Local - Ratio of drive access distance to OD distance (inbound)",
        339: "Drive to Local  - Destination zone densityIndex (inbound)",
        340: "Drive to Local  - Topology (inbound)",
        341: "Drive to Local  - Person is less than 10 years old (inbound)",
        342: "Drive to Light rail/Ferry - Unavailable (outbound)",
        343: "Drive to Light rail/Ferry - Unavailable for zero auto households (outbound)",
        344: "Drive to Light rail/Ferry - Unavailable for persons less than 16 (outbound)",
        345: "Drive to Light rail/Ferry - In-vehicle time (outbound)",
        346: "Drive to Light rail/Ferry - In-vehicle time on Light Rail (incremental w/ ivt) (outbound)",
        347: "Drive to Light rail/Ferry - In-vehicle time on Ferry (incremental w/ keyivt) (outbound)",
        348: "drive to Lrf - Short iwait time (outbound)",
        349: "drive to Lrf - Long iwait time (outbound)",
        350: "drive to Lrf - transfer wait time (outbound)",
        351: "drive to Lrf - number of transfers (outbound)",
        352: "Drive to Light rail/Ferry - Drive time (outbound)",
        353: "Drive to Light rail/Ferry - Walk egress time (outbound)",
        354: "Drive to Light rail/Ferry - Walk other time (outbound)",
        355: "Drive to Light rail/Ferry - Fare and operating cost  (outbound)",
        356: "Drive to Light rail/Ferry - Ratio of drive access distance to OD distance (outbound)",
        357: "Drive to Light rail/Ferry  - Destination zone densityIndex (outbound)",
        358: "Drive to Light rail/Ferry  - Topology (outbound)",
        359: "Drive to Light rail/Ferry  - Person is less than 10 years old (outbound)",
        360: "Drive to Light rail/Ferry - Unavailable (inbound)",
        361: "Drive to Light rail/Ferry - Unavailable for zero auto households (inbound)",
        362: "Drive to Light rail/Ferry - Unavailable for persons less than 16 (inbound)",
        363: "Drive to Light rail/Ferry - In-vehicle time (inbound)",
        364: "Drive to Light rail/Ferry - In-vehicle time on Light Rail (incremental w/ ivt) (inbound)",
        365: "Drive to Light rail/Ferry - In-vehicle time on Ferry (incremental w/ keyivt) (inbound)",
        366: "drive to Lrf - Short iwait time (inbound)",
        367: "drive to Lrf - Long iwait time (inbound)",
        368: "drive to Lrf - transfer wait time (inbound)",
        369: "drive to Lrf - number of transfers (inbound)",
        370: "Drive to Light rail/Ferry - Drive time (inbound)",
        371: "Drive to Light rail/Ferry - Walk access time (inbound)",
        372: "Drive to Light rail/Ferry - Walk other time (inbound)",
        373: "Drive to Light rail/Ferry - Fare and operating cost  (inbound)",
        374: "Drive to Light rail/Ferry - Ratio of drive access distance to OD distance (inbound)",
        375: "Drive to Light rail/Ferry  - Destination zone densityIndex (inbound)",
        376: "Drive to Light rail/Ferry  - Topology (inbound)",
        377: "Drive to Light rail/Ferry  - Person is less than 10 years old (inbound)",
        378: "Drive to Express bus - Unavailable (outbound)",
        379: "Drive to Express bus - Unavailable for zero auto households (outbound)",
        380: "Drive to Express bus - Unavailable for persons less than 16 (outbound)",
        381: "Drive to Express bus - In-vehicle time (outbound)",
        382: "Drive to Express bus - In-vehicle time on Express bus (incremental w/ ivt) (outbound)",
        383: "drive to exp - Short iwait time (outbound)",
        384: "drive to exp - Long iwait time (outbound)",
        385: "drive to exp - transfer wait time (outbound)",
        386: "drive to exp - number of transfers (outbound)",
        387: "Drive to Express bus - Drive time (outbound)",
        388: "Drive to Express bus - Walk egress time (outbound)",
        389: "Drive to Express bus - Walk other time (outbound)",
        390: "Drive to Express bus - Fare and operating cost (outbound)",
        391: "Drive to Express bus - Ratio of drive access distance to OD distance (outbound)",
        392: "Drive to Express bus  - Destination zone densityIndex (outbound)",
        393: "Drive to Express bus  - Topology (outbound)",
        394: "Drive to Express bus  - Person is less than 10 years old (outbound)",
        395: "Drive to Express bus - Unavailable (inbound)",
        396: "Drive to Express bus - Unavailable for zero auto households (inbound)",
        397: "Drive to Express bus - Unavailable for persons less than 16 (inbound)",
        398: "Drive to Express bus - In-vehicle time (inbound)",
        399: "Drive to Express bus - In-vehicle time on Express bus (incremental w/ ivt) (inbound)",
        400: "drive to exp - Short iwait time (inbound)",
        401: "drive to exp - Long iwait time (inbound)",
        402: "drive to exp - transfer wait time (inbound)",
        403: "drive to exp - number of transfers (inbound)",
        404: "Drive to Express bus - Drive time (inbound)",
        405: "Drive to Express bus - Walk access time (inbound)",
        406: "Drive to Express bus - Walk other time (inbound)",
        407: "Drive to Express bus - Fare and operating cost  (inbound)",
        408: "Drive to Express bus - Ratio of drive access distance to OD distance (inbound)",
        409: "Drive to Express bus  - Destination zone densityIndex (inbound)",
        410: "Drive to Express bus  - Topology (inbound)",
        411: "Drive to Express bus  - Person is less than 10 years old (inbound)",
        412: "Drive to heavy rail - Unavailable (outbound)",
        413: "Drive to heavy rail - Unavailable for zero auto households (outbound)",
        414: "Drive to heavy rail - Unavailable for persons less than 16 (outbound)",
        415: "Drive to heavy rail - In-vehicle time (outbound)",
        416: "Drive to heavy rail - In-vehicle time on heavy rail (incremental w/ ivt) (outbound)",
        417: "drive to HeavyRail - Short iwait time (outbound)",
        418: "drive to HeavyRail - Long iwait time (outbound)",
        419: "drive to HeavyRail - transfer wait time (outbound)",
        420: "drive to HeavyRail - number of transfers (outbound)",
        421: "Drive to heavy rail - Drive time (outbound)",
        422: "Drive to heavy rail - Walk egress time (outbound)",
        423: "Drive to heavy rail - Walk other time (outbound)",
        424: "Drive to heavy rail - Fare and operating cost (outbound)",
        425: "Drive to heavy rail - Ratio of drive access distance to OD distance (outbound)",
        426: "Drive to heavy rail  - Destination zone densityIndex (outbound)",
        427: "Drive to heavy rail  - Topology (outbound)",
        428: "Drive to heavy rail  - Person is less than 10 years old (outbound)",
        429: "Drive to heavy rail - Unavailable (inbound)",
        430: "Drive to heavy rail - Unavailable for zero auto households (inbound)",
        431: "Drive to heavy rail - Unavailable for persons less than 16 (inbound)",
        432: "Drive to heavy rail - In-vehicle time (inbound)",
        433: "Drive to heavy rail - In-vehicle time on heavy rail (incremental w/ ivt) (inbound)",
        434: "drive to HeavyRail - Short iwait time (inbound)",
        435: "drive to HeavyRail - Long iwait time (inbound)",
        436: "drive to HeavyRail - transfer wait time (inbound)",
        437: "drive to HeavyRail - number of transfers (inbound)",
        438: "Drive to heavy rail - Drive time (inbound)",
        439: "Drive to heavy rail - Walk access time (inbound)",
        440: "Drive to heavy rail - Walk other time (inbound)",
        441: "Drive to heavy rail - Fare and operating cost (inbound)",
        442: "Drive to heavy rail - Ratio of drive access distance to OD distance (inbound)",
        443: "Drive to heavy rail  - Destination zone densityIndex (inbound)",
        444: "Drive to heavy rail  - Topology (inbound)",
        445: "Drive to heavy rail  - Person is less than 10 years old (inbound)",
        446: "Drive to Commuter rail - Unavailable (outbound)",
        447: "Drive to Commuter rail - Unavailable for zero auto households (outbound)",
        448: "Drive to Commuter rail - Unavailable for persons less than 16 (outbound)",
        449: "Drive to Commuter rail - In-vehicle time (outbound)",
        450: "Drive to Commuter rail - In-vehicle time on commuter rail (incremental w/ ivt) (outbound)",
        451: "drive to Commuter - Short iwait time (outbound)",
        452: "drive to Commuter - Long iwait time (outbound)",
        453: "drive to Commuter - transfer wait time (outbound)",
        454: "drive to Commuter - number of transfers (outbound)",
        455: "Drive to Commuter rail - Drive time (outbound)",
        456: "Drive to Commuter rail - Walk egress time (outbound)",
        457: "Drive to Commuter rail - Walk other time (outbound)",
        458: "Drive to Commuter rail - Fare and operating cost (outbound)",
        459: "Drive to Commuter rail - Ratio of drive access distance to OD distance (outbound)",
        460: "Drive to Commuter rail  - Destination zone densityIndex (outbound)",
        461: "Drive to Commuter rail  - Topology (outbound)",
        462: "Drive to Commuter rail - Person is less than 10 years old (outbound)",
        463: "Drive to Commuter rail - Unavailable",
        464: "Drive to Commuter rail - Unavailable for zero auto households",
        465: "Drive to Commuter rail - Unavailable for persons less than 16",
        466: "Drive to Commuter rail - In-vehicle time",
        467: "Drive to Commuter rail - In-vehicle time on commuter rail (incremental w/ ivt)",
        468: "drive to Commuter - Short iwait time",
        469: "drive to Commuter - Long iwait time",
        470: "drive to Commuter - transfer wait time",
        471: "drive to Commuter - number of transfers",
        472: "Drive to Commuter rail - Drive time",
        473: "Drive to Commuter rail - Walk access time (inbound)",
        474: "Drive to Commuter rail - Walk other time",
        475: "Drive to Commuter rail - Fare and operating cost ",
        476: "Drive to Commuter rail - Ratio of drive access distance to OD distance",
        477: "Drive to Commuter rail  - Destination zone densityIndex",
        478: "Drive to Commuter rail  - Topology",
        479: "Drive to Commuter rail - Person is less than 10 years old",
        480: "Taxi - In-vehicle time",
        481: "Taxi - Wait time",
        482: "Taxi - Tolls",
        483: "Taxi - Bridge toll",
        484: "Taxi - Fare",
        485: "TNC Single - In-vehicle time",
        486: "TNC Single - Wait time",
        487: "TNC Single - Tolls",
        488: "TNC Single - Bridge toll",
        489: "TNC Single - Cost",
        490: "TNC Shared - In-vehicle time",
        491: "TNC Shared - Wait time",
        492: "TNC Shared - Tolls",
        493: "TNC Shared - Bridge toll",
        494: "TNC Shared - Cost",
        495: "Auto tour mode availability",
        496: "Walk tour mode availability",
        497: "Bike tour mode availability",
        498: "Walk to Transit tour mode availability",
        499: "Drive to Transit tour modes availability",
        500: "Ride Hail tour modes availability",
        501: "Drive Alone tour mode ASC -- shared ride 2",
        502: "Drive Alone tour mode ASC -- shared ride 3+",
        503: "Drive Alone tour mode ASC -- walk",
        504: "Drive Alone tour mode ASC -- ride hail",
        505: "Shared Ride 2 tour mode ASC -- shared ride 2",
        506: "Shared Ride 2 tour mode ASC -- shared ride 3+",
        507: "Shared Ride 2 tour mode ASC -- walk",
        508: "Shared Ride 2 tour mode ASC -- ride hail",
        509: "Shared Ride 3+ tour mode ASC -- shared ride 2",
        510: "Shared Ride 3+ tour mode ASC -- shared ride 3+",
        511: "Shared Ride 3+ tour mode ASC -- walk",
        512: "Shared Ride 3+ tour mode ASC -- ride hail",
        513: "Walk tour mode ASC -- ride hail",
        514: "Bike tour mode ASC -- walk",
        515: "Bike tour mode ASC -- ride hail",
        516: "Walk to Transit tour mode ASC -- light rail",
        517: "Walk to Transit tour mode ASC -- ferry",
        518: "Walk to Transit tour mode ASC -- express bus",
        519: "Walk to Transit tour mode ASC -- heavy rail",
        520: "Walk to Transit tour mode ASC -- commuter rail",
        521: "Walk to Transit tour mode ASC -- shared ride 2",
        522: "Walk to Transit tour mode ASC -- shared ride 3+",
        523: "Walk to Transit tour mode ASC -- walk",
        524: "Walk to Transit tour mode ASC -- ride hail",
        525: "Drive to Transit tour mode ASC -- light rail (higher b/c loc d-trn skims differ)",
        526: "Drive to Transit tour mode ASC -- ferry",
        527: "Drive to Transit tour mode ASC -- express bus",
        528: "Drive to Transit tour mode ASC -- heavy rail",
        529: "Drive to Transit tour mode ASC -- commuter rail",
        530: "Drive to Transit tour mode ASC -- ride hail",
        531: "Ride Hail tour mode ASC -- shared ride 2",
        532: "Ride Hail tour mode ASC -- shared ride 3+",
        533: "Ride Hail tour mode ASC -- walk",
        534: "Ride Hail tour mode ASC -- walk to transit",
        535: "Ride Hail tour mode ASC -- taxi",
        536: "Ride Hail tour mode ASC -- tnc single",
        537: "Ride Hail tour mode ASC -- tnc shared",
        538: "Walk not available for long distances",
        539: "Bike not available for long distances",
        540: "Origin density index, walk, bike, walk-transit, TNC",
        541: "Walk-express penalty for intermediate stops",
        542: "Sharing preference adjustment - car modes",
        543: "Sharing preference adjustment - walk to light rail",
        544: "Sharing preference adjustment - drive to light rail",
        545: "Sharing preference adjustment - walk to ferry",
        546: "Sharing preference adjustment - drive to ferry",
        547: "Sharing preference adjustment - express bus",
        548: "Sharing preference adjustment - heavy rail",
        549: "Sharing preference adjustment - commuter rail",
        550: "TNC single adjustment",
        551: "TNC shared adjustment",
        552: "PBA50 Blueprint bike infra constant",
    }

    # 03-Mar-2020 19:26:09, INFO, *******************************************************************************************
    # 03-Mar-2020 19:26:09, INFO, For each model expression, 'coeff * expressionValue' pairs are listed for each available alternative.  At the end, total utility is listed.
    # 03-Mar-2020 19:26:09, INFO, The last line shows total utility for each available alternative.
    # 03-Mar-2020 19:26:09, INFO, Exp                               1                             2                             3                             4                             5                             6                             7                             8                             9                            10                            11                            12                            13                            14                            15                            16                            17                            18                            19                            20                            21   
    # 03-Mar-2020 19:26:09, INFO, --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 03-Mar-2020 19:26:09, INFO, 1           0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02       0.00000 *  -2.79000e-02   
    ROW_NAMES = WORK_ROW_NAMES

    if not attr_dict['TourPurpose'].startswith("work"):
        print("read_trip_mode_choice_lines() doesn't handle purpose {}".format(attr_dict['TourPurpose']))
        return(100, pandas.DataFrame())

    # read 5 lines that we don't care about
    for lines_read in range(1,6):
        line = file_object.readline().strip()
        # print("Skipping lines_read={} line={}".format(lines_read, line))

    row_alt_dicts = []
    # read utiltities
    for utils_read in range(1,len(ROW_NAMES)+1):
        line     = file_object.readline().strip()
        match    = MC_UTILITY_RE.match(line)
        if match == None: print("match == None for utils_read={} line={}".format(utils_read, line))
        row_num   = int(match.group(3)) # row number
        row_descr = ROW_NAMES[row_num]
        assert(utils_read == row_num)

        full_idx  = 4  # coefficient x variable
        for mode_alt in range(1, NUM_MC_ALT+1):
            row_alt_dict = attr_dict.copy()
            row_alt_dict["row num"         ] = row_num
            row_alt_dict["row description" ] = row_descr
            row_alt_dict["mode alt"        ] = mode_alt
            row_alt_dict["orig"            ] = trip_mc_od["orig"]
            row_alt_dict["origWalkSegment" ] = trip_mc_od["origWalkSegment"]
            row_alt_dict["dest"            ] = trip_mc_od["dest"]
            row_alt_dict["destWalkSegment" ] = trip_mc_od["destWalkSegment"]
            row_alt_dict["direction"       ] = trip_mc_od["direction"] # inbound or outbound
            row_alt_dict["coefficient"     ] = float(match.group(full_idx+1))
            row_alt_dict["variable"        ] = match.group(full_idx+2)
            if row_alt_dict["variable"] == "Infinity":
                row_alt_dict["variable"] = numpy.Infinity
            elif row_alt_dict["variable"] == "NaN":
                row_alt_dict["variable"] = numpy.NaN
            else:
                row_alt_dict["variable"] = float(row_alt_dict["variable"])

            row_alt_dicts.append(row_alt_dict)

            full_idx += 4 #

    # read 1 more lines that we don't care about, the dashes
    line     = file_object.readline().strip()
    assert("----------------------------" in line)
    lines_read += 1

    # total utility
    line     = file_object.readline().strip()
    match    = MC_TOTAL_UTILITY_RE.match(line)

    full_idx = 3 # TOTAL_UTIL_RE_TXT
    for mode_alt in range(1,NUM_MC_ALT+1):
        row_alt_dict = attr_dict.copy()
        row_alt_dict["row num"         ] = -1
        row_alt_dict["row description" ] = "Total Utility"
        row_alt_dict["mode alt"        ] = mode_alt
        row_alt_dict["orig"            ] = trip_mc_od["orig"]
        row_alt_dict["origWalkSegment" ] = trip_mc_od["origWalkSegment"]
        row_alt_dict["dest"            ] = trip_mc_od["dest"]
        row_alt_dict["destWalkSegment" ] = trip_mc_od["destWalkSegment"]
        row_alt_dict["direction"       ] = trip_mc_od["direction"] # inbound or outbound
        row_alt_dict["coefficient"     ] = 0.0
        row_alt_dict["variable"        ] = match.group(full_idx+1)
        if row_alt_dict["variable"] == "Infinity":
            row_alt_dict["variable"] = numpy.Infinity
        elif row_alt_dict["variable"] == "NaN":
            row_alt_dict["variable"] = numpy.NaN
        else:
            row_alt_dict["variable"] = float(row_alt_dict["variable"])
        # print(row_alt_dict["variable"])

        row_alt_dicts.append(row_alt_dict)

        full_idx += 3 # go to next alt

    df = pandas.DataFrame.from_records(row_alt_dicts)

    # to keep reasonable, drop everything with coefficient == 0
    # df = df.loc[ df.coefficient != 0]
    # drop alternative specific constants
    # df = df.loc[ (df["row num"] < 396)|(df["row num"] > 463)]

    # print("head: \n{}".format(df.head(NUM_MC_ALT)))
    # print("tail: \n{}".format(df.tail(NUM_MC_ALT)))

    return (lines_read + utils_read, df)

def read_destination_choice_lines(file_object, type_str, purpose, hh, persnum, ptype, tournum, base_or_build, log_file):
    """
    Read the destination choice utilities from the file_object
    Saves as destchoice_[type_str]_hh[hh]_pers[persnum]/[base_or_build]_dc_utilities.csv
    Also copies log file into that directory as backup
    """
    output_dir      = "destchoice_{}_hh{}_pers{}".format(type_str, hh, persnum)
    output_filename = "{}_dc_utilities.csv".format(base_or_build)
    # from DestinationChoice.xls UEC, Work
    WORK_ROW_NAMES = {
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
    SHOPPING_ROW_NAMES = {
        1 : "token, numberOfSubzones",
        2 : "token, $dest",
        3 : "token, mcLogsum",
        4 : "token, sizeTerm",
        5 : "token, dcSoaCorrections",
        6 : "token, distance",
        7 : "Sample of alternatives correction factor",
        8 : "Distance, piecewise linear from 0 to 1 miles",
        9 : "Distance, piecewise linear from 1 to 2 miles",
        10: "Distance, piecewise linear from 2 to 5 miles",
        11: "Distance, piecewise linear from 5 to 15 miles",
        12: "Distance, piecewise linear for 15+ miles",
        13: "Mode choice logsum",
        14: "Size variable",
        15: "No attractions"
    }

    ROW_NAMES = WORK_ROW_NAMES
    if type_str == "NonMandLocChoice":
        ROW_NAMES = SHOPPING_ROW_NAMES

    # 10-Jul-2019 18:40:30, INFO, *******************************************************************************************
    # 10-Jul-2019 18:40:30, INFO, For each model expression, 'coeff * expressionValue' pairs are listed for each available alternative.  At the end, total utility is listed.
    # 10-Jul-2019 18:40:30, INFO, The last line shows total utility for each available alternative.
    # 10-Jul-2019 18:40:31, INFO, Exp                               1                             2                             3                             4                             5
    # 10-Jul-2019 18:40:36, INFO, -----------------------------------------------------------------------------------------------------------------------------------------------------------
    # 10-Jul-2019 18:40:36, INFO, 1           0.00000 *   3.00000e+00       0.00000 *   3.00000e+00       0.00000 *   3.00000e+00       0.00000 *   3.00000e+00       0.00000 *   3.00000e+00

    # read 5 lines that we don't care about
    for lines_read in range(1,6):
        line = file_object.readline().strip()
        print("{}   {}".format(lines_read, line[:30]))

    row_alt_dicts = []

    # read utiltities
    for utils_read in range(1,len(ROW_NAMES)+1):
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

        print("{}   {}".format(utils_read, line[:30]))


        # print(match.group(0))
        row_num   = int(match.group(3)) # row number
        row_descr = ROW_NAMES[row_num]

        full_idx  = 4  # coefficient x variable
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
    try:
        os.mkdir(output_dir)
    except:
        pass
    df.to_csv(os.path.join(output_dir,output_filename), index=False)
    print("Wrote {}".format(os.path.join(output_dir,output_filename)))

    # copy source log file
    shutil.copyfile(log_file, os.path.join(output_dir, log_file))
    print("Copied {} to {}".format(log_file, output_dir))

    return (lines_read + utils_read, output_dir)

def read_wfh_choice_lines(file_object, attr_dict, base_or_build, log_file):
    """
    Read the destination choice utilities from the file_object
    Saves as destchoice_[type_str]_hh[hh]_pers[persnum]/[base_or_build]_dc_utilities.csv
    Also copies log file into that directory as backup
    """
    # read 5 lines that we don't care about
    for lines_read in range(1,6):
        line = file_object.readline().strip()
        print(f"Skipping [{line}]")

    # from CoordinatedDailyActivityPattern.xls UEC, WorkFromHome
    WFH_ROW_NAMES = {
        1 : "token, income (2000 dollars)",
        2 : "token, industry is AGR",
        3 : "token, industry is HER",
        4 : "token, industry is MWT",
        5 : "token, industry is RET",
        6 : "token, home county",
        7 : "token, work superdistrict",
        8 : "token, work county",
        9 : "token, distance home-to-work",
        10: "token, income (2023 dollars)",
        11: "Estimated constant",
        12: "Household income 75-100k (2023$)",
        13: "Household income 100-200k (2023$)",
        14: "Household income 200k+ (2023$)",
        15: "Industry is Agricultural and natural resources",
        16: "Industry is Health, educational and recreational service",
        17: "Industry is Manufacturing, wholesale trade and transportation",
        18: "Industry is Retail trade",
        19: "Home county is North Bay",
        20: "Distance from home to work (in miles)",
        21: "Calibration constant",
        22: "EN7 Boost for Superdistrict 01",
        23: "EN7 Boost for Superdistrict 02",
        24: "EN7 Boost for Superdistrict 03",
        25: "EN7 Boost for Superdistrict 04",
        26: "EN7 Boost for Superdistrict 05",
        27: "EN7 Boost for Superdistrict 06",
        28: "EN7 Boost for Superdistrict 07",
        29: "EN7 Boost for Superdistrict 08",
        30: "EN7 Boost for Superdistrict 09",
        31: "EN7 Boost for Superdistrict 10",
        32: "EN7 Boost for Superdistrict 11",
        33: "EN7 Boost for Superdistrict 12",
        34: "EN7 Boost for Superdistrict 13",
        35: "EN7 Boost for Superdistrict 14",
        36: "EN7 Boost for Superdistrict 15",
        37: "EN7 Boost for Superdistrict 16",
        38: "EN7 Boost for Superdistrict 17",
        39: "EN7 Boost for Superdistrict 18",
        40: "EN7 Boost for Superdistrict 19",
        41: "EN7 Boost for Superdistrict 20",
        42: "EN7 Boost for Superdistrict 21",
        43: "EN7 Boost for Superdistrict 22",
        44: "EN7 Boost for Superdistrict 23",
        45: "EN7 Boost for Superdistrict 24",
        46: "EN7 Boost for Superdistrict 25",
        47: "EN7 Boost for Superdistrict 26",
        48: "EN7 Boost for Superdistrict 27",
        49: "EN7 Boost for Superdistrict 28",
        50: "EN7 Boost for Superdistrict 29",
        51: "EN7 Boost for Superdistrict 30",
        52: "EN7 Boost for Superdistrict 31",
        53: "EN7 Boost for Superdistrict 32",
        54: "EN7 Boost for Superdistrict 33",
        55: "EN7 Boost for Superdistrict 34",
    }

    row_alt_dicts = []

    # read utiltities
    for utils_read in range(1,len(WFH_ROW_NAMES)+1):
        line     = file_object.readline().strip()
        match    = WFH_UTILITY_RE.match(line)
        # print(f"parsing line: [{line}]")
        # print(f"WFH_UTILITY_RE: [{WFH_UTILITY_RE}]")
        # print(f"match: [{match}]")

        row_num   = int(match.group(3)) # row number
        row_descr = WFH_ROW_NAMES[row_num]

        full_idx  = 4  # coefficient x variable
        for wfh_alt in range(1, NUM_WFH_ALT+1):
            row_alt_dict = attr_dict.copy() # start with these keys
            row_alt_dict["row num"        ] = row_num
            row_alt_dict["row description"] = row_descr
            row_alt_dict["wfh alt"        ] = wfh_alt
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

    # 31-Oct-2024 11:16:47, INFO, 54          1.00000 *   0.00000e+00       0.00000 *   0.00000e+00   
    # 31-Oct-2024 11:16:47, INFO, --------------------------------------------------------------------
    # 31-Oct-2024 11:16:47, INFO, Alt Utility             7.45000e+00                   0.00000e+00   

    # read 1 more lines that we don't care about, the dashes
    line     = file_object.readline().strip()
    assert("----------------------------" in line)
    lines_read += 1

    # total utility
    line     = file_object.readline().strip()
    match    = WFH_TOTAL_UTILITY_RE.match(line)
    print(match.groups())
    full_idx = 4
    for wfh_alt in range(1,NUM_WFH_ALT+1):
        row_alt_dict = attr_dict.copy()
        row_alt_dict["row num"        ] = -1
        row_alt_dict["row description"] = "Total Utility"
        row_alt_dict["wfh alt"       ] = wfh_alt
        row_alt_dict["coefficient"    ] = 1.0
        row_alt_dict["variable"       ] = match.group(full_idx+1)
        if row_alt_dict["variable"] == "Infinity":
            row_alt_dict["variable"] = numpy.Infinity
        elif row_alt_dict["variable"] == "NaN":
            row_alt_dict["variable"] = numpy.NaN
        else:
            row_alt_dict["variable"] = float(row_alt_dict["variable"])
        # print(row_alt_dict["variable"])

        row_alt_dicts.append(row_alt_dict)

        full_idx += 3 # go to next alt

    df = pandas.DataFrame.from_records(row_alt_dicts)

    output_dir      = pathlib.Path(".") # just save this local
    output_filename = f"cdap_wfh_hhid{attr_dict['HHID']}_persid{attr_dict['PERSID']}.csv"
    df.to_csv(os.path.join(output_dir,output_filename), index=False)
    print("Wrote {}".format(os.path.join(output_dir,output_filename)))

    # copy source log file
    # shutil.copyfile(log_file, os.path.join(output_dir, log_file))
    # print("Copied {} to {}".format(log_file, output_dir))

    return (lines_read + utils_read, output_dir)


if __name__ == '__main__':
    pandas.options.display.width = 1000
    pandas.options.display.max_columns = 100

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument("base_or_build",  choices=["base","build"], help="For output file name")
    parser.add_argument("log_file",  metavar="event-node0-something.log", help="Log file to parse")

    args = parser.parse_args()


    line_re       = re.compile(f"{DATE_LOG_TYPE_RE_TXT}(.*)$")
    tour_dc_re    = re.compile(f"{DATE_LOG_TYPE_RE_TXT}{TOURDC_RE_TXT}")
    tour_mc_re    = re.compile(f"{DATE_LOG_TYPE_RE_TXT}{TOURMC_RE_TXT}")
    trip_mc_re    = re.compile(f"{DATE_LOG_TYPE_RE_TXT}{TRIPMC_RE_TXT}")
    trip_mc_od_re = re.compile(f"{DATE_LOG_TYPE_RE_TXT}{TRIPMC_ORIGDEST_RE_TXT}")
    cdap_wfh_re   = re.compile(f"{DATE_LOG_TYPE_RE_TXT}{WFH_RE_TXT}")
    attrs_re      = re.compile(r"(?P<attr_name>[A-Za-z]+)=(?P<attr_value>[0-9A-Za-z\-_]+[ ]?[0-9A-Za-z\-_]*)")  # may have one space in attr_value
    attrs_nospc_re= re.compile(r"(?P<attr_name>[A-Za-z]+)=(?P<attr_value>[0-9A-Za-z\-_]+)")  # may have one space in attr_value


    print("Reading {}".format(args.log_file))
    log_fo = open(args.log_file, 'r')
    lines_read = 0
    output_dir = None
    modechoice_df = pandas.DataFrame()
    trip_mc_od = {}

    while True:
        line = log_fo.readline()
        # check for eof
        if line == "": break
        # strip trailing/leading whitespace
        line = line.strip()

        lines_read += 1
        # print(f"global loop line=[{line}]")

        match = tour_mc_re.match(line)
        if match:
            print(f"tour_mc_re match for {line}")

            type_str = "UsualWorkLocChoice"
            if match.group('nonm') in [" Individual Non-Mandatory"," INDIVIDUAL_NON_MANDATORY"]:
                type_str = "NonMandLocChoice"
            elif match.group('nonm') == " MANDATORY":
                type_str = "MandatoryTourModeChoice"
            output_dir  = "."

            # parse the attrs
            attrs_dict = dict(attrs_re.findall(match.group('attrs')))
            # add purpose from match if needed
            if ('Purpose' not in attrs_dict) and ('purpose' in match.groupdict()):
                attrs_dict['Purpose'] = match.groupdict()['purpose'].strip()

            print(f"Found Tour Mode Choice info for type_str={type_str}")

            (new_lines_read,df) = read_tour_mode_choice_logsum_lines(log_fo, type_str, attrs_dict, args.base_or_build, args.log_file)
            lines_read += new_lines_read
            modechoice_df = pandas.concat([modechoice_df, df])

            continue

        match = tour_dc_re.match(line)
        if match:

            dctype  = match.group(3)
            purpose = match.group(4)
            hh      = match.group(5)
            persnum = match.group(6)
            ptype   = match.group(7)
            tournum = match.group(9)
            print("Found {} Destination Choice info for purpose={} hh={} persnum={} ptype={} tournum={}".format(dctype, purpose, hh, persnum, ptype, tournum))

            type_str = "UsualWorkLocChoice"
            if "Non-Mandatory" in dctype:
                type_str = "NonMandLocChoice"

            # read the rest of the relevant lines
            (new_lines_read,output_dir) = read_destination_choice_lines(log_fo, type_str, purpose, hh, persnum, ptype, tournum, args.base_or_build, args.log_file)
            lines_read += new_lines_read

            continue

        match = trip_mc_od_re.match(line)
        if match:
            label = match.group(3)
            value = match.group(4) if label == "direction" else int(match.group(4))
            print("  Found Trip Mode Choice info for {}:{}".format(label, value))
            trip_mc_od[label] = value
            continue

        match = trip_mc_re.match(line)
        if match:
            print("trip_mc_re match: {}".format(match.groupdict()))

            type_str         = "tripModeChoice"
            output_dir       = "."

            # parse the attrs
            attrs_dict = dict(attrs_re.findall(match.group('attrs')))

            print("Found Trip Mode Choice info type_str={} attributes: {}".format(type_str, attrs_dict))

            (new_lines_read,df) = read_trip_mode_choice_lines(log_fo, type_str, attrs_dict, args.base_or_build, args.log_file)
            if new_lines_read > 0:
                lines_read += new_lines_read
                modechoice_df = pandas.concat([modechoice_df, df])
            continue

        match = cdap_wfh_re.match(line)
        if match:
            print(f"cdap_wfh_re match: {match.groupdict()}")
            # parse the attrs
            attrs_dict = dict(attrs_nospc_re.findall(match.group('attrs')))
            print(f"{match.group('attrs')=}")
            print(f"{attrs_dict=}")

            print("Found WFH Choice info attributes: {}".format(attrs_dict))

            (new_lines_read,df) = read_wfh_choice_lines(log_fo, attrs_dict, args.base_or_build, args.log_file)
            continue

        match = line_re.match(line)

        if lines_read <= 10:
            if match: print(f"{lines_read:7} generic match: {match.group(3)}")
            else: print(f"{lines_read:7} No match: {line}")

        # end for line in log file object
    log_fo.close()

    print("modechoice_df length: {}".format(len(modechoice_df)))
    print("output_dir={}".format(output_dir))
    if len(modechoice_df) > 0:
        if not os.path.exists(output_dir): os.makedirs(output_dir)

        output_filename = "{}_{}_utilities.csv".format(args.base_or_build, type_str)
        modechoice_df.to_csv(os.path.join(output_dir, output_filename), index=False)
        print("Wrote {}".format(os.path.join(output_dir,output_filename)))
