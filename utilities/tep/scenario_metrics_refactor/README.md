# Scenario Metrics Refactor

## User-editable inputs

- `config/scenario_metrics.json`: paths, iteration, metric definitions, thresholds, filters, grouping, and output filenames.
- `config/taz_filters_example.csv`: example zone crosswalk. Replace its rows with the full TAZ list and add any number of binary 0/1 columns.

## Run

```bash
python createScenarioMetrics.py --config config/scenario_metrics.json
```

## Add a geography

Add a new 0/1 column to the TAZ crosswalk. Metrics using `ALL_BINARY_FILTERS` will automatically process it.

## Add an accessibility metric

Copy an item under `accessibility_metrics`, give it a unique name and output file, then change its skim, threshold, measure, and filters as needed.

## Notes

- Review path resolution relative to the config directory before integrating into the production model folder.
- The refactor preserves the original metric intent while separating configuration, loading, filtering, calculations, and outputs.
- Run against a small scenario first and compare totals with the current scripts.
