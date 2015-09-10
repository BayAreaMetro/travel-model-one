import os
import copy
import string
import yaml

import orca
import pandas as pd
import yaml

from activitysim import activitysim as asim
from activitysim import skim as askim

"""
Mode choice for work location choice here
"""

# define the relationship between the persons data and the land use data 
#   to get access to the destination-specific land use variables
orca.broadcast('land_use', 'persons', cast_index=True, onto_on='workplace_taz')

# merge the person and land use data, including only the relevant columns
@orca.table()
def persons_merged(persons, land_use):
  return orca.merge_tables(persons.name, tables=[persons, land_use], columns = ['TERMINAL', 'PRKCST', 'TOPOLOGY', 'TOTHH', 'TOTEMP', 'TOTACRE'])

# _mode_choice_spec is from .util.mode -- bring in here for now
def _mode_choice_spec(mode_choice_spec_df, mode_choice_coeffs,
                      mode_choice_settings):
    """
    Ok we have read in the spec - we need to do several things to reformat it
    to the same style spec that all the other models have.

    mode_choice_spec_df : DataFrame
        This is the actual spec DataFrame, the same as all of the other spec
        dataframes, except that 1) expressions can be prepended with a "$"
        - see pre_process_expressions above 2) There is an Alternative column -
        see expand_alternatives above and 3) there are assumed to be
        expressions in the coefficient column which get evaluated by
        evaluate_expression_list above
    mode_choice_coeffs : DataFrame
        This has the same columns as the spec (columns are assumed to be
        independent segments of the model), and the coefficients (values) in
        the spec DataFrame refer to values in the mode_choice_coeffs
        DataFrame.  The mode_choice_coeffs DataFrame can also contain
        expressions which refer to previous rows in the same column.  Is is
        assumed that all values in mode_choice_coeffs can be cast to float
        after running evaluate_expression_list, and that these floats are
        substituted in multiple place in the mode_choice_spec_df.
    mode_choice_settings : Dict, usually read from YAML
        Has two values which are used.  One key in CONSTANTS which is used as
        the scope for the evals which take place here and one that is
        VARIABLE_TEMPLATES which is used as the scope for expressions in
        mode_choice_spec_df which are prepended with "$"

    Returns
    -------
    new_spec_df : DataFrame
        A new spec DataFrame which is exactly like all of the other models.
    """

    constants = mode_choice_settings['CONSTANTS']
    templates = mode_choice_settings['VARIABLE_TEMPLATES']
    df = mode_choice_spec_df
    index_name = df.index.name

    # the expressions themselves can be prepended with a "$" in order to use
    # model templates that are shared by several different expressions
    df.index = pre_process_expressions(df.index, templates)
    df.index.name = index_name

    df = df.set_index('Alternative', append=True)

    # for each segment - e.g. eatout vs social vs work vs ...
    for col in df.columns:

        # first the coeffs come as expressions that refer to previous cells
        # as well as constants that come from the settings file
        mode_choice_coeffs[col] = evaluate_expression_list(
            mode_choice_coeffs[col],
            constants=constants)

        # then use the coeffs we just evaluated within the spec (they occur
        # multiple times in the spec which is why they get stored uniquely
        # in a different file
        df[col] = evaluate_expression_list(
            df[col],
            mode_choice_coeffs[col].to_dict())

    df = expand_alternatives(df)

    return df

# pre_process_expressions is from .util.mode -- bring in here for now
def pre_process_expressions(expressions, variable_templates):
    """
    This one is pretty simple - pass in a list of expressions which contain
    references to templates and pass a dictionary of the templates themselves.
    Strings will only be evaluated which are prepended with $.

    Parameters
    ----------
    expressions : list of strs
        These are the expressions that will be evaluated - generally these
        contain templates that get passed below.  So will be something like
        ['$SKIM_TEMPLATE.format(sk="AMPEAK")']
    variable_templates : dict of templates
        Will be passed as the scope of eval.  Keys are usually template names
        and values are strings.  The dict could be something like
        {'SKIM_TEMPLATE': 'skims[{sk}]'}

    Returns
    -------
    expressions : list of strs
        Each expression is evaluated with variable_templates in the scope and
        the result is returned.
    """
    return [eval(e[1:], variable_templates) if e.startswith('$') else e for
            e in expressions]

# evaluate_expression_list is from .util.mode -- bring in here for now
def evaluate_expression_list(expressions, constants):
    """
    Evaluate a list of expressions - each one can depend on the one before
    it.  These are usually used for the coefficients which have relationships
    to each other.  So ivt=.7 and then ivt_lr=ivt*.9.

    Parameters
    ----------
    expressions : Series
        Same as below except the values are accumulated from expression to
        expression and there is no assumed "$" at the beginning.  This is a
        Series because the index are the names of the expressions which are
        used in subsequent evals - thus naming the expressions is required.
        For better or worse, the expressions are assumed to evaluate to
        floats and this is guaranteed by casting to float after eval-ing.
    constants : dict
        will be passed as the scope of eval - usually a separate set of
        constants are passed in here

    Returns
    -------
    expressions : Series

    """
    d = {}
    # this could be a simple expression except that the dictionary
    # is accumulating expressions - i.e. they're not all independent
    # and must be evaluated in order
    for k, v in expressions.iteritems():
        # make sure it can be converted to a float
        d[k] = float(eval(str(v), copy.copy(d), constants))
    return pd.Series(d)

# expand_alternatives is from .util.mode -- bring in here for now
def expand_alternatives(df):
    """
    Alternatives are kept as a comma separated list.  At this stage we need
    need to split them up so that there is only one alternative per row, and
    where an expression is shared among alternatives, that row is copied
    with each alternative alternative value (pun intended) substituted for
    the alternative value for each row.  The DataFrame needs an Alternative
    column which is a comma separated list of alternatives.  See the test for
    an example.
    """

    # first split up the alts using string.split
    alts = [string.split(s, ",") for s in df.reset_index()['Alternative']]

    # this is the number of alternatives in each row
    len_alts = [len(x) for x in alts]

    # this repeats the locs for the number of alternatives in each row
    ilocs = np.repeat(np.arange(len(df)), len_alts)

    # grab the rows the right number of times (after setting a rowid)
    df['Rowid'] = np.arange(len(df))
    df = df.iloc[ilocs]

    # now concat all the lists
    new_alts = sum(alts, [])

    df.reset_index("Alternative", inplace=True)
    df["Alternative"] = new_alts
    # rowid needs to bet set here - we're going to unstack this and we need
    # a unique identifier to keep track of the rows during the unstack
    df = df.set_index(['Rowid', 'Alternative'], append=True)

    return df

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
                         skims,
                         mode_choice_spec,
                         mode_choice_settings):

    tours = persons_merged.to_frame()

    print mode_choice_spec.work

    # simulate decision for each person
    choices = _mode_choice_simulate(
        tours,
        skims,
        get_segment_and_unstack(mode_choice_spec, 'work'),
        mode_choice_settings['CONSTANTS'])

    print "Choices:\n", choices.value_counts()
    orca.add_column("persons", "mode", choices)
