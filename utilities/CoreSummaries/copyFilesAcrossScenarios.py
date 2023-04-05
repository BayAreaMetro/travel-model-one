USAGE = r"""

  Replaces the old summarizeAcrossScenariosUnion.bat but moving into python because .bat files are limited.

  Takes an arg with the ModelRuns.xlsx

"""
import argparse, os, shutil
import pandas

# output_dir -> file_list
OUTPUT_FILES = {
    ".":[
        "avgload5period",
        "avgload5period_vehclasses"
    ],
    "metrics":[
        "topsheet",
        "scenario_metrics",
        "auto_times",
        "parking_costs_tour",
        "parking_costs_tour_destTaz",
        "parking_costs_tour_ptype_destTaz",
        "parking_costs_trip_destTaz",
        "parking_costs_trip_distBins",
        "emfac_ghg",
        "vmt_vht_metrics_by_taz",
    ],
    "core_summaries":[
        "ActiveTransport",
        "ActivityPattern",
        "AutomobileOwnership",
        "CommuteByEmploymentLocation",
        "CommuteByIncomeHousehold",
        "CommuteByIncomeJob",
        "JourneyToWork",
        "JourneyToWork_modes",
        "PerTripTravelTime",
        "TimeOfDay",
        "TimeOfDay_personsTouring",
        "TravelCost",
        "TripDistance",
        "VehicleMilesTraveled"
    ],
    "trn":[
        "trnline",
    ],
    "shapefile":[
        "network_links_withXY",
        "network_trn_links",
        "network_trn_route_links",
    ]
}

# mapping based on 'run_set' column to location of model runs on M/L
RUN_SET_MODEL_PATHS = {
    'IP'            :'M:\\Application\\Model One\\RTP2021\\IncrementalProgress',
    'DraftBlueprint':'M:\\Application\\Model One\\RTP2021\\IncrementalProgress',
    'FinalBlueprint':'M:\\Application\\Model One\\RTP2021\\Blueprint',
    'EIR'           :'M:\\Application\\Model One\\RTP2021\\Blueprint',
    'NGF'           :'L:\\Application\\Model_One\\NextGenFwys\\Scenarios',
}

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument("ModelRuns_xlsx", metavar="ModelRuns.xlsx", help="ModelRuns.xlsx")
    # topsheet + scenario_metrics only option?
    my_args = parser.parse_args()

    model_runs_df = pandas.read_excel(my_args.ModelRuns_xlsx)
    print("Read {}; head:\n{}".format(my_args.ModelRuns_xlsx, model_runs_df.head()))
    print(model_runs_df.dtypes)

    # expects columns: 'project','year','directory','run_set','category','urbansim_path','urbansim_runid','status'
    assert('run_set' in model_runs_df.columns)
    assert('status' in model_runs_df.columns)
    assert('directory' in model_runs_df.columns)

    print("Enter destination directory: ", end="")
    my_args.dest_dir = input()
    assert(os.path.isdir(my_args.dest_dir))

    status_values_set = set(model_runs_df['status'].tolist())
    print("Which runs do you want to copy?  Found these options for status: {}".format(status_values_set))
    print("Enter 'all' or a comma-delimited list: ", end="")
    status_to_copy = input()
    if status_to_copy=="all":
        my_args.status_to_copy = status_values_set
    else:
        my_args.status_to_copy = set(status_to_copy.split(","))

    # copy files
    for output_dir in OUTPUT_FILES.keys():
        print("Copying files for {}".format(output_dir))

        for output_file in OUTPUT_FILES[output_dir]:

            print("  Copying output_file: {}".format(output_file))

            for model_run in model_runs_df.itertuples():
                # only copy if model run status was specified above
                if model_run.status not in my_args.status_to_copy: 
                    continue

                if model_run.run_set not in RUN_SET_MODEL_PATHS.keys():
                    print("    run_set value {} not recognized; skipping".format(model_run.run_set))
                    continue

                source_dir = os.path.join(RUN_SET_MODEL_PATHS[model_run.run_set], model_run.directory)

                file_suffix_list = ["csv"]
                if output_dir == "shapefile":
                    file_suffix_list = ["shp", "shp.xml", "cpg", "dbf", "prj", "shx"]
                
                for file_suffix in file_suffix_list:
                    source_file = os.path.join(source_dir, "OUTPUT", output_dir, "{}.{}".format(output_file, file_suffix))
                    dest_file = os.path.join(my_args.dest_dir, "{}_{}.{}".format(output_file, model_run.directory, file_suffix))

                    # skip if it exists already
                    if os.path.isfile(dest_file):
                        print("    Destination file {} exists -- skipping".format(dest_file))
                        continue

                    # skip if source file doesn't exist
                    if not os.path.isfile(source_file):
                        print("   Source file {} does not exist -- skipping".format(source_file))
                        continue

                    # log it
                    print("    Copying {}".format(source_file))
                    print("      => {}".format(dest_file))
                    shutil.copyfile(source_file, dest_file)
    # delete files
    # run directories to keep
    current_directory = list(model_runs_df.loc[model_runs_df.status == "current"]['directory'])
    # extensions to modify
    extensions = ('.csv','.shp', 'shp.xml', '.cpg', '.dbf', '.prj', '.shx')
    # delete files from previous ModelRun.xlsx
    for f in os.listdir(my_args.dest_dir):
        if not (any(x in f for x in current_directory)):
            if f.endswith(extensions):
                if f != 'freeway_arterial_links.csv':
                    os.remove(f)
                    print('Remove' + ' '+ f)

    print("Complete")
