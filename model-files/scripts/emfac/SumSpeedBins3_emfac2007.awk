# This script is needed for emfac 2007 only (not needed for emfac 2014 and 2017)
#This file creates a factor for growing the vehicle population files, using county VMT total ratios for project year and base year, and an EMFAC-generated factor 
#The output of this script is a unique file for each county, by vehicle population for each vehicle and fuel type
#Form for running this script is gawk -f sumspeedbins3.awk inp_vehpop*.csv
#SAI
#November 22, 2010


BEGIN{                                                                                      
IGNORECASE=1													#Make input case-insensitive.
FS=(",")														#Set field separator for comma-delimiting.
for (i=1;i<=11;i++){
	getline<"HourlyTotalCounty.csv"								#Use getline function to input HourlyTotalCounty.csv data, and sum VMT over 24 hour period.
	for (j=3; j<=26;j++){
	    	if ($1~/alameda/){alameda1+=$j}                                  #If the first column has a string with [respective county name] in it, sum 24 hourly values into single county total and store in [countyname]1 variable.
		if ($1~/contra/){contra1+=$j}
		if ($1~/marin/){marin1+=$j}
		if ($1~/napa/){napa1+=$j}
		if ($1~/francisco/){francisco1+=$j}
		if ($1~/mateo/){mateo1+=$j}
		if ($1~/clara/){clara1+=$j}
		if ($1~/solano/){solano1+=$j}
		if ($1~/sonoma/){sonoma1+=$j}
	}	
}
for (i=1;i<=11;i++){
	getline<"Inp_CtyTot_VMT.csv"
     if ($1~/alameda/){alameda2=$3;alameda3=$4}                                  #If the first column has a string with [respective county name] in it, save the base year county value into [countyname]2 variable.
	if ($1~/contra/){contra2=$3;contra3=$4}
	if ($1~/marin/){marin2=$3;marin3=$4}
	if ($1~/napa/){napa2=$3;napa3=$4}
	if ($1~/francisco/){francisco2=$3;francisco3=$4}
	if ($1~/mateo/){mateo2=$3;mateo3=$4}
	if ($1~/clara/){clara2=$3;clara3=$4}
	if ($1~/solano/){solano2=$3;solano3=$4}
	if ($1~/sonoma/){sonoma2=$3;sonoma3=$4}

}
alameda_factor=(alameda1/alameda2)/alameda3                                      #Create factors by county by dividing project year vmt by vmt from 05 base year, then dividing by EMFAC factor
contra_factor=(contra1/contra2)/contra3
marin_factor=(marin1/marin2)/marin3
napa_factor=(napa1/napa2)/napa3
francisco_factor=(francisco1/francisco2)/francisco3
mateo_factor=(mateo1/mateo2)/mateo3
clara_factor=(clara1/clara2)/clara3
solano_factor=(solano1/solano2)/solano3
sonoma_factor=(sonoma1/sonoma2)/sonoma3
}

{


if (FILENAME~/alameda/){
	if (FNR==1){print $0>"out_vehpop_Alameda.csv"}
	if (FNR>=2){printf("%s,%.9f,%.9f,%.9f\n",$1,$2*alameda_factor,$3*alameda_factor,$4*alameda_factor)>"out_vehpop_Alameda.csv"}       #Read in each county's vehicle population files, apply factor, and write out new files.
}

if (FILENAME~/contra/){
	if (FNR==1){print $0>"out_vehpop_ContraCosta.csv"}
	if (FNR>=2){printf("%s,%.9f,%.9f,%.9f\n",$1,$2*contra_factor,$3*contra_factor,$4*contra_factor)>"out_vehpop_ContraCosta.csv"}
}

if (FILENAME~/marin/){
	if (FNR==1){print $0>"out_vehpop_Marin.csv"}
	if (FNR>=2){printf("%s,%.9f,%.9f,%.9f\n",$1,$2*marin_factor,$3*marin_factor,$4*marin_factor)>"out_vehpop_Marin.csv"}
}

if (FILENAME~/napa/){
	if (FNR==1){print $0>"out_vehpop_Napa.csv"}
	if (FNR>=2){printf("%s,%.9f,%.9f,%.9f\n",$1,$2*napa_factor,$3*napa_factor,$4*napa_factor)>"out_vehpop_Napa.csv"}
}

if (FILENAME~/sf/){
	if (FNR==1){print $0>"out_vehpop_SF.csv"}
	if (FNR>=2){printf("%s,%.9f,%.9f,%.9f\n",$1,$2*francisco_factor,$3*francisco_factor,$4*francisco_factor)>"out_vehpop_SF.csv"}
}

if (FILENAME~/sm/){
	if (FNR==1){print $0>"out_vehpop_SM.csv"}
	if (FNR>=2){printf("%s,%.9f,%.9f,%.9f\n",$1,$2*mateo_factor,$3*mateo_factor,$4*mateo_factor)>"out_vehpop_SM.csv"}
}

if (FILENAME~/sc/){
	if (FNR==1){print $0>"out_vehpop_SC.csv"}
	if (FNR>=2){printf("%s,%.9f,%.9f,%.9f\n",$1,$2*clara_factor,$3*clara_factor,$4*clara_factor)>"out_vehpop_SC.csv"}
}

if (FILENAME~/solano/){
	if (FNR==1){print $0>"out_vehpop_Solano.csv"}
	if (FNR>=2){printf("%s,%.9f,%.9f,%.9f\n",$1,$2*solano_factor,$3*solano_factor,$4*solano_factor)>"out_vehpop_Solano.csv"}
}

if (FILENAME~/sonoma/){
	if (FNR==1){print $0>"out_vehpop_Sonoma.csv"}
	if (FNR>=2){printf("%s,%.9f,%.9f,%.9f\n",$1,$2*sonoma_factor,$3*sonoma_factor,$4*sonoma_factor)>"out_vehpop_Sonoma.csv"}
}

}


END{
}