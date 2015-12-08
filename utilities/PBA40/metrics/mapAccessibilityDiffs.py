USAGE = """

  This script:

  * Reads [run_dir]\OUTPUT\metrics\BC_config.csv to find the base_dir
  * Reads the accessibilities and accessibility markets for [run_dir] and base_dir
  * Outputs into [run_dir]\OUTPUT\metrics a mandatoryAcc_[ID]_base[baseID].csv and
                                         nonMandatoryAcc_[ID]_base[baseID].csv
    for joining and mapping
  * (someday) accessiblity_diffs_[ID]_base[baseID].pdf with maps
"""
import argparse, csv, datetime, os, sys
import pandas


def read_accessibilities(proj_dir, mandatory, col_prefix):
    """
    Read the accessibilities and return them as a dataframe
    """
    filename = os.path.join(proj_dir, "OUTPUT", "accessibilities",
                            "mandatoryAccessibilities.csv" if mandatory else "nonMandatoryAccessibilities.csv")
    acc_df   = pandas.read_table(filename, sep=",")
    acc_df.drop('destChoiceAlt', axis=1, inplace=True)
    acc_df.set_index(['taz','subzone'], inplace=1)
    # convert the loads of columns to two: variable, value
    acc_df   = pandas.DataFrame(acc_df.stack())
    acc_df.reset_index(inplace=True)
    # split the income/autosufficiency label
    acc_df['incQ_label']     = acc_df['level_2'].str.split('_',n=1).str.get(0)
    acc_df['autoSuff_label'] = acc_df['level_2'].str.split('_',n=1).str.get(1)
    # remove the now extraneous 'level_2'
    acc_df.drop('level_2', axis=1, inplace=True)
    acc_df.rename(columns={0:'%s_dclogsum' % col_prefix,
                           'subzone':'walk_subzone'},
                  inplace=True)
    return acc_df

def read_markets(proj_dir, col_prefix):
    """
    Read the accessibility markets and return them as a dataframe
    """
    filename   = os.path.join(proj_dir, "OUTPUT", "core_summaries", "AccessibilityMarkets.csv")
    acc_mar_df = pandas.read_table(filename, sep=",")

    acc_mar_df.rename(columns={'num_persons':'%s_num_persons' % col_prefix,
                               'num_workers':'%s_num_workers' % col_prefix,
                               'num_workers_students':'%s_num_workers_students' % col_prefix},
                      inplace=True)
    return acc_mar_df

if __name__ == '__main__':
    pandas.set_option('display.width', 300)

    parser = argparse.ArgumentParser(description = USAGE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=str,
                        help="Directory with model run results OUPUT\metrics, etc")

    my_args = parser.parse_args()

    config_filepath = os.path.join(my_args.run_dir, "OUTPUT","metrics","BC_config.csv")
    if not os.path.exists(config_filepath):
        print "No config file at [%s]" % config_filepath
        raise


    config = {}
    config_file = open(config_filepath, 'rb')
    config_reader = csv.reader(config_file, delimiter=",")
    for row in config_reader:
        config[row[0]] = row[1]
    config_file.close()

    if config["Compare"] != "scenario-baseline":
        print "This script only supports Compare=scenario-baseline right now."
        raise

    base_run_dir = config['base_dir']
    # strip off OUTPUT\metrics
    base_run_dir = os.path.normpath(os.path.join(base_run_dir,"..",".."))

    # read the scenario and base accessibilities
    scen_mand_acc = read_accessibilities(my_args.run_dir, True,  "scen")
    scen_nonm_acc = read_accessibilities(my_args.run_dir, False, "scen")
    base_mand_acc = read_accessibilities(base_run_dir, True,  "base")
    base_nonm_acc = read_accessibilities(base_run_dir, False, "base")

    # read the scenario and base markets
    scen_market   = read_markets(my_args.run_dir, "scen")
    base_market   = read_markets(base_run_dir,    "base")

    # average the markets
    market        = pandas.merge(scen_market, base_market, how='outer')
    market.fillna(0, inplace=True)
    market['avg_num_workers_students'] = 0.5*market.base_num_workers_students + 0.5*market.scen_num_workers_students
    market['avg_num_persons']          = 0.5*market.base_num_persons          + 0.5*market.scen_num_persons

    # diff the logsums
    mand_acc      = pandas.merge(scen_mand_acc, base_mand_acc, how='left')
    mand_acc['logsum_diff']         = mand_acc.scen_dclogsum - mand_acc.base_dclogsum
    mand_acc['logsum_diff_minutes'] = mand_acc.logsum_diff / 0.0134

    nonm_acc      = pandas.merge(scen_nonm_acc, base_nonm_acc, how='left')
    nonm_acc['logsum_diff']         = nonm_acc.scen_dclogsum - nonm_acc.base_dclogsum
    nonm_acc['logsum_diff_minutes'] = nonm_acc.logsum_diff / 0.0175

    # add market columns
    mand_acc      = pandas.merge(mand_acc, market[['taz','walk_subzone','incQ_label','autoSuff_label','avg_num_workers_students']], how='left')
    nonm_acc      = pandas.merge(nonm_acc, market[['taz','walk_subzone','incQ_label','autoSuff_label','avg_num_persons']],          how='left')

    # consumer surplus
    mand_acc['cs_hours'] = mand_acc.avg_num_workers_students * mand_acc.logsum_diff_minutes/60.0
    nonm_acc['cs_hours'] = nonm_acc.avg_num_persons          * nonm_acc.logsum_diff_minutes/60.0

    # walk subzone label
    mand_acc['walk_subzone_label'] = '?'
    mand_acc.loc[mand_acc.walk_subzone==0, 'walk_subzone_label'] =    "no_walk_transit"
    mand_acc.loc[mand_acc.walk_subzone==1, 'walk_subzone_label'] = "short_walk_transit"
    mand_acc.loc[mand_acc.walk_subzone==2, 'walk_subzone_label'] =  "long_walk_transit"

    nonm_acc['walk_subzone_label'] = '?'
    nonm_acc.loc[nonm_acc.walk_subzone==0, 'walk_subzone_label'] =    "no_walk_transit"
    nonm_acc.loc[nonm_acc.walk_subzone==1, 'walk_subzone_label'] = "short_walk_transit"
    nonm_acc.loc[nonm_acc.walk_subzone==2, 'walk_subzone_label'] =  "long_walk_transit"

    # ok now we want to move walk_subzone, incQ_label, autoSuff_label to be row headers
    mand_pivot = pandas.pivot_table(mand_acc,
                                    values=['cs_hours','logsum_diff_minutes','avg_num_workers_students'],
                                    index=['taz'],
                                    columns=['walk_subzone_label','incQ_label','autoSuff_label'])
    mand_totals = mand_pivot.sum(axis=1, level=[0])
    # rename/flatten column names
    mand_pivot.columns = [' '.join(col).strip() for col in mand_pivot.columns.values]
    mand_pivot = pandas.merge(mand_pivot, mand_totals, left_index=True, right_index=True)
    mand_csv = os.path.join(my_args.run_dir, "OUTPUT", "metrics","mandatory_logsum_%s_base%s.csv" % (my_args.run_dir, base_run_dir))
    mand_pivot.to_csv(mand_csv)
    print "Wrote mandatory csv to [%s]" % mand_csv

    # ok now we want to move walk_subzone, incQ_label, autoSuff_label to be row headers
    nonm_pivot = pandas.pivot_table(nonm_acc,
                                    values=['cs_hours','logsum_diff_minutes','avg_num_persons'],
                                    index=['taz'],
                                    columns=['walk_subzone_label','incQ_label','autoSuff_label'])
    nonm_totals = nonm_pivot.sum(axis=1, level=[0])
    # rename/flatten column names
    nonm_pivot.columns = [' '.join(col).strip() for col in nonm_pivot.columns.values]
    nonm_pivot = pandas.merge(nonm_pivot, nonm_totals, left_index=True, right_index=True)
    nonm_csv = os.path.join(my_args.run_dir, "OUTPUT", "metrics","nonMandatory_logsum_%s_base%s.csv" % (my_args.run_dir, base_run_dir))
    nonm_pivot.to_csv(nonm_csv)
    print "Wrote nonMandatory csv to [%s]" % nonm_csv
