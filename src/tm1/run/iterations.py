"""Which steps run, in which iteration, and which of them this invocation wants.

The config describes the pipeline in one block; a run needs it flat -- an ordered
list of ``(step, iteration)``. That flattening is here, along with the selection
``--steps`` / ``--resume-at`` / ``--until`` apply to the result.

Pure: it reads config and returns lists. Nothing here executes a step, opens a run
directory or writes a log, which is what lets ``tm1 status`` work out what a run
*would* do without importing the thing that does it.

One block decides every step's iteration, and nothing else does:

* ``iterate:`` -- its steps repeat, iterations 0..count.  ``iteration_zero_begins``
  marks where iteration 0 (the warm start, ``RunModel.bat``'s ``set ITER=0``) joins
  in: a step above it runs only in iterations 1..count; a step at or after it runs
  in iteration 0 too, unless ``only_iteration:``/``skip_iteration:`` says otherwise.

A step written flat runs once where it sits: iteration 1 before the loop, the
final iteration after it.
"""

import logging
from pathlib import Path

log = logging.getLogger(__name__)


#: Step name reserved for the global feedback loop.
_ITERATE = "iterate"

#: Marker step -- not itself a step -- showing where iteration 0 joins the loop.
_ITERATION_ZERO_BEGINS = "iteration_zero_begins"

#: Keys pinning an individual step to, or away from, iteration 0.  Everything
#: else in the loop runs at every iteration a plain read of its position implies.
_ONLY_ITERATION = "only_iteration"
_SKIP_ITERATION = "skip_iteration"

#: Keys `iterate:` understands.  Anything else is refused by name, so a config
#: written for a removed mechanism (`warmstart:`, `warm_start:`, `first_round:`)
#: fails loudly instead of being silently ignored.
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

    Checked against dicts alone, so ``iterate:`` (whose keys are already
    restricted) cannot be disabled wholesale -- a scenario varies what the
    pipeline does, not whether half of it exists.
    """
    return not (isinstance(step_cfg, dict) and step_cfg.get(_ENABLED) is False)


def iteration_plan(
    steps_cfg: object, override: int | None = None
) -> tuple[list[tuple[str, int]], dict[tuple[str, int], dict]]:
    """Expand the config into the execution plan, one entry per run of a step.

    Returns ``(plan, configs)``: the ordered ``[(step, iteration)]`` list, and the
    config block behind each entry.

    A step's iteration comes from where it is written inside ``iterate:``, and
    from nothing else:

    - Before ``iteration_zero_begins``: iterations 1..count only.
    - At or after it: every iteration 0..count, unless ``only_iteration:`` or
      ``skip_iteration:`` narrows that.
    - Anything outside ``iterate:`` runs once, where it is written: at
      iteration 1 before the loop, at the final iteration after it.
    """
    plan: list[tuple[str, int]] = []
    configs: dict[tuple[str, int], dict] = {}
    seen_iterate = False
    current = 1

    def add(name: str, it: int, cfg: dict) -> None:
        if (name, it) in configs:
            msg = (
                f"Step {name!r} is defined twice for iteration {it}. Two runs "
                f"of a step must land at different iterations -- pin one with "
                f"`{_ONLY_ITERATION}:`/`{_SKIP_ITERATION}:`, or rename it."
            )
            raise ValueError(msg)
        configs[(name, it)] = cfg
        plan.append((name, it))

    for name, step_cfg in normalize_steps(steps_cfg):
        if name == _ITERATE:
            if seen_iterate:
                msg = f"`{_ITERATE}` is declared twice; it is the whole of the run's feedback loop."
                raise ValueError(msg)
            seen_iterate = True
            count, body, zero_idx = iterate_block(step_cfg, override)
            for i in range(0, count + 1):
                for idx, (body_name, body_cfg) in enumerate(body):
                    if idx < zero_idx:
                        if i == 0:
                            continue  # not part of the warm start
                    else:
                        only = body_cfg.get(_ONLY_ITERATION)
                        if only is not None and i != int(only):
                            continue
                        skip_it = body_cfg.get(_SKIP_ITERATION)
                        if skip_it is not None and i == int(skip_it):
                            continue
                    add(body_name, i, body_cfg)
            current = count
        else:
            _reject_iteration_key(name, step_cfg)
            add(name, current, step_cfg)

    return plan, configs


def _reject_iteration_key(name: str, step_cfg: dict) -> None:
    """A step's iteration comes from where it is written, never from a key.

    ``iteration:`` was how a step pinned its own round before ``iterate:``'s
    ``iteration_zero_begins``/``only_iteration:``/``skip_iteration:`` existed.
    Refused rather than ignored, so a config written against the older shape
    fails loudly instead of quietly running at the wrong iteration.
    """
    if "iteration" not in step_cfg:
        return
    msg = (
        f"Step {name!r} declares `iteration:`, which is not a step key. "
        f"Iterations come from position inside `{_ITERATE}:` -- before or after "
        f"`{_ITERATION_ZERO_BEGINS}`, and `{_ONLY_ITERATION}:`/"
        f"`{_SKIP_ITERATION}:` for the few steps that need pinning -- or from "
        f"where a step outside `{_ITERATE}:` is written."
    )
    raise ValueError(msg)


def iterate_block(
    it_cfg: object, override: int | None
) -> tuple[int, list[tuple[str, dict]], int]:
    """Validate the ``iterate:`` block and return ``(count, body, zero_idx)``.

    *body* excludes the ``iteration_zero_begins`` marker itself; *zero_idx* is
    the index in *body* at or after which a step runs at iteration 0 too (equal
    to ``len(body)`` when there is no marker, i.e. no step runs at iteration 0).

    The body is checked here for the keys the loop refuses -- see
    :func:`iteration_plan` -- and the block itself for keys it does not take, so
    a config written for a removed mechanism fails loudly.
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
            f"only `count` and `steps`. A step that runs once regardless of "
            f"iteration is written outside `{_ITERATE}:`, before or after it; "
            f"either way it may declare `{_SKIP_IF_EXISTS}:`."
        )
        raise ValueError(msg)

    count = int(override if override is not None else it_cfg.get("count", 1))
    if count < 1:
        msg = f"{_ITERATE}.count must be >= 1, got {count}"
        raise ValueError(msg)

    raw_body = normalize_steps(it_cfg.get("steps") or [], where=f"{_ITERATE}.steps")
    if not raw_body:
        msg = f"`{_ITERATE}` declares no steps; the loop body cannot be empty."
        raise ValueError(msg)

    body: list[tuple[str, dict]] = []
    zero_idx = len(raw_body)
    marker_seen = False
    for body_name, body_cfg in raw_body:
        if body_name == _ITERATION_ZERO_BEGINS:
            if marker_seen:
                msg = (
                    f"`{_ITERATION_ZERO_BEGINS}` is declared twice inside "
                    f"`{_ITERATE}`; it can mark only one point in the pipeline."
                )
                raise ValueError(msg)
            marker_seen = True
            zero_idx = len(body)
            continue
        body.append((body_name, body_cfg))

    for body_name, body_cfg in body:
        if "iteration" in body_cfg:
            msg = (
                f"Step {body_name!r} declares `iteration:` inside `{_ITERATE}`, "
                f"whose iterations are numbered by the loop itself."
            )
            raise ValueError(msg)
        if _SKIP_IF_EXISTS in body_cfg and body_cfg.get(_ONLY_ITERATION) is None:
            msg = (
                f"Step {body_name!r} declares `{_SKIP_IF_EXISTS}` inside "
                f"`{_ITERATE}` without `{_ONLY_ITERATION}:`. It would run at "
                f"more than one iteration, landing on the same path every time, "
                f"so an existence check cannot tell one iteration's product "
                f"from another's. Pin it with `{_ONLY_ITERATION}: <n>` if it "
                f"truly runs once, or drop `{_SKIP_IF_EXISTS}`."
            )
            raise ValueError(msg)

    return count, body, zero_idx


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
    would be numbered 1 -- and an iteration-0 step run as iteration 1 writes
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
