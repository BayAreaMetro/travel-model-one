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

import argparse, re, os, shutil, sys
import numpy, pandas

NUM_TAZ      = 1454
NUM_SUBZONES = 3
NUM_DEST_ALT = NUM_TAZ*NUM_SUBZONES
NUM_MC_ALT   = 21

# start of every log line
DATE_LOG_TYPE_RE_TXT  = "^(\d\d-\w\w\w-\d\d\d\d \d\d:\d\d:\d\d, INFO, )"

# marks the start of what we're looking for in the work location choice log
TOURDC_RE_TXT         = "(Utility Expressions for (Usual Location Choice Model for:|Individual Non-Mandatory Tour Destination Choice Model,) Purpose=([ A-Za-z\-_]+) for HH=(\d+), PersonNum=(\d+), PersonType=([ A-Za-z\-]+), Tour(Num|Id)=(\d+))"
#                         Utility Expressions for Individual Non-Mandatory Tour Destination Choice Model, Purpose=shopping for HH=47127, PersonNum=2, PersonType=Part-time worker, TourId=0.

# marks the start of the Tour Mode Choice lins in work location choice log
TOURMC_RE_TXT         = "(Utility Expressions for( Individual Non-Mandatory)? Tour Mode Choice Logsum calculation for ([ A-Za-z\-_]+) Location Choice   HH=(\d+), PersonNum=(\d+), PersonType=([ A-Za-z\-]+),( TourId=\d+[,])? destTaz=(\d+) destWalkSubzone=(\d+))"
#                         Utility Expressions for Individual Non-Mandatory    Tour Mode Choice Logsum calculation for shopping Location Choice   HH=47127, PersonNum=2, PersonType=Part-time worker, TourId=0, destTaz=1254 destWalkSubzone=1

# utility expression for one term - coefficient x variable
UTILITY_RE_TXT        = "(\s+([\.\-0-9]+) [*]\s+(([\.\-0-9]+e[+-]\d\d)|NaN|Infinity))"
# utility expression for all terms - expression number  (coefficient x variable)xNUM_DEST_ALT
FULL_UTILITY_RE_TXT   = "(\d+)" + UTILITY_RE_TXT*NUM_DEST_ALT
UTILITY_RE            = re.compile("{}{}".format(DATE_LOG_TYPE_RE_TXT, FULL_UTILITY_RE_TXT))
# utility expression for tour mc terms - expression number  (coefficient x variable)NUM_MC_ALT
MC_UTILITY_RE_TXT     = "(\d+)" + UTILITY_RE_TXT*NUM_MC_ALT
MC_UTILITY_RE         = re.compile("{}{}".format(DATE_LOG_TYPE_RE_TXT, MC_UTILITY_RE_TXT))

# utility express for total utility
TOTAL_UTIL_RE_TXT     = "(\s+(([\.\-0-9]+e[+-]\d\d)|NaN|Infinity))"
# utility expression for all terms
TOTAL_UTILITY_RE_TXT  = "(Alt Utility)" + TOTAL_UTIL_RE_TXT*NUM_DEST_ALT
TOTAL_UTILITY_RE      = re.compile("{}{}".format(DATE_LOG_TYPE_RE_TXT, TOTAL_UTILITY_RE_TXT))
# utility expression for all mode choice terms
MC_TOTAL_UTILITY_RE_TXT = "(Alt Utility)" + TOTAL_UTIL_RE_TXT*NUM_MC_ALT
MC_TOTAL_UTILITY_RE     = re.compile("{}{}".format(DATE_LOG_TYPE_RE_TXT, MC_TOTAL_UTILITY_RE_TXT))

def read_tour_mode_choice_logsum_lines(file_object, type_str, purpose, hh, persnum, ptype, destTaz, destSubz, base_or_build, log_file):
    """
    Read tour mode choice logsum utilities from the file_object
    """
    #if destTaz > 25:
    #    return (0, pandas.DataFrame())

    # from ModeChoice.xls UEC, Work
    WORK_ROW_NAMES = {
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
        12 : "token, age",
        13 : "token, timeOutbound",
        14 : "token, timeInBound",
        15 : "token, tourDuration",
        16 : "token, tourCategoryJoint",
        17 : "token, numberOfParticipantsInJointTour",
        18 : "token, tourCategorySubtour",
        19 : "token, workTourModeIsSOV",
        20 : "token, workTourModeIsBike",
        21 : "token, destZoneAreaType",
        22 : "token, originDensityIndex",
        23 : "token, densityIndex",
        24 : "token, zonalShortWalkOrig",
        25 : "token, zonalLongWalkOrig",
        26 : "token, zonalShortWalkDest",
        27 : "token, zonalLongWalkDest",
        28 : "token, c_ivt",
        29 : "token, c_ivt_lrt",
        30 : "token, c_ivt_ferry",
        31 : "token, c_ivt_exp",
        32 : "token, c_ivt_hvy",
        33 : "token, c_ivt_com",
        34 : "token, c_walkTimeShort",
        35 : "token, c_walkTimeLong",
        36 : "token, c_bikeTimeShort",
        37 : "token, c_bikeTimeLong",
        38 : "token, c_cost",
        39 : "token, c_shortiWait",
        40 : "token, c_longiWait",
        41 : "token, c_wacc",
        42 : "token, c_wegr",
        43 : "token, c_waux",
        44 : "token, c_dtim",
        45 : "token, c_xwait",
        46 : "token, c_dacc_ratio",
        47 : "token, c_xfers_wlk",
        48 : "token, c_xfers_drv",
        49 : "token, c_drvtrn_distpen_0",
        50 : "token, c_drvtrn_distpen_max",
        51 : "token, c_topology_walk",
        52 : "token, c_topology_bike",
        53 : "token, c_topology_trn",
        54 : "token, c_densityIndex",
        55 : "token, c_age1619_da",
        56 : "token, c_age010_trn",
        57 : "token, c_age16p_sr",
        58 : "token, c_hhsize1_sr",
        59 : "token, c_hhsize2_sr",
        60 : "token, costPerMile",
        61 : "token, costShareSr2",
        62 : "token, costShareSr3",
        63 : "token, waitThresh",
        64 : "token, walkThresh",
        65 : "token, shortWalk",
        66 : "token, longWalk",
        67 : "token, walkSpeed",
        68 : "token, bikeThresh",
        69 : "token, bikeSpeed",
        70 : "token, maxCbdAreaTypeThresh",
        71 : "token, indivTour",
        72 : "token, upperEA",
        73 : "token, upperAM",
        74 : "token, upperMD",
        75 : "token, upperPM",
        76 : "token, zeroAutoHh",
        77 : "token, autoDeficientHh",
        78 : "token, autoSufficientHh",
        79 : "token, shortWalkMax",
        80 : "token, longWalkMax",
        81 : "token, walkTransitOrig",
        82 : "token, walkTransitDest",
        83 : "token, walkTransitAvailable",
        84 : "token, driveTransitAvailable",
        85 : "token, originWalkTime",
        86 : "token, originWalkTime",
        87 : "token, destinationWalkTime",
        88 : "token, destinationWalkTime",
        89 : "token, cbdDummy",
        90 : "token, dailyParkingCost",
        91 : "token, costInitialTaxi",
        92 : "token, costPerMileTaxi",
        93 : "token, costPerMinuteTaxi",
        94 : "token, costInitialSingleTNC",
        95 : "token, costPerMileSingleTNC",
        96 : "token, costPerMinuteSingleTNC",
        97 : "token, costMinimumSingleTNC",
        98 : "token, costInitialSharedTNC",
        99 : "token, costPerMileSharedTNC",
        100: "token, costPerMinuteSharedTNC",
        101: "token, costMinimumSharedTNC",
        102: "token, totalWaitTaxi",
        103: "token, totalWaitSingleTNC",
        104: "token, totalWaitSharedTNC",
        105: "token, autoIVTFactorAV",
        106: "token, autoParkingCostFactorAV",
        107: "token, autoCostPerMileFactorAV",
        108: "token, autoTerminalTimeFactorAV",
        109: "token, sharedTNCIVTFactor",
        110: "token, useAV",
        111: "token, autoIVTFactor",
        112: "token, autoParkingCostFactor",
        113: "token, autoCPMFactor",
        114: "token, autoTermTimeFactor",
        115: "token, outPeriod",
        116: "token, outPeriod",
        117: "token, outPeriod",
        118: "token, outPeriod",
        119: "token, outPeriod",
        120: "token, inPeriod",
        121: "token, inPeriod",
        122: "token, inPeriod",
        123: "token, inPeriod",
        124: "token, inPeriod",
        125: "token, sovOut",
        126: "token, sovIn",
        127: "token, sovAvailable",
        128: "token, sovtollAvailable",
        129: "token, hov2Out",
        130: "token, hov2In",
        131: "token, hov2Available",
        132: "token, hov2tollAvailable",
        133: "token, hov3Out",
        134: "token, hov3In",
        135: "token, hov3Available",
        136: "token, hov3tollAvailable",
        137: "token, walkLocalAvailable",
        138: "token, walkLrfAvailable",
        139: "token, walkExpressAvailable",
        140: "token, walkHeavyRailAvailable",
        141: "token, walkCommuterAvailable",
        142: "token, driveLocalAvailable",
        143: "token, driveLrfAvailable",
        144: "token, driveExpressAvailable",
        145: "token, driveHeavyRailAvailable",
        146: "token, driveCommuterAvailable",
        147: "token, walkFerryAvailable",
        148: "token, driveFerryAvailable",
        149: "Drive alone - Unavailable",
        150: "Drive alone - Unavailable for zero auto households",
        151: "Drive alone - Unavailable for persons less than 16",
        152: "Drive alone - Unavailable for joint tours",
        153: "Drive alone - Unavailable if didn't drive to work",
        154: "Drive alone - In-vehicle time",
        155: "Drive alone - Terminal time",
        156: "Drive alone - Operating cost ",
        157: "Drive alone - Parking cost ",
        158: "Drive alone - Bridge toll ",
        159: "Drive alone - Person is between 16 and 19 years old",
        160: "Drive alone toll - Unavailable",
        161: "Drive alone toll - Unavailable for zero auto households",
        162: "Drive alone toll - Unavailable for persons less than 16",
        163: "Drive alone toll - Unavailable for joint tours",
        164: "Drive alone toll - Unavailable if didn't drive to work",
        165: "Drive alone toll - In-vehicle time",
        166: "Drive alone toll - Terminal time",
        167: "Drive alone toll - Operating cost ",
        168: "Drive alone toll - Parking cost ",
        169: "Drive alone toll - Bridge toll ",
        170: "Drive alone toll - Value toll ",
        171: "Drive alone toll - Person is between 16 and 19 years old",
        172: "Shared ride 2 - Unavailable",
        173: "Shared ride 2 - Unavailable based on party size",
        174: "Shared ride 2 - In-vehicle time",
        175: "Shared ride 2 - Terminal time",
        176: "Shared ride 2 - Operating cost ",
        177: "Shared ride 2 - Parking cost ",
        178: "Shared ride 2 - Bridge toll ",
        179: "Shared ride 2 - One person household",
        180: "Shared ride 2 - Two person household",
        181: "Shared ride 2 - Person is 16 years old or older",
        182: "Shared ride 2 toll - Unavailable",
        183: "Shared ride 2 toll - Unavailable based on party size",
        184: "Shared ride 2 toll - In-vehicle time",
        185: "Shared ride 2 toll - Terminal time",
        186: "Shared ride 2 toll - Operating cost ",
        187: "Shared ride 2 toll - Parking cost ",
        188: "Shared ride 2 toll - Bridge toll ",
        189: "Shared ride 2 toll - Value toll ",
        190: "Shared ride 2 toll - One person household",
        191: "Shared ride 2 toll - Two person household",
        192: "Shared ride 2 toll - Person is 16 years old or older",
        193: "Shared ride 3+ - Unavailable",
        194: "Shared ride 3+ - In-vehicle time",
        195: "Shared ride 3+ - Terminal time",
        196: "Shared ride 3+ - Operating cost ",
        197: "Shared ride 3+ - Parking cost ",
        198: "Shared ride 3+ - Bridge toll ",
        199: "Shared ride 3+ - One person household",
        200: "Shared ride 3+ - Two person household",
        201: "Shared ride 3+ - Person is 16 years old or older",
        202: "Shared ride 3+ toll - Unavailable",
        203: "Shared ride 3+ toll - In-vehicle time",
        204: "Shared ride 3+ - Terminal time",
        205: "Shared ride 3+ toll - Operating cost ",
        206: "Shared ride 3+ toll - Parking cost ",
        207: "Shared ride 3+ toll - Bridge toll ",
        208: "Shared ride 3+ toll - Value toll ",
        209: "Shared ride 3+ toll - One person household",
        210: "Shared ride 3+ toll - Two person household",
        211: "Shared ride 3+ toll - Person is 16 years old or older",
        212: "Walk - Time up to 2 miles",
        213: "Walk - Time beyond 2 of a miles",
        214: "Walk - Destination zone densityIndex",
        215: "Walk - Topology",
        216: "Bike - Unavailable if didn't bike to work",
        217: "Bike - Time up to 2 miles",
        218: "Bike - Time beyond 2 of a miles",
        219: "Bike - Destination zone densityIndex",
        220: "Bike - Topology",
        221: "Walk to Local - Unavailable",
        222: "Walk to Local - In-vehicle time",
        223: "Walk to Local - Short iwait time",
        224: "Walk to Local - Long iwait time",
        225: "Walk to Local - transfer wait time",
        226: "Walk to Local - number of transfers",
        227: "Walk to Local - Walk access time",
        228: "Walk to Local - Walk egress time",
        229: "Walk to Local - Walk other time",
        230: "Walk to Local - Fare ",
        231: "Walk to Local - Destination zone densityIndex",
        232: "Walk to Local - Topology",
        233: "Walk to Local - Person is less than 10 years old",
        234: "Walk to Light rail/Ferry - Unavailable",
        235: "Walk to Light rail/Ferry - In-vehicle time",
        236: "Walk to Light rail/Ferry - In-vehicle time on Light Rail (incremental w/ ivt)",
        237: "Walk to Light rail/Ferry - In-vehicle time on Ferry (incremental w/ keyivt)",
        238: "Walk to Light rail/Ferry - Short iwait time",
        239: "Walk to Light rail/Ferry - Long iwait time",
        240: "Walk to Light rail/Ferry - transfer wait time",
        241: "Walk to Light rail/Ferry - number of transfers",
        242: "Walk to Light rail/Ferry - Walk access time",
        243: "Walk to Light rail/Ferry - Walk egress time",
        244: "Walk to Light rail/Ferry - Walk other time",
        245: "Walk to Light rail/Ferry - Fare ",
        246: "Walk to Light rail/Ferry - Destination zone densityIndex",
        247: "Walk to Light rail/Ferry - Topology",
        248: "Walk to Light rail/Ferry - Person is less than 10 years old",
        249: "Walk to Express bus - Unavailable",
        250: "Walk to Express bus - In-vehicle time",
        251: "Walk to Express bus - In-vehicle time on Express bus (incremental w/ ivt)",
        252: "Walk to Express bus - Short iwait time",
        253: "Walk to Express bus - Long iwait time",
        254: "Walk to Express bus - transfer wait time",
        255: "Walk to Express bus - number of transfers",
        256: "Walk to Express bus - Walk access time",
        257: "Walk to Express bus - Walk egress time",
        258: "Walk to Express bus - Walk other time",
        259: "Walk to Express bus - Fare ",
        260: "Walk to Express bus - Destination zone densityIndex",
        261: "Walk to Express bus - Topology",
        262: "Walk to Express bus - Person is less than 10 years old",
        263: "Walk to heavy rail - Unavailable",
        264: "Walk to heavy rail - In-vehicle time",
        265: "Walk to heavy rail - In-vehicle time on heavy rail (incremental w/ ivt)",
        266: "Walk to heavy rail - Short iwait time",
        267: "Walk to heavy rail - Long iwait time",
        268: "Walk to heavy rail - transfer wait time",
        269: "Walk to heavy rail - number of transfers",
        270: "Walk to heavy rail - Walk access time",
        271: "Walk to heavy rail - Walk egress time",
        272: "Walk to heavy rail - Walk other time",
        273: "Walk to heavy rail - Fare ",
        274: "Walk to heavy rail - Destination zone densityIndex",
        275: "Walk to heavy rail - Topology",
        276: "Walk to heavy rail - Person is less than 10 years old",
        277: "Walk to Commuter rail - Unavailable",
        278: "Walk to Commuter rail - In-vehicle time",
        279: "Walk to Commuter rail - In-vehicle time on commuter rail (incremental w/ ivt)",
        280: "Walk to Commuter rail - Short iwait time",
        281: "Walk to Commuter rail - Long iwait time",
        282: "Walk to Commuter rail - transfer wait time",
        283: "Walk to Commuter rail - number of transfers",
        284: "Walk to Commuter rail - Walk access time",
        285: "Walk to Commuter rail - Walk egress time",
        286: "Walk to Commuter rail - Walk other time",
        287: "Walk to Commuter rail - Fare ",
        288: "Walk to Commuter rail - Destination zone densityIndex",
        289: "Walk to Commuter rail - Topology",
        290: "Walk to Commuter rail - Person is less than 10 years old",
        291: "Drive to Local - Unavailable",
        292: "Drive to Local - Unavailable for zero auto households",
        293: "Drive to Local - Unavailable for persons less than 16",
        294: "Drive to Local - In-vehicle time",
        295: "Drive to Local - Short iwait time",
        296: "Drive to Local - Long iwait time",
        297: "Drive to Local - transfer wait time",
        298: "Drive to Local - number of transfers",
        299: "Drive to Local - Drive time",
        300: "Drive to Local - Walk access time (at attraction end)",
        301: "Drive to Local - Walk egress time (at attraction end)",
        302: "Drive to Local - Walk other time",
        303: "Drive to Local - Fare and operating cost ",
        304: "Drive to Local - Ratio of drive access distance to OD distance",
        305: "Drive to Local  - Destination zone densityIndex",
        306: "Drive to Local  - Topology",
        307: "Drive to Local  - Person is less than 10 years old",
        308: "Drive to Light rail/Ferry - Unavailable",
        309: "Drive to Light rail/Ferry - Unavailable for zero auto households",
        310: "Drive to Light rail/Ferry - Unavailable for persons less than 16",
        311: "Drive to Light rail/Ferry - In-vehicle time",
        312: "Drive to Light rail/Ferry - In-vehicle time on Light Rail (incremental w/ ivt)",
        313: "Drive to Light rail/Ferry - In-vehicle time on Ferry (incremental w/ keyivt)",
        314: "drive to Light rail/Ferry - Short iwait time",
        315: "drive to Light rail/Ferry - Long iwait time",
        316: "drive to Light rail/Ferry - transfer wait time",
        317: "drive to Light rail/Ferry - number of transfers",
        318: "Drive to Light rail/Ferry - Drive time",
        319: "Drive to Light rail/Ferry - Walk access time (at attraction end)",
        320: "Drive to Light rail/Ferry - Walk egress time (at attraction end)",
        321: "Drive to Light rail/Ferry - Walk other time",
        322: "Drive to Light rail/Ferry - Fare and operating cost ",
        323: "Drive to Light rail/Ferry - Ratio of drive access distance to OD distance",
        324: "Drive to Light rail/Ferry  - Destination zone densityIndex",
        325: "Drive to Light rail/Ferry  - Topology",
        326: "Drive to Light rail/Ferry  - Person is less than 10 years old",
        327: "Drive to Express bus - Unavailable",
        328: "Drive to Express bus - Unavailable for zero auto households",
        329: "Drive to Express bus - Unavailable for persons less than 16",
        330: "Drive to Express bus - In-vehicle time",
        331: "Drive to Express bus - In-vehicle time on Express bus (incremental w/ ivt)",
        332: "drive to Express bus - Short iwait time",
        333: "drive to Express bus - Long iwait time",
        334: "drive to Express bus - transfer wait time",
        335: "drive to Express bus - number of transfers",
        336: "Drive to Express bus - Drive time",
        337: "Drive to Express bus - Walk access time (at attraction end)",
        338: "Drive to Express bus - Walk egress time (at attraction end)",
        339: "Drive to Express bus - Walk other time",
        340: "Drive to Express bus - Fare and operating cost ",
        341: "Drive to Express bus - Ratio of drive access distance to OD distance",
        342: "Drive to Express bus  - Destination zone densityIndex",
        343: "Drive to Express bus  - Topology",
        344: "Drive to Express bus  - Person is less than 10 years old",
        345: "Drive to heavy rail - Unavailable",
        346: "Drive to heavy rail - Unavailable for zero auto households",
        347: "Drive to heavy rail - Unavailable for persons less than 16",
        348: "Drive to heavy rail - In-vehicle time",
        349: "Drive to heavy rail - In-vehicle time on heavy rail (incremental w/ ivt)",
        350: "drive to heavy rail - Short iwait time",
        351: "drive to heavy rail - Long iwait time",
        352: "drive to heavy rail - transfer wait time",
        353: "drive to heavy rail - number of transfers",
        354: "Drive to heavy rail - Drive time",
        355: "Drive to heavy rail - Walk access time (at attraction end)",
        356: "Drive to heavy rail - Walk egress time (at attraction end)",
        357: "Drive to heavy rail - Walk other time",
        358: "Drive to heavy rail - Fare and operating cost ",
        359: "Drive to heavy rail - Ratio of drive access distance to OD distance",
        360: "Drive to heavy rail  - Destination zone densityIndex",
        361: "Drive to heavy rail  - Topology",
        362: "Drive to heavy rail  - Person is less than 10 years old",
        363: "Drive to Commuter rail - Unavailable",
        364: "Drive to Commuter rail - Unavailable for zero auto households",
        365: "Drive to Commuter rail - Unavailable for persons less than 16",
        366: "Drive to Commuter rail - In-vehicle time",
        367: "Drive to Commuter rail - In-vehicle time on commuter rail (incremental w/ ivt)",
        368: "drive to Commuter rail - Short iwait time",
        369: "drive to Commuter rail - Long iwait time",
        370: "drive to Commuter rail - transfer wait time",
        371: "drive to Commuter rail - number of transfers",
        372: "Drive to Commuter rail - Drive time",
        373: "Drive to Commuter rail - Walk access time (at attraction end)",
        374: "Drive to Commuter rail - Walk egress time (at attraction end)",
        375: "Drive to Commuter rail - Walk other time",
        376: "Drive to Commuter rail - Fare and operating cost ",
        377: "Drive to Commuter rail - Ratio of drive access distance to OD distance",
        378: "Drive to Commuter rail  - Destination zone densityIndex",
        379: "Drive to Commuter rail  - Topology",
        380: "Drive to Commuter rail - Person is less than 10 years old",
        381: "Taxi - In-vehicle time",
        382: "Taxi - Wait time",
        383: "Taxi - Tolls",
        384: "Taxi - Bridge toll",
        385: "Taxi - Fare",
        386: "TNC Single - In-vehicle time",
        387: "TNC Single - Wait time",
        388: "TNC Single - Tolls",
        389: "TNC Single - Bridge toll",
        390: "TNC Single - Cost",
        391: "TNC Shared - In-vehicle time",
        392: "TNC Shared - Wait time",
        393: "TNC Shared - Tolls",
        394: "TNC Shared - Bridge toll",
        395: "TNC Shared - Cost",
        396: "Walk - Alternative-specific constant - Zero auto",
        397: "Walk - Alternative-specific constant - Auto deficient",
        398: "Walk - Alternative-specific constant - Auto sufficient",
        399: "Bike - Alternative-specific constant - Zero auto",
        400: "Bike - Alternative-specific constant - Auto deficient",
        401: "Bike - Alternative-specific constant - Auto sufficient",
        402: "Shared ride 2 - Alternative-specific constant - Zero auto",
        403: "Shared ride 2 - Alternative-specific constant - Auto deficient",
        404: "Shared ride 2 - Alternative-specific constant - Auto sufficient",
        405: "Shared ride 3+ - Alternative-specific constant - Zero auto",
        406: "Shared ride 3+ - Alternative-specific constant - Auto deficient",
        407: "Shared ride 3+ - Alternative-specific constant - Auto sufficient",
        408: "Walk to Transit - Alternative-specific constant - Zero auto",
        409: "Walk to Transit - Alternative-specific constant - Auto deficient",
        410: "Walk to Transit - Alternative-specific constant - Auto sufficient",
        411: "Drive to Transit  - Alternative-specific constant - Zero auto",
        412: "Drive to Transit  - Alternative-specific constant - Auto deficient",
        413: "Drive to Transit  - Alternative-specific constant - Auto sufficient",
        414: "Taxi - Alternative-specific constant - Zero auto",
        415: "Taxi - Alternative-specific constant - Auto deficient",
        416: "Taxi - Alternative-specific constant - Auto sufficient",
        417: "TNC-Single - Alternative-specific constant - Zero auto",
        418: "TNC-Single - Alternative-specific constant - Auto deficient",
        419: "TNC-Single - Alternative-specific constant - Auto sufficient",
        420: "TNC-Shared - Alternative-specific constant - Zero auto",
        421: "TNC-Shared - Alternative-specific constant - Auto deficient",
        422: "TNC-Shared - Alternative-specific constant - Auto sufficient",
        423: "Walk - Alternative-specific constant - Joint Tours",
        424: "Walk - Alternative-specific constant - Joint Tours",
        425: "Walk - Alternative-specific constant - Joint Tours",
        426: "Bike - Alternative-specific constant - Joint Tours",
        427: "Bike - Alternative-specific constant - Joint Tours",
        428: "Bike - Alternative-specific constant - Joint Tours",
        429: "Shared ride 2 - Alternative-specific constant - Joint Tours",
        430: "Shared ride 2 - Alternative-specific constant - Joint Tours",
        431: "Shared ride 2 - Alternative-specific constant - Joint Tours",
        432: "Shared ride 3+ - Alternative-specific constant - Joint Tours",
        433: "Shared ride 3+ - Alternative-specific constant - Joint Tours",
        434: "Shared ride 3+ - Alternative-specific constant - Joint Tours",
        435: "Walk to Transit - Alternative-specific constant - Joint Tours",
        436: "Walk to Transit - Alternative-specific constant - Joint Tours",
        437: "Walk to Transit - Alternative-specific constant - Joint Tours",
        438: "Drive to Transit  - Alternative-specific constant - Joint Tours",
        439: "Drive to Transit  - Alternative-specific constant - Joint Tours",
        440: "Drive to Transit  - Alternative-specific constant - Joint Tours",
        441: "Taxi - Alternative-specific constant - Zero auto - Joint Tours",
        442: "Taxi - Alternative-specific constant - Auto deficient - Joint Tours",
        443: "Taxi - Alternative-specific constant - Auto sufficient - Joint Tours",
        444: "TNC-Single - Alternative-specific constant - Zero auto - Joint Tours",
        445: "TNC-Single - Alternative-specific constant - Auto deficient - Joint Tours",
        446: "TNC-Single - Alternative-specific constant - Auto sufficient - Joint Tours",
        447: "TNC-Shared - Alternative-specific constant - Zero auto - Joint Tours",
        448: "TNC-Shared - Alternative-specific constant - Auto deficient - Joint Tours",
        449: "TNC-Shared - Alternative-specific constant - Auto sufficient - Joint Tours",
        450: "Local bus",
        451: "Light rail - Alternative-specific constant (walk access)",
        452: "Light rail - Alternative-specific constant (drive access)",
        453: "Ferry - Alternative-specific constant (walk access)",
        454: "Ferry - Alternative-specific constant (drive access)",
        455: "Express bus - Alternative-specific constant",
        456: "Heavy rail - Alternative-specific constant ",
        457: "Commuter rail - Alternative-specific constant ",
        458: "Walk to Transit - CBD dummy",
        459: "Drive to Transit  - CBD dummy",
        460: "Walk to Transit - San Francisco dummy",
        461: "Drive to Transit - San Francisco dummy",
        462: "Walk to Transit - Within SF dummy",
        463: "Drive to Transit - Within SF dummy",
        464: "Drive to Transit - distance penalty",
        465: "Walk not available for long distances",
        466: "Bike not available for long distances",
        467: "Sharing preference adjustment - car modes",
        468: "Sharing preference adjustment - walk to light rail",
        469: "Sharing preference adjustment - drive to light rail",
        470: "Sharing preference adjustment - walk to ferry",
        471: "Sharing preference adjustment - drive to ferry",
        472: "Sharing preference adjustment - express bus",
        473: "Sharing preference adjustment - heavy rail",
        474: "Sharing preference adjustment - commuter rail",
        475: "TNC single adjustment",
        476: "TNC shared adjustment"
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
        12 : "token, age",
        13 : "token, timeOutbound",
        14 : "token, timeInbound",
        15 : "token, tourDuration",
        16 : "token, tourCategoryJoint",
        17 : "token, numberOfParticipantsInJointTour",
        18 : "token, tourCategorySubtour",
        19 : "token, workTourModeIsSOV",
        20 : "token, workTourModeIsBike",
        21 : "token, destZoneAreaType",
        22 : "token, originDensityIndex",
        23 : "token, densityIndex",
        24 : "token, zonalShortWalkOrig",
        25 : "token, zonalLongWalkOrig",
        26 : "token, zonalShortWalkDest",
        27 : "token, zonalLongWalkDest",
        28 : "token, c_ivt",
        29 : "token, c_ivt_lrt",
        30 : "token, c_ivt_ferry",
        31 : "token, c_ivt_exp",
        32 : "token, c_ivt_hvy",
        33 : "token, c_ivt_com",
        34 : "token, c_walkTimeShort",
        35 : "token, c_walkTimeLong",
        36 : "token, c_bikeTimeShort",
        37 : "token, c_bikeTimeLong",
        38 : "token, c_cost",
        39 : "token, c_shortiWait",
        40 : "token, c_longiWait",
        41 : "token, c_wacc",
        42 : "token, c_wegr",
        43 : "token, c_waux",
        44 : "token, c_dtim",
        45 : "token, c_xwait",
        46 : "token, c_dacc_ratio",
        47 : "token, c_xfers_wlk",
        48 : "token, c_xfers_drv",
        49 : "token, c_drvtrn_distpen_0",
        50 : "token, c_drvtrn_distpen_max",
        51 : "token, c_topology_walk",
        52 : "token, c_topology_bike",
        53 : "token, c_topology_trn",
        54 : "token, c_densityIndex",
        55 : "token, c_age1619_da",
        56 : "token, c_age010_trn",
        57 : "token, c_age16p_sr",
        58 : "token, c_hhsize1_sr",
        59 : "token, c_hhsize2_sr",
        60 : "token, costPerMile",
        61 : "token, costShareSr2",
        62 : "token, costShareSr3",
        63 : "token, waitThresh",
        64 : "token, walkThresh",
        65 : "token, shortWalk",
        66 : "token, longWalk",
        67 : "token, walkSpeed",
        68 : "token, bikeThresh",
        69 : "token, bikeSpeed",
        70 : "token, maxCbdAreaTypeThresh",
        71 : "token, indivTour",
        72 : "token, upperEA",
        73 : "token, upperAM",
        74 : "token, upperMD",
        75 : "token, upperPM",
        76 : "token, zeroAutoHh",
        77 : "token, autoDeficientHh",
        78 : "token, autoSufficientHh",
        79 : "token, shortWalkMax",
        80 : "token, longWalkMax",
        81 : "token, walkTransitOrig",
        82 : "token, walkTransitDest",
        83 : "token, walkTransitAvailable",
        84 : "token, driveTransitAvailable",
        85 : "token, originWalkTime",
        86 : "token, originWalkTime",
        87 : "token, destinationWalkTime",
        88 : "token, destinationWalkTime",
        89 : "token, cbdDummy",
        90 : "token, dailyParkingCost",
        91 : "token, costInitialTaxi",
        92 : "token, costPerMileTaxi",
        93 : "token, costPerMinuteTaxi",
        94 : "token, costInitialSingleTNC",
        95 : "token, costPerMileSingleTNC",
        96 : "token, costPerMinuteSingleTNC",
        97 : "token, costMinimumSingleTNC",
        98 : "token, costInitialSharedTNC",
        99 : "token, costPerMileSharedTNC",
        100: "token, costPerMinuteSharedTNC",
        101: "token, costMinimumSharedTNC",
        102: "token, totalWaitTaxi",
        103: "token, totalWaitSingleTNC",
        104: "token, totalWaitSharedTNC",
        105: "token, autoIVTFactorAV",
        106: "token, autoParkingCostFactorAV",
        107: "token, autoCostPerMileFactorAV",
        108: "token, autoTerminalTimeFactorAV",
        109: "token, sharedTNCIVTFactor",
        110: "token, useAV",
        111: "token, autoIVTFactor",
        112: "token, autoParkingCostFactor",
        113: "token, autoCPMFactor",
        114: "token, autoTermTimeFactor",
        115: "token, outPeriod",
        116: "token, outPeriod",
        117: "token, outPeriod",
        118: "token, outPeriod",
        119: "token, outPeriod",
        120: "token, inPeriod",
        121: "token, inPeriod",
        122: "token, inPeriod",
        123: "token, inPeriod",
        124: "token, inPeriod",
        125: "token, sovOut",
        126: "token, sovIn",
        127: "token, sovAvailable",
        128: "token, sovtollAvailable",
        129: "token, hov2Out",
        130: "token, hov2In",
        131: "token, hov2Available",
        132: "token, hov2tollAvailable",
        133: "token, hov3Out",
        134: "token, hov3In",
        135: "token, hov3Available",
        136: "token, hov3tollAvailable",
        137: "token, walkLocalAvailable",
        138: "token, walkLrfAvailable",
        139: "token, walkExpressAvailable",
        140: "token, walkHeavyRailAvailable",
        141: "token, walkCommuterAvailable",
        142: "token, driveLocalAvailable",
        143: "token, driveLrfAvailable",
        144: "token, driveExpressAvailable",
        145: "token, driveHeavyRailAvailable",
        146: "token, driveCommuterAvailable",
        147: "token, walkFerryAvailable",
        148: "token, driveFerryAvailable",
        149: "Drive alone - Unavailable",
        150: "Drive alone - Unavailable for zero auto households",
        151: "Drive alone - Unavailable for persons less than 16",
        152: "Drive alone - Unavailable for joint tours",
        153: "Drive alone - Unavailable if didn't drive to work",
        154: "Drive alone - In-vehicle time",
        155: "Drive alone - Terminal time",
        156: "Drive alone - Operating cost ",
        157: "Drive alone - Parking cost ",
        158: "Drive alone - Bridge toll ",
        159: "Drive alone - Person is between 16 and 19 years old",
        160: "Drive alone toll - Unavailable",
        161: "Drive alone toll - Unavailable for zero auto households",
        162: "Drive alone toll - Unavailable for persons less than 16",
        163: "Drive alone toll - Unavailable for joint tours",
        164: "Drive alone toll - Unavailable if didn't drive to work",
        165: "Drive alone toll - In-vehicle time",
        166: "Drive alone toll - Terminal time",
        167: "Drive alone toll - Operating cost ",
        168: "Drive alone toll - Parking cost ",
        169: "Drive alone toll - Bridge toll ",
        170: "Drive alone toll - Value toll ",
        171: "Drive alone toll - Person is between 16 and 19 years old",
        172: "Shared ride 2 - Unavailable",
        173: "Shared ride 2 - Unavailable based on party size",
        174: "Shared ride 2 - In-vehicle time",
        175: "Shared ride 2 - Terminal time",
        176: "Shared ride 2 - Operating cost ",
        177: "Shared ride 2 - Parking cost ",
        178: "Shared ride 2 - Bridge toll ",
        179: "Shared ride 2 - One person household",
        180: "Shared ride 2 - Two person household",
        181: "Shared ride 2 - Person is 16 years old or older",
        182: "Shared ride 2 toll - Unavailable",
        183: "Shared ride 2 toll - Unavailable based on party size",
        184: "Shared ride 2 toll - In-vehicle time",
        185: "Shared ride 2 toll - Terminal time",
        186: "Shared ride 2 toll - Operating cost ",
        187: "Shared ride 2 toll - Parking cost ",
        188: "Shared ride 2 toll - Bridge toll ",
        189: "Shared ride 2 toll - Value toll ",
        190: "Shared ride 2 toll - One person household",
        191: "Shared ride 2 toll - Two person household",
        192: "Shared ride 2 toll - Person is 16 years old or older",
        193: "Shared ride 3+ - Unavailable",
        194: "Shared ride 3+ - In-vehicle time",
        195: "Shared ride 3+ - Terminal time",
        196: "Shared ride 3+ - Operating cost ",
        197: "Shared ride 3+ - Parking cost ",
        198: "Shared ride 3+ - Bridge toll ",
        199: "Shared ride 3+ - One person household",
        200: "Shared ride 3+ - Two person household",
        201: "Shared ride 3+ - Person is 16 years old or older",
        202: "Shared ride 3+ toll - Unavailable",
        203: "Shared ride 3+ toll - In-vehicle time",
        204: "Shared ride 3+ - Terminal time",
        205: "Shared ride 3+ toll - Operating cost ",
        206: "Shared ride 3+ toll - Parking cost ",
        207: "Shared ride 3+ toll - Bridge toll ",
        208: "Shared ride 3+ toll - Value toll ",
        209: "Shared ride 3+ toll - One person household",
        210: "Shared ride 3+ toll - Two person household",
        211: "Shared ride 3+ toll - Person is 16 years old or older",
        212: "Walk - Time up to 2 miles",
        213: "Walk - Time beyond 2 of a miles",
        214: "Walk - Destination zone densityIndex",
        215: "Walk - Topology",
        216: "Bike - Unavailable if didn't bike to work",
        217: "Bike - Time up to 2 miles",
        218: "Bike - Time beyond 2 of a miles",
        219: "Bike - Destination zone densityIndex",
        220: "Bike - Topology",
        221: "Walk to Local - Unavailable",
        222: "Walk to Local - In-vehicle time",
        223: "Walk to Local - Short iwait time",
        224: "Walk to Local - Long iwait time",
        225: "Walk to Local - transfer wait time",
        226: "Walk to Local - number of transfers",
        227: "Walk to Local - Walk access time",
        228: "Walk to Local - Walk egress time",
        229: "Walk to Local - Walk other time",
        230: "Walk to Local - Fare ",
        231: "Walk to Local - Destination zone densityIndex",
        232: "Walk to Local - Topology",
        233: "Walk to Local - Person is less than 10 years old",
        234: "Walk to Light rail/Ferry - Unavailable",
        235: "Walk to Light rail/Ferry - In-vehicle time",
        236: "Walk to Light rail/Ferry - In-vehicle time on Light Rail (incremental w/ ivt)",
        237: "Walk to Light rail/Ferry - In-vehicle time on Ferry (incremental w/ keyivt)",
        238: "Walk to Light rail/Ferry - Short iwait time",
        239: "Walk to Light rail/Ferry - Long iwait time",
        240: "Walk to Light rail/Ferry - transfer wait time",
        241: "Walk to Light rail/Ferry - number of transfers",
        242: "Walk to Light rail/Ferry - Walk access time",
        243: "Walk to Light rail/Ferry - Walk egress time",
        244: "Walk to Light rail/Ferry - Walk other time",
        245: "Walk to Light rail/Ferry - Fare ",
        246: "Walk to Light rail/Ferry - Destination zone densityIndex",
        247: "Walk to Light rail/Ferry - Topology",
        248: "Walk to Light rail/Ferry - Person is less than 10 years old",
        249: "Walk to Express bus - Unavailable",
        250: "Walk to Express bus - In-vehicle time",
        251: "Walk to Express bus - In-vehicle time on Express bus (incremental w/ ivt)",
        252: "Walk to Express bus - Short iwait time",
        253: "Walk to Express bus - Long iwait time",
        254: "Walk to Express bus - transfer wait time",
        255: "Walk to Express bus - number of transfers",
        256: "Walk to Express bus - Walk access time",
        257: "Walk to Express bus - Walk egress time",
        258: "Walk to Express bus - Walk other time",
        259: "Walk to Express bus - Fare ",
        260: "Walk to Express bus - Destination zone densityIndex",
        261: "Walk to Express bus - Topology",
        262: "Walk to Express bus - Person is less than 10 years old",
        263: "Walk to heavy rail - Unavailable",
        264: "Walk to heavy rail - In-vehicle time",
        265: "Walk to heavy rail - In-vehicle time on heavy rail (incremental w/ ivt)",
        266: "Walk to heavy rail - Short iwait time",
        267: "Walk to heavy rail - Long iwait time",
        268: "Walk to heavy rail - transfer wait time",
        269: "Walk to heavy rail - number of transfers",
        270: "Walk to heavy rail - Walk access time",
        271: "Walk to heavy rail - Walk egress time",
        272: "Walk to heavy rail - Walk other time",
        273: "Walk to heavy rail - Fare ",
        274: "Walk to heavy rail - Destination zone densityIndex",
        275: "Walk to heavy rail - Topology",
        276: "Walk to heavy rail - Person is less than 10 years old",
        277: "Walk to Commuter rail - Unavailable",
        278: "Walk to Commuter rail - In-vehicle time",
        279: "Walk to Commuter rail - In-vehicle time on commuter rail (incremental w/ ivt)",
        280: "Walk to Commuter rail - Short iwait time",
        281: "Walk to Commuter rail - Long iwait time",
        282: "Walk to Commuter rail - transfer wait time",
        283: "Walk to Commuter rail - number of transfers",
        284: "Walk to Commuter rail - Walk access time",
        285: "Walk to Commuter rail - Walk egress time",
        286: "Walk to Commuter rail - Walk other time",
        287: "Walk to Commuter rail - Fare ",
        288: "Walk to Commuter rail - Destination zone densityIndex",
        289: "Walk to Commuter rail - Topology",
        290: "Walk to Commuter rail - Person is less than 10 years old",
        291: "Drive to Local - Unavailable",
        292: "Drive to Local - Unavailable for zero auto households",
        293: "Drive to Local - Unavailable for persons less than 16",
        294: "Drive to Local - In-vehicle time",
        295: "Drive to Local - Short iwait time",
        296: "Drive to Local - Long iwait time",
        297: "Drive to Local - transfer wait time",
        298: "Drive to Local - number of transfers",
        299: "Drive to Local - Drive time",
        300: "Drive to Local - Walk access time (at attraction end)",
        301: "Drive to Local - Walk egress time (at attraction end)",
        302: "Drive to Local - Walk other time",
        303: "Drive to Local - Fare and operating cost ",
        304: "Drive to Local - Ratio of drive access distance to OD distance",
        305: "Drive to Local  - Destination zone densityIndex",
        306: "Drive to Local  - Topology",
        307: "Drive to Local  - Person is less than 10 years old",
        308: "Drive to Light rail/Ferry - Unavailable",
        309: "Drive to Light rail/Ferry - Unavailable for zero auto households",
        310: "Drive to Light rail/Ferry - Unavailable for persons less than 16",
        311: "Drive to Light rail/Ferry - In-vehicle time",
        312: "Drive to Light rail/Ferry - In-vehicle time on Light Rail (incremental w/ ivt)",
        313: "Drive to Light rail/Ferry - In-vehicle time on Ferry (incremental w/ keyivt)",
        314: "drive to Light rail/Ferry - Short iwait time",
        315: "drive to Light rail/Ferry - Long iwait time",
        316: "drive to Light rail/Ferry - transfer wait time",
        317: "drive to Light rail/Ferry - number of transfers",
        318: "Drive to Light rail/Ferry - Drive time",
        319: "Drive to Light rail/Ferry - Walk access time (at attraction end)",
        320: "Drive to Light rail/Ferry - Walk egress time (at attraction end)",
        321: "Drive to Light rail/Ferry - Walk other time",
        322: "Drive to Light rail/Ferry - Fare and operating cost ",
        323: "Drive to Light rail/Ferry - Ratio of drive access distance to OD distance",
        324: "Drive to Light rail/Ferry  - Destination zone densityIndex",
        325: "Drive to Light rail/Ferry  - Topology",
        326: "Drive to Light rail/Ferry  - Person is less than 10 years old",
        327: "Drive to Express bus - Unavailable",
        328: "Drive to Express bus - Unavailable for zero auto households",
        329: "Drive to Express bus - Unavailable for persons less than 16",
        330: "Drive to Express bus - In-vehicle time",
        331: "Drive to Express bus - In-vehicle time on Express bus (incremental w/ ivt)",
        332: "drive to Express bus - Short iwait time",
        333: "drive to Express bus - Long iwait time",
        334: "drive to Express bus - transfer wait time",
        335: "drive to Express bus - number of transfers",
        336: "Drive to Express bus - Drive time",
        337: "Drive to Express bus - Walk access time (at attraction end)",
        338: "Drive to Express bus - Walk egress time (at attraction end)",
        339: "Drive to Express bus - Walk other time",
        340: "Drive to Express bus - Fare and operating cost ",
        341: "Drive to Express bus - Ratio of drive access distance to OD distance",
        342: "Drive to Express bus  - Destination zone densityIndex",
        343: "Drive to Express bus  - Topology",
        344: "Drive to Express bus  - Person is less than 10 years old",
        345: "Drive to heavy rail - Unavailable",
        346: "Drive to heavy rail - Unavailable for zero auto households",
        347: "Drive to heavy rail - Unavailable for persons less than 16",
        348: "Drive to heavy rail - In-vehicle time",
        349: "Drive to heavy rail - In-vehicle time on heavy rail (incremental w/ ivt)",
        350: "drive to heavy rail - Short iwait time",
        351: "drive to heavy rail - Long iwait time",
        352: "drive to heavy rail - transfer wait time",
        353: "drive to heavy rail - number of transfers",
        354: "Drive to heavy rail - Drive time",
        355: "Drive to heavy rail - Walk access time (at attraction end)",
        356: "Drive to heavy rail - Walk egress time (at attraction end)",
        357: "Drive to heavy rail - Walk other time",
        358: "Drive to heavy rail - Fare and operating cost ",
        359: "Drive to heavy rail - Ratio of drive access distance to OD distance",
        360: "Drive to heavy rail  - Destination zone densityIndex",
        361: "Drive to heavy rail  - Topology",
        362: "Drive to heavy rail  - Person is less than 10 years old",
        363: "Drive to Commuter rail - Unavailable",
        364: "Drive to Commuter rail - Unavailable for zero auto households",
        365: "Drive to Commuter rail - Unavailable for persons less than 16",
        366: "Drive to Commuter rail - In-vehicle time",
        367: "Drive to Commuter rail - In-vehicle time on commuter rail (incremental w/ ivt)",
        368: "drive to Commuter rail - Short iwait time",
        369: "drive to Commuter rail - Long iwait time",
        370: "drive to Commuter rail - transfer wait time",
        371: "drive to Commuter rail - number of transfers",
        372: "Drive to Commuter rail - Drive time",
        373: "Drive to Commuter rail - Walk access time (at attraction end)",
        374: "Drive to Commuter rail - Walk egress time (at attraction end)",
        375: "Drive to Commuter rail - Walk other time",
        376: "Drive to Commuter rail - Fare and operating cost ",
        377: "Drive to Commuter rail - Ratio of drive access distance to OD distance",
        378: "Drive to Commuter rail  - Destination zone densityIndex",
        379: "Drive to Commuter rail  - Topology",
        380: "Drive to Commuter rail - Person is less than 10 years old",
        381: "Taxi - In-vehicle time",
        382: "Taxi - Wait time",
        383: "Taxi - Tolls",
        384: "Taxi - Bridge toll",
        385: "Taxi - Fare",
        386: "TNC Single - In-vehicle time",
        387: "TNC Single - Wait time",
        388: "TNC Single - Tolls",
        389: "TNC Single - Bridge toll",
        390: "TNC Single - Cost",
        391: "TNC Shared - In-vehicle time",
        392: "TNC Shared - Wait time",
        393: "TNC Shared - Tolls",
        394: "TNC Shared - Bridge toll",
        395: "TNC Shared - Cost",
        396: "Walk - Alternative-specific constant - Zero auto",
        397: "Walk - Alternative-specific constant - Auto deficient",
        398: "Walk - Alternative-specific constant - Auto sufficient",
        399: "Bike - Alternative-specific constant - Zero auto",
        400: "Bike - Alternative-specific constant - Auto deficient",
        401: "Bike - Alternative-specific constant - Auto sufficient",
        402: "Shared ride 2 - Alternative-specific constant - Zero auto",
        403: "Shared ride 2 - Alternative-specific constant - Auto deficient",
        404: "Shared ride 2 - Alternative-specific constant - Auto sufficient",
        405: "Shared ride 3+ - Alternative-specific constant - Zero auto",
        406: "Shared ride 3+ - Alternative-specific constant - Auto deficient",
        407: "Shared ride 3+ - Alternative-specific constant - Auto sufficient",
        408: "Walk to Transit - Alternative-specific constant - Zero auto",
        409: "Walk to Transit - Alternative-specific constant - Auto deficient",
        410: "Walk to Transit - Alternative-specific constant - Auto sufficient",
        411: "Drive to Transit  - Alternative-specific constant - Zero auto",
        412: "Drive to Transit  - Alternative-specific constant - Auto deficient",
        413: "Drive to Transit  - Alternative-specific constant - Auto sufficient",
        414: "Taxi - Alternative-specific constant - Zero auto",
        415: "Taxi - Alternative-specific constant - Auto deficient",
        416: "Taxi - Alternative-specific constant - Auto sufficient",
        417: "TNC-Single - Alternative-specific constant - Zero auto",
        418: "TNC-Single - Alternative-specific constant - Auto deficient",
        419: "TNC-Single - Alternative-specific constant - Auto sufficient",
        420: "TNC-Shared - Alternative-specific constant - Zero auto",
        421: "TNC-Shared - Alternative-specific constant - Auto deficient",
        422: "TNC-Shared - Alternative-specific constant - Auto sufficient",
        423: "Walk - Alternative-specific constant - Joint Tours",
        424: "Walk - Alternative-specific constant - Joint Tours",
        425: "Walk - Alternative-specific constant - Joint Tours",
        426: "Bike - Alternative-specific constant - Joint Tours",
        427: "Bike - Alternative-specific constant - Joint Tours",
        428: "Bike - Alternative-specific constant - Joint Tours",
        429: "Shared ride 2 - Alternative-specific constant - Joint Tours",
        430: "Shared ride 2 - Alternative-specific constant - Joint Tours",
        431: "Shared ride 2 - Alternative-specific constant - Joint Tours",
        432: "Shared ride 3+ - Alternative-specific constant - Joint Tours",
        433: "Shared ride 3+ - Alternative-specific constant - Joint Tours",
        434: "Shared ride 3+ - Alternative-specific constant - Joint Tours",
        435: "Walk to Transit - Alternative-specific constant - Joint Tours",
        436: "Walk to Transit - Alternative-specific constant - Joint Tours",
        437: "Walk to Transit - Alternative-specific constant - Joint Tours",
        438: "Drive to Transit  - Alternative-specific constant - Joint Tours",
        439: "Drive to Transit  - Alternative-specific constant - Joint Tours",
        440: "Drive to Transit  - Alternative-specific constant - Joint Tours",
        441: "Taxi - Alternative-specific constant - Zero auto - Joint Tours",
        442: "Taxi - Alternative-specific constant - Auto deficient - Joint Tours",
        443: "Taxi - Alternative-specific constant - Auto sufficient - Joint Tours",
        444: "TNC-Single - Alternative-specific constant - Zero auto - Joint Tours",
        445: "TNC-Single - Alternative-specific constant - Auto deficient - Joint Tours",
        446: "TNC-Single - Alternative-specific constant - Auto sufficient - Joint Tours",
        447: "TNC-Shared - Alternative-specific constant - Zero auto - Joint Tours",
        448: "TNC-Shared - Alternative-specific constant - Auto deficient - Joint Tours",
        449: "TNC-Shared - Alternative-specific constant - Auto sufficient - Joint Tours",
        450: "Local bus",
        451: "Light rail - Alternative-specific constant (walk access)",
        452: "Light rail - Alternative-specific constant (drive access)",
        453: "Ferry - Alternative-specific constant (walk access)",
        454: "Ferry - Alternative-specific constant (drive access)",
        455: "Express bus - Alternative-specific constant",
        456: "Heavy rail - Alternative-specific constant ",
        457: "Commuter rail - Alternative-specific constant ",
        458: "Walk to Transit - CBD dummy",
        459: "Drive to Transit  - CBD dummy",
        460: "Walk to Transit - San Francisco dummy",
        461: "Drive to Transit - San Francisco dummy",
        462: "Walk to Transit - Within SF dummy",
        463: "Drive to Transit - Within SF dummy",
        464: "Drive to Transit - distance penalty",
        465: "Walk not available for long distances",
        466: "Bike not available for long distances",
        467: "Sharing preference adjustment - car modes",
        468: "Sharing preference adjustment - walk to light rail",
        469: "Sharing preference adjustment - drive to light rail",
        470: "Sharing preference adjustment - walk to ferry",
        471: "Sharing preference adjustment - drive to ferry",
        472: "Sharing preference adjustment - express bus",
        473: "Sharing preference adjustment - heavy rail",
        474: "Sharing preference adjustment - commuter rail",
        475: "TNC single adjustment",
        476: "TNC shared adjustment",
    }
    # 06-Aug-2019 09:24:58, INFO, *******************************************************************************************
    # 06-Aug-2019 09:24:58, INFO, For each model expression, 'coeff * expressionValue' pairs are listed for each available alternative.  At the end, total utility is listed.
    # 06-Aug-2019 09:24:58, INFO, The last line shows total utility for each available alternative.
    # 06-Aug-2019 09:24:58, INFO, Exp                               1                             2                             3                             4                             5                             6                             7                             8                             9                            10                            11                            12                            13                            14                            15                            16                            17                            18                            19                            20                            21
    # 06-Aug-2019 09:24:58, INFO, --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # 06-Aug-2019 09:24:58, INFO, 1           0.00000 *   5.76907e+00       0.00000 *   5.76907e+00       0.00000 *   5.76907e+00       0.00000 *   5.76907e+00       0.00000 *   5.7

    ROW_NAMES = WORK_ROW_NAMES
    if type_str == "NonMandLocChoice":
        ROW_NAMES = SHOPPING_ROW_NAMES

    # read 5 lines that we don't care about
    for lines_read in range(1,6):
        line = file_object.readline().strip()
        # print("{}   {}".format(lines_read, line[:30]))

    row_alt_dicts = []

    # read utiltities
    for utils_read in range(1,len(ROW_NAMES)+1):
        line     = file_object.readline().strip()
        match    = MC_UTILITY_RE.match(line)
        row_num   = int(match.group(2)) # row number
        row_descr = ROW_NAMES[row_num]

        full_idx  = 3  # coefficient x variable
        for mode_alt in range(1, NUM_MC_ALT+1):
            row_alt_dict = {}
            row_alt_dict["row num"        ] = row_num
            row_alt_dict["row description"] = row_descr
            row_alt_dict["mode alt"       ] = mode_alt
            row_alt_dict["dest taz"       ] = destTaz
            row_alt_dict["dest subzone"   ] = destSubz
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

    if destTaz == 1 and destSubz == 0:
        print(match.groups())

    full_idx = 3 # TOTAL_UTIL_RE_TXT
    for mode_alt in range(1,NUM_MC_ALT+1):
        row_alt_dict = {}
        row_alt_dict["row num"        ] = -1
        row_alt_dict["row description"] = "Total Utility"
        row_alt_dict["mode alt"       ] = mode_alt
        row_alt_dict["dest taz"       ] = destTaz
        row_alt_dict["dest subzone"   ] = destSubz
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

    # to keep reasonable, drop everything with coefficient == 0
    df = df.loc[ df.coefficient != 0]
    # drop alternative specific constants
    df = df.loc[ (df["row num"] < 396)|(df["row num"] > 463)]

    if destTaz == 1 and destSubz == 0:
        print("head: \n{}".format(df.head(NUM_MC_ALT)))
        print("tail: \n{}".format(df.tail(NUM_MC_ALT)))

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

if __name__ == '__main__':
    pandas.options.display.width = 1000
    pandas.options.display.max_columns = 100

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument("base_or_build",  choices=["base","build"], help="For output file name")
    parser.add_argument("log_file",  metavar="event-node0-something.log", help="Log file to parse")

    args = parser.parse_args()


    line_re     = re.compile("{}(.*)$".format(DATE_LOG_TYPE_RE_TXT))
    tour_dc_re  = re.compile("{}{}".format(DATE_LOG_TYPE_RE_TXT, TOURDC_RE_TXT))
    tour_mc_re  = re.compile("{}{}".format(DATE_LOG_TYPE_RE_TXT, TOURMC_RE_TXT))

    print("Reading {}".format(args.log_file))
    log_fo = open(args.log_file, 'r')
    lines_read = 0
    output_dir = None
    tour_mc_df = pandas.DataFrame()

    while True:
        line = log_fo.readline().strip()
        # check for eof
        if line == "": break

        lines_read += 1

        match = tour_mc_re.match(line)
        if match:
            nonm    = match.group(3)
            purpose = match.group(4)
            hh      = match.group(5)
            persnum = match.group(6)
            ptype   = match.group(7)
            destTaz = int(match.group(9))
            destSubz= int(match.group(10))

            type_str = "UsualWorkLocChoice"
            if nonm and "Individual Non-Mandatory" in nonm:
                type_str = "NonMandLocChoice"

            print("Found Tour Mode Choice logsum info for purpose={} hh={} persnum={} ptype={} destTaz={} destWalkSubzone={}".format(
                  purpose, hh, persnum, ptype, destTaz, destSubz))


            (new_lines_read,df) = read_tour_mode_choice_logsum_lines(log_fo, type_str, purpose, hh, persnum, ptype, destTaz, destSubz, args.base_or_build, args.log_file)
            lines_read += new_lines_read
            tour_mc_df = tour_mc_df.append(df)

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

        match = line_re.match(line)

        if lines_read <= 10:
            print(match.group(2))

        # end for line in log file object
    log_fo.close()

    print("tour_mc_df length: {}".format(len(tour_mc_df)))
    if len(tour_mc_df) > 0:
        output_filename = "{}_tourmc_utilities.csv".format(args.base_or_build)
        tour_mc_df.to_csv(os.path.join(output_dir, output_filename), index=False)
        print("Wrote {}".format(os.path.join(output_dir,output_filename)))
