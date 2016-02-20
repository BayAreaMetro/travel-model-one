USAGE = """

  Calculates auto and truck personal and vehicle distances traveled by facility type.

  * Reads hwy\iter%ITER%\avgload5period_vehclasses.csv
  * Summarizes VMT by mode (auto_VMT, sm_med_truck_VMT, heavy_truck_VMT)
  * Summarizes PMT by mode (car_driver_PMT, car_passenger_PMT, truck_driver_PMT)
  * Summarizes PHT by mode (car_driver_PMT, car_passenger_PMT, truck_driver_PMT)
  * Outputs metrics\ITHIM\DistanceTraveledByFacilityType_auto+truck.csv

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
        cols_to_keep.append("ctim%s" % timeperiod)
        for vehclass in VEHCLASSES:
            cols_to_keep.append("vol%s_%s"  % (timeperiod, vehclass))
            cols_to_keep.append("vol%s_%st" % (timeperiod, vehclass)) # toll
    loaded_net_df = loaded_net_df[cols_to_keep]

    # filter out FT=10 since those are toll plazas and not real links
    loaded_net_df = loaded_net_df.loc[loaded_net_df.ft != 10,]

    # transform FT to ITHIM FT
    # From M:\Application\ITHIM\2014.06.24_ITHIM_IntegrationManual_MTC.pdf
    ft_mapping = {
        1: "Freeway",   # Freeway-to-freeway connector
        2: "Freeway",   # Freeway
        3: "Freeway",   # Expressway
        4: "Arterial",  # Collector
        5: "Freeway",   # Freeway ramp
        6: "Local",     # Dummy link
        7: "Arterial",  # Major arterial
        8: "Freeway",   # Managed freeway
        9: "unknown"    # Special facility
    }
    loaded_net_df["ITHIM_ft"] = loaded_net_df["ft"]
    loaded_net_df.replace({"ITHIM_ft":ft_mapping}, inplace=True)
    loaded_net_df.drop("ft", axis=1, inplace=True)

    # stack -- index=a,b,distance,ft, and then we have var -> value
    loaded_net_df = pandas.DataFrame(loaded_net_df.set_index(['a','b','distance','ITHIM_ft']).stack()).reset_index()
    vol_net_df    = loaded_net_df.loc[loaded_net_df.level_4.str[:3] == 'vol'].copy()
    tim_net_df    = loaded_net_df.loc[loaded_net_df.level_4.str[:4] == 'ctim'].copy()
    assert(len(vol_net_df) + len(tim_net_df) == len(loaded_net_df))  # we have everything

    # Link Times
    tim_net_df['timeperiod'] = tim_net_df['level_4'].str[-2:]
    tim_net_df.rename(columns={0:'time'}, inplace=True)
    tim_net_df.drop('level_4', axis=1, inplace=True)

    # Person and Vehicle Miles
    vol_net_df['timeperiod'] = vol_net_df['level_4'].str[3:5]
    vol_net_df['vehclass']   = vol_net_df['level_4'].str.split('_',n=1).str.get(1)
    vol_net_df.rename(columns={0:'volume'}, inplace=True)

    # remove the now extraneous 'level_4'
    vol_net_df.drop('level_4', axis=1, inplace=True)

    # Put the times/volumes together
    vol_net_df = pandas.merge(left=vol_net_df, right=tim_net_df, how='left')

    # Vehicle miles traveled
    vol_net_df['car_VMT']   = 0
    vol_net_df.loc[(vol_net_df.vehclass=='da')|(vol_net_df.vehclass=='dat'), 'car_VMT'] = vol_net_df['distance']*vol_net_df['volume']
    vol_net_df.loc[(vol_net_df.vehclass=='s2')|(vol_net_df.vehclass=='s2t'), 'car_VMT'] = vol_net_df['distance']*vol_net_df['volume']
    vol_net_df.loc[(vol_net_df.vehclass=='s3')|(vol_net_df.vehclass=='s2t'), 'car_VMT'] = vol_net_df['distance']*vol_net_df['volume']
    vol_net_df['truck_VMT'] = 0
    vol_net_df.loc[(vol_net_df.vehclass=='sm')|(vol_net_df.vehclass=='smt'), 'truck_VMT'] = vol_net_df['distance']*vol_net_df['volume']
    vol_net_df.loc[(vol_net_df.vehclass=='hv')|(vol_net_df.vehclass=='hvt'), 'truck_VMT']  = vol_net_df['distance']*vol_net_df['volume']

    # each vehicle mile traveled has a driver
    vol_net_df['car_driver_PMT']    = vol_net_df['car_VMT']
    vol_net_df['truck_driver_PMT']  = vol_net_df['truck_VMT'] 
    # but s2 and s3 miles traveled have passengers
    vol_net_df['car_passenger_PMT'] = 0.0
    vol_net_df.loc[(vol_net_df.vehclass=='s2')|(vol_net_df.vehclass=='s2t'), 'car_passenger_PMT'] = vol_net_df['car_VMT']*1.0
    vol_net_df.loc[(vol_net_df.vehclass=='s3')|(vol_net_df.vehclass=='s3t'), 'car_passenger_PMT'] = vol_net_df['car_VMT']*2.5

    # person hours traveled
    vol_net_df['car_driver_PHT']   = 0
    vol_net_df.loc[(vol_net_df.vehclass=='da')|(vol_net_df.vehclass=='dat'), 'car_driver_PHT'] = vol_net_df['time']*vol_net_df['volume']/60.0
    vol_net_df.loc[(vol_net_df.vehclass=='s2')|(vol_net_df.vehclass=='s2t'), 'car_driver_PHT'] = vol_net_df['time']*vol_net_df['volume']/60.0
    vol_net_df.loc[(vol_net_df.vehclass=='s3')|(vol_net_df.vehclass=='s2t'), 'car_driver_PHT'] = vol_net_df['time']*vol_net_df['volume']/60.0
    vol_net_df['truck_driver_PHT'] = 0
    vol_net_df.loc[(vol_net_df.vehclass=='sm')|(vol_net_df.vehclass=='smt'), 'truck_driver_PHT'] = vol_net_df['time']*vol_net_df['volume']/60.0
    vol_net_df.loc[(vol_net_df.vehclass=='hv')|(vol_net_df.vehclass=='hvt'), 'truck_driver_PHT'] = vol_net_df['time']*vol_net_df['volume']/60.0
    # but s2 and s3 miles traveled have passengers
    vol_net_df['car_passenger_PHT'] = 0.0
    vol_net_df.loc[(vol_net_df.vehclass=='s2')|(vol_net_df.vehclass=='s2t'), 'car_passenger_PHT'] = vol_net_df['car_driver_PHT']*1.0
    vol_net_df.loc[(vol_net_df.vehclass=='s3')|(vol_net_df.vehclass=='s3t'), 'car_passenger_PHT'] = vol_net_df['car_driver_PHT']*2.5


    # groupby facility type
    loaded_ft_df = vol_net_df[['ITHIM_ft',
                               'car_VMT','truck_VMT',
                               'car_driver_PMT','car_passenger_PMT','truck_driver_PMT',
                               'car_driver_PHT','car_passenger_PHT','truck_driver_PHT']].groupby(['ITHIM_ft']).agg(numpy.sum)

    # reformat
    loaded_ft_df = loaded_ft_df.unstack().to_frame().reset_index()
    loaded_ft_df.rename(columns={"level_0":"Parameter", 0:"value", "ITHIM_ft":"Mode"}, inplace=True)
    loaded_ft_df["Mode"]      = loaded_ft_df["Parameter"].str[:-4] + str(" - ") + loaded_ft_df["Mode"] # move auto, sm_med_truck, etc to Mode
    loaded_ft_df["Parameter"] = loaded_ft_df["Parameter"].str[-3:]

    loaded_ft_df.loc[loaded_ft_df.Parameter=="VMT","Parameter"] = "Vehicle Miles Traveled"
    loaded_ft_df.loc[loaded_ft_df.Parameter=="PMT","Parameter"] = "Person Miles Traveled"
    loaded_ft_df.loc[loaded_ft_df.Parameter=="PHT","Parameter"] = "Person Hours Traveled"
    loaded_ft_df["Units"] = "miles"
    loaded_ft_df.loc[loaded_ft_df.Parameter=="Person Hours Traveled","Units"] = "hours"

    outfile = os.path.join("metrics","ITHIM","DistanceTraveledByFacilityType_auto+truck.csv")
    loaded_ft_df.to_csv(outfile, index=False)
    print "Wrote %s" % outfile

