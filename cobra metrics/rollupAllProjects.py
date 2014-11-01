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

    ALL_PROJECTS_FILENAME = "AllProjects.csv"
    all_projs_dict = {}
    for proj_file in os.listdir("."):

        # skip this one, if it exists already
        if proj_file == ALL_PROJECTS_FILENAME: continue

        proj_series = pd.Series.from_csv(proj_file, index_col=[0,1,2])
        proj_id     = proj_series.loc['Project ID',numpy.NaN,numpy.NaN]
        assert("%s.csv" % proj_id == proj_file)
        all_projs_dict[proj_id] = proj_series


    all_projs_dataframe = pd.DataFrame(all_projs_dict).transpose()
    
    # flatten the multi index for Tableau
    new_cols = []
    for col in all_projs_dataframe.columns:
        if str(col[1]) == "nan":
            new_cols.append(col[0])
        else:
            new_cols.append("%s - %s - %s" % col)

    all_projs_dataframe.columns = pd.Index(new_cols)
    del all_projs_dataframe['category1 - category2 - variable_name']
    print all_projs_dataframe
    all_projs_dataframe.to_csv(ALL_PROJECTS_FILENAME, index=False)