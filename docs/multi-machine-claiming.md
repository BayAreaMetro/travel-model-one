# Multi-machine claiming — scope

Status: **not built.** This file is the placeholder so the idea has a home and a
number; the code arrives in its own PR.

## The problem

A study is many cases. Eight cases at ~15 h each is five days on one box, and the
runs are already independent and individually named — `tm1 cases` lists them, each
gets its own directory, nothing is shared. What is missing is a way to hand them out
without two people starting the same one.

## The shape

One file, no change to `config.yaml` or `cases.yaml`:

```
model3c> tm1 claim ctramp_2023

  claimed BP-03-TRNF-2035  (3 of 8 unclaimed)
  starting run in E:/runs/ctramp_2023/BP-03-TRNF-2035-001
```

and from anywhere:

```
model3c> tm1 status ctramp_2023

  CASE                    MACHINE   STATUS               ELAPSED
  PARITY-2023             tm2-b     complete             15h22m
  BP-01-NONE-2035         tm2-b     complete             14h58m
  BP-02-TELE-2035         model3a   running  round 2/3    4h12m
  BP-03-TRNF-2035         model3c   running  round 0/3    0h03m
  BP-04-CORD-2035         —         free
  SENS-NOTL-ADOPT-2035    model3b   FAILED   hwy_assign    8h04m
```

## The one decision that matters

A claim is a file created **exclusively** on the shared drive, so the filesystem is
the mutex and two machines cannot take the same case. Only the claim crosses the
network — runs stay on local disk, since each is ~100 GB and Cube's cluster is far
too chatty for a network path. The run receipt already records which machine holds a
case, which is how `status` knows where to look and how a failed case gets picked
back up.

## Why it is not in the harness PR

Different failure domain (network, locking, stale claims from a machine that died)
and premature until there are cases worth batching. The seam it attaches to —
projects, cases, fingerprinted run directories, receipts — is already there.

## Open questions

- Reclaiming a case whose machine died: timeout on the claim file, or explicit
  `tm1 claim --release`?
- Does `tm1 status` read every machine's run directory over the network, or does each
  machine publish a small status file next to its claim?
- Priority: does `tm1 claim` take the next unclaimed case in declaration order, or is
  there an explicit queue?
