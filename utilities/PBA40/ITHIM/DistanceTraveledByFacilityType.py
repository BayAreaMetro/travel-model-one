USAGE = """

  Calculates auto and truck personal and vehicle distances traveled by facility type.

  * Reads hwy\iter%ITER%\avgload5period_vehclasses.csv

"""
import os, sys
import numpy, pandas

if __name__ == '__main__':
    pandas.set_option('display.width', 500)
    iteration       = int(os.environ['ITER'])
    TIMEPERIODS     = ['EA','AM','MD','PM','EV']
    VEHCLASSES      = ['da','s2','s3','sm','hv']

    # read the network with volumes
    loaded_net_df = pandas.read_table(os.path.join("hwy", "iter%d" % iteration, "avgload5period_vehclasses.csv"), sep=",")

    # we only need a subset of columns
    cols_to_keep = ['a','b','distance','ft']
    for timeperiod in TIMEPERIODS:
        for vehclass in VEHCLASSES:
            cols_to_keep.append("vol%s_%s"  % (timeperiod, vehclass))
            cols_to_keep.append("vol%s_%st" % (timeperiod, vehclass)) # toll
    loaded_net_df = loaded_net_df[cols_to_keep]

    # stack -- index=a,b,distance,ft, and then we have var -> value
    loaded_net_df = pandas.DataFrame(loaded_net_df.set_index(['a','b','distance','ft']).stack()).reset_index()
    loaded_net_df['timeperiod'] = loaded_net_df['level_4'].str[3:5]
    loaded_net_df['vehclass']   = loaded_net_df['level_4'].str.split('_',n=1).str.get(1)
    loaded_net_df.rename(columns={0:'volume'}, inplace=True)

    # remove the now extraneous 'level_4'
    loaded_net_df.drop('level_4', axis=1, inplace=True)

    # Vehicle miles traveled
    loaded_net_df['auto_VMT']   = 0
    loaded_net_df.loc[(loaded_net_df.vehclass=='da')|(loaded_net_df.vehclass=='dat'), 'auto_VMT'] = loaded_net_df['distance']*loaded_net_df['volume']
    loaded_net_df.loc[(loaded_net_df.vehclass=='s2')|(loaded_net_df.vehclass=='s2t'), 'auto_VMT'] = loaded_net_df['distance']*loaded_net_df['volume']
    loaded_net_df.loc[(loaded_net_df.vehclass=='s3')|(loaded_net_df.vehclass=='s2t'), 'auto_VMT'] = loaded_net_df['distance']*loaded_net_df['volume']
    loaded_net_df['sm_med_truck_VMT'] = 0
    loaded_net_df.loc[(loaded_net_df.vehclass=='sm')|(loaded_net_df.vehclass=='smt'), 'sm_med_truck_VMT'] = loaded_net_df['distance']*loaded_net_df['volume']
    loaded_net_df['heavy_truck_VMT'] = 0
    loaded_net_df.loc[(loaded_net_df.vehclass=='hv')|(loaded_net_df.vehclass=='hvt'), 'heavy_truck_VMT']  = loaded_net_df['distance']*loaded_net_df['volume']

    # each vehicle mile traveled has a driver
    loaded_net_df['car_driver_PMT']    = loaded_net_df['auto_VMT']
    loaded_net_df['truck_driver_PMT']  = loaded_net_df['sm_med_truck_VMT'] + loaded_net_df['heavy_truck_VMT']
    # but s2 and s3 miles traveled have passengers
    loaded_net_df['car_passenger_PMT'] = 0.0
    loaded_net_df.loc[(loaded_net_df.vehclass=='s2')|(loaded_net_df.vehclass=='s2t'), 'car_passenger_PMT'] = loaded_net_df['auto_VMT']*1.0
    loaded_net_df.loc[(loaded_net_df.vehclass=='s3')|(loaded_net_df.vehclass=='s3t'), 'car_passenger_PMT'] = loaded_net_df['auto_VMT']*2.5

    print loaded_net_df.loc[(loaded_net_df.volume>0)&(loaded_net_df.ft!=6),:].head(30)
    print loaded_net_df.columns

    # groupby facility type
    loaded_ft_df = loaded_net_df[['ft','distance',
                                  'auto_VMT','sm_med_truck_VMT','heavy_truck_VMT',
                                  'car_driver_PMT','car_passenger_PMT','truck_driver_PMT']].groupby(['ft']).agg(numpy.sum)
    loaded_ft_df.to_csv(os.path.join("metrics","ITHIM","DistanceTraveledByFacilityType_auto+truck.csv"))
    # sum volumes -- these are vehicle volumes
    # sum person volumes
