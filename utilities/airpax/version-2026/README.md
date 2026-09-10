# Airport Passenger Demand Workflow

This workflow creates airport ground-access demand matrices for OAK, SFO, and SJC. User-maintained assumptions and source datasets are stored separately from source-derived parameter tables so the model inputs can be reviewed and regenerated when needed.

## Directory layout

```text
.
├── build_parameters.py
├── make_air_passenger_demand.py
├── input/
│   ├── TPS_TAZ_airport_TOD.xlsx
│   └── gosling_summaries/
│       ├── 2007_fromOAK.dbf
│       ├── ...
│       └── 2035b_toSJC.dbf
├── parameters/
│   ├── README.md
│   └── *.csv
└── output/
    └── *.dbf
```

The model TAZ correspondence remains in the model geography directory. By default, both scripts read:

```text
../../geographies/taz-superdistrict-county.csv
```

relative to the script directory. 

## Workflow

`build_parameters.py` creates the source-derived parameter CSVs from the Gosling airport summaries, `TPS_TAZ_airport_TOD.xlsx`, the model geography, and the user-maintained assumptions in `parameters/`.

`make_air_passenger_demand.py` reads the parameter CSVs, assembles the required TOD/access-mode/submode combinations in memory, and writes the airport demand DBFs to `output/`.

## Run

For a normal model run using the existing parameter CSVs:

```bash
python make_air_passenger_demand.py
```

For a full source-to-output run that first rebuilds the source-derived parameter CSVs:

```bash
python make_air_passenger_demand.py --rebuild-parameters
```

The parameter files may also be rebuilt independently:

```bash
python build_parameters.py
```

See `parameters/README.md` for the parameter manifest, editability guidance, and source descriptions.
