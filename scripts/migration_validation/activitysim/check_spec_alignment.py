"""Sweep the mode-choice specs for label/column mismatches: rows whose Label
implies specific modes but whose coefficient cells sit in other mode columns.

This is the check that would have caught the shifted transit-hesitance rows
(coefficients landing on DRIVE_HVY/DRIVE_COM/TAXI instead of
DRIVE_EXP/DRIVE_HVY/DRIVE_COM). Known intentional cross-mode rows (escort
DA bar, trip-level tour_mode_ASC rows) are expected findings — review, don't
blindly fail.
"""
import re
from pathlib import Path

import pandas as pd

_CONFIGS = Path(__file__).resolve().parents[3] / "default-configs" / "activity" / "configs"
FILES = [
    _CONFIGS / "tour_mode_choice.csv",
    _CONFIGS / "trip_mode_choice.csv",
]

# label keyword -> set of allowed mode columns
HINTS = [
    (r"DRIVEALONEFREE|Drive_alone(?!.*toll)", {"DRIVEALONEFREE"}),
    (r"DRIVEALONEPAY", {"DRIVEALONEPAY"}),
    (r"SHARED2FREE", {"SHARED2FREE"}),
    (r"SHARED2PAY", {"SHARED2PAY"}),
    (r"SHARED3FREE", {"SHARED3FREE"}),
    (r"SHARED3PAY", {"SHARED3PAY"}),
    (r"WALK_LOC", {"WALK_LOC"}),
    (r"WALK_LRF", {"WALK_LRF"}),
    (r"WALK_EXP", {"WALK_EXP"}),
    (r"WALK_HVY", {"WALK_HVY"}),
    (r"WALK_COM", {"WALK_COM"}),
    (r"DRIVE_LOC", {"DRIVE_LOC"}),
    (r"DRIVE_LRF", {"DRIVE_LRF"}),
    (r"DRIVE_EXP", {"DRIVE_EXP"}),
    (r"DRIVE_HVY", {"DRIVE_HVY"}),
    (r"DRIVE_COM", {"DRIVE_COM"}),
    (r"(?<!joint_)Taxi(?!.*TNC)", {"TAXI"}),
    (r"TNC_Single|tnc_single", {"TNC_SINGLE"}),
    (r"TNC_Shared|tnc_shared", {"TNC_SHARED"}),
    (r"local_bus", {"WALK_LOC", "DRIVE_LOC"}),
    (r"express_bus", {"WALK_EXP", "DRIVE_EXP"}),
    (r"heavy_rail|Heavy_Rail", {"WALK_HVY", "DRIVE_HVY"}),
    (r"commuter_rail|Commuter_Rail", {"WALK_COM", "DRIVE_COM"}),
    (r"walk_lrt|walk_to_light_rail|Walk_to_Light_Rail|walk_ferry|walk_to_ferry|Walk_to_Ferry", {"WALK_LRF"}),
    (r"drive_lrt|drive_to_light_rail|Drive_to_Light_Rail|drive_ferry|drive_to_ferry|Drive_to_Ferry", {"DRIVE_LRF"}),
    (r"Walk_to_Transit", {"WALK_LOC", "WALK_LRF", "WALK_EXP", "WALK_HVY", "WALK_COM"}),
    (r"Drive_to_Transit", {"DRIVE_LOC", "DRIVE_LRF", "DRIVE_EXP", "DRIVE_HVY", "DRIVE_COM"}),
]

for path in FILES:
    spec = pd.read_csv(path)
    mode_cols = [c for c in spec.columns if c not in ("Label", "Description", "Expression")]
    print("===", path.name)
    flagged = 0
    for _, row in spec.iterrows():
        label = str(row["Label"])
        allowed: set[str] | None = None
        for pat, modes in HINTS:
            if re.search(pat, label, flags=re.IGNORECASE if pat.islower() else 0):
                allowed = modes
                break
        if allowed is None:
            continue
        cells = {c for c in mode_cols if pd.notna(row[c])}
        stray = cells - allowed
        if stray:
            flagged += 1
            print(f"  MISMATCH {label}: allowed {sorted(allowed)}, stray {sorted(stray)}")
    if not flagged:
        print("  clean")
