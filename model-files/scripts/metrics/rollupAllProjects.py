import os
import sys

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
    NUM_DESCRIPTION_FIELDS     = 24

    all_projs_list = []
    proj_ids       = []
    for proj_file in os.listdir("."):

        # skip this one, if it exists already
        if proj_file == ALL_PROJECTS_DATA_FILENAME: continue
        if proj_file == ALL_PROJECTS_DESC_FILENAME: continue
        if proj_file == "base.csv": continue

        proj_series = pd.Series.from_csv(proj_file, index_col=[0,1,2], header=0)
        proj_id     = proj_series.loc['Project ID',numpy.NaN,numpy.NaN]
        assert("%s.csv" % proj_id == proj_file)
        all_projs_list.append(proj_series)
        proj_ids.append(proj_id)

    all_projs_dataframe = pd.concat(all_projs_list, axis=1, 
                                    join_axes=[all_projs_list[0].index],
                                    names=proj_ids)
    # all_projs_dataframe now has a 3-tuple MultiIndex for rows,
    # and the columns are the project ids

    # save the project attributes (constants) aside for later
    projs_desc          = all_projs_dataframe.iloc[:NUM_DESCRIPTION_FIELDS,]

    # stack the rows -- that is, before the columns were the project ids, one col per project
    # convert it to rows -- so there's one value column, and a row per project id
    all_projs_dataframe.columns = proj_ids
    all_projs_dataframe = all_projs_dataframe.iloc[NUM_DESCRIPTION_FIELDS:,].stack()
    # Name the new column in the index 'Values'
    new_names = list(all_projs_dataframe.index.names)
    new_names[-1] = 'Project ID'
    all_projs_dataframe.index.names = new_names
    all_projs_dataframe.name = 'Values'

    # save this
    all_projs_dataframe.to_csv(ALL_PROJECTS_DATA_FILENAME, header=True)

    projs_desc.index = projs_desc.index.get_level_values(0)
    projs_desc = projs_desc.transpose()
    projs_desc.to_csv(ALL_PROJECTS_DESC_FILENAME, index=False, header=True)
    # print projs_desc.columns

