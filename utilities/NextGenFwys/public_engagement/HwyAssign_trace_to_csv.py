import pandas as pd
print('running: HwyAssign_trace_to_csv.py')
df = pd.read_csv('DApath.log', sep='\s\s+', engine='python', header=None)
df_toll = pd.read_csv('DAtollpath.log', sep='\s\s+', engine='python', header=None)
print('read: .log files')
print(df.head())
df[df.iloc[:, 0] == df.iloc[:, 0].max()].to_csv('DApath.csv', index=None, header=False)
df_toll[df_toll.iloc[:, 0] == df_toll.iloc[:, 0].max()].to_csv('DAtollpath.csv', index=None, header=False)
print('wrote: .csv files')