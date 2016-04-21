USAGE = """

  python rollupITHIMAcrossScenarios.py ScenarioKey.csv scenario_ITHIM_results.csv

  Reads ScenarioKey.csv and then the ITHIM files for the corresponding scenarios,
  including incQ1 and incQ4 results.

  Outputs scenario_ITHIM_results.csv

"""

import csv, os, sys
import pandas

if __name__ == '__main__':

    if len(sys.argv) != 3:
        print USAGE
        sys.exit()

    scenario_file = sys.argv[1]
    output_file   = sys.argv[2]

    print "Reading scenario key file: [%s]" % scenario_file
    csvfile = open(scenario_file, 'rb')
    csvreader = csv.DictReader(csvfile, delimiter=",")

    all_results_df  = None
    all_results_set = False

    # read the ITHIM files
    for row in csvreader:
        src          = row["src"]
        scenario     = row["Scenario"]
        modelversion = src[5:7]

        if modelversion != "05":
            print "Scenario [%s] with src [%s] has modelversion [%s] != 05.  Skipping because ITHIM results don't exist." % (scenario, src, modelversion)
            continue

        for incQ in [-1,1,4]:
            ithim_file = os.path.join(src,"OUTPUT","metrics","ITHIM","results%s.csv" % ("" if incQ<0 else "_inc%d" % incQ))
            results_df = pandas.read_csv(ithim_file)
            print "Read [%s] for [%s]" % (ithim_file, scenario)

            # set "report_year" to scenario
            if incQ > 0:
                results_df["report_year"] = scenario + (", incQ%d" % incQ)
                results_df["scenario_id"] = results_df["scenario_id"] + ("_incQ%d" % incQ)
            else:
                results_df["report_year"] = scenario

            if all_results_set:
                all_results_df  = pandas.concat([all_results_df, results_df], axis=0)
            else:
                all_results_df  = results_df
                all_results_set = True

    # bug fix
    all_results_df["scenid_itemid_mode_strata_age_sex"] = all_results_df["scenid_itemid_mode_strata_age_sex"].str.replace("freeway", "highway")

    # Save it
    all_results_df.to_csv(output_file, index=False)
    print "Wrote %s" % output_file


