"""Build the tolled and time-of-day highway networks (RunModel.bat step 3).

The stock Cube jobs run as-is; the one piece of legacy glue between them is
rewritten natively:

- ``csvToDbf.py`` -> :func:`_write_dbf` — ``hwy/tolls.csv`` to the
  ``hwy/tolls.dbf`` that ``SetTolls.job``'s ``LOOKUPI`` reads (Cube's lookup
  cannot read csv).  Same column-type inference ladder as the legacy script:
  try int, fall back to float, fall back to string.
- ``SetTolls.job``                  ``hwy/freeflow.net`` -> ``hwy/withTolls.net``
- ``SetHovXferPenalties.job``       ``hwy/withTolls.net`` -> ``hwy/withHovXferPenalties.net``
- ``CreateFiveHighwayNetworks.job`` ``hwy/withTolls.net`` -> ``hwy/avgload{EA..EV}.net``

None of the jobs distributes, so no Cube cluster is started.

``withHovXferPenalties.net`` is consumed by nothing downstream —
``CreateFiveHighwayNetworks`` reads ``withTolls.net`` — but the job still runs
so the sequence stays exactly ``RunModel.bat``'s.

Config::

    build_highway_networks:
      run_dir: "{run_dir}"

.. warning:: CUBE-ERA IMPLEMENTATION — DELETE WITH CUBE, KEEP THE STEP'S JOB.

    The *function* is permanent: every assignment engine needs tolled,
    time-of-day networks built from ``INPUT/hwy``.  The *implementation* is
    not: the three ``.job`` scripts and the ``.net`` files they produce mean
    nothing to a non-Cube engine (the AequilibraE lineage already builds its
    networks natively — see ``build_aeq_inputs``).  When Cube is retired,
    replace this module's body wholesale rather than porting any of it, and
    delete the DBF writer below with it: ``tolls.dbf`` exists only because
    Cube's ``LOOKUPI`` cannot read csv.  Do not promote the DBF writer to a
    shared utility.
"""

import csv
import logging
import struct
from datetime import datetime
from pathlib import Path

from cube.job import run_cube_job
from tm1.project.config import step_config

log = logging.getLogger(__name__)

PERIODS: tuple[str, ...] = ("EA", "AM", "MD", "PM", "EV")

_JOBS: tuple[str, ...] = (
    "SetTolls.job",
    "SetHovXferPenalties.job",
    "CreateFiveHighwayNetworks.job",
)

_OUTPUTS: tuple[str, ...] = (
    "withTolls.net",
    "withHovXferPenalties.net",
    *(f"avgload{p}.net" for p in PERIODS),
)

# DBF field widths, as csvToDbf.py chose them: numerics are 10 wide (5 decimal
# places when float); strings are sized to the longest value plus two.
_NUM_WIDTH = 10
_NUM_DECIMALS = 5
_DBF_NAME_LEN = 10


def _infer_fields(header: list[str], rows: list[list[str]]) -> list[tuple[str, str, int, int]]:
    """Per-column DBF specs ``(name, type, length, decimals)`` from the csv values.

    Follows csvToDbf.py's ladder — a column is int until a value fails ``int()``,
    then float until one fails ``float()``, then character — so the fields come
    out identical to what the legacy conversion produced.
    """
    fields: list[tuple[str, str, int, int]] = []
    seen: set[str] = set()
    for idx, col in enumerate(header):
        name = col[:_DBF_NAME_LEN].upper()
        if name in seen:
            msg = f"Column {col!r} collides with another at DBF name {name!r}"
            raise ValueError(msg)
        seen.add(name)

        values = [row[idx] for row in rows]
        try:
            for v in values:
                int(v)
            fields.append((name, "N", _NUM_WIDTH, 0))
            continue
        except ValueError:
            pass
        try:
            for v in values:
                float(v)
            fields.append((name, "N", _NUM_WIDTH, _NUM_DECIMALS))
        except ValueError:
            fields.append((name, "C", max(len(v) for v in values) + 2, 0))
    return fields


def _format_value(value: str, ftype: str, length: int, decimals: int) -> bytes:
    """One csv value as its fixed-width DBF record bytes."""
    if ftype == "N":
        text = str(int(value)) if decimals == 0 else f"{float(value):.{decimals}f}"
        out = text.rjust(length)
    else:
        out = value.ljust(length)
    if len(out) > length:
        msg = f"Value {value!r} does not fit DBF field width {length}"
        raise ValueError(msg)
    return out.encode("ascii")


def _write_dbf(csv_path: Path, dbf_path: Path) -> int:
    """Convert a csv to a dBASE III file (native csvToDbf.py). Returns row count."""
    with csv_path.open(newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    fields = _infer_fields(header, rows)
    record_size = 1 + sum(length for _, _, length, _ in fields)
    header_size = 32 + 32 * len(fields) + 1
    today = datetime.now().astimezone()

    with dbf_path.open("wb") as out:
        out.write(
            struct.pack(
                "<4BIHH20x",
                0x03, today.year - 1900, today.month, today.day,
                len(rows), header_size, record_size,
            )
        )
        offset = 1  # running record offset, as the legacy writer recorded it
        for name, ftype, length, decimals in fields:
            out.write(
                struct.pack(
                    "<11scI2B14x",
                    name.encode("ascii"), ftype.encode("ascii"),
                    offset, length, decimals,
                )
            )
            offset += length
        out.write(b"\x0d")
        for row in rows:
            out.write(b" ")
            for value, spec in zip(row, fields, strict=True):
                out.write(_format_value(value, spec[1], spec[2], spec[3]))
        out.write(b"\x1a")

    log.info("Wrote %s: %d records, %d fields", dbf_path, len(rows), len(fields))
    return len(rows)


def run(
    config_dir: Path,  # noqa: ARG001
    cfg: dict,
    **kwargs: object,
) -> str | None:
    """tolls.csv -> tolls.dbf, then the three stock network-building Cube jobs."""
    step_cfg = step_config(cfg, "build_highway_networks", kwargs)
    run_dir = Path(step_cfg.get("run_dir") or cfg["run_dir"])
    hwy = run_dir / "hwy"

    if not kwargs.get("force", False) and all((hwy / n).exists() for n in _OUTPUTS):
        log.info("Highway networks already built in %s", hwy)
        return "skipped"

    for needed in (hwy / "freeflow.net", hwy / "tolls.csv"):
        if not needed.exists():
            msg = f"build_highway_networks input missing: {needed}"
            raise FileNotFoundError(msg)

    _write_dbf(hwy / "tolls.csv", hwy / "tolls.dbf")

    scripts = run_dir / "CTRAMP" / "scripts" / "preprocess"
    for job in _JOBS:
        run_cube_job(scripts / job, run_dir, timeout=1800)

    missing = [n for n in _OUTPUTS if not (hwy / n).exists()]
    if missing:
        msg = f"Cube jobs finished but outputs are missing from {hwy}: {missing}"
        raise FileNotFoundError(msg)
    return None
