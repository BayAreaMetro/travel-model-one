Steps:
produce a new list of OD pairs
currently a manual process
List of Origin and Destination TAZs are selected using GIS software to visualize the geographic locations desired
It's helpful to have a layer that includes geometries for zip codes to better locate the relevant TAZs
Both the TAZ layer as well as one for California zip codes can be found online
Note that for the purposes of TransitAssign_NGFtrace.job, the O/D lists can be a maximum of 55 Origins or Destinations which cannot exceed 255 characters in length
Update the list of O/Ds in TransitAssign_NGFtrace.job and TraceDApaths.bat located on X:\travel-model-one-master\utilities\NextGenFwys\public_engagement
TransitAssign_NGFtrace.job 
update variables token_debug_origin_list & token_debug_destination_list
TraceDApaths.bat
update variables ORIGIN & DESTINATION
Note that this step can be avoided by updating the relevant scripts to check for O/D lists passed in the command line as arguments (my vision is that this would be done in UpdateMapDataForNewOD.bat). I was unable to do so myself, but I believe it may be an easy fix for the FMS team
run UpdateMapDataForNewOD.bat on a modeling server to generate the driven and transit trace paths
first verify the desired model runs in the script
update paths based on mapped drives on respective modeling server being used to run the batch file
clean the driven and transit trace paths
driven
copy HwyAssign_trace_to_csv.py to the relevant HwyAssign_trace folder and run it from there
(done as part of UpdateMapDataForNewOD.bat)
transit
run Convert_lin_to_csv.py to produce individual ab link tables for all transit lines contained in transitLines.lin
these lookup tables are used in Convert_PRN_to_CSV.py 
clean the output trace files (.PRN) by running Convert_PRN_to_CSV.py 
detailed breakdowns of transit routes used as well as relevant link node information for most OD pairs are extracted from the trace files
find the transit fares associated with the OD trips
run Lookup_transit_fare_using_OD_pairs_and_modes.py
this script iterates through a list of pathways and reads trnskmam tables for various mode combinations to find the transit fare cost of an OD trip
produce lists of Origins and Destinations for the drive to transit portions of the various traced paths.
Driven paths would need to be produced for the new lists of Origins and Destinations using TraceDApaths.bat (see above for instructions)