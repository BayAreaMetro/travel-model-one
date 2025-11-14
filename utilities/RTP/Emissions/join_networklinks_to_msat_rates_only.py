USAGE = """
    Joins the output network csvs with 1)  the emission rates by county, model year; emission rates for pollutants other than PM2.5
    are also based on speed, which is joined to int(CSPD) in the network output.

    This file is separate from the Overburdened Communities Analysis. This is only for expediting calculations for total MSAT emissions.

"""

import argparse, os
import pandas as pd
import numpy as np

# Lookup table for counties
LOOKUP_COUNTY = pd.DataFrame({
    "county2": ["AL", "CC", "MA", "NA", "SF", "SM", "SC", "SL", "SN"],
    "county_census": ["001", "013", "041", "055", "075", "081", "085", "095", "097"],
    "county_name": ["Alameda", "Contra Costa", "Marin", "Napa", "San Francisco", "San Mateo", "Santa Clara", "Solano", "Sonoma"]
})

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description = USAGE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('rtp', type=str, choices=['RTP2021','RTP2025'], help='Specify RTP')
    my_args = parser.parse_args()


    if my_args.rtp == 'RTP2021':
        MODEL_DIRS = {
            # "IP_2015": "M:/Application/Model One/RTP2021/IncrementalProgress/2015_TM152_IPA_17",
            "NP_2050": "M:/Application/Model One/RTP2021/Blueprint/2050_TM152_FBP_NoProject_24",
            # "FBP_2050": "M:/Application/Model One/RTP2021/Blueprint/2050_TM152_FBP_PlusCrossing_24",
            "FBP_Amd1_2050": "M:/Application/Model One/RTP2021/Blueprint/2050_TM152_FBP_PlusCrossing_24_Amd1",
            # "Alt1_2050": "M:/Application/Model One/RTP2021/Blueprint/2050_TM152_EIR_Alt1_06",
            # "Alt2_2050": "M:/Application/Model One/RTP2021/Blueprint/2050_TM152_EIR_Alt2_05"
        }
    elif my_args.rtp == 'RTP2025':
        MODEL_DIRS = {
            "IP_2023": "M:/Application/Model One/RTP2025/IncrementalProgress/2023_TM161_IPA_35",
            "NP_2050": "M:/Application/Model One/RTP2025/Blueprint/2050_TM161_FBP_NoProject_16",
            "FBP_2050": "M:/Application/Model One/RTP2025/Blueprint/2050_TM161_FBP_Plan_16",
            # "Alt1_2050": "M:/Application/Model One/RTP2025/Blueprint/2050_TM152_EIR_Alt1_06",
            # "Alt2_2050": "M:/Application/Model One/RTP2025/Blueprint/2050_TM152_EIR_Alt2_05"
        }
    if my_args.rtp == 'RTP2021':
        NETWORK_DIRS = {
            # "IP_2015": "M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_62/net_2015_Baseline/shapefile",
            "NP_2050": "M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_62/net_2050_Baseline/shapefile",
            # "FBP_2050": "M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_64/net_2050_Blueprint/shapefile",
            "FBP_Amd1_2050": "M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_64_Amd1/net_2050_Blueprint/shapefile",
            # "Alt1_2050": "M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_64/net_2050_Alt1/shapefile",
            # "Alt2_2050": "M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_64/net_2050_Alt2/shapefile"
        }
    elif my_args.rtp == 'RTP2025':
        NETWORK_DIRS = {
            "IP_2023": "M:/Application/Model One/RTP2025/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_v31/net_2023_Baseline/shapefiles",
            "NP_2050": "M:/Application/Model One/RTP2025/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_v31/net_2050_Baseline/shapefile",
            "FBP_2050": "M:/Application/Model One/RTP2025/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_v31/net_2050_Blueprint/shapefiles",
            # "Alt1_2050": "M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_64/net_2050_Alt1/shapefile",
            # "Alt2_2050": "M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_64/net_2050_Alt2/shapefile"
        }

    # Set base directory
    if my_args.rtp == 'RTP2021':
        if os.getenv("USERNAME") == "lzorn":
            BASE_DIR = "E:/Box/CARE Communities/CARE-Data-PBA50"
        else:
            BASE_DIR = "M:/Application/PBA50Plus_Data_Processing/OverburdenedCommunities_analysis/PBA50_reproduce"
        EMISSION_RATES_DIR = os.path.join(BASE_DIR, "PBA50_COC_ER_Lookups")
    elif my_args.rtp == 'RTP2025':
        BASE_DIR = "M:/Application/PBA50Plus_Data_Processing/OverburdenedCommunities_analysis/PBA50plus"
        EMISSION_RATES_DIR = os.path.join(BASE_DIR, "EmissionRates_Lookups").replace("\\","/")
    
    # Name of the analysis: "CARE" in RTP2021 and "OverBurdened" in RTP2025
    if my_args.rtp == 'RTP2021':
        analysis_name = "CARE"
    elif my_args.rtp == 'RTP2025':
        analysis_name = "OverBurdened"

    # Index and special columns
    index_cols = ["a", "b"]
    special_cols = ["distance", "lanes", "gl", "ft", "at", "tollclass", "ffs"]

    # Initialize emissions rates
    emissions_rates = {}

    # Process network files
    for network in list(NETWORK_DIRS):
        model_dir = os.path.basename(MODEL_DIRS[network])
        model_year = model_dir[:4]
        print(f"Processing {network} for year {model_year}: {model_dir}")

        network_file = os.path.join(MODEL_DIRS[network], "OUTPUT", "avgload5period_vehclasses.csv")
        print(network_file)
        network_df = pd.read_csv(network_file)
       
        # get countyName including "external"
        GL_conditions = [
            (network_df['gl'] == 1),
            (network_df['gl'] == 2),
            (network_df['gl'] == 3),
            (network_df['gl'] == 4),
            (network_df['gl'] == 5),
            (network_df['gl'] == 6),
            (network_df['gl'] == 7),
            (network_df['gl'] == 8),
            (network_df['gl'] == 9),
            (network_df['gl'] == 10)]
        CountyName_choices = ["San Francisco", "San Mateo", "Santa Clara", "Alameda", "Contra Costa", "Solano", "Napa", "Sonoma", "Marin", "external"]
        network_df['countyName'] = np.select(GL_conditions, CountyName_choices , default='null')
        if 'countyName' not in special_cols:
            special_cols.append("countyName")


        print(f"Read {len(network_df)} rows from {network_file}")

        # Keep subset of columns
        network_df = network_df[index_cols + special_cols + 
                                [col for col in network_df.columns if col.startswith("cspd")] + 
                                [col for col in network_df.columns if col.startswith("vol") and col.endswith("tot")]]
        
        print(f"network_long_crosswalk_df has {list(network_df)} columns")

        # network_df=network_df.drop(columns=['gl'])
        print('network_df.head()')
        print(f"network_long_crosswalk_df has {list(network_df)} columns")
        print(network_df.head())

        # Pivot time periods for cspd
        cspd_df = network_df[index_cols + [col for col in network_df.columns if col.startswith("cspd")]]
        cspd_tp_df = cspd_df.melt(id_vars=index_cols, var_name="time_period", value_name="cspd")
        cspd_tp_df['time_period'] = cspd_tp_df['time_period'].apply(lambda x: x.replace("cspd", ""))
        cspd_tp_df["cspd_int"] = cspd_tp_df["cspd"].apply(np.floor).astype(int)
        print(cspd_tp_df.head())

        # Pivot time periods for voltot
        vol_df = network_df[index_cols + [col for col in network_df.columns if col.startswith("vol")]]
        vol_tp_df = vol_df.melt(id_vars=index_cols, var_name="time_period", value_name="voltot")
        vol_tp_df['time_period'] = vol_tp_df['time_period'].apply(lambda x: x.replace("vol", ""))
        vol_tp_df['time_period'] = vol_tp_df['time_period'].apply(lambda x: x.replace("_tot", ""))
        print(vol_tp_df.head())
        assert len(vol_tp_df) == len(cspd_tp_df)

        # Combine dataframes
        network_long_df = network_df[index_cols + special_cols].merge(cspd_tp_df, on=index_cols, how="inner")
        network_long_df = network_long_df.merge(vol_tp_df, on=index_cols + ["time_period"], how="left")
        network_long_df["vmttot"] = network_long_df["voltot"] * network_long_df["distance"]
        assert len(network_long_df) == len(cspd_tp_df)
        print(f"network_long_df has {list(network_long_df)} columns")
  
        # Filter out dummy links
        network_long_df = network_long_df[network_long_df["ft"] != 6]
        print(f"network_long_df has {len(network_long_df)} rows")
        print(f"network_long_df has {list(network_long_df)} columns")
        print(network_long_df.head())

        # Read exhaust-based emissions
        if f"AL-{model_year}" not in emissions_rates:
            emissions_file = os.path.join(EMISSION_RATES_DIR, f"Year {model_year} MSAT Emission Rates with E2025 (PBA2050+).xlsx").replace("\\","/")
            for _, row in LOOKUP_COUNTY.iterrows():
                county2 = row["county2"]
                sheet_name = f"{county2}-{model_year}.csv"
                emissions_df = pd.read_excel(emissions_file, sheet_name=sheet_name)
                emissions_df.columns = emissions_df.columns.str.replace("-", "_").str.replace(".", "_")
                emissions_rates[f"{county2}-{model_year}"] = emissions_df

        # Read non-exhaust-based emission rates
        non_exhaust_key = f"non-exhaust-{model_year}"
        if non_exhaust_key not in emissions_rates:
            emissions_file = os.path.join(EMISSION_RATES_DIR, "PM2.5 Non-Exhaust ERs (w E2025).xlsx")
            emissions_df = pd.read_excel(emissions_file, sheet_name=model_year, skiprows=1)
            emissions_df.columns = emissions_df.columns.str.replace(" ", "_")
            emissions_rates[non_exhaust_key] = emissions_df
            print(emissions_df)
 

        # Process emissions for each county
        network_long_emissions_df = pd.DataFrame()

        for _, row in LOOKUP_COUNTY.iterrows():
            county2 = row["county2"]
            county_census = row["county_census"]
            county_name = row["county_name"]

            index_name = f"{county2}-{model_year}"
            non_exhaust_rates = emissions_rates[non_exhaust_key].query(f"County == '{county_name}'")
            print(non_exhaust_rates)

            # Filter for this county
            this_co_df = network_long_df.query(f"countyName == '{county_name}'")

            # Join based on congested speed int
            print(county_name)
            print('this_co_df')
            print(this_co_df.head())
            print(list(this_co_df))
            print('emissions_rates[index_name]')
            print(emissions_rates[index_name].head())
            print(list(emissions_rates))
      
            this_co_df = this_co_df.merge(emissions_rates[index_name], left_on="cspd_int", right_on="Speed", how="left")
            this_co_df = this_co_df.merge(emissions_df, how="right",left_on="countyName",right_on="County")

            print(this_co_df.head())
            print(list(network_long_emissions_df))
            network_long_emissions_df = pd.concat([network_long_emissions_df, this_co_df])


        # Write the result
        if my_args.rtp == 'RTP2021':
            output_fullpath = os.path.join(BASE_DIR, "links_CARE_EMFAC2021_FEIR", f"links_CARE_{model_dir}.csv")
        elif my_args.rtp == 'RTP2025':
            output_fullpath = os.path.join(BASE_DIR, "total_MSAT_emissions", f"links_total_MSATs_v3_{model_dir}.csv")
        
        network_long_emissions_df.to_csv(output_fullpath, float_format='%.7f', index=False)

        print(f"Wrote {len(network_long_emissions_df)} rows and {len(list(network_long_emissions_df))} columns to {output_fullpath}")