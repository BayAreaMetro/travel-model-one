"""Step orchestrator — runs steps declared in scenario_config.yaml.

Each step is a module (or any object) exposing ``run(scenario_dir, cfg, **kwargs)``.
Steps run in the order written.  ``steps:`` is a list of ``name: {config}`` entries
(a mapping also works, but only the list form can name a step twice -- the warm
start and the loop each carry their own copy of the assignment steps).  "What runs,
and when" is answerable by reading the config top to bottom.

Two entries nest, and they are the only ones::

    steps:
      - copy_inputs: {...}          # runs once, where it is written
      - warmstart:                  # runs once, at iteration 0
          - hwy_assign: {job: ..., skip_if_exists: "hwy/iter0/LOADEA.net"}
      - iterate:                    # rounds 1..count
          count: 3
          steps:
            - hwy_assign: {job: ...}
      - summarize: {...}            # runs once, at the final round

``warmstart:`` is ``RunModel.bat``'s ``set ITER=0`` pass: assign the staged demand
once, so round 1 has congested skims to read.  A step's round is decided by where
it is written and nowhere else -- there is no per-step ``iteration:`` key.

A step outside ``iterate:`` may declare ``skip_if_exists: <path>`` -- its work is
done when that file is on disk, so a rerun walks past it and a deleted file forces
a rebuild.  The key is refused inside ``iterate:``: the loop is the part of the run
that always re-runs, and its outputs land on the same paths every round, so an
existence check cannot tell this round's product from the last one's.

A scenario may add its own steps -- typically pre- or post-processing -- by
pointing at Python code::

    steps:
      copy_inputs: {...}
      simulate_ctramp: {...}
      assignment: {...}
      vmt_vht_metrics:
        script: "hooks.py:vmt_vht_metrics"     # path, relative to the scenario dir
      trip_length_report:
        module: "mtc_local.reports:trip_lengths"   # importable dotted path

There is no separate "hook" concept: a pre-processing step is one written before
the step it prepares for, a post-processing step one written after.  Custom steps
get the same contract as built-in ones -- the same resolved ``cfg``, the same
``**kwargs``, the same ``"skipped"`` return sentinel -- and can be targeted
individually with ``tm1 run --steps <name>``.

``script``/``module`` may name the function after a colon; without one, ``run`` is
used, matching the built-in steps.  Naming it lets one file hold several steps.

A step may instead run a program the harness cannot call in-process — a Cube
``.job``, or anything else, spawned as a subprocess::

    steps:
      set_tolls:
        job: "CTRAMP/scripts/preprocess/SetTolls.job"    # relative to proj_dir
      csv_to_dbf:
        command: "CTRAMP/scripts/preprocess/csvToDbf.py"
        args: ["hwy/tolls.csv", "hwy/tolls.dbf"]

**Writing the code yourself? Use ``script:`` or ``module:``.**  They are imported
and called with the resolved ``cfg``, so the step can pass values to later steps
and return ``"skipped"``.  ``command:`` gets none of that -- only argv, an
environment, and an exit code -- and exists for programs the harness does not own,
today the legacy ``RunModel.bat`` corpus.  Pointing ``command:`` at something in the
scenario directory is an error naming ``script:``, because that is where your own
code lives.

``job:``/``command:`` are executed rather than imported, so they name no entrypoint
and resolve against ``proj_dir`` rather than the scenario directory — that is the
directory ``RunModel.bat`` ran its artifacts from, and every one of them assumes it.
See :mod:`tm1.steps.external`.

Built-in step names always win: a scenario can add steps but never redefine one.

``cfg`` is shared across steps, so a step *may* modify it to pass computed values
downstream (a pre-processing step that resolves a path for the step after it, for
example).  This is supported; it also means an ill-behaved step can affect later
ones.
"""

import importlib
import importlib.util
import logging
import os
import sys
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from types import ModuleType

import tm1.steps.assignment as assignment_step
import tm1.steps.configure_ctramp as configure_ctramp_step
import tm1.steps.external as external_step
import tm1.steps.setup as setup_step
import tm1.steps.simulate_ctramp as simulate_ctramp_step
from tm1 import add_run_logfile, remove_run_logfile, slack
from tm1.config import load_config, resolve_templates
from tm1.slack import notify

log = logging.getLogger(__name__)


def _fmt_elapsed(seconds: float) -> str:
    """Format elapsed time as human-readable string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h{m:02d}m"


#: Built-in steps, mapped to the callable that runs each one.  Values are plain
#: callables so a single module can supply several steps, and so built-in and
#: scenario-supplied steps resolve to exactly the same kind of thing.
STEPS: dict[str, Callable] = {
    "copy_inputs": setup_step.run,
    "configure_ctramp": configure_ctramp_step.run,
    "simulate_ctramp": simulate_ctramp_step.run,
    "assignment": assignment_step.run,
}

DEFAULT_STEPS = list(STEPS.keys())

#: Keys a scenario uses to point a step at code the runner does not supply.
#: ``script``/``module`` are imported and called; ``job``/``command`` are spawned
#: (see :mod:`tm1.steps.external`).  Order matters only for the error messages.
_CUSTOM_KEYS = ("script", "module", *external_step.KEYS)

#: Function called on a custom step's module when none is named after a colon.
_DEFAULT_ENTRYPOINT = "run"


def _split_entrypoint(target: str) -> tuple[str, str]:
    """Split ``"hooks.py:vmt_vht_metrics"`` into target and function name.

    Only splits when the trailing segment is a Python identifier, so Windows
    drive letters survive: ``E:/runs/prep.py`` keeps its colon, because
    ``/runs/prep.py`` is not an identifier.
    """
    head, sep, tail = target.rpartition(":")
    if sep and tail.isidentifier():
        return head, tail
    return target, _DEFAULT_ENTRYPOINT


def _load_script(path: Path, scenario_dir: Path) -> ModuleType:
    """Import a ``.py`` file as a module, without putting its directory on sys.path.

    The module is registered under a name qualified by the scenario, so two
    scenarios that both ship a ``preprocess.py`` do not collide in
    ``sys.modules``.
    """
    spec = importlib.util.spec_from_file_location(
        f"tm1_scenario_{scenario_dir.name}_{path.stem}", path
    )
    if spec is None or spec.loader is None:
        msg = f"Could not load step script as a Python module: {path}"
        raise ImportError(msg)
    mod = importlib.util.module_from_spec(spec)
    # Registered before exec so the module can import itself / pickle cleanly.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


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


def _normalize_steps(steps_cfg: object, where: str = "steps") -> list[tuple[str, dict]]:
    """Ordered ``(name, config)`` pairs from either shape of ``steps:``.

    A mapping is the compact form.  A list of single-key mappings is the explicit
    form -- and the only one that can name the same step twice, which is how the
    warm start and the loop each carry their own copy of the assignment steps.
    """
    if isinstance(steps_cfg, dict):
        return [(str(name), cfg or {}) for name, cfg in steps_cfg.items()]
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
            pairs.append((str(name), cfg or {}))
        return pairs
    msg = f"`{where}` must be a mapping or a list of `name: {{config}}` entries."
    raise TypeError(msg)


def _iteration_plan(
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

    for name, step_cfg in _normalize_steps(steps_cfg):
        if name == _WARMSTART:
            _check_block_placement(name, seen)
            for body_name, body_cfg in _warmstart_block(step_cfg):
                add(body_name, _WARMSTART_ROUND, body_cfg)
        elif name == _ITERATE:
            _check_block_placement(name, seen)
            count, body = _iterate_block(step_cfg, override)
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


def _warmstart_block(ws_cfg: object) -> list[tuple[str, dict]]:
    """Validate the ``warmstart:`` block and return its body.

    A bare list of steps, not a block with keys.  The only thing it says is *these
    run at iteration 0*, and unlike ``iterate:`` there is no ``count`` to state, so
    a ``steps:`` wrapper would be a level of nesting carrying no information.
    """
    # `ws_cfg` is truthy here so an empty block falls through to the check below:
    # `_normalize_steps` turns an empty list into `{}`, which is a subset of anything.
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

    body = _normalize_steps(ws_cfg or [], where=_WARMSTART)
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


def _iterate_block(
    it_cfg: object, override: int | None
) -> tuple[int, list[tuple[str, dict]]]:
    """Validate the ``iterate:`` block and return ``(count, body)``.

    The body is checked here for the two keys the loop refuses -- see
    :func:`_iteration_plan` -- and the block itself for keys it does not take,
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

    body = _normalize_steps(it_cfg.get("steps") or [], where=f"{_ITERATE}.steps")
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


def _skip_target(step_cfg: dict, cfg: dict) -> Path | None:
    """The declared product that lets this step skip itself, if it is on disk.

    ``skip_if_exists:`` is a statement in the config -- *this step's work is done
    when this file exists* -- and the check is exactly that, nothing inferred.
    Deleting the file forces a rebuild.  Relative paths resolve against
    ``proj_dir``, where every model artifact lives.
    """
    declared = step_cfg.get(_SKIP_IF_EXISTS)
    if not declared:
        return None
    path = Path(str(declared)).expanduser()
    if not path.is_absolute():
        path = Path(cfg["proj_dir"]) / path
    return path if path.exists() else None


def _fmt_plan(plan: list[tuple[str, int]], n_iters: int) -> str:
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
            f"Planned: {_fmt_plan(plan, n_iters)}\n"
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


def _apply_until(
    plan: list[tuple[str, int]], until: str | None
) -> list[tuple[str, int]]:
    """Drop everything after *until*, which itself **runs**.

    The mirror of :func:`_apply_resume`, and composable with it -- together they
    name any contiguous slice of the plan.  Naming a boundary rather than listing
    steps is what keeps this usable as the pipeline grows: ``--until
    0:publish_networks`` is the whole warm start however many steps that is.
    """
    if not until:
        return plan
    return plan[: _match_token(plan, until, "--until") + 1]


def _select_steps(
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
                f"Planned: {_fmt_plan(plan, n_iters)}"
            )
            raise ValueError(msg)
        wanted.update(hits)

    return [entry for entry in plan if entry in wanted]


def _apply_resume(
    plan: list[tuple[str, int]],
    resume_at: str | None,
    proj_dir: str | Path | None = None,
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
    if proj_dir is not None:
        p = Path(proj_dir)
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
            f"Planned: {_fmt_plan(plan, n_iters)}\n"
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


def _resolve_slack_level(cfg: dict, slack_level: str | bool | None) -> None:
    """CLI flag wins, then the scenario's `slack:` key, then "minimal"."""
    if slack_level is not None:
        slack.level = "verbose" if slack_level is True else slack_level
        return
    cfg_slack = cfg.get("slack", "minimal")
    slack.level = cfg_slack if isinstance(cfg_slack, str) else "off"


def _report_step(label: str, name: str, result: object, elapsed: float) -> None:
    """Record a finished step, distinguishing a real run from a self-skip."""
    if result == "skipped":
        notify(f"[{label}] {name} already done, skipped")
        log.info("--- Skipped: %s ---", name)
        return
    elapsed_str = _fmt_elapsed(elapsed)
    notify(f"[{label}] {name} done ({elapsed_str})")
    log.info("--- Done: %s (%s) ---", name, elapsed_str)


def _report_resume(
    full_plan: list[tuple[str, int]], plan: list[tuple[str, int]], n_iters: int
) -> None:
    """State what a resumed run will skip and run, before it does any of it.

    Printed up front so a mistyped iteration is caught by reading the skipped
    list -- resuming at ``3:assignment`` would show ``simulate_ctramp@3`` as
    skipped, i.e. about to assign demand that was never generated.
    """
    if len(plan) >= len(full_plan):
        return
    skipped = full_plan[: len(full_plan) - len(plan)]
    log.info("Resuming at %s, iteration %d of %d", plan[0][0], plan[0][1], n_iters)
    log.info("  skipping %d already-completed step(s): %s",
             len(skipped), _fmt_plan(skipped, n_iters))
    log.info("  running %d: %s", len(plan), _fmt_plan(plan, n_iters))


def _notify_start(
    label: str, steps: list[str], configs: dict[tuple[str, int], dict],
    n_iters: int, kwargs: dict,
) -> None:
    """Announce what is about to run.

    Reads the demand step's config off the plan entries: it sits inside
    ``iterate``, so a top-level lookup would silently report defaults.
    """
    sim_cfg = next(
        (
            entry_cfg for (name, _), entry_cfg in configs.items()
            if name in ("simulate_ctramp", "simulate_activitysim")
        ),
        {},
    )
    sample_rate = kwargs.get("sample_rate") or sim_cfg.get("sample_rate")
    sample_str = "per-iteration ramp" if sample_rate is None else f"{sample_rate:.0%}"
    notify(
        f":rabbit2: Starting {label}\n"
        f"  • steps: {', '.join(steps)}\n"
        f"  • sample: {sample_str} | threads: {sim_cfg.get('threads', 1)} | "
        f"shadow pricing: {'on' if sim_cfg.get('shadow_pricing', False) else 'off'}\n"
        f"  • iterations: {n_iters}"
    )


def _start_run_log(cfg: dict, label: str, steps: list[str]) -> logging.Handler | None:
    """Open a per-run log file under ``{proj_dir}/logs`` and record what is starting.

    ``RunModel.bat`` appended a line to ``logs/feedback.rpt`` per milestone; this
    keeps the whole run instead -- every step boundary, every Cube job result and
    any traceback -- at DEBUG, while the console stays at INFO.

    The filename carries a timestamp so concurrent or repeated runs never write
    into each other's log, and so a failed run's log survives the next attempt.
    Returns None when no ``proj_dir`` is configured, leaving console-only logging.
    """
    proj_dir = cfg.get("proj_dir")
    if not proj_dir:
        return None

    log_cfg = cfg.get("logging", {}) or {}
    log_dir = Path(log_cfg.get("dir") or Path(proj_dir) / "logs")
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")

    # pid separates concurrent runs on one machine; the counter separates runs
    # started within the same second.  FileHandler appends, so a name collision
    # would silently merge two runs into one log.
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"tm1_{stamp}_{os.getpid()}.log"
    attempt = 1
    while path.exists():
        path = log_dir / f"tm1_{stamp}_{os.getpid()}_{attempt}.log"
        attempt += 1

    level = getattr(logging, str(log_cfg.get("level", "DEBUG")).upper(), logging.DEBUG)
    handler = add_run_logfile(path, level=level)

    log.info("Run log: %s", path)
    log.debug("scenario=%s  steps=%s", label, ", ".join(steps))
    log.debug("proj_dir=%s", proj_dir)
    return handler


def _sole_custom_key(step_name: str, declared: list[str]) -> str:
    """The one custom key a step declares, or an error explaining the alternatives."""
    if len(declared) > 1:
        named = ", ".join(repr(k) for k in declared)
        msg = f"Step {step_name!r} declares {named}; use exactly one."
        raise ValueError(msg)

    if not declared:
        msg = (
            f"Unknown step: {step_name!r}. Built-in steps are "
            f"{', '.join(STEPS)}. To run your own code, give the step a "
            f"'script:' (path relative to the scenario directory) or a "
            f"'module:' (importable dotted path) -- both imported and called. To "
            f"spawn a program the harness does not own, give it a 'job:' (Cube "
            f".job) or a 'command:', both relative to proj_dir."
        )
        raise ValueError(msg)

    return declared[0]


def _load_step(step_name: str, step_cfg: dict | None, scenario_dir: Path) -> Callable:
    """Resolve one step's config block to the callable that runs it.

    Takes the block itself rather than a name to look up, because a name may
    appear more than once in the plan -- the entry identifies the step.

    Built-in steps take precedence.  Anything else declares either native Python
    (``script:``, a path relative to the scenario directory, or ``module:``, an
    importable dotted path, each optionally naming a function after a colon) or a
    legacy artifact to run in place (``job:``/``command:``, relative to
    ``proj_dir``).
    """
    declared = (
        [k for k in _CUSTOM_KEYS if k in step_cfg] if isinstance(step_cfg, dict) else []
    )

    if step_name in STEPS:
        if declared:
            msg = (
                f"Step {step_name!r} is built in and cannot be redefined by "
                f"{declared[0]!r}. Rename the custom step, or drop the "
                f"{declared[0]!r} key to use the built-in."
            )
            raise ValueError(msg)
        return STEPS[step_name]

    key = _sole_custom_key(step_name, declared)

    # Legacy artifacts are executed, not imported: there is no module to load and
    # no entrypoint to name, so they resolve before the import machinery below.
    if key in external_step.KEYS:
        log.info("Step %s -> legacy %s at %s", step_name, key, step_cfg[key])
        return external_step.make_step(step_name, step_cfg)

    target, func_name = _split_entrypoint(step_cfg[key])

    if key == "module":
        mod = importlib.import_module(target)
    else:
        path = Path(target).expanduser()
        if not path.is_absolute():
            path = scenario_dir / path
        if not path.is_file():
            msg = f"Step {step_name!r}: script not found: {path}"
            raise FileNotFoundError(msg)
        mod = _load_script(path, scenario_dir)
        target = str(path)

    source = f"{target}:{func_name}"
    if not hasattr(mod, func_name):
        named = "" if func_name == _DEFAULT_ENTRYPOINT else f" (named by {step_name!r})"
        msg = (
            f"Step {step_name!r}: {target} defines no {func_name}(){named}. Steps "
            f"need 'def {func_name}(scenario_dir, cfg, **kwargs)', the same "
            f"contract as the built-in steps."
        )
        raise AttributeError(msg)

    func = getattr(mod, func_name)
    if not callable(func):
        msg = f"Step {step_name!r} ({source}): {func_name!r} is not callable."
        raise TypeError(msg)

    log.info("Step %s -> custom code at %s", step_name, source)
    return func


def run_model(
    scenario_dir: Path,
    steps: list[str] | None = None,
    slack_level: str | bool | None = "minimal",
    **kwargs: object,
) -> None:
    """Run a sequence of pipeline steps for a scenario.

    Parameters
    ----------
    scenario_dir : Path
        Path to the scenario directory.
    steps : list[str], optional
        Steps to run.  If None, uses step keys from config or DEFAULT_STEPS.
    slack_level : str
        "false", "minimal", or "verbose".
    **kwargs
        Passed through to each step's ``run()`` function.
        Common: ``base_model_dir``, ``force``.
    """
    scenario_dir = Path(scenario_dir).resolve()
    label = f"scenarios/{scenario_dir.name}"

    cfg = resolve_templates(load_config(scenario_dir))

    _resolve_slack_level(cfg, slack_level)

    steps_cfg = cfg.get("steps") or {name: {} for name in DEFAULT_STEPS}  # pyright: ignore[reportAttributeAccessIssue]

    # Always the config's whole plan: `--steps`, `--resume-at` and `--until`
    # select from it rather than defining one, so a step keeps the round it
    # actually belongs to.  `--iterations N` overrides iterate.count.  Built
    # before the run log opens: a config error is a console conversation, not
    # a run.
    full_plan, configs = _iteration_plan(steps_cfg, override=kwargs.get("iterations"))

    declared = list(dict.fromkeys(name for name, _ in full_plan))
    log_handler = _start_run_log(cfg, label, steps or declared)
    t0_total = time.time()

    try:
        n_iters = max((i for _, i in full_plan), default=1)
        plan = _select_steps(full_plan, steps)
        plan = _apply_resume(plan, kwargs.get("resume_at"), cfg.get("proj_dir"))
        plan = _apply_until(plan, kwargs.get("until"))
        _report_resume(full_plan, plan, n_iters)
        prev_iter = None
        _notify_start(label, steps or declared, configs, n_iters, kwargs)

        for name, iteration in plan:
            step_cfg = configs[(name, iteration)]

            # The step's declared product is already on disk: its work is done.
            # Announced before the skip check, not after: a skipped step still
            # belongs to its round, and anything placing it by the last banner --
            # a reader, or `tm1 status` -- would file it under the previous one.
            if n_iters > 1 and iteration != prev_iter:
                log.info("=== Iteration %d of %d ===", iteration, n_iters)
                prev_iter = iteration

            skip = _skip_target(step_cfg, cfg)
            if skip is not None:
                # The round is on the line so `tm1 status` can place a step in the
                # plan exactly, rather than inferring it from position -- a resumed
                # run starts mid-plan, where position alone is ambiguous.
                log.info(
                    "--- Step: %s (iteration %d) -- skipped, %s exists ---",
                    name, iteration, skip,
                )
                notify(f"[{label}] {name} skipped ({skip.name} exists)")
                continue

            run_step = _load_step(name, step_cfg, scenario_dir)

            log.info("--- Step: %s (iteration %d) ---", name, iteration)
            t0_step = time.time()
            try:
                # Merged rather than passed positionally: an explicit caller-supplied
                # `iteration` would otherwise be a duplicate-keyword TypeError.
                # `step_cfg` is the entry's own block -- with `steps:` as a list a
                # name may appear twice, so the entry, not the name, identifies it.
                result = run_step(
                    scenario_dir, cfg,
                    **{
                        **kwargs,
                        "iteration": iteration,
                        "step_name": name,
                        "step_cfg": step_cfg,
                    },
                )
            except KeyboardInterrupt:
                log.warning("Cancelled during %s", name)
                notify(f":no_entry_sign: {label} cancelled during {name}")
                raise
            except Exception as e:
                # exc_info so the run log keeps the traceback, not just the message
                log.exception("Step %s failed: %s", name, e)  # noqa: TRY401
                # The failed step did not finish, so resuming includes it.
                log.error(  # noqa: TRY400 -- traceback already logged above
                    "Resume with: tm1 run --scenario %s --resume-at %s",
                    scenario_dir.name,
                    resume_token(full_plan, name, iteration),
                )
                notify(f":exclamation: {label} failed at {name}: {e}")
                raise
            _report_step(label, name, result, time.time() - t0_step)

        total = time.time() - t0_total
        # Logged as well as notified: it is how `tm1 status` tells a finished run
        # from one that stopped on the last step it happened to reach.
        log.info("=== Finished %s in %s ===", label, _fmt_elapsed(total))
        notify(f"Finished {label} in {_fmt_elapsed(total)} :white_check_mark:")
    finally:
        # Detached even on failure, so the log is flushed and a second run in the
        # same process does not append to it.
        remove_run_logfile(log_handler)
