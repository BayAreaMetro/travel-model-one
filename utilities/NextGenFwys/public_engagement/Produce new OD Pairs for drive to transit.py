import pandas as pd
import os

# Define a function to process each file
def process_csv(file_path):
    # Read the CSV file
    df = pd.read_csv(file_path)
    
    # Extract the required columns
    df_processed = df[['N', 'TAZ1454']]

    return df_processed

# Define a list of relevant pathways to process the files for
pathways = ['2035_TM152_NGF_NP10', '2035_TM152_NGF_NP10_Path1a_02']
# Define the directory containing the CSV files
scenarios_dir = 'L:\\Application\\Model_One\\NextGenFwys\\Scenarios'
transit_paths_dir = 'L:\\Application\\Model_One\\NextGenFwys\\metrics\\Engagament Visualizations\\transit paths'


# Initialize a list to hold all the data frames
combined_df = pd.DataFrame(columns=['orig_taz', 'dest_taz'])

for runid in pathways:
    directory = os.path.join(transit_paths_dir, f'network_nodes_TAZ_{runid}.csv')

    existing_table = pd.read_csv(os.path.join(transit_paths_dir,f'TPPL_{runid}.csv'))
    existing_table.columns = ['mode', 'lines', 'wait', 'time', 'actual', 'B', 'A', 'orig_taz', 'dest_taz', 'iteration', 'runid',\
                              "wlk_loc_wlk", "wlk_lrf_wlk", "wlk_exp_wlk", "wlk_hvy_wlk", "wlk_com_wlk", "drv_loc_wlk", "drv_lrf_wlk",\
                              "drv_exp_wlk", "drv_hvy_wlk", "drv_com_wlk", "wlk_loc_drv", "wlk_lrf_drv", "wlk_exp_drv", "wlk_hvy_drv", "wlk_com_drv"]
    final_columns = ['mode', 'A', 'B', 'orig_taz', 'dest_taz', 'runid']
    existing_table = existing_table[final_columns]
    print('read: ' + directory)

    mode2_table = existing_table[(existing_table['mode'] == 2)]
    mode_2_TAZs = process_csv(directory)
    merged_2_table = pd.merge(mode2_table, mode_2_TAZs, left_on=['B'], right_on=['N'], how='inner')
    merged_2_table = pd.DataFrame({'orig_taz': merged_2_table['orig_taz'], 'dest_taz': merged_2_table['TAZ1454']})

    mode7_table = existing_table[(existing_table['mode'] == 7)]
    mode_7_TAZs = process_csv(directory)
    merged_7_table = pd.merge(mode7_table, mode_7_TAZs, left_on=['A'], right_on=['N'], how='inner')
    merged_7_table = pd.DataFrame({'orig_taz': merged_7_table['TAZ1454'], 'dest_taz': merged_7_table['dest_taz']})

    # Append the DataFrame to the list
    combined_df = pd.concat([merged_2_table, merged_7_table], ignore_index=True)
    combined_df = combined_df[['orig_taz', 'dest_taz']]

    # Save the combined DataFrame as a single CSV
    combined_path = os.path.join(transit_paths_dir, f'drive_to_transit_OD_pairs_{runid}.csv')
    combined_df.to_csv(combined_path, index=False)