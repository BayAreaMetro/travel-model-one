USAGE = """

  python rollupITHIMAcrossScenarios.py

  Reads ScenarioKey.csv and then the ITHIM files for the corresponding scenarios.

  Outputs scenario_ITHIM_results.csv

"""

import csv, os
import pandas

if __name__ == '__main__':

    csvfile = open('ScenarioKey.csv', 'rb')
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

        ithim_file = os.path.join(src,"OUTPUT","metrics","ITHIM","results.csv")
        results_df = pandas.read_csv(ithim_file)
        print "Read [%s] for [%s]" % (ithim_file, scenario)

        # set "report_year" to scenario
        results_df["report_year"] = scenario

        if all_results_set:
            all_results_df  = pandas.concat([all_results_df, results_df], axis=0)
        else:
            all_results_df  = results_df
            all_results_set = True

    # bug fix
    all_results_df["scenid_itemid_mode_strata_age_sex"] = all_results_df["scenid_itemid_mode_strata_age_sex"].str.replace("freeway", "highway")

    # Save it
    outfile = "scenario_ITHIM_results.csv"
    all_results_df.to_csv(outfile, index=False)
    print "Wrote %s" % outfile


