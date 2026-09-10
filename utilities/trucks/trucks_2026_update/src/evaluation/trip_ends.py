from pathlib import Path

import pandas as pd 
import numpy as np
import openmatrix as omx

path_pattern = "TripsTrk{tod}x.omx"
tods = ["EA", "AM", "MD", "PM", "EV"]

def long_format_trips_by_scenario(scenarios: list[dict]):

    rows = []
    for scenario in scenarios:
        scneario_name = scenario["name"]
        scenario_path = scenario["path"]
        for tod in tods: 
            fname = path_pattern.format(tod=tod)
            ref_path = Path(scenario_path, 'nonres', fname)
            reference_omx = omx.open_file(ref_path, "r")
            for truck_type in reference_omx.list_matrices():
                m = np.array(reference_omx[truck_type])
                internal_break = 1454
                correction_factor = 1
                
                if scenario == "BICOUNTY_MODEL":
                    # This is the last TAZ in the 9-county Bay Area Region. 
                    # 6274-6594 Are San Joaquin Country trips. 
                    # Remanining are model gateways. 
                    internal_break = 6272 
                    correction_factor = 0 # Avoid county  SanJoaquin-to-SanJoaquin trips. 
                    m = m/100 # BICOUNTY_MODEL outputs are multiplied by 100 to avoid rounding issues. 
    
                ii = m[:internal_break][:,:internal_break].sum()
                ix = m[:internal_break][:,internal_break:].sum()
                xi = m[internal_break:][:,:internal_break].sum()
                xx = m[internal_break:][:,internal_break:].sum() * correction_factor
                # print(f"{scenario}_{truck_type}_{tod}: {m.sum():.0f}")
            
                rows.append({
                    "scenario": scneario_name,
                    "tod": tod,
                    "truck_type": truck_type,
                    "flow_type": "internal-internal",
                    "truck_trips": ii, 
                })

                rows.append({
                    "scenario": scneario_name,
                    "tod": tod,
                    "truck_type": truck_type,
                    "flow_type": "internal-external",
                    "truck_trips": ix, 
                })

                rows.append({
                    "scenario": scneario_name,
                    "tod": tod,
                    "truck_type": truck_type,
                    "flow_type": "external-internal",
                    "truck_trips": xi, 
                })

                rows.append({
                    "scenario": scneario_name,
                    "tod": tod,
                    "truck_type": truck_type,
                    "flow_type": "external-external",
                    "truck_trips": xx, 
                })
            reference_omx.close()
    df = pd.DataFrame(rows)
    return df

def build_trip_ends_flows_table(df):
    return (
        df.pivot_table(
            index = ["truck_type", "flow_type"], 
            columns = ["scenario"], 
            values = "truck_trips", 
            aggfunc = "sum"
            )
        )

def build_trip_ends_tod_table(df):
    return (
        df.pivot_table(
            index = ["truck_type","tod"], 
            columns = ["scenario"], 
            values = "truck_trips", 
            aggfunc = "sum"
        )
    )