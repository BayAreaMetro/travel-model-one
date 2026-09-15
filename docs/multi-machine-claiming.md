# Multi-machine claiming

Status: **not built.** This is the rough scope only so far.

## The problem

A study is many scenarios. Eight scenarios at ~15 h each is five days on one box, and the runs
are already independent and individually named — `tm1 scenarios` lists them, each gets its
own directory, nothing is shared. What is missing is a way to hand them out without two
people starting the same one, and without logging into every machine to do it manually.
Defined once upfront in a yaml, then distributed.

## What the team requires

- One repo clone, on the shared network drive.
- Results land on the shared network drive.
- Hot data is copied to each machine and stays there.

All three hold. The exception is the Python environment — the venv, the folder of
installed packages `tm1` runs from. It stays on each machine's own disk, and nothing is
copied per run:

- One venv per machine, built once. `uv.lock` on the share pins every package version, so
  `uv venv` + `uv sync` on each box produces the same set from the same file.
- The agent re-syncs between runs, never during one. `uv sync --frozen` means "make this
  venv match `uv.lock` exactly, do not re-resolve versions", so picking up a new commit is
  one command and a run always starts on the environment the lockfile names.
- Not one shared venv on the share: Windows locks a loaded `.pyd` — a compiled Python
  extension — for the life of the process using it. One machine mid-run would block the
  update, and a half-applied sync would break every machine at once.

A run started by hand is a separate process from the agent, so the agent must confirm no
run on the box is live before syncing, not just that its own last one finished.

The shared checkout is a **deployment, not a working tree**: read-only for the modelling
group, writable only by whoever runs the pull. Otherwise a stray `git checkout` lands in
the middle of a fifteen-hour run.

## Where things live

| Root | Where | Size | Purpose |
|---|---|---|---|
| `TM1_SHARED_DRIVE_ROOT` | share | — | inputs, archived results, index. Renames `TM1_M_DRIVE`. |
| `TM1_LOCAL_RUNS_ROOT` | local disk | ~100 GB/run | where the run happens. Renames `TM1_RUNS_ROOT`. |
| `{shared_drive}/tm1/index` | share, derived | KB | work list, claims, heartbeats, mirrored receipts |
| `publish_outputs` `to:` | share, per project | ~2 GB/run | the kept result, declared in `scenarios.yaml` |

The run directory cannot go on the share, and that is arithmetic rather than preference.
`MAX_RUN_DIR_LEN` is 70 in `run/directory.py`, because Cube and the Java stack are not
long-path aware and a run nests roughly 160 characters below its own root:

    //models.ad.mtc.ca.gov/data/models/   35
    runs/                                 5
    PBA50+_FBP/                          11
    BP-03-TRNF-2035-001                  19
                                       = 70   before a single file nests

    E:/runs/PBA50+_FBP/BP-03-TRNF-2035-001  = 38, comfortable

The archive destination is a `publish_outputs` entry in each project's `scenarios.yaml`,
not a machine setting: different studies publish to different folders, and it is symmetric
with `copy_inputs`, whose source paths are deliberately literal and visible. Its acceptance
test is already written into the model — a scenario warmstarts from a previous run's
`OUTPUT/main` — so **an archived run must be usable as the next study's warmstart.**

Reclaiming local disk means deleting a run directory's contents but **keeping `.tm1/`**:
the receipt survives, so `allocate()` still reports `COMPLETE` and the next `tm1 run`
does not spend fifteen hours redoing something already archived. Manual, never automatic.

## machines.yaml

At the repo root, committed. Inventory, not secrets. A machine needs a body only when it
differs from defaults; a bare name exists so `--on all` has a roster and a dead agent
shows as missing rather than being invisible.

```yaml
defaults:
  env:
    TM1_SHARED_DRIVE_ROOT:  //models.ad.mtc.ca.gov/data/models
    TM1_LOCAL_RUNS_ROOT:    E:/runs
    TM1_GAWK_DIR:           C:/Program Files/Git/usr/bin
    TM1_SLACK_WEBHOOK_FILE: "{shared_drive}/Software/Slack/TravelModel_SlackWebhook.txt"
  compute:
    hwy_assign.cluster_nodes: 48
    simulate_ctramp.threads:  24

machines:
  tm2-b:
  model3-a:
  model3-b:
  model3-c:
  model3-d:
  model2-a:
    env:     {TM1_LOCAL_RUNS_ROOT: F:/runs}
    compute: {hwy_assign.cluster_nodes: 16}
  model2-c:
  model2-d:
  mainmodel:
    enabled: false        # parked; claims nothing
```

Shared paths are written in full — `//server/share/...` — rather than as a mapped drive
letter such as `M:`. Drive letters are assigned per login session, so a hostname key
cannot predict them.

### The invariant

`run/fingerprint.py` already names the keys a machine may tune without making its output
incomparable with another machine's — `cluster_nodes`, `threads`, `intrastep_processes`,
`acc_threads`, `timeout`, `commpath`. That set is exactly the registry's write scope:
**a `compute:` address outside the fingerprint's skip-list is a validation error.** A
check, not a convention, so the registry cannot change a result.

Two of those keys turn out not to belong in it at all:

- `acc_threads` writes `num.acc.threads` for the Java calculator behind the deferred
  `RunLogsums.bat`. Nothing in this pipeline consumes it, so tuning it per machine tunes
  nothing.
- `intrastep_processes` is not a count — it selects a file, and exactly two exist
  (`HwyIntraStep_48.block`, `_64.block`). It is slaved to `hwy_assign.cluster_nodes`, and
  exceeding it makes HwyAssign address processes that were never started. So it is
  **derived**: the largest available block ≤ `cluster_nodes`.

### Resolution order

Process environment → `machines.yaml[host]` → `machines.yaml[defaults]`. The registry only
sets what is unset, so a box can be overridden in an emergency without a commit.

**An unknown hostname must run, not refuse** — fall through to `defaults:` with a warning
naming the host and the file. `RuntimeConfiguration.py` was retired precisely because an
unknown host was a hard stop and `tm2-b` was not on its list. This must not rebuild that
whitelist in better YAML.

## How a machine gets work

Nothing connects to another machine: no remote execution, no credentials, no background
service. Each machine reads the shared drive for available work rather than being sent it.

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

`O_EXCL` is the whole coordination mechanism, and it is one flag: create this file, and
fail if it already exists rather than opening it. The file server settles the race — one
machine creates `<id>.claim` and owns that scenario, the rest get `FileExistsError` and
move on. No lock service, no queue. The same mechanism already allocates run numbers in
`run/directory.py`, via `mkdir(exist_ok=False)`.

The receipt needs no new format. `run/receipt.py` already writes `.tm1/scenario.json` with
`project`, `scenario`, `run`, `fingerprint`, `machine`, `pid` and `status`; mirroring it to
the index is a copy, not a schema.

Liveness is an empty file judged by its last-modified time. Windows domain logins already
require each machine's clock to sit within five minutes of the domain controller's, so a
twenty-minute staleness threshold needs no clock protocol.

The limitation is real and worth stating: if the agent is not running on a box, its work
sits queued and nothing errors. That is the cost of having no push channel, and it is why
the roster and the heartbeat exist — `tm1 status` shows the queued scenario next to
`model3-d — no heartbeat since 09:14`.

## Command surface

One new flag, one new verb-free form, and one widening of an existing flag.

    tm1 run <project> --scenario 2023_TM161_IPA_16                 this machine, foreground
    tm1 run <project> --scenario '2050_*' --on model3-a model3-b   n scenarios, named machines
    tm1 run <project> --on all                                     everything, everyone
    tm1 run                                                        the agent: take what I am given
    tm1 status [<project>]                                         + machine roster block
    tm1 release <project>:<scenario>                               hand a held scenario back

`--scenario` takes one ID today. Claiming needs it to take several, and globs, resolved
against the project's declared scenarios. One ID with no `--on` keeps its current
behaviour.

**`--on` defaults to this machine.** It is always the targeting flag; omitting it means
`--on <this host>`, which is what `tm1 run <project>` already does today. Naming other
machines is the explicit case, and so is `--on all`.

Every run takes a claim, including a local one. Running here must not bypass the mutex —
otherwise a person and this box's own agent can start the same scenario twice. When the
target is this machine and only this machine, the run proceeds in the foreground instead
of being left for the agent to pick up.

`--on` is a **filter, not an assignment**: whichever named machine frees up next takes the
next scenario. Real pinning idles a free box while a scenario waits for its assigned
machine, and re-invents the shard counts that claiming exists to avoid.

A failed scenario stays `HELD` on the machine that failed it. No auto-reclaim — a box
someone is debugging on does not get work pushed back at it.

### Per machine, once

    uv venv C:\tm1venv
    $env:UV_PROJECT_ENVIRONMENT = "C:\tm1venv"; uv sync
    setx TM1_LOCAL_RUNS_ROOT "F:\runs"          # only if it differs from defaults
    schtasks /create /tn "tm1 agent" /sc onlogon /rl highest ^
             /tr "C:\tm1venv\Scripts\tm1.exe run"

Set the task to restart on failure. That is the supervisor, and it is why the agent can
run scenarios in-process rather than needing subprocess isolation. No clone, no
per-machine config file.

## Deliberately not built

- Remote execution of any kind: logging into one machine to start work on another.
- A Windows service, or any long-lived process that is not `tm1` itself.
- A message queue or network protocol between machines. The shared drive is the only
  channel.
- Capability-based scheduling. Scenarios are not routed by machine size.
- Auto-reclaim of failed scenarios.
- Versioned shared venvs. Revisit only if two dependency sets must be live at once.

## Before writing code

Two of these can sink the design and cost minutes to answer.

- **Can Cube get a Bentley license from a scheduled task?** If a task in session 0 cannot
  obtain one, the boxes must stay logged in with the task set to *run only when user is
  logged on* — a policy conversation with whoever owns the machines, and it means share
  permissions go to a domain group of modellers rather than to machine accounts.

  `cube/job.py::is_local_session` is a proxy, not a verified session check: it rules out
  SSH and VS Code Remote only, so it would treat an agent under Task Scheduler as local
  and call `runtpp` directly. If the license does not reach session 0, the fix is to teach
  that function to recognise the agent — the relay it already uses for remote sessions
  (`schtasks /it`, polling a sentinel for the exit code) is the mechanism.
- **Does exclusive create work on this share?** Two Python shells racing to create the same
  path; there must be exactly one winner. The design rests on the file server refusing the
  second create rather than letting both through.
- **The machine roster.** The list above is the four-year-old `RuntimeConfiguration`
  whitelist plus `tm2-b`. Which boxes still exist, and what is the real local runs disk on
  each?
- **Share permissions on three trees.** These are Windows ACLs — access control lists, the
  per-folder record of who may read, write, create or delete. Repo: Read & Execute for the
  group, Modify for the puller. Index: Modify for everyone, since creating a file is the
  claim and deleting it is `tm1 release`. Archive: Write for everyone.

## Commit order

1. `machines.yaml`, loader, validation, env renames, with the migration note.
2. Derive `intrastep_processes`; drop `acc_threads` from the registry.
3. `--scenario` takes several IDs and globs.
4. Shared index — work list, claim, heartbeat, receipt mirror. The riskiest commit; needs
   the exclusive-create test answered first.
5. `--on`, roster filter, status roster block.
6. Agent loop and the per-machine setup doc.

Orchestration must never become a prerequisite for proving parity.
