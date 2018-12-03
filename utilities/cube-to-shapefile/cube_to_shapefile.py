USAGE = """

Create shapefile of Cube network, roadway and transit.

Requires arcpy, so may need to need arcgis version of python

 e.g. set PATH=C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3
      python cube_to_shapefile.py roadway.net

 It saves all output to the current working directory.
 The roadway network is: network_nodes.shp and network_links.shp

"""

import argparse, collections, csv, logging, os, re, subprocess, sys, traceback
import numpy, pandas

RUNTPP_PATH     = "C:\\Program Files (x86)\\Citilabs\\CubeVoyager"
LOG_FILE        = "cube_to_shapefile.log"

# shapefiles
NODE_SHPFILE    = "network_nodes.shp"
LINK_SHPFILE    = "network_links.shp"

TRN_LINES_SHPFILE = "network_trn_lines{}.shp"
TRN_LINKS_SHPFILE = "network_trn_links{}.shp"
TRN_STOPS_SHPFILE = "network_trn_stops{}.shp"

# aggregated by name set
TRN_ROUTE_LINKS_SHPFILE = "network_trn_route_links.shp"

TIMEPERIOD_DURATIONS = collections.OrderedDict([
    ("EA",3.0),
    ("AM",4.0),
    ("MD",5.0),
    ("PM",4.0),
    ("EV",8.0)
])

TRN_OPERATORS = collections.OrderedDict([
    # filename_append       # list of operator text
    ("_SF_Muni",             ["San Francisco MUNI"]),
    ("_SC_VTA",              ["Santa Clara VTA"]),
    ("_AC_Transit",          ["AC Transit", "AC Transbay"]),
    ("_SM_SamTrans",         ["samTrans"]),
    ("_SC_Transit",          ["Sonoma County Transit"]),
    ("_CC_CountyConnection", ["The County Connection"]),
    ("_GG_Transit",          ["Golden Gate Transit", "Golden Gate Ferry"]),
    ("_WestCAT",             ["WestCAT"]),
    ("_WHEELS",              ["WHEELS"]),
    ("_Stanford",            ["Stanford Marguerite Shuttle"]),
    ("_TriDelta",            ["TriDelta Transit"]),
    ("_Caltrain",            ["Caltrain"]),
    ("_BART",                ["BART"]),
    ("_ferry",               ["Alameda Harbor Bay Ferry", "Alameda/Oakland Ferry","Angel Island - Tiburon Ferry",
                              "Oakland/South SSF Ferry", "South SF/Oakland Ferry", "Vallejo Baylink Ferry"]),
    ("_other" ,              []),  # this will get filled in with operators not covered already
])

MODE_NUM_TO_NAME = {
    # number: name (https://github.com/BayAreaMetro/modeling-website/wiki/TransitModes)
    # Support
    1  :"Walk access connector",
    2  :"Drive access connector",
    3  :"Stop-to-stop or stop-to-station transfer link",
    4  :"Drive access funnel link",
    5  :"Walk access funnel link",
    6  :"Walk egress connector",
    7  :"Drive egress connector",
    # Local Bus
    10 :"West Berkeley",    
    11 :"Broadway Shuttle",
    12 :"Emery Go Round",
    13 :"Stanford Shuttles",
    14 :"Caltrain Shuttles",
    15 :"VTA Shuttles",
    16 :"Palo Alto/Menlo Park Shuttles",
    17 :"Wheels ACE Shuttles",
    18 :"Amtrak Shuttles",
    19 :"San Leandro Links",
    20 :"MUNI Cable Cars",
    21 :"MUNI Local",
    24 :"SamTrans Local",
    27 :"Santa Clara VTA Community bus",
    28 :"Santa Clara VTA Local",
    30 :"AC Transit Local",
    33 :"WHEELS Local",
    38 :"Union City Transit ",
    40 :"AirBART",
    42 :"County Connection (CCTA) Local",
    44 :"Tri-Delta",
    46 :"WestCAT Local",
    49 :"Vallejo Transit Local",
    52 :"Fairfield And Suisun Transit Local",
    55 :"American Canyon Transit",
    56 :"Vacaville City Coach",
    58 :"Benicia Breeze",
    60 :"VINE Local",
    63 :"Sonoma County Transit Local",
    66 :"Santa Rosa City Bus",
    68 :"Petaluma Transit",
    70 :"Golden Gate Transit Local",
    # Express Bus
    80 :"SamTrans Express",
    81 :"Santa Clara VTA Express",
    82 :"Dumbarton Express",
    83 :"AC Transit Transbay",
    84 :"AC Transit Transbay",
    86 :"County Connection Express",
    87 :"Golden Gate Transit Express San Francisco",
    88 :"Golden Gate Transit Express Richmond",
    90 :"WestCAT Express",
    91 :"Vallejo Transit Express",
    92 :"Fairfield And Suisun Transit Express",
    93 :"VINE Express",
    94 :"SMART Temporary Express",
    95 :"VINE Express",
    # Ferry
    100:"East Bay Ferries",
    101:"Golden Gate Ferry - Larkspur",
    102:"Golden Gate Ferry - Sausalito",
    103:"Tiburon Ferry",
    104:"Vallejo Baylink Ferry",
    105:"South City Ferry",
    # Light Rail
    110:"MUNI Metro",
    111:"Santa Clara VTA LRT",
    # Heavy Rail
    120:"BART",
    121:"Oakland Airport Connector",
    # Commuter Rail
    130:"Caltrain",
    131:"Amtrak - Capitol Corridor",
    132:"Amtrak - San Joaquin",
    133:"ACE",
    134:"Dumbarton Rail",
    135:"SMART",
    136:"E-BART",
    137:"High-Speed Rail"
}

def runCubeScript(workingdir, script_filename, script_env):
    """
    Run the cube script specified in the workingdir specified.
    Returns the return code.
    """
    # run it
    proc = subprocess.Popen('"{0}" "{1}"'.format(os.path.join(RUNTPP_PATH,"runtpp"), script_filename), 
                            cwd=workingdir, env=script_env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for line in proc.stdout:
        line_str = line.decode("utf-8")
        line_str = line_str.strip('\r\n')
        logging.info("  stdout: {0}".format(line_str))
    for line in proc.stderr:
        line_str = line.decode("utf-8")
        line_str = line_str.strip('\r\n')
        logging.info("  stderr: {0}".format(line_str))
    retcode = proc.wait()
    if retcode == 2:
        raise Exception("Failed to run Cube script %s" % (script_filename))
    logging.info("  Received {0} from 'runtpp {1}'".format(retcode, script_filename))

# from maz_taz_checker.py, I am sorry.  Library?!
def rename_fields(input_feature, output_feature, old_to_new):
    """
    Renames specified fields in input feature class/table
    old_to_new: {old_field: [new_field, new_alias]}
    """
    field_mappings = arcpy.FieldMappings()
    field_mappings.addTable(input_feature)

    for (old_field_name, new_list) in old_to_new.items():
        mapping_index          = field_mappings.findFieldMapIndex(old_field_name)
        if mapping_index < 0:
            message = "Field: {0} not in {1}".format(old_field_name, input_feature)
            raise Exception(message)

        field_map              = field_mappings.fieldMappings[mapping_index]
        output_field           = field_map.outputField
        output_field.name      = new_list[0]
        output_field.aliasName = new_list[1]
        field_map.outputField  = output_field
        field_mappings.replaceFieldMap(mapping_index, field_map)

    # use merge with single input just to use new field_mappings
    arcpy.Merge_management(input_feature, output_feature, field_mappings)
    return output_feature

if __name__ == '__main__':
    pandas.options.display.width = 500
    pandas.options.display.max_rows = 1000

    # assume code dir is where this script is
    CODE_DIR    = os.path.dirname(os.path.realpath(__file__))
    WORKING_DIR = os.getcwd()

    # create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(ch)
    # file handler
    fh = logging.FileHandler(LOG_FILE, mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(fh)

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument("netfile",  metavar="network.net", help="Cube input roadway network file")
    parser.add_argument("--linefile", metavar="transit.lin", help="Cube input transit line file", required=False)
    parser.add_argument("--by_operator", action="store_true", help="Split transit lines by operator")
    parser.add_argument("--join_link_nntime", action="store_true", help="Join links based on NNTIME")
    parser.add_argument("--trn_stop_info", metavar="transit_stops.csv", help="CSV with extra transit stop information")
    args = parser.parse_args()
    # print(args)

    # setup the environment
    script_env                 = os.environ.copy()
    script_env["PATH"]         = "{0};{1}".format(script_env["PATH"],RUNTPP_PATH)
    script_env["NET_INFILE"]   = args.netfile
    script_env["NODE_OUTFILE"] = NODE_SHPFILE
    script_env["LINK_OUTFILE"] = LINK_SHPFILE

    # if these exist, check the modification stamp of them and of the source file to give user the option to opt-out of re-exporting
    do_export = True
    if os.path.exists(NODE_SHPFILE) and os.path.exists(LINK_SHPFILE):
        net_mtime  = os.path.getmtime(args.netfile)
        node_mtime = os.path.getmtime(NODE_SHPFILE)
        link_mtime = os.path.getmtime(LINK_SHPFILE)
        if (net_mtime < node_mtime) and (net_mtime < link_mtime):
            # give a chance to opt-out since it's slowwwwww
            print("{} and {} exist with modification times after source network modification time.  Re-export? (y/n)".format(NODE_SHPFILE, LINK_SHPFILE))
            response = input("")
            if response in ["n","N"]:
                do_export = False

    # run the script to do the work
    if do_export:
        runCubeScript(WORKING_DIR, os.path.join(CODE_DIR, "export_network.job"), script_env)
        logging.info("Wrote network node file to {}".format(NODE_SHPFILE))
        logging.info("Wrote network link file to {}".format(LINK_SHPFILE))
    else:
        logging.info("Opted out of re-exporting roadway network file.  Using existing {} and {}".format(NODE_SHPFILE, LINK_SHPFILE))

    # MakeXYEventLayer_management
    import arcpy
    arcpy.env.workspace = WORKING_DIR

    # define the spatial reference
    # http://spatialreference.org/ref/epsg/nad83-utm-zone-10n/
    sr = arcpy.SpatialReference(26910)
    arcpy.DefineProjection_management(NODE_SHPFILE, sr)
    arcpy.DefineProjection_management(LINK_SHPFILE, sr)

    # if we don't have a transit file, then we're done
    if not args.linefile: sys.exit(0)

    import Wrangler

    operator_files = [""]
    if args.by_operator:
        operator_files = list(TRN_OPERATORS.keys())

    # store cursors here
    line_cursor      = {}
    link_cursor      = {}
    stop_cursor      = {}
    operator_to_file = {}

    # store link information here -- we'll aggregate this a bit and output later
    link_rows = []
    link_rows_cols   = [
        "A", "A_X", "A_Y", "A_STATION",
        "B", "B_X", "B_Y", "B_STATION",
        "NAME"    ,        "NAME_SET"  ,
        "MODE"    ,        "MODE_NAME" ,  "MODE_TYPE",
        "OPERATOR",        "OPERATOR_T",
        "SEATCAP" ,        "CRUSHCAP"  ,
        # assume these are additive
        "TRIPS_EA", "TRIPS_AM", "TRIPS_MD", "TRIPS_PM", "TRIPS_EV"
    ]

    for operator_file in operator_files:
        if args.by_operator:
            for op_txt in TRN_OPERATORS[operator_file]:
                operator_to_file[op_txt] = operator_file

        # delete shapefiles if one exists already
        arcpy.Delete_management(TRN_LINES_SHPFILE.format(operator_file))
        arcpy.Delete_management(TRN_LINKS_SHPFILE.format(operator_file))
        arcpy.Delete_management(TRN_STOPS_SHPFILE.format(operator_file))

        # create the lines shapefile
        arcpy.CreateFeatureclass_management(WORKING_DIR, TRN_LINES_SHPFILE.format(operator_file), "POLYLINE")
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "NAME",       "TEXT", field_length=25)
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "NAME_SET",   "TEXT", field_length=25)
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "FREQ_EA",    "FLOAT")
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "FREQ_AM",    "FLOAT")
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "FREQ_MD",    "FLOAT")
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "FREQ_PM",    "FLOAT")
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "FREQ_EV",     "FLOAT")
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "MODE",       "SHORT")
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "MODE_NAME",  "TEXT", field_length=40)
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "MODE_TYPE",  "TEXT", field_length=15)
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "OPERATOR_T", "TEXT", field_length=40)
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "VEHICLETYP", "SHORT")
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "VTYPE_NAME", "TEXT", field_length=40)
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "SEATCAP",    "SHORT")
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "CRUSHCAP",   "SHORT")
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "OPERATOR",   "SHORT")
        # helpful additional fields
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "FIRST_N",    "LONG")
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "FIRST_NAME", "TEXT", field_length=40)
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "LAST_N",     "LONG")
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "LAST_NAME",  "TEXT", field_length=40)
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "N_OR_S",     "TEXT", field_length=3)
        arcpy.AddField_management(TRN_LINES_SHPFILE.format(operator_file), "E_OR_W",     "TEXT", field_length=3)
        arcpy.DefineProjection_management(TRN_LINES_SHPFILE.format(operator_file), sr)

        line_cursor[operator_file] = arcpy.da.InsertCursor(TRN_LINES_SHPFILE.format(operator_file), ["NAME", "NAME_SET", "SHAPE@",
                                   "FREQ_EA", "FREQ_AM", "FREQ_MD", "FREQ_PM", "FREQ_EV",
                                   "MODE", "MODE_NAME", "MODE_TYPE", "OPERATOR_T", "VEHICLETYP", "VTYPE_NAME", "SEATCAP", "CRUSHCAP",
                                   "OPERATOR",
                                   "FIRST_N", "FIRST_NAME", "LAST_N", "LAST_NAME", "N_OR_S", "E_OR_W"])

        # create the links shapefile
        arcpy.CreateFeatureclass_management(WORKING_DIR, TRN_LINKS_SHPFILE.format(operator_file), "POLYLINE")
        arcpy.AddField_management(TRN_LINKS_SHPFILE.format(operator_file), "NAME",     "TEXT", field_length=25)
        arcpy.AddField_management(TRN_LINKS_SHPFILE.format(operator_file), "A",        "LONG")
        arcpy.AddField_management(TRN_LINKS_SHPFILE.format(operator_file), "B",        "LONG")
        arcpy.AddField_management(TRN_LINKS_SHPFILE.format(operator_file), "A_STATION","TEXT", field_length=40)
        arcpy.AddField_management(TRN_LINKS_SHPFILE.format(operator_file), "B_STATION","TEXT", field_length=40)
        arcpy.AddField_management(TRN_LINKS_SHPFILE.format(operator_file), "SEQ",     "SHORT")
        arcpy.AddField_management(TRN_LINKS_SHPFILE.format(operator_file), "NNTIME",  "FLOAT", field_precision=7, field_scale=2)
        arcpy.DefineProjection_management(TRN_LINKS_SHPFILE.format(operator_file), sr)

        link_cursor[operator_file] = arcpy.da.InsertCursor(TRN_LINKS_SHPFILE.format(operator_file),
                                                           ["NAME", "SHAPE@", "A", "B", "A_STATION","B_STATION", "SEQ", "NNTIME"])

        # create the stops shapefile
        arcpy.CreateFeatureclass_management(WORKING_DIR, TRN_STOPS_SHPFILE.format(operator_file), "POINT")
        arcpy.AddField_management(TRN_STOPS_SHPFILE.format(operator_file), "NAME",     "TEXT", field_length=25)
        arcpy.AddField_management(TRN_STOPS_SHPFILE.format(operator_file), "STATION",  "TEXT", field_length=40)
        arcpy.AddField_management(TRN_STOPS_SHPFILE.format(operator_file), "N",        "LONG")
        arcpy.AddField_management(TRN_STOPS_SHPFILE.format(operator_file), "SEQ",      "SHORT")
        arcpy.AddField_management(TRN_STOPS_SHPFILE.format(operator_file), "IS_STOP",  "SHORT")
        # from node attributes http://bayareametro.github.io/travel-model-two/input/#node-attributes
        # PNR attributes are for TAPs so not included here
        arcpy.DefineProjection_management(TRN_STOPS_SHPFILE.format(operator_file), sr)

        stop_cursor[operator_file] = arcpy.da.InsertCursor(TRN_STOPS_SHPFILE.format(operator_file),
                                                           ["NAME", "SHAPE@", "STATION", "N", "SEQ", "IS_STOP"])
    # print(operator_to_file)

    # read the node points
    nodes_array = arcpy.da.TableToNumPyArray(in_table="{}.DBF".format(NODE_SHPFILE[:-4]),
                                             field_names=["N","X","Y"])
    node_dicts = {}
    for node_field in ["X","Y"]:
        node_dicts[node_field] = dict(zip(nodes_array["N"].tolist(), nodes_array[node_field].tolist()))

    # read the stop information, if there is any
    stops_to_station = {}
    if args.trn_stop_info:
        stop_info_df = pandas.read_csv(args.trn_stop_info)
        logging.info("Read {} lines from {}".format(len(stop_info_df), args.trn_stop_info))
        # only want node numbers and names
        stop_info_dict = stop_info_df[["TM2 Node","Station"]].to_dict(orient='list')
        stops_to_station = dict(zip(stop_info_dict["TM2 Node"],
                                    stop_info_dict["Station"]))

    (trn_file_base, trn_file_name) = os.path.split(args.linefile)
    trn_net = Wrangler.TransitNetwork(modelType="TravelModelOne", modelVersion=1.5)
    trn_net.parseFile(fullfile=args.linefile)
    logging.info("Read trn_net: {}".format(trn_net))

    # build lines and links
    line_count = 0
    link_count = 0
    stop_count = 0
    total_line_count = len(trn_net.line(re.compile(".")))

    line_group_pattern = re.compile(r"([A-Z0-9]+_[A-Z0-9]+)")

    for line in trn_net:
        # print(line)
        # figure out the name set
        match_obj = re.match(line_group_pattern, line.name)
        name_set  = match_obj.group(1) if match_obj else "No match"

        line_point_array = arcpy.Array()
        link_point_array = arcpy.Array()
        last_n           = -1
        last_station     = ""
        seq              = 1
        op_txt           = "op_txt_none" # line.attr['USERA1'].strip('\""')

        vtype_num  = 0 # int(line.attr['VEHICLETYPE'])
        vtype_name = ""
        seatcap    = 0
        crushcap   = 0
        if vtype_num in trn_net.ptsystem.vehicleTypes:
            vtype_dict = trn_net.ptsystem.vehicleTypes[vtype_num]
            if "NAME"     in vtype_dict: vtype_name = vtype_dict["NAME"].strip('"')
            if "SEATCAP"  in vtype_dict: seatcap    = int(vtype_dict["SEATCAP"])
            if "CRUSHCAP" in vtype_dict: crushcap   = int(vtype_dict["CRUSHCAP"])

        if not args.by_operator:
            operator_file = ""
        elif op_txt in operator_to_file:
            operator_file = operator_to_file[op_txt]
        else:
            operator_file = "_other"
            operator_to_file[op_txt] = operator_file
            if op_txt not in TRN_OPERATORS[operator_file]:
                TRN_OPERATORS[operator_file].append(op_txt)

        logging.info("Adding line {:4}/{:4} {:25} operator {:40} to operator_file [{}]".format(
              line_count+1,total_line_count,
              line.name, op_txt, operator_file))
        # for attr_key in line.attr: print(attr_key, line.attr[attr_key])

        # keep information about first and last nodes
        first_n     = -1
        first_name  = None
        first_point = None
        last_n      = -1
        last_name   = None
        last_point  = None
        for node in line.n:
            n = abs(int(node.num))
            station = stops_to_station[n] if n in stops_to_station else ""
            is_stop = 1 if node.isStop() else 0
            nntime = -999
            if "NNTIME" in node.attr: nntime = float(node.attr["NNTIME"])
            mode_name = "unknown_mode"
            if int(line.attr['MODE']) in MODE_NUM_TO_NAME:
                mode_name = MODE_NUM_TO_NAME[int(line.attr['MODE'])]

            mode_type = "Commuter Rail"
            if int(line.attr['MODE']) < 10:
                mode_type = "Support"
            elif int(line.attr['MODE']) < 80:
                mode_type = "Local Bus"
            elif int(line.attr['MODE']) < 100:
                mode_type = "Express Bus"
            elif int(line.attr['MODE']) < 110:
                mode_type = "Ferry"
            elif int(line.attr['MODE']) < 120:
                mode_type = "Light Rail"
            elif int(line.attr['MODE']) < 130:
                mode_type = "Heavy Rail"

            if first_n < 0:
                first_n    = n
                first_name = station
                first_point = (node_dicts["X"][n], node_dicts["Y"][n])

            # From NNTIME documentation:
            # NODES=1,2,3,4, NNTIME=10, NODES=5,6,7, NNTIME=15
            # Sets the time from node 1 to node 4 to ten minutes,
            # and sets the time from node 4 to node 7 to fifteen minutes.

            # print(node.num, n, node.attr, node.stop)
            point = arcpy.Point( node_dicts["X"][n], node_dicts["Y"][n] )

            # start at 0 for stops
            stop_cursor[operator_file].insertRow([line.name, point, station, n, seq-0, is_stop])
            stop_count += 1

            # add to line array
            line_point_array.add(point)

            # and link array
            link_point_array.add(point)

            # if join_link_nntime, add polyline only when NNTIME is set
            if ((args.join_link_nntime == False) and (link_point_array.count > 1)) or \
               ((args.join_link_nntime == True ) and (nntime > 0)):
                plink_shape = arcpy.Polyline(link_point_array)
                link_cursor[operator_file].insertRow([line.name, plink_shape,
                                                      last_n, n, last_station, station, seq, nntime])
                # save the link data for aggregation
                link_rows.append( [last_n, last_point[0],      last_point[1],      last_name,
                                   n,      node_dicts["X"][n], node_dicts["Y"][n], station,
                                   line.name, name_set,
                                   line.attr['MODE'], mode_name, mode_type,
                                   0, op_txt, # line.attr['OPERATOR'], op_txt,
                                   seatcap, crushcap,
                                   TIMEPERIOD_DURATIONS["EA"]*60.0/float(line.attr['FREQ[1]']) if float(line.attr['FREQ[1]'])>0 else 0,
                                   TIMEPERIOD_DURATIONS["AM"]*60.0/float(line.attr['FREQ[2]']) if float(line.attr['FREQ[2]'])>0 else 0,
                                   TIMEPERIOD_DURATIONS["MD"]*60.0/float(line.attr['FREQ[3]']) if float(line.attr['FREQ[3]'])>0 else 0,
                                   TIMEPERIOD_DURATIONS["PM"]*60.0/float(line.attr['FREQ[4]']) if float(line.attr['FREQ[4]'])>0 else 0,
                                   TIMEPERIOD_DURATIONS["EV"]*60.0/float(line.attr['FREQ[5]']) if float(line.attr['FREQ[5]'])>0 else 0
                                ])
                link_count += 1
                link_point_array.removeAll()
                link_point_array.add(point)

            last_n     = n
            last_name  = station
            last_point = (node_dicts["X"][n], node_dicts["Y"][n])
            seq += 1

        # one last link if necessary
        if link_point_array.count > 1:
            plink_shape = arcpy.Polyline(link_point_array)
            link_cursor[operator_file].insertRow([line.name, plink_shape,
                                                  last_n, n, last_station, station, seq, nntime])


            link_count += 1
            link_point_array.removeAll()


        pline_shape = arcpy.Polyline(line_point_array)

        line_cursor[operator_file].insertRow([line.name, name_set, pline_shape,
                                              float(line.attr['FREQ[1]']),
                                              float(line.attr['FREQ[2]']),
                                              float(line.attr['FREQ[3]']),
                                              float(line.attr['FREQ[4]']),
                                              float(line.attr['FREQ[5]']),
                                              line.attr['MODE'], mode_name, mode_type,
                                              op_txt, # operator
                                              0, # line.attr['VEHICLETYPE'],
                                              vtype_name, seatcap, crushcap,
                                              0, # line.attr['OPERATOR'],
                                              first_n, first_name,
                                              last_n,  last_name,
                                              "N" if last_point[1] > first_point[1] else "S",
                                              "E" if last_point[0] > first_point[0] else "W"
                                            ])
        line_count += 1

    del stop_cursor
    logging.info("Wrote {} stops to {}".format(stop_count, TRN_STOPS_SHPFILE))

    del line_cursor
    logging.info("Wrote {} lines to {}".format(line_count, TRN_LINES_SHPFILE))

    del link_cursor
    logging.info("Wrote {} links to {}".format(link_count, TRN_LINKS_SHPFILE))

    # aggregate link level data
    links_df = pandas.DataFrame(columns=link_rows_cols, data=link_rows)
    links_df["LINE_COUNT"] = 1
    logging.debug("\n{}".format(links_df.head(20)))

    # SEATCAP and CRUSHCAP are passengers per trip -- multiply by trip to get passengers pr time period
    links_df["SEATCAP_EA"] = links_df["SEATCAP"]*links_df["TRIPS_EA"]
    links_df["SEATCAP_AM"] = links_df["SEATCAP"]*links_df["TRIPS_AM"]
    links_df["SEATCAP_MD"] = links_df["SEATCAP"]*links_df["TRIPS_MD"]
    links_df["SEATCAP_PM"] = links_df["SEATCAP"]*links_df["TRIPS_PM"]
    links_df["SEATCAP_EV"] = links_df["SEATCAP"]*links_df["TRIPS_EV"]

    links_df["CRSHCAP_EA"] = links_df["CRUSHCAP"]*links_df["TRIPS_EA"]
    links_df["CRSHCAP_AM"] = links_df["CRUSHCAP"]*links_df["TRIPS_AM"]
    links_df["CRSHCAP_MD"] = links_df["CRUSHCAP"]*links_df["TRIPS_MD"]
    links_df["CRSHCAP_PM"] = links_df["CRUSHCAP"]*links_df["TRIPS_PM"]
    links_df["CRSHCAP_EV"] = links_df["CRUSHCAP"]*links_df["TRIPS_EV"]

    # aggregate by A,B,MODE,MODE_NAME,OPERATOR,OPERATOR_T,NAME_SET
    links_df_GB = links_df.groupby(by=["A","B","A_STATION","B_STATION","NAME_SET","MODE","MODE_NAME","MODE_TYPE","OPERATOR","OPERATOR_T"])
    links_df    = links_df_GB.agg({"A_X":"first", "A_Y":"first", "B_X":"first", "B_Y":"first", "LINE_COUNT":"sum",
                                   "TRIPS_EA"  :"sum","TRIPS_AM"  :"sum","TRIPS_MD"  :"sum","TRIPS_PM"  :"sum","TRIPS_EV"  :"sum",
                                   "SEATCAP_EA":"sum","SEATCAP_AM":"sum","SEATCAP_MD":"sum","SEATCAP_PM":"sum","SEATCAP_EV":"sum",
                                   "CRSHCAP_EA":"sum","CRSHCAP_AM":"sum","CRSHCAP_MD":"sum","CRSHCAP_PM":"sum","CRSHCAP_EV":"sum"}).reset_index()
    links_df["ROUTE_A_B"] = links_df["NAME_SET"] + " " + links_df["A"].astype(str) + "_" + links_df["B"].astype(str)

    logging.debug("\n{}".format(links_df.head(20)))
    # create the link file by route
    arcpy.Delete_management(TRN_ROUTE_LINKS_SHPFILE)
    arcpy.CreateFeatureclass_management(WORKING_DIR, TRN_ROUTE_LINKS_SHPFILE, "POLYLINE")
    arcpy.AddField_management(TRN_ROUTE_LINKS_SHPFILE, "A",         "LONG")
    arcpy.AddField_management(TRN_ROUTE_LINKS_SHPFILE, "B",         "LONG")
    arcpy.AddField_management(TRN_ROUTE_LINKS_SHPFILE, "A_STATION", "TEXT", field_length=40)
    arcpy.AddField_management(TRN_ROUTE_LINKS_SHPFILE, "B_STATION", "TEXT", field_length=40)
    arcpy.AddField_management(TRN_ROUTE_LINKS_SHPFILE, "NAME_SET",  "TEXT", field_length=25)
    arcpy.AddField_management(TRN_ROUTE_LINKS_SHPFILE, "MODE",      "SHORT")
    arcpy.AddField_management(TRN_ROUTE_LINKS_SHPFILE, "MODE_NAME", "TEXT", field_length=40)
    arcpy.AddField_management(TRN_ROUTE_LINKS_SHPFILE, "MODE_TYPE", "TEXT", field_length=15)
    arcpy.AddField_management(TRN_ROUTE_LINKS_SHPFILE, "OPERATOR",  "SHORT")
    arcpy.AddField_management(TRN_ROUTE_LINKS_SHPFILE, "OPERATOR_T","TEXT", field_length=40)
    arcpy.AddField_management(TRN_ROUTE_LINKS_SHPFILE, "LINE_COUNT","SHORT")
    arcpy.AddField_management(TRN_ROUTE_LINKS_SHPFILE, "ROUTE_A_B", "TEXT", field_length=40)

    for timeperiod in TIMEPERIOD_DURATIONS.keys():
        arcpy.AddField_management(TRN_ROUTE_LINKS_SHPFILE, "TRIPS_{}".format(timeperiod),    "FLOAT", field_precision=7, field_scale=2)
        arcpy.AddField_management(TRN_ROUTE_LINKS_SHPFILE, "SEATCAP_{}".format(timeperiod),  "FLOAT", field_precision=9, field_scale=2)
        arcpy.AddField_management(TRN_ROUTE_LINKS_SHPFILE, "CRSHCAP_{}".format(timeperiod),  "FLOAT", field_precision=9, field_scale=2)

    arcpy.DefineProjection_management(TRN_ROUTE_LINKS_SHPFILE, sr)

    # update link_rows_cols
    for remove_col in ["A_X","A_Y","B_X","B_Y","NAME","SEATCAP","CRUSHCAP"]:
        link_rows_cols.remove(remove_col)
    link_rows_cols = ["SHAPE@"] + link_rows_cols + ["LINE_COUNT", "ROUTE_A_B"] + \
        ["SEATCAP_{}".format(tp) for tp in TIMEPERIOD_DURATIONS.keys()] + \
        ["CRSHCAP_{}".format(tp) for tp in TIMEPERIOD_DURATIONS.keys()]
    # create cursor
    link_cursor = arcpy.da.InsertCursor(TRN_ROUTE_LINKS_SHPFILE, link_rows_cols)
    ab_array    = arcpy.Array()

    # fill it in
    links_df_records = links_df.to_dict(orient="records")
    for record in links_df_records:
        cursor_rec = []
        for col in link_rows_cols:
            if col=="SHAPE@":
                ab_array.add( arcpy.Point( record["A_X"], record["A_Y"]) )
                ab_array.add( arcpy.Point( record["B_X"], record["B_Y"]))
                ab_line   = arcpy.Polyline(ab_array)
                cursor_rec.append(ab_line)
                ab_array.removeAll()
            else:
                cursor_rec.append (record[col])
        link_cursor.insertRow(cursor_rec)

    del link_cursor
    logging.info("Wrote {} links to {}".format(len(links_df), TRN_ROUTE_LINKS_SHPFILE))
