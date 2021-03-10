USAGE = """

Melts(?) tazdata for tableau

"""

import glob, os, sys
import pandas

SD_NAMES = "X:\\travel-model-one-master\utilities\geographies\superdistrict-county.csv"

if __name__ == '__main__':

    # read superdistrict/county labels
    sd_names_df = pandas.read_csv(SD_NAMES)
    print('sd_names_df: \n{}'.format(sd_names_df))

    file_list = glob.glob('tazData_*.csv')

    print('file_list: {}'.format(file_list))
    tazdata_df_list = []

    for filename in sorted(file_list):
        model_dir = filename[8:-4]
        print('model_dir: {}'.format(model_dir))

        # nonstandard - skip
        if model_dir.startswith('2035_TM152_IPA'): continue

        tazdata_df = pandas.read_csv(filename)

        # handle problem with double school enrollment columns -- drop second
        # see https://app.asana.com/0/450971779231601/1200008687160138/f
        colnames = list(tazdata_df.columns.values)
        if 'HSENROLL.1' in colnames:
            tazdata_df.drop(columns=['HSENROLL.1','COLLFTE.1','COLLPTE.1'], inplace=True)

        tazdata_df['directory'] = model_dir
        # print('tazdata_head: \n{}'.format(tazdata_df.head()))

        tazdata_df_list.append(tazdata_df)

    # put them all together
    tazdata_all_df = pandas.concat(tazdata_df_list)
    tazdata_all_df = pandas.merge(left=tazdata_all_df, right=sd_names_df, on=['SD','COUNTY'], how='left')
    print('tazdata_all_df len={} head=\n{}'.format(len(tazdata_all_df), tazdata_all_df.head()))

    tazdata_all_df.drop(columns=['ZERO','sftaz'], inplace=True)
    index_cols      = ['directory','ZONE','COUNTY','COUNTY_NUM_NAME','DISTRICT','SD','SD_NUM_NAME']
    standalone_cols = ['AREATYPE','EMPRES','SHPOP62P','TERMINAL','TOPOLOGY','TOTACRE','TOTEMP','TOTHH','TOTPOP','OPRKCST','PRKCST']
    # these columns don't make sense independently
    group_cols      = { 'person_age'     :['AGE0004','AGE0519','AGE2044','AGE4564','AGE65P'],
                        'emp_by_industry':['AGREMPN','FPSEMPN', 'HEREMPN','MWTEMPN','RETEMPN','OTHEMPN'],
                        'hh_by_inc'      :['HHINCQ1','HHINCQ2','HHINCQ3','HHINCQ4'],
                        'pop'            :['HHPOP','gqpop'],
                        'enrollment'     :['HSENROLL','COLLFTE','COLLPTE'],
                        'acre'           :['CIACRE','RESACRE'],
                        'du'             :['MFDU','SFDU']
                      }

    print("columns: {}".format(tazdata_all_df.columns))

    # a couple extra columns
    tazdata_all_df['totdu']    = tazdata_all_df['MFDU'] + tazdata_all_df['SFDU']
    tazdata_all_df['HHINCQ12'] = tazdata_all_df['HHINCQ1'] + tazdata_all_df['HHINCQ2']
    value_vars = standalone_cols + ['totdu','HHINCQ12']
    for group_key in group_cols.keys():
        value_vars = value_vars + group_cols[group_key]

    # melt the vars into long form
    tazdata_melt_df = tazdata_all_df.melt(id_vars=index_cols, value_vars=value_vars)

    output_file = "tazDataAll_standalone.csv"
    tazdata_melt_df.to_csv(output_file, index=False, header=True)
    print("Wrote {}".format(output_file))

    for group_key in group_cols.keys():
        # for group columns, we want the format to be
        # TAZ du_group du
        # 1   MFDU     25
        # 1   SFDU     10
        # etc 
        tazdata_group_df = tazdata_all_df[index_cols+group_cols[group_key]]
        print("Processing group {}".format(group_key))
        print("tazdata_group_df: \n{}".format(tazdata_group_df.head()))

        tazdata_melt_df = tazdata_group_df.melt(id_vars=index_cols, value_vars=group_cols[group_key],
                                                var_name="{}_group".format(group_key), value_name=group_key)
        print("tazdata_melt_df: \n{}".format(tazdata_melt_df.head()))

        # output - use dash to distinguish
        output_file = "tazDataAll_{}.csv".format(group_key)
        tazdata_melt_df.to_csv(output_file, index=False, header=True)
        print("Wrote {}".format(output_file))

    sys.exit()