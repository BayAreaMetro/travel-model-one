# combine PRN files of interest to make it easier to search for desired information

# Step 1: Import necessary libraries
import os

# Step 2: Define the directory where your .prn files are located
directory = os.getcwd()

# Step 3: Get a list of all .prn files in the directory
prn_files = ["TPPL{:04d}.PRN".format(i) for i in range(116, 126)]

# Step 4: Open a new file for writing
output_file = open('TPPL_combined.PRN', 'wb')  # Change 'combined.prn' to your desired output file name

# Step 5: Iterate through the list of .prn files and append their contents to the output file
for prn_file in prn_files:
    with open(os.path.join(directory, prn_file), 'rb') as f:
        output_file.write(f.read())

# Step 6: Close the output file
output_file.close()

print('Files combined successfully!')
