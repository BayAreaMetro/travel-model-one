MTC_INPUT_PATHS = {
    "od_omx":     "data/interim/cube_io/mtc_truck_od_trips/tripstrk{tod}x.omx",
    "skims":      "data/interim/cube_io/mtc_skims/COM_HWYSKIM{tod}.omx",
    "land_use":   "data/external/mtc/2023_TM161_IPA_35/landuse/tazData.csv",
}

SW_INPUT_PATHS = {
    "od_omx":           "data/interim/cube_io/statewide_od_matrices/TRIPS_FFM_2020.omx",
    "skims":            "data/external/caltrans/Year2020/skims.h5",
    "taz_county":       "data/external/caltrans/Year2020/taz_MPO_region.csv",
    # TNL zone positions: 0-based integer indices into the 7000×7000 matrix
    "tln_indices": {
        2655: "PORT OF SAN FRANCISCO",
        2656: "PORT OF REDWOOD CITY",
        2658: "PORT OF OAKLAND",
        6987: "SFO AIRPORT",
        6988: "OAK AIRPORT",
    },
}

COUNTY_MAP = {
    1: "San Francisco",
    2: "San Mateo", 
    3: "Santa Clara",  
    4: "Alameda", 
    5: "Contra Costa",  
    6: "Solano", 
    7: "Napa", 
    8: "Sonoma",  
    9: "Marin", 
    }

COUNTIES = list(COUNTY_MAP.values())


SW_DIST_PAIRS = {
    "light_trucks": "dist_comp",
    "medium_trucks": "dist_comp",
    "heavy_trucks": "dist_comp"
    }

SW_TIME_PAIRS = {
    "light_trucks": "time_comp",
    "medium_trucks": "time_comp",
    "heavy_trucks": "time_comp"
}

SW_TRIP_DIST_CONFIG = {
    "sw_distance": {
        "plot_pairs": SW_DIST_PAIRS,
        "bins": 25,
        "filters": {
            "origin_county": COUNTIES,
            "destination_county": COUNTIES
        },
        "title": "Travel Distance Distribution - CSF2TDM",
        "x_label": "Distance (miles)"
    },
    "sw_time": {
        "plot_pairs": SW_TIME_PAIRS,
        "bins": 25,
        "filters": {
            "origin_county": COUNTIES,
            "destination_county": COUNTIES
        },
        "title": "Travel Time Distribution - CSF2TDM",
        "x_label": "Time (minutes)"
    },
        # TNLs
    "origin_2655_distance": {
        "plot_pairs": SW_DIST_PAIRS,
        "bins": 25,
        "filters": {"origin": [2655]},
        "title": "Travel Distance Distribution - CSF2TDM 2655: PORT OF SAN FRANCISCO",
        "x_label": "Distance (miles)"
    },
    "origin_2655_time": {
        "plot_pairs": SW_TIME_PAIRS,
        "bins": 25,
        "filters": {"origin": [2655]},
        "title": "Travel Time Distribution - CSF2TDM 2655: PORT OF SAN FRANCISCO",
        "x_label": "Time (minutes)"
    },
    "origin_2656_distance": {
        "plot_pairs": SW_DIST_PAIRS,
        "bins": 25,
        "filters": {"origin": [2656]},
        "title": "Travel Distance Distribution - CSF2TDM 2656: PORT OF REDWOOD CITY",
        "x_label": "Distance (miles)"
    },
    "origin_2656_time": {
        "plot_pairs": SW_TIME_PAIRS,
        "bins": 25,
        "filters": {"origin": [2656]},
        "title": "Travel Time Distribution - CSF2TDM 2656: PORT OF REDWOOD CITY",
        "x_label": "Time (minutes)"
    },
    "origin_2658_distance": {
        "plot_pairs": SW_DIST_PAIRS,
        "bins": 25,
        "filters": {"origin": [2658]},
        "title": "Travel Distance Distribution - CSF2TDM 2658: PORT OF OAKLAND",
        "x_label": "Distance (miles)"
    },
    "origin_2658_time": {
        "plot_pairs": SW_TIME_PAIRS,
        "bins": 25,
        "filters": {"origin": [2658]},
        "title": "Travel Time Distribution - CSF2TDM 2658: PORT OF OAKLAND",
        "x_label": "Time (minutes)"
    },
    "origin_6987_distance": {
        "plot_pairs": SW_DIST_PAIRS,
        "bins": 25,
        "filters": {"origin": [6987]},
        "title": "Travel Distance Distribution - CSF2TDM 6987: SFO AIRPORT",
        "x_label": "Distance (miles)"
    },
    "origin_6987_time": {
        "plot_pairs": SW_TIME_PAIRS,
        "bins": 25,
        "filters": {"origin": [6987]},
        "title": "Travel Time Distribution - CSF2TDM 6987: SFO AIRPORT",
        "x_label": "Time (minutes)"
    },
    "origin_6988_distance": {   
        "plot_pairs": SW_DIST_PAIRS,
        "bins": 25,
        "filters": {"origin": [6988]},
        "title": "Travel Distance Distribution - CSF2TDM 6988: OAK AIRPORT",
        "x_label": "Distance (miles)"
    },
    "origin_6988_time": {
        "plot_pairs": SW_TIME_PAIRS,
        "bins": 25,
        "filters": {"origin": [6988]},
        "title": "Travel Time Distribution - CSF2TDM 6988: OAK AIRPORT",
        "x_label": "Time (minutes)"
    }   
}

MTC_DIST_PAIRS =  {
        "very_small_trucks": "distance_comp_very_small",
        "small_trucks": "distance_comp_small",
        "medium_trucks": "distance_comp_medium",
        "large_trucks": "distance_comp_large"
}

MTC_TIME_PAIRS =  {
        "very_small_trucks": "time_comp_very_small",    
        "small_trucks": "time_comp_small",
        "medium_trucks": "time_comp_medium",
        "large_trucks": "time_comp_large"
}


MTC_TRIP_DIST_CONFIG = {
    "mtc_distance": {
        "plot_pairs": MTC_DIST_PAIRS,

        "bins": 25,
        "filters": {
            "origin_county": COUNTIES,
            "destination_county": COUNTIES
        },
        "title": "Travel Distance Distribution - MTC Region",
        "x_label": "Distance (miles)"
    },

    "mtc_time": {
        "plot_pairs": MTC_TIME_PAIRS,
        "bins": 25,
        "filters": {
            "origin_county": COUNTIES,
            "destination_county": COUNTIES
        },
        "title": "Travel Time Distribution - MTC Region",
        "x_label": "Time (minutes)"
    },

   # TNLs
    "origin_142_distance": {
        "plot_pairs": MTC_DIST_PAIRS,
        "bins": 25,
        "filters": {"origin": [142]},
        "title": "Travel Distance Distribution - TAZ 142: PORT OF SAN FRANCISCO",
        "x_label": "Distance (miles)"
    },

    "origin_142_time": {
        "plot_pairs": MTC_TIME_PAIRS,
        "bins": 25,
        "filters": {"origin": [142]},
        "title": "Travel Time Distribution - TAZ 142: PORT OF SAN FRANCISCO",
        "x_label": "Time (minutes)"
    },

    "origin_313_distance": {
        "plot_pairs": MTC_DIST_PAIRS,
        "bins": 25,
        "filters": {"origin": [313]},
        "title": "Travel Distance Distribution - TAZ 313: PORT OF REDWOOD CITY",
        "x_label": "Distance (miles)"
    },

    "origin_313_time": {
        "plot_pairs": MTC_TIME_PAIRS,
        "bins": 25,
        "filters": {"origin": [313]},
        "title": "Travel Time Distribution - TAZ 313: PORT OF REDWOOD CITY",
        "x_label": "Time (minutes)"
    },

    "origin_965_distance": {
        "plot_pairs": MTC_DIST_PAIRS,
        "bins": 25,
        "filters": {"origin": [965]},
        "title": "Travel Distance Distribution - TAZ 965: PORT OF OAKLAND",
        "x_label": "Distance (miles)"
    },

    "origin_965_time": {
        "plot_pairs": MTC_TIME_PAIRS,
        "bins": 25,
        "filters": {"origin": [965]},
        "title": "Travel Time Distribution - TAZ 965: PORT OF OAKLAND",
        "x_label": "Time (minutes)"
    },

    "origin_239_distance": {
        "plot_pairs": MTC_DIST_PAIRS,
        "bins": 25,
        "filters": {"origin": [239]},
        "title": "Travel Distance Distribution - TAZ 239: SFO AIRPORT",
        "x_label": "Distance (miles)"
    },

    "origin_239_time": {
        "plot_pairs": MTC_TIME_PAIRS,
        "bins": 25,
        "filters": {"origin": [239]},
        "title": "Travel Time Distribution - TAZ 239: SFO AIRPORT",
        "x_label": "Time (minutes)"
    },

    "origin_874_distance": {
        "plot_pairs": MTC_DIST_PAIRS,
        "bins": 25,
        "filters": {"origin": [874]},
        "title": "Travel Distance Distribution - TAZ 874: OAK AIRPORT",
        "x_label": "Distance (miles)"
    },

    "origin_874_time": {
        "plot_pairs": MTC_TIME_PAIRS,
        "bins": 25,
        "filters": {"origin": [874]},
        "title": "Travel Time Distribution - TAZ 874: OAK AIRPORT",
        "x_label": "Time (minutes)"
    }
}