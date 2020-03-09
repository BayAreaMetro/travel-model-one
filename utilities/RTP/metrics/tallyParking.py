import os
import sys

import pandas

USAGE = """

  python tallyParking.py

  Simple script that reads

  * main/indivTourData_%ITER%.csv,
  * main/jointTourData_%ITER%.csv,
  * main/personData_%ITER%.csv (for fp_choice)
  * landuse/tazData.csv (for county, parking costs lookup)
  and tallies up the total tour-based parking costs for drive-tours by tour origin and destination county.
  Also zeros out costs for work tours with free parking.

  Outputs the result to metrics/parking_costs.csv
"""

if __name__ == '__main__':
    pandas.set_option('display.max_columns', 300)
    pandas.set_option('expand_frame_repr', False)

    iteration     = int(os.environ['ITER'])
    sampleshare   = float(os.environ['SAMPLESHARE'])

    ############ Read tazdata ############
    tazdata       = pandas.read_table(os.path.join("landuse", "tazData.csv"), sep=",", index_col=[0])
    tazdata.columns = tazdata.columns.str.upper()
    tazdata       = tazdata[['COUNTY','PRKCST','OPRKCST']]
    # print tazdata.head()

    ############ Read persons ############
    persons       = pandas.read_table(os.path.join("main", "personData_%d.csv" % iteration),
                                sep=",", index_col=False)
    # Free parking eligibility choice
    persons       = persons[['hh_id','person_id','person_num','fp_choice']]

    ############ Read individual tours ############
    indiv_tours   = pandas.read_table(os.path.join("main", "indivTourData_%d.csv" % iteration),
                                      sep=",", index_col=False)
    indiv_tours   = indiv_tours[['hh_id','person_id','tour_category','tour_id',
                                 'tour_purpose','orig_taz','dest_taz','start_hour','end_hour','tour_mode']]
    # Filter to auto tours
    indiv_tours   = indiv_tours.loc[(indiv_tours.tour_mode>=1)&(indiv_tours.tour_mode<=6)]
    indiv_tours['num_participants'] = 1
    indiv_tours_participants = len(indiv_tours)
    indiv_tours['tour_id_str'] = 'i' + indiv_tours['tour_id'].apply(str)
    print "Read %d individual auto tours" % len(indiv_tours)

    indiv_tours = pandas.merge(left=indiv_tours, right=persons, on=['hh_id','person_id'])
    assert(len(indiv_tours) == indiv_tours_participants)
    # print indiv_tours.head()

    ############ Read joint tours ############
    joint_tours   = pandas.read_table(os.path.join("main", "jointTourData_%d.csv" % iteration),
                                      sep=",", index_col=False)
    joint_tours   = joint_tours[['hh_id','tour_participants','tour_category','tour_id',
                                 'tour_purpose','orig_taz','dest_taz','start_hour','end_hour','tour_mode']]
    # Filter to auto tours
    joint_tours   = joint_tours.loc[(joint_tours.tour_mode>=1)&(joint_tours.tour_mode<=6)]
    joint_tours['num_participants'] = joint_tours.tour_participants.str.count(' ') + 1
    joint_tour_participants = joint_tours.num_participants.sum()
    joint_tours['tour_id_str'] = 'j' + joint_tours['tour_id'].apply(str)
    print "Read %d joint auto tours with %d num_participants" % (len(joint_tours), joint_tour_participants)

    # Split joint tours by space and give each its own row
    s           = joint_tours['tour_participants'].str.split(' ').apply(pandas.Series, 1).stack()
    s.index     = s.index.droplevel(-1)
    s.name      = 'person_num'
    s           = s.astype(int)  # no strings
    joint_tours = joint_tours.join(s)

    # Verify we have one row for each person-tour
    assert(len(joint_tours) == joint_tour_participants)

    # Join to persons to get person_id, fp_choice
    joint_tours = pandas.merge(left=joint_tours, right=persons,  on=['hh_id','person_num'])
    # Verify we didn't lose or add rows and that we found everyone's person id
    assert(len(joint_tours) == joint_tour_participants)
    assert(len(joint_tours.loc[pandas.notnull(joint_tours.person_id)] == joint_tour_participants))

    # drop tour_participants so we can merge
    joint_tours.drop('tour_participants', axis=1, inplace=True)
    assert(sorted(list(indiv_tours.columns.values)) == sorted(list(joint_tours.columns.values)))
    tours = pandas.concat([indiv_tours, joint_tours])

    # tour duration
    tours['tour_duration'] = tours.end_hour - tours.start_hour
    # origin county
    tours = pandas.merge(left=tours,         right=tazdata[['COUNTY']],
                         left_on='orig_taz', right_index=True)
    tours.rename(columns={'COUNTY':'orig_county'}, inplace=True)
    # destination county, parking costs
    tours = pandas.merge(left=tours,         right=tazdata,
                         left_on='dest_taz', right_index=True)
    tours.rename(columns={'COUNTY':'dest_county'}, inplace=True)
    assert(len(tours) == joint_tour_participants + indiv_tours_participants)

    # make sure this is a good index
    dupes = tours.duplicated(subset=['hh_id','person_id','person_num','tour_category','tour_purpose','tour_id'])
    assert(dupes.sum()==0)

    tours['tour_purpose2'] = tours.tour_purpose  # duplicate for index
    tours.set_index(['hh_id','person_id','person_num','tour_category','tour_purpose2','tour_id'], inplace=True)

    # default: tour_duration * OPRKCST
    tours['parking_cost']                                                  = tours.tour_duration*tours.OPRKCST
    # work, university and school use tours.PRKCST
    tours.loc[tours.tour_purpose.str.startswith('work'),   'parking_cost'] = tours.tour_duration*tours.PRKCST
    tours.loc[tours.tour_purpose.str.startswith('school'), 'parking_cost'] = tours.tour_duration*tours.PRKCST
    tours.loc[tours.tour_purpose=='university',            'parking_cost'] = tours.tour_duration*tours.PRKCST
    # some work tours have free parking
    # fp_choice: Integer, 1 - person will park for free; 2 -person will pay to park
    tours.loc[tours.tour_purpose.str.startswith('work')&tours.fp_choice==1, 'parking_cost'] = 0

    tours['parking_category']                                                = 'Non-Work'
    tours.loc[tours.tour_purpose.str.startswith('work'), 'parking_category'] = 'Work'
    print "Working tours with free parking: %d" % len(tours.loc[(tours.parking_category=='Work')&(tours.fp_choice==1)])

    # convert year 2000 cents to year 2000 dollars
    tours['parking_cost'] = 0.01*tours['parking_cost']
    # aggregate to origin/destination counties
    tours_by_od_county = tours[['parking_category','orig_county','dest_county','parking_cost']].groupby(['parking_category','orig_county','dest_county']).sum()

    tours_by_od_county.to_csv(os.path.join("metrics", "parking_costs.csv"),
                              header=True, index=True )