USAGE = r"""

  Replaces the old summarizeAcrossScenariosUnion.bat but moving into python because .bat files are limited.

  Takes an arg with the ModelRuns.xlsx

"""
import argparse, os, re, pathlib, shutil
import pandas

# output_dir -> file_list
COPY_FILES = {
    "OUTPUT":[
        "avgload5period",
        "avgload5period_vehclasses"
    ],
    "OUTPUT\\metrics":[
        "topsheet",
        "scenario_metrics",
        "auto_times",
        "auto_timesbyTimePeriod",
        "parking_costs_tour",
        "parking_costs_tour_destTaz",
        "parking_costs_tour_ptype_destTaz",
        "parking_costs_trip_destTaz",
        "parking_costs_trip_distBins",
        "vmt_vht_metrics_by_taz",
        "trips_cordon_mode_summary",
        "truck_trips_by_timeperiod",
        "transit_crowding_complete"
    ],
    "OUTPUT\\core_summaries":[
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
        "VehicleMilesTraveled",
        "ODTravelTime_byModeTimeperiodIncome",
        "ActivityDurationSummary"
    ],
    "OUTPUT\\trn":[
        "trnline",
    ],
    "OUTPUT\\shapefile":[
        "network_links_withXY",
        "network_trn_links",
        "network_trn_route_links",
        "network_trn_lines"
    ],
    "OUTPUT\\emfac":[
        "emfac_summary",
    ],
    "INPUT\\landuse":[
        "tazData",
    ]
}

# mapping based on 'run_set' column to location of model runs on M/L
RUN_SET_MODEL_PATHS = {
    'RTP_2025IP'    :'M:\\Application\\Model One\\RTP2025\\IncrementalProgress',
    'RTP2025'       :'M:\\Application\\Model One\\RTP2025\\Blueprint',
    'IP'            :'M:\\Application\\Model One\\RTP2021\\IncrementalProgress',
    'RTP2021'       :'M:\\Application\\Model One\\RTP2021\\Blueprint',
    'DraftBlueprint':'M:\\Application\\Model One\\RTP2021\\IncrementalProgress',
    'FinalBlueprint':'M:\\Application\\Model One\\RTP2021\\Blueprint',
    'EIR'           :'M:\\Application\\Model One\\RTP2021\\Blueprint',
    'NGF'           :'L:\\Application\\Model_One\\NextGenFwys\\Scenarios',
    'NGF_Round2'    :'L:\\Application\\Model_One\\NextGenFwys_Round2\\Scenarios',
    'RTP2025_IP'    :'M:\\Application\\Model One\\RTP2025\\IncrementalProgress',
    'STIP'          :'M:\\Application\\Model One\\STIP2024'
}

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument("ModelRuns_xlsx", metavar="ModelRuns.xlsx", help="ModelRuns.xlsx")
    # topsheet + scenario_metrics only option?
    my_args = parser.parse_args()

    model_runs_df = pandas.read_excel(my_args.ModelRuns_xlsx)
    print(f"Read {my_args.ModelRuns_xlsx}; head:\n{model_runs_df.head()}")
    print(model_runs_df.dtypes)

    # expects columns: 'project','year','directory','run_set','category','urbansim_path','urbansim_runid','status'
    assert('run_set' in model_runs_df.columns)
    assert('status' in model_runs_df.columns)
    assert('directory' in model_runs_df.columns)

    print("Enter destination directory: ", end="")
    my_args.dest_dir = input()
    assert(os.path.isdir(my_args.dest_dir))

    status_values_set = set(model_runs_df['status'].tolist())
    print(f"Which runs do you want to copy?  Found these options for status: {status_values_set}")
    print("Enter 'all' or a comma-delimited list: ", end="")
    status_to_copy = input()
    if status_to_copy=="all":
        my_args.status_to_copy = status_values_set
    else:
        my_args.status_to_copy = set(status_to_copy.split(","))

    # option to delete files
    print("Do you want to delete files related to any other runs? (y/n): ", end="")
    my_args.delete_other_run_files = input().lower()
    print(my_args)

    # create list of model run directories to copy
    directory_copy_list = list(model_runs_df.loc[model_runs_df['status'].isin(my_args.status_to_copy)]['directory'])
    # lower case these
    directory_copy_list = [dir.lower() for dir in directory_copy_list]
    print(f"{directory_copy_list=}")

    # copy files
    for copy_dir in COPY_FILES.keys():
        print(f"Copying files for {copy_dir}")

        for copy_file in COPY_FILES[copy_dir]:

            if my_args.delete_other_run_files == "y":
                print(f"  Looking for other versions of output_file to delete: {copy_file}")

                # these are the files we're ok to delete
                # assume model run ID starts with 4-digit year
                potential_file_to_delete_re_str = r"^{}_(?P<run_id>\d\d\d\d_.+)\.{}$".format(
                    copy_file,
                    "csv" if copy_dir != "shapefile" else "(shp|shp.xml|cpg|dbf|prj|shx)")
                # print(potential_file_to_delete_re_str)
                potential_file_to_delete_re = re.compile(potential_file_to_delete_re_str)

                for potential_file_to_delete in os.listdir(my_args.dest_dir):
                    match = re.search(potential_file_to_delete_re, potential_file_to_delete)
                    if match == None: continue

                    if match.group('run_id').lower() not in directory_copy_list:
                        print(f"    => Deleting {potential_file_to_delete}")
                        os.remove(os.path.join(my_args.dest_dir, potential_file_to_delete))

            print(f"  Copying copy_file: {copy_file}")

            for model_run in model_runs_df.itertuples():
                # only copy if model run status was specified above
                if model_run.status not in my_args.status_to_copy: 
                    continue

                if model_run.run_set not in RUN_SET_MODEL_PATHS.keys():
                    print(f"    run_set value {model_run.run_set} not recognized; skipping")
                    continue

                source_dir = pathlib.Path(RUN_SET_MODEL_PATHS[model_run.run_set]) / model_run.directory

                file_suffix_list = ["csv"]
                if copy_dir.endswith("shapefile"):
                    file_suffix_list = ["shp", "shp.xml", "cpg", "dbf", "prj", "shx"]
                
                for file_suffix in file_suffix_list:
                    source_file =  source_dir / copy_dir / f"{copy_file}.{file_suffix}"
                    dest_file = pathlib.Path(my_args.dest_dir) / f"{copy_file}_{model_run.directory}.{file_suffix}"
                    # skip if it exists already
                    if os.path.isfile(dest_file):
                        print(f"    Destination file {dest_file} exists -- skipping")
                        continue

                    # skip if source file doesn't exist
                    if not os.path.isfile(source_file):
                        print(f"   Source file {source_file} does not exist -- skipping")
                        continue

                    # log it
                    print(f"    Copying {source_file}")
                    print(f"      => {dest_file}")
                    shutil.copyfile(source_file, dest_file)

    print("Complete")
