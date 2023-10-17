import pandas as pd
import os

# Define a function to process each file
def process_csv(file_path):
    # Read the CSV file
    df = pd.read_csv(file_path)
    
    # Extract the required columns
    df_processed = df.iloc[:, [0, 1, 12]]
    df_processed.columns = ['orig_taz', 'dest_taz', 'fare']

    # Define list of origins and destinations of interest
    O = [410,972,146,478,820,767,558,607,234,16,742,1178,81,296,355,315,677,1145,1098,1176,1083,189,991,700,1421,1448,1270,1246,1366,1336,1402,1291,1412,1311]
    D = [4,971,115,75,429,1019,558,871,355,311,257,608,1061,212,460,1113,777,188,1361,1146,742,1262,1439,1224,1299,1204,660,1342,1430,1168,707,1413,1310,1399]

    # Filter out rows with invalid orig_taz and dest_taz values
    df_processed = df_processed[df_processed['orig_taz'].isin(O) & df_processed['dest_taz'].isin(D)]
    
    # Sum columns 4 to 11
    df_processed['total'] = (df.iloc[:, [3,6,7,8,9,10]]).sum(axis=1)

    # print(df_processed)
    
    return df_processed

# Define a function to clean the existing table
def clean_existing_table(existing_table):
    # Keep rows with the largest value in column 'actual' for each unique combination of 'orig_taz' and 'dest_taz'
    existing_table['actual'] = existing_table.groupby(['orig_taz', 'dest_taz'])['actual'].transform('max')
    existing_table = existing_table.drop_duplicates(subset=['orig_taz', 'dest_taz'], keep='first')
    existing_table = existing_table.sort_values(['orig_taz', 'dest_taz'], ascending=[True, True])

    print('existing table:')
    print(existing_table)
    
    return existing_table

# Define a function to merge with another table
def merge_with_existing(df_processed, existing_table, access_egress):
    print('df_processed:')
    print(df_processed)
    existing_table[access_egress] = existing_table[access_egress].fillna('')
    return pd.merge(existing_table, df_processed, on=['orig_taz', 'dest_taz', access_egress], how='inner')

# Define a list of relevant pathways to process the files for
pathways = ['2035_TM152_NGF_NP10', '2035_TM152_NGF_NP10_Path1a_02']
# Define the directory containing the CSV files
scenarios_dir = 'L:\\Application\\Model_One\\NextGenFwys\\Scenarios'
transit_paths_dir = 'L:\\Application\\Model_One\\NextGenFwys\\metrics\\Engagament Visualizations\\transit paths'


# Initialize a list to hold all the data frames
combined_df = pd.DataFrame(columns=['orig_taz', 'dest_taz', 'actual', 'runid', 'fare', 'total',\
                                    "wlk_loc_wlk", "wlk_lrf_wlk", "wlk_exp_wlk", "wlk_hvy_wlk", "wlk_com_wlk", "drv_loc_wlk", "drv_lrf_wlk",\
                                    "drv_exp_wlk", "drv_hvy_wlk", "drv_com_wlk", "wlk_loc_drv", "wlk_lrf_drv", "wlk_exp_drv", "wlk_hvy_drv", "wlk_com_drv"])

for runid in pathways:
    directory = os.path.join(scenarios_dir, runid, 'OUTPUT', 'skims_csv')

    existing_table = pd.read_csv(os.path.join(transit_paths_dir,f'TPPL_{runid}.csv'))
    existing_table.columns = ['mode', 'lines', 'wait', 'time', 'actual', 'b', 'a', 'orig_taz', 'dest_taz', 'iteration', 'runid',\
                              "wlk_loc_wlk", "wlk_lrf_wlk", "wlk_exp_wlk", "wlk_hvy_wlk", "wlk_com_wlk", "drv_loc_wlk", "drv_lrf_wlk",\
                              "drv_exp_wlk", "drv_hvy_wlk", "drv_com_wlk", "wlk_loc_drv", "wlk_lrf_drv", "wlk_exp_drv", "wlk_hvy_drv", "wlk_com_drv"]
    final_columns = ['orig_taz', 'dest_taz', 'actual', 'runid',\
                     "wlk_loc_wlk", "wlk_lrf_wlk", "wlk_exp_wlk", "wlk_hvy_wlk", "wlk_com_wlk", "drv_loc_wlk", "drv_lrf_wlk",\
                     "drv_exp_wlk", "drv_hvy_wlk", "drv_com_wlk", "wlk_loc_drv", "wlk_lrf_drv", "wlk_exp_drv", "wlk_hvy_drv", "wlk_com_drv"]
    existing_table = clean_existing_table(existing_table[final_columns])

    # Iterate through files in the directory
    for filename in os.listdir(directory):
        if filename.endswith(".csv") and 'trnskmam' in filename and'_trn_' not in filename:
            # pull access/egress combination from filename
            access_egress = filename.split('trnskmam_')[-1].split('.')[0]
            file_path = os.path.join(directory, filename)
            print('read: ' + file_path)
            df_processed = process_csv(file_path)
            df_processed[access_egress] = access_egress
            merged_table = merge_with_existing(df_processed, existing_table, access_egress)
            print('merged table:')
            print(merged_table)
            # Append the DataFrame to the list
            combined_df = pd.concat([combined_df, merged_table], ignore_index=True)

# drop duplicate rows
combined_df['absolute_difference'] = abs(combined_df['actual'] - combined_df['total'])
combined_df = combined_df.sort_values(by=['absolute_difference'], ascending=True).drop_duplicates(['orig_taz', 'dest_taz', 'runid'])
rows_before = combined_df.shape[0]
combined_df = combined_df[combined_df['absolute_difference'] < 3]
rows_after = combined_df.shape[0]
print(str(rows_before - rows_after) + ' rows had an absolute difference in travel time greater than 3 and thus were not included in the final table.')
combined_df = combined_df[['orig_taz', 'dest_taz', 'actual', 'runid', 'fare', 'total']]
# Print the final merged table
print(combined_df)

# Save the combined DataFrame as a single CSV
combined_path = os.path.join(transit_paths_dir, 'OD_taz_travel_times_E1.csv')
combined_df.to_csv(combined_path, index=False)