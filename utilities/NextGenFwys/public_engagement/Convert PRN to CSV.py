import os
import csv
import pandas as pd
import numpy as np

# Define a function to extract tables from a given PRN file
def extract_tables(original_file_name, input_file, output_dir):
    # Read all lines from the input PRN file
    with open(input_file, 'r') as f:
        lines = f.readlines()

    in_table = False  # Initialize flag for being inside a table
    table_lines = []  # Initialize list to hold lines of the current table

    # Loop through each line in the file
    for line in lines:
        if line.startswith("TRACE:") and in_table:
            # Save the table if a new TRACE section starts
            save_table(original_file_name, table_lines, output_dir)
            in_table = False  # Reset flag
            table_lines = []  # Reset list

        if line.startswith("TRACE:"):
            in_table = True  # Set flag to indicate we are inside a table

        if in_table:
            table_lines.append(line)  # Add the line to the current table

    # Save the last table (if any) after the loop ends
    if in_table:
        save_table(original_file_name, table_lines, output_dir)

def save_table(original_file_name, table_lines, output_dir):
    # Create a subfolder 'tables' if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Get the trace number from the table header
    trace_range = table_lines[0].split('= ')[-1].strip()  # Extract trace range from the line

    # Create a CSV writer for this table
    output_file = f"{original_file_name}_{trace_range}.csv"
    output_path = os.path.join(output_dir, output_file)

    with open(output_path, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)

        # Process the table content
        for line in table_lines[1:]:

            if line.startswith('M') & (line.startswith('Metropolitan') == False):  # Check if the line starts with 'M'
                row = line.split()  # Split the line into parts
                if (len(row)>7) & (len(row)< 15):
                    csvwriter.writerow(row[1:])  # Append the parts (excluding the first element 'M') to the data list

            elif (line.startswith(('1','2','3','4','5','6','7','8','9','0',\
                ' 1',' 2',' 3',' 4',' 5',' 6',' 7',' 8',' 9',' 0',\
                '  1','  2','  3','  4','  5','  6','  7','  8','  9','  0',\
                '   1','   2','   3','   4','   5','   6','   7','   8','   9','   0'))):
                row = line.split()
                if (len(row)>7) & (len(row)< 15):
                    csvwriter.writerow(row)

# Define a function to extract tables from multiple PRN files
def extract_tables_from_prn_files(input_dir, output_dir):

    # Generate a list of PRN file names (formatted as TPPLXXXX.PRN)
    # prn_files = [f for f in os.listdir(input_dir) if f.endswith(".PRN")]
    # select the range by visually scanning the dates of the new PRN files produced
    # for details on how to produce the files, see https://app.asana.com/0/1201809392759895/1205348861092578/f
    prn_files = ["TPPL{:04d}.PRN".format(i) for i in range(111, 126)]

    # Loop through the list of PRN files
    for prn_file in prn_files:
        input_path = os.path.join(input_dir, prn_file)  # Get the full path of the PRN file
        original_file_name = prn_file.split(".")[0]  # Extract the file name without the extension

        with open(input_path, 'r') as f:
            if 'tripsam.tpp' in f.read():  # Check if 'tripsam.tpp' is mentioned in the file
                extract_tables(original_file_name, input_path, output_dir)

# Define a function to process saved CSV files
def process_saved_csvs(input_dir):

    # Define list of origins and destinations of interest
    O = [410,972,146,478,820,767,558,607,234,16,742,1178,81,296,355,315,677,1145,1098,1176,1083,189,991,700,1421,1448,1270,1246,1366,1336,1402,1291,1412,1311]
    D = [4,971,115,75,429,1019,558,871,355,311,257,608,1061,212,460,1113,777,188,1361,1146,742,1262,1439,1224,1299,1204,660,1342,1430,1168,707,1413,1310,1399]
    
    skipped = 0 #count how many OD pairs weren't relevant

    # create output_dir
    output_dir = os.path.join(input_dir, 'cleaned tables')
    os.makedirs(output_dir, exist_ok=True)

    # Get a list of all CSV files in the specified directory
    csv_files = [f for f in os.listdir(input_dir) if f.endswith(".csv")]

    # Initialize a list to hold all the data frames
    df_list = []

    # Loop through the list of CSV files
    for csv_file in csv_files:
        input_path = os.path.join(input_dir, csv_file)  # Get the full path of the CSV file

        # Define column names for the CSV
        column_names = ['mode', 'b', 'wait', 'time', 'actual', 'percvd', 'dist', 'total', 'lines', 'lines (2)', 'lines (3)']
        final_columns = ['mode', 'lines', 'wait', 'time', 'actual', 'b']

        # Read the CSV into a DataFrame and select specific columns
        df = pd.read_csv(input_path, names = column_names)
        df = df[final_columns]

        # Get the origin from the file name
        origin = float(csv_file.split('_')[1].split('-')[0])
        # Get the destination from the file name
        destination = float(csv_file.split('_')[1].split('-')[1].split('.')[0])

        # check to make sure the routes are of interest
        if (origin not in O) | (destination not in D):
            skipped += 1
            continue
        # Get the iteration number from the file name
        iteration = csv_file.split('_')[0].split('L')[1]

        # Add an 'a' column to the DataFrame
        df['a'] = df['b'].shift(1)
        # Fill NaN values in 'a' column with the first origin
        df['a'].fillna(origin, inplace = True)
        # cast 'a' column as integers
        df['a'] = df['a'].astype(int)

        # replace all occurences of '--' with 0 in 'wait'
        df['wait'] = df['wait'].replace('--', 0).astype(float)

        # extract the name of the line before the weight value and overwrite the column with these cleaned strings
        # Define a function to extract the desired part
        def extract_part(s):
            if pd.notnull(s) and isinstance(s, str) and '(' in s:
                return str(s).split('(')[0].strip()
            else:
                return s

        # Apply the function to Col9
        df['lines'] = df['lines'].apply(extract_part)

        # Identify non-zero strings in the second column of Table 1
        non_zero_strings = df[df['lines'] != 0]['lines'].tolist()
        # print('non_zero_strings:')
        # print(non_zero_strings)

        # Iterate through non-zero strings and perform operations
        for string in non_zero_strings:

            if not pd.isnull(string):
                # Load corresponding CSV file
                # get the pathway name from the input directory
                scenarios_directory = 'L:\\Application\\Model_One\\NextGenFwys\\Scenarios\\'
                pathway_name = input_dir.split("\\trn")[0].split("Projects\\")[-1]
                transit_lines_location = '\\INPUT\\trn\\TransitLineTables\\'
                transit_lines_dir = scenarios_directory + pathway_name + transit_lines_location  # create the full directory of the csv file
                csv_name = string.replace("-","")
                csv_dir = os.path.join(transit_lines_dir, f'{csv_name}.csv')  # Output to 'tables' subfolder
                # print('read: ' + csv_dir)

                # try:
                line_links = pd.read_csv(csv_dir) # Assuming the CSV files are named accordingly
                # print('string: ' + string)
                # print(line_links)
                # locate index of string
                idx_string = df.index[(df['lines'] == string)==True].tolist()[0]
                # use index string to locate matches of nodes
                match_a = df.iloc[idx_string - 1,4].item()
                match_b = df.loc[df['lines'] == string,'b'].item()
                if '-' in string:
                    idx_start = line_links.index[line_links.b == match_b]
                    idx_end = line_links.index[line_links.b == match_a]
                else:
                    idx_start = line_links.index[line_links.b == match_a]
                    idx_end = line_links.index[line_links.b == match_b]

                # print(idx_string, match_a, match_b, idx_start, idx_end)
                good = list(zip(list(idx_start+1), list(idx_end)))#required sequences

                #unpack list of list
                g2 = [list(range(x[0],x[1]+1)) for x in good]

                # Filter line_links for rows between match_a and match_b
                filtered_rows = line_links.iloc[np.r_[[y for x in g2 for y in x]]]#If you want to return just the valid dataset

                # Create a new DataFrame with values from filtered_rows
                new_rows = pd.DataFrame({'a': filtered_rows['a'], 'b': filtered_rows['b']})

                # add the line name and mode
                new_rows['mode'] = df.loc[df['lines'] == string,'mode'].item()
                new_rows['lines'] = string

                # print('filtered rows:')
                # print(filtered_rows)
                
                # Append new_rows to df
                df = pd.concat([df.iloc[:idx_string], new_rows, df.iloc[idx_string:]]).reset_index(drop=True)
                # print('new df:')
                # print(df)

                # except:
                #     print("Skipping: " + transit_lines_dir)
                #     print("No such file or directory.")

        # make sure wait column contains floats
        df['wait'] = df['wait'].astype(float)

        # add origin TAZ column
        df['origin'] = int(origin)
        # add destination TAZ column
        df['destination'] = int(destination)
        # add iteration column
        df['iteration'] = int(iteration)
        # add pathway column
        df['pathway'] = pathway_name

        # create a new folder for cleaned tables
        output_path = os.path.join(output_dir, csv_file)

        # write the file with the processed df
        df.to_csv(output_path, index=False, header = False)

        # Append the DataFrame to the list
        df_list.append(df)

    # Concatenate all DataFrames in the list
    combined_df = pd.concat(df_list)

    # Find the maximum value of 'iteration' for each group of 'origin' and 'destination'
    max_iteration = combined_df.groupby(['origin', 'destination'])['iteration'].transform('max')

    # Filter the DataFrame for rows where 'iteration' is equal to the maximum value
    combined_df = combined_df[combined_df['iteration'] == max_iteration]

    # Save the combined DataFrame as a single CSV
    combined_path = os.path.join(output_dir, f'TPPL_{pathway_name}.csv')
    combined_df.to_csv(combined_path, index=False, header=False)

    print("Skipped: " + str(skipped) + " OD pairs")

if __name__ == "__main__":
    input_dir = os.getcwd()  # Use the current directory
    output_dir = os.path.join(input_dir, 'tables(2)')  # Output to 'tables' subfolder

    # Call the function to extract tables from PRN files and save them as CSVs
    extract_tables_from_prn_files(input_dir, output_dir)

    # Then, process saved CSVs
    process_saved_csvs(output_dir)

