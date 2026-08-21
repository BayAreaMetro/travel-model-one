# TM-1.7 Freight Model Update

## Overview

This folder contains the workflows, documentation, and model estimation pipelines developed to support the TM-1.7 Freight Model Updates.

The primary objective of this effort is to evaluate whether freight truck trip patterns from the California Statewide Freight Forecasting and Travel Demand Model, version 2 (CSF2TDM) can be replicated within the TM-1.6 4-step modeling framework and whether model validation performance can be improved. 

Because comprehensive observed freight demand datasets are limited, the project uses CSF2TDM 2020 results as the primary reference dataset for model estimation. 

Validation is performed using observed truck traffic counts from Caltrans (2018) and the Bay Area Toll Authority (BATA, 2023), comparing modeled truck volumes against observed conditions across available count locations.

### Project Structure

- `config/`  : YAML model specifications and pipeline settings.
- `data/`    : Local data storage. **Note:** This folder is git-ignored; all project data is hosted in [Box](https://mtcdrive.box.com/s/udd1rxpqffzfckf9iyi5kfcagma80nyf)
- `notebooks/` : Jupyter notebooks for exploration and simple analysis. 
- `src/`     : Core source code for data pipelines, modeling tasks and evaluation. 
- `reports/`     : Simple Reports

---

## Reference Demand Data

The principal source of freight demand data is the 2020 CSF2TDM. While statewide model outputs are not ideal as an observed data source, they represent the most comprehensive freight demand information currently available for this project. As a result, CSF2TDM outputs are treated as the reference dataset used to estimate freight model components within the TM framework. 

The following datasets from the CSF2TDM were utilized as primary inputs to the freight model development process:


| Dataset | Description | Box Location | File Within Archive |
|----------|-------------|--------------|--------------------|
| CSF2TDM Freight OD Demand | Statewide freight OD matrix (7,000 × 7,000) containing truck trips by vehicle class across TAZs, gateways, special generators, and Transportation Logistics Nodes (TLNs). | [Year2020.zip](https://mtcdrive.box.com/s/5bttqe153n2xf3z1mnmklqjlvshfvv6e) | `Year2020/FFM/Trips/TRIPS_FFM_2020.mat`
| CSF2TDM TAZ | Shapefile containing the 5528 Traffic Analysis Zones (TAZs) in CSF2TDM. | [CSF2TDM_TAZs.zip](https://mtcdrive.box.com/s/dik32cuwbjvkpu7e8zuu70ki6m4uzg1f)  |  | 
| CSF2TDM Traffic Network | Highway network used to identify the location of gateways, special generators, TLNs, and other network nodes not represented by standard TAZs. | [Year2020.zip](https://mtcdrive.box.com/s/5bttqe153n2xf3z1mnmklqjlvshfvv6e) |`Year2020/HwyNetwork_Loaded_ADT_2020_Daily.NET`|
|CSF2TDM TAZ Equivalences| Lookup table linking CSF2TDM TAZ IDs to OD matrix indices and providing associated geographic attributes, including county, district, and MPO. |  [Year2020.zip](https://mtcdrive.box.com/s/5bttqe153n2xf3z1mnmklqjlvshfvv6e)| `Year2020/taz_MPO_region.csv`|

**Note:** The datasets summarized above represent the primary CSF2TDM inputs used in this project. Additional information on the statewide model's structure, assumptions, and methodologies can be found in [DR1_CSF2TDM_ModelDocumentation_12-10-2025.pdf](https://mtcdrive.box.com/s/wr9p4tgxtlridkz589txguno6q84wrw3).

---

## Validation Data

Model validation relies on observed truck traffic counts from the following available sources.

| Dataset | Year | Description | Count Locations in MTC Region | Box Location |
|----------|------|-------------|----------------|--------------|
| Caltrans Truck Counts | 2018 | Hourly truck counts by FHWA vehicle classification throughout 2018 | 28 | [counts](https://mtcdrive.box.com/s/5f6jwgthq39fajdble2f5b1vjm4ydoog) | 
|  Bay Area Toll Authority (BATA) | 2023 | • Hourly truck volumes by axle classification at seven Bay Area toll bridges, based on Tuesday-Thursday observations collected during March-May and September-November (excluding holidays)<br>• Each toll plaza observation was manually matched to the corresponding MTC highway network link at the toll collection location for validation purposes.| 7 | [BATA_counts_by_plaza_hour_axles.xlsx](https://mtcdrive.box.com/s/5mjgq6iwjlzxidap533rr9zd6xb6ukbi) [BATA_TM_network_link_matching.csv](https://mtcdrive.box.com/s/re5hrvsc5601hh905u46hanr70rxh4ca)|

Other datasources evaluated: 
- PEMS: #TODO: Why not used
- 2023 Caltrans census data.  #TODO: Why not used

---

## Data Pipelines

Several data preparation and analysis pipelines were developed to support model estimation, calibration, and validation. These pipelines transform source datasets into analysis-ready inputs and provide quality control checks used throughout the project.

| Pipeline | Description                                                                                                | Key Outputs                                                                                                                                                                                                    | Results                                                                                                    | Details |
|-----------|------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|---------|
| CSF2TDM to TM Zone Translation & Truck OD Projection| Projects statewide freight demand from the CSF2TDM zone system to the MTC travel model zone system.        | A CSF2TDM-to-TAZ1454 crosswalk, truck OD trips projected to the TM-1.x zoning system (in both CSF2TDM and TM-1.x formats), and production/attraction vectors for internal zones, gateways, and special generators. | [data/interim/matrix_pojection](https://mtcdrive.box.com/s/dk1xgewcz1l4eivm9l9q4qfs754tm79r)               |[src/data/od_projection/readme.md](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/src/data/od_projection/readme.md) |
| Observed Truck Counts Data Processing | Processes Caltrans and BATA truck count datasets for model validation and time-of-day estimation.          | Observed counts by time-of-day and truck type                                                                                                                                                                  | [Box: data/intermim/observed_data](https://mtcdrive.box.com/s/m4ujta7m2h6ftztlkt6zm69em57flec8)            |[src/data/observed](https://github.com/BayAreaMetro/travel-model-one/tree/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/src/data/observed) |
| CSF2TDM vs TM Comparison | Exploratory analysis comparing translated CSF2TDM demand to TM freight demand patterns.                    | Trip rates per job, household, and persons. Trip distributions by truck class, and international gateways by time and distance                                                                                 | Github Issue[#96](https://github.com/BayAreaMetro/travel-model-one/issues/96)                              |[src/data/EDA](https://github.com/BayAreaMetro/travel-model-one/tree/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/src/data/EDA) |
| Trip Distribution Inputs | Prepares input files to calibrate distance-/time-based friction factors for the trip distrobution models.  | CSF2TDM  Trips Lengh Frequency Distribution (TLFD) by truck type| [Box: data/intermim/trip_distribution_inputs](https://mtcdrive.box.com/s/2553udqtgpb7sky0kc5joa1bs6rgw897) | [src.data.trip_distribution.build_inputs](https://github.com/BayAreaMetro/travel-model-one/tree/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/src/data/trip_distribution)

---

## TM-1.7 – Truck Model Updates

The updates summarized in this section represent the final set of truck model enhancements incorporated into TM-1.7. Model development involved a series of experiments designed to evaluate the performance and sensitivity of individual modifications, including changes to trip generation, trip distribution, time-of-day factors, IX/XI/XX demand adjustments, and special generator treatments.

The results of these experiments were used to inform the final model specification documented below. Detailed descriptions of the experimental runs, model comparisons, and evaluation results are available in [Experiments](reports/experiments.md).


| Model Component | Summary of Changes | Modified Scripts / Inputs | Supporting Evidence|
|-----------------|--------------------|---------------------------|--------------------|
| Trip Generation | Re-estimation of truck trip generation models using CSF2TDM freight demand as the calibration target for small, medium, and large truck classes. The existing TM1.6 very small truck generation model was retained. As documented in GitHub Issue [#95](https://github.com/BayAreaMetro/travel-model-one/issues/95), the truck market segmentation was updated from the TM1.6 garage/non-garage to freight/non-freight|[TruckTripGeneration.job](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/model-files/scripts/nonres/TruckTripGeneration.job)|[src/models/generation](https://github.com/BayAreaMetro/travel-model-one/tree/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/src/models/trip_generation) <br>[model_coefficients.csv](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/models/truck_trip_generation/20260716_162029/tableau/model_coefficients.csv)<br>[model_comparison.csv](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/models/truck_trip_generation/20260716_162029/tableau/model_comparison.csv) |
| Trip Distribution | Re-estimation of freight trip distribution models using distance-based friction factors. As documented in GitHub Issue [#99](https://github.com/BayAreaMetro/travel-model-one/issues/99), the project transitioned from the existing TM1.6 time-based distribution approach to a distance-based approach. Calibration targets were derived from CSF2TDM OD demand matrices for small, medium, and large truck classes, while TM1.6 OD patterns were used for very small trucks due to the absence of an equivalent vehicle class in CSF2TDM. | [TruckTripDistribuion.job](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/model-files/scripts/nonres/TruckTripDistribution.job) <br>[truckFF_distance_based.dat](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/models/trip_distribution/truckFF_distance_based.dat)| [src/models/trip_distribution](https://github.com/BayAreaMetro/travel-model-one/tree/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/src/models/trip_distribution) <br>[Estimated Gamma Coefficients](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/models/trip_distribution/plots/friction_curves.png)<br> [Friction Factors](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/notebooks/friction_factors.ipynb) | 
| Time of Day | Estimation of truck time-of-day factors using observed counts from Caltrans (2018) and BATA (2023) | [TruckTimeOfDay.job](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/model-files/scripts/nonres/TruckTimeOfDay.job)| [TOD Report](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/models/tod/truck_tod_report.pdf) <br> [notebooks/tod.ipynb](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/notebooks/tod.ipynb) |
| IX/XI/XX Truck Demand Adjustment | Adjustment of truck shares for internal-external (IX), external-internal (XI), and external-external (XX) travel markets to ensure consistency with truck demand patterns observed in the CSF2TDM.| [IxTimeOfDay.job](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/model-files/scripts/nonres/IxTimeOfDay.job)| [IX-XI-II Trips.ipynb](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/notebooks/IX-XI-II%20Trips.ipynb)
| Special Generators | Truck production trips for medium and large trucks for 6 special generators identified as International gateways in CSF2TDM. These are PORT OF OAKLAND, PORT OF SAN FRANCISCO, PORT OF RICHMOND, PORT OF REEDWWOD CITY, SFO, OAK. | [SpecialGeneratorTruckTripDistribution.job](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/model-files/scripts/nonres/SpecialGeneratorTruckTripDistribution.job) <br> [SpecialGeneratorTruckTripGeneration.job](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/model-files/scripts/nonres/SpecialGeneratorTruckTripGeneration.job) <br>[RunIteration.bat](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/model-files/RunIteration.bat)| [Special Generators.ipynb](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/notebooks/Special%20Generators.ipynb)|

---

## Validation

Validation focused on comparing modeled truck volumes against observed truck counts and evaluating the performance of the proposed TM1.7 freight model relative to the existing TM1.6 implementation.

### Traffic Count Validation

Comparison of modeled versus observed truck counts using available Caltrans and BATA count data.

| Truck Class | TM1.6 | TM1.7 |
|------------|:-----:|:-----:|
| Heavy Trucks | ![](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/models/evaluation/best_TM17_20260728/plots/scatter_TM-1.6_HV.png?raw=true)| ![](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/models/evaluation/best_TM17_20260728/plots/scatter_TM-1.7_GEN_IX_HV.png?raw=true)|



### Trip Distribution Validation

Comparison of modeled and reference trip length frequency distributions (TLFDs) by truck class.

| Truck Class | TM1.6 | TM1.7 |
|------------|:-----:|:-----:|
| Very Small | ![](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/models/evaluation/best_TM17_20260728/plots/trip_distribution_TM-1.6_Very%20Small.png?raw=true) | ![](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/models/evaluation/best_TM17_20260728/plots/trip_distribution_TM-1.7_GEN_IX_Very%20Small.png?raw=true)|
| Small | ![](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/models/evaluation/best_TM17_20260728/plots/trip_distribution_TM-1.6_Small.png?raw=true) | ![](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/models/evaluation/best_TM17_20260728/plots/trip_distribution_TM-1.7_GEN_IX_Small.png?raw=true)|
| Medium | ![](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/models/evaluation/best_TM17_20260728/plots/trip_distribution_TM-1.6_Medium.png?raw=true) | ![](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/models/evaluation/best_TM17_20260728/plots/trip_distribution_TM-1.7_GEN_IX_Medium.png?raw=true)|
| Large | ![](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/models/evaluation/best_TM17_20260728/plots/trip_distribution_TM-1.6_Large.png?raw=true) | ![](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/models/evaluation/best_TM17_20260728/plots/trip_distribution_TM-1.7_GEN_IX_Large.png?raw=true)|
---


## Quick Start

The analyses and results documented in this repository can be reproduced by cloning the repository, setting up the project environment, downloading the required datasets, and running the individual pipelines documented below.

### 1. Clone the Repository

```bash
git clone https://github.com/BayAreaMetro/travel-model-one.git
cd travel-model-one/utilities/trucks/trucks_2026_update
```

### 2. Create the Environment

This project uses **UV** for dependency management. Installation instructions are available in the UV documentation:

https://docs.astral.sh/uv/

From the project root directory:

```bash
uv venv
source .venv/bin/activate
uv sync
```

### 3. Download Project Data

All project datasets are stored in Box and are not tracked by GitHub:

https://mtcdrive.box.com/s/udd1rxpqffzfckf9iyi5kfcagma80nyf

Download the required datasets and place them in the local `data/` directory following the instructions provided in the corresponding pipeline documentation.