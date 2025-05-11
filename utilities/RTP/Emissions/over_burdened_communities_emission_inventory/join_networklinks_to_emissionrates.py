USAGE = """
    Joins the output network csvs with 1) crosswalks of link-CARE Communities (RTP2021/PBA50) and link-Overburdened Communities (RTP2025/PBA50+),
    and 2) the emission rates by county, model year, and CARE/non-CARE or Overburdened/non-Overburdened; emission rates for pollutants other than PM2.5
    are also based on speed, which is joined to int(CSPD) in the network output.

    PlanBayArea2050 / RTP2021 Asana Task: https://app.asana.com/0/316552326098022/1200007791721297/f
    PlanBayArea2050 / RTP2021 Amd1 Asana Task: https://app.asana.com/0/1201730518396783/1208059626391587/f
    PlanBayArea2050+ / RTP2025 Asana Task: https://app.asana.com/1/11860278793487/project/1159042832247728/task/1209490522594295?focus=true

"""

import argparse, os, logging, datetime
import pandas as pd
import numpy as np

####################################################################################
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

    # Set base directory
    if my_args.rtp == 'RTP2021':
        if os.getenv("USERNAME") == "lzorn":
            BASE_DIR = "E:/Box/CARE Communities/CARE-Data-PBA50"
        else:
            BASE_DIR = "M:/Application/PBA50Plus_Data_Processing/OverburdenedCommunities_analysis/PBA50_reproduce"
        EMISSION_RATES_DIR = os.path.join(BASE_DIR, "PBA50_COC_ER_Lookups")
        LINK_OUTPUT_DIR = os.path.join(BASE_DIR, "links_CARE_EMFAC2021_FEIR")
    elif my_args.rtp == 'RTP2025':
        BASE_DIR = "M:/Application/PBA50Plus_Data_Processing/OverburdenedCommunities_analysis/PBA50plus"
        EMISSION_RATES_DIR = os.path.join(BASE_DIR, "EmissionRates_Lookups")
        LINK_OUTPUT_DIR = os.path.join(BASE_DIR, "links_OverBurdened")
    
    ######################################################################
    # Set up logging
    LOG_FILE = os.path.join(LINK_OUTPUT_DIR,"join_networklinks_to_emissionrates_{}_{}.log")
    # create logger
    LOGGER = logging.getLogger(__name__)
    LOGGER.setLevel('INFO')
    # console handler
    ch = logging.StreamHandler()
    ch.setLevel('INFO')
    ch.setFormatter(logging.Formatter('%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    LOGGER.addHandler(ch)
    # file handlers
    fh = logging.FileHandler(LOG_FILE.format(my_args.rtp, datetime.date.today()), mode='w')
    fh.setLevel('INFO')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    LOGGER.addHandler(fh)

    if my_args.rtp == 'RTP2021':
        MODEL_DIRS = {
            # "IP_2015": "M:/Application/Model One/RTP2021/IncrementalProgress/2015_TM152_IPA_17",
            "NP_2050": "M:/Application/Model One/RTP2021/Blueprint/2050_TM152_FBP_NoProject_24",
            # "FBP_2050": "M:/Application/Model One/RTP2021/Blueprint/2050_TM152_FBP_PlusCrossing_24",
            "FBP_Amd1_2050": "M:/Application/Model One/RTP2021/Blueprint/2050_TM152_FBP_PlusCrossing_24_Amd1",
            # "Alt1_2050": "M:/Application/Model One/RTP2021/Blueprint/2050_TM152_EIR_Alt1_06",
            # "Alt2_2050": "M:/Application/Model One/RTP2021/Blueprint/2050_TM152_EIR_Alt2_05"
        }
        NETWORK_DIRS = {
            "NP_2050": "M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_62/net_2050_Baseline/shapefile",
            # "FBP_2050": "M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_64/net_2050_Blueprint/shapefile",
            "FBP_Amd1_2050": "M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_64_Amd1/net_2050_Blueprint/shapefile",
            # "Alt1_2050": "M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_64/net_2050_Alt1/shapefile",
            # "Alt2_2050": "M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_64/net_2050_Alt2/shapefile"
        }
    elif my_args.rtp == 'RTP2025':
        MODEL_DIRS = {
            "IP_2023": "M:/Application/Model One/RTP2025/IncrementalProgress/2023_TM161_IPA_35",
            "NP_2050": "M:/Application/Model One/RTP2025/Blueprint/2050_TM161_FBP_NoProject_16",
            "FBP_2050": "M:/Application/Model One/RTP2025/Blueprint/2050_TM161_FBP_Plan_16",
            # "Alt1_2050": "M:/Application/Model One/RTP2025/Blueprint/2050_TM152_EIR_Alt1_06",
            # "Alt2_2050": "M:/Application/Model One/RTP2025/Blueprint/2050_TM152_EIR_Alt2_05"
        }
        NETWORK_DIRS = {
            "IP_2023": "M:/Application/Model One/RTP2025/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_v35/net_2023_Baseline/shapefiles",
            "NP_2050": "M:/Application/Model One/RTP2025/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_v35/net_2050_Baseline/shapefiles",
            "FBP_2050": "M:/Application/Model One/RTP2025/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_v35/net_2050_Blueprint/shapefiles",
            # "Alt1_2050": "M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_64/net_2050_Alt1/shapefile",
            # "Alt2_2050": "M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_64/net_2050_Alt2/shapefile"
        }

    # Name of the analysis: "CARE" in RTP2021 and "OverBurdened" in RTP2025
    if my_args.rtp == 'RTP2021':
        analysis_name = "CARE"
        shp_id = "COUNTYCARE"
        link_tagging_col = "linkCC_share"

        emission_rates_file_PM25 = 'PM2.5 Non-Exhaust ERs (w E2021 & Mar 2021 road dust update).xlsx'
        emission_rates_file_MSAT = 'MSAT Emission Rates with E2021 (PBA2050).xlsx'
        emission_rates_PM25_area_col = "C_"
        emission_rates_PM25_nonarea_col = "NC_"
        emission_rates_MSAT_area_col = "C_EO_"
        emission_rates_MSAT_nonarea_col = "NC_EO_"
    elif my_args.rtp == 'RTP2025':
        analysis_name = "Overburdened"
        shp_id = "COUNTY_OBC"
        link_tagging_col = "linkOBC_share"

        emission_rates_file_PM25 = 'PM2.5 Non-Exhaust ERs (w E2025).xlsx'
        emission_rates_file_MSAT = 'MSAT Emission Rates with E2025 (PBA2050+).xlsx'
        # emission_rates_PM25_area_col = ""
        # emission_rates_PM25_nonarea_col = ""
        # emission_rates_MSAT_area_col = ""
        # emission_rates_MSAT_nonarea_col = ""

    # Index and special columns
    index_cols = ["a", "b"]
    special_cols = ["distance", "lanes", "gl", "ft", "at", "tollclass", "ffs"]

    # Initialize emissions rates
    emissions_rates = {}

    # Process network files
    for network in list(NETWORK_DIRS):
        model_dir = os.path.basename(MODEL_DIRS[network])
        model_year = model_dir[:4]
        LOGGER.info(f"Processing {network} for year {model_year}: {model_dir}")

        network_file = os.path.join(MODEL_DIRS[network], "OUTPUT", "avgload5period_vehclasses.csv")
        LOGGER.info(network_file)
        network_df = pd.read_csv(network_file)
        LOGGER.info(f"Read {len(network_df)} rows from {network_file}")

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

        # Keep subset of columns
        network_df = network_df[index_cols + special_cols + 
                                [col for col in network_df.columns if col.startswith("cspd")] + 
                                [col for col in network_df.columns if col.startswith("vol") and col.endswith("tot")]]


        # Pivot time periods for cspd
        cspd_df = network_df[index_cols + [col for col in network_df.columns if col.startswith("cspd")]]
        cspd_tp_df = cspd_df.melt(id_vars=index_cols, var_name="time_period", value_name="cspd")
        cspd_tp_df['time_period'] = cspd_tp_df['time_period'].apply(lambda x: x.replace("cspd", ""))
        cspd_tp_df["cspd_int"] = cspd_tp_df["cspd"].apply(np.floor).astype(int)

        # Pivot time periods for voltot
        vol_df = network_df[index_cols + [col for col in network_df.columns if col.startswith("vol")]]
        vol_tp_df = vol_df.melt(id_vars=index_cols, var_name="time_period", value_name="voltot")
        vol_tp_df['time_period'] = vol_tp_df['time_period'].apply(lambda x: x.replace("vol", ""))
        vol_tp_df['time_period'] = vol_tp_df['time_period'].apply(lambda x: x.replace("_tot", ""))
        assert len(vol_tp_df) == len(cspd_tp_df)

        # Combine dataframes
        network_long_df = network_df[index_cols + special_cols].merge(cspd_tp_df, on=index_cols, how="outer")
        network_long_df = network_long_df.merge(vol_tp_df, on=index_cols + ["time_period"], how="left")
        network_long_df["vmttot"] = network_long_df["voltot"] * network_long_df["distance"]
        assert len(network_long_df) == len(cspd_tp_df)

        # Read CARE/Overburdened mapping
        link_crosswalk_file = os.path.join(NETWORK_DIRS[network], f"link_to_COUNTY_{analysis_name}.csv")
        link_crosswalk = pd.read_csv(link_crosswalk_file)
        LOGGER.info(f"Read {len(link_crosswalk)} lines from {link_crosswalk}; head:")
        LOGGER.info(link_crosswalk.head())

        # Combine with network_long
        network_long_crosswalk_df = network_long_df.merge(
            link_crosswalk[["A", "B", shp_id, link_tagging_col]].rename(columns={"A": "a", "B": "b"}),
            on=["a", "b"], how="left"
        )
        network_long_crosswalk_df["county_census"] = network_long_crosswalk_df[shp_id].str[:3]
        network_long_crosswalk_df[analysis_name] = network_long_crosswalk_df[shp_id].str.len() > 3

        # Filter out dummy links
        network_long_crosswalk_df = network_long_crosswalk_df[network_long_crosswalk_df["ft"] != 6]
        LOGGER.info(f"network_long_crosswalk_df has {len(network_long_crosswalk_df)} rows")

        # Read exhaust-based emissions
        if f"AL-{model_year}" not in emissions_rates:
            emissions_file = os.path.join(EMISSION_RATES_DIR, f"Year {model_year} {emission_rates_file_MSAT}")
            for _, row in LOOKUP_COUNTY.iterrows():
                county2 = row["county2"]
                sheet_name = f"{county2}-{model_year}.csv"
                emissions_df = pd.read_excel(emissions_file, sheet_name=sheet_name)
                emissions_df.columns = emissions_df.columns.str.replace("-", "_").str.replace(".", "_")
                emissions_rates[f"{county2}-{model_year}"] = emissions_df

        # Read non-exhaust-based emission rates
        non_exhaust_key = f"non-exhaust-{model_year}"
        if non_exhaust_key not in emissions_rates:
            emissions_file = os.path.join(EMISSION_RATES_DIR, emission_rates_file_PM25)
            emissions_df = pd.read_excel(emissions_file, sheet_name=model_year, skiprows=1)
            emissions_df.columns = emissions_df.columns.str.replace(" ", "_")
            emissions_rates[non_exhaust_key] = emissions_df

        # Process emissions for each county
        network_long_emissions_df = pd.DataFrame()

        for _, row in LOOKUP_COUNTY.iterrows():
            county2 = row["county2"]
            county_census = row["county_census"]
            county_name = row["county_name"]

            index_name = f"{county2}-{model_year}"
            non_exhaust_rates = emissions_rates[non_exhaust_key].query(f"County == '{county_name}'")

            # Filter for this county
            this_co_df = network_long_crosswalk_df.query(f"county_census == '{county_census}'")

            # Join based on congested speed int
            LOGGER.info(county_name)
            LOGGER.info('this_co_df')
            LOGGER.info(this_co_df.head())
            LOGGER.info(list(this_co_df))
            LOGGER.info('emissions_rates[index_name]')
            LOGGER.info(emissions_rates[index_name].head())
            LOGGER.info(list(emissions_rates))
            this_co_df = this_co_df.merge(emissions_rates[index_name], left_on="cspd_int", right_on="Speed", how="left")
            LOGGER.info('this_co_df after merge')
            LOGGER
            LOGGER.info(this_co_df.head())

            if my_args.rtp == 'RTP2021':            
                this_co_df = this_co_df.assign(
                    PM2_5=np.where(this_co_df[analysis_name],
                                    this_co_df[emission_rates_MSAT_area_col+"PM2_5"],
                                    this_co_df[emission_rates_MSAT_nonarea_col+"PM2_5"]),
                    Benzene=np.where(this_co_df[analysis_name],
                                        this_co_df[emission_rates_MSAT_area_col+"Benzene"],
                                        this_co_df[emission_rates_MSAT_nonarea_col+"Benzene"]),
                    Butadiene=np.where(this_co_df[analysis_name],
                                        this_co_df[emission_rates_MSAT_area_col+"Butadiene"],
                                        this_co_df[emission_rates_MSAT_nonarea_col+"Butadiene"]),
                    DieselPM=np.where(this_co_df[analysis_name],
                                        this_co_df[emission_rates_MSAT_area_col+"DieselPM"],
                                        this_co_df[emission_rates_MSAT_nonarea_col+"DieselPM"]),
                    Tire_Wear=np.where(this_co_df[analysis_name],
                                    non_exhaust_rates[emission_rates_PM25_area_col+"Tire_Wear"].values[0],
                                    non_exhaust_rates[emission_rates_PM25_nonarea_col+"Tire_Wear"].values[0]),
                    Brake_Wear=np.where(this_co_df[analysis_name],
                                        non_exhaust_rates[emission_rates_PM25_area_col+"Brake_Wear"].values[0],
                                        non_exhaust_rates[emission_rates_PM25_nonarea_col+"Brake_Wear"].values[0]),
                    Entrained_Road_Dust=np.where(this_co_df[analysis_name],
                        non_exhaust_rates[emission_rates_PM25_area_col+"Entrained_Road_Dust"].values[0],
                        non_exhaust_rates[emission_rates_PM25_nonarea_col+"Entrained_Road_Dust"].values[0])
                )

                cols_to_drop = [emission_rates_MSAT_area_col+ i for i in ["PM2_5", "Benzene", "Butadiene", "DieselPM"]] + \
                                [emission_rates_MSAT_nonarea_col+ i for i in ["PM2_5", "Benzene", "Butadiene", "DieselPM"]]
                LOGGER.info(cols_to_drop)    
                this_co_df = this_co_df.drop(columns= cols_to_drop)

            elif my_args.rtp == 'RTP2025':
                this_co_df = this_co_df.assign(
                    Tire_Wear=np.where(this_co_df[analysis_name],
                                    non_exhaust_rates["Tire_Wear"].values[0],
                                    non_exhaust_rates["Tire_Wear"].values[0]),
                    Brake_Wear=np.where(this_co_df[analysis_name],
                                    non_exhaust_rates["Brake_Wear"].values[0],
                                    non_exhaust_rates["Brake_Wear"].values[0])
                )

            this_co_df = this_co_df.drop(columns= ['Speed'])

            LOGGER.info('this_co_df after assign')
            LOGGER.info(this_co_df.head())
            network_long_emissions_df = pd.concat([network_long_emissions_df, this_co_df])

        LOGGER.info(list(network_long_emissions_df))
        LOGGER.info(network_long_emissions_df)
        # Write the result
        if my_args.rtp == 'RTP2021':
            output_fullpath = os.path.join(LINK_OUTPUT_DIR, f"links_CARE_{model_dir}_python.csv")
        elif my_args.rtp == 'RTP2025':
            output_fullpath = os.path.join(LINK_OUTPUT_DIR, f"links_OverBurdened_{model_dir}.csv")
        
        network_long_emissions_df.to_csv(output_fullpath, float_format='%.7f', index=False)
        LOGGER.info(f"Wrote {len(network_long_emissions_df)} rows and {len(list(network_long_emissions_df))} columns to {output_fullpath}")
