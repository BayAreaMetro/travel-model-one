DESCRIPTION = """

    Sets up input directories for Sensitivity Tests requested by CARB in the current working dir.

    Specifically, this sets up 4 income sensitivity tests, copying transit line files
    from a pivot directory and multiplying the transit frequencies by 0.5, 0.75, 1.25 and 1.50.

"""
import os, numpy, pandas, subprocess, sys
pandas.set_option('display.width', 300)
pandas.set_option('float_format', '{:0.4f}'.format)

PIVOT_BASE_DIR = r"M:\\Application\\Model One\\RTP2017\\Scenarios\\"
PIVOT_DIR      = "2015_06_002"
HH_FILE        = "hhFile.pba40_scen00_v12.2015.csv"
PERS_FILE      = "personFile.pba40_scen00_v12.2015.csv"
TAZDATA_FILE   = "tazData.csv"
CSV_TO_DBF_R   = r"C:\\Users\\lzorn\Documents\\travel-model-one-master\\utilities\\taz-data-csv-to-dbf\\taz-data-csv-to-dbf.R"

def convertCsvToDbf(infile, outfile):
    """
    Run the cube script specified in the tempdir specified.
    Returns the return code.
    """
    # run it
    env_dict = dict(os.environ, F_INPUT=infile, F_OUTPUT=outfile)
    command = "Rscript.exe --vanilla %s" % CSV_TO_DBF_R
    proc = subprocess.Popen(command, env=env_dict,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for line in proc.stdout:
        line = line.strip('\r\n')
        print "  stdout: " + line
    for line in proc.stderr:
        line = line.strip('\r\n')
        print "  stderr: " + line
    retcode = proc.wait()
    if retcode == 2:
        raise Exception("Failed to run [%s]" % command)
    print "  Received %d from '%s'" % (retcode, command)

if __name__ == '__main__':

    # read household file
    HH_INPUT_FILE = os.path.join(PIVOT_BASE_DIR, PIVOT_DIR, "INPUT", "popsyn", HH_FILE)
    households_df = pandas.read_csv(HH_INPUT_FILE)
    HINC_col = households_df['HINC'].copy().astype(float)
    print "Read households file [%s] - %d lines" % (HH_INPUT_FILE, len(households_df))

    PERS_INPUT_FILE = os.path.join(PIVOT_BASE_DIR, PIVOT_DIR, "INPUT", "popsyn", PERS_FILE)
    persons_df = pandas.read_csv(PERS_INPUT_FILE)
    PINC_col = persons_df['EARNS'].copy().astype(float)
    print "Read persons    file [%s] - %d lines" % (PERS_INPUT_FILE, len(persons_df))

    TAZDATA_INPUT_FILE = os.path.join(PIVOT_BASE_DIR, PIVOT_DIR, "INPUT", "landuse", TAZDATA_FILE)
    # read the float fields as strings so we don't change the precision or anything
    tazdata_df = pandas.read_csv(TAZDATA_INPUT_FILE,
                                 dtype={"TOTACRE":str,
                                        "RESACRE":str,
                                        "CIACRE":str,
                                        "SHPOP62P":str,
                                        "PRKCST":str,
                                        "OPRKCST":str,
                                        "HSENROLL":str,
                                        "COLLFTE":str,
                                        "COLLPTE":str,
                                        "TERMINAL":str})
    tazdata_cols = list(tazdata_df.columns.values)
    print "Read tazdata    file [%s] - %d lines" % (TAZDATA_INPUT_FILE, len(tazdata_df))

    # income
    for inc_multiplier in [0.75, 0.90, 1.10, 1.25]:

        # this is the directory
        print ""
        dirname = "%s_inc%03d" % (PIVOT_DIR, inc_multiplier*100)

        if os.path.exists(dirname):
            print "Directory [%s] exists -- skipping" % dirname
            continue

        popsyn_dir = os.path.join(dirname, "INPUT", "popsyn")
        os.makedirs(popsyn_dir)
        print "Created directory [%s]" % popsyn_dir

        ## household income and income categories
        households_df['HINC'] = HINC_col*inc_multiplier

        households_df.loc[ (households_df.HINC >       0) & (households_df.HINC <  20000), 'hinccat1'] = 1
        households_df.loc[ (households_df.HINC >=  20000) & (households_df.HINC <  50000), 'hinccat1'] = 2
        households_df.loc[ (households_df.HINC >=  50000) & (households_df.HINC < 100000), 'hinccat1'] = 3
        households_df.loc[ (households_df.HINC >= 100000)                                , 'hinccat1'] = 4

        households_df.loc[ (households_df.HINC >       0) & (households_df.HINC <  10000), 'hinccat2'] = 1
        households_df.loc[ (households_df.HINC >=  10000) & (households_df.HINC <  20000), 'hinccat2'] = 2
        households_df.loc[ (households_df.HINC >=  20000) & (households_df.HINC <  30000), 'hinccat2'] = 3
        households_df.loc[ (households_df.HINC >=  30000) & (households_df.HINC <  40000), 'hinccat2'] = 4
        households_df.loc[ (households_df.HINC >=  40000) & (households_df.HINC <  50000), 'hinccat2'] = 5
        households_df.loc[ (households_df.HINC >=  50000) & (households_df.HINC <  60000), 'hinccat2'] = 6
        households_df.loc[ (households_df.HINC >=  60000) & (households_df.HINC <  75000), 'hinccat2'] = 7
        households_df.loc[ (households_df.HINC >=  75000) & (households_df.HINC < 100000), 'hinccat2'] = 8
        households_df.loc[ (households_df.HINC >= 100000)                                , 'hinccat2'] = 9

        output_file = os.path.join(popsyn_dir, "hhFile.pba40_2015.inc%03d.csv" % int(inc_multiplier*100))
        households_df.to_csv(output_file, index=False, float_format="%.0f")
        print "Wrote [%s]" % output_file

        ## persons
        persons_df['EARNS'] = PINC_col*inc_multiplier

        output_file = os.path.join(popsyn_dir, "personFile.pba40_2015.inc%03d.csv" % int(inc_multiplier*100))
        persons_df.to_csv(output_file, index=False, float_format="%.0f")
        print "Wrote [%s]" % output_file

        # adjust tazdata by tallying households to tazs
        tazdata_dir = os.path.join(dirname, "INPUT", "landuse")
        os.makedirs(tazdata_dir)
        print "Created directory [%s]" % tazdata_dir

        # summarize households by quartile
        HU_households_df = households_df.loc[ households_df.UNITTYPE == 0, ['TAZ','HINC']].copy()
        # https://github.com/BayAreaMetro/modeling-website/wiki/TazData
        HU_households_df["HHINCQ1"] = 0
        HU_households_df["HHINCQ2"] = 0
        HU_households_df["HHINCQ3"] = 0
        HU_households_df["HHINCQ4"] = 0
        HU_households_df.loc[                                 (HU_households_df.HINC < 30000), "HHINCQ1"] = 1
        HU_households_df.loc[(HU_households_df.HINC >= 30000)&(HU_households_df.HINC < 60000), "HHINCQ2"] = 1
        HU_households_df.loc[(HU_households_df.HINC >= 60000)&(HU_households_df.HINC <100000), "HHINCQ3"] = 1
        HU_households_df.loc[(HU_households_df.HINC >=100000)                                , "HHINCQ4"] = 1

        HU_HHINC = HU_households_df[["TAZ","HHINCQ1","HHINCQ2","HHINCQ3","HHINCQ4"]].groupby(["TAZ"]).sum()
        HU_HHINC["hhq_tot"] = HU_HHINC["HHINCQ1"] + HU_HHINC["HHINCQ2"] + HU_HHINC["HHINCQ3"] + HU_HHINC["HHINCQ4"]

        # we don't want to change the tothh from tazdata
        HU_HHINC = pandas.merge(left=HU_HHINC,   right=tazdata_df[["ZONE","TOTHH"]],
                                left_index=True, right_on="ZONE")
        HU_HHINC["hh_scale"] = HU_HHINC["TOTHH"] / HU_HHINC["hhq_tot"]
        HU_HHINC["hh_diff"]  = HU_HHINC["TOTHH"] - HU_HHINC["hhq_tot"]

        print "  Simple tally of households:"
        print "    TAZ household diff in [%d,%d]" % (HU_HHINC["hh_diff"].min(), HU_HHINC["hh_diff"].max())
        print "    TOTHH sum=%d  hhq_tot sum=%d" % (HU_HHINC["TOTHH"].sum(), HU_HHINC["hhq_tot"].sum())

        # first, scale and round to try to hit TOTHH -- these are the goal numbers (except they're floats)
        HU_HHINC["HHINCQ1_f"] = HU_HHINC["hh_scale"]*HU_HHINC["HHINCQ1"]
        HU_HHINC["HHINCQ2_f"] = HU_HHINC["hh_scale"]*HU_HHINC["HHINCQ2"]
        HU_HHINC["HHINCQ3_f"] = HU_HHINC["hh_scale"]*HU_HHINC["HHINCQ3"]
        HU_HHINC["HHINCQ4_f"] = HU_HHINC["hh_scale"]*HU_HHINC["HHINCQ4"]

        HU_HHINC[["HHINCQ1","HHINCQ2","HHINCQ3","HHINCQ4"]] = HU_HHINC[["HHINCQ1_f","HHINCQ2_f","HHINCQ3_f","HHINCQ4_f"]].round().astype(int)
        HU_HHINC["hhq_tot"] = HU_HHINC["HHINCQ1"] + HU_HHINC["HHINCQ2"] + HU_HHINC["HHINCQ3"] + HU_HHINC["HHINCQ4"]

        HU_HHINC["hh_scale"] = HU_HHINC["TOTHH"] / HU_HHINC["hhq_tot"]
        HU_HHINC["hh_diff"]  = HU_HHINC["TOTHH"] - HU_HHINC["hhq_tot"]

        print "  Simple scale & round per TAZ"
        print "    TAZ household diff in [%d,%d]" % (HU_HHINC["hh_diff"].min(), HU_HHINC["hh_diff"].max())
        print "    TOTHH sum=%d  hhq_tot sum=%d" % (HU_HHINC["TOTHH"].sum(), HU_HHINC["hhq_tot"].sum())

        # next, add one or two based on probability
        # so these are the diffs between what we have and goals
        HU_HHINC["HHINCQ1_fd"] = 0
        HU_HHINC["HHINCQ2_fd"] = 0
        HU_HHINC["HHINCQ3_fd"] = 0
        HU_HHINC["HHINCQ4_fd"] = 0
        HU_HHINC.loc[ HU_HHINC.hh_diff != 0, "HHINCQ1_fd"] = HU_HHINC["HHINCQ1_f"]-HU_HHINC["HHINCQ1"]
        HU_HHINC.loc[ HU_HHINC.hh_diff != 0, "HHINCQ2_fd"] = HU_HHINC["HHINCQ2_f"]-HU_HHINC["HHINCQ2"]
        HU_HHINC.loc[ HU_HHINC.hh_diff != 0, "HHINCQ3_fd"] = HU_HHINC["HHINCQ3_f"]-HU_HHINC["HHINCQ3"]
        HU_HHINC.loc[ HU_HHINC.hh_diff != 0, "HHINCQ4_fd"] = HU_HHINC["HHINCQ4_f"]-HU_HHINC["HHINCQ4"]

        # zero the opposite sign since those aren't candidates for adding/subtracting
        HU_HHINC.loc[ (HU_HHINC.hh_diff < 0) & (HU_HHINC.HHINCQ1_fd > 0), "HHINCQ1_fd"] = 0
        HU_HHINC.loc[ (HU_HHINC.hh_diff < 0) & (HU_HHINC.HHINCQ2_fd > 0), "HHINCQ2_fd"] = 0
        HU_HHINC.loc[ (HU_HHINC.hh_diff < 0) & (HU_HHINC.HHINCQ3_fd > 0), "HHINCQ3_fd"] = 0
        HU_HHINC.loc[ (HU_HHINC.hh_diff < 0) & (HU_HHINC.HHINCQ4_fd > 0), "HHINCQ4_fd"] = 0

        HU_HHINC.loc[ (HU_HHINC.hh_diff > 0) & (HU_HHINC.HHINCQ1_fd < 0), "HHINCQ1_fd"] = 0
        HU_HHINC.loc[ (HU_HHINC.hh_diff > 0) & (HU_HHINC.HHINCQ2_fd < 0), "HHINCQ2_fd"] = 0
        HU_HHINC.loc[ (HU_HHINC.hh_diff > 0) & (HU_HHINC.HHINCQ3_fd < 0), "HHINCQ3_fd"] = 0
        HU_HHINC.loc[ (HU_HHINC.hh_diff > 0) & (HU_HHINC.HHINCQ4_fd < 0), "HHINCQ4_fd"] = 0

        # make the remainder sum to 1
        HU_HHINC["HHINCQ_fdtot"] = HU_HHINC.HHINCQ1_fd + HU_HHINC.HHINCQ2_fd + HU_HHINC.HHINCQ3_fd + HU_HHINC.HHINCQ4_fd
        HU_HHINC.loc[ abs(HU_HHINC.hh_diff) > 0.1, "HHINCQ1_fd"]   = HU_HHINC["HHINCQ1_fd"]/HU_HHINC["HHINCQ_fdtot"]
        HU_HHINC.loc[ abs(HU_HHINC.hh_diff) > 0.1, "HHINCQ2_fd"]   = HU_HHINC["HHINCQ2_fd"]/HU_HHINC["HHINCQ_fdtot"]
        HU_HHINC.loc[ abs(HU_HHINC.hh_diff) > 0.1, "HHINCQ3_fd"]   = HU_HHINC["HHINCQ3_fd"]/HU_HHINC["HHINCQ_fdtot"]
        HU_HHINC.loc[ abs(HU_HHINC.hh_diff) > 0.1, "HHINCQ4_fd"]   = HU_HHINC["HHINCQ4_fd"]/HU_HHINC["HHINCQ_fdtot"]

        def increment_HHINCQ(row):
            if row["hh_diff"]==0:
                return row
            inc_col = numpy.random.choice(["HHINCQ1","HHINCQ2","HHINCQ3","HHINCQ4"], p=[row["HHINCQ1_fd"],row["HHINCQ2_fd"],row["HHINCQ3_fd"],row["HHINCQ4_fd"]])
            if row["hh_diff"] > 0:
                row[inc_col] += 1
            else:
                row[inc_col] -= 1
            return row

        # print HU_HHINC.head(20)

        HU_HHINC = HU_HHINC.apply(increment_HHINCQ, axis=1)

        HU_HHINC[["ZONE","HHINCQ1","HHINCQ2","HHINCQ3","HHINCQ4"]] = HU_HHINC[["ZONE","HHINCQ1","HHINCQ2","HHINCQ3","HHINCQ4"]].astype(int)
        HU_HHINC["hhq_tot"] = HU_HHINC["HHINCQ1"] + HU_HHINC["HHINCQ2"] + HU_HHINC["HHINCQ3"] + HU_HHINC["HHINCQ4"]

        HU_HHINC["hh_scale"] = HU_HHINC["TOTHH"] / HU_HHINC["hhq_tot"]
        HU_HHINC["hh_diff"]  = HU_HHINC["TOTHH"] - HU_HHINC["hhq_tot"]

        # print HU_HHINC.head(20)
        print "  After incrementing"
        print "    TAZ household diff in [%d,%d]" % (HU_HHINC["hh_diff"].min(), HU_HHINC["hh_diff"].max())
        print "    TOTHH sum=%d  hhq_tot sum=%d" % (HU_HHINC["TOTHH"].sum(), HU_HHINC["hhq_tot"].sum())

        # put it back together with tazdata, replacing where we have updates
        tazdata_df = pandas.merge(left=tazdata_df, right=HU_HHINC[["ZONE","HHINCQ1","HHINCQ2","HHINCQ3","HHINCQ4"]],
                                  on="ZONE", suffixes=["","_new"], how="left")
        # replce where we have updates
        tazdata_df.loc[ pandas.notnull(tazdata_df.HHINCQ1_new), "HHINCQ1"] = tazdata_df.HHINCQ1_new
        tazdata_df.loc[ pandas.notnull(tazdata_df.HHINCQ1_new), "HHINCQ2"] = tazdata_df.HHINCQ2_new
        tazdata_df.loc[ pandas.notnull(tazdata_df.HHINCQ1_new), "HHINCQ3"] = tazdata_df.HHINCQ3_new
        tazdata_df.loc[ pandas.notnull(tazdata_df.HHINCQ1_new), "HHINCQ4"] = tazdata_df.HHINCQ4_new

        tazdata_df = tazdata_df[tazdata_cols]
        output_file = os.path.join(tazdata_dir, "tazData.csv")
        tazdata_df.to_csv(output_file, index=False, float_format="%.0f")
        print "Wrote [%s]" % output_file

        output_dbf_file = os.path.join(tazdata_dir, "tazData.dbf")
        convertCsvToDbf(output_file, output_dbf_file)

    print "Done"