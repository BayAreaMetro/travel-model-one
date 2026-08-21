"""The runs a project defines, and how each one differs from ``config.yaml``.

``config.yaml`` is the full model with its default values. A **case** is a named
set of overrides on it, and ``cases.yaml`` declares them three ways -- all expanding
to the same flat list, so there is one code path and one set of rules::

    cases:      one entry per run, written out
    ladder:     cumulative -- rung k applies rungs 1..k, for isolating one
                intervention's contribution against its predecessor
    matrix:     the cross product of named axes, minus `exclude:` combinations

This module *enumerates* cases. Applying one to a config -- and checking that its
addresses resolve -- is :mod:`tm1.project.overrides`.

Case IDs
--------
``SERIES-TOKENS-YEAR`` -- ``A001-NOPK-2035`` -- unique within the project and stable
forever, because the ID names the run directory: a renamed case is an unrun case,
and that is fifteen hours. ``description:`` carries the prose. Ladder and matrix
generate IDs from an ``id:`` template whose tokens are their part names, so adding a
matrix axis value never renames an existing case. Ladder IDs carry the rung index
and *do* shift when a rung is inserted -- correctly, since that changes what every
downstream rung means.
"""

import itertools
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

#: A case ID: uppercase segments joined by hyphens.  Lowercase and underscores are
#: refused so IDs read as identifiers rather than prose, and so two cases cannot
#: differ only by case on a filesystem that does not.
_ID = re.compile(r"^[A-Z0-9]+(-[A-Z0-9]+)*$")

#: A trailing three-digit segment would be ambiguous with the run-iteration suffix
#: a run directory carries (``A001-NOPK-2035-001``).
_ID_TAIL = re.compile(r"-[0-9]{3}$")

#: ``{token}`` in an ``id:`` template.
_TOKEN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def pairs(steps: object) -> list[tuple[str, object]]:
    """An ordered block written either way, as ``(name, value)`` pairs.

    Both project files use the shape: a mapping, or a list of single-key
    mappings.  ``steps:`` needs the list form to name a step twice; ladder
    ``rungs:`` need it to stay ordered.

    The value is handed back as it is written, not coerced: ``warmstart:`` is a
    *list* of steps and ``iterate:`` a mapping, so flattening either to a dict
    would lose the block.
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
class Case:
    """One run: an ID, what it is, and how it differs from ``config.yaml``."""

    id: str
    description: str = ""
    #: address -> value, applied in declaration order.
    overrides: dict[str, object] = field(default_factory=dict)
    #: axis or rung name -> token, for display and ``--select``.
    tokens: dict[str, str] = field(default_factory=dict)
    #: Where it came from: ``cases``, ``ladder:<id>``, ``matrix:<id>``.
    source: str = "cases"


def _check_id(case_id: str, seen: dict[str, str], source: str) -> None:
    """Refuse a malformed ID, or one that collides with a case already made."""
    if not _ID.match(case_id):
        msg = (
            f"Case ID {case_id!r} ({source}): use uppercase segments joined by "
            f"hyphens, e.g. A001-NOPK-2035."
        )
        raise ValueError(msg)
    if _ID_TAIL.search(case_id):
        msg = (
            f"Case ID {case_id!r} ({source}): a trailing three-digit segment is "
            f"ambiguous with the run-iteration suffix a run directory carries."
        )
        raise ValueError(msg)
    if case_id in seen:
        msg = (
            f"Case ID {case_id!r} ({source}) collides with {seen[case_id]}. "
            f"An ID names a run directory, so two cases cannot share one."
        )
        raise ValueError(msg)
    seen[case_id] = f"{case_id} ({source})"


def _split_meta(entry: object) -> tuple[str, dict]:
    """``description:`` off the front of an override table."""
    if entry is None:
        return "", {}
    if not isinstance(entry, dict):
        msg = f"A case must be a mapping of address: value; got {entry!r}."
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


def _expand_ladder(spec: dict, seen: dict[str, str]) -> list[Case]:
    """Cumulative cases: rung k carries rungs 1..k, in order."""
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
    cases: list[Case] = []
    cumulative: dict[str, object] = dict(shared)
    applied: list[str] = []
    for index, (name, body) in enumerate(rungs, start=1):
        rung_prose, overrides = _split_meta(body)
        cumulative.update(overrides)
        # Trailing stops are dropped so the joined list reads as one sentence
        # rather than as prose with its own punctuation embedded.
        applied.append((rung_prose or name).rstrip("."))
        tokens = {"n": f"{index:02d}", "rung": name}
        case_id = _render(template, tokens, f"ladder {template!r}")
        _check_id(case_id, seen, f"ladder rung {index}")
        cases.append(Case(
            id=case_id,
            # The description names everything the rung carries, because that is
            # what the run *is* -- a reader should not have to count backwards.
            description=" ".join(filter(None, [
                prose, "Cumulative through: " + "; ".join(applied) + ".",
            ])),
            overrides=dict(cumulative),
            tokens=dict(tokens),
            source=f"ladder:{template}",
        ))
    return cases


def _expand_matrix(spec: dict, seen: dict[str, str]) -> tuple[list[Case], list[dict]]:
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
    cases: list[Case] = []
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
        case_id = _render(template, tokens, f"matrix {template!r}")
        _check_id(case_id, seen, f"matrix {template}")
        cases.append(Case(
            id=case_id,
            description=" ".join(filter(None, [prose, " ".join(parts)])),
            overrides=overrides,
            tokens=tokens,
            source=f"matrix:{template}",
        ))
    return cases, excluded


def _matches(tokens: dict[str, str], rule: object) -> bool:
    """Whether a combination matches a partial ``exclude:`` spec.

    Partial on purpose: naming a subset of axes drops every case containing it, so
    an exclusion survives a new axis being added.
    """
    if not isinstance(rule, dict):
        msg = f"`exclude:` entries must be mappings of axis: token; got {rule!r}."
        raise TypeError(msg)
    return all(tokens.get(str(a)) == str(t) for a, t in rule.items())


@dataclass
class Expansion:
    """Every case a project defines, and what its matrices dropped."""

    cases: list[Case] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)

    def by_id(self, case_id: str) -> Case | None:
        """One case by ID, matched case-insensitively."""
        folded = case_id.upper()
        return next((c for c in self.cases if c.id.upper() == folded), None)


def expand(cases_cfg: object) -> Expansion:
    """Every pathway in ``cases.yaml``, expanded to a flat list of cases."""
    if cases_cfg is None:
        return Expansion()
    if not isinstance(cases_cfg, dict):
        msg = "cases.yaml must be a mapping with `cases:`, `ladder:` or `matrix:`."
        raise TypeError(msg)

    unknown = sorted(set(cases_cfg) - {"cases", "ladder", "matrix"})
    if unknown:
        msg = (
            f"cases.yaml declares {', '.join(unknown)}; the three pathways are "
            f"`cases:` (explicit), `ladder:` (cumulative) and `matrix:` (cross product)."
        )
        raise ValueError(msg)

    seen: dict[str, str] = {}
    out = Expansion()

    for case_id, entry in (cases_cfg.get("cases") or {}).items():
        _check_id(str(case_id), seen, "cases")
        prose, overrides = _split_meta(entry)
        out.cases.append(Case(str(case_id), prose, overrides, source="cases"))

    for spec in cases_cfg.get("ladder") or []:
        out.cases += _expand_ladder(spec, seen)

    for spec in cases_cfg.get("matrix") or []:
        cases, excluded = _expand_matrix(spec, seen)
        out.cases += cases
        out.excluded += excluded

    return out


def load(config_dir: Path) -> Expansion:
    """Expand ``cases.yaml`` from *config_dir*, which every project must have."""
    path = Path(config_dir) / "cases.yaml"
    if not path.is_file():
        msg = (
            f"No cases.yaml in {config_dir}. Every project declares the runs it "
            f"defines, even when that is one case with no overrides."
        )
        raise FileNotFoundError(msg)
    with path.open(encoding="utf-8") as f:
        return expand(yaml.safe_load(f))


def render(expansion: Expansion) -> str:
    """The case list as a table: ID, tokens, description.

    What a modeller reads before writing the twenty-eighth case, and the only
    place the matrix's dropped combinations are visible -- a matrix that silently
    yielded nine cases instead of twelve would read as full coverage.
    """
    if not expansion.cases:
        return "  no cases declared."

    axes: list[str] = []
    for case in expansion.cases:
        axes += [a for a in case.tokens if a not in axes]

    headers = ["ID", *(a.upper() for a in axes), "DESCRIPTION"]
    rows = [
        [c.id, *(c.tokens.get(a, "--") for a in axes), " ".join(c.description.split())]
        for c in expansion.cases
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
