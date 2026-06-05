from pathlib import Path

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def compute_trip_rates_by_county(od_long, value_cols, land_use, rate_bases):
    mask = (od_long["origin_county"].isin(land_use.index)) & (od_long["destination_county"].isin(land_use.index))
    df = od_long[mask]
    results = []
    source = od_long["source"].iloc[0]

    for t in value_cols:
        trips = df.groupby("origin_county")[t].sum()

        for col, label in rate_bases.items():
            temp = pd.DataFrame({
                "county": trips.index,
                "trips": trips.values,
                "land_use_val": land_use.loc[trips.index, col].values,
                "land_use_col": col
            })

            temp["rate"] = temp["trips"] / temp["land_use_val"]

            temp["type"] = t
            temp["metric"] = label

            results.append(temp)

            # ---------- REGION ----------
            region_trips = trips.sum()
            region_lu = land_use[col].sum()

            results.append(pd.DataFrame({
                "county": ["REGION"],
                "trips": [region_trips],
                "land_use_val": [region_lu],
                "land_use_col": col,
                "rate": [region_trips / region_lu],
                "type": [t],
                "metric": [label]
            }))
    out = pd.concat(results, ignore_index=True)
    out["source"] = source
    return out

def plot_rates(rates_df, outpath=None):

    for metric_name in rates_df["metric"].unique():
    
        data = rates_df[
            (rates_df["metric"] == metric_name) &
            (rates_df["county"] != "REGION")
        ]

        plt.figure(figsize=(10, 6))

        sns.lineplot(
            data=data,
            x="county",
            y="rate",
            hue="type",
            marker="o"
        )

        plt.title(metric_name)
        plt.xlabel("County")
        plt.ylabel(metric_name)
        plt.xticks(rotation=45)

        plt.tight_layout()

        if outpath is not None:
            source = rates_df["source"].loc[0]
            name = metric_name.lower().replace(" ", "_")
            filename = f"{source}_{name}.png"
            path = Path(outpath, filename)
            print(f"Saving {filename} to: {path}")
            plt.savefig(path)