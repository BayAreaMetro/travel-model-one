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
            # elif (line.startswith(('', 'Metropolitan', '-')) == False):
            #     row = line.split()
            #     if (len(row)>7) & (len(row)< 15):
            #         csvwriter.writerow(row)
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

    # Loop through the list of CSV files
    for csv_file in csv_files:
        input_path = os.path.join(input_dir, csv_file)  # Get the full path of the CSV file
        # print('path: ' + input_path)
        # Define column names for the CSV
        column_names = ['Column1', 'Column2', 'Column3', 'Column4', 'Column5', 'Column6', 'Column7', 'Column8', 'Column9', 'Column10', 'Column11']
        final_columns = ['Column1', 'Column2', 'Column3', 'Column4', 'Column5', 'Column6', 'Column7', 'Column8']
        # Read the CSV into a DataFrame and select specific columns
        table = pd.read_csv(input_path, names = column_names)
        table = table[final_columns]

        # Get the origin from the file name
        origin = csv_file.split('_')[1].split('-')[0]

        # Add an 'origin' column to the DataFrame
        table['Column9'] = table['Column2'].shift(1)

        # Fill NaN values in 'origin' column with the first origin
        table.fillna(origin, inplace = True)

        # Overwrite the original file with the processed table
        table.to_csv(input_path, index=False, header = False)

if __name__ == "__main__":
    input_dir = os.getcwd()  # Use the current directory
    output_dir = os.path.join(input_dir, 'tables')  # Output to 'tables' subfolder

    # Call the function to extract tables from PRN files and save them as CSVs
    extract_tables_from_prn_files(input_dir, output_dir)

    # Then, process saved CSVs
    process_saved_csvs(output_dir)

