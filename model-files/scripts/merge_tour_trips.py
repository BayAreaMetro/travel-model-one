###
USAGE = r"""
Post-processes outputs of tour and trips data and consolidates them into one file
Joint tours and trips are disaggregated into joint-person tour/trips
Usage:
    python merge_tour_trips.py <ITER>
"""
# Script to combine individual tour/trip and joint tour/trip as one file
# Look at how I did it for TM2/follow current post-processing scripts as well
# Essentially just a function that will read both trip and tours?
# Also include a column that'll specify if its joint or not (joint_id?)


import pandas as pd
import argparse
import pathlib

person_type = {
    1: "Full-time worker",
    2: "Part-time worker",
    3: "University student",
    4: "Non-worker",
    5: "Retired",
    6: "Student of driving age",
    7: "Student of non-driving age",
    8: "Child too young for school"
}

def format_joint_tour_trip(
        joint_tour_file,
        joint_trip_file,
        person_file
):
    """Format joint tour and trips to person-tour/person-trip"""
    joint_tour = pd.read_csv(joint_tour_file)
    joint_trip = pd.read_csv(joint_trip_file)
    person = pd.read_csv(person_file, usecols = ["hh_id", "person_id", "person_num", "type"])

    # Converting person type from label to key
    person["person_type"] = person["type"].map({v: k for k, v in person_type.items()})
    person = person.drop(columns = ["type"])

    # Creating joint tour id as hh_id + tour_id
    joint_tour["joint_tour_id"] = (joint_tour["hh_id"].astype(str) + joint_tour["tour_id"].astype(str)).astype(int)

    # Creating joint trip id as hh_id + tour_id + incremental stop id
    joint_trip["stop_id_incr"] = joint_trip.groupby(["hh_id", "tour_id"]).cumcount()
    joint_trip["joint_trip_id"] = (joint_trip["hh_id"].astype(str) + 
                                   joint_trip["tour_id"].astype(str) + 
                                   joint_trip["stop_id_incr"].astype(str)).astype(int)
    joint_trip = joint_trip.drop(columns = ["stop_id_incr"])

    joint_tour["person_num"] = joint_tour["tour_participants"].str.split(" ")
    joint_tour["num_participants"] = joint_tour["person_num"].str.len()
    joint_tour = joint_tour.drop(columns = ["tour_participants"])
    joint_persons = joint_tour.explode("person_num")
    joint_persons["person_num"] = joint_persons["person_num"].astype(int)

    # Merge on person to get person_id
    joint_person_tour = pd.merge(joint_persons, person, on = ["hh_id", "person_num"], how = "left", validate = "many_to_one")

    # Joining joint_person_tour 
    # This is a many to many inner join since we are unwinding joint trips by persons on the trip. Each joint trip becomes a row per participant
    joint_person_trip = pd.merge(joint_trip, 
                                 joint_person_tour[["joint_tour_id", "hh_id", "tour_id", "person_num", "person_id"]], 
                                 on= ['hh_id', 'tour_id'], 
                                 how = 'inner', 
                                 suffixes = (None, "_right"), 
                                 validate = 'many_to_many')

    return joint_person_tour, joint_person_trip

def format_indiv_tour_trip(
        indiv_tour_file,
        indiv_trip_file
):
    indiv_tour = pd.read_csv(indiv_tour_file)
    indiv_trip = pd.read_csv(indiv_trip_file)
    indiv_tour["num_participants"] = 1
    indiv_trip["num_participants"] = 1

    return indiv_tour, indiv_trip

def format_all_tours_trips(
        indiv_tour_file,
        indiv_trip_file,
        joint_tour_file,
        joint_trip_file,
        person_file
):
    """Joining all tours and trips together and returns all tours and all trips dataframe"""
    indiv_tour, indiv_trip = format_indiv_tour_trip(indiv_tour_file, indiv_trip_file)

    joint_tour, joint_trip = format_joint_tour_trip(joint_tour_file, joint_trip_file, person_file)

    all_tours = pd.concat([indiv_tour, joint_tour], ignore_index=True, join = "outer")

    all_trips = pd.concat([indiv_trip, joint_trip], ignore_index = True, join = "outer")

    return all_tours, all_trips


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = USAGE,
                                         formatter_class=argparse.RawDescriptionHelpFormatter)
    
    parser.add_argument("--iter",
                        help="Iteration for which to configure.  If not specified, will configure for pre-run.",
                        type=int, choices=[1,2,3])
    my_args = parser.parse_args()

    ITER = my_args.iter
    print(f"ITER = {ITER}")
    SIMULATION_MAIN_DIR = pathlib.Path("main")

    print("Merging individual and joint tours and trips")
    indiv_tour_file = SIMULATION_MAIN_DIR / f"indivTourData_{ITER}.csv"
    indiv_trip_file = SIMULATION_MAIN_DIR / f"indivTripData_{ITER}.csv"
    joint_tour_file = SIMULATION_MAIN_DIR / f"jointTourData_{ITER}.csv"
    joint_trip_file =  SIMULATION_MAIN_DIR / f"jointTripData_{ITER}.csv"
    person_file = SIMULATION_MAIN_DIR / f"personData_{ITER}.csv"
    
    all_tours, all_trips = format_all_tours_trips(
        indiv_tour_file,
        indiv_trip_file,
        joint_tour_file,
        joint_trip_file,
        person_file
    )

    all_tours.to_csv(SIMULATION_MAIN_DIR/ f"AllTours_{ITER}.csv", index= False)
    all_trips.to_csv(SIMULATION_MAIN_DIR / f"AllTrips_{ITER}.csv", index = False)


