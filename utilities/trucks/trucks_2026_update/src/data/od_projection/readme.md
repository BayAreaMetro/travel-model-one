# CSF2TDM TO TM-1.6 OD Projection Pipeline 

This pipeline projects origin-destination (OD) matrices from the CSF2TDM zoning system into the TM-1.6 zoning system. 

The CSF2TDM matrices contain 7,000 zones. Of these, 5,128 are TAZs represented as polygons, while the remaining records are node-based zones used to represent gateways and special generator nodes. For this workflow, polygon-based zones are referred to as **zones**, and node-based zones are referred to as **gates**.

The Travel Model One (TM-1.x) contains origin-destination (OD) matrices with dimensions of 1,475 × 1,475. Of these, 1,454 represent TAZs, while the remaining 21 represent gateways for the nine-county Bay Area region.

Once projected, the pipeline produces three primary outputs:

- CSF2TDM OD Matrix (TM-1.x zoning system): An OMX file containing origin-destination (OD) matrices projected to the TM-1.x zoning system (1,475 × 1,475), while preserving the format, structure, and naming conventions of the CSF2TDM reference data.

- CSF2TDM OD Matrix (TM-1.6 format): OD matrices projected to the TM-1.x zoning system and reformatted to match the TM-1.6 post-trip-distribution structure. This output consists of five OMX files corresponding to the model time periods: Early AM (EA, 3:00 AM-6:00 AM), AM Peak (AM, 6:00 AM-9:00 AM), Midday (MD, 9:00 AM-3:00 PM), PM Peak (PM, 3:00 PM-7:00 PM), and Evening (EV, 7:00 PM-3:00 AM).

- Marginal Vectors: Production and attraction vectors derived from the projected matrices, reported separately for Traffic Analysis Zones (TAZs), gateways, and special generators.

General pipeline workflow: 

```txt
CSF2TDM Zones + Nodes
          |
          v
   Crosswalk Creation
          |
          v
    Matrix Projection
          |
          +-----------------------------------+
          |                                   |
          v                                   v
 CSF2TDM OD Matrices(CSF2TDM Format)   P/A Marginals
          |
          v
 CSF2TDM OD Matrices (TM-1.X Format)
```

## Usage

Run the pipeline from the project root using Python’s module execution syntax.

```bash
python -m src.data.od_projection.pipeline
python -m src.data.od_projection.pipeline --config <path_to_config> 
```

If no configuration file is specified, the pipeline uses the default configuration located at: `utilities/trucks/trucks_2026_update/configs/od_projection_configs.yaml`

Use this file as a reference when creating custom configurations or modifying pipeline settings.

## Required Inputs

The pipeline reads the following input files from the `input` section of the YAML configuration.

| Input | Description | Used for |
|---|---|---|
| `from_shapefile` | Source CSF2TDM zone shapefile. This file contains the source TAZ polygons used by the statewide matrix system. | Defines the source polygon-based zones used to build the spatial crosswalk. |
| `from_network_nodes` | Source network node shapefile from the statewide network. This includes node-based records used to represent gateways and special generator locations. | Used to identify and prepare source gates, including regional gateways and special generator nodes. |
| `from_omx` | Source OMX file containing the OD matrices to be projected. | Provides the original source-zone OD matrices that are transformed into the TM-1.6 zoning system. |
| `to_shapefile` | Target TM-1.6 TAZ shapefile. This file contains the target MTC travel analysis zones. | Defines the target polygon-based zones for the projected matrices. |
| `to_network_nodes` | Target MTC network node shapefile. This includes target network nodes used to represent gates in the TM-1.6 system. | Used to define target gates and connect source external flows to the target system. |
| `tm_land_use` | TM-1.6 land use CSV file. This file contains TAZ-level land use attributes. | Used to derive or support truck trip generation weights in the crosswalk for production and attraction-based allocation. |

  **Note**: Before running this pipeline, convert the CSF2TDM cube files to a Python-readable format. Use the script provided below to perform the conversion. The script must be executed on a machine with access to a Cube license: [tpp_to_omx.s](https://github.com/BayAreaMetro/travel-model-one/blob/tm1.7_truck_updates/utilities/trucks/trucks_2026_update/src/data/od_projection/tpp_to_omx.s)

  ## Pipeline workflow

### 1. Crosswalk generation 

The crosswalk translates data between the source (CSF2TDM) and target (TM-1.x) zoning systems by identifying spatial relationships among zones and gateways. Because the CSF2TDM and TM-1.x zoning systems do not share a one-to-one correspondence, the crosswalk is represented as a many-to-many relationship. A single CSF2TDM zone may overlap multiple TM-1.x zones, and a single TM-1.x zone may receive contributions from multiple CSF2TDM zones. Allocation weights are therefore used to distribute trips and other zonal attributes between the two systems.

Three types of mappings are included:

- **Internal Zones**: CSF2TDM zones located within the nine-county Bay Area are matched to TM-1.x zones using a polygon overlay. Small geometric artifacts ("slivers") caused by minor boundary misalignments between the two zoning systems are removed prior to weight calculation. Overlaps smaller than 50 m², overlaps representing less than 10% of both parent zones, and highly elongated or irregular polygons (compactness < 0.02) are excluded. This tresholds can be modified in the YAML configuration. By default, crosswalk weights are proportional to the area of overlap between the CSF2TDM and TM-1.x TAZs. In addition, the workflow generates production- and attraction-based weighting factors derived from the original TM-1.6 truck generation equations.([link](https://github.com/BayAreaMetro/travel-model-one/blob/b5365528a6961512d2fff0b8a5303f6a951a08d0/utilities/trucks/trucks_2026_update/src/data/od_projection/prepare_projection_inputs.py#L70-L169)). 

- **Internal gateways**: CSF2TDM gateway nodes located within the nine-county Bay Area are assigned directly to the TM-1.x zone in which they are located. A small buffer is applied during the spatial matching process to account for minor positional inaccuracies between gateway locations and zone boundaries.

- **External Zones and Gateways**: CSF2TDM zones and gateway nodes located outside the nine-county Bay Area are assigned to the nearest TM-1.x gateway, with an allocation weight of 1.0. This mapping is used solely to translate external connectors between zoning systems; external-to-external trips are subsequently excluded through a dedicated masking step during OD matrix projection.

The final crosswalk combines all internal and external mappings into a single table containing source zone identifiers, target zone identifiers, crosswalk type, and allocation weights. All weights are normalized to ensure they sum to 1.0 for each source zone. 

### 2. Matrix Projection 

The matrix projection process transforms CSF2TDM origin-destination (OD) matrices to the TM-1.x zoning system using the previously generated crosswalk. Because the two zoning systems do not share a one-to-one correspondence, trips are redistributed according to crosswalk allocation weights. 

Before projection, a mask is applied to the source matrices to retain only trips that are relevant to the TM-1.x model region. Specifically, a trip is retained if either its origin or destination corresponds to an internal Bay Area zone or gateway. This step prevents external-to-external trips from being projected into the TM-1.x network, while preserving trips that enter, leave, or occur within the modeled region.

Projection is performed using the following matrix operation:

$$
M_{to} = W_{row}^{T} M_{from} W_{col}
$$

where:

- `M_from` is the source CSF2TDM OD matrix.
- `M_to` is the projected TM-1.x OD matrix.
- `W_row` contains origin allocation weights (e.g. production weights)
- `W_col` contains destination allocation weights. (e.g attraction weights)

This formulation efficiently redistributes trips from the source zoning system to the target zoning system while preserving the many-to-many relationships captured in the crosswalk.


### 3. Formatting MTC-Compatible OMX Files

The projection workflow produces a CSF2TDM matrix file that preserves the truck market segments and time-of-day structure used in TM-1.X. However, the TM-1.X travel model expects a different OMX organization consisting of one file per time period (`EA`, `AM`, `MD`, `PM`, and `EV`), with each file containing four truck-class matrices (`vstruck`, `struck`, `mtruck`, and `ctruck`). The resulting matrices are then mapped to the TM-1.X truck classes according to configurable rules defined in the project configuration file.

#### Time-of-Day Mapping

CSF2TDM time periods are translated to TM-1.X time periods using the following mapping:

| Statewide TOD | MTC TOD |
|---------------|---------|
| AM | AM |
| MID | MD |
| PM | PM |
| OFF | EA + EV |

For the AM, MID, and PM periods, the mapping is direct. The OFF period is split between the EA and EV periods. The workflow computes origin-destination-specific split factors using reference MTC trip tables. For each OD pair, EA and EV proportions are calculated from the distribution of truck trips in the reference model. Where no reference trips exist for a given OD pair, the workflow applies an equal split between the target periods.

#### Truck-Class Mapping

Projected CSF2TDM truck classes are aggregated into the truck classes used by TM-1.X:

| MTC Truck Type | Source Matrices |
|---------------|----------------|
| Very Small `vstruck` | Preserved from the reference MTC OMX file |
| Small `struck` | Sum of all `LT_*` matrices |
| Medium `mtruck` | Sum of all `M1T_*` and `M2T_*` matrices |
| Large `ctruck` | Sum of all `HT_*` matrices |

The `vstruck` matrix has no equivalent in the CSF2TDM truck model and is therefore copied directly from the reference TM-1.6 trip tables.


Each file includes the four truck-class matrices used by the MTC travel model (vstruck, struck, mtruck, and ctruck) by time of day. The outputs are formatted to serve as inputs to `model-files/scripts/nonres/TruckTollChoice.job`.

### 4. Production and Attraction Marginals 

For subsequent trip generation model estimation, CSF2TDM truck OD trips are summarized into production and attraction vectors. Productions are calculated as the sum of trips across rows, while attractions are calculated as the sum across columns. These summaries are generated separately for internal-to-internal trips, gateway trips, and special generators.

## Output Files

### Crosswalk

| Field | Data Type | Description |
|---|---|---|
| `from_id` | Integer | Unique identifier for the source CSF2TDM zone or gateway. |
| `to_id` | Integer | Unique identifier for the target TM-1.x TAZ or gateway. |
| `type` | String | Mapping category based on the source feature's location and geometry: `internal_zone`, `external_zone`, `internal_gate`, or `external_gate`. |
| `area_weight` | Float | Allocation weight based on the share of the source zone's area that overlaps the target TAZ. |
| `all_trucks_production_weight` | Float | Production-based allocation weight derived from the TM-1.6 truck trip production equations. |
| `all_trucks_attraction_weight` | Float | Attraction-based allocation weight derived from the TM-1.6 truck trip attraction equations. |


### Projected CSF2TDM OMX Files

The pipeline produces three OMX files containing CSF2TDM truck OD trips projected to the TM-1.x zoning system.

| File | Description |
|---|---|
| `SwTAZ_to_TMTaz_TRIPS_FFM_2020.omx` | Contains truck trips associated with all CSF2TDM zones and gateways, excluding special generators. |
| `SwTazTln_to_TMTaz_TRIPS_FFM_2020.omx` | Contains truck trips associated with MTC special generators only. |
| `SwTLN_to_TMTaz_TRIPS_FFM_2020.omx` | Contains all truck trips, including trips associated with standard zones, gateways, and special generators. |

Each OMX file has the following dimensions:


- **Matrix dimensions:** 1,475 x 1,475
- **Number of matrices:** 44

#### Naming Components
Each matrix name consists of four components separated by underscores:

```text
<truck_class>_<segment>_<geography>_<time_period>
```


#### Truck Class

The first component identifies the truck class.

| Value | Description |
|---|---|
| `LT` | Light trucks |
| `MT1` | Medium-duty trucks, Class 1 |
| `MT2` | Medium-duty trucks, Class 2 |
| `HT` | Heavy trucks |

#### Market Segment

The second component identifies the truck market segment.

| Value | Description |
|---|---|
| `FR` | Freight |
| `NF` | Non-Freight |

#### Geographic Market

The third component identifies the geographic market associated with the truck trips.

| Value | Description |
|---|---|
| `CA` | California truck trips |
| `EXT` | External truck trips |

#### Time Period

The fourth component identifies the CSF2TDM time period.

| Value | Description |
|---|---|
| `OFF` | Off-peak period |
| `AM` | AM peak period |
| `MID` | Midday period |
| `PM` | PM peak period |


### Projected CSF2TDM Files in TM-1.x Format

The pipeline reformats the projected CSF2TDM truck trips to match the file structure and matrix naming conventions required by the TM-1.x travel model.

The output consists of five time-period-specific trip-table sets. Each set is written in two formats:

- **OMX (`.omx`)**: An Open Matrix file used by Python and other OMX-compatible tools.
- **TPP (`.tpp`)**: A Cube-format trip table used by the TM-1.6 model workflow.


Each file contains four truck-class OD matrices with dimensions of 1,475 x 1,475:

| Matrix | Truck Class 
|---|---|
| `vstruck` | Very small trucks |
| `struck` | Small trucks |
| `mtruck` | Medium trucks | 
| `ctruck` | Combination and heavy trucks |


### Production and Attraction Marginals

The pipeline produces three files containing production and attraction marginals derived from the projected CSF2TDM truck OD matrices.

Productions are calculated by summing each OD matrix across destinations (row totals), while attractions are calculated by summing across origins (column totals).

The files report marginals separately for the following zone types:

| File Contents | Number of Records | Description |
|---|---:|---|
| Traffic Analysis Zones | 1,454 | Production and attraction marginals for the internal TM-1.x TAZs. |
| Gateways | 21 | Production and attraction marginals for the TM-1.x regional gateways. |
| Special generators | 6 | Production and attraction marginals for special generators located within the MTC region. |

The production and attraction fields retain the CSF2TDM matrix naming convention and include a suffix identifying the marginal type

For example: 
- HT_FR_CA_PM_production
- HT_FR_CA_PM_attraction
