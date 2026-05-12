# PopulationSim Development Plan

## Goal
Replace the monolithic `run_populationsim.py` with:
1. PopulationSim annotation CSVs (config-driven, no custom code)
2. A thin runner in `src/tm1/populationsim.py` for the few true cross-table operations
3. Scenario-level config inheritance (same pattern as ActivitySim)

## Current State
`run_populationsim.py` does everything in one script:
- PUMS filtering, person/household derivations, cross-table aggregations,
  GQ handling, income deflation, control totals preprocessing, and PopSim invocation.

## Migration Plan

### Eliminate → PopSim annotation CSVs

| Step | Target Config |
|------|---------------|
| `pemploy` derivation | `annotate_persons_preprocessor.csv` |
| `pstudent` derivation | `annotate_persons_preprocessor.csv` |
| `ptype` derivation | `annotate_persons_preprocessor.csv` |
| `occupation` (SOC mapping) | `annotate_persons_preprocessor.csv` |
| Income deflation (`ADJINC * HINCP * deflator`) | `annotate_households_preprocessor.csv` |
| Vacant unit filter (NP > 0) | `seed_households.filter` in `settings.yaml` |
| Institutional GQ filter | `seed_households.filter` in `settings.yaml` |
| PUMA filter (Bay Area only) | `seed_households.filter` or geo_cross_walk inner join (already implicit) |
| Control totals derived columns | Pre-bake into controls CSV or add annotation |
| Post-synthesis HHT fillna | ActivitySim `annotate_households_preprocessor.csv` |
| Post-synthesis person_id | ActivitySim handles this natively |

### Keep in runner (cross-table operations)

These require person→household aggregation that PopSim annotations can't express:

1. **num_workers** — count of employed persons per household (person ESR → HH aggregate)
2. **PINCP→HINCP transfer** — for GQ records where HINCP is missing, use person income
3. **GQ weight transfer** — copy PWGTP to WGTP for non-institutional GQ households

### Runner structure (`src/tm1/populationsim.py`)

```
def run(scenario_config):
    1. Fetch/cache PUMS CSVs and control totals (URL or local)
    2. Run cross-table seed prep (the 3 operations above)
    3. Invoke PopulationSim with config chain:
       [scenario/population/, base-models/population/configs_mp/, base-models/population/configs/]
    4. Copy final outputs to {proj_dir}/data/
```

### Scenario config integration

```yaml
steps:
  populationsim:
    seed_population:
      pums_households: "M:/Data/Census/PUMS/..."
      pums_persons: "M:/Data/Census/PUMS/..."
      output_dir: "{proj_dir}/data/popsim_seed"
    synthesize:
      data_dir: "{proj_dir}/data/popsim_seed"
      output_dir: "{proj_dir}/data"
      configs:
        - "scenarios/base_2023/population"
        - "base-models/population/configs"
    controls:
      taz: "https://raw.githubusercontent.com/..."
      county: "https://raw.githubusercontent.com/..."
      region: "https://raw.githubusercontent.com/..."
```

### Config inheritance for scenarios

- `base-models/population/configs/` — canonical base (settings, annotations, controls format)
- `scenarios/<name>/population/` — overrides only (different control totals, year-specific thresholds)
- Same rule as ActivitySim: YAMLs merge, CSVs replace

## Sequencing

1. Write annotation CSVs for person/household derivations
2. Add filter expressions to `settings.yaml`
3. Verify PopSim produces identical output to current script
4. Create `src/tm1/populationsim.py` with just cross-table logic
5. Wire into `scenario_config.yaml`
6. Delete `run_populationsim.py`
