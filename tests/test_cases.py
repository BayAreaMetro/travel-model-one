"""Tests for cases: expansion, addresses, and what each refuses.

The rules being pinned here are the ones that make a case safe to write without
reading the loader: an address has to already exist, a value replaces rather than
merges, a step in two blocks has to say which, and `steps` is off limits.  Each of
those failing silently would produce a run that completes and reports plausible
numbers for the wrong configuration.
"""

from pathlib import Path

import pytest
import yaml

from tm1.project import cases, overrides
from tm1.project.cases import Case, expand
from tm1.project.overrides import apply_case, resolve_address

#: Every project the repo ships, discovered rather than named, so adding, renaming or
#: retiring one needs no edit here.
PROJECTS = sorted((Path(__file__).parents[1] / "projects").glob("*/config.yaml"))

#: A config with the *shape* a project has and none of its content: top-level keys, an
#: `env:` block, a step with several entries, a `warmstart:` and an `iterate:` that
#: share a step name, a mapping-valued key, and a step that does not declare `enabled`.
#:
#: Deliberately synthetic.  What follows pins the override *mechanism*, so it must not
#: move when a real project's YAML changes: a project evolving is not a regression, and
#: a test that says otherwise only teaches people to edit the assertion until it passes.
#: The two tests that genuinely need a real project are at the bottom, and they assert
#: what is true of any valid one rather than what today's happens to say.
FIXTURE = """
slack: minimal
m_drive: "M:/models"

env:
  MODEL_YEAR: 2023
  EN7: DISABLED
  PATH: "C:/gawk;%PATH%"

steps:
  - copy_inputs:
      input_hwy:
        from: "M:/networks/hwy"
        to: "{run_dir}/INPUT/hwy"
      input_landuse:
        from: "M:/landuse"
        to: "{run_dir}/INPUT/landuse"

  - warmstart:
      - hwy_assign:
          job: "CTRAMP/scripts/assign/HwyAssign.job"
          cluster_nodes: 48

  - iterate:
      count: 3
      steps:
        - simulate_ctramp:
            threads: 24
            sample_rate:
              1: 0.15
              2: 0.30
              3: 0.50
        - hwy_assign:
            job: "CTRAMP/scripts/assign/HwyAssign.job"
            cluster_nodes: 48

  - skims_database:
      job: "CTRAMP/scripts/database/SkimsDatabase.job"
"""

#: Values FIXTURE declares, and the ones a case overrides them with.
EXPECTED_PROBLEMS = 2
FIXTURE_YEAR = 2023
HORIZON_YEAR = 2035
FIXTURE_NODES = 48
FEWER_NODES = 24
FEWER_THREADS = 12


@pytest.fixture
def cfg() -> dict:
    """The fixture config -- the thing addresses are written against."""
    return yaml.safe_load(FIXTURE)


# --------------------------------------------------------------------------- #
# Addresses
# --------------------------------------------------------------------------- #


def test_a_top_level_key(cfg: dict) -> None:
    """The simplest override there is, and it must not mutate the shared config."""
    out = apply_case(cfg, Case("A", overrides={"slack": "off"}))

    assert out["slack"] == "off"
    assert cfg["slack"] == "minimal", "the original must not be mutated"


def test_the_forecast_year(cfg: dict) -> None:
    """The commonest override there is.

    `MODEL_YEAR` lives in `env:` because that is what it is -- a variable the Cube jobs
    read from the environment -- so the address goes through the block rather than
    naming a top-level key.
    """
    out = apply_case(cfg, Case("A", overrides={"env.MODEL_YEAR": HORIZON_YEAR}))

    assert out["env"]["MODEL_YEAR"] == HORIZON_YEAR
    assert out["env"]["EN7"] == "DISABLED", "its siblings must survive"
    assert cfg["env"]["MODEL_YEAR"] == FIXTURE_YEAR, "the original must not be mutated"


def test_inside_a_top_level_mapping_keeps_its_siblings(cfg: dict) -> None:
    """`env.EN7` rather than replacing `env:`, which would drop PATH."""
    out = apply_case(cfg, Case("A", overrides={"env.EN7": "ENABLED"}))

    env = out["env"]
    assert env["EN7"] == "ENABLED"
    assert "PATH" in env


def test_inside_a_step(cfg: dict) -> None:
    """Repointing an input is the most common override there is."""
    out = apply_case(cfg, Case("A", overrides={
        "copy_inputs.input_landuse.from": "M:/elsewhere/landuse",
    }))

    entries = _step(out, "copy_inputs")
    assert entries["input_landuse"]["from"] == "M:/elsewhere/landuse"
    assert entries["input_hwy"]["from"].endswith("/hwy"), "siblings untouched"


def test_the_loops_own_key(cfg: dict) -> None:
    """`iterate.count` is the block's own key, not a step inside it."""
    out = apply_case(cfg, Case("A", overrides={"iterate.count": 1}))

    assert _block(out, "iterate")["count"] == 1


def test_a_step_inside_the_loop(cfg: dict) -> None:
    """Two implicit hops -- `steps:` then `iterate.steps:` -- neither written out."""
    out = apply_case(cfg, Case("A", overrides={
        "iterate.simulate_ctramp.threads": FEWER_THREADS,
    }))

    assert _in_block(out, "iterate", "simulate_ctramp")["threads"] == FEWER_THREADS


def test_the_same_step_in_the_warm_start(cfg: dict) -> None:
    """hwy_assign runs in both blocks; each carries its own config."""
    out = apply_case(cfg, Case("A", overrides={
        "warmstart.hwy_assign.cluster_nodes": FEWER_NODES,
    }))

    assert _in_block(out, "warmstart", "hwy_assign")["cluster_nodes"] == FEWER_NODES
    assert _in_block(out, "iterate", "hwy_assign")["cluster_nodes"] == FIXTURE_NODES


def test_a_bare_name_in_two_blocks_is_refused(cfg: dict) -> None:
    """Guessing would change a different round than the one meant."""
    with pytest.raises(ValueError, match="ambiguous"):
        resolve_address(cfg, "hwy_assign.cluster_nodes")


def test_an_unknown_address_names_the_closest_match(cfg: dict) -> None:
    """The typo that would otherwise run the default and say nothing."""
    with pytest.raises(KeyError, match="m_drive"):
        resolve_address(cfg, "m_drve")


def test_an_unknown_key_inside_a_step_names_the_closest_match(cfg: dict) -> None:
    """Deeper than the first segment, the suggestion comes from the step block."""
    with pytest.raises(KeyError, match="sample_rate"):
        resolve_address(cfg, "iterate.simulate_ctramp.sample_ratio")


def test_steps_itself_is_not_addressable(cfg: dict) -> None:
    """A case varies values; a different pipeline is a different project."""
    with pytest.raises(ValueError, match="not addressable"):
        resolve_address(cfg, "steps.0")


def test_a_value_replaces_rather_than_merges(cfg: dict) -> None:
    """The whole ramp, not one round of it -- naming a mapping replaces it."""
    out = apply_case(cfg, Case("A", overrides={
        "iterate.simulate_ctramp.sample_rate": {1: 0.05},
    }))

    assert _in_block(out, "iterate", "simulate_ctramp")["sample_rate"] == {1: 0.05}


def test_an_int_keyed_mapping_is_not_addressable_below_itself(cfg: dict) -> None:
    """`sample_rate:` is keyed by round number, so `.1` matches no string key."""
    with pytest.raises(KeyError):
        resolve_address(cfg, "iterate.simulate_ctramp.sample_rate.1")


def test_enabled_may_be_set_on_a_step_that_does_not_declare_it(cfg: dict) -> None:
    """The one universal key: an optional step is switched off by the case."""
    out = apply_case(cfg, Case("A", overrides={"skims_database.enabled": False}))

    assert _step(out, "skims_database")["enabled"] is False


def test_any_other_new_key_is_still_refused(cfg: dict) -> None:
    """`enabled` is the only universal key; everything else must already exist."""
    with pytest.raises(KeyError):
        resolve_address(cfg, "skims_database.invented_key")


# --------------------------------------------------------------------------- #
# Expansion
# --------------------------------------------------------------------------- #


def test_an_explicit_case_with_no_overrides_is_the_config_as_written(cfg: dict) -> None:
    """The degenerate case: a project with one empty case runs config.yaml."""
    out = expand({"cases": {"BASE-2023": None}})

    assert [c.id for c in out.cases] == ["BASE-2023"]
    assert apply_case(cfg, out.cases[0]) == cfg


def test_a_ladder_accumulates_its_rungs() -> None:
    """Rung k carries rungs 1..k, so its diff against k-1 isolates one change."""
    out = expand({"ladder": [{
        "id": "L1-{n}-{rung}-2035",
        "model_year": 2035,
        "rungs": [
            {"TRNF": {"description": "Transit frequency.", "env.EN7": "ENABLED"}},
            {"CORD": {"description": "Cordon pricing.", "set_tolls.job": "v/cordon.job"}},
        ],
    }]})

    assert [c.id for c in out.cases] == ["L1-01-TRNF-2035", "L1-02-CORD-2035"]
    assert out.cases[0].overrides == {"model_year": 2035, "env.EN7": "ENABLED"}
    assert out.cases[1].overrides == {
        "model_year": 2035, "env.EN7": "ENABLED", "set_tolls.job": "v/cordon.job",
    }
    assert "Transit frequency; Cordon pricing." in out.cases[1].description


def test_a_matrix_is_the_cross_product_minus_exclusions() -> None:
    """And the exclusions are reported, not silently dropped from the count."""
    out = expand({"matrix": [{
        "id": "A1-{tolls}-{landuse}",
        "axes": {
            "tolls": {"NOTL": None, "CORD": {"set_tolls.job": "v/cordon.job"}},
            "landuse": {"ADPT": None, "JHBL": {"model_year": 2035}},
        },
        "exclude": [{"tolls": "CORD", "landuse": "JHBL"}],
    }]})

    assert [c.id for c in out.cases] == [
        "A1-NOTL-ADPT", "A1-NOTL-JHBL", "A1-CORD-ADPT",
    ]
    assert out.excluded == [{"tolls": "CORD", "landuse": "JHBL"}]


def test_adding_an_axis_value_does_not_rename_existing_cases() -> None:
    """Name stability is correctness: a renamed case is an unrun case."""
    spec = {"id": "A1-{tolls}", "axes": {"tolls": {"NOTL": None, "CORD": None}}}
    before = {c.id for c in expand({"matrix": [spec]}).cases}

    spec["axes"]["tolls"]["HIGH"] = None
    after = {c.id for c in expand({"matrix": [spec]}).cases}

    assert before < after


def test_an_exclusion_may_name_a_subset_of_the_axes() -> None:
    """So it survives a new axis being added, rather than silently stopping."""
    out = expand({"matrix": [{
        "id": "A1-{a}-{b}",
        "axes": {"a": {"X": None, "Y": None}, "b": {"P": None, "Q": None}},
        "exclude": [{"a": "Y"}],
    }]})

    assert [c.id for c in out.cases] == ["A1-X-P", "A1-X-Q"]


def test_a_generated_id_colliding_with_an_explicit_one_is_refused() -> None:
    """An ID names a run directory, so a collision would merge two runs."""
    with pytest.raises(ValueError, match="collides"):
        expand({
            "cases": {"A1-NOTL": None},
            "matrix": [{"id": "A1-{tolls}", "axes": {"tolls": {"NOTL": None}}}],
        })


@pytest.mark.parametrize("bad", ["a001-nopk", "A001_NOPK", "A001 NOPK"])
def test_a_malformed_id_is_refused(bad: str) -> None:
    """IDs read as identifiers, not prose -- and not as two names differing by case."""
    with pytest.raises(ValueError, match="uppercase segments"):
        expand({"cases": {bad: None}})


def test_a_trailing_three_digit_segment_is_refused() -> None:
    """It would be ambiguous with the run-iteration suffix on a run directory."""
    with pytest.raises(ValueError, match="run-iteration"):
        expand({"cases": {"A001-NOPK-035": None}})


def test_an_unknown_pathway_is_refused_by_name() -> None:
    """A config written for a removed spelling must fail rather than do nothing."""
    with pytest.raises(ValueError, match="three pathways"):
        expand({"scenarios": {"A": None}})


# --------------------------------------------------------------------------- #
# Validation across the whole project
# --------------------------------------------------------------------------- #


def test_validate_reports_every_case_not_just_the_first(cfg: dict) -> None:
    """A bundle is queued and left; finding case 27's typo at hour 40 is the point."""
    expansion = expand({"cases": {
        "A-ONE": {"m_drve": "X:/"},
        "A-TWO": {"iterate.simulate_ctramp.sample_ratio": 0.5},
        "A-GOOD": {"env.MODEL_YEAR": 2035},
    }})

    problems = overrides.validate(cfg, expansion)

    assert len(problems) == EXPECTED_PROBLEMS
    assert any(p.startswith("A-ONE") for p in problems)
    assert any(p.startswith("A-TWO") for p in problems)


@pytest.mark.parametrize("config_path", PROJECTS, ids=lambda p: p.parent.name)
def test_every_shipped_project_validates(config_path: Path) -> None:
    """Whatever a project's cases.yaml declares must resolve against its config.yaml.

    The only test here that reads a real project, and it asserts nothing about what
    that project *says* -- just that its cases resolve.  So editing a config or a
    case cannot break it; writing an address that does not exist can, which is the
    whole point.
    """
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    expansion = cases.load(config_path.parent)

    assert expansion.cases, "a project declares at least one case"
    assert overrides.validate(cfg, expansion) == []


def test_at_least_one_project_ships() -> None:
    """Guards the discovery above: a bad glob would silently test nothing."""
    assert PROJECTS


# --------------------------------------------------------------------------- #


def _step(cfg: dict, name: str) -> dict:
    return next(s[name] for s in cfg["steps"] if isinstance(s, dict) and name in s)


def _block(cfg: dict, name: str) -> dict:
    return _step(cfg, name)


def _in_block(cfg: dict, block: str, step: str) -> dict:
    entries = _block(cfg, block)
    steps = entries["steps"] if block == "iterate" else entries
    return next(s[step] for s in steps if isinstance(s, dict) and step in s)
