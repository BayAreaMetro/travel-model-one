#
# crawl_model_dirs
#
# Script to crawl a set of model dirs on L/M and then find their corresponding
# run directories on model2-[abcd]
#
# Can check for a criteria and report on it, and optionally do something in response
#
USAGE = """

"""

import argparse, collections, filecmp, glob, logging, os, re, shutil, subprocess, sys, time

MODEL_MACHINES = collections.OrderedDict([
    ('model2-a','\\\\model2-a\\Model2A-Share\\Projects'),
    ('model2-b','\\\\model2-b\\Model2B-Share\\Projects'),
    ('model2-c','\\\\model2-c\\Model2C-Share\\Projects'),
    ('model2-d','\\\\model2-d\\Model2D-Share\\Projects'),
    ('model3-a','\\\\model3-a\\Model3A-Share\\Projects'),
    #('model2-a',r'A:\Projects'),
    #('model2-b',r'B:\Projects'),
    #('model2-c',r'F:\Projects'),
    #('model2-d',r'D:\Projects'),
])

# on shared M or L drive -- this serves as the "index"
MODEL_DIRS_PATH_DEFAULT  = "L:\\RTP2021_PPA\\Projects"
LOG_FILE                 = "crawl_model_dirs.log"

# regex for run_id
# e.g. ('2050_TM151_PPA_RT_04', '2050', '151', '_RT', 'RT', '04', '_2300_CaltrainDTX_00', '2300_CaltrainDTX_00')
RUN_ID_RE           = re.compile(r"((\d\d\d\d)_TM(\d\d\d)_PPA(_(BF|CG|RT))?_(\d\d))(_(.*))?")

# 'model_run_dir': path to model run on model2-x 
#                                 (e.g. '\\\\MODEL2-B\\Model2B-Share\\Projects\\2050_TM151_PPA_CG_04_2202_BART_DMU_Brentwood_00')

def run_command(workingdir, command, script_env):
    """
    Given command in the workingdir specified.
    Returns the return code.
    """
    logging.debug("run_command with workingdir={}".format(workingdir))
    logging.debug("                    command={}".format(command))
    logging.debug("                 script_env={}".format(script_env))
    # run it
    proc = subprocess.Popen(command, cwd=workingdir, env=script_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    for line in proc.stdout:
        line_str = line.decode("utf-8")
        line_str = line_str.strip('\r\n')
        logging.debug("  stdout: {0}".format(line_str))
    for line in proc.stderr:
        line_str = line.decode("utf-8")
        line_str = line_str.strip('\r\n')
        logging.debug("  stderr: {0}".format(line_str))
    retcode = proc.wait()

    if retcode != 0:
        raise Exception("Received {}; Failed to run command [{}]".format(retcode, command))
    logging.info("  Received {} from [{}]".format(retcode, command))
    return retcode

def find_model_dirs(model_dirs_path):
    """
    Returns dictionary with the following:

    run_id -> { 'ML_dir'       : path to model run on M or L drive 
                                 (e.g. 'M:\\Application\\Model One\\RTP2021\\ProjectPerformanceAssessment\\Projects\\2202_BART_DMU_Brentwood\\2050_TM151_PPA_CG_04_2202_BART_DMU_Brentwood_00')
                'baseline_id'  : run_id of baseline, extracted from the run_id (e.g. '2050_TM151_PPA_CG_04')
              }
    """
    logging.info("Finding model directories in {}".format(model_dirs_path))
    model_run_dict = {}

    model_dirs = os.listdir(model_dirs_path)
    model_dirs.sort()

    for model_dir in model_dirs:
        model_dir_path = os.path.join(model_dirs_path, model_dir)
        logging.debug("model_dir={}".format(model_dir))

        m = RUN_ID_RE.match(model_dir)

        # if we have a match, assume model dir
        if m != None and os.path.isdir(model_dir_path):
            model_run_dict[model_dir] = {}
            model_run_dict[model_dir]['ML_dir'] = model_dir_path
            model_run_dict[model_dir]['baseline_id'] = m.group(1)
            logging.debug("  =>      ML_dir: {}".format(model_dir_path))
            logging.debug("  => baseline_id: {}".format(m.group(1)))

        # otherwise, check subdirs
        elif os.path.isdir(model_dir_path):
            # not NetworkTests
            if model_dir=="NetworkTests": continue

            sub_dirs = os.listdir(model_dir_path)

            for sub_dir in sub_dirs:
                sub_dir_path = os.path.join(model_dir_path, sub_dir)
                logging.debug(" sub_dir={}".format(sub_dir))

                sub_m = RUN_ID_RE.match(sub_dir)
                if sub_m != None and os.path.isdir(sub_dir_path):
                    model_run_dict[sub_dir] = {}
                    model_run_dict[sub_dir]['ML_dir'] = sub_dir_path
                    model_run_dict[sub_dir]['baseline_id'] = sub_m.group(1)
                    logging.debug("  =>      ML_dir: {}".format(sub_dir_path))
                    logging.debug("  => baseline_id: {}".format(sub_m.group(1)))

    return model_run_dict

def find_model_server_dirs(model_run_dict):
    """
    Given a model run_dict with run_ids as keys, sets the "model_run_dir" to the location of the run on one of the model servers if it can be found
    """
   
    RENAMED = {                   # model machine name  => ML/index
        "2050_TM151_PPA_RT_01_1_Crossings4_plus2fare_00": "2050_TM151_PPA_RT_01_1_Crossings4_05",
        "2050_TM151_PPA_CG_01_1_Crossings4_plus2fare_01": "2050_TM151_PPA_CG_01_1_Crossings4_05",
        "2050_TM151_PPA_BF_01_1_Crossings4_plus2fare_00": "2050_TM151_PPA_BF_01_1_Crossings4_05",
        "2050_TM151_PPA_BF_00_1_Crossings6_01"          : "2050_TM151_PPA_BF_01_1_Crossings6_01", # named incorrectly on model machine
        "2050_TM151_PPA_CG_04_2_WETA_NetExpansion_00"   : "2050_TM151_PPA_CG_04_2601_WETA_NetExpansion_00",  # named incorrectly on model machine
    }
    for machine in MODEL_MACHINES.keys():
        machine_path = MODEL_MACHINES[machine]

        logging.info("Finding model run directories in {}".format(machine_path))

        # iterate through the directories to see if one matches
        project_dirs = os.listdir(machine_path)
        project_dirs.sort(reverse=True)

        for project_dir in project_dirs:

            # lookup in our M/L index array
            # some were renamed so account for that
            if project_dir in RENAMED.keys():
                index_project_dir = RENAMED[project_dir]
            else:
                index_project_dir = project_dir

            # if it's not one of ours, don't care
            if index_project_dir not in model_run_dict.keys():
                # there are some cases where they were renamed
                # e.g. baseline01 runs were renamed to baseline02 on ML
                (index_project_dir, subs) = re.subn(r"(\d\d\d\d_TM\d\d\d_PPA_[BCR][FGT])_01_(.+)", r"\1_02_\2", project_dir)
                if subs == 0: continue

                logging.debug(" Didn't find project_dir {} in keys; trying {}".format(project_dir, index_project_dir))
                if index_project_dir not in model_run_dict.keys(): continue
                logging.debug(" ==> found it")

            model_run_dir = os.path.join(machine_path, project_dir)

            # check if it's already set
            if "model_run_dir" in model_run_dict[index_project_dir]:
                logging.warn("Found model run dir {} but it's already set: {}".format(model_run_dir, model_run_dict[index_project_dir]["model_run_dir"]))

            else:
                # set it
                model_run_dict[index_project_dir]["model_run_dir"] = model_run_dir

def find_bad_quickboards(model_run_dict):
    """
    Given a run_dict with run_ids as keys, sets "bad_quickboards" if there are bad quickboards files based on
    the existence of trn\\trnlinkam_withSupport.dbf files that are older than the fixed version of ConsolidateLoadedTransit.R,
    so older than 5/16/2019 10:58a
    """
    fixed_time = os.path.getmtime("\\\\mainmodel\MainModelShare\\travel-model-one-1.5.1.1\\model-files\\scripts\\core_summaries\\ConsolidateLoadedTransit.R")
    logging.info("Finding bad quickboards (e.g. trnlinkam_withSupport.dbf files older than {}".format(time.ctime(fixed_time)))
    counts = {"bad_quickboards":0}

    for run_id in model_run_dict.keys():
        # only check those with model_run_dirs
        if "model_run_dir" not in model_run_dict[run_id]: continue

        trn_dbf_file  = os.path.join(model_run_dict[run_id]["model_run_dir"],"trn","trnlinkam_withSupport.dbf")

        # if this file doesn't exist then ignore
        if not os.path.exists(trn_dbf_file): continue

        # get the modification time
        trn_dbf_mtime = os.path.getmtime(trn_dbf_file)
        # logging.debug("Time for {} is {}".format(trn_dbf_file, time.ctime(trn_dbf_mtime)))

        if trn_dbf_mtime < fixed_time:
            model_run_dict[run_id]["bad_quickboards"] = True
            counts["bad_quickboards"] += 1

    logging.info("Found {:4} runs with bad_quickboards".format(counts["bad_quickboards"]))

def fix_bad_quickboards(model_run_dict):
    """
    Companion to find_bad_quickboards() -- fixes them by:
    1) Copying updated ConsolidateLoadedTransit.R script into model run CTRAMP
    2) Running it
    3) Running quickboards.bat
    4) Copying updated files into M/L
    """
    logging.info("Fixing bad quickboards")
    FIXED_SCRIPT = "\\\\mainmodel\MainModelShare\\travel-model-one-1.5.1.1\\model-files\\scripts\\core_summaries\\ConsolidateLoadedTransit.R"
    fixed_count = 0

    for run_id in model_run_dict.keys():
        if "bad_quickboards" not in model_run_dict[run_id]: continue
        if model_run_dict[run_id]["bad_quickboards"] != True: continue

        logging.debug("Fixing {} with model_run_dir {}".format(run_id, model_run_dict[run_id]["model_run_dir"]))
        logging.debug("  Copying and running fixed ConsolidateLoadedTransit.R script")

        shutil.copy(FIXED_SCRIPT, os.path.join(model_run_dict[run_id]["model_run_dir"], "CTRAMP", "scripts", "core_summaries"))
        # run it
        script_env = {}
        script_env["SystemRoot"] = r"C:\WINDOWS"
        script_env["TARGET_DIR"] = model_run_dict[run_id]["model_run_dir"]
        script_env["ITER"]       = "3"
        script_env["R_LIB"]      = r"C:\Users\lzorn\Documents\R\win-library\3.5"
        ret_code = run_command(command   =[r"C:\Program Files\R\R-3.5.1\bin\x64\Rscript.exe", '--vanilla', r".\CTRAMP\scripts\core_summaries\ConsolidateLoadedTransit.R"],
                               workingdir=model_run_dict[run_id]["model_run_dir"],
                               script_env=script_env)
        if ret_code != 0:
            logging.warn("  Received non-zero return code: {}".format(ret_code))
            continue

        # run quickboards
        logging.debug("  Running quickboards")
        script_env["PATH"] = r"C:\Program Files\Java\jdk1.8.0_181\bin"
        ret_code = run_command(command   =[os.path.join(model_run_dict[run_id]["model_run_dir"], "CTRAMP", "scripts", "metrics", "quickboards.bat"),
                                                        r".\CTRAMP\scripts\metrics\quickboards.ctl"],
                               workingdir=model_run_dict[run_id]["model_run_dir"],
                               script_env=script_env)
        if ret_code != 0:
            logging.warn("  Received non-zero return code: {}".format(ret_code))
            continue
        # move aside old quickboards
        shutil.move(os.path.join(model_run_dict[run_id]["model_run_dir"], "trn","quickboards.xls"),
                    os.path.join(model_run_dict[run_id]["model_run_dir"], "trn","quickboards_bad.xls"))
        # move fixed quickboards into place
        shutil.move(os.path.join(model_run_dict[run_id]["model_run_dir"], "quickboards.xls"),
                    os.path.join(model_run_dict[run_id]["model_run_dir"], "trn","quickboards.xls"))
        # move aside old quickboards on ML
        shutil.move(os.path.join(model_run_dict[run_id]["ML_dir"], "OUTPUT", "trn", "quickboards.xls"),
                    os.path.join(model_run_dict[run_id]["ML_dir"], "OUTPUT", "trn", "quickboards_bad.xls"))
        # copy fixed quickboards into place
        shutil.copy(os.path.join(model_run_dict[run_id]["model_run_dir"], "trn","quickboards.xls"),
                    os.path.join(model_run_dict[run_id]["ML_dir"], "OUTPUT", "trn", "quickboards.xls"))

        # plus dbfs
        for timeperiod in ["ea","am","md","pm","ev"]:
            # delete the bad ones
            os.remove(os.path.join(model_run_dict[run_id]["ML_dir"], "OUTPUT", "trn", "trnlink{}_withSupport.dbf".format(timeperiod)))

            shutil.copy(os.path.join(model_run_dict[run_id]["model_run_dir"], "trn", "trnlink{}_withSupport.dbf".format(timeperiod)),
                        os.path.join(model_run_dict[run_id]["ML_dir"], "OUTPUT", "trn"))
        fixed_count += 1

    logging.info("Fixed {} bad_quickboards".format(fixed_count))

def find_bad_ouput(model_run_dict):
    """
    Given a run_dict with run_ids as keys, sets "bad_output" if the OUTPUT doesn't match extractor.
    Checks the extractor\\metrics\\auto_times.csv with OUTPUT\\metrics\\auto_times.csv
    """
    logging.info("Finding bad output (e.g. runs with mismatching OUTPUT\\metrics\\auto_times.csv and extractor\\metrics\\auto_times.csv")
    counts = {"missing":0, "mismatch":0}
    for run_id in model_run_dict.keys():

        # only check those with model_run_dirs
        if "model_run_dir" not in model_run_dict[run_id]: continue

        # only check those with extractor metrics auto_times.csv
        extractor_file = os.path.join(model_run_dict[run_id]["model_run_dir"], "extractor", "metrics", "auto_times.csv")
        if not os.path.exists(extractor_file): continue

        # and output metrics auto_times.csv
        output_file = os.path.join(model_run_dict[run_id]["ML_dir"], "OUTPUT", "metrics", "auto_times.csv")
        if not os.path.exists(output_file):
            model_run_dict[run_id]["bad_output"] = "missing"
            counts["missing"] += 1

        elif filecmp.cmp(extractor_file, output_file) == False:
            model_run_dict[run_id]["bad_output"] = "mismatch"
            counts["mismatch"] += 1

    logging.info("Found {:4} runs with bad_output == missing".format(counts["missing"]))
    logging.info("Found {:4} runs with bad_output == mismatch".format(counts["mismatch"]))

def find_trnbuild_type(model_run_dict):
    """
    Given a run_dict with run_ids as keys, sets "trnbuild_type" as "x86" or "x64" based on the line that looks like this in the last
    trn\TransitAssignment.iter3\TPPL*.PRN file

    TRNBUILD (v.06/18/2018 [6.4.4 x64])  Wed May 08 21:00:07 2019
    """
    logging.info("Finding trnbuild type (e.g. x86 vs x64)")
    counts = {"x64":0, "x86":0}
    trnbuild_type_re = re.compile(r"TRNBUILD \(v\S+ \[(\S+) (x64|x86)\]\)")

    for run_id in model_run_dict.keys():

        # only check those with model_run_dirs
        if "model_run_dir" not in model_run_dict[run_id]: continue

        trn_dir = os.path.join(model_run_dict[run_id]["model_run_dir"], "trn", "TransitAssignment.iter3")
        if not os.path.exists(trn_dir): continue

        prn_files = glob.glob(os.path.join(trn_dir, "TPPL*.PRN"))
        if len(prn_files) == 0: continue

        prn_files.sort()
        last_prn_file = prn_files[-1]

        prn_file = open(last_prn_file, "r")
        for line in prn_file:
            m = trnbuild_type_re.match(line)
            if m == None: continue

            # logging.debug("Found match on {} with {}".format(line, m.groups()))
                
            if m.group(1) != "6.4.4":
                logging.warn("Unexpected TRNBUILD version found for run {} in {}: {}".format(run_id, prn_file, m.group(0)))
                model_run_dict[run_id]["trnbuild_type"] = m.group(0)

            else:
                model_run_dict[run_id]["trnbuild_type"] = m.group(2)
                if m.group(2) == "x64": counts["x64"] += 1
                if m.group(2) == "x86": counts["x86"] += 1

            break
        prn_file.close()

    logging.info("Found {:4} runs with trnbuild_type == x64".format(counts["x64"]))
    logging.info("Found {:4} runs with trnbuild_type == x86".format(counts["x86"]))


def find_mismatch_trnbuild(model_run_dict):
    """
    Find runs with baseline runs set and check if the trnbuild_type matches.
    Sets "trnbuild_base" = one of ["missing_run", "missing_trnbuild_type", "match", "mismatch"]
    """
    counts = {"missing_run":0, "missing_trnbuild_type":0, "match":0, "mismatch":0}
    logging.info("Finding trnbuild_base (e.g. checking if base and build have matching trnbuild_type)")

    for run_id in model_run_dict.keys():
        # only look at those that have a baseline and a trnbuild_type
        if "baseline_id" not in model_run_dict[run_id].keys(): continue
        baseline_id = model_run_dict[run_id]["baseline_id"]

        if "trnbuild_type" not in model_run_dict[run_id].keys(): continue
        trnbuild_type = model_run_dict[run_id]["trnbuild_type"]

        # lookup baseline run info
        if baseline_id not in model_run_dict.keys():
            model_run_dict[run_id]["trnbuild_base"] = "missing_run"
            counts["missing_run"] += 1
            continue

        if "trnbuild_type" not in model_run_dict[baseline_id].keys():
            model_run_dict[run_id]["trnbuild_base"] = "missing_trnbuild_type"
            counts["missing_trnbuild_type"] += 1
            continue

        baseline_trnbuild_type = model_run_dict[baseline_id]["trnbuild_type"]
        if baseline_trnbuild_type == trnbuild_type:
            model_run_dict[run_id]["trnbuild_base"] = "match"
            counts["match"] += 1

        else:
            model_run_dict[run_id]["trnbuild_base"] = "mismatch"
            counts["mismatch"] += 1

    logging.info("Found {:4} runs with trnbuild_base == match".format(counts["match"]))
    logging.info("Found {:4} runs with trnbuild_base == mismatch".format(counts["mismatch"]))
    logging.info("Found {:4} runs with trnbuild_base == missing_trnbuild_type".format(counts["missing_trnbuild_type"]))
    logging.info("Found {:4} runs with trnbuild_base == missing_run".format(counts["missing_run"]))


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument("--model_dirs_path", help="Model directory path. e.g. L:\\RTP2021_PPA\\Projects", default="L:\\RTP2021_PPA\\Projects")
    args = parser.parse_args()

    # create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(ch)
    # file handler
    fh = logging.FileHandler(os.path.join(args.model_dirs_path, LOG_FILE), mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(fh)

    # create the model run dictionary with initial keys "ML_dir" and "baseline_id"
    model_run_dict = find_model_dirs(args.model_dirs_path)

    # add the "model_run_dir"
    find_model_server_dirs(model_run_dict)

    # add "bad_quickbards"
    find_bad_quickboards(model_run_dict)
    fix_bad_quickboards(model_run_dict)

    # add "bad_output"
    find_bad_ouput(model_run_dict)

    # add "trnbuild_type"
    find_trnbuild_type(model_run_dict)

    # add "trnbuild_base"
    find_mismatch_trnbuild(model_run_dict)

    # print them
    run_ids = model_run_dict.keys()
    run_ids.sort()

    for run_id in run_ids:
        logging.debug("{}".format(run_id))
        for key in sorted(model_run_dict[run_id].keys()):
            logging.debug("  {:<15} => {}".format(key, model_run_dict[run_id][key]))


