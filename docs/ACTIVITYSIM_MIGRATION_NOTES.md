# ActivitySim Migration Notes

Decisions, fixes, and gotchas encountered migrating TM1 from CTRAMP to ActivitySim 1.5.1.

## Input Table Column Mapping

### persons.csv (from PopulationSim `personFile.csv`)

There's a fair amount of renaming and recoding going on both within and between PopulationSim and ActivitySim, sometimes multiple remappings for the same column. I'm guessing this is due to a lot of legacy migration decisions over time.

We should plan to streamline this substantially by removing a lot of redundant fields and repetive renaming that gets consistently carried through from PopulationSim to ActivitySim. For now, the mapping is as follows:



| CSV Column | ActivitySim Column | Notes |
|---|---|---|
| `HHID` | `household_id` | Rename added — was missing in prototype configs |
| `PERID` | `person_id` | Index column |
| `AGE` | `age` | Case mismatch — CSV is uppercase |
| `SEX` | `sex` | Case mismatch — CSV is uppercase |
| `pemploy` | `pemploy` | No change needed |
| `pstudent` | `pstudent` | No change needed |
| `ptype` | `ptype` | No change needed |

**`PNUM` removed** from `keep_columns`. The PopulationSim output does not include
person-number-within-household. ActivitySim derives it internally. No UEC in
the prototype_mtc configs references `PNUM`.

### households.csv (from PopulationSim `hhFile.csv`)

| CSV Column | ActivitySim Column | Notes |
|---|---|---|
| `HHID` | `household_id` | Index column |
| `TAZ` | `home_zone_id` | Recoded to zero-based |
| `HINC` | `income` | |
| `PERSONS` | `hhsize` | |
| `hworkers` | `num_workers` | |
| `VEHICL` | `auto_ownership` | |
| `HHT` | `HHT` | No rename needed |

### land_use.csv (from `tazData.csv`)

| CSV Column | ActivitySim Column | Notes |
|---|---|---|
| `ZONE` | `zone_id` | Recoded to zero-based |
| `COUNTY` | `county_id` | |
| `AREATYPE` | `area_type` | |

## Skim Conversion (TPP → OMX)

Highway, transit, and non-motorized skims are converted from Cube Voyager TPP
format to a single `skims.omx` file by `scripts/setup_scenario.py`. The full
mapping is documented in `docs/skim_conversion_mapping.md`.

Key decisions:
- External zones (1455–1475) are included in the matrix but are not used by
  ActivitySim demand models — they are assignment-only in the TM1 zone system.
- Transit skims use the highest available `*.avg.iter{N}.tpp` file from the
  reference run.
- **`wacc` and `wegr`** (walk access/egress time) added to the transit skim
  mapping. The prototype configs omitted these but `accessibility.csv` and
  `annotate_persons_workplace.csv` reference `WLK_TRN_WLK_WACC` and `_WEGR`.
- **Aggregate `WLK_TRN_WLK_*` skims** come from Cube's "best-path" combined transit
  files (`trnskm{period}_wlk_trn_wlk.tpp`). Cube's transit
  path-builder already computes the best path across all sub-modes. We simply
  add `trn` to the mode list alongside `loc`, `lrf`, `exp`, `hvy`, `com`.
  Similarly `DRV_TRN_WLK` and `WLK_TRN_DRV` are read from the corresponding
  `drv_trn_wlk` / `wlk_trn_drv` TPP files.
- **`WLK_TRN_WLK_IVT` → `WLK_TRN_WLK_TOTIVT`**: The prototype configs used
  `_IVT` for the aggregate transit skim but `_TOTIVT` for all other 15 mode-specific
  keys. This was an inconsistency in the original port — both map to the same
  Cube column (`ivt`). Fixed in `accessibility.csv` and
  `annotate_persons_workplace.csv` to use `TOTIVT` everywhere, matching the
  mode-specific convention and eliminating a special case in the skim mapping.

## `write_trip_matrices` — Duplicate `tour_id` Index

The `write_trip_matrices` step crashed with:

```
InvalidIndexError: Reindexing only valid with uniquely valued Index objects
```

The failing expression in `write_trip_matrices_annotate_trips_preprocessor.csv`:

```
trips.tour_id.map(tours.number_of_participants)
```

**Cause:** Joint tours share a `tour_id` across participants, creating duplicate
values in the `tours` table index. Newer pandas (2.x) rejects `.map()` on a
Series with a non-unique index — the prototype_mtc configs were written for
pandas 1.x which silently used the first match.

**Fix:** Changed the expression to deduplicate before mapping:

```
trips.tour_id.map(tours.reset_index().drop_duplicates(subset='tour_id').set_index('tour_id').number_of_participants)
```

This is safe because all participants of a joint tour share the same
`number_of_participants` value. The upstream prototype_mtc example has the same
bug (as of April 2026).

## Slack Notifications

Migrated from legacy `model-files/scripts/notify_slack.py` to `src/tm1/slack.py`.
- Webhook URL resolved from `SLACK_WEBHOOK_URL` env var (via `.env`) or MTC
  default file at `M:\Software\Slack\TravelModel_SlackWebhook.txt`.
- Notifications: setup start, ActivitySim start, major pipeline milestones,
  finish/error.
- Disable with `--no-slack` flag or `notify_slack=False` in `run()`.

## Package Structure

| Package | Purpose |
|---|---|
| `src/cubeio` | Generic Cube Voyager I/O (TPP reader, OMX converter) |
| `src/tm1` | TM1-specific utilities (config loading, Slack notifications) |
| `scripts/setup_scenario.py` | Assemble ActivitySim data directory from reference run |
| `scripts/run_model.py` | Orchestrator — setup + launch ActivitySim |
