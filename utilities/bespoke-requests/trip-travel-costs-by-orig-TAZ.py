import copy, os, subprocess, sys
import pandas

# convert rdata from csv
OUTPUT_FOLDER = "L:\\RTP2021_PPA\\Projects\\2015_TM151_PPA_12\\OUTPUT\\updated_output"
trips_rdata   = os.path.join(OUTPUT_FOLDER, "trips.rdata")
trips_csv     = os.path.join(OUTPUT_FOLDER, "trips.csv")

if os.path.exists(trips_csv):
	print("{} exists -- skipping conversion from {}".format(trips_csv, trips_rdata))
else:
	print("Converting {} to {}".format(trips_rdata, trips_csv))
	myenv         = copy.deepcopy(os.environ)
	convert_cmd   = [r"C:\\Program Files\\R\\R-3.5.2\\bin\\x64\\RScript.exe", "-e",
					 "load('{}'); write.table(trips, file='{}', sep=',', row.names=FALSE)".format(trips_rdata.replace("\\","/"), trips_csv.replace("\\","/"))]
	proc = subprocess.Popen( convert_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=myenv )
	for line in proc.stdout:
	    line = line.strip(b'\r\n')
	    print("stdout: " + line)
	
	for line in proc.stderr:
	    line = line.strip(b'\r\n')
	    print("stderr: " + line)
	retcode  = proc.wait()
	print("Received {} from [{}]".format(retcode, convert_cmd))

# read the csv
trips_df = pandas.read_csv(trips_csv)
print("Read {}".format(trips_csv))
# these are the columns available
print(trips_df.columns.values.tolist())
# keep subset of columns to free memory?
trips_df = trips_df[["orig_taz","dest_taz","num_participants","trip_mode","distance","cost","time"]]
print(trips_df.head())

# assume SAMPLE_SHARE=0.5, standard for iter3
SAMPLESHARE=0.5

# aggregate to origin taz, trip_mode, summing num_participants and taking mean of distance, cost, time
trips_by_orig_tripmode_df = trips_df.groupby(["orig_taz","trip_mode"]).agg({
	'num_participants':'sum', 'distance':'mean', 'cost':'mean', 'time':'mean'}).reset_index()

# this has total cost/time/distance for person trips, but the person trips are a sample -- so scale up
trips_by_orig_tripmode_df['num_participants'] = trips_by_orig_tripmode_df['num_participants']/SAMPLESHARE
print(trips_by_orig_tripmode_df.head())

# write the result
trips_by_orig_tripmode_df.to_csv(os.path.join(OUTPUT_FOLDER, "trip-travel-costs-by-orig-TAZ.csv"), index=False)