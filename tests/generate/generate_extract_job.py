"""Generate a Cube .job that extracts sampled rows from full TPPs into small
golden TPPs, then dumps them to CSV.

Uses the SAME row-sampling logic so the golden CSVs and golden TPPs cover
exactly the same cells.

The output TPPs have the same zone count and tables as the originals, but
only the sampled rows contain data — everything else is zero.  This makes
the files very small (all-zero rows compress to ~8 bytes each in TPP).

Usage:
    python tests/generate/generate_extract_job.py

Writes:
    tests/generate/extract_golden_tpps.job   — run on MODEL3-C with runtpp

Output on MODEL3-C:
    golden_tpp/*.tpp   — small golden TPP files
    golden_tpp/*.csv   — Cube's own CSV dump of those TPPs (ground truth)
"""

import hashlib
import random
from pathlib import Path

# Must match cherry_pick_test_data.py exactly
FIXED_ROWS = [1, 2, 3, 100, 500, 1000, 1473, 1474, 1475]
N_RANDOM = 10
ZONES = 1475

SKIMS_DIR = r"E:\Model3C-Share\Projects\2023_TM161_IPA_35_testrun\skims"
OUTPUT_DIR = r"E:\Model3C-Share\Projects\2023_TM161_IPA_35_testrun\skims\golden_tpp"


def seed_for_file(stem: str) -> int:
    return int(hashlib.md5(stem.encode()).hexdigest()[:8], 16)


# Per-file extra rows that exercise specific block types / code paths.
# These rows MUST appear in the golden TPPs so the unit tests cover
# the bugs found during exhaustive validation.
EXTRA_ROWS: dict[str, list[int]] = {
    # row 749: TOLLVTOLLS2 has zone_field=20 → 0xC8 dense short-lo + big RLE
    "HWYSKMMD": [749],
    # rows 811, 1101: ddist uses type 0x40 (hi-byte-only sparse)
    "trnskmam_drv_com_wlk": [811, 1101],
}


def sample_rows(stem: str) -> sorted:
    rng = random.Random(seed_for_file(stem))
    extras = set(EXTRA_ROWS.get(stem, []))
    base = set(FIXED_ROWS) | extras
    candidates = [r for r in range(1, ZONES + 1) if r not in base]
    randoms = rng.sample(candidates, min(N_RANDOM, len(candidates)))
    return sorted(base | set(randoms))


# Representative files covering all block types:
#   Highway EA:  0x00, 0xC0, 0xC8(dense)
#   Highway AM:  0x00, 0x80, 0xC0, 0xC8(dense+sparse)
#   Transit:     0x00, 0x40, 0x80, 0xC0
#   NonMotorized: 0xC8, 0xE8(dense+sparse)
#   + one more highway period (PM) and transit combo for breadth

HIGHWAY_TABLES = [
    "TIMEDA",
    "DISTDA",
    "BTOLLDA",
    "TOLLTIMEDA",
    "TOLLDISTDA",
    "TOLLBTOLLDA",
    "TOLLVTOLLDA",
    "TIMES2",
    "DISTS2",
    "BTOLLS2",
    "TOLLTIMES2",
    "TOLLDISTS2",
    "TOLLBTOLLS2",
    "TOLLVTOLLS2",
    "TIMES3",
    "DISTS3",
    "BTOLLS3",
    "TOLLTIMES3",
    "TOLLDISTS3",
    "TOLLBTOLLS3",
    "TOLLVTOLLS3",
]

TRANSIT_TABLES = [
    "ivt",
    "iwait",
    "xwait",
    "wait",
    "wacc",
    "waux",
    "wegr",
    "dtime",
    "ddist",
    "fare",
    "boards",
    "ivtLOC",
    "ivtLRF",
    "ivtEXP",
    "ivtHVY",
    "ivtCOM",
    "ivtFerry",
    "ivtMUNILoc",
    "ivtMUNIMet",
    "distLOC",
    "distLRF",
    "distEXP",
    "distHVY",
    "distCOM",
    "distFerry",
    "firstMode",
    # Table 27 may or may not exist:
    "boards2",
]

NONMOT_TABLES = ["DISTWALK", "DISTBIKE", "DIST"]

FILES = [
    # (stem, input_name, table_list, n_tables_guaranteed)
    ("HWYSKMEA", "HWYSKMEA.tpp", HIGHWAY_TABLES, 21),
    ("HWYSKMAM", "HWYSKMAM.tpp", HIGHWAY_TABLES, 21),
    ("HWYSKMMD", "HWYSKMMD.tpp", HIGHWAY_TABLES, 21),  # exercises 0xC8 dense short-lo + big RLE
    ("HWYSKMPM", "HWYSKMPM.tpp", HIGHWAY_TABLES, 21),
    (
        "trnskmam_drv_com_wlk",
        "trnskmam_drv_com_wlk.tpp",
        TRANSIT_TABLES,
        26,
    ),  # exercises 0x40 hi-byte-only
    ("trnskmam_wlk_com_wlk", "trnskmam_wlk_com_wlk.tpp", TRANSIT_TABLES, 26),
    ("trnskmam_drv_hvy_wlk", "trnskmam_drv_hvy_wlk.tpp", TRANSIT_TABLES, 26),
    ("trnskmpm_wlk_loc_drv", "trnskmpm_wlk_loc_drv.tpp", TRANSIT_TABLES, 26),
    ("nonmotskm", "nonmotskm.tpp", NONMOT_TABLES, 3),
]


def _generate_matrix_block(stem, input_name, tables, n_tables):
    """Generate one RUN PGM=MATRIX block."""
    rows = sample_rows(stem)
    n = len(tables)

    # Build the IF condition for sampled rows
    row_checks = " || ".join(f"I == {r}" for r in rows)

    lines = []
    lines.append(f"; --- {stem} ({len(rows)} sampled rows) ---")
    lines.append("RUN PGM=MATRIX")
    lines.append(f'    FILEI MATI[1] = "{SKIMS_DIR}\\{input_name}"')
    lines.append(f'    FILEO MATO[1] = "{OUTPUT_DIR}\\{stem}.tpp",')

    # MO list
    mo_names = ", ".join(f'"{t}"' for t in tables[:n_tables])
    lines.append(f"        MO=1-{n_tables}, NAME={mo_names}")
    lines.append("")

    # Read tables
    for i, tbl in enumerate(tables[:n_tables], 1):
        lines.append(f"    MW[{i}] = MI.1.{tbl}")
    lines.append("")

    # Conditional: only copy sampled rows, zero everything else
    lines.append(f"    IF ({row_checks})")
    lines.append("      ; keep data as-is")
    lines.append("    ELSE")
    for i in range(1, n_tables + 1):
        lines.append(f"      MW[{i}] = 0")
    lines.append("    ENDIF")
    lines.append("")
    lines.append("ENDRUN")
    lines.append("")
    return "\n".join(lines)


def _generate_csv_dump_block(stem, tables, n_tables):
    """Generate a RUN PGM=MATRIX block that dumps a golden TPP to CSV."""
    lines = []
    lines.append(f"; --- dump {stem}.tpp → {stem}.csv ---")
    lines.append("RUN PGM=MATRIX")
    lines.append(f'    FILEI MATI[1] = "{OUTPUT_DIR}\\{stem}.tpp"')
    lines.append(f'    FILEO PRINTO[1] = "{OUTPUT_DIR}\\{stem}.csv"')
    lines.append("")

    # Read tables into MW
    for i, tbl in enumerate(tables[:n_tables], 1):
        lines.append(f"    MW[{i}] = MI.1.{tbl}")
    lines.append("")

    # Header row
    header = "I,J," + ",".join(tables[:n_tables])
    lines.append("    IF (I == 1)")
    lines.append(f'      PRINT LIST="{header}", PRINTO=1')
    lines.append("    ENDIF")
    lines.append("")

    # Sparse output: only print rows/cols where at least one value is nonzero
    checks = " || ".join(f"MW[{i}] != 0" for i in range(1, n_tables + 1))
    lines.append("    JLOOP")
    lines.append(f"      IF ({checks})")

    # Build PRINT LIST
    parts = ['        PRINT LIST=I(5), ",", J(5)']
    for i in range(1, n_tables + 1):
        parts.append(f'          ",", MW[{i}](15.6f)')
    parts.append("          PRINTO=1")
    lines.append(",\n".join(parts))

    lines.append("      ENDIF")
    lines.append("    ENDJLOOP")
    lines.append("")
    lines.append("ENDRUN")
    lines.append("")
    return "\n".join(lines)


def main():
    job_lines = []
    job_lines.append("; extract_golden_tpps.job")
    job_lines.append(";")
    job_lines.append("; Extract sampled rows from full TPP files to create small golden TPPs.")
    job_lines.append("; Row sampling matches cherry_pick_test_data.py exactly.")
    job_lines.append(";")
    job_lines.append(f"; Output: {OUTPUT_DIR}\\")
    job_lines.append(";")
    # Create output dir before any RUN PGM blocks
    job_lines.append(f'*if not exist "{OUTPUT_DIR}" mkdir "{OUTPUT_DIR}"')
    job_lines.append("")

    # Print sampled rows for reference
    for stem, _, _, _ in FILES:
        rows = sample_rows(stem)
        job_lines.append(f"; {stem}: rows {rows}")
    job_lines.append("")

    for stem, input_name, tables, n_tables in FILES:
        job_lines.append(_generate_matrix_block(stem, input_name, tables, n_tables))

    # Part 2: dump each golden TPP to CSV
    job_lines.append("; =======================================================================")
    job_lines.append("; PART 2: Dump golden TPPs to CSV (ground truth for Python reader tests)")
    job_lines.append("; =======================================================================")
    job_lines.append("")

    for stem, _, tables, n_tables in FILES:
        job_lines.append(_generate_csv_dump_block(stem, tables, n_tables))

    job_text = "\n".join(job_lines)

    out_path = Path(__file__).resolve().parent / "extract_golden_tpps.job"
    out_path.write_text(job_text, encoding="utf-8")
    print(f"Wrote {out_path} ({len(job_text)} bytes)")
    print("\nFiles to extract:")
    for stem, _, _, _ in FILES:
        rows = sample_rows(stem)
        print(f"  {stem:40s}  {len(rows)} rows: {rows}")


if __name__ == "__main__":
    main()
