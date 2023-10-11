# combine PRN files of interest to make it easier to search for desired information

# Step 1: Import necessary libraries
import os

# Step 2: Define the directory where your .prn files are located
directory = os.getcwd()

# Step 3: Get a list of all .prn files in the directory
# select the range by visually scanning the dates of the new PRN files produced
# for details on how to produce the files, see https://app.asana.com/0/1201809392759895/1205348861092578/f
prn_files = ["TPPL{:04d}.PRN".format(i) for i in range(111, 126)]

# Step 4: Open a new file for writing
output_file = open('TPPL_AM_combined.PRN', 'wb')  # Change 'combined.prn' to your desired output file name

# Step 5: Iterate through the list of .prn files and append their contents to the output file
for prn_file in prn_files:
    with open(os.path.join(directory, prn_file), 'rb') as f:
        output_file.write(f.read())

# Step 6: Close the output file
output_file.close()

print('Files combined successfully!')
