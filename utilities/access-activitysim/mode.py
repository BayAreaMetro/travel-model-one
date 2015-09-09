import os
import yaml

import orca
import pandas as pd
import yaml

from activitysim import activitysim as asim
from activitysim import skim as askim
from .util.mode import _mode_choice_spec

"""
Mode choice for work location choice here
"""

# define the relationship between the persons data and the land use data 
#   to get access to the destination-specific land use variables
orca.broadcast('persons', 'land_use', cast_index=True, onto_on='workplace_taz')

# merge the person and land use data
@orca.table()
def persons_merged(persons, land_use):
  return orca.merge_tables(persons.name, tables=[persons, land_use])

@orca.injectable()
def mode_choice_settings(configs_dir):
    with open(os.path.join(configs_dir,
                           "configs",
                           "tour_mode_choice.yaml")) as f:
        return yaml.load(f)


@orca.injectable()
def mode_choice_spec_df(configs_dir):
    with open(os.path.join(configs_dir,
                           "configs",
                           "tour_mode_choice.csv")) as f:
        return asim.read_model_spec(f)


@orca.injectable()
def mode_choice_coeffs(configs_dir):
    with open(os.path.join(configs_dir,
                           "configs",
                           "tour_mode_choice_coeffs.csv")) as f:
        return pd.read_csv(f, index_col='Expression')


@orca.injectable()
def mode_choice_spec(mode_choice_spec_df, mode_choice_coeffs,
                     mode_choice_settings):
    return _mode_choice_spec(mode_choice_spec_df, mode_choice_coeffs,
                             mode_choice_settings)


def _mode_choice_simulate(tours, skims, spec, additional_constants, omx=None):
    """
    This is a utility to run a mode choice model for each segment (usually
    segments are trip purposes).  Pass in the tours that need a mode,
    the Skim object, the spec to evaluate with, and any additional expressions
    you want to use in the evaluation of variables.
    """

    # create in-bound and out-bound skim objects
    in_skims = askim.Skims3D(skims.set_keys("home_taz", "workplace_taz"),
                             "in_period", -1)
    skims.set_keys("home_taz", "workplace_taz")

    if omx:
        in_skims.set_omx(omx)

    locals_d = {
        "in_skims": in_skims,
        "skims": skims
    }
    locals_d.update(additional_constants)

    choices, _ = asim.simple_simulate(tours,
                                      spec,
                                      skims=[in_skims, skims],
                                      locals_d=locals_d)

    alts = spec.columns
    choices = choices.map(dict(zip(range(len(alts)), alts)))

    return choices


def get_segment_and_unstack(spec, segment):
    """
    This does what it says.  Take the spec, get the column from the spec for
    the given segment, and unstack.  It is assumed that the last column of
    the multiindex is alternatives so when you do this unstacking,
    each alternative is in a column (which is the format this as used for the
    simple_simulate call.  The weird nuance here is the "Rowid" column -
    since many expressions are repeated (e.g. many are just "1") a Rowid
    column is necessary to identify which alternatives are actually part of
    which original row - otherwise the unstack is incorrect (i.e. the index
    is not unique)
    """
    return spec[segment].unstack().\
        reset_index(level="Rowid", drop=True).fillna(0)


@orca.step()
def mode_choice_simulate(persons_merged,
                         mode_choice_spec,
                         mode_choice_settings,
                         skims, omx_file):

    persons = persons_merged.to_frame()

    print mode_choice_spec.work

    # simulate decision for each person
    choices = _mode_choice_simulate(
        persons,
        skims,
        get_segment_and_unstack(mode_choice_spec, 'work'),
        mode_choice_settings['CONSTANTS'],
        omx=omx_file)

    print "Choices:\n", choices.value_counts()
    orca.add_column("persons", "mode", choices)
