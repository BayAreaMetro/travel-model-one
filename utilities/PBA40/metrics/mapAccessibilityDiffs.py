USAGE = """

  This script:

  * Reads [run_dir]\OUTPUT\metrics\BC_config.csv to find the base_dir
  * Reads the accessibilities and accessibility markets for [run_dir] and base_dir
  * Outputs into [run_dir]\OUTPUT\metrics a mandatory_logsum.csv,
                                         nonNandatory_logsum.csv,
                                    mandatory_logsum_tableau.csv,
                                 nonMandatory_logsum_tableau.csv
    for joining and mapping.  The second two are the same as the first two but unpivoted (tableau-style).
  * Outputs [run_dir]\OUTPUT\metrics\CSmap_204_Streetcar.pdf with mandatory map using 0.5 std dev
"""
import argparse, csv, datetime, os, shutil, sys, traceback
import numpy, pandas

NOISE_THRESHHOLD = 0.1
NOISE_SHALLOW    = 0.05

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


def create_map(proj_dir, CWD, pivot_df, mand_nonm, reduced_noise):
    """
    Uses arcpy to create the PDF map
    """
    import arcpy
    print "Importing arcpy"
    ARCPY_DIR = r"M:\Application\Model One\RTP2017\Project Performance Assessment\Projects\_Complete\logsummaps\arcpy"

    mxd = arcpy.mapping.MapDocument(os.path.join(ARCPY_DIR, "ConsumerSurplus.mxd"))
    df  = arcpy.mapping.ListDataFrames(mxd,"*")[0]

    # update it to point to this project
    mxd.findAndReplaceWorkspacePaths("203_Irvington", my_args.run_dir, False)

    # get the Join Layer layer
    cs_lyr = arcpy.mapping.ListLayers(mxd, "Join Layer", df)[0]

    # we need to export the layer because we can't alter symbology on a joined layer
    shp_out = os.path.join(ARCPY_DIR, "copies", "layer_%s.shp" % my_args.run_dir)
    if arcpy.Exists(shp_out):
        print "Exists [%s]" % shp_out
        arcpy.Delete_management(shp_out)
        print "Deleted [%s]" % shp_out
    arcpy.CopyFeatures_management(cs_lyr, shp_out)
    cs_lyr.visible = False

    # now make the symbology layer point that that
    symb_lyr = arcpy.mapping.ListLayers(mxd, "Consumer Surplus Hours", df)[0]
    symb_lyr.replaceDataSource( os.path.join(ARCPY_DIR, "copies"), "SHAPEFILE_WORKSPACE", "layer_%s" % my_args.run_dir, False)
    # symb_lyr.symbology.reclassify()
    if not reduced_noise:
        symb_lyr.symbology.valueField = "mandat_108"
        colname = 'cs_hours'
    else:
        symb_lyr.symbology.valueField = "mandat_111"
        colname = 'cs_hours_rn'
    cs_mean = pivot_df[colname].mean()
    cs_std  = pivot_df[colname].std()

    symb_lyr.symbology.classBreakValues=[pivot_df[colname].min()-1.0,
                                         cs_mean-2.75*cs_std,
                                         cs_mean-2.25*cs_std,
                                         cs_mean-1.75*cs_std,
                                         cs_mean-1.25*cs_std,
                                         cs_mean-0.75*cs_std,
                                         cs_mean-0.25*cs_std,
                                         cs_mean+0.25*cs_std,
                                         cs_mean+0.75*cs_std,
                                         cs_mean+1.25*cs_std,
                                         cs_mean+1.75*cs_std,
                                         cs_mean+2.25*cs_std,
                                         cs_mean+2.75*cs_std,
                                         pivot_df[colname].max()
                                         ]
    symb_lyr.symbology.classBreakLabels=["< 2.75 Std. Dev.",
                                         "-2.75 - -2.25 Std. Dev.",
                                         "-2.25 - -1.75 Std. Dev.",
                                         "-1.75 - -1.25 Std. Dev.",
                                         "-1.25 - -0.75 Std. Dev.",
                                         "-0.75 - -0.25 Std. Dev.",
                                         "-0.25 -  0.25 Std. Dev.",
                                         " 0.25 -  0.75 Std. Dev.",
                                         " 0.75 -  1.25 Std. Dev.",
                                         " 1.25 -  1.75 Std. Dev.",
                                         " 1.75 -  2.25 Std. Dev.",
                                         " 2.25 -  2.75 Std. Dev.",
                                         "> 2.75 Std. Dev."
                                         ]

    desc_str =    "Min:      {:9,.2f}".format(pivot_df[colname].min())
    desc_str += "\nMean:     {:9,.2f}".format(cs_mean)
    desc_str += "\nMax:      {:9,.2f}".format(pivot_df[colname].max())
    desc_str += "\nStd.Dev.: {:9,.2f}".format(cs_std)
    desc_str += "\nSum:      {:9,.2f}".format(pivot_df[colname].sum())
    text_elm = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT")[0]
    text_elm.text = desc_str

    mxd.saveACopy(os.path.join(ARCPY_DIR, "copies", "ConsumerSurplus_%s.mxd" % my_args.run_dir))

    pdffile = "CSmap_%s%s_%s.pdf" % (mand_nonm, "_%.2frn" % NOISE_THRESHHOLD if reduced_noise else "", my_args.run_dir)
    print "Trying to write [%s]" % pdffile
    arcpy.mapping.ExportToPDF(mxd, pdffile)

    # move it
    shutil.copy2(os.path.join(ARCPY_DIR, pdffile),
                os.path.join(CWD, my_args.run_dir, "OUTPUT", "metrics"))
    print "Wrote [%s]" % os.path.join(CWD, my_args.run_dir, "OUTPUT", "metrics", pdffile)
    os.remove(os.path.join(ARCPY_DIR, pdffile))

if __name__ == '__main__':
    pandas.set_option('display.width', 300)
    CWD = os.getcwd()

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

    # reduce noise for logsum_diff_minutes
    # This is because artifacts crop up in the logsum minutes which are just noise
    # For example, if some TAZs previously had 39.9 minute drive access to transit in the baseline and cross over to 40.06 minutes
    # of drive access; they could lose a drive-to-transit mode which would give them a small negative logsum difference, which is really
    # not representative of an actual change in accessibility, but it can come up in the model and then get multiplied out by a large
    # TAX population.
    mand_ldm_max = mand_acc.logsum_diff_minutes.abs().max()
    mand_acc['ldm_ratio'] = mand_acc.logsum_diff_minutes.abs()/mand_ldm_max    # how big is the magnitude compared to max magnitude?
    mand_acc['ldm_mult' ] = 1.0/(1.0+numpy.exp(-(mand_acc.ldm_ratio-NOISE_THRESHHOLD)/NOISE_SHALLOW))
    mand_acc['ldm_rn']    = mand_acc.logsum_diff_minutes*mand_acc.ldm_mult

    nonm_ldm_max = nonm_acc.logsum_diff_minutes.abs().max()
    nonm_acc['ldm_ratio'] = nonm_acc.logsum_diff_minutes.abs()/nonm_ldm_max    # how big is the magnitude compared to max magnitude?
    nonm_acc['ldm_mult' ] = 1.0/(1.0+numpy.exp(-(nonm_acc.ldm_ratio-NOISE_THRESHHOLD)/NOISE_SHALLOW))
    nonm_acc['ldm_rn']    = nonm_acc.logsum_diff_minutes*nonm_acc.ldm_mult

    # add market columns
    mand_acc      = pandas.merge(mand_acc, market[['taz','walk_subzone','incQ_label','autoSuff_label','avg_num_workers_students']], how='left')
    nonm_acc      = pandas.merge(nonm_acc, market[['taz','walk_subzone','incQ_label','autoSuff_label','avg_num_persons']],          how='left')

    # consumer surplus
    mand_acc['cs_hours'] = mand_acc.avg_num_workers_students * mand_acc.logsum_diff_minutes/60.0
    nonm_acc['cs_hours'] = nonm_acc.avg_num_persons          * nonm_acc.logsum_diff_minutes/60.0

    # consumer surplus -- reduced noise
    mand_acc['cs_hours_rn'] = mand_acc.avg_num_workers_students * mand_acc.ldm_rn/60.0
    nonm_acc['cs_hours_rn'] = nonm_acc.avg_num_persons          * nonm_acc.ldm_rn/60.0

    # walk subzone label
    mand_acc['walk_subzone_label'] = '?'
    mand_acc.loc[mand_acc.walk_subzone==0, 'walk_subzone_label'] =    "no_walk_transit"
    mand_acc.loc[mand_acc.walk_subzone==1, 'walk_subzone_label'] = "short_walk_transit"
    mand_acc.loc[mand_acc.walk_subzone==2, 'walk_subzone_label'] =  "long_walk_transit"

    nonm_acc['walk_subzone_label'] = '?'
    nonm_acc.loc[nonm_acc.walk_subzone==0, 'walk_subzone_label'] =    "no_walk_transit"
    nonm_acc.loc[nonm_acc.walk_subzone==1, 'walk_subzone_label'] = "short_walk_transit"
    nonm_acc.loc[nonm_acc.walk_subzone==2, 'walk_subzone_label'] =  "long_walk_transit"

    # write as is for tableau
    mand_csv_tableau = os.path.join(my_args.run_dir, "OUTPUT", "metrics","mandatory_logsum_tableau.csv")
    mand_acc.to_csv(mand_csv_tableau, index=False)
    print "Wrote mandatory (tableau) csv to [%s]" % mand_csv_tableau

    nonm_csv_tableau = os.path.join(my_args.run_dir, "OUTPUT", "metrics","nonMandatory_logsum_tableau.csv")
    nonm_acc.to_csv(nonm_csv_tableau, index=False)
    print "Wrote nonmatory (tableau) csv to [%s]" % nonm_csv_tableau

    # ok now we want to move walk_subzone, incQ_label, autoSuff_label to be row headers
    mand_pivot = pandas.pivot_table(mand_acc,
                                    values=['cs_hours','logsum_diff_minutes','avg_num_workers_students', 'ldm_rn','cs_hours_rn'],
                                    index=['taz'],
                                    columns=['walk_subzone_label','incQ_label','autoSuff_label'])
    mand_totals = mand_pivot.sum(axis=1, level=[0])
    # rename/flatten column names
    mand_pivot.columns = [' '.join(col).strip() for col in mand_pivot.columns.values]
    mand_pivot = pandas.merge(mand_pivot, mand_totals, left_index=True, right_index=True)

    # remove the columns _rn disaggregate columns because it's too much. Keep only the taz sum
    drop_cols = []
    for col in mand_pivot.columns.values:
        if col.startswith('ldm_rn ') or col.startswith('cs_hours_rn '): drop_cols.append(col)
    mand_pivot.drop(drop_cols, axis=1, inplace=True)

    mand_csv = os.path.join(my_args.run_dir, "OUTPUT", "metrics","mandatory_logsum.csv")
    mand_pivot.to_csv(mand_csv)
    print "Wrote mandatory csv to [%s]" % mand_csv

    # ok now we want to move walk_subzone, incQ_label, autoSuff_label to be row headers
    nonm_pivot = pandas.pivot_table(nonm_acc,
                                    values=['cs_hours','logsum_diff_minutes','avg_num_persons', 'ldm_rn','cs_hours_rn'],
                                    index=['taz'],
                                    columns=['walk_subzone_label','incQ_label','autoSuff_label'])
    nonm_totals = nonm_pivot.sum(axis=1, level=[0])
    # rename/flatten column names
    nonm_pivot.columns = [' '.join(col).strip() for col in nonm_pivot.columns.values]
    nonm_pivot = pandas.merge(nonm_pivot, nonm_totals, left_index=True, right_index=True)

    # remove the columns _rn disaggregate columns because it's too much. Keep only the taz sum
    drop_cols = []
    for col in nonm_pivot.columns.values:
        if col.startswith('ldm_rn ') or col.startswith('cs_hours_rn '): drop_cols.append(col)
    nonm_pivot.drop(drop_cols, axis=1, inplace=True)

    nonm_csv = os.path.join(my_args.run_dir, "OUTPUT", "metrics","nonMandatory_logsum.csv")
    nonm_pivot.to_csv(nonm_csv)
    print "Wrote nonMandatory csv to [%s]" % nonm_csv

    try:
        create_map(my_args.run_dir, CWD, mand_pivot, "mandat", reduced_noise=False)
        create_map(my_args.run_dir, CWD, mand_pivot, "mandat", reduced_noise=True)
        create_map(my_args.run_dir, CWD, nonm_pivot, "nonMan", reduced_noise=False)
        create_map(my_args.run_dir, CWD, nonm_pivot, "nonMan", reduced_noise=True)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
