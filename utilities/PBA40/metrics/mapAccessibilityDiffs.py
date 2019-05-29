USAGE = """

  This script:

  * Reads the accessibilities and accessibility markets for [run_dir] and [base_dir]
  * Uses RunResults.py to calculateConsumerSurplus(), which also creates consumer_surplus.csv and associated tableau file in the logsums dir
"""
import argparse, csv, datetime, os, re, shutil, sys, traceback
import numpy, pandas
import RunResults

def read_accessibilities(proj_dir, mandatory, col_prefix, include_output_dir):
    """
    Read the accessibilities and return them as a dataframe
    """
    filename = os.path.join(proj_dir, "OUTPUT" if include_output_dir else "", "logsums",
                            "mandatoryAccessibilities.csv" if mandatory else "nonMandatoryAccessibilities.csv")
    acc_df   = pandas.read_table(filename, sep=",")
    acc_df.drop('destChoiceAlt', axis=1, inplace=True)
    acc_df.set_index(['taz','subzone'], inplace=True)
    # convert the loads of columns to two: variable, value
    acc_df   = pandas.DataFrame(acc_df.stack())
    acc_df.reset_index(inplace=True)
    # split the income/autosufficiency label
    acc_df['incQ_label']     = acc_df['level_2'].str.split('_',n=1).str.get(0)
    acc_df['autoSuff_label'] = acc_df['level_2'].str.split('_',n=1).str.get(1)
    acc_df['hasAV']          = -1
    acc_df.loc[ acc_df['autoSuff_label'].str.endswith('_noAV'), 'hasAV'] = 0
    acc_df.loc[ acc_df['autoSuff_label'].str.endswith('_noAV'), 'autoSuff_label'] = acc_df['autoSuff_label'].str[:-5]
    acc_df.loc[ acc_df['autoSuff_label'].str.endswith('_AV'),   'hasAV'] = 1
    acc_df.loc[ acc_df['autoSuff_label'].str.endswith('_AV'),   'autoSuff_label'] = acc_df['autoSuff_label'].str[:-3]

    # remove the now extraneous 'level_2'
    acc_df.drop('level_2', axis=1, inplace=True)
    acc_df.rename(columns={0:'%s_dclogsum' % col_prefix,
                           'subzone':'walk_subzone'},
                  inplace=True)
    return acc_df

def read_markets(proj_dir, col_prefix, include_output_dir):
    """
    Read the accessibility markets and return them as a dataframe
    """
    filename   = os.path.join(proj_dir, "OUTPUT" if include_output_dir else "", "core_summaries", "AccessibilityMarkets.csv")
    acc_mar_df = pandas.read_table(filename, sep=",")

    acc_mar_df.rename(columns={'num_persons':'%s_num_persons' % col_prefix,
                               'num_workers':'%s_num_workers' % col_prefix,
                               'num_workers_students':'%s_num_workers_students' % col_prefix},
                      inplace=True)
    return acc_mar_df

if __name__ == '__main__':
    pandas.set_option('display.width', 300)
    CWD = os.getcwd()

    parser = argparse.ArgumentParser(description = USAGE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--include_output_dir', action="store_true", help="Assume metrics etc in OUTPUT subdir")
    parser.add_argument('run_dir',  type=str, help="Directory with model run results OUPUT\metrics, etc")
    parser.add_argument('base_dir', type=str, help="Directory with base model run results OUPUT\metrics, etc")

    my_args = parser.parse_args()

    # read the scenario and base accessibilities
    scen_mand_acc = read_accessibilities(my_args.run_dir,  True,  "scen", my_args.include_output_dir)
    scen_nonm_acc = read_accessibilities(my_args.run_dir,  False, "scen", my_args.include_output_dir)
    base_mand_acc = read_accessibilities(my_args.base_dir, True,  "base", my_args.include_output_dir)
    base_nonm_acc = read_accessibilities(my_args.base_dir, False, "base", my_args.include_output_dir)

    # read the scenario and base markets
    scen_market   = read_markets(my_args.run_dir,  "scen", my_args.include_output_dir)
    base_market   = read_markets(my_args.base_dir, "base", my_args.include_output_dir)

    print("scen_mand_acc length {} head\n{}".format(len(scen_mand_acc), scen_mand_acc.head()))
    print("scen_nonm_acc length {} head\n{}".format(len(scen_nonm_acc), scen_nonm_acc.head()))
    print("base_mand_acc length {} head\n{}".format(len(base_mand_acc), base_mand_acc.head()))
    print("base_nonm_acc length {} head\n{}".format(len(base_nonm_acc), base_nonm_acc.head()))

    print("scen_market length {} head\n{}".format(len(scen_market), scen_market.head()))
    print("base_market length {} head\n{}".format(len(base_market), base_market.head()))

    (proj_dir, run_id) = os.path.split(my_args.run_dir)

    config        = {'Foldername - Future':run_id}
    daily_results = {}
    (scen_mand_acc, scen_nonm_acc, mandatoryAccess, nonMandatoryAccess) = \
        RunResults.RunResults.calculateConsumerSurplus(config, daily_results,
                                                       scen_mand_acc, base_mand_acc,
                                                       scen_nonm_acc, base_nonm_acc,
                                                       scen_market,   base_market,
                                                       debug_dir=os.path.join(my_args.run_dir, "OUTPUT" if my_args.include_output_dir else "", "logsums"))
