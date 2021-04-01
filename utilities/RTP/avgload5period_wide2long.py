USAGE = """

Quick script to convert avgload5period_[model_run].csv to avgload5periodlong_[model_run].csv
by moving time period from columns to rows.

"""
import argparse, os, sys
import pandas

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument("model_run", help="Model run")
    args = parser.parse_args()

    inputfile  = "avgload5period_{}.csv".format(args.model_run)
    outputfile = "avgload5periodlong_{}.csv".format(args.model_run)

    wide_df = pandas.read_csv(inputfile)
    print("Read {}; head:\n{}".format(inputfile, wide_df.head()))

    wide_df.rename(columns=lambda x: x.strip(), inplace=True)
    wide_df.rename(columns={'volEA_tot':'voltotEA', 'volAM_tot':'voltotAM', 
                            'volMD_tot':'voltotMD', 'volPM_tot':'voltotPM', 'volEV_tot':'voltotEV'}, inplace=True)
    cols = wide_df.columns.values
    print("columns: {}".format(cols))

    # 'cspdEA' 'cspdAM' 'cspdMD' 'cspdPM' 'cspdEV'
    # 'volEA_tot' 'volAM_tot' 'volMD_tot' 'volPM_tot' 'volEV_tot'
    # 'ctimEA' 'ctimAM' 'ctimMD' 'ctimPM' 'ctimEV'
    # 'vcEA' 'vcAM' 'vcMD' 'vcPM' 'vcEV'
    long_df = pandas.wide_to_long(wide_df, 
                                 stubnames=['cspd','ctim','vc', 'voltot'], i=['a','b'], j='timeperiod', suffix='(EA|AM|MD|PM|EV)')
    long_df.reset_index(inplace=True)
    print(long_df.head())

    long_df.to_csv(outputfile, index=False, header=True)
    print("Wrote {}".format(outputfile))