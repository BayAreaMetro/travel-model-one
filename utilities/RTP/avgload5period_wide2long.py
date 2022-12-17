USAGE = """

Quick script to convert avgload5period_[model_run].csv to avgload5periodlong_[model_run].csv
by moving time period from columns to rows.

Useful for tableau (join with output from avgload5period_no_attributes_shapefile.job)

"""
import argparse, os, sys
import pandas

TIMEPERIODS = ['EA','AM','MD','PM','EV']
VEHCLASSES  = ['da','s2','s3','sm','hv',
               'dat','s2t','s3t','smt','hvt',
               'daav','s2av','s3av']

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument("--vehclasses", action="store_true", help="Pass to run on vehclasses file")
    parser.add_argument("model_run", help="Model run")
    args = parser.parse_args()

    inputfile  = "avgload5period{}_{}.csv".format("_vehclasses" if args.vehclasses else "", args.model_run)
    outputfile = "avgload5periodlong{}_{}.csv".format("_vehclasses" if args.vehclasses else "", args.model_run)

    wide_df = pandas.read_csv(inputfile)
    print("Read {}; head:\n{}".format(inputfile, wide_df.head()))

    wide_df.rename(columns=lambda x: x.strip(), inplace=True)
    if args.vehclasses:
        # vehicle classes first
        long_df = pandas.wide_to_long(
            wide_df, 
            stubnames = ['volEA_','volAM_','volMD_','volPM_','volEV_'], 
            i         = ['a','b'], 
            j         = 'vehclass', 
            suffix    = '(da|s2|s3|sm|hv|dat|s2t|s3t|smt|hvt|daav|s2av|s3av|tot)')
        long_df.reset_index(inplace=True)

        # now time periods - strip trailing whitespace
        long_df.rename(columns=lambda x: x.strip('_'), inplace=True)

        print(long_df.head())
        print("columns: {}".format(long_df.columns.values))

        long_df = pandas.wide_to_long(
            long_df, 
            stubnames = ['cspd','ctim','vc','vol'], 
            i         = ['a','b','vehclass'], 
            j         = 'timeperiod', 
            suffix    = '(EA|AM|MD|PM|EV)')
        long_df.reset_index(inplace=True)

        print(long_df.head())
        print("columns: {}".format(long_df.columns.values))

    else:
        wide_df.rename(columns={'volEA_tot':'voltotEA', 'volAM_tot':'voltotAM', 
                                'volMD_tot':'voltotMD', 'volPM_tot':'voltotPM', 'volEV_tot':'voltotEV'}, inplace=True)
        cols = wide_df.columns.values
        print("columns: {}".format(cols))

        # 'cspdEA' 'cspdAM' 'cspdMD' 'cspdPM' 'cspdEV'
        # 'volEA_tot' 'volAM_tot' 'volMD_tot' 'volPM_tot' 'volEV_tot'
        # 'ctimEA' 'ctimAM' 'ctimMD' 'ctimPM' 'ctimEV'
        # 'vcEA' 'vcAM' 'vcMD' 'vcPM' 'vcEV'
        long_df = pandas.wide_to_long(
            wide_df, 
            stubnames= ['cspd','ctim','vc', 'voltot'],
            i        = ['a','b'], 
            j        = 'timeperiod', 
            suffix   = '(EA|AM|MD|PM|EV)')
        long_df.reset_index(inplace=True)
        print(long_df.head())

    long_df.to_csv(outputfile, index=False, header=True)
    print("Wrote {}".format(outputfile))