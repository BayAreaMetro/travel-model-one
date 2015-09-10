import numpy as np
import orca
import pandas as pd

from activitysim.activitysim import other_than
from activitysim.util import reindex


# this caches things so you don't have to read in the file from disk again
@orca.table(cache=True)
def persons_internal(store):
    df = store["persons"]
    return df


# this caches all the columns that are computed on the persons table
@orca.table(cache=True)
def persons(persons_internal):
    return persons_internal.to_frame()

# this is the placeholder for all the columns to update after the
# workplace location choice model
@orca.table()
def persons_workplace(persons):
    return pd.DataFrame(index=persons.index)

# set the short and long walk time based on the sub-zone
@orca.column("persons")
def origin_walk_time(persons):
	return ((persons.home_sub_zone == 0) * -999 + 
		(persons.home_sub_zone == 1) * 0.333 / 3.00 * 60.0 +
		(persons.home_sub_zone == 2) * 0.666 / 3.00 * 60.0)  

@orca.column("persons")
def value_of_time(persons):
	return persons.value_of_time

@orca.column("persons")
def auto_suff_cat(persons):
	return persons.auto_suff_cat

@orca.column("persons")
def income_segment(persons):
	return persons.income_segment

 


    