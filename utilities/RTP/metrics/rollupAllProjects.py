import os
import csv
import pandas as pd
#from pandas import qs_dataframe


#os.chdir(os.path.join(os.getcwd(), 'all_projects_metrics_dir'))


############ rolling up all bc_metrics


# create empty dataframe with essential columns
df_metrics = pd.DataFrame(columns=[u'category1', u'category2', u'category3', u'variable_name', u'values', u'Project', u'Future', u'ProjectID', u'BaseID',\
            u'PPA ID', u'Mode'])

# create a list of the bcmetrics.csv for all projects in the folder 
bcmetrics_file_list = [i for i in os.listdir('.') if 'BC_' in i]

# loop through each project file in the list, and add relevant data to the dataframe
for file in bcmetrics_file_list:
    df = pd.read_csv(file)
    df['Project'] = df.loc[4,'values']
    df['Future'] = df.loc[8,'values']
    df['ProjectID'] = df.loc[3,'values']
    df['BaseID'] = df.loc[9,'values']
    df['PPA ID'] = df.loc[3,'values'][0:4]
    df['Mode'] = df.loc[5,'values']
    drop_index = list(range(0,14))
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

