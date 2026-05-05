"""Hand-curated crosswalk between CTRAMP UEC row numbers and ActivitySim spec labels.

Each submodel maps asim_label → ctramp_row_number.
Rows that appear on only one side (unmapped) show up automatically via outer join.
"""

# fmt: off

# {submodel_name: {asim_label: ctramp_row_no}}
MAPPINGS: dict[str, dict[str, int]] = {

    "Workplace Location": {
        "util_dist_0_1":                       18,
        "util_dist_1_2":                       19,
        "util_dist_2_5":                       20,
        "util_dist_5_15":                      21,
        "util_dist_15_up":                     22,
        "util_dist_0_5_high":                  32,
        "util_dist_15_up_high":                33,
        "util_mode_logsum":                    23,
        "util_size_variable":                  24,
        "util_no_attractions":                 28,
        "util_sample_of_corrections_factor":   17,
    },
}

# fmt: on
