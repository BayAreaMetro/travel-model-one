"""Cases: the runs a project defines, and how each one differs.

A project's ``config.yaml`` is the full model with its default values.  A **case**
is a named set of overrides into it, and ``cases.yaml`` declares them three ways --
all expanding to the same thing, so there is one code path and one set of rules::

    cases:      one entry per run, written out
    ladder:     cumulative -- rung k applies rungs 1..k, for isolating one
                intervention's contribution against its predecessor
    matrix:     the cross product of named axes, minus `exclude:` combinations

Addresses
---------
An override names *where the value lives* in ``config.yaml``::

    model_year: 2035                                   a top-level key
    env.EN7: ENABLED                                   inside a top-level mapping
    copy_inputs.input_landuse.from: "M:/.../landuse"   inside a step
    iterate.count: 1                                   the loop's own key
    iterate.simulate_ctramp.threads: 12                a step inside the loop
    warmstart.hwy_assign.cluster_nodes: 24             the same step, round 0

Four rules, and they are the whole mechanism:

1. **The address must already exist.**  There is nothing to declare and no schema
   to keep in step: the config's own value at an address is the default, its type
   is the type, and its existence is the validation.  An address that resolves to
   nothing is an error naming the closest match, so a typo cannot quietly run the
   default.  The one exception is :data:`UNIVERSAL_STEP_KEYS`.
2. **Values replace, never merge.**  Naming a mapping replaces it whole.  Name a
   deeper address to change one key of it -- which is why descent exists: replacing
   ``env:`` to change ``EN7`` would silently drop ``PATH``.
3. **A step name in both blocks must be qualified.**  Twelve steps appear in both
   ``warmstart:`` and ``iterate:``; bare, they are ambiguous, and guessing would
   change a different round than the one meant.
4. **``steps`` itself is not addressable.**  A case varies values inside the
   pipeline; it never adds, removes, or reorders steps.  A different pipeline shape
   is a different project.

Case IDs
--------
``SERIES-TOKENS-YEAR`` -- ``A001-NOPK-2035`` -- unique within the project and stable
forever, because the ID names the run directory: a renamed case is an unrun case,
and that is fifteen hours.  ``description:`` carries the prose.  Ladder and matrix
generate IDs from an ``id:`` template whose tokens are their part names, so adding a
matrix axis value never renames an existing case.  Ladder IDs carry the rung index
and *do* shift when a rung is inserted -- correctly, since that changes what every
downstream rung means.
"""

import copy
import difflib
import itertools
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

#: Keys a case may set on a step even when the step does not declare them.  The
#: list is deliberately one item: everything else must already exist, so the
#: config stays the record of what a step can be asked to do.
UNIVERSAL_STEP_KEYS = frozenset({"enabled"})

#: Blocks that nest steps and are addressed by name.
_WARMSTART = "warmstart"
_ITERATE = "iterate"
_BLOCKS = (_WARMSTART, _ITERATE)

#: The top-level key holding the pipeline.  Not addressable -- see rule 4.
_STEPS = "steps"

#: A case ID: uppercase segments joined by hyphens.  Lowercase and underscores are
#: refused so IDs read as identifiers rather than prose, and so two cases cannot
#: differ only by case on a filesystem that does not.
_ID = re.compile(r"^[A-Z0-9]+(-[A-Z0-9]+)*$")

#: A trailing three-digit segment would be ambiguous with the run-iteration suffix
#: a run directory carries (``A001-NOPK-2035-001``).
_ID_TAIL = re.compile(r"-[0-9]{3}$")

#: Tokens in an `id:` template.
_TOKEN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


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


# --------------------------------------------------------------------------- #
# Addresses
# --------------------------------------------------------------------------- #


def _step_entries(cfg: dict) -> list[tuple[str, dict, str]]:
    """Every step as ``(name, config, qualifier)``.

    *qualifier* is ``""`` for a flat step and the block name for one inside
    ``warmstart:`` or ``iterate:``.  Built by walking rather than by importing the
    runner's plan, because a case is applied *before* the plan exists.
    """
    entries: list[tuple[str, dict, str]] = []
    for name, block in _pairs(cfg.get(_STEPS)):
        if name == _WARMSTART:
            inner = block
        elif name == _ITERATE:
            inner = block.get(_STEPS) if isinstance(block, dict) else None
        else:
            # A step with no body has nothing to address, so it is not an entry.
            if isinstance(block, dict):
                entries.append((name, block, ""))
            continue
        entries += [(n, c, name) for n, c in _pairs(inner) if isinstance(c, dict)]
    return entries


def _pairs(steps: object) -> list[tuple[str, object]]:
    """``steps:`` in either shape, as ordered ``(name, value)``.

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


def _block(cfg: dict, name: str) -> object:
    """The ``warmstart:`` or ``iterate:`` block, if the config has one."""
    for step_name, block in _pairs(cfg.get(_STEPS)):
        if step_name == name:
            return block
    return None


def _root_for(cfg: dict, segments: list[str], address: str) -> tuple[object, list[str]]:
    """Where an address starts walking, and what is left to walk.

    Resolves the first segment -- a top-level key, a block name, or a step name --
    and hands back the container it names.  Everything after that is ordinary
    mapping descent, which is why the grammar needs no depth rule.
    """
    head = segments[0]

    if head == _STEPS:
        msg = (
            f"{address!r}: `steps` is not addressable. A case sets values inside "
            f"steps; it cannot add, remove, or reorder them -- a different pipeline "
            f"is a different project."
        )
        raise ValueError(msg)

    if head in _BLOCKS:
        return _in_nested_block(cfg, head, segments, address)

    if head in cfg:
        return cfg, segments

    matches = [(n, c, q) for n, c, q in _step_entries(cfg) if n == head]
    if not matches:
        raise KeyError(_unknown(cfg, address, head))
    if len({q for _, _, q in matches}) > 1 or len(matches) > 1:
        blocks = sorted({q for _, _, q in matches if q})
        qualified = ", ".join(f"{b}.{head}.…" for b in blocks) or head
        msg = (
            f"{address!r}: step {head!r} appears in {' and '.join(blocks)}, so a bare "
            f"name is ambiguous. Qualify it: {qualified}"
        )
        raise ValueError(msg)
    return matches[0][1], segments[1:]


def _in_nested_block(
    cfg: dict, head: str, segments: list[str], address: str
) -> tuple[object, list[str]]:
    """An address starting at ``warmstart:`` or ``iterate:``.

    ``iterate.count`` is the loop's own key; every other second segment names a
    step inside the block, which is how the twelve steps that appear in both get
    told apart.
    """
    block = _block(cfg, head)
    if block is None:
        msg = f"{address!r}: this project has no `{head}:` block."
        raise ValueError(msg)

    if len(segments) > 1 and segments[1] != _STEPS:
        inner = dict(_pairs(block.get(_STEPS) if isinstance(block, dict) else block))
        if segments[1] in inner:
            return _in_block(cfg, head, segments[1], address), segments[2:]
        if head == _ITERATE and isinstance(block, dict) and segments[1] in block:
            return block, segments[1:]

    msg = f"{address!r}: name a step inside `{head}:`, or `iterate.count`."
    raise ValueError(msg)


def _in_block(cfg: dict, block_name: str, step: str, address: str) -> dict:
    """One step's config inside ``warmstart:`` or ``iterate:``."""
    for name, step_cfg, qualifier in _step_entries(cfg):
        if qualifier == block_name and name == step:
            return step_cfg
    msg = f"{address!r}: `{block_name}:` has no step named {step!r}."
    raise KeyError(msg)


def _unknown(cfg: dict, address: str, head: str) -> str:
    """An error naming the closest thing the config actually has."""
    known = sorted(
        {k for k in cfg if k != _STEPS}
        | {n for n, _, _ in _step_entries(cfg)}
        | set(_BLOCKS)
    )
    close = difflib.get_close_matches(head, known, n=3, cutoff=0.6)
    hint = f" Did you mean {', '.join(close)}?" if close else ""
    return f"{address!r}: no such address -- {head!r} is not in config.yaml.{hint}"


def resolve_address(cfg: dict, address: str) -> tuple[dict, str]:
    """The container and key an address names, for assignment.

    Raises rather than creating anything: the address must already exist, except
    for :data:`UNIVERSAL_STEP_KEYS` on a step.
    """
    segments = [s for s in address.split(".") if s]
    if not segments:
        msg = "An override address cannot be empty."
        raise ValueError(msg)

    container, rest = _root_for(cfg, segments, address)
    if not rest:
        msg = f"{address!r}: names a container, not a value."
        raise ValueError(msg)

    for segment in rest[:-1]:
        if not isinstance(container, dict) or segment not in container:
            raise KeyError(_missing(address, segment, container))
        container = container[segment]

    key = rest[-1]
    if not isinstance(container, dict):
        msg = f"{address!r}: {key!r} is not inside a mapping."
        raise TypeError(msg)
    if key not in container and key not in UNIVERSAL_STEP_KEYS:
        raise KeyError(_missing(address, key, container))
    return container, key


def _missing(address: str, segment: str, container: object) -> str:
    """An error naming the closest key of the mapping actually reached."""
    keys = sorted(str(k) for k in container) if isinstance(container, dict) else []
    close = difflib.get_close_matches(segment, keys, n=3, cutoff=0.6)
    hint = f" Did you mean {', '.join(close)}?" if close else (
        f" It holds: {', '.join(keys[:8])}" if keys else ""
    )
    return f"{address!r}: {segment!r} is not there.{hint}"


def apply_case(cfg: dict, case: Case) -> dict:
    """*cfg* with *case*'s overrides applied, leaving the original untouched."""
    out = copy.deepcopy(cfg)
    for address, value in case.overrides.items():
        container, key = resolve_address(out, address)
        container[key] = copy.deepcopy(value)
    return out


# --------------------------------------------------------------------------- #
# Expansion
# --------------------------------------------------------------------------- #


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

    rungs = _pairs(spec.get("rungs"))
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


def validate(cfg: dict, expansion: Expansion) -> list[str]:
    """Every problem across every case, rather than the first one.

    All of them, because a bundle is queued and left: finding case 27's typo at
    hour 40 is the failure this exists to prevent.
    """
    problems: list[str] = []
    for case in expansion.cases:
        for address in case.overrides:
            try:
                resolve_address(copy.deepcopy(cfg), address)
            except (KeyError, ValueError) as exc:
                # args[0] rather than str(): KeyError's str() is the repr of its
                # argument, which wraps an already-quoted message in more quotes.
                problems.append(f"{case.id}: {exc.args[0]}")
    return problems


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
