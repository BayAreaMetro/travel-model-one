USAGE = """

  python Extract_new_OD_pairs_to_trace_from_drive_to_transit.py

  This script does not need to be run from a specific directory

  The purpose of this script is to produce a list of Origins and Destinations for the drive to transit portions of the various traced paths.
  Driven paths would need to be produced for the new lists of Origins and Destinations using TraceDApaths.bat

  Main Execution:

    Initializes an empty DataFrame (combined_df) to hold the results.
    Iterates through a list of pathways.
    Reads an existing table from a CSV file (TPPL_[runid].csv) and selects specific columns.
    Processes two modes (mode 2 and mode 7) separately:
    For mode 2, the script reads another CSV file (network_nodes_TAZ_[runid].csv), processes it using the process_csv function, and merges it with the existing table based on the 'B' and 'N' columns. The result is a DataFrame (merged_2_table) with columns 'orig_taz' and 'dest_taz'.
    For mode 7, a similar process is applied, and the result is stored in a DataFrame (merged_7_table).
    Combines the two DataFrames (merged_2_table and merged_7_table) and selects only the 'orig_taz' and 'dest_taz' columns.
    Saves the combined DataFrame as a single CSV file for each pathway.

"""
import pandas as pd
import os
import sys

# Define a function to process each file
def process_csv(file_path):
    # Read the CSV file
    df = pd.read_csv(file_path)
    
    # Extract the required columns
    df_processed = df[['N', 'TAZ1454']]

    return df_processed

def main():

    # Check if 3 command-line arguments are provided
    if len(sys.argv) == 2:
        # Extract tables_version from command-line arguments 
        tables_version = sys.argv[1]
    else:
        # initialize tables_version with default string
        tables_version = '00'

    # Define a list of relevant pathways to process the files for
    pathways = ['2035_TM152_NGF_NP10', '2035_TM152_NGF_NP10_Path1a_02', '2035_TM152_NGF_NP10_Path4_02']
    # Define the directory containing the CSV files
    scenarios_dir = 'L:\\Application\\Model_One\\NextGenFwys\\Scenarios'
    transit_paths_dir = f'L:\\Application\\Model_One\\NextGenFwys\\metrics\\Engagament Visualizations\\transit paths (v{tables_version})'


    # Initialize a list to hold all the data frames
    combined_df = pd.DataFrame(columns=['orig_taz', 'dest_taz'])

    for runid in pathways:
        directory = os.path.join(transit_paths_dir, f'network_nodes_TAZ_{runid}.csv')

        existing_table = pd.read_csv(os.path.join(transit_paths_dir,f'TPPL_{runid}.csv'))
        num_columns = existing_table.shape[1]
        column_names = ['mode', 'lines', 'wait', 'time', 'actual', 'B', 'A', 'orig_taz', 'dest_taz', 'iteration', 'runid',\
                                "wlk_loc_wlk", "wlk_lrf_wlk", "wlk_exp_wlk", "wlk_hvy_wlk", "wlk_com_wlk", "drv_loc_wlk", "drv_lrf_wlk",\
                                "drv_exp_wlk", "drv_hvy_wlk", "drv_com_wlk", "wlk_loc_drv", "wlk_lrf_drv", "wlk_exp_drv", "wlk_hvy_drv", "wlk_com_drv"]
        first_n_column_names = column_names[:num_columns]
        existing_table.columns = first_n_column_names
        final_columns = ['mode', 'A', 'B', 'orig_taz', 'dest_taz', 'runid']
        existing_table = existing_table[final_columns]
        print('read: ' + directory)

        mode2_table = existing_table[(existing_table['mode'] == 2)]
        mode_2_TAZs = process_csv(directory)
        merged_2_table = pd.merge(mode2_table, mode_2_TAZs, left_on=['B'], right_on=['N'], how='inner')
        merged_2_table['origin'] = merged_2_table['orig_taz']
        merged_2_table['destination'] = merged_2_table['TAZ1454']
        renamed_2_table = pd.DataFrame({'orig_taz': merged_2_table['orig_taz'], 'dest_taz': merged_2_table['TAZ1454']})

        mode7_table = existing_table[(existing_table['mode'] == 7)]
        mode_7_TAZs = process_csv(directory)
        merged_7_table = pd.merge(mode7_table, mode_7_TAZs, left_on=['A'], right_on=['N'], how='inner')
        merged_7_table['origin'] = merged_7_table['TAZ1454']
        merged_7_table['destination'] = merged_7_table['dest_taz']
        renamed_7_table = pd.DataFrame({'orig_taz': merged_7_table['TAZ1454'], 'dest_taz': merged_7_table['dest_taz']})

        # Append the DataFrame to the list
        combined_df = pd.concat([renamed_2_table, renamed_7_table], ignore_index=True)
        combined_df = combined_df[['orig_taz', 'dest_taz']]

        # Apply a custom lambda function to each column to remove duplicates and shift values upwards
        combined_df = combined_df.apply(lambda x: x.drop_duplicates().reset_index(drop=True))

        # Save the combined DataFrame as a single CSV
        combined_path = os.path.join(transit_paths_dir, f'drive_to_transit_OD_pairs_{runid}.csv')
        combined_df.to_csv(combined_path, index=False)

        # cast all columns except column 'C' to integers
        lookup_df.loc[:, lookup_df.columns != 'runid'] = lookup_df.loc[:, lookup_df.columns != 'runid'].astype(int)

        # repeat with old column names to use as lookup file later
        lookup_df = pd.concat([merged_2_table, merged_7_table], ignore_index=True)
        lookup_path = os.path.join(transit_paths_dir, f'drive_to_transit_lookup_{runid}.csv')
        lookup_df.to_csv(lookup_path, index=False)

if __name__ == "__main__":
    main()