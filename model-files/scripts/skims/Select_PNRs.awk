# usage: gawk -f Select_PNRs.awk [-v type=express_bus|light_rail|ferry|heavy_rail|commuter_rail|all|walk] [-v period=EA|AM|MD|PM|EV]  XX_Transit_suplinks.dat > XX_Transit_suplinks_MOD.dat
# default type: walk

BEGIN{ 
  KEEP_PNRS=2
		
    # determine which files to read PNRs from
	if (type=="express_bus" || type=="all") {
		pnrFiles["../transitLines_express_bus.pnr"] = 1
	}
	if (type=="light_rail" || type=="all") {
		pnrFiles["../transitLines_light_rail.pnr"] = 1
	}
	if (type=="ferry" || type=="all") {
		pnrFiles["../transitLines_ferry.pnr"] = 1
	}
	if (type=="heavy_rail" || type=="all") {
		pnrFiles["../transitLines_heavy_rail.pnr"] = 1
	}
	if (type=="commuter_rail" || type=="all") {
		pnrFiles["../transitLines_commuter_rail.pnr"] = 1
	}
	if (type=="walk") {
	    # keep all walk links   
	}
	
	# determine which period to read distances from
	if (period=="EA" || period=="ea") {
		linkFile="EA_Transit_suplinks.dat"
	}
	if (period=="AM" || period=="am") {
		linkFile="AM_Transit_suplinks.dat"
	}
	if (period=="MD" || period=="md") {
		linkFile="MD_Transit_suplinks.dat"
	}
	if (period=="PM" || period=="pm") {
		linkFile="PM_Transit_suplinks.dat"
	}
	if (period=="EV" || period=="ev") {
		linkFile="EV_Transit_suplinks.dat"
	}
	
	print " " > "/dev/stderr"
	# create an array with the PNRs
	# PNR[node number] => 1    
	numPNRs=0
	for (pnrFile in pnrFiles) {
		curNumPNRs = 0
		while(getline <pnrFile> 0){
			if ($1=="PNR" && match($2,/NODE=([0-9 ]+)(-([0-9 ]+))?/,match_arr) != 0) {
				# print "[",match_arr[1],"]" > "/dev/stderr"
				PNR[match_arr[1]] = 1
				++curNumPNRs
				++numPNRs
			}
			else {
				# print "no match: ",$0 > "/dev/stderr"
			}
		}
		print "Read ",curNumPNRs," PNRS from",pnrFile > "/dev/stderr"
	}
    
    # One record for each input drive-access link
    # use distance, not time, because more stable across scenarios
	# dist[mode,taz,pnrNum] => dist
	#		      2 x 2376 x 49
	# fill this up with our first pass
    FIELDWIDTHS= "11 5 1 5 6 1 6 4 7 5 8 1 "
	while(getline <linkFile> 0) {
		two=$2
		four=$4
		sub(/^ */,"",two)
		sub(/^ */,"",four)
		if ($6==2) {
			dist[$6,two,four] = $8
		} else if ($6==7) {
			dist[$6,four,two] = $8
		} 
	}
	print "Found ",length(dist)," drive access links" > "/dev/stderr"

	#
	# Also, fill up the max travel time from each taz, for the allowed PNR types
	# (intitialized to zero)
	# maxdist[taz] => dist 
	#
	# now we sort them to know what to keep
	for (mode=1;mode<=9;++mode){
	if (mode==2 || mode==7) {
		for (taz=1;taz<=2376;++taz){
		
			# make a set of the travel times just for this taz
			delete tazDist
			for (pnr in PNR) {
				key = mode SUBSEP taz SUBSEP pnr
				# print "mode=", mode, "taz=", taz, "pnr=", pnr, "key=", key
				if (key in dist) {
					tazDist[key] = dist[key]
				}
			}
			
			# sort in order of travel time
			asort(tazDist,sortedTazDist)
							
		    	# if less than 2, keep them
			if (length(tazDist)<=KEEP_PNRS) {
				# print "Found ", length(tazDist), " PNRs for taz ",taz," for mode=",mode,"; dropping 0" 
				#keep the first two
				for (i=1;i<=KEEP_PNRS;++i) {				    
					for (key in tazDist) {
						# print key, "==>", tazDist[key]
						if (tazDist[key]==sortedTazDist[i]) {
							keepLines[key] = 1
							# print "Keeping ",key > "/dev/stderr"
						}
					}
				}								
			}
			
			# otherwise, keep the two shortest
			else {
				# print "Found ", length(tazDist), " PNRs for taz ",taz," for mode=",mode,"; dropping ",length(tazDist)-KEEP_PNRS > "/dev/stderr" 
				#keep the first two
				for (i=1;i<=KEEP_PNRS;++i) {				    
					for (key in tazDist) {
						# print key, "==>", tazDist[key]
						if (tazDist[key]==sortedTazDist[i]) {
							keepLines[key] = 1
							# print "Keeping ",key > "/dev/stderr"
						}
					}
				}				
				
				# drop the rest
				for (i=KEEP_PNRS+1;i<=length(tazDist);++i){
					# print i,"=>",sortedTazDist[i] > "/dev/stderr"
			
					# these are the ones to drop -- map it back and store 
					for (key in tazDist) {
						# print key, "==>", tazDist[key]
						if (tazDist[key]==sortedTazDist[i]) {
							dropLines[key] = 1
							del tazDist[key] # if the time is there twice, we will drop both
							# print "Dropping ",key > "/dev/stderr"
						}
					}
				}
			}			
		}
	}
	}
	totalLinks=0
	numDriveKept=0
	numWalkKept=0
}

# now, go through the whole list, dropping those that appear in the drop set
{
    totalLinks++
    
    # print all walk links, if type==walk
    if (type=="walk") {
        if ($6==2 || $6==7) {
            # do nothing
        } else {
            print $0
	    	numWalkKept++
        }
        
    # otherwise, print only PNR links
    } else {
	    if ($6==2 || $6==7) {
	    	two=$2
	    	four=$4
	    	sub(/^ */,"",two)
	    	sub(/^ */,"",four)
	    	
	    	thisDist = $8
	    	
	    	if ($6==2) {
	    		key = $6 SUBSEP two SUBSEP four
	    		thisTaz=two
	    	} else if ($6==7) {
	    		key = $6 SUBSEP four SUBSEP two
	    		thisTaz=four
	    	} 
	    	
	    	if (key in keepLines) {
	    		print $0
	    		numDriveKept++
	    	} else {
	    		# dropping! 
	    		# print "thisDist=",thisDist," bestDist=",bestDist[thisTaz]," Dropping",$0 > "/dev/stderr"
	    	} 
	    }
	    else {
	    	# not a PNR link
	    }
    }
    

}

END{    
    print "Found   ",totalLinks,   " total links" > "/dev/stderr"
	print "Kept    ",numDriveKept, " drive access links" > "/dev/stderr"
	print "Kept    ",numWalkKept,  " walk access links" > "/dev/stderr"
}
