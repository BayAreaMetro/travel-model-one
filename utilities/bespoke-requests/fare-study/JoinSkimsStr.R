JoinSkimsStr <- function(fullrun=FALSE, iter=4, sampleshare=0.5, logrun=FALSE, baufares=FALSE, ...) {
  
  library(tidyverse)
  library(readxl)
  library(openxlsx)
  library(reshape2)
  library(crayon)

  # Version 1 01 by Alex Mitrani, based on CoreSummaries.R by MTC staff, updated on 21 July 2021.  This function takes time and cost variables from the CSV files corresponding to the detailed skims and joins them on to the trips .rdata file.  
  # Version 1 02 by Alex Mitrani, added "..." to the command syntax so that the user can specify the list of variables from CSV skims files to be added to the trips data.  
  
  # Required subfolders of the root folder where this will be run:
  # "database"
  # "main" - only the files for the specified iteration are needed.  
  # "popsyn"
  # "landuse"
  # "CTRAMP\scripts\block"
  
  # Examples of use:
  # Use fullrun=TRUE if the code will be run in the original model directory and the rdata files do not yet exist in updated_outputs.  
  # 
  # If detailed distance skims are not available:
  # trips <- JoinSkimsStr(fullrun=TRUE, iter=4, sampleshare=0.5, logrun=TRUE, "walktime", "wait", "IVT", "transfers", "boardfare", "faremat", "xfare", "othercost", "distance")
  # 
  # If detailed distance skims are available:
  # trips <- JoinSkimsStr(fullrun=TRUE, iter=4, sampleshare=0.5, logrun=TRUE, "walktime", "wait", "IVT", "transfers", "boardfare", "faremat", "xfare", "othercost", "distance", "dFree", "dInterCity", "dLocal", "dRegional", "ddist", "dFareMat")
  
  
  # Utils
  
  
  now1 <- Sys.time()
  cat(yellow(paste0("JoinSkimsStr run started at ", now1, "\n \n")))  
  
  datestampr <- function(dateonly = FALSE, houronly = FALSE, minuteonly = FALSE, myusername = FALSE) {
    
    #General info
    now <- Sys.time()
    year <- format(now, "%Y")
    month <- format(now, "%m")
    day <- format(now, "%d")
    hour <- format(now, "%H")
    minute <- format(now, "%M")
    second <- format(now, "%S")
    username <- Sys.getenv("USERNAME")
    
    # Work --------------------------------------------------------------------
    
    
    if (nchar(day)==2) {
      
      day <- day
      
    } else {
      
      day <- paste0("0",day)
      
    }
    
    if (nchar(month)==2) {
      
      month <- month
      
    } else {
      
      month <- paste0("0",month)
      
    }
    
    if (myusername == TRUE) {
      
      if (dateonly == TRUE) {
        
        datestampr <- paste0(year,month,day,username)
        
      } else if (houronly == TRUE) {
        
        datestampr <- paste0(year,month,day,hour,username)
        
      } else if (minuteonly == TRUE) {
        
        datestampr <- paste0(year,month,day,hour,minute,username)
        
      } else {
        
        datestampr <- paste0(year,month,day,hour,minute,second,username)
        
      }
      
    } else {
      
      if (dateonly == TRUE) {
        
        datestampr <- paste0(year,month,day)
        
      } else if (houronly == TRUE) {
        
        datestampr <- paste0(year,month,day,hour)
        
      } else if (minuteonly == TRUE) {
        
        datestampr <- paste0(year,month,day,hour,minute)
        
      } else {
        
        datestampr <- paste0(year,month,day,hour,minute,second)
        
      }
      
    }
    
    return(datestampr)
    
  }
  
  dropr <- function(mydf,...) {
    
    my_return_name <- deparse(substitute(mydf))
    
    myinitialsize <- round(object.size(mydf)/1000000, digits = 3)
    cat(paste0("Size of ", my_return_name, " before removing variables: ", myinitialsize, " MB. \n"))
    
    names_to_drop <- c(...)
    mytext <- paste("The following variables will be dropped from ", my_return_name, ": ", sep = "")
    print(mytext)
    print(names_to_drop)
    mydf <- mydf[,!names(mydf) %in% names_to_drop]
    
    myfinalsize <- round(object.size(mydf)/1000000, digits = 3)
    cat(paste0("Size of ", my_return_name, " after removing variables: ", myfinalsize, " MB. \n"))
    ramsaved <- round(myinitialsize - myfinalsize, digits = 3)
    cat(paste0("RAM saved: ", ramsaved, " MB. \n"))
    
    return(mydf)
    
  }	
  

	# Core Summaries

	# Overhead
  
  if (logrun==TRUE) {
  
    datestring <- datestampr(myusername=TRUE)
    mylogfilename <- paste0("JoinSkimsStr_", datestring,".txt")
    sink()
    sink(mylogfilename, split=TRUE)
    cat(yellow(paste0("A log of the output will be saved to ", mylogfilename, ". \n \n")))
    
  }
	
	mywd <- getwd()
	
	# For RStudio, these can be set in the .Rprofile
	TARGET_DIR   <- mywd  		# The location of the input files
	ITER         <- iter        # The iteration of model outputs to read
	SAMPLESHARE  <- sampleshare # Sampling
	
	TARGET_DIR   <- gsub("\\\\","/",TARGET_DIR) # switch slashes around
	
	stopifnot(nchar(TARGET_DIR  )>0)
	stopifnot(nchar(ITER        )>0)
	stopifnot(nchar(SAMPLESHARE )>0)
	
	
	MAIN_DIR    <- file.path(TARGET_DIR,"main"           )
	RESULTS_DIR <- file.path(TARGET_DIR,"core_summaries")
	UPDATED_DIR <- file.path(TARGET_DIR,"updated_output")

	
if (fullrun==TRUE) {
	


		# read means-based cost factors
		MBT_factors <- readLines(file.path(TARGET_DIR,"ctramp/scripts/block/hwyParam.block"))
		MBF_factors <- readLines(file.path(TARGET_DIR,"ctramp/scripts/block/trnParam.block"))

		MBT_Q1_line <- grep("Means_Based_Tolling_Q1Factor",MBT_factors,value=TRUE)
		MBT_Q1_string <- substr(MBT_Q1_line,32,39)
		MBT_Q1_factor <- as.numeric(MBT_Q1_string)
		MBT_Q2_line <- grep("Means_Based_Tolling_Q2Factor",MBT_factors,value=TRUE)
		MBT_Q2_string <- substr(MBT_Q2_line,32,39)
		MBT_Q2_factor <- as.numeric(MBT_Q2_string)

		MBF_Q1_line <- grep("Means_Based_Fare_Q1Factor",MBF_factors,value=TRUE)
		MBF_Q1_string <- substr(MBF_Q1_line,29,36)
		MBF_Q1_factor <- as.numeric(MBF_Q1_string)
		MBF_Q2_line <- grep("Means_Based_Fare_Q2Factor",MBF_factors,value=TRUE)
		MBF_Q2_string <- substr(MBF_Q2_line,29,36)
		MBF_Q2_factor <- as.numeric(MBF_Q2_string)


		# write results in TARGET_DIR/core_summaries
		if (!file.exists(RESULTS_DIR)) {
		  dir.create(RESULTS_DIR)
		}
		# write tables in TARGET_DIR/updated_output
		if (!file.exists(UPDATED_DIR)) {
		  dir.create(UPDATED_DIR)
		}
		SAMPLESHARE <- as.numeric(SAMPLESHARE)

		cat("TARGET_DIR  = ",TARGET_DIR, "\n")
		cat("ITER        = ",ITER,       "\n")
		cat("SAMPLESHARE = ",SAMPLESHARE,"\n")

		# Overhead
		## Lookups

		# For time periods, see https://github.com/BayAreaMetro/modeling-website/wiki/TimePeriods
		# For counties, see https://github.com/BayAreaMetro/modeling-website/wiki/TazData
		# For walk_subzones, see https://github.com/BayAreaMetro/modeling-website/wiki/Household

		######### time periods
		LOOKUP_TIMEPERIOD    <- data.frame(timeCodeNum=c(1,2,3,4,5),
										   timeperiod_label=c("Early AM","AM Peak","Midday","PM Peak","Evening"),
										   timeperiod_abbrev=c("EA","AM","MD","PM","EV"))
		# no factors -- joins don't work
		LOOKUP_TIMEPERIOD$timeCodeNum       <- as.integer(LOOKUP_TIMEPERIOD$timeCodeNum)
		LOOKUP_TIMEPERIOD$timeperiod_label  <- as.character(LOOKUP_TIMEPERIOD$timeperiod_label)
		LOOKUP_TIMEPERIOD$timeperiod_abbrev <- as.character(LOOKUP_TIMEPERIOD$timeperiod_abbrev)

		######### counties
		LOOKUP_COUNTY        <- data.frame(COUNTY=c(1,2,3,4,5,6,7,8,9),
										   county_name=c("San Francisco","San Mateo","Santa Clara","Alameda",
														 "Contra Costa","Solano","Napa","Sonoma","Marin"))
		LOOKUP_COUNTY$COUNTY      <- as.integer(LOOKUP_COUNTY$COUNTY)
		LOOKUP_COUNTY$county_name <- as.character(LOOKUP_COUNTY$county_name)

		######### walk subzones
		LOOKUP_WALK_SUBZONE  <- data.frame(walk_subzone=c(0,1,2),
										   walk_subzone_label=c("Cannot walk to transit (more than two-thirds of a mile away)",
																"Short-walk to transit (less than one-third of a mile)",
																"Long-walk to transit (between one-third and two-thirds of a mile)"))
		LOOKUP_WALK_SUBZONE$walk_subzone <- as.integer(LOOKUP_WALK_SUBZONE$walk_subzone)

		######### person types
		LOOKUP_PTYPE         <- data.frame(ptype=c(1,2,3,4,5,6,7,8),
										   ptype_label=c("Full-time worker","Part-time worker","College student","Non-working adult",
														 "Retired","Driving-age student","Non-driving-age student",
														 "Child too young for school"))
		LOOKUP_PTYPE$ptype   <- as.integer(LOOKUP_PTYPE$ptype)
		
		# Data Reads: Land Use

		# The land use file: https://github.com/BayAreaMetro/modeling-website/wiki/TazData
		tazData           <- read.table(file=file.path(TARGET_DIR,"landuse","tazData.csv"), header=TRUE, sep=",")
		names(tazData)    <- toupper(names(tazData))
		tazData           <- select(tazData, ZONE, SD, COUNTY, PRKCST, OPRKCST)
		tazData           <- left_join(tazData, LOOKUP_COUNTY, by=c("COUNTY"))
		names(tazData)[names(tazData)=="ZONE"] <- "taz"


		# Data Reads: Household files

		## Read the household files and land use file

		# There are two household files:

		# * the model input file from the synthesized household/population (https://github.com/BayAreaMetro/modeling-website/wiki/PopSynHousehold)
		# * the model output file (https://github.com/BayAreaMetro/modeling-website/wiki/Household)

		input.pop.households <- read.table(file = file.path(TARGET_DIR,"popsyn","hhFile.csv"),
										   header=TRUE, sep=",")
		input.ct.households  <- read.table(file = file.path(MAIN_DIR,paste0("householdData_",ITER,".csv")),
										   header=TRUE, sep = ",")

		## Join them

		# Rename/drop some columns and join them on household id. Also join with tazData to get the super district and county.

		# drop random number fields
		input.ct.households  <- select(input.ct.households, -ao_rn, -fp_rn, -cdap_rn,
		  -imtf_rn, -imtod_rn, -immc_rn, -jtf_rn, -jtl_rn, -jtod_rn, -jmc_rn, -inmtf_rn,
		  -inmtl_rn, -inmtod_rn, -inmmc_rn, -awf_rn, -awl_rn, -awtod_rn, -awmc_rn, -stf_rn, -stl_rn)

		# in case households aren't numeric - make the columns numeric
		for(i in names(input.pop.households)){
		  input.pop.households[[i]] <- as.numeric(input.pop.households[[i]])
		}

		# rename
		names(input.pop.households)[names(input.pop.households)=="HHID"] <- "hh_id"

		households <- inner_join(input.pop.households, input.ct.households)
		households <- inner_join(households, tazData)
		# wrap as a d data frame tbl so it's nicer for printing
		households <- as_tibble(households)
		# clean up
		remove(input.pop.households, input.ct.households)
		print(paste("Read household files; have",prettyNum(nrow(households),big.mark=","),"rows"))

		## Recode a few new variables

		# Create the following new household variables:
		#  * income quartiles (`incQ`)
		#  * worker categories (`workers`)
		#  * dummy for households with children that don't drive (`kidsNoDr`)
		#  * auto sufficiency (`autoSuff`)
		#  * walk subzone label (`walk_subzone_label`)

		# incQ are Income Quartiles
		LOOKUP_INCQ          <- data.frame(incQ=c(1,2,3,4),
										   incQ_label=c("Less than $30k","$30k to $60k","$60k to $100k","More than $100k"))
		LOOKUP_INCQ$incQ     <- as.integer(LOOKUP_INCQ$incQ)

		households    <- mutate(households, incQ=1*(income<30000) +
												 2*((income>=30000)&(income<60000)) +
												 3*((income>=60000)&(income<100000)) +
												 4*(income>=100000))
		# households    <- left_join(households, LOOKUP_INCQ, by=c("incQ"))
		households    <- left_join(households, LOOKUP_INCQ)

		# workers are hworkers capped at 4
		households    <- mutate(households, workers=4*(hworkers>=4) + hworkers*(hworkers<4))
		WORKER_LABELS <- c("Zero", "One", "Two", "Three", "Four or more")

		# auto sufficiency
		LOOKUP_AUTOSUFF          <- data.frame(autoSuff=c(0,1,2),
										autoSuff_label=c("Zero automobiles","Automobiles < workers","Automobiles >= workers"))
		LOOKUP_AUTOSUFF$autoSuff <- as.integer(LOOKUP_AUTOSUFF$autoSuff)

		households    <- mutate(households, autoSuff=1*((autos>0)&(autos<hworkers)) +
													 2*((autos>0)&(autos>=hworkers)))
		# households    <- left_join(households, LOOKUP_AUTOSUFF, by=c("autoSuff"))
		households    <- left_join(households, LOOKUP_AUTOSUFF)

		# walk subzone label
		# households    <- left_join(households, LOOKUP_WALK_SUBZONE, by=c("walk_subzone"))
		households    <- left_join(households, LOOKUP_WALK_SUBZONE)

		# Data Reads: Person files

		# There are two person files:
		# * the model input file from the synthesized household/population (https://github.com/BayAreaMetro/modeling-website/wiki/PopSynPerson)
		# * the model output file (https://github.com/BayAreaMetro/modeling-website/wiki/Person)

		## Read the person files
		input.pop.persons    <- read.table(file = file.path(TARGET_DIR,"popsyn","personFile.csv"),
										   header=TRUE, sep=",")
		input.ct.persons     <- read.table(file = file.path(MAIN_DIR,paste0("personData_",ITER,".csv")),
										   header=TRUE, sep = ",")

		## Join them

		# Rename
		names(input.pop.persons)[names(input.pop.persons)=="HHID"] <- "hh_id"
		names(input.pop.persons)[names(input.pop.persons)=="PERID"] <- "person_id"

		# in case households aren't numeric - make the columns numeric
		for(i in names(input.pop.persons)){
		  input.pop.persons[[i]] <- as.numeric(input.pop.persons[[i]])
		}

		# Inner join so persons must be present in both.  So only simulated persons stay.
		# persons              <- inner_join(input.pop.persons, input.ct.persons, by=c("hh_id", "person_id"))
		persons              <- inner_join(input.pop.persons, input.ct.persons)
		# Get incQ from Households
		# persons              <- left_join(persons, select(households, hh_id, incQ, incQ_label), by=c("hh_id"))
		persons              <- left_join(persons, select(households, hh_id, incQ, incQ_label))

		# Person type label
		# persons              <- left_join(persons, LOOKUP_PTYPE, by=c("ptype"))
		persons              <- left_join(persons, LOOKUP_PTYPE)

		# wrap as a d data frame tbl so it's nicer for printing
		persons              <- as_tibble(persons)
		# clean up
		remove(input.pop.persons, input.ct.persons)
		print(paste("Read persons files; have",prettyNum(nrow(persons),big.mark=","), "rows"))


		# kidsNoDr is 1 if the household has children in the household that don't drive (pre-school age or school age)
		# calculate for persons and transfer to households as a binary
		persons              <- mutate(persons, kidsNoDr=ifelse((ptype==7)|(ptype==8),1,0))
		kidsNoDr_hhlds       <- summarise(group_by(select(persons, hh_id, kidsNoDr), hh_id), kidsNoDr=max(kidsNoDr))
		households           <- left_join(households, kidsNoDr_hhlds)
		remove(kidsNoDr_hhlds)

		# Tours

		## Read Individual Tours

		# The fields are documented here: https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour

		indiv_tours     <- as_tibble(read.table(file=file.path(MAIN_DIR, paste0("indivTourData_",ITER,".csv")),
											 header=TRUE, sep=","))
		indiv_tours     <- mutate(indiv_tours, tour_id=paste0("i",substr(tour_purpose,1,4),tour_id))

		# Add income from household table
		# indiv_tours     <- left_join(indiv_tours, select(households, hh_id, income, incQ, incQ_label), by=c("hh_id"))
		indiv_tours     <- left_join(indiv_tours, select(households, hh_id, income, incQ, incQ_label))
		indiv_tours     <- mutate(indiv_tours, num_participants=1)

		# Add in County, Superdistrict, Parking Cost from TAZ Data for the tour destination
		indiv_tours     <- left_join(indiv_tours,
									 mutate(tazData, dest_taz=taz, dest_COUNTY=COUNTY, dest_county_name=county_name,
											dest_SD=SD, PRKCST, OPRKCST) %>%
									   select(dest_taz, dest_COUNTY, dest_county_name, dest_SD, PRKCST, OPRKCST))
		# 							 by=c("dest_taz"))

		# Add free-parking choice from persons table
		# indiv_tours   <- left_join(indiv_tours, select(persons, person_id, fp_choice), by=c("person_id"))
		indiv_tours   <- left_join(indiv_tours, select(persons, person_id, fp_choice))

		# Compute the tour parking rate
		indiv_tours   <- mutate(indiv_tours, parking_rate=ifelse(tour_category=='MANDATORY',PRKCST,OPRKCST))

		# Free parking for work tours if fp_choice==1
		indiv_tours   <- mutate(indiv_tours, parking_rate=ifelse((substr(tour_purpose,0,4)=='work')*(fp_choice==1),0.0,parking_rate))

		## Data Reads: Joint Tours

		# The fields are documented here: https://github.com/BayAreaMetro/modeling-website/wiki/JointTour

		joint_tours    <- as_tibble(read.table(file=file.path(MAIN_DIR, paste0("jointTourData_",ITER,".csv")),
											header=TRUE, sep=","))
		joint_tours     <- mutate(joint_tours, tour_id=paste0("j",substr(tour_purpose,1,4),tour_id))

		# Add Income from household table
		# joint_tours    <- left_join(joint_tours, select(households, hh_id, income, incQ, incQ_label), by=c("hh_id"))
		joint_tours    <- left_join(joint_tours, select(households, hh_id, income, incQ, incQ_label))

		# Add in County, Superdistrict, Parking Cost from TAZ Data for the tour destination
		joint_tours     <- left_join(joint_tours,
									 mutate(tazData, dest_taz=taz, dest_COUNTY=COUNTY, dest_county_name=county_name,
											dest_SD=SD, PRKCST, OPRKCST) %>%
									   select(dest_taz, dest_COUNTY, dest_county_name, dest_SD, PRKCST, OPRKCST))
									 # by=c("dest_taz"))

		# Add parking rate
		joint_tours    <- mutate(joint_tours, parking_rate=OPRKCST)
		
		# Data Reads: Trips

		## Read Individual Trips and recode a few variables

		# The fields are documented here: https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip

		indiv_trips     <- read.table(file=file.path(MAIN_DIR, paste0("indivTripData_",ITER,".csv")), header=TRUE, sep=",")
		indiv_trips     <- select(indiv_trips, hh_id, person_id, person_num, tour_id, orig_taz, orig_walk_segment, dest_taz, dest_walk_segment,
								  trip_mode, tour_purpose, orig_purpose, dest_purpose, depart_hour, stop_id, tour_category, avAvailable, sampleRate, inbound) %>%
						   mutate(tour_id = paste0("i",substr(tour_purpose,1,4),tour_id))
		print(paste("Read",prettyNum(nrow(indiv_trips),big.mark=","),"individual trips"))

		## Data Reads: Joint Trips and recode a few variables

		# The fields are documented here: https://github.com/BayAreaMetro/modeling-website/wiki/JointTrip
		joint_trips     <- as_tibble(read.table(file=file.path(MAIN_DIR, paste0("jointTripData_",ITER,".csv")), header=TRUE, sep=","))
		joint_trips     <- select(joint_trips, hh_id, tour_id, orig_taz, orig_walk_segment, dest_taz, dest_walk_segment, trip_mode, num_participants, tour_purpose, orig_purpose, dest_purpose, depart_hour, stop_id, tour_category, avAvailable, sampleRate, inbound) %>%
						            mutate(tour_id = paste0("j",substr(tour_purpose,1,4),tour_id))

		print(paste("Read",prettyNum(nrow(joint_trips),big.mark=","),
					"joint trips or ",prettyNum(sum(joint_trips$num_participants),big.mark=","),
					"joint person trips"))

		## Add `num_participants` to joint_tours
		joint_tours     <- left_join(joint_tours, unique(select(joint_trips, hh_id, tour_id, num_participants)))
# 									 by=c("hh_id","tour_id"))

		## Combine individual tours and joint tours together, keeping person_id, person_num, tour_participants for both
		tours <- rbind(select(mutate(indiv_tours, tour_participants=as.character(person_num)), -person_type, -atWork_freq),
					   select(mutate(joint_tours, person_id=0, person_num=0, fp_choice=0), -tour_composition))
		print(paste("Combined indiv_tours (",prettyNum(nrow(indiv_tours),big.mark=","),"rows ) and joint_tours (",
			  prettyNum(nrow(joint_tours),big.mark=","),"rows) into",
			  prettyNum(nrow(tours),big.mark=","),"tours with columns",toString(colnames(tours))))
		print(head(select(tours,hh_id,person_id,person_num,tour_id,num_participants,tour_participants),10))
		print(tail(select(tours,hh_id,person_id,person_num,tour_id,num_participants,tour_participants),10))


		# add residence TAZ info
		tours <- left_join(tours, select(households, hh_id, taz, SD, COUNTY, county_name))
						   # by=c("hh_id"))

		# add simple_purpose, duration, parking cost to tours table
		add_tour_attrs <- function(ftours) {
		  # add simple_purpose
		  ftours <- mutate(ftours, simple_purpose='non-work')
		  ftours$simple_purpose[ftours$tour_purpose=='work_low'       ] <- 'work'
		  ftours$simple_purpose[ftours$tour_purpose=='work_med'       ] <- 'work'
		  ftours$simple_purpose[ftours$tour_purpose=='work_high'      ] <- 'work'
		  ftours$simple_purpose[ftours$tour_purpose=='work_very high' ] <- 'work'

		  ftours$simple_purpose[ftours$tour_purpose=='school_grade'   ] <- 'school'
		  ftours$simple_purpose[ftours$tour_purpose=='school_high'    ] <- 'school'

		  ftours$simple_purpose[ftours$tour_purpose=='university'     ] <- 'college'

		  ftours$simple_purpose[ftours$tour_purpose=='atwork_business'] <- 'at work'
		  ftours$simple_purpose[ftours$tour_purpose=='atwork_eat'     ] <- 'at work'
		  ftours$simple_purpose[ftours$tour_purpose=='atwork_maint'   ] <- 'at work'

		  # Calculate the duration consistently with MtcModeChoiceDMU.java
		  # https://github.com/BayAreaMetro/travel-model-one/blob/15dc6cdfd04e828cf319c21a4b7077ad3c7ca3e6/core/projects/mtc/src/java/com/pb/mtc/ctramp/MtcModeChoiceDMU.java#L83
		  ftours   <- mutate(ftours, duration=end_hour-start_hour+1.0)

		  # Parking cost is based on tour duration
		  ftours   <- mutate(ftours, parking_cost=parking_rate*duration)
		  # Distribute costs across shared ride modes (same value used in skims, assignment) for indiv tours
		  ftours   <- mutate(ftours,
							 parking_cost=ifelse((num_participants==1)&((tour_mode==3)|(tour_mode==4)),
												parking_cost/1.75,parking_cost))
		  ftours   <- mutate(ftours,
							 parking_cost=ifelse((num_participants==1)&((tour_mode==5)|(tour_mode==6)),
												 parking_cost/2.50,parking_cost))
		  # Set the transit parking cost to zero
		  ftours   <- mutate(ftours, parking_cost=ifelse(tour_mode>6,0.0,parking_cost))
		  return(ftours)
		}

		tours <- add_tour_attrs(tours)

		## Convert joint trips to joint person trips

		# Getting the tour participants person nums from the joint_tours table, and unwind it so that each joint tour
		# becomes a row per partipant.  
		# Inputs: joint_tours has columns tour_participants, hh_id, tour_id
		#         persons has hh_id, person_num, person_id
		# Returns table of person-tours, with columns hh_id, tour_id, tour_participants person_num, person_id
		get_joint_tour_persons <- function(joint_tours, persons) {
		  # tour participants are person ids separated by spaces -- create a table of hh_id, person_num for them
		  joint_tour_persons <- data.frame(hh_id=numeric(), tour_id=numeric(), person_num=numeric())
		  # unwind particpants into table with cols hh_id, tour_id, person_num1, person_num2, ...
		  participants   <- strsplit(as.character(joint_tours$tour_participants)," ")
		  max_peeps      <- max(sapply(participants,length))
		  participants   <- lapply(participants, function(X) c(X,rep(NA, max_peeps-length(X))))
		  participants   <- data.frame(t(do.call(cbind, participants)))
		  participants   <- mutate(participants, hh_id=joint_tours$hh_id, tour_id=joint_tours$tour_id, tour_participants=joint_tours$tour_participants)
		  print("get_join_tour_persons; head(participants):")
		  print(head(participants))
		  # melt the persons so they are each on their own row
		  for (peep in 1:max_peeps) {
			jtp <- melt(participants, id.var=c("hh_id","tour_id","tour_participants"), measure.vars=paste0("X",peep), na.rm=TRUE)
			jtp <- mutate(jtp, person_num=value)
			jtp <- select(jtp, hh_id, tour_id, tour_participants, person_num)
			joint_tour_persons <- rbind(joint_tour_persons, jtp)
		  }
		  joint_tour_persons <- transform(joint_tour_persons, person_num=as.numeric(person_num))
		  # sort by hh_id
		  joint_tour_persons <- joint_tour_persons[with(joint_tour_persons, order(hh_id, tour_participants, tour_id)),]
		  # merge with the persons to get the person_id
		  joint_tour_persons <- left_join(joint_tour_persons, select(persons, hh_id, person_num, person_id), by=c("hh_id","person_num"))

		  print("get_join_tour_persons; head(joint_tour_persons):")
		  print(head(joint_tour_persons))
		  return(joint_tour_persons)
		}

		joint_tour_persons <- get_joint_tour_persons(joint_tours, persons)

		# attach persons to the joint_trips
		# joint_person_trips <- inner_join(joint_trips, joint_tour_persons, by=c("hh_id", "tour_id"))
		joint_person_trips <- inner_join(joint_trips, joint_tour_persons)
		# select out person_num and the person table columns
		#joint_person_trips <- select(joint_person_trips, hh_id, person_id, tour_id, tour_participants, orig_taz, dest_taz, trip_mode,
		#                             num_participants, tour_purpose, orig_purpose, dest_purpose, depart_hour, stop_id, avAvailable, sampleRate, inbound)

		print(paste("Created joint_person_trips with",prettyNum(nrow(joint_person_trips),big.mark=","),"rows from",
			  prettyNum(nrow(joint_trips),big.mark=","),"rows from joint_trips and",
			  prettyNum(nrow(joint_tour_persons),big.mark=","),"rows from joint_tour_persons"))

		# cleanup
		remove(joint_trips,joint_tour_persons)

		## Combine Individual Trips and Joint Person Trips
		indiv_trips <- mutate(indiv_trips, num_participants=1, tour_participants=as.character(person_num))
		print(toString(colnames(joint_person_trips)))
		print(toString(colnames(indiv_trips)))
		trips <- as_tibble(rbind(indiv_trips, joint_person_trips))
		print(paste("Combined",prettyNum(nrow(indiv_trips),big.mark=","),
					"individual trips with",prettyNum(nrow(joint_person_trips),big.mark=","),
					"joint trips to make",prettyNum(nrow(trips),big.mark=",")," total trips with columns",toString(colnames(trips))))

		remove(indiv_trips,joint_person_trips)

		## Add Variables to Trips

		# Add some variable to trips, such as:
		#   * `timeCode`, a recoding of the `depart_hour` for joining skims
		#   * `home_taz` from household table
		#   * `incQ` and label from the household table
		#   * `autoSuff` and label from the household table
		#   * `walk_subzone` and label from the household table
		#   * `ptype` and label, `fp_choice` from persons

		trips <- mutate(trips,
						timeCodeNum=1*(depart_hour<6) +                                       # EA
									2*((depart_hour>5)&(depart_hour<10)) +                    # AM
									3*((depart_hour>9)&(depart_hour<15)) +                    # MD
									4*((depart_hour>14)&(depart_hour<19)) +                   # PM
									5*((depart_hour>18))                                      # EV
						)
		# trips <- left_join(trips, LOOKUP_TIMEPERIOD, by=c("timeCodeNum"))
		trips <- left_join(trips, LOOKUP_TIMEPERIOD)
		trips <- select(mutate(trips, timeCode=timeperiod_abbrev), -timeperiod_abbrev)
		trips <- left_join(trips,
						   mutate(households, home_taz=taz) %>%
							 select(hh_id, incQ, incQ_label, autoSuff, autoSuff_label,
									home_taz, walk_subzone, walk_subzone_label))
						   # by=c("hh_id"))
		trips <- left_join(trips,
						   select(persons, hh_id, person_id, ptype, ptype_label, fp_choice))
						   # by=c("hh_id","person_id"))
		
		# need to reconcile this...
		
		# trip_mode	trip_mode_name
		# 1	Drive alone (single-occupant vehicles), not eligibile to use value toll facilities
		# 2	Drive alone (single-occupant), eligible to use value toll facilities
		# 3	Shared ride 2 (two-occupant vehicles), not eligibile to use value toll facilities
		# 4	Shared ride 2 (two-occupant vehicles), eligible to use value toll facilities
		# 5	Shared ride 3+ (three-or-more-occupant vehicles), not eligibile to use value toll facilities
		# 6	Shared ride 3+ (three-of-more occupant vehicles), eligible to use value toll facilities
		# 7	Walk the entire way (no transit, no bicycle)
		# 8	Bicycle the entire way (no transit)
		# 9	Walk to local bus
		# 10	Walk to light rail or ferry
		# 11	Walk to express bus
		# 12	Walk to heavy rail
		# 13	Walk to commuter rail
		# 14	Drive to local bus
		# 15	Drive to light rail or ferry
		# 16	Drive to express bus
		# 17	Drive to heavy rail
		# 18	Drive to commuter rail
		# 19	Taxi (added in Travel Model 1.5)
		# 20	TNC (Transportation Network Company, or ride-hailing services) - Single party (added in Travel Model 1.5)
		# 21	TNC - Shared e.g. sharing with strangers (added in Travel Model 1.5)
		
		# to this: 
		# da
		# daToll
		# s2
		# s2Toll
		# s3
		# s3Toll
		# walk
		# bike
		# wComW
		# wHvyW
		# wExpW
		# wLrfW
		# wLocW
		# wTrnW
		# dComW
		# dHvyW
		# dExpW
		# dLrfW
		# dLocW
		# dTrnW
		# wComD
		# wHvyD
		# wExpD
		# wLrfD
		# wLocD
		# wTrnD
		
		trips <- trips %>%
		  mutate(
		    
		    skims_mode = case_when(
		      
		      trip_mode == 1 ~ "da",
		      trip_mode == 2 ~ "daToll",
		      trip_mode == 3 ~ "s2",
		      trip_mode == 4 ~ "s2Toll",	 
		      trip_mode == 5 ~ "s3",
		      trip_mode == 6 ~ "s3Toll",	
		      trip_mode == 7 ~ "walk",
		      trip_mode == 8 ~ "bike",		        
		      trip_mode == 9 ~ "wLocW",	
		      trip_mode == 10 ~ "wLrfW",	
		      trip_mode == 11 ~ "wExpW",	
		      trip_mode == 12 ~ "wHvyW",	
		      trip_mode == 13 ~ "wComW",	
		      trip_mode == 14 & (orig_purpose == 'Home') ~ "dLocW",	
		      trip_mode == 15 & (orig_purpose == 'Home') ~ "dLrfW",	
		      trip_mode == 16 & (orig_purpose == 'Home') ~ "dExpW",	
		      trip_mode == 17 & (orig_purpose == 'Home') ~ "dHvyW",	
		      trip_mode == 18 & (orig_purpose == 'Home') ~ "dComW",
		      trip_mode == 14 & (dest_purpose == 'Home') ~ "wLocD",	
		      trip_mode == 15 & (dest_purpose == 'Home') ~ "wLrfD",	
		      trip_mode == 16 & (dest_purpose == 'Home') ~ "wExpD",	
		      trip_mode == 17 & (dest_purpose == 'Home') ~ "wHvyD",	
		      trip_mode == 18 & (dest_purpose == 'Home') ~ "wComD",	        
		      trip_mode == 19 ~ "Taxi",
		      trip_mode == 20 ~ "TNCa",
		      trip_mode == 21 ~ "TNCs",
		      TRUE ~ "Other"
		      
		    )
		    
		  )		  

		num_tours       <- nrow(tours)
		num_tours_dist  <- nrow( distinct(tours, hh_id, tour_participants, tour_id))
		print(paste("num_tours",      prettyNum(num_tours,big.mark=",")))
		print(paste("num_tours_dist", prettyNum(num_tours_dist,big.mark=",")))

		## Add Tour Duration to Trips
		print(paste("Before adding tour duration to trips -- have",prettyNum(nrow(trips),big.mark=","),"rows"))
		# this will only work for individual tours since person_id is set
		# trips <- left_join(trips, select(tours, hh_id, tour_participants, tour_id, duration), by=c("hh_id", "tour_participants", "tour_id")) %>% 
	#	  rename(tour_duration=duration)
		trips <- left_join(trips, select(tours, hh_id, tour_participants, tour_id, duration))
		trips <- trips %>% 
		  rename(tour_duration=duration)
		print(paste("After adding tour duration to trips -- have",prettyNum(nrow(trips),big.mark=","),"rows"))		  
		
		## Cleanup and save tours, trips and households
		print(paste("Saving trips.rds with",prettyNum(nrow(trips),big.mark=","),"rows and",ncol(trips),"columns"))
		saveRDS(trips, file=file.path(UPDATED_DIR, "trips.rds"))
		
		print(paste("Saving tours.rds with",prettyNum(nrow(tours),big.mark=","),"rows and",ncol(tours),"columns"))
		saveRDS(tours, file=file.path(UPDATED_DIR, "tours.rds"))
		remove(tours)
		
		print(paste("Saving households.rds with",prettyNum(nrow(households),big.mark=","),"rows and",ncol(households),"columns"))
		save(households, file=file.path(UPDATED_DIR, "households.rds"))
		remove(households)				
			
	} else {
	  
	  # Overhead
	  ## Lookups
	  
	  # For time periods, see https://github.com/BayAreaMetro/modeling-website/wiki/TimePeriods
	  # For counties, see https://github.com/BayAreaMetro/modeling-website/wiki/TazData
	  # For walk_subzones, see https://github.com/BayAreaMetro/modeling-website/wiki/Household
	  
	  ######### time periods
	  LOOKUP_TIMEPERIOD    <- data.frame(timeCodeNum=c(1,2,3,4,5),
	                                     timeperiod_label=c("Early AM","AM Peak","Midday","PM Peak","Evening"),
	                                     timeperiod_abbrev=c("EA","AM","MD","PM","EV"))
	  # no factors -- joins don't work
	  LOOKUP_TIMEPERIOD$timeCodeNum       <- as.integer(LOOKUP_TIMEPERIOD$timeCodeNum)
	  LOOKUP_TIMEPERIOD$timeperiod_label  <- as.character(LOOKUP_TIMEPERIOD$timeperiod_label)
	  LOOKUP_TIMEPERIOD$timeperiod_abbrev <- as.character(LOOKUP_TIMEPERIOD$timeperiod_abbrev)
	  
	  # mypathfile <- paste0(mywd, "/", myscenarioid, "/OUTPUT/updated_output/trips.rdata")
	  
	  ## Load main data file
	  
	  # load(mypathfile)
	  
	  trips <- readRDS(file=file.path(UPDATED_DIR, "trips.rds"))
	  
	  names(trips)
	  
	  ## Set means-based cost factors
	  MBT_Q1_factor <- 1.0
	  MBT_Q2_factor <- 1.0
	  MBF_Q1_factor <- 1.0
	  MBF_Q2_factor <- 1.0	
		
	
	}
	  

## Add variables from skims to data
	
	
	add_myvariable <- function(mydf, mytp, myvarname) {
	  
	  # the following lines should only be used for testing and should be commented out of the final code
	  	  
	  # myvar <- "walktime"
	  # mytp <- "AM"
	  # mydf <- trips
	  
	  # the preceding lines should only be used for testing and should be commented out of the final code	  
	  
	  # The variable may or may not already exist
	  
	  if (myvarname %in% names(mydf)) {
	    
	    cat(paste0("The variable ", myvarname, " already exists.", "\n \n"))
	    
	  } else {
	    
	    myvar <- rlang::sym(paste0(myvarname))
	    
	    # Assign value
	    mydf <- mydf %>%
	      mutate(!!myvar := 0.0)
	    
	  }
	  
	  # separate the relevant and irrelevant tours/trips
	  relevant <- mydf %>%
	    filter(timeCode == mytp)
	  
	  irrelevant <- mydf %>%
	    filter(timeCode != mytp)
	  
	  remove(mydf)
	  
	  # Read the relevant skim table
	  # sample filename: SkimsDatabaseEV_transfers.csv
	  skim_file <- file.path(TARGET_DIR,"database",paste0("SkimsDatabase",mytp, "_", myvarname,".csv"))
	  myskimdf <- read.table(file = skim_file, header=TRUE, sep=",")
	  
	  # rename columns for join
	  myskimdf <- myskimdf %>%
	    rename(orig_taz = orig, dest_taz = dest)
	  
	  # Left join tours to the skims
	  # relevant <- left_join(relevant, distSkims, by=c("orig_taz","dest_taz"))
	  relevant <- left_join(relevant, myskimdf)
	  
	  remove(myskimdf)
	  
	  myvar <- rlang::sym(paste0(myvarname))
	  
	  # Assign value
	  relevant <- relevant %>%
	    mutate(!!myvar := 0.0)
	  
	  # define any missing variables as zero
	  
	  for (checkvar in c("da",  "daToll",  "s2",  "s2Toll",  "s3",  "s3Toll",  "walk",  "bike",  "wComW",  "wHvyW",  "wExpW",  "wLrfW",  "wLocW",  "wTrnW",  "dComW",  "dHvyW",  "dExpW",  "dLrfW",  "dLocW",  "dTrnW",  "wComD",  "wHvyD",  "wExpD",  "wLrfD",  "wLocD",  "wTrnD")) {
	    
	    if (checkvar %in% names(relevant)) {
	      
	      cat(paste0("The variable ", checkvar, " already exists.", "\n \n"))
	      
	    } else {
	      
	      checkvar <- rlang::sym(paste0(checkvar))
	      
	      relevant <- relevant %>%
	        mutate(!!checkvar :=0)
	      
	    }
	    
	  }
	  
	  relevant <- relevant %>%
	    mutate(!!myvar := (skims_mode == "da") * da +
	             (skims_mode == "daToll") * daToll +
	             (skims_mode == "s2") * s2     +
	             (skims_mode == "s2Toll") * s2Toll +
	             (skims_mode == "s3") * s3     +
	             (skims_mode == "s3Toll") * s3Toll +
	             (skims_mode == "walk") * walk   +
	             (skims_mode == "bike") * bike   +
	             (skims_mode == "wLocW") * wLocW   +
	             (skims_mode == "wLrfW") * wLrfW   +
	             (skims_mode == "wExpW") * wExpW   +
	             (skims_mode == "wHvyW") * wHvyW   +
	             (skims_mode == "wComW") * wComW   +
	             (skims_mode == "dLocW") * dLocW   +
	             (skims_mode == "dLrfW") * dLrfW   +
	             (skims_mode == "dExpW") * dExpW   +
	             (skims_mode == "dHvyW") * dHvyW   +
	             (skims_mode == "dComW") * dComW   +	             
	             (skims_mode == "wLocD") * wLocD   +
	             (skims_mode == "wLrfD") * wLrfD   +
	             (skims_mode == "wExpD") * wExpD   +
	             (skims_mode == "wHvyD") * wHvyD   +
	             (skims_mode == "wComD") * wComD)
	  
	  relevant <- relevant %>%
	    mutate(!!myvar := ifelse(!!myvar < -990.0, 0, !!myvar))
	  
	  relevant <- relevant %>%
	    mutate(mynumvalues = !is.na(!!myvar))
	  
	  mynumvalues <- sum(relevant$mynumvalues)

	  relevant <- relevant %>%
	    mutate(mynonzerovalues = !is.na(!!myvar)&(!!myvar>0))	  
	  
	  mynonzerovalues <- sum(relevant$mynonzerovalues)
	  
	  print(paste("For",
	              mytp,
	              "assigned",
	              prettyNum(mynumvalues,big.mark=","),
	              "values, with",
	              prettyNum(mynonzerovalues,big.mark=","),
	              "nonzero values"))
	  
	  relevant <- relevant %>%
	    mutate(!!myvar := ifelse(is.na(!!myvar)==TRUE, 0, !!myvar))
	  
	  cat(paste0("\n \n", "Please check the following summary table of the variable ", myvarname, " for the time period ", mytp, " by mode.", "\n \n"))
	  
	  test <- relevant %>%
      group_by(skims_mode) %>%
      summarize(myvar_min := min(!!myvar), myvar_mean := mean(!!myvar), myvar_max := max(!!myvar)) %>%
      ungroup()

    test %>% print(n = 23)
	  
	  relevant <- dropr(relevant, "da",  "daToll",  "s2",  "s2Toll",  "s3",  "s3Toll",  "walk",  "bike",  "wComW",  "wHvyW",  "wExpW",  "wLrfW",  "wLocW",  "wTrnW",  "dComW",  "dHvyW",  "dExpW",  "dLrfW",  "dLocW",  "dTrnW",  "wComD",  "wHvyD",  "wExpD",  "wLrfD",  "wLocD",  "wTrnD", "mynumvalues", "mynonzerovalues")
	  
	  mydf <- rbind(relevant, irrelevant)
	  
	  test <- mydf %>%
	    group_by(skims_mode) %>%
	    summarize(myvar_min := min(!!myvar), myvar_mean := mean(!!myvar), myvar_max := max(!!myvar)) %>%
	    ungroup()
	  
	  test %>% print(n = 23)
	  
	  print(gc())
	  
	  return(mydf)
	  
	}
	
	# saveRDS(trips, "trips.rds")
	
	# the following lines should only be used for testing and should be commented out of the final code
	
	# myvar <- "walktime"
	# timeperiod <- "AM"
	
	# the preceding lines should only be used for testing and should be commented out of the final code
	
	# trips <- add_myvariable(mydf = trips, mytp = timeperiod, myvar = myvar)
	
	
# myvarlist <- c("walktime", "wait", "IVT", "transfers", "boardfare", "faremat", "xfare", "othercost", "distance")	
	myvarlist <- c(...)

trips <- dropr(trips, "da",  "daToll",  "s2",  "s2Toll",  "s3",  "s3Toll",  "walk",  "bike",  "wComW",  "wHvyW",  "wExpW",  "wLrfW",  "wLocW",  "wTrnW",  "dComW",  "dHvyW",  "dExpW",  "dLrfW",  "dLocW",  "dTrnW",  "wComD",  "wHvyD",  "wExpD",  "wLrfD",  "wLocD",  "wTrnD")
	
	for (myvarname in myvarlist) {

	  for (timeperiod in LOOKUP_TIMEPERIOD$timeperiod_abbrev) {
	    trips <- add_myvariable(mydf = trips, mytp = timeperiod, myvarname = myvarname)
	  }
	  
	  cat(paste0("\n \n", "Please check the following summary table of the variable ", myvarname, " for all time periods, by mode.", "\n \n"))
	  
	  myvar <- rlang::sym(paste0(myvarname))
	  
	  test <- trips %>%
      group_by(skims_mode) %>%
	    summarize(myvar_min := min(!!myvar), myvar_mean := mean(!!myvar), myvar_max := max(!!myvar)) %>%
      ungroup()
      
    test %>% print(n = 23)

	}

	trips <- as_tibble(trips)
			
	# calculate bau fare, for purposes of comparison
	trips <- trips %>%
	  mutate(bau_fare = boardfare + xfare + faremat)
	  
	if (baufares==TRUE) {
	
		trips <- trips %>%
		  mutate(fare = bau_fare)
	
	}

	trips <- as_tibble(trips)
	
	print(paste("Saving trips.rds with",prettyNum(nrow(trips),big.mark=","),"rows and",ncol(trips),"columns"))
	saveRDS(trips, file=file.path(UPDATED_DIR, "trips.rds"))
	
	summarize_attributes_min <- trips %>%
	  group_by(skims_mode) %>%
	  summarize(walktime = min(walktime), wait = min(wait), IVT = min(IVT), transfers = min(transfers), boardfare = min(boardfare), xfare = min(xfare), faremat = min(faremat), bau_fare = min(bau_fare), fare = min(fare)) %>%
	  ungroup()
	
	summarize_attributes_min %>% print(n = 23)
	
	summarize_attributes_mean <- trips %>%
	  group_by(skims_mode) %>%
	  summarize(walktime = mean(walktime), wait = mean(wait), IVT = mean(IVT), transfers = mean(transfers), boardfare = mean(boardfare), xfare = mean(xfare), faremat = mean(faremat), bau_fare = mean(bau_fare), fare = mean(fare)) %>%
	  ungroup()
	
	summarize_attributes_mean %>% print(n = 23)
	
	summarize_attributes_max <- trips %>%
	  group_by(skims_mode) %>%
	  summarize(walktime = max(walktime), wait = max(wait), IVT = max(IVT), transfers = max(transfers), boardfare = max(boardfare), xfare = max(xfare), faremat = max(faremat), bau_fare = max(bau_fare), fare = max(fare)) %>%
	  ungroup()
	
	summarize_attributes_max %>% print(n = 23)	
	
	now2 <- Sys.time()
	cat(yellow(paste0("JoinSkimsStr run finished at ", now2, "\n \n")))
	elapsed_time <- now2 - now1
	print(elapsed_time)	
	
	if (logrun==TRUE) {
	  sink()
	  cat(yellow(paste0("A log of the output has been saved to ", mylogfilename, ". \n \n")))
	}	
	
	print(gc())
	
	return(trips)
	
}
