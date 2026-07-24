from pathlib import Path

import openmatrix as omx
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from src.data.EDA.trip_distributions import compute_weighted_histograms

_BLUE   = "#4472C4"   # observed / target data
_ORANGE = "#ED7D31"   # modelled data (bar charts)
_RED    = "#C0392B"   # modelled line / trend line

def plot_trip_distributions(completed_scenarios: list[dict]):


    trip_dist_configs = {
    "Very Small": {
        "distance": "distanceVSM", 
        "trips": "verySmall",
        "observed_path": "data/processed/trip_distribution_inputs/observed_frequency_distribution_blended_distance_strucks.csv", #TODO: Change when I have the right verysmall trucks
        }, 
    "Small": {
        "distance": "distanceSML", 
        "trips": "small", 
        "observed_path": "data/processed/trip_distribution_inputs/observed_frequency_distribution_blended_distance_strucks.csv",
        }, 
    "Medium": {
        "distance": "distanceMED", 
        "trips": "medium", 
        "observed_path": "data/processed/trip_distribution_inputs/observed_frequency_distribution_blended_distance_mtrucks.csv",
        }, 
    "Large": {
        "distance": "distanceLRG", 
        "trips": "large",
        "observed_path": "data/processed/trip_distribution_inputs/observed_frequency_distribution_blended_distance_ctrucks.csv",
        }, 
    }
    to_keep_cols = ['bin_id', 'bin_start', 'bin_end', 'center', 'trips', 'share']

    figures ={}

    
    avg_distance_results = {}
    coincidence_ratio_results = {}
    observed_avg_distance = {}


    for scenario in completed_scenarios:
        scenario_name = scenario["name"]
        scenario_path = scenario["path"]

        skims = read_blended_skims(scenario_path)
        trips = read_trip_distribution_results(scenario_path)
        df = trips.merge(skims, on = ["origin", "destination"], how = "inner")

        for truck_type, configs in trip_dist_configs.items():
            simulated_tlfd = compute_weighted_histograms(df, {configs["trips"]: configs["distance"]}, bins_width = 5)
            observed_tlfd = pd.read_csv(configs["observed_path"])
            merged_tlfd = observed_tlfd[to_keep_cols].merge(
                simulated_tlfd[to_keep_cols], 
                on=['bin_id', 'bin_start', 'bin_end', 'center'], 
                suffixes=('_observed', '_simulated')
            )

            fig, (obs_atl, mod_atl, cr)  = _plot_tlfd(
                merged_tlfd, 
                title = f"{truck_type} Trip Distribution", 
                observed_col = "share_observed", 
                simulated_col = "share_simulated", 
                x_label = "Travel Distance (miles)", 
                y_label = "Share"
            )
            figures[(scenario_name, truck_type)] = fig
            avg_distance_results.setdefault(truck_type, {})[scenario_name] = mod_atl
            coincidence_ratio_results.setdefault(truck_type, {})[scenario_name] = cr
            
            if truck_type not in observed_avg_distance:
                observed_avg_distance[truck_type] = obs_atl

    average_distance = pd.DataFrame.from_dict(avg_distance_results, orient="index")
    average_distance.index.name = "Truck Type"
    average_distance["Observed"] = pd.Series(observed_avg_distance).reindex(average_distance.index)

    coincidence_ratio = pd.DataFrame.from_dict(coincidence_ratio_results, orient="index")
    coincidence_ratio.index.name = "Truck Type"
    return figures, average_distance, coincidence_ratio

def read_blended_skims(scenario_path):
    skims_path = Path(scenario_path, "nonres/blendedTruckTime.omx")
    # skims_path = "../data/processed/trip_distribution_inputs/mtc_blended_skims.omx"
    n = 1454
    base = pd.DataFrame({
        "origin": np.repeat(np.arange(1, n + 1), n),
        "destination": np.tile(np.arange(1, n + 1), n),
    })
    
    # Actual Matricees names: distanceVSM, distanceSML, distanceMED, distanceLRG
    omx_file = omx.open_file(skims_path, "r")
    for skim_name in omx_file.list_matrices():
        if skim_name.startswith("time"):
            continue
        matrix = np.array(omx_file[skim_name])[:1454,:1454]
        base[skim_name] = matrix.ravel()
    omx_file.close()
    return base

def read_trip_distribution_results(scenario_path):
    
    path = Path(scenario_path, "nonres/DailyTruckTrips.omx")
    # path =  "C:/temp/mtc_cube_runs/TM-1.6_FIX_ROUNDING_ISSUE/nonres/DailyTruckTrips.omx"
    n = 1454
    long_format_df = pd.DataFrame({
        "origin": np.repeat(np.arange(1, n + 1), n),
        "destination": np.tile(np.arange(1, n + 1), n),
    })
    
    omx_file = omx.open_file(path, "r")
    for truck_type in omx_file.list_matrices():
        matrix = np.array(omx_file[truck_type])
        long_format_df[truck_type] = matrix.ravel()
    omx_file.close()
    return long_format_df

def _plot_tlfd(
    tlfd_table: pd.DataFrame,
    title: str,
    observed_col = "observed_share", 
    simulated_col = "modeled_share", 
    x_label = "Travel Distance (miles)", 
    y_label = "Share"
) -> Figure:
    """
    Create a single TLFD figure.
    """

    starts = tlfd_table["bin_start"].to_numpy()
    ends   = tlfd_table["bin_end"].to_numpy()

    midpts = (starts + ends) / 2.0
    widths = ends - starts

    obs = tlfd_table[observed_col].to_numpy()
    mod = tlfd_table[simulated_col].to_numpy()

    obs_atl = float((midpts * obs).sum())
    mod_atl = float((midpts * mod).sum())

    # Coincidence Ratio
    cr = np.minimum(obs, mod).sum() / np.maximum(obs, mod).sum()

    fig, ax = plt.subplots(figsize=(5, 4))

    ax.bar(
        starts,
        obs,
        width=widths,
        align="edge",
        color=_BLUE,
        alpha=0.60,
        label="Observed",
    )

    ax.plot(
        midpts,
        mod,
        "o-",
        color=_RED,
        linewidth=1.6,
        markersize=5,
        label="Simulated",
    )

    ax.axvline(
        obs_atl,
        color=_BLUE,
        linestyle="--",
        linewidth=1.2,
        label=f"Observed Average Travel Distance {obs_atl:.1f} min",
    )

    ax.axvline(
        mod_atl,
        color=_RED,
        linestyle="--",
        linewidth=1.2,
        label=f"Simulated Average Travel Distance {mod_atl:.1f} min",
    )

    ax.set_title(f"{title}\nCoincidence Ratio = {cr:.1%}")
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)

    tick_step = 4
    ax.set_xticks(starts[::tick_step])
    ax.set_xticklabels(
        [str(int(v)) for v in starts[::tick_step]],
        rotation=45,
        ha="right"
    )
        
    # ax.legend(fontsize=7)
    handles, labels = ax.get_legend_handles_labels()

    desired_order = [
        "Observed",
        "Simulated",
        f"Observed Average Travel Distance {obs_atl:.1f} min",
        f"Simulated Average Travel Distance {mod_atl:.1f} min",
    ]
    
    handle_dict = dict(zip(labels, handles))

    ax.legend(
        [handle_dict[label] for label in desired_order],
        desired_order,
        fontsize=7, 
        loc="upper right",
        bbox_to_anchor=(1.0, 0.80),
    )
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    return fig, (obs_atl, mod_atl, cr) 