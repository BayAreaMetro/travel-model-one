USAGE = """

Filter out households and persons with home TAZ in unconnected zones from either
popsyn inputs or from accessibilities/logsums inputs.

For run_mode==logsum:

  Input:   skims\\unconnected_zones.csv (from skims\\findNoAccessZones.job)
           logsums\\accessibilities_dummy_full_households.csv
           logsums\\accessibilities_dummy_full_persons.csv
           logsums\\accessibilities_dummy_full_model_households.csv
           logsums\\accessibilities_dummy_full_model_persons.csv
           logsums\\accessibilities_dummy_full_indivTours.csv

  Output:  logsums\\accessibilities_dummy_households.csv
           logsums\\accessibilities_dummy_persons.csv
           logsums\\accessibilities_dummy_model_households.csv
           logsums\\accessibilities_dummy_model_persons.csv
           logsums\\accessibilities_dummy_indivTours.csv

For run_mode==popsyn:

  Input:  skims\\unconnected_zones.csv (from skims\\findNoAccessZones.job)
          INPUT\\hhFile*.csv
          INPUT\\personFile*.csv

  Output: popsyn\\[householdfile]
          popsyn\\[personFile]
"""

import argparse, os, pathlib, shutil, sys
import pandas

FILES_TO_PROCESS = {
    'logsum': ["households","persons","model_households","model_persons","indivTours"],
    'popsyn':  ["hhFile.*", "personFile.*"]
}

if __name__ == '__main__':
    # for notify_slack
    sys.path.insert(1, "CTRAMP\\scripts")

    parser = argparse.ArgumentParser(description=USAGE)
    parser.add_argument('run_mode', choices=['popsyn','logsum'])
    args = parser.parse_args()

    unconnected_zones_file = pathlib.Path("skims") / "unconnected_zones.csv"
    unconnected_zones_df = pandas.read_csv(unconnected_zones_file)
    unconnected_zones = unconnected_zones_df['ZONE'].tolist()
    
    print(f"Found {len(unconnected_zones)} unconnected zone(s) in {unconnected_zones_file}")

    # exclude external zones
    unconnected_zones[:] = [x for x in unconnected_zones if x <= 1454]
    print(f"Found {len(unconnected_zones)} unconnected zone(s) in {unconnected_zones_file} after excluding external zones")

    # notify slack since this could be important
    if len(unconnected_zones)>0:
        # try but don't force it
        try:
            import notify_slack
            notify_slack.post_message(f"Found {len(unconnected_zones)} unconnected zone(s) in {unconnected_zones_file} after excluding external zones")
        except Exception as e:
            print(f"Exception caught trying to notify slack:\n{e}")

    # nothing to do -- just copy the files
    if len(unconnected_zones)==0:
        print("No filtering to do -- copying files")

        for filepart in FILES_TO_PROCESS[args.run_mode]:
            if args.run_mode == 'logsum':
                shutil.copyfile(src=pathlib.Path("logsums") / f"accessibilities_dummy_full_{filepart}.csv",
                                dst=pathlib.Path("logsums") / f"accessibilities_dummy_{filepart}.csv")
            if args.run_mode == 'popsyn':
                # copy INPUT\popsyn\hhFileXXX.csv to popsyn\hhfileXXX.csv, etc
                for filename in pathlib.Path("INPUT/popsyn").glob(filepart):
                    shutil.copyfile(src=filename, dst=pathlib.Path(*filename.parts[1:]))
        sys.exit(0)

    # let's filter
    filter_hh_ids = []
    for filepart in FILES_TO_PROCESS[args.run_mode]:

        # read the file
        if args.run_mode == 'logsum':
            infile = pathlib.Path("logsums") / f"accessibilities_dummy_full_{filepart}.csv"
        if args.run_mode == 'popsyn':
            infiles = sorted(pathlib.Path("INPUT/popsyn").glob(filepart))
            assert(len(infiles)==1)
            infile = infiles[0]
            
        df = pandas.read_csv(infile)
        print(f"Read {len(df):9d} lines from {infile}")

        # first, we need the list of household IDs
        if len(filter_hh_ids) == 0:
            filter_hh_ids = df.loc[ df.TAZ.isin(unconnected_zones), "HHID"].unique().tolist()
            print(f"Filtering out {len(filter_hh_ids)} households: {filter_hh_ids[:20]}...")

            # For the popsyn case, notify slack since this could be a problem.
            # Normally, we expect that flooded zones wouldn't have landuse
            if (len(filter_hh_ids)>0) and (args.run_mode == 'popsyn'):
                # try but don't force it
                try:
                    import notify_slack
                    notify_slack.post_message(f":warning: Filtering out {len(filter_hh_ids)} households for {args.run_mode}")
                except Exception as e:
                    print(f"Exception caught trying to notify slack:\n{e}")

        # HHID or hh_id
        if "HHID" in list(df.columns.values):
            df = df.loc[ ~df.HHID.isin(filter_hh_ids) ]
        elif "hh_id" in list(df.columns.values):
            df = df.loc[ ~df.hh_id.isin(filter_hh_ids) ]
        else:
            raise NotImplementedError("Input file has neither HHID or hh_id")

        # write it out
        if args.run_mode == 'logsum':
            outfile = pathlib.Path("logsums") / f"accessibilities_dummy_{filepart}.csv"
        if args.run_mode == 'popsyn':
            outfile = pathlib.Path(*infile.parts[1:])

        df.to_csv(outfile, index=False)
        print(f"Wrote {len(df):8d} lines to   {outfile}")
    
    # done