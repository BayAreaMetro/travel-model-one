#
# Script to map the pems counts locations
#    github: https://github.com/BayAreaMetro/pems-typical-weekday
#    box:    https://mtcdrive.app.box.com/share-data
# to network links in Travel Model One or Two
#   See: https://github.com/BayAreaMetro/TM1_2015_Base_Network
#        https://github.com/BayAreaMetro/travel-model-two
# based on crosswalk type, route number and direction (e.g. mainline 101 N) and location.
#
# lmz 2018.18.16

library(sp)
library(rgdal)
library(rgeos)
library(tibble)
library(plyr)
library(dplyr)
library(reshape)
library(foreign)

HOME_DIR       <- Sys.getenv("HOME")
BOX_PEMS_DIR   <- file.path(HOME_DIR, "../Box/Modeling and Surveys/Share Data/pems-typical-weekday")  # Box Drive default
PEMS_DATA_FILE <- "pems_period.csv"
TM_VERSION     <- "TM1" # set to TM1 or TM2

CROSSWALK_DIR  <- paste0("M:/Crosswalks/PeMSStations_",TM_VERSION,"network")
TM_NETWORK_DIR <- "M:/Application/Model One/Networks/TM1_2015_Base_Network/shapefile"
TM_NETWORK     <- paste0(TM_VERSION,"_freeways_wgs84")

VALIDATION_YEAR<- 2015
PEMS_YEARS     <- c(2014,2015,2016)    # select pems stations with data for these years since PEMS stations may move

# output files
CROSSWALK_FILE <- "crosswalk"  # will output csv and dbf
PEMS_LOCS_FILE <- "pems_locs"
PEMS_LOCS_WITH_CROSSWALK <- "pems_locs_with_crosswalk"
TM_LINKS_WITH_PEMS_LOCS  <- "TM_links_with_pems"

############# PEMS data processing first

pems_df        <- read.table(file=file.path(BOX_PEMS_DIR, PEMS_DATA_FILE), sep=",", header=TRUE)

# select to PEMS_YEARS
pems_df        <- filter(pems_df, year %in% PEMS_YEARS)

# add unique key (e.g. "404594 4 280 N" and select out to key, postmile/lat/lon, year
pems_df        <- mutate(pems_df, key=paste(station, district, route, direction)) %>%
  select(key, station, district, route, direction, type, abs_pm, latitude, longitude, year)

# remove the ones without coords
pems_df        <- pems_df[!(is.na(pems_df$longitude)) | !(is.na(pems_df$latitude)),]

# remove the ones that are freeway-to-freeway ramps for now since we don't label these with route/dir
pems_df        <- filter(pems_df, type != "FF")
print(paste("pems_df has",nrow(pems_df),"rows"))

# key = station, district, route, direction; e.g. "400001 4 101 N"
# pems_df[ which(pems_df$key=="401052 4 80 W"), ]

# figure out how many keys move locations based on changed abs_pm/lat/longitude
pems_key_loc   <- distinct(pems_df, key, abs_pm, latitude, longitude) %>% arrange(key) %>% 
  mutate(is_dupe = duplicated(key))
moved_pems_keys <- filter(pems_key_loc, is_dupe==TRUE) %>% select(key) %>% mutate(moved=1)
print(paste("Out of",nrow(distinct(pems_df, key)),"distinct PEMS keys, dropped",nrow(moved_pems_keys),"because location moved"))

# drop pems keys that have moved
pems_df        <- left_join(pems_df, moved_pems_keys) %>% filter(is.na(moved)) %>% select(-moved)
print(paste("pems_df has",nrow(pems_df),"rows"))
remove(pems_key_loc, moved_pems_keys)

# drop duplicates (multiple years)
pems_df        <- distinct(pems_df, key, .keep_all=TRUE)

# add pems_rowid and type_route_dir
pems_df        <- group_by(pems_df, key) %>% arrange(desc(year))
pems_df        <- as.data.frame(pems_df) %>% rowid_to_column("pems_rowid") %>%
  mutate(type_route_dir = paste(type, route, direction))

# create the SpatialPointsDataFrame object
pems_locs <- SpatialPointsDataFrame(coords=pems_df[,c("longitude","latitude")], data=pems_df, proj4string = CRS("+proj=longlat +datum=WGS84"))
summary(pems_locs)
writeOGR(obj=pems_locs, dsn=file.path(CROSSWALK_DIR, "shapefiles"), layer=paste0(PEMS_LOCS_FILE,"_",VALIDATION_YEAR), driver="ESRI Shapefile")
print(paste0("Wrote PEMS locations: ",file.path(CROSSWALK_DIR, "shapefiles", paste0(PEMS_LOCS_FILE,"_",VALIDATION_YEAR,".shp"))))

############# TM freeway network data processing second

# read the route links shapefile
route_links   <- readOGR(dsn=file.path(TM_NETWORK_DIR), layer=TM_NETWORK)
summary(route_links)

# set type to match pems type
if (TM_VERSION == "TM1") {
  # https://github.com/BayAreaMetro/modeling-website/wiki/MasterNetworkLookupTables
  route_links$type <- ""
  route_links$type[ route_links$FT ==  1 ] <- "FF"  # freeway-to-freeway
  route_links$type[ route_links$FT ==  2 ] <- "ML"  # freeway - mainline
  route_links$type[ route_links$FT ==  3 ] <- "ML"  # expressway - mainline
  route_links$type[ route_links$FT ==  7 ] <- "ML"  # arterial (e.g. when 101 goes through SF)
  route_links$type[ route_links$FT ==  8 ] <- "ML"  # Managed Freeway
  route_links$type[ route_links$FT == 10 ] <- "ML"  # Toll plaza
  route_links$type[ (route_links$USE==2)|(route_links$USE==3) ] <- "HV" # HOV
  route_links$type[ (route_links$FT==5) ] <- "RA"   # generic ramp
} else if (TM_VERSION == "TM2") {
  route_links$type <- ""
  route_links$type[ route_links$FT == 1 ] <- "FF"  # freeway-to-freeway
  route_links$type[ route_links$FT == 2 ] <- "ML"  # freeway - mainline
  route_links$type[ route_links$FT == 3 ] <- "ML"  # expressway - mainline
  route_links$type[ (route_links$FT == 2)&((route_links$USECLASS==2)|(route_links$USECLASS==3)) ] <- "HV" # HOV
  route_links$type[ (route_links$FT==5) ] <- "RA"   # generic ramp
  route_links$type[ (route_links$FT==5)&(route_links$RAMP==1)] = "FR" # Off-ramp
  route_links$type[ (route_links$FT==5)&(route_links$RAMP==2)] = "OR" # On-ramp
}

# convert to factor
route_links$type <- factor(route_links$type)
summary(route_links)

if (TM_VERSION == "TM1") {
  route_links$route     <- as.character(route_links$ROUTENUM)
  route_links$route[ route_links$ROUTENUM == 0 ] <- NA  # 0 is no route
  
  route_links$direction <- route_links$ROUTEDIR
  # NAME doesn't exist in TM1 network links -- add it
  route_links$NAME      <- paste0(route_links$route," ", route_links$direction)
  
} else if (TM_VERSION == "TM2") {

  # find route and direction from the NAME
  pat                   <- "(US-|CA-|I-)(\\d+)\\s*([EWNS])*(Byp)?"
  does_match            <- grepl(pat,route_links$NAME)
  route_links$route     <- sub(pattern=pat, replacement="\\2", x=route_links$NAME, perl=TRUE)
  route_links$direction <- sub(pattern=pat, replacement="\\3", x=route_links$NAME, perl=TRUE)
  # set to NA if no match or empty
  route_links$route[     does_match==FALSE ] <- NA
  route_links$direction[ does_match==FALSE ] <- NA
  route_links$direction[ route_links$direction==""] <- NA

  # special for 87
  route_links[ which(route_links$NAME=="Guadalupe Fwy N"), "route"    ] <- "87"
  route_links[ which(route_links$NAME=="Guadalupe Fwy N"), "direction"] <- "N"
  route_links[ which(route_links$NAME=="Guadalupe Fwy S"), "route"    ] <- "87"
  route_links[ which(route_links$NAME=="Guadalupe Fwy S"), "direction"] <- "S"
  route_links[ which(route_links$NAME=="Guadalupe Pkwy" ), "route"    ] <- "87"

  # special for 37,12
  route_links[ which(route_links$NAME=="Sears Point Rd" ), "route" ] <- "37"
  route_links[ which(route_links$NAME=="Marine World Pk"), "route" ] <- "37"
  route_links[ which(route_links$NAME=="Jameson Canyon" ), "route" ] <- "12"

  # Links in this box marked as I-580 are also I-80 and PeMS uses I-80
  # "The section of the Eastshore Freeway between the MacArthur Maze and the 580 (Hoffman) split between Albany is a wrong-way
  # concurrency where the northbound direction is signed as I-80 East and I-580 West, while the southbound direction is signed
  # as westbound I-80 and eastbound I-580. This segment suffers from severe traffic congestion during rush hour due to the merger
  # of three freeways (I-80, I-580, and I-880) at the MacArthur Maze.
  levels(route_links$NAME) <- c(levels(route_links$NAME), "I-580 E/I-80 W", "I-580 W/I-80 E")

  # Southbound: I-580 E => I-80 W.  28 links with Y1 in [37.840, 37.887]
  route_links[ which((route_links$NAME=="I-580 E")&(route_links$Y1>=37.840)&(route_links$Y1<=37.887)), "NAME"] <-  "I-580 E/I-80 W"
  print(paste("Found ",nrow( route_links[which(route_links$NAME == "I-580 E/I-80 W"),]),"links for I-580 E/I-80 W"))
  # Northbound: I-580 W => I-80 E.  32 links with Y1 in [37.836, 37.884]
  route_links[ which((route_links$NAME=="I-580 W")&(route_links$Y1>=37.836)&(route_links$Y1<=37.884)), "NAME"] <- "I-580 W/I-80 E"
  print(paste("Found ",nrow( route_links[which(route_links$NAME == "I-580 W/I-80 E"),]),"links for I-580 W/I-80 E"))

  route_links[ which(route_links$NAME=="I-580 E/I-80 W"), "route"    ] <- "80"
  route_links[ which(route_links$NAME=="I-580 E/I-80 W"), "direction"] <- "W"
  route_links[ which(route_links$NAME=="I-580 W/I-80 E"), "route"    ] <- "80"
  route_links[ which(route_links$NAME=="I-580 W/I-80 E"), "direction"] <- "E"


  # associate routes with known directions
  route_dirs <- unique(as.data.frame( route_links[ which(!is.na(route_links$route) & !is.na(route_links$direction)), c("route","direction")] ))
  route_dirs$dir_choice <- ifelse((route_dirs$direction=="E"|route_dirs$direction=="W"),"EW","NS")
  route_dirs <- unique(select(route_dirs, "route","dir_choice"))

  # hack: these aren't included
  route_dirs <- unique(rbind(route_dirs, c("9","NS"), c("35","NS"), c("25","NS"), c("116","EW"), c("128","EW"), c("77","EW"), c("82","NS")))

  # these have routes but no direction - try to impute
  route_links           <- merge(route_links, route_dirs, by.x="route", by.y="route")
  route_links$xdiff     <- route_links$X2 - route_links$X1
  route_links$ydiff     <- route_links$Y2 - route_links$Y1
  route_links$impute_ew <- ifelse(route_links$xdiff > 0, "E","W")
  route_links$impute_ns <- ifelse(route_links$ydiff > 0, "N","S")
  route_links$impute_dir<- ifelse(route_links$dir_choice=="EW",route_links$impute_ew,route_links$impute_ns)
  route_links$direction <- ifelse(is.na(route_links$direction), route_links$impute_dir, route_links$direction)

}

print("Routes without direction:")
no_dir <- route_links[ which(!is.na(route_links$route) & is.na(route_links$direction)), ]
print(paste(nrow(no_dir),"rows"))
# print(route_links[ which(!is.na(route_links$route) & is.na(route_links$direction)), c("NAME","route","direction","dir_choice","impute_ew","xdiff","impute_ns","ydiff")])

# make these factors, and routes are numeric
route_links$route     <- factor(as.numeric(route_links$route))
route_links$direction <- factor(route_links$direction)

# these are the non-matching
print("Routes without number:")
no_num <- route_links[ which(is.na(route_links$route)), ]
print(sort(unique(no_num$NAME)))

# set A_B
route_links$A_B <- paste0(route_links$A,"_",route_links$B)

summary(route_links)

# add link_rowid for dataframe and select out the relevant fields
route_links_df<- mutate(as.data.frame(route_links)) %>%
  rowid_to_column("link_rowid") %>%
  select(type, route, direction, A, B, NAME, link_rowid)

# For ramps, PEMS labels the ramp route/direction based on the freeway. Try to intelligently update network links similarly.
fwy_links_df   <- route_links_df[ (route_links_df$route != 0)&(!is.na(route_links_df$direction)), ]


# join ramp links B to fwy A for on ramps
route_links_df  <- left_join(route_links_df, fwy_links_df, by=(c("B"="A")), suffix=c("","_tofwy"))
# and A to fwy B for off ramps
route_links_df  <- left_join(route_links_df, fwy_links_df, by=(c("A"="B")), suffix=c("","_frfwy"))

## straightforward on-ramps and off-ramps -- inherit the route and direction and get type
route_links_df$is_onramp <- ((route_links_df$type=="RA")|(route_links_df$type=="OR")) & (!is.na(route_links_df$type_tofwy)&( is.na(route_links_df$type_frfwy))&(route_links_df$type_tofwy=="ML"))
route_links_df$type[      which(route_links_df$is_onramp) ] <- "OR"
route_links_df$route[     which(route_links_df$is_onramp) ] <- route_links_df$route_tofwy[     which(route_links_df$is_onramp) ]
route_links_df$direction[ which(route_links_df$is_onramp) ] <- route_links_df$direction_tofwy[ which(route_links_df$is_onramp) ]

route_links_df$is_offramp <- ((route_links_df$type=="RA")|(route_links_df$type=="FR")) & ( is.na(route_links_df$type_tofwy)&(!is.na(route_links_df$type_frfwy))&(route_links_df$type_frfwy=="ML"))
route_links_df$type[      which(route_links_df$is_offramp) ] <- "FR"
route_links_df$route[     which(route_links_df$is_offramp) ] <- route_links_df$route_frfwy[     which(route_links_df$is_offramp) ]
route_links_df$direction[ which(route_links_df$is_offramp) ] <- route_links_df$direction_frfwy[ which(route_links_df$is_offramp) ]

print(table(route_links_df$type))

# this version is for distance-joining
route_links_df_dist <- select(route_links_df, type, route, direction, A, B, NAME, link_rowid) %>% 
  mutate(type_route_dir=paste(type,route,direction)) %>%
  select(-type,-route,-direction)

# this produces rows (caltrans locs) x columns (route_links)
distances <- gDistance(route_links, pems_locs, byid=TRUE)
# transform them so we can join to the inner join
distances_long <- melt(distances) %>% mutate(pems_rowid=X1, link_rowid=X2+1) %>% dplyr::rename(distance=value) %>% select(-X1,-X2)

print(dim(distances))


matching_routes <- inner_join(pems_df, route_links_df_dist, by="type_route_dir")
matching_routes <- left_join(matching_routes, distances_long)

# for each pems_rowid which has the minimum distance
xwalk <- matching_routes %>% group_by(pems_rowid) %>% slice(which.min(distance)) %>% as.data.frame()

# go back to original columns, plus A, B, distance
xwalk <- select(xwalk, station, district, route, direction, type, abs_pm, latitude, longitude, A, B, distance) %>%
  dplyr::rename(distlink=distance)

# for joins
xwalk <- mutate(xwalk, A_B=paste0(A,"_",B))

# summarize how many pems ids join to a single link
mult_pems <- group_by(xwalk, A_B) %>% summarise(pemsonlink=n())
xwalk     <- left_join(xwalk, mult_pems)

# write it
write.csv(xwalk, file.path(CROSSWALK_DIR, paste0(CROSSWALK_FILE,"_",VALIDATION_YEAR,".csv")), row.names=FALSE, quote=FALSE)
print(paste("Wrote crosswalk:",file.path(CROSSWALK_DIR, paste0(CROSSWALK_FILE,".csv"))))

write.dbf(xwalk, file.path(CROSSWALK_DIR, paste0(CROSSWALK_FILE,"_",VALIDATION_YEAR,".dbf")), factor2char=TRUE)
print(paste("Wrote crosswalk:",file.path(CROSSWALK_DIR, paste0(CROSSWALK_FILE,".dbf"))))

# write pems_loc joined with xwalk as shapefile
pems_df              <- left_join(pems_df, xwalk)
pems_locs$A          <- pems_df$A
pems_locs$B          <- pems_df$B
pems_locs$A_B        <- pems_df$A_B
pems_locs$distlink   <- pems_df$distlink
pems_locs$pemsonlink <- pems_df$pemsonlink

writeOGR(obj=pems_locs, dsn=file.path(CROSSWALK_DIR, "shapefiles"), layer=paste0(PEMS_LOCS_WITH_CROSSWALK,"_",VALIDATION_YEAR), driver="ESRI Shapefile")
print(paste0("Wrote PEMS locations with crosswalk: ",file.path(CROSSWALK_DIR, "shapefiles", paste0(PEMS_LOCS_WITH_CROSSWALK,"_",VALIDATION_YEAR,".shp"))))

# write links joined with pems as shapefile

# reference: http://www.nickeubank.com/wp-content/uploads/2015/10/RGIS2_MergingSpatialData_part1_Joins.html#spatial-non-spatial

# keeps only route_links associated with pems stations
# and duplicates if they match to multiple pems locations
route_links_with_pems <- merge(route_links, xwalk, by.x="A_B", by.y="A_B", 
                               all.x=FALSE,
                               duplicateGeoms=TRUE, suffixes=c("", " pems"))

# iterate over the rows in route_links_with_pems
lines_list <- list()
for (i in 1:nrow(route_links_with_pems@data)) {
  coord     <- coordinates(route_links_with_pems[i,])[[1]][[1]]
  pems_loc  <- c(route_links_with_pems@data[i,]$longitude,
                 route_links_with_pems@data[i,]$latitude)
  new_coord <- matrix(NA, nrow=4, ncol=2)
  new_coord[1,] <- pems_loc  # PEMS
  new_coord[2,] <- coord[1,] # A
  new_coord[3,] <- coord[2,] # B
  new_coord[4,] <- pems_loc  # PEMS
  
  # create a new line
  my_line  <- Line(new_coord)
  my_lines <- Lines(list(my_line), ID=rownames(route_links_with_pems@data)[i])
  lines_list[[i]] <- my_lines
}

sp_lines = SpatialLines(lines_list)
sp_lines_df = SpatialLinesDataFrame(sp_lines, data=route_links_with_pems@data)
writeOGR(obj=sp_lines_df, dsn=file.path(CROSSWALK_DIR, "shapefiles"), 
         layer=paste0(TM_LINKS_WITH_PEMS_LOCS,"_",VALIDATION_YEAR),
         driver="ESRI Shapefile")

