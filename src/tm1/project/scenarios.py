"""The runs a project defines, and how each one differs from the shared model.

The shared ``default-configs/ctramp-cube-model.yaml`` is the full pipeline with
its placeholder values. A **scenario** is a named set of overrides on it. A
project states them across files, all read from its directory, each named for
what it holds so none needs a wrapper key to say so:

``steps.yaml``
    optional; a project's own pre/post-processing hooks (``script:``/``module:``)
    that the shared model has no name for, appended once after the shared
    pipeline's own steps, for every scenario alike. Genuinely project-wide,
    unlike an override: every scenario runs the same pipeline shape, so there is
    nothing to state per scenario.
``scen_*.yaml``
    at least one; explicit scenarios, one entry per run, written out as
    ``SCENARIO_ID: {overrides}`` directly at the top level -- no ``scenarios:``
    wrapper. Each names a slice however a reader wants them grouped -- a model
    year, a Plan/NoProject pair, whatever reads best split up.
``ladder*.yaml``
    optional; cumulative scenarios -- rung k applies rungs 1..k, for isolating
    one intervention's contribution against its predecessor -- a top-level
    list of ladder specs (``id:``, ``rungs:``, ...), no ``ladder:`` wrapper.
``matrix*.yaml``
    optional; the cross product of named axes, minus ``exclude:``
    combinations -- a top-level list of matrix specs (``id:``, ``axes:``,
    ...), no ``matrix:`` wrapper.

Every file matching one of these globs is merged into one expansion before
anything is checked, so an ID collision or an unresolved placeholder is caught
across the whole project, not just the file that introduced it. All three
scenario pathways expand to the same flat list, so there is one code path and
one set of rules.

There is no project-level defaults layer: each scenario states its own full set
of overrides, including the ones every scenario in the project happens to share
(``m_drive``-style values, its data sources, its base ``model_year``). Restating
them is the cost of every scenario being readable on its own, without also
reading a separate block to know what an apparently-empty scenario actually
runs. The shared model every project inherits is :mod:`tm1.project.config`;
:func:`tm1.project.overrides.validate` refuses a scenario that leaves one of the
shared model's ``REQUIRED`` placeholders unresolved.

This module *enumerates* scenarios. Applying one to a config -- and checking that
its addresses resolve -- is :mod:`tm1.project.overrides`.

Scenario IDs
------------
``YEAR_MODELVERSION_SERIES_SCENARIO_VERSION`` -- ``2050_TM161_FBP_Plan_16`` --
unique within the project and stable forever, because the ID names the run
directory: a renamed scenario is an unrun scenario, and that is fifteen hours.
``description:`` carries the prose.
Ladder and matrix generate IDs from an ``id:`` template whose tokens are their
part names, so adding a matrix axis value never renames an existing scenario.
Ladder IDs carry the rung index and *do* shift when a rung is inserted --
correctly, since that changes what every downstream rung means.
"""

import itertools
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

#: A scenario ID: segments of letters, digits, underscores or hyphens -- case is
#: preserved, so a multi-part last segment may be camelCase.  Two IDs differing
#: only by case still collide (see _check_id): the run directory they name is
#: the same one on a filesystem that does not distinguish them.
_ID = re.compile(r"^[A-Za-z0-9_]+(-[A-Za-z0-9_]+)*$")

#: A trailing three-digit segment would be ambiguous with the run-iteration suffix
#: a run directory carries (``A001-NOPK-2035_001``).
_ID_TAIL = re.compile(r"_[0-9]{3}$")

#: ``{token}`` in an ``id:`` template.
_TOKEN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

#: A project's own pipeline additions, alongside the scenario files below.
_STEPS_FILE = "steps.yaml"

#: Explicit scenarios: one file per group a reader wants open at once (a model
#: year, a Plan/NoProject pair, ...) -- not one file per pathway. No
#: `scenarios:` wrapper: the filename already says what it holds, so a
#: scenario ID is written directly at the top level. All matches are merged
#: into one expansion, so an ID collision is caught across the whole project.
#: Public: it is also how :mod:`tm1.cli` recognises a directory as a project.
SCENARIO_GLOB = "scen_*.yaml"

#: Ladder scenarios: a top-level list of ladder specs (``id:``, ``rungs:``,
#: ...), no `ladder:` wrapper -- same reasoning as :data:`SCENARIO_GLOB`.
#: Optional: most projects need no ladder at all.
LADDER_GLOB = "ladder*.yaml"

#: Matrix scenarios: a top-level list of matrix specs (``id:``, ``axes:``,
#: ...), no `matrix:` wrapper -- same reasoning as :data:`SCENARIO_GLOB`.
#: Optional: most projects need no matrix at all.
MATRIX_GLOB = "matrix*.yaml"

#: Keys a scen_*.yaml file must not use as a scenario ID -- each belongs in a
#: different file instead, named for what it holds.
_FORBIDDEN_SCENARIO_KEYS = {
    "scenarios": "name scenarios directly at the top level -- no `scenarios:` wrapper needed.",
    "steps": "project steps belong in steps.yaml, not a scen_*.yaml file.",
    "ladder": f"ladder scenarios belong in a {LADDER_GLOB} file, not a scen_*.yaml file.",
    "matrix": f"matrix scenarios belong in a {MATRIX_GLOB} file, not a scen_*.yaml file.",
}


def _read_yaml(path: Path) -> object:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def pairs(steps: object) -> list[tuple[str, object]]:
    """An ordered block written either way, as ``(name, value)`` pairs.

    Both project files use the shape: a mapping, or a list of single-key
    mappings.  ``steps:`` needs the list form to name a step twice; ladder
    ``rungs:`` need it to stay ordered.

    The value is handed back as it is written, not coerced: ``iterate:`` is a
    *mapping* (``count``, ``steps``), and its own ``steps:`` may itself be a list
    or a mapping, so flattening either to a dict here would lose the block.
    """
    if isinstance(steps, dict):
        return [(str(k), v) for k, v in steps.items()]
    if isinstance(steps, list):
        out: list[tuple[str, object]] = []
        for item in steps:
            if isinstance(item, dict) and len(item) == 1:
                k, v = next(iter(item.items()))
                out.append((str(k), v))
        return out
    return []


@dataclass
class Scenario:
    """One run: an ID, what it is, and how it differs from the shared model."""

    id: str
    description: str = ""
    #: address -> value, applied in declaration order.
    overrides: dict[str, object] = field(default_factory=dict)
    #: axis or rung name -> token, for display and ``--select``.
    tokens: dict[str, str] = field(default_factory=dict)
    #: Where it came from: ``scenarios``, ``ladder:<id>``, ``matrix:<id>``.
    source: str = "scenarios"


def _check_id(scenario_id: str, seen: dict[str, str], source: str) -> None:
    """Refuse a malformed ID, or one that collides with a scenario already made."""
    if not _ID.match(scenario_id):
        msg = (
            f"Scenario ID {scenario_id!r} ({source}): use segments of letters, "
            f"digits, underscores or hyphens, e.g. A001-NOPK-2035 or "
            f"2050_TM161_FBP_Plan_16."
        )
        raise ValueError(msg)
    if _ID_TAIL.search(scenario_id):
        msg = (
            f"Scenario ID {scenario_id!r} ({source}): a trailing three-digit "
            f"segment is ambiguous with the run-iteration suffix a run directory "
            f"carries."
        )
        raise ValueError(msg)
    folded = scenario_id.upper()
    if folded in seen:
        msg = (
            f"Scenario ID {scenario_id!r} ({source}) collides with "
            f"{seen[folded]}: run directories are case-insensitive on Windows, "
            f"so IDs differing only by case would land in the same folder."
        )
        raise ValueError(msg)
    seen[folded] = f"{scenario_id} ({source})"


def _split_meta(entry: object) -> tuple[str, dict]:
    """``description:`` off the front of an override table."""
    if entry is None:
        return "", {}
    if not isinstance(entry, dict):
        msg = f"A scenario must be a mapping of address: value; got {entry!r}."
        raise TypeError(msg)
    body = dict(entry)
    return str(body.pop("description", "") or "").strip(), body


def _render(template: str, tokens: dict[str, str], where: str) -> str:
    """An ``id:`` template with its tokens substituted."""
    missing = [t for t in _TOKEN.findall(template) if t not in tokens]
    if missing:
        msg = (
            f"{where}: id template {template!r} uses {', '.join(missing)}, which "
            f"is not an axis or rung name here."
        )
        raise ValueError(msg)
    return _TOKEN.sub(lambda m: tokens[m.group(1)], template)


def _expand_ladder(spec: dict, seen: dict[str, str]) -> list[Scenario]:
    """Cumulative scenarios: rung k carries rungs 1..k, in order."""
    template = str(spec.get("id") or "")
    if not template:
        msg = 'A ladder needs an `id:` template, e.g. "L1-{n}-{rung}-2035".'
        raise ValueError(msg)
    prose = str(spec.get("description", "") or "").strip()
    shared = {
        k: v for k, v in spec.items()
        if k not in {"id", "description", "rungs"}
    }

    rungs = pairs(spec.get("rungs"))
    scenarios: list[Scenario] = []
    cumulative: dict[str, object] = dict(shared)
    applied: list[str] = []
    for index, (name, body) in enumerate(rungs, start=1):
        rung_prose, overrides = _split_meta(body)
        cumulative.update(overrides)
        # Trailing stops are dropped so the joined list reads as one sentence
        # rather than as prose with its own punctuation embedded.
        applied.append((rung_prose or name).rstrip("."))
        tokens = {"n": f"{index:02d}", "rung": name}
        scenario_id = _render(template, tokens, f"ladder {template!r}")
        _check_id(scenario_id, seen, f"ladder rung {index}")
        scenarios.append(Scenario(
            id=scenario_id,
            # The description names everything the rung carries, because that is
            # what the run *is* -- a reader should not have to count backwards.
            description=" ".join(filter(None, [
                prose, "Cumulative through: " + "; ".join(applied) + ".",
            ])),
            overrides=dict(cumulative),
            tokens=dict(tokens),
            source=f"ladder:{template}",
        ))
    return scenarios


def _expand_matrix(spec: dict, seen: dict[str, str]) -> tuple[list[Scenario], list[dict]]:
    """The cross product of the axes, minus excluded combinations."""
    template = str(spec.get("id") or "")
    if not template:
        msg = 'A matrix needs an `id:` template, e.g. "A1-{tolls}-{landuse}".'
        raise ValueError(msg)
    prose = str(spec.get("description", "") or "").strip()
    shared = {
        k: v for k, v in spec.items()
        if k not in {"id", "description", "axes", "exclude"}
    }

    axes = spec.get("axes") or {}
    if not isinstance(axes, dict) or not axes:
        msg = f"matrix {template!r}: `axes:` must name at least one axis."
        raise TypeError(msg)
    names = list(axes)
    points = [list((axes[a] or {}).items()) for a in names]

    excluded: list[dict] = []
    scenarios: list[Scenario] = []
    for combo in itertools.product(*points):
        tokens = {axis: str(token) for axis, (token, _) in zip(names, combo, strict=True)}
        if any(_matches(tokens, rule) for rule in spec.get("exclude") or []):
            excluded.append(dict(tokens))
            continue
        overrides = dict(shared)
        parts: list[str] = []
        for _axis, (_token, body) in zip(names, combo, strict=True):
            point_prose, point_overrides = _split_meta(body)
            overrides.update(point_overrides)
            if point_prose:
                parts.append(point_prose)
        scenario_id = _render(template, tokens, f"matrix {template!r}")
        _check_id(scenario_id, seen, f"matrix {template}")
        scenarios.append(Scenario(
            id=scenario_id,
            description=" ".join(filter(None, [prose, " ".join(parts)])),
            overrides=overrides,
            tokens=tokens,
            source=f"matrix:{template}",
        ))
    return scenarios, excluded


def _matches(tokens: dict[str, str], rule: object) -> bool:
    """Whether a combination matches a partial ``exclude:`` spec.

    Partial on purpose: naming a subset of axes drops every scenario containing
    it, so an exclusion survives a new axis being added.
    """
    if not isinstance(rule, dict):
        msg = f"`exclude:` entries must be mappings of axis: token; got {rule!r}."
        raise TypeError(msg)
    return all(tokens.get(str(a)) == str(t) for a, t in rule.items())


@dataclass
class Expansion:
    """Every scenario a project defines, and what its matrices dropped."""

    scenarios: list[Scenario] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)
    #: `steps:` -- this project's own pipeline additions, appended once after
    #: the shared pipeline's own steps, for every scenario alike.
    extra_steps: list = field(default_factory=list)

    def by_id(self, scenario_id: str) -> Scenario | None:
        """One scenario by ID, matched case-insensitively."""
        folded = scenario_id.upper()
        return next((c for c in self.scenarios if c.id.upper() == folded), None)


def expand(scenarios_cfg: object) -> Expansion:
    """Every pathway a project's scenario files declare, expanded to a flat list."""
    if scenarios_cfg is None:
        return Expansion()
    if not isinstance(scenarios_cfg, dict):
        msg = (
            "A project's scenario config must be a mapping with `scenarios:`, "
            "`ladder:`, `matrix:` or `steps:`."
        )
        raise TypeError(msg)

    unknown = sorted(set(scenarios_cfg) - {"steps", "scenarios", "ladder", "matrix"})
    if unknown:
        msg = (
            f"A project's scenario config declares {', '.join(unknown)}; recognised "
            f"keys are `steps:` (this project's own pipeline additions) plus the "
            f"three pathways: `scenarios:` (explicit), `ladder:` (cumulative) and "
            f"`matrix:` (cross product)."
        )
        raise ValueError(msg)

    seen: dict[str, str] = {}
    out = Expansion(extra_steps=list(scenarios_cfg.get("steps") or []))

    for scenario_id, entry in (scenarios_cfg.get("scenarios") or {}).items():
        _check_id(str(scenario_id), seen, "scenarios")
        prose, overrides = _split_meta(entry)
        out.scenarios.append(Scenario(str(scenario_id), prose, overrides, source="scenarios"))

    for spec in scenarios_cfg.get("ladder") or []:
        out.scenarios += _expand_ladder(spec, seen)

    for spec in scenarios_cfg.get("matrix") or []:
        scenarios, excluded = _expand_matrix(spec, seen)
        out.scenarios += scenarios
        out.excluded += excluded

    return out


def load(config_dir: Path) -> Expansion:
    """Expand a project's scenario files from *config_dir*.

    ``steps.yaml`` (optional) holds this project's own pipeline additions, read
    once. ``scen_*.yaml`` (at least one, required), ``ladder*.yaml`` (optional)
    and ``matrix*.yaml`` (optional) each hold a slice of one pathway, grouped
    however a reader wants them open at once -- not one pathway necessarily in
    one file. Every matching file is merged into one config before
    :func:`expand` sees any of it, so a scenario ID declared twice is caught
    naming both files, not silently overwritten by whichever sorts last.
    """
    config_dir = Path(config_dir)

    extra_steps: list = []
    steps_path = config_dir / _STEPS_FILE
    if steps_path.is_file():
        extra_steps = _read_yaml(steps_path) or []
        if not isinstance(extra_steps, list):
            msg = f"{steps_path} must be a list of steps, e.g. `- vmt_vht_metrics: {{...}}`."
            raise TypeError(msg)

    scenario_paths = sorted(config_dir.glob(SCENARIO_GLOB))
    if not scenario_paths:
        msg = (
            f"No {SCENARIO_GLOB} in {config_dir}. Every project declares the runs "
            f"it defines, even when that is one scenario with no overrides, in at "
            f"least one file named like scen_2023.yaml."
        )
        raise FileNotFoundError(msg)

    merged: dict[str, object] = {
        "scenarios": {}, "ladder": [], "matrix": [], "steps": extra_steps,
    }
    owner: dict[str, Path] = {}
    for path in scenario_paths:
        doc = _read_yaml(path) or {}
        if not isinstance(doc, dict):
            msg = f"{path} must be a mapping: a scenario ID at the top level for each run it declares."
            raise TypeError(msg)
        for scenario_id, entry in doc.items():
            if scenario_id in _FORBIDDEN_SCENARIO_KEYS:
                msg = f"{path} declares `{scenario_id}:` -- {_FORBIDDEN_SCENARIO_KEYS[scenario_id]}"
                raise ValueError(msg)
            if scenario_id in owner:
                msg = (
                    f"Scenario {scenario_id!r} is declared in both "
                    f"{owner[scenario_id].name} and {path.name}."
                )
                raise ValueError(msg)
            owner[scenario_id] = path
            merged["scenarios"][scenario_id] = entry

    for path in sorted(config_dir.glob(LADDER_GLOB)):
        specs = _read_yaml(path) or []
        if not isinstance(specs, list):
            msg = f"{path} must be a list of ladder specs, e.g. `- id: ..., rungs: [...]`."
            raise TypeError(msg)
        merged["ladder"] += specs

    for path in sorted(config_dir.glob(MATRIX_GLOB)):
        specs = _read_yaml(path) or []
        if not isinstance(specs, list):
            msg = f"{path} must be a list of matrix specs, e.g. `- id: ..., axes: {{...}}`."
            raise TypeError(msg)
        merged["matrix"] += specs

    return expand(merged)


def render(expansion: Expansion) -> str:
    """The scenario list as a table: ID, tokens, description.

    What a modeller reads before writing the twenty-eighth scenario, and the only
    place the matrix's dropped combinations are visible -- a matrix that silently
    yielded nine scenarios instead of twelve would read as full coverage.
    """
    if not expansion.scenarios:
        return "  no scenarios declared."

    axes: list[str] = []
    for scenario in expansion.scenarios:
        axes += [a for a in scenario.tokens if a not in axes]

    headers = ["ID", *(a.upper() for a in axes), "DESCRIPTION"]
    rows = [
        [c.id, *(c.tokens.get(a, "--") for a in axes), " ".join(c.description.split())]
        for c in expansion.scenarios
    ]
    # The last column is prose and is not padded, so a long description cannot
    # push every row's trailing whitespace out.
    widths = [max(len(r[i]) for r in [headers, *rows]) for i in range(len(headers) - 1)]

    def _line(cells: list[str]) -> str:
        padded = [c.ljust(w) for c, w in zip(cells, widths, strict=False)]
        return ("  " + "  ".join([*padded, cells[-1]])).rstrip()

    out = [_line(headers), *(_line(row) for row in rows)]
    if expansion.excluded:
        out.append("")
        out.append(f"  {len(expansion.excluded)} combination(s) excluded:")
        out += [
            "    " + ", ".join(f"{a}={t}" for a, t in combo.items())
            for combo in expansion.excluded
        ]
    return "\n".join(out)
