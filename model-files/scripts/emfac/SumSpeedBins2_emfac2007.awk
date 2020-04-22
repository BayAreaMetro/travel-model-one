# This script is needed for emfac 2007 only (not needed for emfac 2014 and 2017)
#This file multiplies total VMT (stratified by county and hour of day) by VMT share values for fuel type and vehicle class
#The output of this script is a unique file for each county, by VMT, in each category of fuel type, vehicle class, and hour of the day
#Form for running this script is gawk -f sumspeedbins2b.awk *.csv
#SAI
#March 22, 2011
#Full Nine (9) County EMFAC Processing with Year 2000_XX_01 Version 0.1 Model One Run

BEGIN{                                                                                      
IGNORECASE=1													#Make input case-insensitive.
FS=(",")														#Set field separator for comma-delimiting.
for (i=1;i<=11;i++){
	getline<"HourlyTotalCounty.csv"								#Use getline function to input HourlyTotalCounty.csv data, and store parsed VMT totals into arrays, double-indexed by county and hour (Hour 1, Hour2...Hour 24) bins.
	for (j=1; j<=24;j++){
	     value1=j+2                                                       #Inputted data begins in column 3, while the hourly bins begin at Hour 1.  The value1 variable corrects for this difference as the data is inputted.
		if ($1~/alameda/){array["alameda",j]=$(value1)}                  #If the first column has a string with [respective county name] in it, save hourly VMT values to aptly-named arrays.
		if ($1~/contra/){array["contra",j]=$(value1)}
		if ($1~/marin/){array["marin",j]=$(value1)}
		if ($1~/napa/){array["napa",j]=$(value1)}
		if ($1~/francisco/){array["francisco",j]=$(value1)}
		if ($1~/mateo/){array["mateo",j]=$(value1)}
		if ($1~/clara/){array["clara",j]=$(value1)}
		if ($1~/solano/){array["solano",j]=$(value1)}
		if ($1~/sonoma/){array["sonoma",j]=$(value1)}
	}	
}
}														   

{
if (FILENAME~/alameda/){name="Alameda";aname="alameda";go=1;vmt_factor=0.87737696738371}     #Begin working with VMT share files.  Set "name" field by filename for later use in outputting files.
if (FILENAME~/contra/){name="ContraCosta";aname="contra";go=1;vmt_factor=1.10608357516879}   #Set "aname" field for naming first index or arrays.
if (FILENAME~/marin/){name="Marin";aname="marin";go=1;vmt_factor=0.949013075744836}          #"go" variable created so that operation below only runs when proper input files are found (a double-check on proper naming of input files).
if (FILENAME~/napa/){name="Napa";aname="napa";go=1;vmt_factor=1.39821735729013}              #Set VMT factor here to factor up VMT.  County VMT factors given by ARB.
if (FILENAME~/SF/){name="SanFrancisco";aname="francisco";go=1;vmt_factor=1.43635486896186}
if (FILENAME~/SM/){name="SanMateo";aname="mateo";go=1;vmt_factor=1.23934513985713}
if (FILENAME~/SC/){name="SantaClara";aname="clara";go=1;vmt_factor=1.02092617359035}
if (FILENAME~/solano/){name="Solano";aname="solano";go=1;vmt_factor=1.19346671684056}
if (FILENAME~/sonoma/){name="Sonoma";aname="sonoma";go=1;vmt_factor=1.11388919621506}


if (go==1){                                                                    								#Proceed only if one of the proper input files (identified above) was located.

	if (FNR==1 || FNR==15 || FNR==29){print $0>(name"FuelVehicle.csv")}        							#Print header rows for line numbers 1, 15, and 29 to respective county files.
		else{
			for (k=1;k<=25;k++){                                             							#If not line numbers 1, 15, or 29, create field counter to begin printing out results of VMT calculations.
			     value2=k-1																	#Outputted data begins in column 2, while the hourly bins begin at Hour1.  The value2 variable corrects for this difference as the data is outputted.
				if (k==1){printf("%s,", $k)>(name"FuelVehicle.csv")}        							#Print the first column (fuel type and vehicle class) to each county file.
				if (k>=2 && k<=24){printf("%.9f,",$k*array[aname,value2]*vmt_factor)>(name"FuelVehicle.csv")}	#Print data records, mulitplying vmt shares by total vmt (saved in arrays) and by vmt factor set above.
				if (k==25){printf("%.9f\n",$k*array[aname,value2]*vmt_factor)>(name"FuelVehicle.csv")}		#Print final record and carriage return		
			}
		}
}
go=0																#Reset "go" variable to 0.  
}


END{
system("gawk \"{if (NF>0){print $0}}\" *FuelVehicle.csv>RegionalVMT.csv")
}