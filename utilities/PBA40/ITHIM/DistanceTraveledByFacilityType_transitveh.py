USAGE = """

  Calculates transit vehicle distances traveled by facility type.

  * Reads trn\trnline(EA|AM|MD|PM|EV)_(wlk|drv)_(com|hvy|exp|lrf|loc)_(wlk_drv).csv
  * Summarizes vehicle distances traveled by transit submode
  * Writes summary to metrics\ITHIM\DistanceTraveledByFacilityType_transitveh.csv

"""
import os, sys
import numpy, pandas

if __name__ == '__main__':
    pandas.set_option('display.width', 500)
    TIMEPERIODS          = ['ea','am','md','pm','ev']
    SUBMODES             = ['com','hvy','exp','lrf','loc']
    TIMEPERIOD_DURATIONS = {'ea':3, 'am':4, 'md':5, 'pm':4, 'ev':8}

    first = True
    trnlines_df = None

    for timeperiod in TIMEPERIODS:
        for access in ['wlk','drv']:
            for submode in SUBMODES:
                for egress in ['wlk','drv']:

                    if access == 'drv' and egress == 'drv': continue
                    filename = os.path.join("trn","trnline%s_%s_%s_%s.csv" % (timeperiod, access, submode, egress))
                    trnline_df = pandas.read_table(filename, sep=",", 
                                                   names=['Name', 'Mode', 'Owner', 'Frequency',
                                                          'LineTime', 'LineDistance', 'TotalBoardings',
                                                          'PassengerMiles', 'PassengerHours', 'ID'])
                    trnline_df['TimePeriod'        ] = timeperiod
                    trnline_df['TimePeriodDuration'] = TIMEPERIOD_DURATIONS[timeperiod]
                    if first:
                        trnlines_df = trnline_df
                        first = False
                    else:
                        trnlines_df = pandas.concat([trnlines_df, trnline_df],
                                                    axis=0)

    # (minutes/timeperiod) x (1 run/freq mins) = runs/timeperiod
    trnlines_df['VehicleRuns'       ] = 60.0 * trnlines_df['TimePeriodDuration'] / trnlines_df['Frequency']
    trnlines_df['VehicleMiles'      ] = trnlines_df['VehicleRuns'] * trnlines_df['LineDistance']
    # Code the transit vehicle mode http://analytics.mtc.ca.gov/foswiki/Main/TransitNetworkCoding
    trnlines_df['Mode Group'] = '?'
    trnlines_df.loc[(trnlines_df.Mode >= 10)&(trnlines_df.Mode < 80), 'Mode Group'] = 'Local bus'
    trnlines_df.loc[(trnlines_df.Mode >= 80)&(trnlines_df.Mode <100), 'Mode Group'] = 'Express bus'
    trnlines_df.loc[(trnlines_df.Mode >=100)&(trnlines_df.Mode <110), 'Mode Group'] = 'Ferry'
    trnlines_df.loc[(trnlines_df.Mode >=110)&(trnlines_df.Mode <120), 'Mode Group'] = 'Light rail'
    trnlines_df.loc[(trnlines_df.Mode >=120)&(trnlines_df.Mode <130), 'Mode Group'] = 'Heavy rail'
    trnlines_df.loc[(trnlines_df.Mode >=130)&(trnlines_df.Mode <140), 'Mode Group'] = 'Commuter rail'

    # group by line name and time period
    trnlines_grouped = trnlines_df.groupby(['Name','TimePeriod'])

    # aggregate across the IDs (e.g. am_*_*_* will have people on the 38 muni bus in the AM but it's one line)
    # Mode, Owner, Frequency, LineTime, LineDistance, TimePeriodDuration, VehicleRuns and VehicleMiles
    # are all the same for a given Name, Timperiod
    trnlines_df = trnlines_grouped.agg({'Mode'              :'first',
                                        'Mode Group'        :'first',
                                        'Owner'             :'first',
                                        'Frequency'         :'first',
                                        'LineTime'          :'first',
                                        'LineDistance'      :'first',
                                        'TimePeriodDuration':'first',
                                        'VehicleRuns'       :'first',
                                        'VehicleMiles'      :'first',
                                        'TotalBoardings'    :numpy.sum,
                                        'PassengerMiles'    :numpy.sum,
                                        'PassengerHours'    :numpy.sum
                                        })
    # print trnlines_df

    trnlines_bymode = trnlines_df.groupby(['Mode Group']).agg({'VehicleMiles'      :numpy.sum,
                                                               'TotalBoardings': numpy.sum,
                                                               'PassengerMiles'    :numpy.sum,
                                                               'PassengerHours'    :numpy.sum})
    # print trnlines_bymode
    outfile = os.path.join("metrics","ITHIM","DistanceTraveledByFacilityType_transitveh.csv")
    trnlines_bymode.to_csv(outfile)
    print "Wrote %s" % outfile