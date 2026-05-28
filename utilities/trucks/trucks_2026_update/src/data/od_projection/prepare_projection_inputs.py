from pathlib import Path

import openmatrix as omx

def prepare_inputs(data: dict, cfg):

    data["to_network_nodes"] = data["to_network_nodes"].set_crs(data["to_shapefile"].crs) #set CRS of the shapefile

    # Set CRS to NAD_1983_California_Teale_Albers. 
    # CSF2TDM Documentation. Page 3-4 Update of the coordindate system
    data.update({
        "from_network_nodes": data["from_network_nodes"].set_crs("EPSG:3310"), 
        "from_shapefile": data["from_shapefile"].set_crs("EPSG:3310").set_index(cfg["zones"]["from_zone_id"]).rename_axis("from_zone_id")})
    
    data.update({
        "to_shapefile": data["to_shapefile"].to_crs("EPSG:3310").set_index(cfg["zones"]["to_zone_id"]).rename_axis("to_zone_id"), 
        "to_network_nodes": data["to_network_nodes"].to_crs("EPSG:3310")})
    
    
    data["from_gate_nodes"] = georeference_sw_nodes(
        sw_shapefile = data["from_shapefile"], 
        sw_network_nodes = data["from_network_nodes"], 
        n_zones = cfg["zones"]["from_matrix_size"]
        )
    
    data["to_gate_nodes"] = georeference_tm16_nodes(
        tm16_network_nodes = data["to_network_nodes"], 
        external_zones = cfg["zones"]["to_gate_range"]
    )

    data["truck_trip_gen_tm16"] = estimate_truck_trip_gen_tm16(
        land_use = data["tm_land_use"]
        )
    
    out_path = cfg["output"]

    fpath = Path(out_path["omx_zone_and_gates"])
    fpath.parent.mkdir(parents=True, exist_ok=True)
    data["projected_zones_and_gates"] = omx.open_file(fpath,'w')

    fpath = Path(out_path["omx_only_zones"])
    fpath.parent.mkdir(parents=True, exist_ok=True)
    data["projected_zones_only"] = omx.open_file(fpath,'w') 

    fpath = Path(out_path["omx_only_gates"])
    fpath.parent.mkdir(parents=True, exist_ok=True)    
    data["projected_gates_only"] = omx.open_file(fpath, 'w')
    return data


def georeference_sw_nodes(sw_shapefile, sw_network_nodes, n_zones, crs = "EPSG:3310"):
    """
    The statewide model matrix has a shape of 7000 x 7000 but only 5285 non-consecutuve TAZ numerated. 
    From the shapefile we know the index of the actual zones, and the missing ones are special nodes
     in the network. We merge them with the network nodes to get their location. 
    """
    relevant_nodes = sw_network_nodes[sw_network_nodes.N.between(1, n_zones)]
    georef_nodes = relevant_nodes[~relevant_nodes.N.isin(sw_shapefile.index)]
    georef_nodes = georef_nodes.to_crs(crs)
    georef_nodes["from_zone_id"] = georef_nodes["N"]
    return georef_nodes.set_index("from_zone_id")[["geometry"]]


def georeference_tm16_nodes(tm16_network_nodes, external_zones, crs = "EPSG:3310"):
    mtc_gateways = tm16_network_nodes[tm16_network_nodes.N.between(external_zones[0], external_zones[1])]
    mtc_gateways["to_zone_id"] = mtc_gateways["N"]
    mtc_gateways = mtc_gateways.to_crs(crs)
    return mtc_gateways.set_index("to_zone_id")[["geometry"]]

def estimate_truck_trip_gen_tm16(land_use):
    """
    This scrip mimics the current TM-1.6 Truck Generation equations in TruckTripGeneration.job : 
    https://github.com/BayAreaMetro/travel-model-one/blob/2f9b0510f24dd430906e02e135e3a17ae06a63f9/model-files/scripts/nonres/TruckTripGeneration.job#L67-L95
    """
    # ------------------------------------
    # GENERATION MODELS
    # -------------------------------------
    df = land_use.copy()

    # non-garage-based, or linked trips - productions (very small updated with NAICS coefficients)
    df["linkedVerySmall_production"] = round(0.4 * (0.95409 * df["RETEMPN"] + 0.54333 * df["FPSEMPN"] + 0.50769 * df["HEREMPN"] + 
                                0.63558 * df["OTHEMPN"] + 1.10181 * df["AGREMPN"] + 0.81576 * df["MWTEMPN"] +
                                0.26565 * df["TOTHH"]))
    df["linkedSmall_production"] = round(0.0324 * df["TOTEMP"])
    df["linkedMedium_production"] = round(0.0039 * df["TOTEMP"])
    df["linkedLarge_production"] = round(0.0073 * df["TOTEMP"])

    # non-garage-based, or linked trips - attractions (equal productions)
    df["linkedVerySmall_attraction"] = df["linkedVerySmall_production"]
    df["linkedSmall_attraction"] = df["linkedSmall_production"]
    df["linkedMedium_attraction"] = df["linkedMedium_production"]
    df["linkedLarge_attraction"] = df["linkedLarge_production"]


    # garage-based - productions (updated NAICS coefficients)
    df["garageSmall_production"] = round(0.02146 * df["RETEMPN"] + 0.02424 * df["FPSEMPN"] + 0.01320 * df["HEREMPN"] +
                        0.04325 * df["OTHEMPN"] + 0.05021 * df["AGREMPN"] + 0.01960 * df["MWTEMPN"])
    df["garageMedium_production"] = round(0.00102 * df["RETEMPN"] + 0.00147 * df["FPSEMPN"] + 0.00025 * df["HEREMPN"] +
                        0.00331 * df["OTHEMPN"] + 0.00445 * df["AGREMPN"] + 0.00165 * df["MWTEMPN"])
    df["garageLarge_production"] = round(0.00183 * df["RETEMPN"] + 0.00482 * df["FPSEMPN"] + 0.00274 * df["HEREMPN"] +
                        0.00795 * df["OTHEMPN"] + 0.01125 * df["AGREMPN"] + 0.00486 * df["MWTEMPN"])
    # garage-based - attractions
    df["garageSmall_attraction"] = round(0.0234 * df["TOTEMP"])
    df["garageMedium_attraction"] = round(0.0046 * df["TOTEMP"])
    df["garageLarge_attraction"] = round(0.0136 * df["TOTEMP"])

    prod_cols = ['linkedSmall_production', 'linkedMedium_production', 'linkedLarge_production',
                'garageSmall_production', 'garageMedium_production', 'garageLarge_production']

    attrac_cols = ['linkedSmall_attraction',  'linkedMedium_attraction', 'linkedLarge_attraction',
                'garageSmall_attraction', 'garageMedium_attraction', 'garageLarge_attraction']

    # ------------------------------------
    # BALANCE ATTRACTIONS TO PRODUCTIONS
    # -------------------------------------
    # Added on 3/31/2026 - Results before that ignored balancing step 
    # 1. Calculate Grand Totals (p[n][0] and a[n][0] in CUBE terms)
    total_p1 = df["linkedVerySmall_production"].sum()
    total_a1 = df["linkedVerySmall_attraction"].sum()

    total_p2 = df["linkedSmall_production"].sum()
    total_a2 = df["linkedSmall_attraction"].sum()

    total_p3 = df["linkedMedium_production"].sum()
    total_a3 = df["linkedMedium_attraction"].sum()

    total_p4 = df["linkedLarge_production"].sum()
    total_a4 = df["linkedLarge_attraction"].sum()

    total_p5 = df["garageSmall_production"].sum()
    total_a5 = df["garageSmall_attraction"].sum()

    total_p6 = df["garageMedium_production"].sum()
    total_a6 = df["garageMedium_attraction"].sum()

    total_p7 = df["garageLarge_production"].sum()
    total_a7 = df["garageLarge_attraction"].sum()

    # 2. Apply Balancing Factors (a[n] = p[n][0] / a[n][0] * a[n])
    df["linkedVerySmall_attraction"] *= (total_p1 / total_a1) if total_a1 != 0 else 1.0
    df["linkedSmall_attraction"]     *= (total_p2 / total_a2) if total_a2 != 0 else 1.0
    df["linkedMedium_attraction"]    *= (total_p3 / total_a3) if total_a3 != 0 else 1.0
    df["linkedLarge_attraction"]     *= (total_p4 / total_a4) if total_a4 != 0 else 1.0

    df["garageSmall_attraction"]     *= (total_p5 / total_a5) if total_a5 != 0 else 1.0
    df["garageMedium_attraction"]    *= (total_p6 / total_a6) if total_a6 != 0 else 1.0
    df["garageLarge_attraction"]     *= (total_p7 / total_a7) if total_a7 != 0 else 1.0

    # ---------------------------------------------------------------
    # COMBINED LINK AND GARAGE-BASED TRIPS FOR EACH CLASS OF TRUCK
    # ---------------------------------------------------------------

    # Aggregating in CSTDM Truck Categories: Light, Medium1, Medium2, Heavy 
    # Production
    df["light_trucks_production"] = round(df[["linkedVerySmall_production"]].sum(axis = 1))
    df["medium1_trucks_production"] = round(df[["linkedSmall_production", "garageSmall_production"]].sum(axis = 1))
    df["medium2_trucks_production"] = round(df[["linkedMedium_production", "garageMedium_production"]].sum(axis = 1))
    df["heavy_trucks_production"] = round(df[["linkedLarge_production", "garageLarge_production"]].sum(axis = 1))
    df["all_trucks_production"] = round(df[prod_cols].sum(axis = 1)) # Does not include VerySmall Category 

    # Attraction
    df["light_trucks_attraction"] = round(df[["linkedVerySmall_attraction"]].sum(axis = 1))
    df["medium1_trucks_attraction"] = round(df[["linkedSmall_attraction", "garageSmall_attraction"]].sum(axis = 1))
    df["medium2_trucks_attraction"] = round(df[["linkedMedium_attraction", "garageMedium_attraction"]].sum(axis = 1))
    df["heavy_trucks_attraction"] = round(df[["linkedLarge_attraction", "garageLarge_attraction"]].sum(axis = 1))
    df["all_trucks_attraction"] = round(df[attrac_cols].sum(axis = 1)) # Does not include VerySmall Category 

    df["to_zone_id"] = df["ZONE"]
    return df.set_index("to_zone_id")
