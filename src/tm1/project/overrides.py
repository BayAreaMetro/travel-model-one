"""Applying a scenario to a config: what an override address means, and where it lands.

An override names *where the value lives* in the config::

    m_drive: "X:/models"                               a top-level key
    env.MODEL_YEAR: 2035                               inside a top-level mapping
    env.EN7: ENABLED                                   ... and its siblings survive
    copy_inputs.input_landuse.from: "M:/.../landuse"   inside a step
    iterate.count: 1                                   the loop's own key
    iterate.simulate_ctramp.threads: 12                a step inside the loop
    iterate.hwy_assign.cluster_nodes: 24               a step that runs every iteration

Three rules, and they are the whole mechanism:

1. **The address must already exist.** There is nothing to declare and no schema to
   keep in step: the config's own value at an address is the default, its type is
   the type, and its existence is the validation. An address that resolves to
   nothing is an error naming the closest match, so a typo cannot quietly run the
   default. The one exception is :data:`UNIVERSAL_STEP_KEYS`.
2. **Values replace, never merge.** Naming a mapping replaces it whole. Name a
   deeper address to change one key of it -- which is why descent exists: replacing
   ``env:`` to change ``EN7`` would silently drop ``PATH``.
3. **``steps`` itself is not addressable.** A scenario varies values inside the
   pipeline; it never adds, removes, or reorders steps. A different pipeline shape
   is a different project.
"""

import copy
import difflib

from tm1.project.scenarios import Expansion, Scenario, pairs

#: Keys a scenario may set on a step even when the step does not declare them.
#: The list is deliberately one item: everything else must already exist, so the
#: config stays the record of what a step can be asked to do.
UNIVERSAL_STEP_KEYS = frozenset({"enabled"})

#: The one block that nests steps and is addressed by name.
_ITERATE = "iterate"

#: The top-level key holding the pipeline.  Not addressable -- see rule 3.
_STEPS = "steps"


def _step_entries(cfg: dict) -> list[tuple[str, dict, str]]:
    """Every step as ``(name, config, qualifier)``.

    *qualifier* is ``""`` for a flat step and ``"iterate"`` for one inside
    ``iterate.steps``.  Built by walking rather than by importing the runner's
    plan, because a scenario is applied *before* the plan exists.
    """
    entries: list[tuple[str, dict, str]] = []
    for name, block in pairs(cfg.get(_STEPS)):
        if name == _ITERATE:
            inner = block.get(_STEPS) if isinstance(block, dict) else None
        else:
            # A step with no body has nothing to address, so it is not an entry.
            if isinstance(block, dict):
                entries.append((name, block, ""))
            continue
        entries += [(n, c, name) for n, c in pairs(inner) if isinstance(c, dict)]
    return entries


def _block(cfg: dict, name: str) -> object:
    """The ``iterate:`` block, if the config has one."""
    for step_name, block in pairs(cfg.get(_STEPS)):
        if step_name == name:
            return block
    return None


def _root_for(cfg: dict, segments: list[str], address: str) -> tuple[object, list[str]]:
    """Where an address starts walking, and what is left to walk.

    Resolves the first segment -- a top-level key, ``iterate``, or a step name --
    and hands back the container it names.  Everything after that is ordinary
    mapping descent, which is why the grammar needs no depth rule.
    """
    head = segments[0]

    if head == _STEPS:
        msg = (
            f"{address!r}: `steps` is not addressable. A scenario sets values "
            f"inside steps; it cannot add, remove, or reorder them -- a different "
            f"pipeline is a different project."
        )
        raise ValueError(msg)

    if head == _ITERATE:
        return _in_nested_block(cfg, head, segments, address)

    if head in cfg:
        return cfg, segments

    matches = [(n, c, q) for n, c, q in _step_entries(cfg) if n == head]
    if not matches:
        raise KeyError(_unknown(cfg, address, head))
    if len(matches) > 1:
        msg = (
            f"{address!r}: step {head!r} appears more than once in the pipeline; "
            f"an address assumes a step appears once."
        )
        raise ValueError(msg)
    return matches[0][1], segments[1:]


def _in_nested_block(
    cfg: dict, head: str, segments: list[str], address: str
) -> tuple[object, list[str]]:
    """An address starting at ``iterate:``.

    ``iterate.count`` is the loop's own key; every other second segment names a
    step inside the block.
    """
    block = _block(cfg, head)
    if block is None:
        msg = f"{address!r}: this project has no `{head}:` block."
        raise ValueError(msg)

    if len(segments) > 1 and segments[1] != _STEPS:
        inner = dict(pairs(block.get(_STEPS) if isinstance(block, dict) else block))
        if segments[1] in inner:
            return _in_block(cfg, head, segments[1], address), segments[2:]
        if isinstance(block, dict) and segments[1] in block:
            return block, segments[1:]

    msg = f"{address!r}: name a step inside `{head}:`, or `iterate.count`."
    raise ValueError(msg)


def _in_block(cfg: dict, block_name: str, step: str, address: str) -> dict:
    """One step's config inside ``iterate:``."""
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
        | {_ITERATE}
    )
    close = difflib.get_close_matches(head, known, n=3, cutoff=0.6)
    hint = f" Did you mean {', '.join(close)}?" if close else ""
    return f"{address!r}: no such address -- {head!r} is not in the config.{hint}"


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


def apply_scenario(cfg: dict, scenario: Scenario) -> dict:
    """*cfg* with *scenario*'s overrides applied, leaving the original untouched."""
    out = copy.deepcopy(cfg)
    for address, value in scenario.overrides.items():
        container, key = resolve_address(out, address)
        container[key] = copy.deepcopy(value)
    return out


#: The sentinel a placeholder value in the shared model file starts with -- e.g.
#: ``"REQUIRED: override copy_inputs.input_hwy.from"``. There is no project-level
#: defaults layer, so this is what stands in for one: a scenario that does not
#: override every address holding it is refused, rather than silently running
#: with a value nobody wrote.
_REQUIRED = "REQUIRED"


def _unresolved_placeholders(obj: object, path: str = "") -> list[str]:
    """Every address in *obj* whose value is still a :data:`_REQUIRED` placeholder."""
    if isinstance(obj, str):
        return [path] if obj.startswith(_REQUIRED) else []
    if isinstance(obj, dict):
        found: list[str] = []
        for key, value in obj.items():
            found += _unresolved_placeholders(value, f"{path}.{key}" if path else str(key))
        return found
    if isinstance(obj, list):
        found = []
        for index, value in enumerate(obj):
            found += _unresolved_placeholders(value, f"{path}[{index}]")
        return found
    return []


def validate(cfg: dict, expansion: Expansion) -> list[str]:
    """Every problem across every scenario, rather than the first one.

    All of them, because a bundle is queued and left: finding scenario 27's typo
    at hour 40 is the failure this exists to prevent.
    """
    problems: list[str] = []
    for scenario in expansion.scenarios:
        for address in scenario.overrides:
            try:
                resolve_address(copy.deepcopy(cfg), address)
            except (KeyError, ValueError) as exc:
                # args[0] rather than str(): KeyError's str() is the repr of its
                # argument, which wraps an already-quoted message in more quotes.
                problems.append(f"{scenario.id}: {exc.args[0]}")

        try:
            applied = apply_scenario(cfg, scenario)
        except (KeyError, ValueError, TypeError):
            # Already reported above; scanning a partially-applied config for
            # placeholders here would only repeat the same failure as noise.
            continue
        problems += [
            f"{scenario.id}: {address} is still a REQUIRED placeholder -- override it"
            for address in _unresolved_placeholders(applied)
        ]
    return problems

