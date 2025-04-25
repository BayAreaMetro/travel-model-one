#!/usr/bin/env python3
USAGE="""
This script is used for computing accessibility benefits (logsum). 
The function calculateConsumerSurplus() is adopted unchanged from mapAccessibilityDiffs.py.

It accesses model runs files from the M drive.
The final output is a single CSV file named "NPA_metrics_Goal_1G_1H.csv".

The script reads the following input files:
- {scenario_dir}/INPUT/metrics/taz_coc_crosswalk.csv (EPC_18 data)
- {scenario_dir}/INPUT/metrics/taz1454_epcPBA50plus_2024_02_29.csv (EPC_22 data)
- {base_dir}|{scenario_dir}/logsums/mandatoryAccessibilities.csv (mandatory accessibilities)
- {base_dir}|{scenario_dir}/logsums/nonMandatoryAccessibilities.csv (nonmandatory accessibilities)
- {base_dir}|{scenario_dir}/core_summaries/AccessibilityMarkets.csv (accessibility markets)

The script writes the following output files:
- {scenario_dir}/OUTPUT/metrics/NPA_Metrics_Goal_1G_1H.csv with columns:
  + epc_category:          one of all_taz, epc_22, epc_18
  + base_id:               base model run ID
  + scenario_id:           scenario model run ID
  + CS diff work/school:   consumer surplus change for mandatory tours
  + num_workers_students:  number of workers and students (potentially making mandatory tours)
  + per_capita CS diff work/school: CS diff work/school divided by num_workers_students
  + CS diff nonmand:       consumer surplus change for nonmandatory tours
  + num_persons:           number of persons (potentially making nonmandatory tours)
  + per_capita CS diff nonmand: CS diff nonmand divided by num_persons
  + per_capita CS diff combined: (CS diff work/school + CS diff nonmand) / (num_workers_students + num_persons)
  + per_capita CS diff work/school relative_to_all: EPC category version / all_taz version
  + per_capita CS diff nonmand relative_to_all: EPC category version / all_taz version
  + per_capita CS diff combined relative_to_all: EPC category version / all_taz version

Goal 1 scripts asana task: https://app.asana.com/1/11860278793487/project/1205004773899709/task/1209227244858523?focus=true

"""

import argparse, pathlib
import pandas as pd
from collections import OrderedDict
import mapAccessibilityDiffs
import RunResults


def compute_access_benefits_metrics(blueprint_dir, base_id, scen_id):
    """
    Compute final access metrics from the daily accessibility processing, merge with EPC data, and return a DataFrame.
    """
    # Read accessbilities for base_id and scen_id
    base_mandatory    = mapAccessibilityDiffs.read_accessibilities(str(blueprint_dir / base_id), True,  "base", True)
    base_nonmandatory = mapAccessibilityDiffs.read_accessibilities(str(blueprint_dir / base_id), False, "base", True)
    scen_mandatory    = mapAccessibilityDiffs.read_accessibilities(str(blueprint_dir / scen_id), True,  "scen", True)
    scen_nonmandatory = mapAccessibilityDiffs.read_accessibilities(str(blueprint_dir / scen_id), False, "scen", True)
    print(f"base_mandatory.head():\n{base_mandatory.head()}")
    print(f"base_nonmandatory.head():\n{base_nonmandatory.head()}")
    print(f"scen_mandatory.head():\n{scen_mandatory.head()}")
    print(f"scen_nonmandatory.head():\n{scen_nonmandatory.head()}")

    # Read accessibility markets
    base_markets = mapAccessibilityDiffs.read_markets(str(blueprint_dir / base_id), "base", True)
    scen_markets = mapAccessibilityDiffs.read_markets(str(blueprint_dir / scen_id), "scen", True)
    print(f"base_markets.head():\n{base_markets.head()}")
    print(f"scen_markets.head():\n{scen_markets.head()}")    
    
    # Create an empty dictionary for daily results
    daily_results = OrderedDict()
    
    # Create minimal config
    config = {}
    
    # Use the static method to calculate consumer surplus
    _, _, mandatoryAccess, nonmandatoryAccess = RunResults.RunResults.calculateConsumerSurplus(
        config                          =config,
        daily_results                   =daily_results,
        mandatoryAccessibilities        =scen_mandatory,
        base_mandatoryAccessibilities   =base_mandatory,
        nonmandatoryAccessibilities     =scen_nonmandatory,
        base_nonmandatoryAccessibilities=base_nonmandatory,
        accessibilityMarkets            =scen_markets,
        base_accessibilityMarkets       =base_markets,
        debug_dir=None  
    )
    print(f"mandatoryAccess:\n{mandatoryAccess}")
    print(f"nonmandatoryAccess:\n{nonmandatoryAccess}")

    # Read Equity Priority Communities (EPC) files
    epc_22_df = pd.read_csv(blueprint_dir / scen_id / "INPUT/metrics/taz1454_epcPBA50plus_2024_02_29.csv", usecols=['TAZ1454','taz_epc'])
    epc_18_df = pd.read_csv(blueprint_dir / scen_id / "INPUT/metrics/taz_coc_crosswalk.csv")
    epc_df = pd.merge(
        left=epc_22_df.rename(columns={'taz_epc':'epc_22'}),
        right=epc_18_df.rename(columns={'taz_coc':'epc_18'}),
        on='TAZ1454',
        validate='one_to_one'
    ).sort_values(by='TAZ1454').reset_index(drop=True)
    print(f"epc_df:\n{epc_df}")
    epc_df['all_taz'] = 1 # this is a bit silly but it removes need for if statements
    # columns are TAZ1454, epc_18, epc_22

    # add epc_18 and epc_22 columns to mandatoryAccess, nonmandatoryAccess
    mandatoryAccess = pd.merge(
        left=mandatoryAccess,
        right=epc_df.rename(columns={'TAZ1454':'taz'}),
        on='taz',
        validate='many_to_one'
    )
    nonmandatoryAccess = pd.merge(
        left=nonmandatoryAccess,
        right=epc_df.rename(columns={'TAZ1454':'taz'}),
        on='taz',
        validate='many_to_one'
    )
    # this is a silly but the RunResults.py code recalculates this column with CEM=False so go back to LCM-based definitions
    mandatoryAccess['CS diff work/school'] = \
        (0.5*mandatoryAccess.base_num_workers_students + 0.5*mandatoryAccess.scen_num_workers_students)*mandatoryAccess.ldm_cem
    nonmandatoryAccess['CS diff all'] = \
        (0.5*nonmandatoryAccess.base_num_persons + 0.5*nonmandatoryAccess.scen_num_persons)*nonmandatoryAccess.ldm_cem
    
    # # Export debug files (optional)
    # mandatoryAccess.to_csv(f"mandatoryAccess_(intermediate_file).csv", index=False)
    # nonmandatoryAccess.to_csv(f"nonmandatoryAccess_(intermediate_file).csv", index=False)
    # columns: taz,epc_22,epc_18,taz_all,walk_subzone,walk_subzone_label,incQ,incQ_label,autoSuff,autoSuff_label,hasAV,mandatory,
    #   base_dclogsum, scen_dclogsum, diff_dclogsum,logsum_diff_minutes,ldm_ratio,ldm_mult,ldm_cem,CS diff all
    #   base_num_persons,base_num_workers,scen_num_workers_students,
    #   scen_num_persons,scen_num_workers,base_num_workers_students,

    # 1G) Total regional accessibility benefit in annualized minutes of equivalent travel time savings
    metrics_dict_list = []
    for epc_category in ["all_taz", "epc_22", "epc_18"]:
        metrics_dict = {}
        metrics_dict['epc_category'] = epc_category
        metrics_dict['base_id']      = base_id
        metrics_dict['scenario_id']  = scen_id
        
        # mandatory
        metrics_dict['CS diff work/school'] =      mandatoryAccess.loc[   mandatoryAccess[epc_category]==1, 'CS diff work/school'].sum()
        metrics_dict['num_workers_students'] = 0.5*mandatoryAccess.loc[   mandatoryAccess[epc_category]==1, 'base_num_workers_students'].sum() + \
                                               0.5*mandatoryAccess.loc[   mandatoryAccess[epc_category]==1, 'scen_num_workers_students'].sum()
        metrics_dict['per_capita CS diff work/school'] = metrics_dict['CS diff work/school'] / metrics_dict['num_workers_students']

        # nonmandatory
        metrics_dict['CS diff nonmand']     =     nonmandatoryAccess.loc[nonmandatoryAccess[epc_category]==1, 'CS diff all'].sum()
        metrics_dict['num_persons']         = 0.5*nonmandatoryAccess.loc[nonmandatoryAccess[epc_category]==1, 'base_num_persons'].sum() + \
                                              0.5*nonmandatoryAccess.loc[nonmandatoryAccess[epc_category]==1, 'scen_num_persons'].sum()
        metrics_dict['per_capita CS diff nonmand'] = metrics_dict['CS diff nonmand'] / metrics_dict['num_persons']

        # combination of both (does this make sense?)
        metrics_dict['per_capita CS diff combined'] = (metrics_dict['CS diff work/school'] + metrics_dict['CS diff nonmand']) / \
                                                     (metrics_dict['num_workers_students'] + metrics_dict['num_persons'])
        metrics_dict_list.append(metrics_dict)

        # 1H) Ratio of the per-capita regional accessibility benefit for EPC residents relative to the
        #     per-capita regional accessibility benefit for all travelers    
        metrics_dict['per_capita CS diff work/school relative_to_all'] = metrics_dict['per_capita CS diff work/school'] / \
                                                                 metrics_dict_list[0]['per_capita CS diff work/school']

        metrics_dict['per_capita CS diff nonmand relative_to_all'] = metrics_dict['per_capita CS diff nonmand'] / \
                                                             metrics_dict_list[0]['per_capita CS diff nonmand']
        
        metrics_dict['per_capita CS diff combined relative_to_all'] = metrics_dict['per_capita CS diff combined'] / \
                                                              metrics_dict_list[0]['per_capita CS diff combined']
    metrics_df = pd.DataFrame(metrics_dict_list)
    print(f"metrics_df:\n{metrics_df}")

    return metrics_df

# ---------------------------
# Main routine
# ---------------------------
if __name__ == '__main__':
    pd.set_option('display.width', 500)
    pd.set_option('display.precision', 10)

    parser = argparse.ArgumentParser(description = USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('base_id', help="Base model run ID")
    parser.add_argument('scen_id', help="Scenario model run ID")
    my_args = parser.parse_args()

    blueprint_dir = pathlib.Path("M:\Application\Model One\RTP2025\Blueprint")
    # temporary for testing
    # blueprint_dir = blueprint_dir / "Archive_FBP"

    # Compute the access benefits (logsum) metrics
    access_benefit_df = compute_access_benefits_metrics(
        blueprint_dir, my_args.base_id, my_args.scen_id)
    
    output_file = blueprint_dir / my_args.scen_id / "OUTPUT" / "metrics" / "NPA_Metrics_Goal_1G_1H.csv"
    access_benefit_df.to_csv(output_file, index = False)
    print(f"Wrote {len(access_benefit_df)} rows to {output_file}")
