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
    prn_files = ["TPPL{:04d}.PRN".format(i) for i in range(116, 126)]

    # Loop through the list of PRN files
    for prn_file in prn_files:
        input_path = os.path.join(input_dir, prn_file)  # Get the full path of the PRN file
        original_file_name = prn_file.split(".")[0]  # Extract the file name without the extension

        with open(input_path, 'r') as f:
            if 'tripsam.tpp' in f.read():  # Check if 'tripsam.tpp' is mentioned in the file
                extract_tables(original_file_name, input_path, output_dir)

# Define a function to process saved CSV files
def process_saved_csvs(input_dir):
    # Get a list of all CSV files in the specified directory
    csv_files = [f for f in os.listdir(input_dir)]

    # Initialize a list to hold all the data frames
    df_list = []

    # Loop through the list of CSV files
    for csv_file in csv_files:
        input_path = os.path.join(input_dir, csv_file)  # Get the full path of the CSV file

        # Define column names for the CSV
        column_names = ['mode', 'b', 'wait', 'time', 'actual', 'percvd', 'dist', 'total', 'lines', 'lines (2)', 'lines (3)']
        final_columns = ['mode', 'lines', 'wait', 'time', 'b']

        # Read the CSV into a DataFrame and select specific columns
        df = pd.read_csv(input_path, names = column_names)
        df = df[final_columns]

        # Get the origin from the file name
        origin = csv_file.split('_')[1].split('-')[0]
        # Get the destination from the file name
        destination = csv_file.split('_')[1].split('-')[1].split('.')[0]
        # Get the iteration number from the file name
        iteration = csv_file.split('_')[0].split('L')[1]

        # Add an 'a' column to the DataFrame
        df['a'] = df['b'].shift(1)
        # Fill NaN values in 'a' column with the first origin
        df['a'].fillna(origin, inplace = True)
        # cast 'a' column as integers
        df['a'] = df['a'].astype(int)

        # add origin TAZ column
        df['origin'] = int(origin)
        # add destination TAZ column
        df['destination'] = int(destination)
        # add iteration column
        df['iteration'] = int(iteration)

        # replace all occurences of '--' with 0 in 'wait'
        df['wait'] = df['wait'].replace('--', 0).astype(float)

        # extract the name of the line before the weight value and overwrite the column with these cleaned strings
        df['lines'] = df['lines'].str.extract(r'(.+?)\(')

        # Overwrite the original file with the processed df
        df.to_csv(input_path, index=False, header = False)

        # Append the DataFrame to the list
        df_list.append(df)

    # Concatenate all DataFrames in the list
    combined_df = pd.concat(df_list)

    # Find the maximum value of 'iteration' for each group of 'origin' and 'destination'
    max_iteration = combined_df.groupby(['origin', 'destination'])['iteration'].transform('max')

    # Filter the DataFrame for rows where 'iteration' is equal to the maximum value
    combined_df = combined_df[combined_df['iteration'] == max_iteration]

    # Save the combined DataFrame as a single CSV
    combined_path = os.path.join(input_dir, 'TPPL.csv')
    combined_df.to_csv(combined_path, index=False, header=False)

if __name__ == "__main__":
    input_dir = os.getcwd()  # Use the current directory
    output_dir = os.path.join(input_dir, 'tables')  # Output to 'tables' subfolder

    # Call the function to extract tables from PRN files and save them as CSVs
    extract_tables_from_prn_files(input_dir, output_dir)

    # Then, process saved CSVs
    process_saved_csvs(output_dir)

