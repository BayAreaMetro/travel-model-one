USAGE = """

  Run this from HwyAssign_trace folder on modeling servers
  e.g., \\model3-a\Model3A-Share\Projects\2035_TM152_NGF_NP10_Path1a_02\HwyAssign_trace  Processes model outputs and creates a single csv with scenario metrics, called metrics\scenario_metrics.csv
  
  This script converts the data from a .log file into .csv files to be used in tableau

  Data is cleaned by only keeping the last iteration of driven routes for each OD pair

"""

import pandas as pd

def main():
    print('running: HwyAssign_trace_to_csv.py')
    # read .log files as pandas dataframes
    df = pd.read_csv('DApath.log', sep='\s\s+', engine='python', header=None)
    df_toll = pd.read_csv('DAtollpath.log', sep='\s\s+', engine='python', header=None)
    print('read: .log files')
    print(df.head())
    # Convert all columns to int dtype.
    df = df.astype('int')
    df_toll = df_toll.astype('int')
    # filter for max iteration and save dataframes as csv files
    df[df.iloc[:, 0] == df.iloc[:, 0].max()].to_csv('DApath.csv', index=None, header=False)
    df_toll[df_toll.iloc[:, 0] == df_toll.iloc[:, 0].max()].to_csv('DAtollpath.csv', index=None, header=False)
    print('wrote: .csv files')

if __name__ == "__main__":
    main()
