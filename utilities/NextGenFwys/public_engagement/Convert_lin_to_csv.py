USAGE = """

  python Convert_lin_to_csv.py

  Run this from trn\TransitAssignment.iter3 of the model run dir.
  example: \\model3-a\Model3A-Share\Projects\2035_TM152_NGF_NP10_Path1a_02\trn\TransitAssignment.iter3
  Processes transitLines.lin and creates csv files for every transit line, each named after the respective line. See \INPUT\trn\TransitLineTables
  
"""

import os
import csv
import pandas as pd

# Define a function to extract tables from a given lin file
def extract_tables(input_file, output_dir):
    # Read all lines from the input lin file
    with open(input_file, 'r') as f:
        lines = f.readlines()

    in_table = False  # Initialize flag for being inside a table
    table_lines = []  # Initialize list to hold lines of the current table

    # Loop through each line in the file
    for line in lines:
        if line.startswith("LINE NAME=") and in_table:
            # Save the table if a new LINE section starts
            save_table(table_lines, output_dir)
            in_table = False  # Reset flag
            table_lines = []  # Reset list

        if line.startswith("LINE NAME="):
            in_table = True  # Set flag to indicate we are inside a table

        if in_table:
            table_lines.append(line)  # Add the line to the current table

    # Save the last table (if any) after the loop ends
    if in_table:
        save_table(table_lines, output_dir)

def save_table(table_lines, output_dir):
    # Create a subfolder 'tables' if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Get the LINE NAME from the table header
    LINE_NAME = table_lines[0].split("\"")[1].strip()  # Extract LINE NAME from the line

    # Create a CSV writer for this table
    output_file = f"{LINE_NAME}.csv"
    output_path = os.path.join(output_dir, output_file)

    with open(output_path, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)

        # Process the table content
        for line in table_lines[1:]:

            if line.startswith(' N= '):  # Check if the line starts with 'N='
                row = line.split()  # Split the line into parts
                # print(row)
                csvwriter.writerow(row[1:])  # Append the parts (excluding the first elements 'N=') to the data list

            elif line.startswith(' N=-'):  # Check if the line starts with 'N='
                row = line.split('-')  # Split the line into parts
                # print(row)
                csvwriter.writerow(row[1:])  # Append the parts (excluding the first elements 'N=') to the data list

            elif (line.startswith(('    1','    2','    3','    4','    5','    6','    7','    8','    9','    0',\
                                   '   -1','   -2','   -3','   -4','   -5','   -6','   -7','   -8','   -9','   -0'))):
                row = line.split()
                # print(row)
                csvwriter.writerow(row[0:1])
# Define a function to extract tables from multiple lin files
def extract_tables_from_lin_files(input_dir, output_dir):
    
    input_path = input_dir + '\\transitLines.lin'

    with open(input_path, 'r') as f:
        extract_tables(input_path, output_dir)

# Define a function to process saved CSV files
def process_saved_csvs(input_dir):
    # Get a list of all CSV files in the specified directory
    csv_files = [f for f in os.listdir(input_dir)]

    # Initialize a list to hold all the data frames
    df_list = []

    # Loop through the list of CSV files
    for csv_file in csv_files:
        input_path = os.path.join(input_dir, csv_file)  # Get the full path of the CSV file

        # print(input_path)

        # Define column names for the CSV
        column_names = ['b', 'access']

        # Read the CSV into a DataFrame and select specific columns
        df = pd.read_csv(input_path, names = column_names, index_col = None)
        df = df[['b']]
        # print(df)

        # split a contents on "," to remove "ACCESS..."
        df['b'] = df['b'].str.split(',').str.get(0)
        # split a contents on"-" to remove " N=-"
        df['b'] = df['b'].str.split('-').str.get(-1)

        # replace all occurences of ',' with '' in 'wait'
        df['b'] = df['b'].str.replace(',', '').str.replace('-','').astype(int)

        # Get the origin from the last row of the "a" column 
        origin = df['b'].iloc[-1]


        # Add a 'b' column to the DataFrame
        df['a'] = df['b'].shift(1)
        # Fill NaN values in 'b' column with the first origin
        df['a'].fillna(origin, inplace = True)

        # Overwrite the original file with the processed df
        df.to_csv(input_path, index=False)

if __name__ == "__main__":
    input_dir = os.getcwd()  # Use the current directory

    # get the pathway name from the input directory
    L_directory = 'L:\\Application\\Model_One\\NextGenFwys\\Scenarios\\'
    pathway = input_dir.split("\\trn")[0].split("Projects\\")[-1]
    trn_location = '\\INPUT\\trn'
    input_dir = L_directory + pathway + trn_location  # create the full directory of the trf folder

    output_dir = os.path.join(input_dir, 'TransitLineTables')  # Output to 'tables' subfolder

    # Check if the directory exists
    if os.path.exists(output_dir):
        # Directory exists, end script
        print(f"The directory '{output_dir}' exists. End.")
    else:
        # Directory does not exist
        print(f"The directory '{output_dir}' does not exist.  Executing extract_tables_from_lin_files.")
        # Call the function to extract tables from lin files and save them as CSVs
        extract_tables_from_lin_files(input_dir, output_dir)

        print("extract_tables_from_lin_files complete.  Executing process_saved_csvs.")
        # Then, process saved CSVs
        process_saved_csvs(output_dir)