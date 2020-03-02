import os
import sys

import pandas as pd

USAGE = """

  python tallyAutos.py

  Simple script that reads main/householdsData_%ITER%.csv, tallies up the households by
  income quartile and number of autos, scales the households by %SAMPLESHARE%, 
  and outputs the result to metrics/autos_owned.csv

"""

if __name__ == '__main__':
    
    iteration  = int(os.environ['ITER'])
    sampleshare= float(os.environ['SAMPLESHARE'])

    households = pd.read_table(os.path.join("main", "householdData_%d.csv" % iteration),
                          sep=",", index_col=[0])

    # by income
    households['incQ'] = 0
    households.loc[                                  households['income'] <  30000, 'incQ'] = 1
    households.loc[ (households['income'] >= 30000)&(households['income'] <  60000),'incQ'] = 2
    households.loc[ (households['income'] >= 60000)&(households['income'] < 100000),'incQ'] = 3
    households.loc[  households['income'] >= 100000                                ,'incQ'] = 4

    # group by income quartiles
    households_by_incQ = households.groupby('incQ')

    autos_by_inc = households_by_incQ['autos'].value_counts()
    autos_by_inc.index.levels[1].name = 'autos'
    autos_by_inc.name = 'households'

    # divide households by sampleshare
    autos_by_inc = autos_by_inc/sampleshare
    autos_by_inc.to_csv(os.path.join("metrics", "autos_owned.csv"), 
                        header=True, index=True )