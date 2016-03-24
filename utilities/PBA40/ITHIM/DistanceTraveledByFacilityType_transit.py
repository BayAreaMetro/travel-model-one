USAGE = """

  Calculates transit vehicle distances traveled by facility type and
    transit passenger miles traveled by facility type (for buses, this includes
    roadway facility types)

  * Reads hwy\iter%ITER%\avgload5period_vehclasses.csv for facility types
  * Reads trn\trnlink(EA|AM|MD|PM|EV)_(wlk|drv)_(com|hvy|exp|lrf|loc)_(wlk_drv).dbf
  * Summarizes vehicle miles traveled, passenger miles traveled, and passenger hours traveled
    by bus+ITHIM facility type and rail
  * Writes summary to metrics\ITHIM\DistanceTraveledByFacilityType_transit.csv

"""
import os, sys
import numpy, pandas

def read_dbf(dbf_fullpath):
    """
    Returns the pandas DataFrame
    """
    import pysal
    dbfin = pysal.open(dbf_fullpath)
    vars = dbfin.header
    data = dict([(var, dbfin.by_col(var)) for var in vars])

    table_df = pandas.DataFrame(data)

    print "  Read %d lines from %s" % (len(table_df), dbf_fullpath)

    return table_df

if __name__ == '__main__':
    pandas.set_option('display.width', 500)
    iteration            = int(os.environ['ITER'])
    TIMEPERIODS          = ['ea','am','md','pm','ev']
    SUBMODES             = ['com','hvy','exp','lrf','loc']
    TIMEPERIOD_DURATIONS = {'ea':3, 'am':4, 'md':5, 'pm':4, 'ev':8}

    # read the road network for facility types
    roadway_file  = os.path.join("hwy", "iter%d" % iteration, "avgload5period_vehclasses.csv")
    loaded_net_df = pandas.read_table(roadway_file, sep=",")
    loaded_net_df = loaded_net_df[['a','b','distance','ft']] # we only need a subset of columns
    print "  Read %s lines from %s" % (len(loaded_net_df), roadway_file)

    # filter out FT=10 since those are toll plazas and not real links
    loaded_net_df = loaded_net_df.loc[loaded_net_df.ft != 10,]

    # transform FT to ITHIM FT
    # From M:\Application\ITHIM\2014.06.24_ITHIM_IntegrationManual_MTC.pdf
    ft_mapping = {
        1: "freeway",   # Freeway-to-freeway connector
        2: "freeway",   # Freeway
        3: "freeway",   # Expressway
        4: "arterial",  # Collector
        5: "freeway",   # Freeway ramp
        6: "local",     # Dummy link
        7: "arterial",  # Major arterial
        8: "freeway",   # Managed freeway
        9: "unknown"    # Special facility
    }
    # the ITHIM facility type is a strata
    loaded_net_df["strata"] = loaded_net_df["ft"]
    loaded_net_df.replace({"strata":ft_mapping}, inplace=True)
    loaded_net_df.rename(columns={'a':'A', 'b':'B'}, inplace=True)
    loaded_net_df.drop("ft", axis=1, inplace=True)
    # print loaded_net_df.head()

    # Read the transit assignment files
    first = True
    trnlines_df = None
    for timeperiod in TIMEPERIODS:
        for access in ['wlk','drv']:
            for submode in SUBMODES:
                for egress in ['wlk','drv']:

                    if access == 'drv' and egress == 'drv': continue
                    filename = os.path.join("trn","trnlink%s_%s_%s_%s.dbf" % (timeperiod, access, submode, egress))
                    trnline_df = read_dbf(filename)
                    trnline_df['access'            ] = access
                    trnline_df['egress'            ] = egress
                    trnline_df['submode'           ] = submode
                    trnline_df['TimePeriod'        ] = timeperiod
                    trnline_df['TimePeriodDuration'] = TIMEPERIOD_DURATIONS[timeperiod]
                    if first:
                        trnlines_df = trnline_df
                        first = False
                    else:
                        trnlines_df = pandas.concat([trnlines_df, trnline_df], axis=0)

    # we only need some columns
    trnlines_df = trnlines_df[['A','B','AB_VOL','DIST','FREQ','MODE','NAME','SEQ','TIME',
                               'access','egress','submode','TimePeriod','TimePeriodDuration']]

    # Recode Line-haul modes to ITHIM modes
    # Line-haul modes http://analytics.mtc.ca.gov/foswiki/Main/TransitNetworkCoding
    trnlines_df['mode'] = 'Non-Transit'
    trnlines_df.loc[(trnlines_df.MODE >= 10)&(trnlines_df.MODE < 80), 'mode'] = 'bus'    # Local bus
    trnlines_df.loc[(trnlines_df.MODE >= 80)&(trnlines_df.MODE <100), 'mode'] = 'bus'    # Express bus
    trnlines_df.loc[(trnlines_df.MODE >=100)&(trnlines_df.MODE <110), 'mode'] = 'rail'   # Ferry
    trnlines_df.loc[(trnlines_df.MODE >=110)&(trnlines_df.MODE <120), 'mode'] = 'rail'   # Light rail
    trnlines_df.loc[(trnlines_df.MODE >=120)&(trnlines_df.MODE <130), 'mode'] = 'rail'   # Heavy rail
    trnlines_df.loc[(trnlines_df.MODE >=130)&(trnlines_df.MODE <140), 'mode'] = 'rail'   # Commuter rail

    # Lose the Non-transit modes (access, egres, transfers)
    trnlines_df = trnlines_df.loc[trnlines_df['mode'] != 'Non-Transit']

    # print trnlines_df.head()
    # print trnlines_df['mode'].value_counts()

    # aggregate across access/egress/submodes
    trnlines_df['count'] = 1 # to check we're aggregating correctly
    trnlines_grouped_df = trnlines_df.groupby(['mode','MODE','NAME','SEQ','A','B',
                                              'TimePeriod','TimePeriodDuration','TIME','DIST','FREQ']).agg({'AB_VOL':numpy.sum,
                                                                                                            'count':numpy.sum}).reset_index()
    # print "Counts: "
    # print trnlines_grouped_df['count'].value_counts()

    # (minutes/timeperiod) x (1 run/freq mins) = runs/timeperiod
    trnlines_grouped_df['Vehicle Runs'            ] = 60.0 * trnlines_grouped_df['TimePeriodDuration'] / trnlines_grouped_df['FREQ']
    trnlines_grouped_df['Vehicle Miles Traveled'  ] = trnlines_grouped_df['Vehicle Runs'] * trnlines_grouped_df['DIST'] / 100.0

    # join bus to roadway for facility type
    trnlines_grouped_df = pandas.merge(left=trnlines_grouped_df, right=loaded_net_df, how='left', on=['A','B'])
    trnlines_grouped_df.loc[trnlines_grouped_df['mode']=='rail', 'strata'] = "" # throw out strata for rail
    # print trnlines_grouped_df.sort("AB_VOL", ascending=False).head()
    # print trnlines_grouped_df.strata.value_counts()

    bus_count = len(trnlines_grouped_df.loc[(trnlines_grouped_df['mode']=='bus'),])
    ft_found  = len(trnlines_grouped_df.loc[(trnlines_grouped_df['mode']=='bus')&(pandas.notnull(trnlines_grouped_df['strata'])),])
    print "Out of %d bus links, %d have a facilty type found (or %.2f%%)" % (bus_count, ft_found, 100.0*ft_found/bus_count)
    # assign those to local since they're probably under-represented
    trnlines_grouped_df.loc[(trnlines_grouped_df['mode']=='bus')&(pandas.isnull(trnlines_grouped_df['strata'])),'strata'] = "local"

    # summarize all the links!
    summary = trnlines_grouped_df.groupby(['mode','strata']).agg({'Vehicle Miles Traveled':numpy.sum}).reset_index()
    summary = summary[['mode','strata','Vehicle Miles Traveled']]

    # drop rail - turns out we don't need it
    summary = summary.loc[summary['mode']=='bus',]

    # unstack the modes
    summary = pandas.melt(summary, id_vars=['mode','strata'])
    summary.rename(columns={"variable":"item_name", "value":"item_value"}, inplace=True)

    # add units
    summary['units'] = 'miles'

    outfile = os.path.join("metrics","ITHIM","DistanceTraveledByFacilityType_transit.csv")
    summary.to_csv(outfile, index=False)
    print "Wrote %s" % outfile
