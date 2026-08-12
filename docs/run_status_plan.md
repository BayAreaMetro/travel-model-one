# `tm1 status` — one screen showing where a run is

A model run is 115 steps over ~16 hours across Cube, Java and Python subprocesses.
Today the only way to know where it is is to read the log, and a long step looks
identical to a hang. This is a read-only view of the plan, filling in as it runs.

Scoped after the phase 1→6 cascade, not part of it.

## The view

```
base_2023_ctramp · round 2 of 3 · 48/115 steps · elapsed 2h04 · ~10h51 left

  ✓ setup                        11/11                   2m
  ✓ warm start · iter 0          17/17, 9 skipped       53m

  loop                           round 1 round 2 round 3
  ▸ simulate_ctramp                 1h59 ▸  1h59       ·
    update_telecommute_en7            2s       ·       ·
    ...
    prep_assign                      10m       ·       ·
    hwy_assign                       31m       ·       ·
    transit_skims                     6m       ·       ·
    hwy_skims                         3m       ·       ·
    accessibility                    31s       ·       ·

  · summaries                    0/3

  ▸ simulate_ctramp running 1h59 · last write main/wsLocResults_2.csv
```

Columns are rounds, so a number's position says which round it belongs to and
there is nothing to disambiguate. `▸` running with live elapsed · `·` pending ·
`⤼` skipped on its `skip_if_exists` sentinel. Sections collapse to one line once
finished; the loop body appears once with a column per round, which is what makes
115 executions fit on a screen.

On a finished run the same table is a profile — `simulate_ctramp` is 11 of the 15
hours, `prep_assign` grows 10→14→18m with sample rate, everything else is flat.
On a dead run it shows where to point `--resume-at`.

## Shape

Two new files, two edits, no new dependencies.

| file | | ~lines |
|---|---|---|
| `src/tm1/status.py` | new | 200 |
| `tests/test_status.py` | new | 120 |
| `src/tm1/runner.py` | edit | 15 |
| `src/tm1/cli.py` | edit | 30 |

`{proj_dir}/logs/status.json` is written by the runner at each step boundary —
the plan, each entry's state and duration, what is running and since when. The
hook points exist: `run_model` already builds `plan` and `configs`, and
`_report_step` already fires on every completion.

**The runner labels each plan entry with its section** (`setup` / `warm start` /
`loop` / `summaries`) when it writes the file. It has `configs` and knows which
entries pinned `iteration: 0`, so it classifies once and the renderer just groups
by label. Nothing re-parses the config.

`tm1 status --scenario <name|path>` mirrors `tm1 run`'s flag. Read-only: it opens
one JSON file and stats `proj_dir`, so it cannot disturb a run and works from any
number of terminals over SSH, during or after.

## Why the runner writes it rather than something parsing the log

Prototyped by replaying the real logs of the 2026-08-11 run. Reconstructing
`(step, round)` from console text is ambiguous once a run spans resumes — this one
spanned five — and three attempts each moved the wrong cells rather than fixing
them. Two smaller traps found the same way:

- the skip line prints *before* the iteration banner, so a warm-start skip reads
  as a round-1 skip
- the liveness probe must exclude `logs/`, or the harness's own logging makes
  every run look alive

The runner has all of this exactly. Nothing else does.

## ETA

A pending step costs what it last cost; `simulate_ctramp` scales by the
sample-rate ratio. Rendered at 17:00 on the real run this gave `~10h51 left`
against an actual finish 18 minutes later — good enough, and it needs no
knowledge of what any step does.

## Deliberately out

- **No intra-step progress.** Knowing what Cube or CT-RAMP is doing internally
  means per-engine probes, and those are thrown away when ActivitySim and a new
  assignment engine land. The newest-write-mtime line covers "is it alive."
- **No watch mode or daemon.** `watch -n 60 tm1 status` is the shell's job.
- **Nothing about Slack.** Notification noise is a separate question with a
  separate five-line answer.
