"""Configuration dataclasses for calibration summaries."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DatasetConfig:
    """One labeled dataset (e.g. a CTRAMP run, a BATS survey).

    Weighting is **either** a uniform ``sampleshare`` expansion *or* explicit
    per-table ``weight_cols`` — never both.  When ``weight_cols`` is
    non-empty, ``sampleshare`` is forced to 1.0.

    Attributes:
        label: Human-readable name shown in outputs.
        paths: Mapping of table name → file path.  Table names must match
            :class:`~.bundle.ModelBundle` field names (e.g. ``wsloc_results``,
            ``taz_data``, ``dist_skim``).
        sampleshare: Population fraction (1.0 for survey/census).
        weight_cols: Mapping of table name → weight column name.  No
            "default" fallback — every table that needs a weight must be
            listed explicitly.
        format: Source data format — drives column renaming to canonical names.
            One of ``"ctramp"``, ``"activitysim"``, or ``"survey"``.
    """

    label: str
    paths: dict[str, Path] = field(default_factory=dict)
    sampleshare: float = 1.0
    weight_cols: dict[str, str] = field(default_factory=dict)
    format: str = "ctramp"


@dataclass
class CalibrationRunConfig:
    """Top-level config for a calibration comparison run.

    Attributes:
        output_dir: Where CSVs and comparison files are written.
        datasets: One or more labeled datasets to summarize/compare.
        submodels: Which submodel summarizers to run.
        write_csv: Whether to write per-dataset CSV files.
    """

    output_dir: Path
    datasets: list[DatasetConfig] = field(default_factory=list)
    submodels: list[str] = field(default_factory=list)
    write_csv: bool = True


def parse_config(cfg: dict) -> CalibrationRunConfig:
    """Parse the ``steps.summaries.calibration`` dict from scenario_config.yaml.

    Expected shape::

        calibration:
          output_dir: "path/to/output"
          datasets:
            - label: "CTRAMP_v161"
              sampleshare: 0.5
              paths:
                wsloc_results: "..."
                taz_data: "..."
          submodels:
            - work_school_location
            - auto_ownership
    """
    calib = cfg.get("steps", {}).get("summaries", {}).get("calibration", {}) or {}

    output_dir = Path(calib.get("output_dir", "output/calibration"))

    datasets = []
    for ds in calib.get("datasets", []):
        raw_wc = ds.get("weight_col", {})
        has_sampleshare = "sampleshare" in ds
        has_weights = bool(raw_wc)

        if has_sampleshare and has_weights:
            msg = (
                f"Dataset {ds['label']!r}: 'sampleshare' and 'weight_col' are "
                f"mutually exclusive — specify one or the other."
            )
            raise ValueError(msg)

        if has_weights:
            if not isinstance(raw_wc, dict):
                msg = (
                    f"Dataset {ds['label']!r}: 'weight_col' must be a mapping "
                    f"of table_name → column_name, got {type(raw_wc).__name__}."
                )
                raise TypeError(msg)
            weight_cols = dict(raw_wc)
            sampleshare = 1.0
        else:
            weight_cols = {}
            sampleshare = float(ds.get("sampleshare", 1.0))

        datasets.append(
            DatasetConfig(
                label=ds["label"],
                paths={k: Path(v) for k, v in ds.get("paths", {}).items()},
                sampleshare=sampleshare,
                weight_cols=weight_cols,
                format=ds.get("format", "ctramp"),
            ),
        )

    submodels = calib.get("submodels", [])
    write_csv = bool(calib.get("write_csv", True))

    return CalibrationRunConfig(
        output_dir=output_dir,
        datasets=datasets,
        submodels=submodels,
        write_csv=write_csv,
    )
