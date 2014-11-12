#This file sums EMFAC output for two csv files (1. travel between zones and 2.travel within zones), by county and speed bin.
#The output of this script is two files: (1)a file with the sum of the two inputs; (2)the share of each speed bin relative to county totals; and (3)total vmt values collapsed to county and hourly bins
#Form for running this script is gawk -f sumspeedbins1.awk createspeedbins*.csv
#SAI
#October 19, 2010


BEGIN{                                                                                      
IGNORECASE=1													#Make input case-insensitive
FS=(",")													#Set field separator for comma-delimiting
}
														#Begin body step	    
{
if (FNR==1 && FILENAME~/BetweenZones/){print $0>"sumspeedbinsall_sums.csv";     				#Prints the header record from BetweenZones file to output file
	print $0>"sharespeedbinsall_sums.csv";
	for (p=1; p<=27; p++){if (p!=3){printf("%s,", $p)>"HourlyTotalCounty.csv"}                              #Print header (except for speed bin number) for HourlyTotalCounty.csv file
	if (p==27){printf "\n">"HourlyTotalCounty.csv"}
	}
	
	
	}

if (FNR>=2) {                                                                   				#Begins at record two for each input file
        
        if ($1~/alameda/){alameda1+=$4; alameda2+=$5; alameda3+=$6; alameda4+=$7; alameda5+=$8; alameda6+=$9;   #Start summing column totals by county
        alameda7+=$10; alameda8+=$11; alameda9+=$12; alameda10+=$13; alameda11+=$14; alameda12+=$15; 
        alameda13+=$16;alameda14+=$17;alameda15+=$18; alameda16+=$19; alameda17+=$20; alameda18+=$21; 
        alameda19+=$22; alameda20+=$23; alameda21+=$24; alameda22+=$25; alameda23+=$26; alameda24+=$27}
  
        if ($1~/contra/){contra1+=$4; contra2+=$5; contra3+=$6; contra4+=$7; contra5+=$8; contra6+=$9; 
        contra7+=$10; contra8+=$11; contra9+=$12; contra10+=$13; contra11+=$14; contra12+=$15; 
        contra13+=$16;contra14+=$17;contra15+=$18; contra16+=$19; contra17+=$20; contra18+=$21; 
        contra19+=$22; contra20+=$23; contra21+=$24; contra22+=$25; contra23+=$26; contra24+=$27}
        
        if ($1~/marin/){marin1+=$4; marin2+=$5; marin3+=$6; marin4+=$7; marin5+=$8; marin6+=$9; 
        marin7+=$10; marin8+=$11; marin9+=$12; marin10+=$13; marin11+=$14; marin12+=$15; 
        marin13+=$16;marin14+=$17;marin15+=$18; marin16+=$19; marin17+=$20; marin18+=$21; 
        marin19+=$22; marin20+=$23; marin21+=$24; marin22+=$25; marin23+=$26; marin24+=$27}
        
        if ($1~/napa/){napa1+=$4; napa2+=$5; napa3+=$6; napa4+=$7; napa5+=$8; napa6+=$9; 
        napa7+=$10; napa8+=$11; napa9+=$12; napa10+=$13; napa11+=$14; napa12+=$15; 
        napa13+=$16;napa14+=$17;napa15+=$18; napa16+=$19; napa17+=$20; napa18+=$21; 
        napa19+=$22; napa20+=$23; napa21+=$24; napa22+=$25; napa23+=$26; napa24+=$27}        
        
        if ($1~/francisco/){francisco1+=$4; francisco2+=$5; francisco3+=$6; francisco4+=$7; francisco5+=$8; francisco6+=$9; 
        francisco7+=$10; francisco8+=$11; francisco9+=$12; francisco10+=$13; francisco11+=$14; francisco12+=$15; 
        francisco13+=$16;francisco14+=$17;francisco15+=$18; francisco16+=$19; francisco17+=$20; francisco18+=$21; 
        francisco19+=$22; francisco20+=$23; francisco21+=$24; francisco22+=$25; francisco23+=$26; francisco24+=$27}
  
        if ($1~/mateo/){mateo1+=$4; mateo2+=$5; mateo3+=$6; mateo4+=$7; mateo5+=$8; mateo6+=$9; 
        mateo7+=$10; mateo8+=$11; mateo9+=$12; mateo10+=$13; mateo11+=$14; mateo12+=$15; 
        mateo13+=$16;mateo14+=$17;mateo15+=$18; mateo16+=$19; mateo17+=$20; mateo18+=$21; 
        mateo19+=$22; mateo20+=$23; mateo21+=$24; mateo22+=$25; mateo23+=$26; mateo24+=$27}
        
        if ($1~/clara/){clara1+=$4; clara2+=$5; clara3+=$6; clara4+=$7; clara5+=$8; clara6+=$9; 
        clara7+=$10; clara8+=$11; clara9+=$12; clara10+=$13; clara11+=$14; clara12+=$15; 
        clara13+=$16;clara14+=$17;clara15+=$18; clara16+=$19; clara17+=$20; clara18+=$21; 
        clara19+=$22; clara20+=$23; clara21+=$24; clara22+=$25; clara23+=$26; clara24+=$27}
        
        if ($1~/solano/){solano1+=$4; solano2+=$5; solano3+=$6; solano4+=$7; solano5+=$8; solano6+=$9; 
        solano7+=$10; solano8+=$11; solano9+=$12; solano10+=$13; solano11+=$14; solano12+=$15; 
        solano13+=$16;solano14+=$17;solano15+=$18; solano16+=$19; solano17+=$20; solano18+=$21; 
        solano19+=$22; solano20+=$23; solano21+=$24; solano22+=$25; solano23+=$26; solano24+=$27} 
        
        if ($1~/sonoma/){sonoma1+=$4; sonoma2+=$5; sonoma3+=$6; sonoma4+=$7; sonoma5+=$8; sonoma6+=$9; 
        sonoma7+=$10; sonoma8+=$11; sonoma9+=$12; sonoma10+=$13; sonoma11+=$14; sonoma12+=$15; 
        sonoma13+=$16;sonoma14+=$17;sonoma15+=$18; sonoma16+=$19; sonoma17+=$20; sonoma18+=$21; 
        sonoma19+=$22; sonoma20+=$23; sonoma21+=$24; sonoma22+=$25; sonoma23+=$26; sonoma24+=$27}
        
        if ($1~/external/){external1+=$4; external2+=$5; external3+=$6; external4+=$7; external5+=$8; external6+=$9; 
        external7+=$10; external8+=$11; external9+=$12; external10+=$13; external11+=$14; external12+=$15; 
        external13+=$16;external14+=$17;external15+=$18; external16+=$19; external17+=$20; external18+=$21; 
        external19+=$22; external20+=$23; external21+=$24; external22+=$25; external23+=$26; external24+=$27}         
        
        for (j=1;j<=27;j++){                                                    				#For columns 1-27, begin saving cell data into arrays called "between" and "within"
        	if (FILENAME~/BetweenZones/){between[FNR,j]=$j}                 				#Array value equal to cell value [FNR,j], where FNR=file record number and j comes from for statement
        	if (FILENAME~/WithinZones/){within[FNR,j]=$j}        		
		}
	    }
}

END{
alameda[1]=alameda1;alameda[2]=alameda2; alameda[3]=alameda3; alameda[4]=alameda4; alameda[5]=alameda5; alameda[6]=alameda6;                   #Make column totals for each county equal to array values.  This will facilitate automated array retrieval in next step.  
alameda[7]=alameda7;alameda[8]=alameda8; alameda[9]=alameda9; alameda[10]=alameda10; alameda[11]=alameda11; alameda[12]=alameda12;
alameda[13]=alameda13;alameda[14]=alameda14; alameda[15]=alameda15; alameda[16]=alameda16; alameda[17]=alameda17; alameda[18]=alameda18;
alameda[19]=alameda19;alameda[20]=alameda20; alameda[21]=alameda21; alameda[22]=alameda22; alameda[23]=alameda23; alameda[24]=alameda24;

contra[1]=contra1;contra[2]=contra2; contra[3]=contra3; contra[4]=contra4; contra[5]=contra5; contra[6]=contra6;
contra[7]=contra7;contra[8]=contra8; contra[9]=contra9; contra[10]=contra10; contra[11]=contra11; contra[12]=contra12;
contra[13]=contra13;contra[14]=contra14; contra[15]=contra15; contra[16]=contra16; contra[17]=contra17; contra[18]=contra18;
contra[19]=contra19;contra[20]=contra20; contra[21]=contra21; contra[22]=contra22; contra[23]=contra23; contra[24]=contra24;

marin[1]=marin1;marin[2]=marin2; marin[3]=marin3; marin[4]=marin4; marin[5]=marin5; marin[6]=marin6;
marin[7]=marin7;marin[8]=marin8; marin[9]=marin9; marin[10]=marin10; marin[11]=marin11; marin[12]=marin12;
marin[13]=marin13;marin[14]=marin14; marin[15]=marin15; marin[16]=marin16; marin[17]=marin17; marin[18]=marin18;
marin[19]=marin19;marin[20]=marin20; marin[21]=marin21; marin[22]=marin22; marin[23]=marin23; marin[24]=marin24;

napa[1]=napa1;napa[2]=napa2; napa[3]=napa3; napa[4]=napa4; napa[5]=napa5; napa[6]=napa6;
napa[7]=napa7;napa[8]=napa8; napa[9]=napa9; napa[10]=napa10; napa[11]=napa11; napa[12]=napa12;
napa[13]=napa13;napa[14]=napa14; napa[15]=napa15; napa[16]=napa16; napa[17]=napa17; napa[18]=napa18;
napa[19]=napa19;napa[20]=napa20; napa[21]=napa21; napa[22]=napa22; napa[23]=napa23; napa[24]=napa24;

francisco[1]=francisco1;francisco[2]=francisco2; francisco[3]=francisco3; francisco[4]=francisco4; francisco[5]=francisco5; francisco[6]=francisco6;
francisco[7]=francisco7;francisco[8]=francisco8; francisco[9]=francisco9; francisco[10]=francisco10; francisco[11]=francisco11; francisco[12]=francisco12;
francisco[13]=francisco13;francisco[14]=francisco14; francisco[15]=francisco15; francisco[16]=francisco16; francisco[17]=francisco17; francisco[18]=francisco18;
francisco[19]=francisco19;francisco[20]=francisco20; francisco[21]=francisco21; francisco[22]=francisco22; francisco[23]=francisco23; francisco[24]=francisco24;

mateo[1]=mateo1;mateo[2]=mateo2; mateo[3]=mateo3; mateo[4]=mateo4; mateo[5]=mateo5; mateo[6]=mateo6;
mateo[7]=mateo7;mateo[8]=mateo8; mateo[9]=mateo9; mateo[10]=mateo10; mateo[11]=mateo11; mateo[12]=mateo12;
mateo[13]=mateo13;mateo[14]=mateo14; mateo[15]=mateo15; mateo[16]=mateo16; mateo[17]=mateo17; mateo[18]=mateo18;
mateo[19]=mateo19;mateo[20]=mateo20; mateo[21]=mateo21; mateo[22]=mateo22; mateo[23]=mateo23; mateo[24]=mateo24;

clara[1]=clara1;clara[2]=clara2; clara[3]=clara3; clara[4]=clara4; clara[5]=clara5; clara[6]=clara6;
clara[7]=clara7;clara[8]=clara8; clara[9]=clara9; clara[10]=clara10; clara[11]=clara11; clara[12]=clara12;
clara[13]=clara13;clara[14]=clara14; clara[15]=clara15; clara[16]=clara16; clara[17]=clara17; clara[18]=clara18;
clara[19]=clara19;clara[20]=clara20; clara[21]=clara21; clara[22]=clara22; clara[23]=clara23; clara[24]=clara24;

solano[1]=solano1;solano[2]=solano2; solano[3]=solano3; solano[4]=solano4; solano[5]=solano5; solano[6]=solano6;
solano[7]=solano7;solano[8]=solano8; solano[9]=solano9; solano[10]=solano10; solano[11]=solano11; solano[12]=solano12;
solano[13]=solano13;solano[14]=solano14; solano[15]=solano15; solano[16]=solano16; solano[17]=solano17; solano[18]=solano18;
solano[19]=solano19;solano[20]=solano20; solano[21]=solano21; solano[22]=solano22; solano[23]=solano23; solano[24]=solano24;

sonoma[1]=sonoma1;sonoma[2]=sonoma2; sonoma[3]=sonoma3; sonoma[4]=sonoma4; sonoma[5]=sonoma5; sonoma[6]=sonoma6;
sonoma[7]=sonoma7;sonoma[8]=sonoma8; sonoma[9]=sonoma9; sonoma[10]=sonoma10; sonoma[11]=sonoma11; sonoma[12]=sonoma12;
sonoma[13]=sonoma13;sonoma[14]=sonoma14; sonoma[15]=sonoma15; sonoma[16]=sonoma16; sonoma[17]=sonoma17; sonoma[18]=sonoma18;
sonoma[19]=sonoma19;sonoma[20]=sonoma20; sonoma[21]=sonoma21; sonoma[22]=sonoma22; sonoma[23]=sonoma23; sonoma[24]=sonoma24;

external[1]=external1;external[2]=external2; external[3]=external3; external[4]=external4; external[5]=external5; external[6]=external6;
external[7]=external7;external[8]=external8; external[9]=external9; external[10]=external10; external[11]=external11; external[12]=external12;
external[13]=external13;external[14]=external14; external[15]=external15; external[16]=external16; external[17]=external17; external[18]=external18;
external[19]=external19;external[20]=external20; external[21]=external21; external[22]=external22; external[23]=external23; external[24]=external24;



for (i=2; i<=131; i++){                                                         						#Begin a loop starting at record two to output summed array values, the i value being the row index                                            
	for (j=1; j<=27; j++){                                                  						#Now set up loop for j, the column index
		combined=between[i,j]+within[i,j]; z=j-3; 									#The combined variable sums between and within matrices; the z variable makes column 4 equal to the first column of data, etc. (4-3=1, 5-3=2, etc.).
		if (j<4){printf ("%s,", between[i,j])>"sumspeedbinsall_sums.csv"} 						#Print first three columns of ID information (county, ARB county, speed bin) from BetweenZones file     
		if (j>=4 && j<27){printf ("%.2f,", combined)>"sumspeedbinsall_sums.csv"}     					#Print data to two decimal places, summing array values captured earlier
		if (j==27) {printf ("%.2f\n", combined)>"sumspeedbinsall_sums.csv"}          					#Print final sum and then the carriage return
        	
        		if (i>=2 && i<=14){        		            		        				#Begin printing the share of each speed bin, by county, to the sharespeedbinsall file.  First Alameda County, and so forth
        			if (j<4){printf ("%s,", between[i,j])>"sharespeedbinsall_sums.csv"}  				#Print first three columns of ID information (county, ARB county, speed bin) from BetweenZones file
        			if (j>=4 && j<27){printf ("%.4f,", combined/alameda[z])>"sharespeedbinsall_sums.csv"}     	#Print share data to four decimal places, divided from arrays captured earlier
        			if (j==27) {printf ("%.4f\n", combined/alameda[z])>"sharespeedbinsall_sums.csv"}          	#Print final share and then the carriage return
        			}
        		if (i>=15 && i<=27){ 	
         			if (j<4){printf ("%s,", between[i,j])>"sharespeedbinsall_sums.csv"}  				#Print first three columns of ID information (county, ARB county, speed bin) from BetweenZones file
        			if (j>=4 && j<27){printf ("%.4f,", combined/contra[z])>"sharespeedbinsall_sums.csv"}     	#Print share data to four decimal places, divided from arrays captured earlier
        			if (j==27) {printf ("%.4f\n", combined/contra[z])>"sharespeedbinsall_sums.csv"}          	#Print final share and then the carriage return
        			}
        		if (i>=28 && i<=40){ 	
         			if (j<4){printf ("%s,", between[i,j])>"sharespeedbinsall_sums.csv"}  				#Print first three columns of ID information (county, ARB county, speed bin) from BetweenZones file
        			if (j>=4 && j<27){printf ("%.4f,", combined/marin[z])>"sharespeedbinsall_sums.csv"}     	#Print share data to four decimal places, divided from arrays captured earlier								      
        			if (j==27) {printf ("%.4f\n", combined/marin[z])>"sharespeedbinsall_sums.csv"}          	#Print final share and then the carriage return
        			}
        		if (i>=41 && i<=53){ 	
         			if (j<4){printf ("%s,", between[i,j])>"sharespeedbinsall_sums.csv"}  				#Print first three columns of ID information (county, ARB county, speed bin) from BetweenZones file
        			if (j>=4 && j<27){printf ("%.4f,", combined/napa[z])>"sharespeedbinsall_sums.csv"}     	        #Print share data to four decimal places, divided from arrays captured earlier
        			if (j==27) {printf ("%.4f\n", combined/napa[z])>"sharespeedbinsall_sums.csv"}          	        #Print final share and then the carriage return
        			}
        		if (i>=54 && i<=66){ 	
         			if (j<4){printf ("%s,", between[i,j])>"sharespeedbinsall_sums.csv"}  				#Print first three columns of ID information (county, ARB county, speed bin) from BetweenZones file
        			if (j>=4 && j<27){printf ("%.4f,", combined/francisco[z])>"sharespeedbinsall_sums.csv"}     	#Print share data to four decimal places, divided from arrays captured earlier
        			if (j==27) {printf ("%.4f\n", combined/francisco[z])>"sharespeedbinsall_sums.csv"}          	#Print final share and then the carriage return
        			}
        		if (i>=67 && i<=79){ 	
         			if (j<4){printf ("%s,", between[i,j])>"sharespeedbinsall_sums.csv"}  				#Print first three columns of ID information (county, ARB county, speed bin) from BetweenZones file
        			if (j>=4 && j<27){printf ("%.4f,", combined/mateo[z])>"sharespeedbinsall_sums.csv"}     	#Print share data to four decimal places, divided from arrays captured earlier
        			if (j==27) {printf ("%.4f\n", combined/mateo[z])>"sharespeedbinsall_sums.csv"}          	#Print final share and then the carriage return
        			}
        		if (i>=80 && i<=92){ 	
         			if (j<4){printf ("%s,", between[i,j])>"sharespeedbinsall_sums.csv"}  				#Print first three columns of ID information (county, ARB county, speed bin) from BetweenZones file
        			if (j>=4 && j<27){printf ("%.4f,", combined/clara[z])>"sharespeedbinsall_sums.csv"}     	#Print share data to four decimal places, divided from arrays captured earlier
        			if (j==27) {printf ("%.4f\n", combined/clara[z])>"sharespeedbinsall_sums.csv"}          	#Print final share and then the carriage return
        			}
        		if (i>=93 && i<=105){ 	
         			if (j<4){printf ("%s,", between[i,j])>"sharespeedbinsall_sums.csv"}  				#Print first three columns of ID information (county, ARB county, speed bin) from BetweenZones file
        			if (j>=4 && j<27){printf ("%.4f,", combined/solano[z])>"sharespeedbinsall_sums.csv"}     	#Print share data to four decimal places, divided from arrays captured earlier
        			if (j==27) {printf ("%.4f\n", combined/solano[z])>"sharespeedbinsall_sums.csv"}          	#Print final share and then the carriage return
        			}
        		if (i>=106 && i<=118){ 	
         			if (j<4){printf ("%s,", between[i,j])>"sharespeedbinsall_sums.csv"}  				#Print first three columns of ID information (county, ARB county, speed bin) from BetweenZones file
        			if (j>=4 && j<27){printf ("%.4f,", combined/sonoma[z])>"sharespeedbinsall_sums.csv"}     	#Print share data to four decimal places, divided from arrays captured earlier
        			if (j==27) {printf ("%.4f\n", combined/sonoma[z])>"sharespeedbinsall_sums.csv"}          	#Print final share and then the carriage return
        			}
        		if (i>=119 && i<=131){ 	
         			if (j<4){printf ("%s,", between[i,j])>"sharespeedbinsall_sums.csv"}  				#Print first three columns of ID information (county, ARB county, speed bin) from BetweenZones file
        			if (j>=4 && j<27){printf ("%.4f,", combined/external[z])>"sharespeedbinsall_sums.csv"}     	#Print share data to four decimal places, divided from arrays captured earlier
        			if (j==27) {printf ("%.4f\n", combined/external[z])>"sharespeedbinsall_sums.csv"}          	#Print final share and then the carriage return
        			}    	
        		if ((i==14 || i==27 || i==40 || i==53 || i==66 || i==79 || i==92 || i==105 || i==118 || i==131) && j==27){   #Print placeholder 0s to work in EMFAC format.
				for (x=1;x<=5;x++){
					printf ("Placeholder,Placeholder,Placeholder,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,\
                                        %.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f\n",0,0,0,0,0,0,\
					0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)>"sharespeedbinsall_sums.csv"}
				}
        	}              
             } 
printf("Alameda,1,")>"HourlyTotalCounty.csv"; for (q=1;q<=24;q++){printf("%.2f,", alameda[q])>"HourlyTotalCounty.csv"};printf("\n")>"HourlyTotalCounty.csv"                      #Print out county totals for each hour to a new file, HourlyTotalCounty.csv
printf("Contra Costa,7,")>"HourlyTotalCounty.csv"; for (q=1;q<=24;q++){printf("%.2f,", contra[q])>"HourlyTotalCounty.csv"};printf("\n")>"HourlyTotalCounty.csv"
printf("Marin,21,")>"HourlyTotalCounty.csv"; for (q=1;q<=24;q++){printf("%.2f,", marin[q])>"HourlyTotalCounty.csv"};printf("\n")>"HourlyTotalCounty.csv"
printf("Napa,28,")>"HourlyTotalCounty.csv"; for (q=1;q<=24;q++){printf("%.2f,", napa[q])>"HourlyTotalCounty.csv"};printf("\n")>"HourlyTotalCounty.csv"
printf("San Francisco,38,")>"HourlyTotalCounty.csv"; for (q=1;q<=24;q++){printf("%.2f,", francisco[q])>"HourlyTotalCounty.csv"};printf("\n")>"HourlyTotalCounty.csv"
printf("San Mateo,41,")>"HourlyTotalCounty.csv"; for (q=1;q<=24;q++){printf("%.2f,", mateo[q])>"HourlyTotalCounty.csv"};printf("\n")>"HourlyTotalCounty.csv"
printf("Santa Clara,43,")>"HourlyTotalCounty.csv"; for (q=1;q<=24;q++){printf("%.2f,", clara[q])>"HourlyTotalCounty.csv"};printf("\n")>"HourlyTotalCounty.csv"
printf("Solano,48,")>"HourlyTotalCounty.csv"; for (q=1;q<=24;q++){printf("%.2f,", solano[q])>"HourlyTotalCounty.csv"};printf("\n")>"HourlyTotalCounty.csv"
printf("Sonoma,49,")>"HourlyTotalCounty.csv"; for (q=1;q<=24;q++){printf("%.2f,", sonoma[q])>"HourlyTotalCounty.csv"};printf("\n")>"HourlyTotalCounty.csv"
printf("External,9999,")>"HourlyTotalCounty.csv"; for (q=1;q<=24;q++){printf("%.2f,", external[q])>"HourlyTotalCounty.csv"}
}


