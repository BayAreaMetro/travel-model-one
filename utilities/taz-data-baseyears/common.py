#
# This file exists so common mappings and lists do not need to be repeated across multiple files
#

BAY_AREA_COUNTY_FIPS = {
    "06001": "Alameda",
    "06013": "Contra Costa",
    "06041": "Marin",
    "06055": "Napa",
    "06075": "San Francisco",
    "06081": "San Mateo",
    "06085": "Santa Clara",
    "06095": "Solano",
    "06097": "Sonoma"
}

# from petrale\applications\travel_model_lu_inputs\2015\Employment\NAICS_to_EMPSIX.xlsx, abag-6 worksheet
# column names are from https://github.com/BayAreaMetro/modeling-website/wiki/TazData
NAICS2_EMPSIX = {
    'NAICS 11':     'AGREMPN',
    'NAICS 21':     'AGREMPN',
    'NAICS 22':     'MWTEMPN',
    'NAICS 23':     'OTHEMPN',
    'NAICS 31-33':  'MWTEMPN',
    'NAICS 42':     'MWTEMPN',
    'NAICS 44-45':  'RETEMPN',
    'NAICS 48-49':  'MWTEMPN',
    'NAICS 51':     'OTHEMPN',
    'NAICS 52':     'FPSEMPN',
    'NAICS 53':     'FPSEMPN',
    'NAICS 54':     'FPSEMPN',
    'NAICS 55':     'FPSEMPN',
    'NAICS 56':     'FPSEMPN',
    'NAICS 61':     'HEREMPN',
    'NAICS 62':     'HEREMPN',
    'NAICS 71':     'HEREMPN',
    'NAICS 72':     'HEREMPN',
    'NAICS 81':     'HEREMPN',
    'NAICS 92':     'OTHEMPN',
}