"""Which steps run, in which round, and which of them this invocation wants.

The config describes the pipeline in blocks; a run needs it flat -- an ordered
list of ``(step, round)``. That flattening is here, along with the selection
``--steps`` / ``--resume-at`` / ``--until`` apply to the result.

Pure: it reads config and returns lists. Nothing here executes a step, opens a run
directory or writes a log, which is what lets ``tm1 status`` work out what a run
*would* do without importing the thing that does it.

Two blocks decide every step's round, and nothing else does:

* ``warmstart:`` -- its steps run once, at round 0 (RunModel.bat's ``set ITER=0``)
* ``iterate:``   -- its steps repeat, rounds 1..count

A step written flat runs once where it sits: round 1 before the loop, the final
round after it.
"""

import logging
from pathlib import Path

log = logging.getLogger(__name__)


#: Step name reserved for the global feedback loop.
_ITERATE = "iterate"

#: Step name reserved for the round-0 block that precedes the loop.
_WARMSTART = "warmstart"

#: The round `warmstart:` steps run as -- `RunModel.bat`'s `set ITER=0`.
_WARMSTART_ROUND = 0

#: Keys `iterate:` understands.  Anything else is refused by name, so a config
#: written for a removed mechanism (`warm_start:`, `first_round:`) fails loudly
#: instead of being silently ignored.
_ITERATE_KEYS = ("count", "steps")

#: Key letting a step *outside* the loop skip itself when its product is on disk.
_SKIP_IF_EXISTS = "skip_if_exists"

#: Key switching a step off entirely.  Default true, so a config need not say it.
#: A step that has no cheap no-op sits in the pipeline disabled and is switched on
#: by the scenario that wants it -- which keeps the step list the same for every
#: scenario.
_ENABLED = "enabled"


def normalize_steps(steps_cfg: object, where: str = "steps") -> list[tuple[str, dict]]:
    """Ordered ``(name, config)`` pairs from either shape of ``steps:``.

    A mapping is the compact form.  A list of single-key mappings is the explicit
    form -- and the only one that can name the same step twice, which is how the
    warm start and the loop each carry their own copy of the assignment steps.

    ``enabled: false`` drops a step here, and *only* here: :mod:`tm1.status` builds
    its grid from this same function, so filtering anywhere else would make the
    status view disagree with what actually ran.
    """
    if isinstance(steps_cfg, dict):
        return [
            (str(name), cfg or {}) for name, cfg in steps_cfg.items()
            if _step_enabled(cfg)
        ]
    if isinstance(steps_cfg, list):
        pairs: list[tuple[str, dict]] = []
        for item in steps_cfg:
            if not isinstance(item, dict) or len(item) != 1:
                msg = (
                    f"`{where}` entries must each be one `name: {{config}}` "
                    f"mapping; got {item!r}."
                )
                raise TypeError(msg)
            name, cfg = next(iter(item.items()))
            if _step_enabled(cfg):
                pairs.append((str(name), cfg or {}))
        return pairs
    msg = f"`{where}` must be a mapping or a list of `name: {{config}}` entries."
    raise TypeError(msg)


def _step_enabled(step_cfg: object) -> bool:
    """Whether a step runs.  Only a literal ``enabled: false`` switches it off.

    Checked against dicts alone, so ``warmstart:`` (a list) and ``iterate:`` (whose
    keys are already restricted) cannot be disabled wholesale -- a scenario varies
    what the pipeline does, not whether half of it exists.
    """
    return not (isinstance(step_cfg, dict) and step_cfg.get(_ENABLED) is False)


def iteration_plan(
    steps_cfg: object, override: int | None = None
) -> tuple[list[tuple[str, int]], dict[tuple[str, int], dict]]:
    """Expand the config into the execution plan, one entry per run of a step.

    Returns ``(plan, configs)``: the ordered ``[(step, round)]`` list, and the
    config block behind each entry.  The block travels with the entry because a
    name may appear more than once -- the warm start's ``hwy_assign`` and the
    loop's are different entries with different configs.

    A step's round comes from where it is written, and from nothing else:

    - ``warmstart:`` runs its steps once, at round 0 -- ``RunModel.bat``'s
      ``set ITER=0``.
    - ``iterate:`` repeats its body ``count`` times, rounds 1..N, identically.
      Body steps may not declare ``skip_if_exists:``; the loop always re-runs.
    - Anything else runs once, where it is written: at round 1 before the loop,
      at the final round after it.
    """
    plan: list[tuple[str, int]] = []
    configs: dict[tuple[str, int], dict] = {}
    seen: set[str] = set()
    current = 1

    def add(name: str, rnd: int, cfg: dict) -> None:
        if (name, rnd) in configs:
            msg = (
                f"Step {name!r} is defined twice for iteration {rnd}. Two copies "
                f"of a step must run in different rounds -- move one into "
                f"`{_WARMSTART}:` or `{_ITERATE}:`, or rename it."
            )
            raise ValueError(msg)
        configs[(name, rnd)] = cfg
        plan.append((name, rnd))

    for name, step_cfg in normalize_steps(steps_cfg):
        if name == _WARMSTART:
            _check_block_placement(name, seen)
            for body_name, body_cfg in warmstart_block(step_cfg):
                add(body_name, _WARMSTART_ROUND, body_cfg)
        elif name == _ITERATE:
            _check_block_placement(name, seen)
            count, body = iterate_block(step_cfg, override)
            for i in range(1, count + 1):
                for body_name, body_cfg in body:
                    add(body_name, i, body_cfg)
            current = count
        else:
            _reject_iteration_key(name, step_cfg)
            add(name, current, step_cfg)

    return plan, configs


def _check_block_placement(name: str, seen: set[str]) -> None:
    """``warmstart:`` and ``iterate:`` appear at most once, warm start first.

    A second copy of either would silently redefine the run's shape, and a warm
    start written after the loop would run round-0 steps at the end -- succeeding
    while overwriting the finished round's networks.
    """
    if name in seen:
        msg = f"`{name}` is declared twice; it is the whole of that part of the run."
        raise ValueError(msg)
    if name == _WARMSTART and _ITERATE in seen:
        msg = (
            f"`{_WARMSTART}` is written after `{_ITERATE}`. It seeds the loop, so "
            f"it has to come before it -- its steps run at iteration "
            f"{_WARMSTART_ROUND} and write the networks and skims round 1 reads."
        )
        raise ValueError(msg)
    seen.add(name)


def _reject_iteration_key(name: str, step_cfg: dict) -> None:
    """A step's round comes from where it is written, never from a key.

    ``iteration:`` was how the warm start declared round 0 before ``warmstart:``
    existed, and every use of it said ``0``.  Refused rather than ignored, so a
    config written against the older shape fails loudly instead of running a
    warm-start step as round 1 -- which writes ``hwy/iter1/`` from iteration-0
    demand, succeeding while producing nonsense.
    """
    if "iteration" not in step_cfg:
        return
    msg = (
        f"Step {name!r} declares `iteration:`, which is not a step key. Rounds "
        f"come from position: `{_WARMSTART}:` runs its steps at iteration "
        f"{_WARMSTART_ROUND}, `{_ITERATE}:` numbers its own rounds 1..count, and "
        f"a step outside both runs where it is written. Move it into "
        f"`{_WARMSTART}:`."
    )
    raise ValueError(msg)


def warmstart_block(ws_cfg: object) -> list[tuple[str, dict]]:
    """Validate the ``warmstart:`` block and return its body.

    A bare list of steps, not a block with keys.  The only thing it says is *these
    run at iteration 0*, and unlike ``iterate:`` there is no ``count`` to state, so
    a ``steps:`` wrapper would be a level of nesting carrying no information.
    """
    # `ws_cfg` is truthy here so an empty block falls through to the check below:
    # `normalize_steps` turns an empty list into `{}`, which is a subset of anything.
    if isinstance(ws_cfg, dict) and ws_cfg and set(ws_cfg) <= set(_ITERATE_KEYS):
        msg = (
            f"`{_WARMSTART}` is a bare list of steps, not a block -- it runs once, "
            f"at iteration {_WARMSTART_ROUND}, so there is no `count` and no "
            f"`steps:` wrapper:\n\n"
            f"    {_WARMSTART}:\n"
            f"      - hwy_assign: {{job: ..., "
            f"{_SKIP_IF_EXISTS}: hwy/iter0/LOADEA.net}}\n"
            f"      - hwy_skims:  {{job: ...}}"
        )
        raise TypeError(msg)

    body = normalize_steps(ws_cfg or [], where=_WARMSTART)
    if not body:
        msg = (
            f"`{_WARMSTART}` declares no steps; delete the block, or fill it in "
            f"with the steps that seed the loop."
        )
        raise ValueError(msg)

    for body_name, body_cfg in body:
        if "iteration" in body_cfg:
            msg = (
                f"Step {body_name!r} declares `iteration:` inside `{_WARMSTART}`, "
                f"which is itself the statement that its steps run at iteration "
                f"{_WARMSTART_ROUND}. Drop the key."
            )
            raise ValueError(msg)

    return body


def iterate_block(
    it_cfg: object, override: int | None
) -> tuple[int, list[tuple[str, dict]]]:
    """Validate the ``iterate:`` block and return ``(count, body)``.

    The body is checked here for the two keys the loop refuses -- see
    :func:`iteration_plan` -- and the block itself for keys it does not take,
    so a config written for a removed mechanism fails loudly.
    """
    if not isinstance(it_cfg, dict) or not it_cfg:
        msg = (
            f"`{_ITERATE}` must be a block with `count` and `steps`:\n\n"
            f"    {_ITERATE}:\n      count: 3\n      steps:\n"
            f"        - simulate_ctramp: {{}}\n        - assignment: {{}}"
        )
        raise TypeError(msg)

    unknown = [k for k in it_cfg if k not in _ITERATE_KEYS]
    if unknown:
        msg = (
            f"`{_ITERATE}` does not take {', '.join(map(repr, unknown))} -- "
            f"only `count` and `steps`. Steps that run outside the rounds go in "
            f"`{_WARMSTART}:` (iteration {_WARMSTART_ROUND}, seeding the loop) or "
            f"are written flat before or after the loop; either way they may "
            f"declare `{_SKIP_IF_EXISTS}:`."
        )
        raise ValueError(msg)

    count = int(override if override is not None else it_cfg.get("count", 1))
    if count < 1:
        msg = f"{_ITERATE}.count must be >= 1, got {count}"
        raise ValueError(msg)

    body = normalize_steps(it_cfg.get("steps") or [], where=f"{_ITERATE}.steps")
    if not body:
        msg = f"`{_ITERATE}` declares no steps; the loop body cannot be empty."
        raise ValueError(msg)

    for body_name, body_cfg in body:
        if _SKIP_IF_EXISTS in body_cfg:
            msg = (
                f"Step {body_name!r} declares `{_SKIP_IF_EXISTS}` inside "
                f"`{_ITERATE}`. The loop always re-runs -- its outputs land "
                f"on the same paths every round, so an existence check "
                f"cannot tell this round's product from the last one's. "
                f"Move the step into `{_WARMSTART}:` if it runs once."
            )
            raise ValueError(msg)
        if "iteration" in body_cfg:
            msg = (
                f"Step {body_name!r} declares `iteration:` inside `{_ITERATE}`, "
                f"whose rounds are numbered by the loop itself."
            )
            raise ValueError(msg)

    return count, body


def skip_target(step_cfg: dict, cfg: dict) -> Path | None:
    """The declared product that lets this step skip itself, if it is on disk.

    ``skip_if_exists:`` is a statement in the config -- *this step's work is done
    when this file exists* -- and the check is exactly that, nothing inferred.
    Deleting the file forces a rebuild.  Relative paths resolve against
    ``run_dir``, where every model artifact lives.
    """
    declared = step_cfg.get(_SKIP_IF_EXISTS)
    if not declared:
        return None
    path = Path(str(declared)).expanduser()
    if not path.is_absolute():
        path = Path(cfg["run_dir"]) / path
    return path if path.exists() else None


def fmt_plan(plan: list[tuple[str, int]], n_iters: int) -> str:
    """Render plan entries, showing the iteration only when there is more than one."""
    if n_iters <= 1:
        return ", ".join(s for s, _ in plan)
    return ", ".join(f"{s}@{i}" for s, i in plan)


def resume_token(plan: list[tuple[str, int]], step: str, iteration: int) -> str:
    """The ``--resume-at`` argument that would restart at this point.

    Includes the iteration prefix only when the step appears more than once, so
    the hint printed on failure is the shortest unambiguous form.
    """
    return f"{iteration}:{step}" if sum(s == step for s, _ in plan) > 1 else step


def _match_token(
    plan: list[tuple[str, int]], token: str, flag: str
) -> int:
    """Index in *plan* of the entry a ``[N:]STEP`` token names.

    A bare name matching several rounds is an error rather than a guess: picking
    the wrong round costs hours of Cube.
    """
    prefix, _, name = token.rpartition(":")
    name = name.strip()
    want = int(prefix.strip()) if prefix.strip() else None

    matches = [
        i for i, (step, it) in enumerate(plan)
        if step == name and (want is None or it == want)
    ]
    n_iters = max((i for _, i in plan), default=1)

    if not matches:
        msg = (
            f"{flag} {token!r} matches nothing in this run.\n"
            f"Planned: {fmt_plan(plan, n_iters)}\n"
            f"Give a step name, or iteration:step to pick a round."
        )
        raise ValueError(msg)

    if want is None and len(matches) > 1:
        rounds = ", ".join(f"{plan[i][1]}:{name}" for i in matches)
        msg = (
            f"{flag} {name!r} is ambiguous -- it runs in {len(matches)} "
            f"iterations. Say which: {rounds}"
        )
        raise ValueError(msg)

    return matches[0]


def apply_until(
    plan: list[tuple[str, int]], until: str | None
) -> list[tuple[str, int]]:
    """Drop everything after *until*, which itself **runs**.

    The mirror of :func:`apply_resume`, and composable with it -- together they
    name any contiguous slice of the plan.  Naming a boundary rather than listing
    steps is what keeps this usable as the pipeline grows: ``--until
    0:publish_networks`` is the whole warm start however many steps that is.
    """
    if not until:
        return plan
    return plan[: _match_token(plan, until, "--until") + 1]


def select_steps(
    plan: list[tuple[str, int]], steps: list[str] | None
) -> list[tuple[str, int]]:
    """Keep only the named steps, **without** disturbing their round numbers.

    ``--steps`` filters the real plan rather than standing in for one.  Building a
    fresh plan from bare names loses the ``iterate:`` expansion, so every step
    would be numbered 1 -- and a warm-start step run as iteration 1 writes
    ``hwy/iter1/`` from iteration-0 demand, succeeding while producing nonsense.

    A name may carry a round (``0:hwy_assign``) to pick one; bare, it keeps every
    round that step legitimately runs in.
    """
    if not steps:
        return plan

    wanted: set[tuple[str, int]] = set()
    for token in steps:
        prefix, _, name = token.rpartition(":")
        name = name.strip()
        want = int(prefix.strip()) if prefix.strip() else None
        hits = [(s, i) for s, i in plan if s == name and (want is None or i == want)]
        if not hits:
            n_iters = max((i for _, i in plan), default=1)
            msg = (
                f"--steps {token!r} matches nothing in this run.\n"
                f"Planned: {fmt_plan(plan, n_iters)}"
            )
            raise ValueError(msg)
        wanted.update(hits)

    return [entry for entry in plan if entry in wanted]


def apply_resume(
    plan: list[tuple[str, int]],
    resume_at: str | None,
    run_dir: str | Path | None = None,
) -> list[tuple[str, int]]:
    """Drop everything before *resume_at*, which itself **runs**.

    Takes ``step`` or ``iteration:step``; the prefix is needed only when a step
    appears more than once, which happens only inside ``iterate`` with
    ``count > 1``.  A bare name matching several entries is an error rather than
    a guess -- picking the wrong round costs hours of Cube.

    The named step re-runs from the start; it is never continued part-way.  Cube
    jobs are not transactional, so a killed ``HwyAssign`` leaves partial ``.net``
    and ``.tpp`` files that only a fresh run overwrites cleanly.
    """
    if not resume_at:
        return plan

    # "Resume" presupposes a previous run.  Without this, pointing it at an empty
    # project directory would skip staging and demand, then assign whatever stale
    # matrices happened to be lying around.
    if run_dir is not None:
        p = Path(run_dir)
        if not p.is_dir() or not any(p.iterdir()):
            msg = (
                f"--resume-at needs a project directory a previous run populated; "
                f"{p} is {'missing' if not p.is_dir() else 'empty'}. Run without "
                f"--resume-at to start from the beginning."
            )
            raise ValueError(msg)

    prefix, _, name = resume_at.rpartition(":")
    name = name.strip()
    want = int(prefix.strip()) if prefix.strip() else None

    matches = [
        i for i, (step, it) in enumerate(plan)
        if step == name and (want is None or it == want)
    ]
    n_iters = max((i for _, i in plan), default=1)

    if not matches:
        msg = (
            f"--resume-at {resume_at!r} matches nothing in this run.\n"
            f"Planned: {fmt_plan(plan, n_iters)}\n"
            f"Give a step name, or iteration:step to pick a round."
        )
        raise ValueError(msg)

    if want is None and len(matches) > 1:
        rounds = ", ".join(f"{plan[i][1]}:{name}" for i in matches)
        msg = (
            f"--resume-at {name!r} is ambiguous -- it runs in {len(matches)} "
            f"iterations. Say which: {rounds}"
        )
        raise ValueError(msg)

    return plan[matches[0] :]
