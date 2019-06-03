import os
import csv
import pandas as pd
from pandas import DataFrame


#os.chdir(os.path.join(os.getcwd(), 'all_projects_metrics_dir'))


############ rolling up all bc_metrics

# get transit model output files for five time periods
bcmetrics_file_list = [i for i in os.listdir('.') if 'BC_' in i]
df_metrics = pd.DataFrame(columns=[u'category1', u'category2', u'category3', u'variable_name', u'values', u'Project', u'Future', u'ProjectID', u'BaseID'])

for file in bcmetrics_file_list:
    df = pd.read_csv(file)
    df['Project'] = df.loc[3,'values']
    df['Future'] = df.loc[7,'values']
    df['ProjectID'] = df.loc[2,'values']
    df['BaseID'] = df.loc[8,'values']
    drop_index = list(range(0,13))
    df = df.drop(drop_index,axis="rows")
    df_metrics = pd.concat([df_metrics, df], axis=0)


df_metrics.to_csv("AllProjects_bc_metrics.csv", header=True, index=False)
print ("Successfully wrote AllProjects_bc_metrics.csv to \\all_projects_metrics_dir")


############ rolling up all quick summaries

quicksummary_file_list = [i for i in os.listdir('.') if 'quicksummary' in i]
quicksummary_list = []

for file in quicksummary_file_list:
    qs_series = pd.Series.from_csv(file, index_col=[0], header=None)
    quicksummary_list.append(qs_series)
  
qs_dataframe = pd.DataFrame(data=quicksummary_list)
qs_dataframe.to_csv("AllProjects_quick_summary.csv", index=False)
print ("Successfully wrote AllProjects_quick_summary.csv to \\all_projects_metrics_dir")

