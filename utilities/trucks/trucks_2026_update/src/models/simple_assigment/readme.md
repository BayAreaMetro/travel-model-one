# Simple Assignment

## Overview

This workflow runs a **partial TM1.6 model execution**, covering:

- Truck toll choice
- Highway assignment
- Post-processing steps (preparing networks for the next iteration)

It executes **a single Highway assignment iteration**, using **externally produced truck OD matrices** in place of the TM-1.6 truck demand.

This workflow uses outputs from a completed TM1.6 run to initialize the simulation at the Truck Toll Choice step. For these experiments, the base run is available from: https://mtcdrive.box.com/s/rrgnyrc73uogqvxtzvkihxz8cqlyeg67. Download and extract this file locally into `data/external/mtc`.

## Usage

### Step 1: Navigate to script directory

```powershell
cd travel-model-one\utilities\trucks\trucks_2026_update\src\models\simple_assigment
```

### Step 2: Run the batch script

```powershell
.\RunAssignment.bat <scenario_name> <scenario_inputs>
```


### Arguments


- `<scenario_name>`: Name of the run. Used to define output folders and log files.
- `<scenario_inputs>` (optional): Path to a directory containing `.tpp` truck trip matrices.  

If `<scenario_inputs>` is not provided, the workflow will use the truck trip tables included in the base TM1.6 run.

For this project, an ETL pipeline is available to transform **CSF2TDM (FFM) model outputs** into the required `.tpp` format.  See **Running Simple Assignment with CSF2TDM Truck Trip Data** for instructions to run the pipeline and use it for the simple assignment. 


## Running Simple Assignment with CSF2TDM Truck Trip Data

### 1. Run the OD Projection Pipeline

Truck trip matrices must be generated using:

```
travel-model-one/utilities/trucks/trucks_2026_update/src.data.od_projection.pipeline
```

This produces:

```
data/interim/matrix_projection/sw_od_trips_with_mtc_format/
```

---

### 2. Convert OMX → TPP

In CUBE Run :

```
travel-model-one/utilities/trucks/trucks_2026_update/src/models/simple_assigment/convert_sw_with_mtc_format_omx_to_tpp.s
```

This script will:
- Read OMX files
- Generate `.tpp` matrices


---

### 3. Run Simple Assigment 


```powershell
.\RunAssignment.bat tm16_with_sw_trips data\interim\matrix_projection\sw_od_trips_with_mtc_format
```


### 4. Outputs

A loaded network is save in this location

```
data/interim/tm16_outputs/<scenario_name>/
```
---
