import os
import orca

from activitysim import activitysim as asim
# from .util.misc import add_dependent_columns

def add_dependent_columns(base_dfname, new_dfname):
    tbl = orca.get_table(new_dfname)
    for col in tbl.columns:
        print "Adding", col
        orca.add_column(base_dfname, col, tbl[col])


"""
The workplace location model predicts the zones in which various people will
work.
"""


@orca.injectable()
def workplace_location_spec(configs_dir):
    f = os.path.join(configs_dir, 'configs', "workplace_location.csv")
    return asim.read_model_spec(f).fillna(0)


@orca.step()
def workplace_location_simulate(set_random_seed,
                                persons,
                                workplace_location_spec,
                                skims,
                                destination_size_terms):

    # for accessibility, simulate for all persons
    choosers = persons.to_frame()
    alternatives = destination_size_terms.to_frame()

    # set the keys for this lookup - in this case there is a TAZ in the choosers
    # and a TAZ in the alternatives which get merged during interaction
    skims.set_keys("home_taz", "destination_taz")
    # the skims will be available under the name "skims" for any @ expressions
    locals_d = {"skims": skims}

    choices, _ = asim.interaction_simulate(choosers,
                                           alternatives,
                                           workplace_location_spec,
                                           skims=skims,
                                           locals_d=locals_d,
                                           sample_size=50)

    choices = choices.reindex(persons.index)

    print "Describe of choices:\n", choices.describe()
    orca.add_column("persons", "workplace_taz", choices)

    add_dependent_columns("persons", "persons_workplace")
