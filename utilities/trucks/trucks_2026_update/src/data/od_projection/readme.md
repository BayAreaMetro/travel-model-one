# CSF2TDM TO TM-1.6 OD Projection Pipeline 

This pipeline projects origin-destination (OD) matrices from the CSF2TDM zoning system into the TM-1.6 zoning system. It reads input OMX matrices, prepares and standardizes the required spatial inputs, builds a spatial crosswalk, project OD matrices, and writes the projected matrices to new OMX output files.

The CSF2TDM matrices contain 7,000 zones. Of these, 5,128 are TAZs represented as polygons, while the remaining records are node-based zones used to represent regional gateways and special generator nodes, such as transportation logistics nodes (e.g.,:  the Port of Oakland). For this workflow, polygon-based zones are referred to as **zones**, and node-based zones are referred to as **gates**.

The projection separates OD truck trips into two output views. One projection includes OD flows from/to zones within the MTC boundary (internal zones), another includes OD flows from/to gates withing the MTC boundary (internal gates), and a third combines both internal zones and internal gates. 

```text
Config
  ↓
Load input datasets
  ↓
Prepare and standardize inputs
  ↓
Build crosswalk
  ↓
Project matrices
  ├─ zones + gates
  ├─ zones only
  └─ gates only
  ↓
Write output OMX files
```

## Usage

Run the pipeline from the project root using Python’s module execution syntax.

```bash
python -m src.data.od_projection.pipeline
python -m src.data.od_projection.pipeline --config <path_to_config> 
```

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
  