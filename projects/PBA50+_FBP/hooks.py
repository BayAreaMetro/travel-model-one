"""Project-specific pipeline steps for ctramp_2023.

Anything in here is ordinary Python, wired in from ``config.yaml``::

    steps:
      vmt_vht_metrics:
        script: "hooks.py:vmt_vht_metrics"

A step is any function taking ``(config_dir, cfg, **kwargs)`` -- the same
contract the built-in steps use.  Where it appears under ``steps:`` decides when
it runs: before ``simulate_ctramp`` makes it pre-processing, after ``assignment``
makes it post-processing.  Return ``"skipped"`` to record a no-op.
"""

import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

PERIODS = ("EA", "AM", "MD", "PM", "EV")

#: Facility types counted as freeway, per ``utilities/RTP/metrics/hwynet.py``:
#: freeway-to-freeway connectors (1), freeways (2) and managed freeways (8).
_FREEWAY_FT = (1, 2, 8)

#: Dummy links carry no real traffic; hwynet.py drops them the same way.
_DUMMY_FT = 6


def vmt_vht_metrics(
    config_dir: Path,  # noqa: ARG001
    cfg: dict,
    **kwargs: object,
) -> str | None:
    """Summarise the loaded network into VMT and VHT by facility type.

    Reads ``hwy/iter{N}/avgload5period.csv`` -- written by the feedback block --
    and writes ``metrics/vmt_vht_metrics.csv``.

    A reduced form of ``utilities/RTP/metrics/hwynet.py``, which additionally
    splits by vehicle class and joins collision, delay and emissions lookups.
    Those need ``avgload5period_vehclasses.csv`` from ``net2csv_avgload5period.job``,
    part of the post-processing phase this pipeline does not yet run.

    Deliberately aggregates rather than copies: the input is ~10 MB and the
    output is a handful of rows, so nothing is duplicated on disk.
    """
    run_dir = Path(cfg["run_dir"])
    # The runner supplies this step's round -- for a step after the loop, the
    # final one.  Reading it out of `steps:` is what a step must NOT do now that
    # a name can appear in several rounds.
    iteration = int(kwargs.get("iteration") or 1)

    loaded = run_dir / "hwy" / f"iter{iteration}" / "avgload5period.csv"
    if not loaded.is_file():
        log.warning("vmt_vht_metrics: %s not found; did the feedback block run?", loaded)
        return "skipped"

    links = pd.read_csv(loaded, skipinitialspace=True)
    links.columns = [c.strip() for c in links.columns]
    links = links[links["ft"] != _DUMMY_FT]

    rows = []
    for period in PERIODS:
        vol = links[f"vol{period}_tot"]
        rows.append(pd.DataFrame({
            "period": period,
            "ft": links["ft"],
            "road_type": links["ft"].isin(_FREEWAY_FT).map(
                {True: "freeway", False: "non-freeway"}
            ),
            "vmt": vol * links["distance"],
            "vht": vol * links[f"ctim{period}"] / 60.0,
            "lane_miles": links["distance"] * links["lanes"],
        }))

    by_link = pd.concat(rows, ignore_index=True)
    summary = (
        by_link.groupby(["period", "road_type", "ft"], as_index=False)
        [["vmt", "vht", "lane_miles"]].sum()
    )
    # Congested speed implied by the assignment, the headline check on a run.
    summary["avg_speed_mph"] = (summary["vmt"] / summary["vht"]).round(1)

    out_dir = run_dir / "metrics"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "vmt_vht_metrics.csv"
    summary.to_csv(out_path, index=False)

    vmt, vht = summary["vmt"].sum(), summary["vht"].sum()
    log.info(
        "vmt_vht_metrics: iter %d -- daily VMT %s, VHT %s, "
        "implied average speed %.1f mph -> %s",
        iteration, f"{vmt:,.0f}", f"{vht:,.0f}",
        vmt / vht if vht else 0.0, out_path,
    )
    return None
