# Multi-machine claiming

Status: **not built.** This is the agreed scope; the code arrives in the commits listed
at the end.

## The problem

A study is many cases. Eight cases at ~15 h each is five days on one box, and the runs
are already independent and individually named — `tm1 cases` lists them, each gets its
own directory, nothing is shared. What is missing is a way to hand them out without two
people starting the same one, and without logging into every machine to do it.

## What the team requires

- One repo clone, on the shared network drive.
- Results land on the shared network drive.
- Hot data is copied to each machine and stays there.

All three hold. The one thing that does *not* move to the share is the virtual
environment: a loaded `.pyd` is locked for the life of a process, so a shared venv cannot
be updated while any machine is mid-run, and a half-applied `uv sync` breaks every
machine at once. Each box builds its own from the shared `uv.lock`, and the agent runs
`uv sync --frozen` between runs — so a machine cannot start a case on a stale
environment.

The shared checkout is a **deployment, not a working tree**: Read & Execute for the
modelling group, Modify only for whoever runs the pull. Otherwise a stray `git checkout`
lands in the middle of a fifteen-hour run.

## Where things live

| Root | Where | Size | Purpose |
|---|---|---|---|
| `TM1_SHARED_DRIVE_ROOT` | share (UNC) | — | inputs, archived results, index. Renames `TM1_M_DRIVE`. |
| `TM1_LOCAL_RUNS_ROOT` | local disk | ~100 GB/run | where the run happens. Renames `TM1_RUNS_ROOT`. |
| `{shared_drive}/tm1/index` | share, derived | KB | work list, claims, heartbeats, mirrored receipts |
| archive `to:` | share, per project | ~2 GB/run | the kept result, declared in `config.yaml` |

The run directory cannot go on the share, and that is arithmetic rather than preference.
`MAX_RUN_DIR_LEN` is 70 in `run/directory.py`, because Cube and the Java stack are not
long-path aware and a run nests roughly 160 characters below its own root:

    //models.ad.mtc.ca.gov/data/models/   35
    runs/                                 5
    PBA50+_FBP/                          11
    BP-03-TRNF-2035-001                  19
                                       = 70   before a single file nests

    E:/runs/PBA50+_FBP/BP-03-TRNF-2035-001  = 38, comfortable

The archive destination is a line in each project's `config.yaml`, not a machine setting:
different studies publish to different folders, and it is symmetric with `copy_inputs`,
whose source paths are deliberately literal and visible. Its acceptance test is already
written into the model — `config.yaml` warmstarts from a previous run's `OUTPUT/main` —
so **an archived run must be usable as the next study's warmstart.**

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

UNC only. Mapped drive letters are per-login-session, so a hostname key cannot predict
them.

### The invariant

`run/fingerprint.py` already names the keys a machine may tune without making its output
incomparable with another machine's — `cluster_nodes`, `threads`, `intrastep_processes`,
`acc_threads`, `timeout`, `commpath`. That set is exactly the registry's write scope:
**a `compute:` address outside the fingerprint's skip-list is a validation error.** Not a
convention, a check. It makes it structurally impossible for the registry to change a
result.

Two of those keys turn out not to belong in it at all:

- `acc_threads` writes `num.acc.threads` for the Java calculator behind the deferred
  `RunLogsums.bat`. Nothing in this pipeline consumes it, so tuning it per machine tunes
  nothing.
- `intrastep_processes` is not a count — it selects a file, and exactly two exist
  (`HwyIntraStep_48.block`, `_64.block`). It is slaved to `hwy_assign.cluster_nodes`, and
  exceeding it makes HwyAssign address processes that were never started. So it is
  **derived**: the largest available block ≤ `cluster_nodes`.

### Resolution order

Process environment → `.env` if present → `machines.yaml[host]` → `machines.yaml[defaults]`.
The registry only sets what is unset, so a box can be overridden in an emergency without
a commit.

**An unknown hostname must run, not refuse** — fall through to `defaults:` with a warning
naming the host and the file. `RuntimeConfiguration.py` was retired precisely because an
unknown host was a hard stop and `tm2-b` was not on its list. This must not rebuild that
whitelist in better YAML.

## How a machine gets work

No SSH, no WinRM, no credentials, no daemon. Nothing connects to another machine. Polling
replaces pushing, and the transport is the SMB share that already holds the inputs.

    — on any machine —
    $ tm1 run PBA50+_FBP --case BP-01 BP-02 BP-03 --on model3-a model3-b

      writes three files, exits 0, contacts nothing

    — index/PBA50+_FBP/BP-01-NONE-2035.work —
    {"case": "BP-01-NONE-2035", "fingerprint": "a3f9c2…",
     "on": ["model3-a", "model3-b"], "queued": "...", "by": "..."}

    — on model3-a, 30-second timer —
    os.listdir(index)                       # .work with no .claim, "on" contains me
    os.open(BP-01.claim, O_CREAT | O_EXCL)  # model3-b races and loses; takes BP-02
    run_model(config_dir, case=...)         # locally, into E:/runs

      then: mirror .tm1/case.json to the index on each state change,
            touch index/model3-a.beat every five minutes

That single `O_EXCL` create is the entire coordination primitive — the SMB server
serialises it, one caller wins, the rest get `FileExistsError`. The same trick is already
load-bearing in `run/directory.py`, where `mkdir(exist_ok=False)` allocates run numbers.

Liveness is a zero-byte file judged by mtime. Domain machines are within five minutes of
each other by Kerberos requirement, so a twenty-minute staleness threshold needs no clock
protocol.

**The honest limitation:** if the agent is not running on a box, its work sits queued and
nothing errors. That is the cost of having no push channel, and it is why the roster and
the heartbeat exist — `tm1 status` shows the queued case next to
`model3-d — no heartbeat since 09:14`.

## Command surface

One new flag, one new verb-free form.

    tm1 run <project> --case PARITY-2023                      this machine, foreground
    tm1 run <project> --case 'BP-*' --on model3-a model3-b    n cases, named machines
    tm1 run <project> --on all                                everything, everyone
    tm1 run                                                   the agent: take what I am given
    tm1 status [<project>]                                    + machine roster block
    tm1 release <project>:<case>                              hand a held case back

**`--on` defaults to this machine.** It is always the targeting flag; omitting it means
`--on <this host>`, which is what `tm1 run <project>` already does today. Naming other
machines is the explicit case, and so is `--on all`.

Every run takes a claim, including a local one. Running here must not bypass the mutex —
otherwise a person and this box's own agent can start the same case twice. When the
target is this machine and only this machine, the run proceeds in the foreground instead
of being left for the agent to pick up.

`--on` is a **filter, not an assignment**: whichever named machine frees up next takes
the next case. Real pinning idles a free box while a case waits for its assigned machine,
and re-invents the shard counts that claiming exists to avoid.

A failed case stays `HELD` on the machine that failed it. No auto-reclaim — a box someone
is debugging on does not get work pushed back at it.

### Per machine, once

    uv venv C:\tm1venv
    $env:UV_PROJECT_ENVIRONMENT = "C:\tm1venv"; uv sync
    setx TM1_LOCAL_RUNS_ROOT "F:\runs"          # only if it differs from defaults
    schtasks /create /tn "tm1 agent" /sc onlogon /rl highest ^
             /tr "C:\tm1venv\Scripts\tm1.exe run"

Set the task to restart on failure. That is the supervisor, and it is why the agent can
run cases in-process rather than needing subprocess isolation. No clone, no `.env`, no
per-machine config file.

## Deliberately not built

- SSH, WinRM, PsExec — any remote execution.
- A Windows Service, or any daemon that is not `tm1` itself.
- Message queue, RPC, wire protocol.
- Capability-based scheduling. Cases are not routed by machine size.
- Auto-reclaim of failed cases.
- Versioned shared venvs. Revisit only if two dependency sets must be live at once.

## Before writing code

Two of these can sink the design and cost minutes to answer.

- **Can Cube get a Bentley license from a scheduled task?** If a task in session 0 cannot
  obtain one, the boxes must stay logged in with the task set to *run only when user is
  logged on* — a policy conversation with whoever owns the machines, and it means share
  ACLs go on a domain group of modellers rather than machine accounts.
- **Is `O_EXCL` create atomic on this share?** Two Python shells, same path, count the
  winners. The whole design rests on the SMB server serialising `FILE_CREATE`.
- **The machine roster.** The list above is the four-year-old `RuntimeConfiguration`
  whitelist plus `tm2-b`. Which boxes still exist, and what is the real local runs disk on
  each?
- **Share ACLs on three trees.** Repo: Read & Execute for the group, Modify for the
  puller. Index: Modify for everyone — create is the claim, delete is `tm1 release`.
  Archive: Write for everyone.

## Commit order

1. `machines.yaml`, loader, validation, env renames. Breaks every `.env` at once, so it
   lands in one commit with the migration note.
2. Derive `intrastep_processes`; drop `acc_threads` from the registry.
3. `archive:` step. Useful on its own, on one machine, today.
4. Shared index — work list, claim, heartbeat, receipt mirror. The riskiest commit; needs
   the `O_EXCL` test answered first.
5. `--on`, roster filter, status roster block.
6. Agent loop and the per-machine setup doc.

Orchestration must never become a prerequisite for proving parity.
