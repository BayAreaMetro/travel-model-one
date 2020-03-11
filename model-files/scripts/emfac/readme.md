RunPrepareEmfac.bat

This batch job processes three types of activity data (by county) for input into EMFAC to run in Burden mode 
and calculating regional on-road emission inventories.  The three types of activity data (all by county) that will 
be inputted are: (1) vehicle speed distribution files (for passenger vehicle types only); (2) vmt files by time of 
day and fuel type; (3) vehicle population files by vehicle type and fuel type.

There are five scripts/steps that produce the activity data inputted into EMFAC. 

Step (1) / Script (1) CreateSpeedBinsBetweenZones.job;
This step and script extracts link level VMT and speeds for the 13 ARB speed cohorts.
This generic script forecast year run applies for all 5 timeperiods.      

Step (2) / Script (2) CreateSpeedBinsWithinZones.job;
This step and script - a) extracts intrazonal level VMT and speeds; and b) extracts total daily trips for the 13 ARB speed cohorts
This generic script forecast year run also applies for all 5 timeperiods.      

Step (3) / Script (3)
This step sums EMFAC output for two csv files 1) travel between zones and 2) travel within zones by county and the 13 ARB 
speed cohorts.
The output of this script is two files: 1) a file with the sum of the two inputs; 2) the share of each speed bin relative to county totals; 
and 3) the total vmt values collapsed to county and hourly bins.

Step (4) / Script (4)
This step multiplies total VMT (stratified by county and hour of day) by VMT share values for fuel type and vehicle class
The output of this script is a unique file for each county, by VMT, in each category of fuel type, vehicle class, and hour of the day

Step (5) / Script (5)
This step creates a factor for growing the vehicle population files, using county VMT total ratios for project year and base year, and an EMFAC-generated factor 
The output of this script is a unique file for each county, by vehicle population for each vehicle and fuel type

time on every highway link by assuming a fixed
delay (in minutes per mile), segmented by area type and facility type.  Links with speeds below a very low 
minimum threshold are sped up to that minimum threshold to help the path builder find valid paths.  This step 
also adds transit-only nodes to the highway network which are needed for the second and third steps in the script. 

Second, transit-only access links are added to the highway network.  This is necessary for TP+ to 
automatically generate walk and drive access links. 

Third, and last, transit-only transfer links are added to the highway network.  This is necessary for TP+
to automatically generate transfer access links. 

 CreateSpeedBinsBetweenZones.job
 CreateSpeedBinsWithinZones.job
 SumSpeedBins1.awk
 SumSpeedBins2.awk
 SumSpeedBins3.awk


The script first loops through the five time periods, which are: (a) early AM, 3 am to 6 am; (b) AM peak period, 
6 am to 10 am; (c) midday, 10 am to 3 pm; (d) PM peak period, 3 pm to 7 pm; and, (e) evening, 7 pm to 3 am the next 
day.

The facility type (FT) codes used by this script are as follows: (1) freeway-to-freeway connector; (2) freeway; 
(3) expressway; (4) collector; (5) freeway ramp; (6) dummy link; (7) major arterial; (8) metered ramp; 
(9) special facility. 

The area type (AT) codes used by this script are as follows: (0) regional core; (1) central business 
district (CBD); (2) urban business; (3) urban; (4) suburban; (5) rural. 

Input:  (1)  A highway network that contains the following variables: (i) PNROK, for which a code of 1 means

             (see CreateFiveHighwayNetworks.job); (ii) CTIM, which is the congested travel time (iii) FT, 
             facility type, whose codes are described above; (iv) AT, area type, whose codes are described above; 
             (v) DISTANCE, coded in miles. 


             contain only an A-node and a B-node, where the A-node is on the highway network and the B-node is








Output: (1)  A time-period-specific transit background network that contains transit-only nodes and the








Notes:  (1) 

See also: (1) TransitSkims.job -- Uses the bus speeds computed here to estimate transit travel times
          (2) BuildTransitNetworks.job -- Creates the transit networks that are subsequently skimmed and assigned


version:  Travel Model One
authors:  dto (2010 08 10); gde
