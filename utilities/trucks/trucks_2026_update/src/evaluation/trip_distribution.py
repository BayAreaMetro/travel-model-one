
from pathlib import Path

import pandas as pd
import numpy as np
import openmatrix as omx
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from src.data.EDA.trip_distributions import compute_weighted_histograms

_BLUE   = "#4472C4"   # observed trip distributions 
_RED    = "#C0392B"   # modelled trip distributions

trip_dist_configs = {
    "Very Small": {
        "distance": "distanceVSM", 
        "trips": "verySmall",
        "observed_path": "data/processed/trip_distribution_inputs/observed_frequency_distribution_blended_distance_vstrucks.csv", 
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


def read_blended_skims(scenario_path) -> pd.DataFrame:
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


def read_trip_distribution_results(scenario_path) -> pd.DataFrame:
    path = Path(scenario_path, "nonres/DailyTruckTrips.omx")
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


def build_trip_distribution(completed_scenarios) -> dict:

    results = {}

    for scenario in completed_scenarios:

        scenario_name = scenario["name"]

        skims = read_blended_skims(scenario["path"])
        trips = read_trip_distribution_results(scenario["path"])

        df = trips.merge(
            skims,
            on=["origin", "destination"],
            how="inner"
        )

        scenario_results = {}

        for truck_type, configs in trip_dist_configs.items():

            simulated_tlfd = compute_weighted_histograms(
                df,
                {configs["trips"]: configs["distance"]},
                bins_width=5
            )

            observed_tlfd = pd.read_csv(configs["observed_path"])

            merged_tlfd =  observed_tlfd[to_keep_cols].merge(
                simulated_tlfd[to_keep_cols], 
                on=['bin_id', 'bin_start', 'bin_end', 'center'], 
                suffixes=('_observed', '_simulated')
                )

            scenario_results[truck_type] = merged_tlfd

        results[scenario_name] = scenario_results

    return results


def build_average_trip_distance_table(results) -> pd.DataFrame:

    avg_distance_results = {}
    observed_avg_distance = {}

    for scenario_name, scenario_results in results.items():

        for truck_type, tlfd in scenario_results.items():

            starts = tlfd["bin_start"].to_numpy()
            ends = tlfd["bin_end"].to_numpy()
            midpts = (starts + ends) / 2.0

            obs = tlfd["share_observed"].to_numpy()
            sim = tlfd["share_simulated"].to_numpy()

            obs_mean = float((midpts * obs).sum())
            sim_mean = float((midpts * sim).sum())

            avg_distance_results.setdefault(truck_type, {})[scenario_name] = sim_mean

            if truck_type not in observed_avg_distance:
                observed_avg_distance[truck_type] = obs_mean

    df = pd.DataFrame.from_dict(
        avg_distance_results,
        orient="index"
    )

    df.index.name = "Truck Type"

    df["Observed"] = (
        pd.Series(observed_avg_distance)
        .reindex(df.index)
    )

    return df


def build_coincidence_ratio_table(results)-> pd.DataFrame:

    coincidence_ratio_results = {}

    for scenario_name, scenario_results in results.items():

        for truck_type, tlfd in scenario_results.items():

            obs = tlfd["share_observed"].to_numpy()
            mod = tlfd["share_simulated"].to_numpy()

            cr = (
                np.minimum(obs, mod).sum()
                / np.maximum(obs, mod).sum()
            )

            coincidence_ratio_results.setdefault(
                truck_type, {}
            )[scenario_name] = cr

    df = pd.DataFrame.from_dict(
        coincidence_ratio_results,
        orient="index"
    )

    df.index.name = "Truck Type"

    return df


def plot_trip_distributions(results) -> dict[tuple[str, str], Figure]:

    figures = {}

    for scenario_name, scenario_results in results.items():

        for truck_type, tlfd in scenario_results.items():

            fig = _plot_tlfd(
                tlfd,
                title=f"{truck_type} Trip Distribution",
                observed_col="share_observed",
                simulated_col="share_simulated",
                x_label="Travel Distance (miles)",
                y_label="Share",
            )

            figures[(scenario_name, truck_type)] = fig

    return figures


def _plot_tlfd(
    tlfd_table: pd.DataFrame,
    title: str,
    observed_col: str = "share_observed",
    simulated_col: str = "share_simulated",
    x_label: str = "Travel Distance (miles)",
    y_label: str = "Share",
) -> Figure:
    """Create a TLFD comparison figure."""

    starts = tlfd_table["bin_start"].to_numpy()
    ends = tlfd_table["bin_end"].to_numpy()

    midpts = (starts + ends) / 2.0
    widths = ends - starts

    obs = tlfd_table[observed_col].to_numpy()
    sim = tlfd_table[simulated_col].to_numpy()

    # Average Trip Length
    obs_mean = float((midpts * obs).sum())
    sim_mean = float((midpts * sim).sum())

    # Coincidence Ratio
    coincidence_ratio = (
        np.minimum(obs, sim).sum()
        / np.maximum(obs, sim).sum()
    )

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
        sim,
        "o-",
        color=_RED,
        linewidth=1.6,
        markersize=5,
        label="Simulated",
    )

    ax.axvline(
        obs_mean,
        color=_BLUE,
        linestyle="--",
        linewidth=1.2,
        label=f"Observed Avg Distance {obs_mean:.1f} mi",
    )

    ax.axvline(
        sim_mean,
        color=_RED,
        linestyle="--",
        linewidth=1.2,
        label=f"Simulated Avg Distance {sim_mean:.1f} mi",
    )

    ax.set_title(
        f"{title}\nCoincidence Ratio = {coincidence_ratio:.1%}"
    )

    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)

    tick_step = 4

    ax.set_xticks(starts[::tick_step])

    ax.set_xticklabels(
        [str(int(v)) for v in starts[::tick_step]],
        rotation=45,
        ha="right",
    )

    handles, labels = ax.get_legend_handles_labels()

    desired_order = [
        "Observed",
        "Simulated",
        f"Observed Avg Distance {obs_mean:.1f} mi",
        f"Simulated Avg Distance {sim_mean:.1f} mi",
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

    return fig
