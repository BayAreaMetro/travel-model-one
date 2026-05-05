"""Hand-curated crosswalk between CTRAMP UEC row numbers and ActivitySim spec labels.

Each submodel maps asim_label → ctramp_row_number (int) or list of row numbers
when multiple CTRAMP rows collapse to a single ActivitySim row (many-to-one).
Rows that appear on only one side (unmapped) show up automatically via outer join.
"""

# fmt: off

# {submodel_name: {asim_label: ctramp_row_no | [ctramp_row_nos]}}
MAPPINGS: dict[str, dict[str, int | list[int]]] = {

    "Workplace Location": {
        "util_dist_0_1":                       18,
        "util_dist_1_2":                       19,
        "util_dist_2_5":                       20,
        "util_dist_5_15":                      21,
        "util_dist_15_up":                     22,
        "util_dist_0_5_high":                  32,
        "util_dist_15_up_high":                33,
        "util_mode_logsum":                    23,
        "util_size_variable":                  [24, 25, 26, 27],
        "util_no_attractions":                 [28, 29, 30, 31],
        "util_sample_of_corrections_factor":   17,
        "util_sf_to_sf":                       34,
        "util_sf_to_san_mateo":                35,
        "util_sf_to_santa_clara":              36,
        "util_san_mateo_to_santa_clara":       37,
        "util_san_mateo_to_alameda":           38,
        "util_santa_clara_to_sf":              39,
        "util_santa_clara_to_santa_clara":     40,
        "util_alameda_to_santa_clara":         41,
        "util_contra_costa_to_san_mateo":      42,
        "util_contra_costa_to_santa_clara":    43,
    },

    "School Location": {
        "util_sample_of_corrections_factor":   7,
        "util_dist_0_1":                       8,
        "util_dist_1_2":                       9,
        "util_dist_2_5":                       10,
        "util_dist_5_15":                      11,
        "util_dist_15_up":                     12,
        "util_mode_choice_logsum":             13,
        "util_size_variable":                  14,
        "util_no_attractions":                 15,
    },
}

# Explanatory notes for rows that appear on only one side or as many-to-one.
# {submodel: {label_or_"row_N": note_text}}
NOTES: dict[str, dict[str, str]] = {

    "Workplace Location": {
        # Many-to-one: CTRAMP has per-income-segment rows, ASim uses size_terms table
        "util_size_variable": (
            "CTRAMP rows 24-27 are per-income-segment size variables (low/med/high/veryhigh) "
            "with identical coeff=1. ActivitySim handles segmentation via "
            "destination_choice_size_terms.csv, so one spec row suffices."
        ),
        "util_no_attractions": (
            "CTRAMP rows 28-31 are per-income-segment no-attractions penalties "
            "(coeff=-999). ActivitySim applies the same penalty across segments "
            "via a single spec row; segmentation is in the size terms table."
        ),
        # ASim-only: no CTRAMP equivalent
        "local_dist": (
            "Intermediate variable that caches skims['DIST'] for reuse by "
            "downstream distance-band expressions. Not a utility term."
        ),
        "local_home_county": (
            "Intermediate variable that looks up the origin county_id for "
            "county-to-county constant expressions. Not a utility term."
        ),
        "util_utility_adjustment": (
            "ActivitySim shadow pricing mechanism — iteratively adjusts zone "
            "attractiveness to match aggregate targets. CTRAMP uses a different "
            "shadow pricing implementation outside the UEC."
        ),
    },

    "School Location": {
        "local_dist": (
            "Intermediate variable that caches skims['DIST'] for reuse by "
            "downstream distance-band expressions. Not a utility term."
        ),
        "util_utility_adjustment": (
            "ActivitySim shadow pricing mechanism — iteratively adjusts zone "
            "attractiveness to match aggregate targets. CTRAMP uses a different "
            "shadow pricing implementation outside the UEC."
        ),
    },
}

# fmt: on
