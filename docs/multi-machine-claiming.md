# Multi-machine claiming

Status: **not built.** This is the rough scope only so far.

## The problem

A study is many scenarios. Eight scenarios at ~15 h each is five days on one box, and the
runs are already independent and individually named — `tm1 scenarios` lists them, each gets
its own directory, nothing is shared. What is missing is a way to hand them out without two
people starting the same one, and without logging into every machine to do it manually.
Defined once upfront in a yaml, then distributed.

## Constraints

- One repo clone, on the shared network drive. It is a **deployment, not a working tree**:
  read-only to the group, writable only by whoever runs the pull, so a stray `git checkout`
  cannot land mid-run.
- Results land on the shared network drive.
- Hot data is copied to each machine and stays there.

The venv is the exception — each machine builds its own from the share's `uv.lock`, and the
agent runs `uv sync --frozen` between runs, never during one. One venv on the share cannot
work: Windows locks a loaded `.pyd` for the life of the process using it, so a machine
mid-run would block the update and a half-applied sync would break every box at once.

## Where things live

```
share   //models.ad.mtc.ca.gov/data/models          TM1_M_DRIVE
  repo/          one clone, deployed
  inputs/        staged per scenario
  tm1/index/     .work / .claim / .beat             the only channel between machines
  archive/       publish_outputs `to:`              ~2 GB per run

machine   model3-a, model3-b, ...
  C:/tm1venv     its own venv, from the share's uv.lock
  E:/runs/       run directories, ~100 GB each      TM1_RUNS_ROOT
```

Runs go on local disk: Cube Cluster is chatty and a network path is slow.

`MAX_RUN_DIR_LEN` is 70 in `run/directory.py` — Cube and the Java stack are not long-path
aware, and a run nests roughly 160 characters below its own root.

    E:/runs/2050_TM161_FBP_Plan_16_001   = 34

`max_run_dir_len` overrides the 70, per environment or per machine, since it depends on the
length of that box's runs root.

The archive destination is a `publish_outputs` entry in each project's `scenarios.yaml`,
not a machine setting — different studies publish to different folders. Its acceptance test
is already in the model: a scenario warmstarts from a previous run's `OUTPUT/main`, so **an
archived run must be usable as the next study's warmstart.**

Reclaiming local disk means deleting a run directory's contents but **keeping `.tm1/`**, so
`allocate()` still reports `COMPLETE` and the next `tm1 run` does not redo fifteen hours of
work already archived. Manual, never automatic.

## The machine registry

`default-configs/environments/<name>.yaml`, committed, selected by `tm1 run --env <name>`
or `TM1_ENV`, `mtc` by default. One file defines a machine once: paths, compute sizing, and
whether it takes work.

```yaml
defaults:
  env:
    TM1_M_DRIVE:            //models.ad.mtc.ca.gov/data/models
    TM1_RUNS_ROOT:          E:/runs
    TM1_GAWK_DIR:           C:/Program Files/Git/usr/bin
    TM1_R_HOME:             C:/Program Files/R/R-4.3.1
    TM1_SLACK_WEBHOOK_FILE: "{m_drive}/Software/Slack/TravelModel_SlackWebhook.txt"
  compute:
    hwy_assign.cluster_nodes: 48
    simulate_ctramp.threads:  24
  max_run_dir_len: 70

machines:
  tm2-b:
  model3-a:
  model3-b:
  model3-c:
  model3-d:
  model3-g:
    env:     {TM1_RUNS_ROOT: E:/Model3G-Share/runs}
  model2-a:
    env:     {TM1_RUNS_ROOT: F:/runs}
    compute: {hwy_assign.cluster_nodes: 16}
  model2-c:
  model2-d:
  mainmodel:
    enabled: false        # parked; claims nothing
```

A bare name still counts: `--on all` needs a roster, and a dead agent should show as
missing rather than be invisible. An agency that is not MTC adds a sibling file with its
own roster rather than editing this one. `config.py::_load_environment` merges
`defaults.env` with `machines[host].env` and applies the result with `setdefault`, instead
of reading top-level keys.

Shared paths are written in full — `//server/share/...`, never a mapped letter like `M:`.
Drive letters are assigned per login session, so a hostname key cannot predict them.

### The invariant

`run/fingerprint.py` already names the keys a machine may tune without making its output
incomparable with another machine's: `cluster_nodes`, `threads`, `intrastep_processes`,
`acc_threads`, `timeout`, `commpath`. That set is exactly the registry's write scope —
**a `compute:` address outside the fingerprint's skip-list is a validation error**, so the
registry cannot change a result.

Two of those keys do not belong in it:

- `acc_threads` patches `num.acc.threads` in `accessibilities.properties`, which nothing
  reads. The logsums step runs `MTCCreateLogsums logsums` against `logsums.properties`,
  whose copy of that key `RuntimeConfiguration.py --logsums` writes. That script is the
  lever, if one is ever wanted.
- `intrastep_processes` selects a file rather than counting anything, and exactly two exist
  (`HwyIntraStep_48.block`, `_64.block`). Exceeding `hwy_assign.cluster_nodes` makes
  HwyAssign address processes that were never started, so it is **derived**: the largest
  available block ≤ `cluster_nodes`.

### Resolution order

Process environment → `machines[host]` → `defaults`. The registry only sets what is unset,
so a box can be overridden in an emergency without a commit.

**An unknown hostname must run, not refuse** — fall through to `defaults:` with a warning
naming the host and the file. `RuntimeConfiguration.py` was retired precisely because an
unknown host was a hard stop and `tm2-b` was not on its list.

## How a machine gets work

Nothing connects to another machine: no remote execution, no credentials, no background
service. Each machine reads the shared drive for work rather than being sent it.

    — on any machine —
    $ tm1 run PBA50+_FBP --scenario 2023_TM161_IPA_16 2050_TM161_FBP_Plan_16 \
                         --on model3-a model3-b

      writes two files, exits 0, contacts nothing

    — index/PBA50+_FBP/2050_TM161_FBP_Plan_16.work —
    {"scenario": "2050_TM161_FBP_Plan_16", "fingerprint": "a3f9c2…",
     "on": ["model3-a", "model3-b"], "queued": "...", "by": "..."}

    — on model3-a, 30-second timer —
    os.listdir(index)                      # .work with no .claim, "on" contains me
    os.open(<id>.claim, O_CREAT | O_EXCL)  # model3-b races and loses; takes the other
    run_model(config_dir, scenario=...)    # locally, into the machine's runs root

      then: mirror .tm1/scenario.json to the index on each state change,
            touch index/model3-a.beat every five minutes

`O_CREAT` and `O_EXCL` are standard flags on `os.open()`: create the file, and fail if it
already exists rather than opening it. The file server settles the race — one machine
creates `<id>.claim` and owns that scenario, the rest get `FileExistsError` and move on.
No lock service, no queue. `run/directory.py` already allocates run numbers the same way,
via `mkdir(exist_ok=False)`.

Nothing new is written to disk for any of this. `run/receipt.py` already produces
`.tm1/scenario.json` with `project`, `scenario`, `run`, `fingerprint`, `machine`, `pid` and
`status`; mirroring it into the index is a copy, not a schema. A heartbeat is an empty file
judged by its last-modified time, and Windows domain logins already hold every clock within
five minutes of the domain controller's, so a twenty-minute staleness threshold needs no
clock protocol.

## Command surface

    tm1 run <project> --scenario 2023_TM161_IPA_16                 this machine, foreground
    tm1 run <project> --scenario '2050_*' --on model3-a model3-b   n scenarios, named machines
    tm1 run <project> --on all                                     everything, everyone
    tm1 run                                                        the agent: take what I am given
    tm1 status [<project>]                                         + machine roster block
    tm1 release <project>:<scenario>                               hand a held scenario back

- `--scenario` takes one ID today; claiming needs several, and globs, resolved against the
  project's declared scenarios.
- `--on` defaults to this machine, so `tm1 run <project>` keeps its current behaviour.
  Naming other machines is the explicit case, and so is `--on all`.
- `--on` **filters, it does not assign**: whichever named machine frees up next takes the
  next scenario. Pinning idles a free box and re-invents the shard counts claiming exists
  to avoid.
- Every run takes a claim, local ones included — otherwise a person and this box's own
  agent start the same scenario twice. A sole local target still runs in the foreground.
- A failed scenario stays `HELD` on the machine that failed it. No auto-reclaim: a box
  someone is debugging on does not get work pushed back at it.

### Per machine, once

    uv venv C:\tm1venv
    $env:UV_PROJECT_ENVIRONMENT = "C:\tm1venv"; uv sync
    schtasks /create /tn "tm1 agent" /sc onlogon /rl highest ^
             /tr "C:\tm1venv\Scripts\tm1.exe run"

Set the task to restart on failure. That is the supervisor, and it is why the agent can run
scenarios in-process rather than needing subprocess isolation. No clone and no local config
file: the box is one line in the committed environment file, with a body only if its runs
disk or cluster size differs from `defaults:`.

## Deliberately not built

- Remote execution of any kind: logging into one machine to start work on another.
- A Windows service, or any long-lived process that is not `tm1` itself.
- A message queue or network protocol between machines. The shared drive is the only
  channel.
- Capability-based scheduling. Scenarios are not routed by machine size.
- Auto-reclaim of failed scenarios.
- Versioned shared venvs. Revisit only if two dependency sets must be live at once.

## Commit order

1. `machines:` and `defaults:` in `environments/<name>.yaml`, loader, validation, with the
   migration note.
2. Derive `intrastep_processes`; drop `acc_threads` from the registry; `max_run_dir_len`.
3. `--scenario` takes several IDs and globs.
4. Shared index — work list, claim, heartbeat, receipt mirror. The riskiest commit; needs
   the exclusive-create test answered first.
5. `--on`, roster filter, status roster block.
6. Agent loop and the per-machine setup doc.

Orchestration must never become a prerequisite for proving parity.

## Risks and open questions

**Queued work can stall silently.** If the agent is not running on a box, its work sits
queued and nothing errors. That is the cost of having no push channel, and it is why the
roster and the heartbeat exist — `tm1 status` shows the queued scenario next to
`model3-d — no heartbeat since 09:14`.

**Can Cube get a Bentley license from a scheduled task?** If a task in session 0 cannot
obtain one, the boxes must stay logged in with the task set to *run only when user is
logged on* — a policy conversation with whoever owns the machines, and share permissions
then go to a domain group of modellers rather than to machine accounts.

`cube/job.py::is_local_session` is a proxy, not a verified session check: it rules out SSH
and VS Code Remote only, so it would treat an agent under Task Scheduler as local and call
`runtpp` directly. If the license does not reach session 0, the fix is to teach that
function to recognise the agent — the relay it already uses for remote sessions
(`schtasks /it`, polling a sentinel for the exit code) is the mechanism.

**Does exclusive create work on this share?** Two Python shells racing to create the same
path; there must be exactly one winner. The design rests on the file server refusing the
second create rather than letting both through.

**The machine roster.** The list above is the four-year-old `RuntimeConfiguration` whitelist
plus `tm2-b`. Which boxes still exist, and what is the real local runs disk on each?

**Share permissions on three trees.** These are Windows ACLs — access control lists, the
per-folder record of who may read, write, create or delete. Repo: Read & Execute for the
group, Modify for the puller. Index: Modify for everyone, since creating a file is the
claim and deleting it is `tm1 release`. Archive: Write for everyone.
