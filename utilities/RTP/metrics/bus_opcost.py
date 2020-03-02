DESCRIPTION = """

  Run this in the directory in M with all the model directories (destinations)
  e.g. M:\Application\Model One\RTP2017\Project Performance Assessment\Projects\_Complete

  For each road SGR run:

    1) Runs net2csv_agvload5period.job if the previous output is out of date
       and doesn't contain bus opcosts; this updates hwy/iter3/avgload5period_vehclasses.csv.

    2) If updated, copies updated file hwy/iter3/avgload5period_vehclasses.csv to extractor/

    3) If updated, copies the updated file hwy/iter3/avgload5period_vehclasses.csv to the M: drive

    4) Calculates bus operating cost by reading the transit assignment files
       (trn/trnlink[ea,am,md,pm,ev]_wlk_exp_wlk.csv) and joining them with the
       roadway network (hwy/iter3/avgload5period_vehclasses.csv); outputs
       metrics/bus_opcost.csv (if it doesn't exist already)

    5) Copies the output file metrics/bus_opcost.csv to extractor/

    6) Copies the outputfile metrics/bus_opcost.csv to the M: drive

  At the end, write out combined outputfile to all_metrics/bus_opcost.txt
  (distilled to just run dir).  Bus Operating Costs are in 2000 dollars.

"""
import logging,os,shutil,subprocess,sys
import pysal
import numpy, pandas

CODE_DIR = r"C:\Users\lzorn\Documents\travel-model-one-v05\utilities\PBA40\metrics"

TIMEPERIODS = [
    ('ea',3.0),
    ('am',4.0),
    ('md',5.0),
    ('pm',4.0),
    ('ev',5.0)
]

# This is just how Lisa has it setup
MODEL_MACHINES_TO_MAPPED_DRIVES = {
    "model2-a" : r"D:\\",
    "model2-b" : r"A:\\",
    "model2-c" : r"E:\\",
    "model2-d" : r"I:\\"
}

ROAD_SGR_RUNS = [
    ("2040_05_503_1401",   "model2-a", "1401_LSRSGR_nofunding"          ),
    ("2040_05_503_1402",   "model2-a", "1402_LSRSGR_localfunding"       ),
    ("2040_05_503_1402_a", "model2-c", "1402_a_LSRSGR_localfunding"     ),
    ("2040_05_503_1403",   "model2-b", "1403_LSRSGR_preservePCI"        ),
    ("2040_05_503_1403_a", "model2-d", "1403_a_LSRSGR_preservePCI"      ),
    ("2040_05_503_1405",   "model2-b", "1405_LSRSGR_localfunding_weight"),
    ("2040_05_503_1406",   "model2-b", "1406_LSRSGR_preservePCI_weight" ),
    ("2040_05_503_1407",   "model2-d", "1407_LSRSGR_idealPCI"           ),
    ("2040_05_503_1408",   "model2-d", "1408_LSRSGR_idealPCI_weight"    ),
    ("2040_05_503_1501",   "model2-a", "1501_Highway_nofunding"         ),
    ("2040_05_503_1502",   "model2-a", "1502_Highway_current"           ),
    ("2040_05_503_1503",   "model2-b", "1503_HighwaySGR_idealIRI"       ),
]

def read_dbf(dbf_fullpath):
    """
    Returns the pandas DataFrame
    """
    import pysal
    dbfin = pysal.open(dbf_fullpath)
    vars = dbfin.header
    data = dict([(var, dbfin.by_col(var)) for var in vars])

    table_df = pandas.DataFrame(data)

    print "  Read %d lines from %s" % (len(table_df), dbf_fullpath)

    return table_df

def runCubeScript(workingdir, script_filename):
    """
    Run the cube script specified in the tempdir specified.
    Returns the return code.
    """
    # run it
    proc = subprocess.Popen("runtpp %s" % script_filename, cwd=workingdir,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for line in proc.stdout:
        line = line.strip('\r\n')
        print "  stdout: " + line
    for line in proc.stderr:
        line = line.strip('\r\n')
        print "  stderr: " + line
    retcode = proc.wait()
    if retcode == 2:
        raise Exception("Failed to run Cube script %s" % (script_filename))
    print "  Received %d from 'runtpp %s'" % (retcode, script_filename)


if __name__ == '__main__':

    ITERATION = int(os.environ['ITER'])
    assert(ITERATION==3)

    all_trn_busopc = 0
    all_trn_busopc_init = False

    for run_dir_tuple in ROAD_SGR_RUNS:

        model_machine_dir = run_dir_tuple[0]
        model_machine     = run_dir_tuple[1]
        m_dir             = run_dir_tuple[2]

        print "Processing %s as %s on %s" % (m_dir, model_machine_dir, model_machine)

        roadnet_file = os.path.join(MODEL_MACHINES_TO_MAPPED_DRIVES[model_machine],
                                    "Projects", model_machine_dir,
                                    "hwy","iter%d" % ITERATION, "avgload5period_vehclasses.csv")
        roadnet_df = pandas.read_table(roadnet_file, sep=",")
        print "  Read %s" % roadnet_file

        if 'busopc' not in roadnet_df.columns.values:
            # 1) if out of date, rerun net2csv_avgload5period.job
            runCubeScript(workingdir=os.path.join(MODEL_MACHINES_TO_MAPPED_DRIVES[model_machine],
                                                  "Projects", model_machine_dir),
                          script_filename=os.path.join(CODE_DIR, "net2csv_avgload5period.JOB"))
            roadnet_df = pandas.read_table(roadnet_file, sep=",")
            assert('busopc' in roadnet_df.columns.values)

            # 2) copy to extractor
            extractor_file = os.path.join(MODEL_MACHINES_TO_MAPPED_DRIVES[model_machine],
                                          "Projects", model_machine_dir,"extractor","avgload5period_vehclasses.csv")
            print "  Copying to %s" % extractor_file
            shutil.copy2(roadnet_file, extractor_file)

            # 3) copy to M
            m_file = os.path.join(m_dir, "OUTPUT", "avgload5period_vehclasses.csv")
            print "  Copying to %s" % m_file
            shutil.copy2(roadnet_file, m_file)

        roadnet_df = roadnet_df[['a','b','state','cityid','cityname','busopc','busopc_pave']]

        trn_busopc_df = 0

        m_file = os.path.join(m_dir, "OUTPUT", "bus_opcost.csv")
        # if the bus_opcost file exists, just read it
        if os.path.exists(m_file):
            trn_busopc_df = pandas.read_csv(m_file, sep=",")
            print "  Read %s" % m_file

        else:

            trn_busopc_df_init = False
            for timeperiod_tuple in TIMEPERIODS:
    
                timeperiod          = timeperiod_tuple[0]
                timeperiod_duration = timeperiod_tuple[1]
    
                # 4) calculate bus operating cost by reading the transit assignment files
                trn_asgn_df = read_dbf(os.path.join(MODEL_MACHINES_TO_MAPPED_DRIVES[model_machine],
                                                    "Projects",model_machine_dir,"trn","trnlink%s_wlk_exp_wlk.dbf" % timeperiod))
    
                # we only want bus lines
                trn_asgn_df = trn_asgn_df.loc[(trn_asgn_df.MODE >= 10)&(trn_asgn_df.MODE<100)]
    
                # FREQ minutes/1 bus
                # => of runs = time period minutes x (1 bus/freq minutes)
                # e.g. 3 hours x (60 min/hour) x (1 bus/30 min) = 6
                trn_asgn_df['bus runs'] = timeperiod_duration*60/trn_asgn_df['FREQ']
                trn_asgn_df['bus miles'] = trn_asgn_df['bus runs'] * trn_asgn_df['DIST']*0.01
    
                # join to the roadway network
                trn_asgn_df = pandas.merge(left=trn_asgn_df, right=roadnet_df, how='left', left_on=['A','B'], right_on=['a','b'])
                # busopc are in 2000 cents per mile. Convert these to 2000 dollars and multiply by bus runs to get daily,
                # then by 300 to get annual, then by 1.49 to get 2017 dollars.
                trn_asgn_df['total bus opcost'         ] = trn_asgn_df['bus runs'] * (0.01*trn_asgn_df['busopc']     ) * (trn_asgn_df['DIST']*0.01) * 300 * 1.49
                trn_asgn_df['total bus pavement opcost'] = trn_asgn_df['bus runs'] * (0.01*trn_asgn_df['busopc_pave']) * (trn_asgn_df['DIST']*0.01) * 300 * 1.49
    
                # check join failures
                join_fail_miles = trn_asgn_df.loc[pandas.isnull(trn_asgn_df.busopc), 'bus miles'].sum()
                total_miles     = trn_asgn_df.loc[:,'bus miles'].sum()
                print "  %s: %d bus miles failed to join out of %d => %.1f%%" % (timeperiod, join_fail_miles, total_miles, 100.0*join_fail_miles/total_miles)
                # sum up Bus Miles Traveled, Bus Opcost, Bus Opcost from Pavement by mode
    
                trn_by_mode = trn_asgn_df.groupby('MODE', as_index=False).agg({'total bus opcost':numpy.sum,
                                                                               'total bus pavement opcost':numpy.sum,
                                                                               'bus miles':numpy.sum})
                trn_by_mode['timeperiod'] = timeperiod
                trn_by_mode['m_dir']      = m_dir
                trn_by_mode['model_dir']  = model_machine_dir
                # print trn_by_mode.head()
    
                if trn_busopc_df_init==False: # it doesn't like checking if a dataFrame is none
                    trn_busopc_df = trn_by_mode
                    trn_busopc_df_init = True
                else:
                    trn_busopc_df = trn_busopc_df.append(trn_by_mode)
                # print "Full table has length %d" % len(trn_busopc_df)
    
            run_busopc_file = os.path.join(MODEL_MACHINES_TO_MAPPED_DRIVES[model_machine],
                                           "Projects", model_machine_dir,"metrics","bus_opcost.csv")
            print "  Writing file %s" % run_busopc_file
            trn_busopc_df.to_csv(run_busopc_file,index=False)
    
            # 5) Copies the output file metrics/bus_opcost.csv to extractor/
            extractor_file = os.path.join(MODEL_MACHINES_TO_MAPPED_DRIVES[model_machine],
                                          "Projects", model_machine_dir,"extractor","bus_opcost.csv")
            print "  Copying to %s" % extractor_file
            shutil.copy2(run_busopc_file, extractor_file)
    
            # 6) Copies the outputfile metrics/bus_opcost.csv to the M: drive
            print "  Copying to %s" % m_file
            shutil.copy2(run_busopc_file, m_file)

        # append to all run bus opc dataframe
        if all_trn_busopc_init==False:
            all_trn_busopc_df = trn_busopc_df
            all_trn_busopc_init = True
        else:
            all_trn_busopc_df = all_trn_busopc_df.append(trn_busopc_df)

    all_busopc_by_run = all_trn_busopc_df.groupby(['m_dir', 'model_dir'], as_index=False).agg({'total bus opcost':numpy.sum,
                                                                                               'total bus pavement opcost':numpy.sum,
                                                                                               'bus miles':numpy.sum})
    all_busopc_by_run.to_csv(os.path.join("all_metrics","bus_opcost.txt"), index=False)
    print "Wrote all_metrics/bus_opcost.csv"