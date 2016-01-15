import os, re, sys

import numpy
import pandas as pd

USAGE = """

  python rollupAllProjects.py

  Run this in the directory with all the project files.  Rolls up project-specific files
  into a single csv, `AllProjects.csv`.

"""

if __name__ == '__main__':

    ALL_PROJECTS_DATA_FILENAME = "AllProjects_Data.csv"
    ALL_PROJECTS_DESC_FILENAME = "AllProjects_Desc.csv"
    QUICKSUMMARY_FILENAME      = "QuickSummary.csv"
    NUM_DESCRIPTION_FIELDS     = 17
    FILE_STR_RE = re.compile("BC_(.+)_base(.+).csv")


    all_projs_list = []
    proj_ids       = []
    compare_ids    = []
    base_ids       = []
    quicksummary_list = []
    for proj_file in os.listdir("."):

        # skip if dir
        if os.path.isdir(proj_file): continue

        # skip this one, if it exists already
        if proj_file in [ALL_PROJECTS_DATA_FILENAME,
                         ALL_PROJECTS_DESC_FILENAME,
                         QUICKSUMMARY_FILENAME]:
            continue
        if proj_file == "base.csv": continue
        if proj_file[-4:] == ".twb": continue

        if proj_file[:13] == "quicksummary_":
            qs_series = pd.Series.from_csv(proj_file, index_col=[0], header=None)
            quicksummary_list.append(qs_series)
            continue

        if proj_file[-4:] != ".csv": continue

        file_match  = FILE_STR_RE.search(proj_file)
        assert(file_match != None)

        proj_series = pd.Series.from_csv(proj_file, index_col=[0,1,2,3], header=0)
        proj_id     = proj_series.loc['Project ID',numpy.NaN,numpy.NaN,numpy.NaN]
        compare_id  = proj_series.loc['Project Compare ID',numpy.NaN,numpy.NaN,numpy.NaN]
        assert(file_match.group(1) == proj_id)
        all_projs_list.append(proj_series)
        proj_ids.append(proj_id)
        compare_ids.append(compare_id)
        base_ids.append(file_match.group(2))


    qs_dataframe = pd.DataFrame(data=quicksummary_list,)
    qs_dataframe.to_csv(QUICKSUMMARY_FILENAME, index=False)

    all_projs_dataframe = pd.concat(all_projs_list, axis=1, 
                                    join_axes=[all_projs_list[0].index],
                                    names=compare_ids)
    # all_projs_dataframe now has a 3-tuple MultiIndex for rows,
    # and the columns are the project ids

    # save the project attributes (constants) aside for later
    projs_desc          = all_projs_dataframe.iloc[:NUM_DESCRIPTION_FIELDS,]

    # stack the rows -- that is, before the columns were the project ids, one col per project
    # convert it to rows -- so there's one value column, and a row per project id
    all_projs_dataframe.columns = compare_ids
    all_projs_dataframe = all_projs_dataframe.iloc[NUM_DESCRIPTION_FIELDS:,].stack()

    # Name the new column in the index 'Values'
    new_names = list(all_projs_dataframe.index.names)
    new_names[-1] = 'Project Compare ID'
    all_projs_dataframe.index.names = new_names
    all_projs_dataframe.name = 'Values'

    # save this
    all_projs_dataframe.to_csv(ALL_PROJECTS_DATA_FILENAME, header=True)

    projs_desc.index = projs_desc.index.get_level_values(0)
    projs_desc = projs_desc.transpose()
    projs_desc.to_csv(ALL_PROJECTS_DESC_FILENAME, index=False, header=True)
    # print projs_desc.columns

