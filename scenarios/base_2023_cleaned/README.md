# base_2023_cleaned

Upgraded PopulationSim scenario using **PUMS 2019-2023 (5-year ACS)** with
2020-vintage PUMAs.  This produces a *new* synthetic population and does NOT
match the legacy reference run.

## Architecture: annotation-driven derivations

The key difference from `base_2023` is that **person model fields are derived
at ActivitySim runtime** instead of being pre-computed by PopulationSim:

```
┌───────────────────┐         ┌──────────────────────────┐
│   PopulationSim   │         │       ActivitySim         │
│                   │         │                           │
│ Raw PUMS fields:  │         │ annotate_persons_pums.csv │
│  ESR, WKW, WKHP,  │──csv──▶│  derives pemploy,         │
│  SCHG, AGEP       │         │  pstudent, ptype          │
│                   │         │                           │
│ Cross-table only: │         │ annotate_persons.csv      │
│  num_workers,     │         │  (standard downstream)    │
│  income, GQ type  │         │                           │
└───────────────────┘         └──────────────────────────┘
```

Benefits:
- **Single source of truth**: person type logic lives in one CSV, not Python code
- **Scenario-overridable**: swap the CSV to change person type definitions
- **PUMS-version agnostic**: change WKW → WKWN in the CSV without touching code
- **Auditable**: the annotation CSV is a readable specification

## Files

```
activitysim/
  settings.yaml                 # imports raw PUMS columns on persons table
  initialize_households.yaml    # adds annotate_persons_pums step before standard
  annotate_persons_pums.csv     # derives pemploy/pstudent/ptype from ESR/WKW/SCHG/AGEP
populationsim/
  pums_encoding.yaml            # income deflator + GQ config (no person-field logic)
```

## Relationship to `base_2023`

| | `base_2023` | `base_2023_cleaned` |
|---|---|---|
| PUMS vintage | 2017-21 (5-year) | 2019-2023 (5-year) |
| PUMA definitions | 2010 (41 PUMAs) | 2020 (62 PUMAs) |
| Income reference year | 2021$ → 2000$ | 2023$ → 2000$ |
| WKW field | Native categorical | Derived from WKWN (in crosswalked file) |
| Person field derivation | Python code (populationsim.py) | ActivitySim annotation CSV |
| Matches reference run? | Yes | No — new population |

## Status

**Not runnable yet.** The following items must be completed:

- [ ] Verify crosswalked PUMS files include `WKW` column (or adapt annotation for `WKWN`)
- [ ] Create 2020-vintage `geo_cross_walk.csv` (62 PUMAs → 1454 TAZs)
- [ ] Write simplified seed population creation that skips person-field derivation
- [ ] Validate PopulationSim output against 2023 Census totals
- [ ] Run ActivitySim end-to-end and compare to `base_2023` results

## When to promote

Once validation shows the cleaned population produces reasonable ActivitySim
results (within ~5% of reference for key metrics), this scenario can replace
`base_2023` as the primary calibration target.
