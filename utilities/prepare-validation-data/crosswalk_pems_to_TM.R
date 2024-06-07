USAGE = "
  Script to map the pems counts locations to the travel model network
    github: https://github.com/BayAreaMetro/pems-typical-weekday
    box:    https://mtcdrive.box.com/v/pems-typical-weekday
  based on crosswalk type, route number and direction (e.g. mainline 101 N) and location.

  Input:
  1) PeMS locations via Box/Modeling and Surveys/Share Data/pems-typical-weekday/pems_period.csv
  2) Model links shapefile for freeways & ramps:
     2015: M:/Application/Model One/Networks/TM1_2015_Base_Network/shapefile/TM1_freeways_wgs84.shp
     2023: M:/Application/Model One/RTP2025/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_v13/net_2023_Blueprint/shapefile_forPeMScrosswalk/TM1_freeways_wgs84.shp
  
  Output:
  1) Debug log file: M:/Crosswalks/PeMSStations_TM1network/crosswalk_pems_to_TM_[2015,2023].log

  2) PeMS locations: M:/Crosswalks/PeMSStations_TM1network/shapefiles/pems_locs_[2015,2023].shp
     These are the PeMS points the script is trying to crosswalk to model links

  3) Crosswalk files: M:/Crosswalks/PeMSStations_TM1network/crosswalk_[2015,2023].[csv,dbf]
     The resulting crosswalk. Columns are:
       station district route direction type  abs_pm latitude longitude     A    B   distlink stationsonlink
     This file is filtered to bad_match==False, so this column is excluded

  4) Crosswalk as shapefile: M:/Crosswalks/PeMSStations_TM1network/shapefiles/pems_locs_with_crosswalk_[2015,2023].shp
     Same as PeMS locations file but with route link information included.
     This includes all stations, without filtering based on bad_match.

  5) Crosswalk visualization: M:/Crosswalks/PeMSStations_TM1network/shapefiles/TM_links_with_pems_[2015,2023].shp
     This is a list of triangles, starting at each PeMS station, and then following the associated link.
     This includes all stations, without filtering based on bad_match (and is helpful for determining the
     bad_match rules)

"

suppressPackageStartupMessages({
  library(sf)
  library(argparser)
  library(tidyverse)
  library(foreign)
})
options(width = 500) # we're printing to a log file

# Parameters
# year(s) and district(s) are now command-line arguments
argparser <- arg_parser(USAGE, hide.opts=TRUE)
argparser <- add_argument(parser=argparser, arg="--pems_years",      short="-p", help="PeMS Years",       type="numeric", nargs=Inf)
argparser <- add_argument(parser=argparser, arg="--validation_year", short="-v", help="Validation year",  type="numeric")

# parse the command line arguments
argv <- parse_args(argparser)

LOG_FILE <- paste0("crosswalk_pems_to_TM_", argv$validation_year, ".log")
print(paste("Saving log to", LOG_FILE))
sink(file=LOG_FILE, type=c("output","message"))

print(paste("Validation year:", argv$validation_year))
print(paste("PeMS year:", argv$pems_years))

if (Sys.getenv("USERNAME") == 'lzorn') {
  BOX_DIR      <- "E://Box"
}
if (Sys.getenv("USERNAME") == "MTCPB") {
  BOX_DIR      <- "//tsclient/C/Users/ftsang/Box"
}

BOX_PEMS_DIR   <- file.path(BOX_DIR, "Modeling and Surveys/Share Data/pems-typical-weekday")  # Box Drive default
PEMS_DATA_FILE <- "pems_period.csv"
TM_VERSION     <- "TM1"

CROSSWALK_DIR  <- paste0("M:/Crosswalks/PeMSStations_",TM_VERSION,"network")
if (argv$validation_year == 2015) {
  TM_NETWORK_DIR <- "M:/Application/Model One/Networks/TM1_2015_Base_Network/shapefile"
} else if (argv$validation_year == 2023) {
  TM_NETWORK_DIR <- "M:/Application/Model One/RTP2025/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_v13/net_2023_Blueprint/shapefile_forPeMScrosswalk"
} else {
  stop(paste("Travel model network needed for validation year:", argv$validation_year))
}
TM_NETWORK     <- paste0(TM_VERSION,"_freeways_wgs84.shp")

# output files
CROSSWALK_FILE <- "crosswalk"  # will output csv and dbf
PEMS_LOCS_FILE <- "pems_locs"
PEMS_LOCS_WITH_CROSSWALK <- "pems_locs_with_crosswalk"
TM_LINKS_WITH_PEMS_LOCS  <- "TM_links_with_pems"

############# PEMS data processing first
print(paste("Reading",file.path(BOX_PEMS_DIR, PEMS_DATA_FILE)))
pems_df <- read.table(file=file.path(BOX_PEMS_DIR, PEMS_DATA_FILE), sep=",", header=TRUE)
print(paste("Read",nrow(pems_df), "rows from", file.path(BOX_PEMS_DIR, PEMS_DATA_FILE)))

# select to argv$pems_years
pems_df <- filter(pems_df, year %in% argv$pems_years)
print(paste("Filtered to",nrow(pems_df),"rows for pems_years"))

print("head(pems_df):")
print(head(pems_df))

# add unique key (e.g. "404594 4 280 N" and select out to key, postmile/lat/lon, year
pems_df <- mutate(pems_df, key=paste(station, district, route, direction)) %>%
  select(key, station, district, route, direction, type, abs_pm, latitude, longitude, year, lanes) %>%
  dplyr::rename(pems_lanes=lanes)

# remove the ones without coords
pems_df <- pems_df %>% 
  filter(!is.na(longitude)) %>% 
  filter(!is.na(latitude))
print(paste("Filtered to",nrow(pems_df),"rows with lat/lon"))

# remove the ones that are freeway-to-freeway ramps for now since we don't label these with route/dir
pems_df <- filter(pems_df, type != "FF")
print(paste("Filtered to",nrow(pems_df),"rows for type != FF"))
print(table(pems_df$type, useNA="always"))

# key = station, district, route, direction; e.g. "400001 4 101 N"
# pems_df[ which(pems_df$key=="401052 4 80 W"), ]

# figure out how many keys move locations based on changed abs_pm/lat/longitude
pems_key_loc <- distinct(pems_df, key, abs_pm, latitude, longitude) %>% arrange(key) %>% 
  mutate(is_dupe = duplicated(key))
moved_pems_keys <- filter(pems_key_loc, is_dupe==TRUE) %>% select(key) %>% distinct() %>% mutate(moved=1)
print(paste("Out of",nrow(distinct(pems_df, key)),"distinct PEMS keys, dropped",
  nrow(moved_pems_keys),"because location moved"))

# drop pems keys that have moved
if (nrow(moved_pems_keys) > 0) {
  pems_df <- left_join(pems_df, moved_pems_keys, by=join_by(key)) %>% filter(is.na(moved)) %>% select(-moved)
  print(paste("Filtered to",nrow(pems_df),"rows of",nrow(distinct(pems_df,key)),
    "distinct keys after dropping stations that have moved"))
}
remove(pems_key_loc, moved_pems_keys)

# drop duplicates (multiple years)
pems_df <- distinct(pems_df, key, .keep_all=TRUE)

# add pems_rowid and type_route_dir
pems_df <- group_by(pems_df, key) %>% arrange(desc(year))
pems_df <- as.data.frame(pems_df) %>% rowid_to_column("pems_rowid") %>%
  mutate(type_route_dir = paste(type, route, direction))

# create the points object
pems_locs <- sf::st_as_sf(pems_df, coords=c("longitude","latitude"), crs = 4326)
print("head(pems_locs)")
print(pems_locs)
# summary(pems_locs)
output_file <- file.path(CROSSWALK_DIR, "shapefiles", paste0(PEMS_LOCS_FILE,"_",argv$validation_year,".shp"))
sf::write_sf(pems_locs, output_file)
print(paste("Wrote",nrow(pems_locs),"PEMS locations to:",output_file))

############# TM freeway network data processing second

# read the route links shapefile
input_file <- file.path(TM_NETWORK_DIR, TM_NETWORK)
route_links <- sf::read_sf(input_file)
print(paste("Read",nrow(route_links),"rows from",input_file))
route_links <- select(route_links, A, B, AT, FT, LANES, USE, TOLLCLASS, ROUTENUM, ROUTEDIR, geometry)
print("head(route_links):")
print(head(route_links))

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
print("table(route_links$type, useNA='always')")
print(table(route_links$type, useNA="always"))

if (TM_VERSION == "TM1") {
  route_links$route <- as.character(route_links$ROUTENUM)
  route_links$route[ route_links$ROUTENUM == 0 ] <- NA  # 0 is no route
  
  route_links$direction <- route_links$ROUTEDIR
  # NAME doesn't exist in TM1 network links -- add it
  route_links$NAME <- paste0(route_links$route," ", route_links$direction)
  
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

no_dir <- filter( route_links, !is.na(route) & is.na(direction))
print(paste("Route links with route and without direction:", nrow(no_dir),"rows"))
if (nrow(no_dir) > 0) {
  print("table(no_dir$route)")
  print(table(no_dir$route))
  # https://github.com/BayAreaMetro/modeling-website/wiki/MasterNetworkLookupTables#vehicle-restrictions-use
  print("table(no_dir$USE) -- if they're all 4, they're Express Lanes...")
  print(table(no_dir$USE))
  print("table(no_dir$FT)")
  print(table(no_dir$FT))
  print("select(no_dir, A, B, route, direction, FT, USE)")
  print(select(no_dir, A, B, route, direction, FT, USE))
}

# make these factors, and routes are numeric
route_links$route     <- factor(as.numeric(route_links$route))
route_links$direction <- factor(route_links$direction)

# links without a route number
no_num <- filter(route_links, is.na(route))
print(paste("Routes without number:", nrow(no_num), "rows"))
# https://github.com/BayAreaMetro/modeling-website/wiki/MasterNetworkLookupTables#vehicle-restrictions-use
print("table(no_num$USE)")
print(table(no_num$USE))
print("table(no_num$FT)")
print(table(no_num$FT))
# seems like ramps (FT=5) are ok, and HOV/Express lanes (USE>1) are ok...
# TODO: what about the others
print("select(no_num, A, B, route, direction, FT, USE)")
print(select(no_num, A, B, route, direction, FT, USE))

# add link_rowid for dataframe and select out the relevant fields
route_links_df<- mutate(as.data.frame(route_links)) %>%
  rowid_to_column("link_rowid") %>%
  select(type, route, direction, A, B, NAME, link_rowid)
print(paste("Created route_links_df with",nrow(route_links_df),"rows"))
print("head(route_links_df)")
print(head(route_links_df))
print("table(route_links_df$type, useNA='always')")
print(table(route_links_df$type, useNA="always"))

# For ramps, PEMS labels the ramp route/direction based on the freeway.
# Try to intelligently update network links similarly.
# First, select freeway links (with routes and direction)
fwy_links_df <- filter(route_links_df, 
  (type=="ML") & (route != 0) & (!is.na(direction)))
# ensure that we don't have A or B that are duplicates -- then we'll get duplicated rows
fwy_links_df <- distinct(fwy_links_df, A, .keep_all=TRUE)
fwy_links_df <- distinct(fwy_links_df, B, .keep_all=TRUE)
print("head(fwy_links_df)")
print(head(fwy_links_df))

# join ramp links B to fwy A for on ramps
route_links_df <- left_join(
  route_links_df, 
  fwy_links_df,
  by=(c("B"="A")),
  suffix=c("","_tofwy"),
  relationship="many-to-one")

# and A to fwy B for off ramps
route_links_df <- left_join(
  route_links_df, 
  fwy_links_df, 
  by=(c("A"="B")),
  suffix=c("","_frfwy"),
  relationship="many-to-one")
print(paste("nrow(route_links_df)=", nrow(route_links_df)))

print("head(route_links_df)")
print(head(route_links_df))

# inherit direction type/route/direction from freeway
route_links_df <- mutate(route_links_df,
  is_onramp = ((type=="RA")|(type=="OR")) & (!is.na(type_tofwy)&(is.na(type_frfwy))&(type_tofwy=="ML"))
) %>% mutate(
  type      = case_when(is_onramp ~ "OR", .default=type),
  route     = case_when(is_onramp ~ route_tofwy, .default=route),
  direction = case_when(is_onramp ~ direction_tofwy, .default=direction)
)

route_links_df_ramp <- mutate(route_links_df,
  is_offramp = ((type=="RA")|(type=="FR")) & (is.na(type_tofwy)&(!is.na(type_frfwy))&(type_frfwy=="ML"))
) %>% mutate(
  type      = case_when(is_offramp ~ "FR", .default=type),
  route     = case_when(is_offramp ~ route_frfwy, .default=route),
  direction = case_when(is_offramp ~ direction_frfwy, .default=direction)
)

print("After simple assignment of type/route/direction for ramps, head(route_links_df):")
print(head(route_links_df))

# count rows with duplicated A,B - this should be zero
dupe_a_b <- route_links_df_ramp %>% group_by(A,B) %>% filter(n()>1)
stopifnot(nrow(dupe_a_b) == 0)

print("table(route_links_df$type, useNA='always')")
print(table(route_links_df$type, useNA="always"))

# this version is for distance-joining
route_links_df_dist <- select(route_links_df, type, route, direction, A, B, NAME, link_rowid) %>% 
  mutate(type_route_dir=paste(type,route,direction)) %>%
  select(-type,-route,-direction)

print(paste("route_links_df_dist has", nrow(route_links_df_dist),"rows"))
print("head(route_links_df_dist)")
print(head(route_links_df_dist))
# count rows with duplicated link_rowid - this should be zero
dupe_link_rowid <- route_links_df_dist %>% group_by(link_rowid) %>% filter(n()>1)
stopifnot(nrow(dupe_link_rowid) == 0)

# this produces rows (pems locs) x columns (route_links)
# https://r-spatial.github.io/sf/reference/geos_measures.html
print(paste("nrow(route_links)=",nrow(route_links),"; nrow(pems_locs)=",nrow(pems_locs)))
distances <- sf::st_distance(route_links, pems_locs, by_element=FALSE)
print("dim(distances)=")
print(dim(distances))
print(str(distances))

# convert to long form
distances_long <- as_tibble(distances, rownames="link_rowid_str")
print("head(distances_long)")
print(head(distances_long))

# https://tidyr.tidyverse.org/reference/gather.html
distances_long <- gather(distances_long, "pems_rowid_str", "distance", -link_rowid_str) %>%
  mutate(pems_rowid_str=str_sub(pems_rowid_str, 2)) # first letter is always "V" -- strip that

distances_long <- mutate(
  distances_long,
  link_rowid = as.integer(link_rowid_str),
  pems_rowid = as.integer(pems_rowid_str),
  distance_m = as.numeric(distance)
) %>% select(-link_rowid_str, -pems_rowid_str, -distance)
print("head(distances_long)")
print(head(distances_long))

matching_routes <- inner_join(pems_df, route_links_df_dist, by=join_by(type_route_dir), relationship="many-to-many")
matching_routes <- left_join(matching_routes, distances_long, by=join_by(pems_rowid, link_rowid))
print("head(matching_routes)")
print(head(matching_routes))

# for each pems_rowid which has the minimum distance
xwalk <- matching_routes %>% group_by(pems_rowid) %>% filter(distance_m == min(distance_m)) %>% as.data.frame()
print(paste("xwalk has", nrow(xwalk),"rows"))
print("head(xwalk)")
print(head(xwalk))
# why are there more rows than pems ids?
# TODO: exactly the same distances??
xwalk <- add_count(xwalk, pems_rowid, name="pems_rowid_count")
print("rows with duplicated pems_rowid:")
print(class(xwalk))
print(filter(xwalk, pems_rowid_count>1))

# remove those
xwalk <- filter(xwalk, pems_rowid_count==1) %>% select(-pems_rowid_count)
print(paste("Filtered to single matches only, or", nrow(xwalk), "rows"))

# go back to original columns, plus A, B, distance
xwalk <- select(xwalk, station, district, route, direction, type, pems_lanes, abs_pm, latitude, longitude, A, B, distance_m) %>%
  dplyr::rename(distlink=distance_m)

# summarize how many pems ids join to a single link
mult_pems <- summarise(xwalk, stationsonlink=n(), .by= c(A,B))
print(paste("mult_pems has", nrow(mult_pems),"rows"))
print("head(mult_pems)")
print(head(mult_pems))

xwalk <- left_join(xwalk, mult_pems, by=join_by(A,B))

print("head(xwalk)")
print(head(xwalk))

# new -- quality control
xwalk <- mutate(xwalk, 
  bad_match = case_when(
    ((type == 'OR') | (type == 'FR') | (type == 'RA')) & (distlink > 400) ~ TRUE, # drop ramps with distlink > 400m
    (distlink > 1400) ~ TRUE, # mainline should be closer than this too, but we have some imprecise links
    .default = FALSE
  ))
print("bad_match values:")
print(table(xwalk$bad_match))

# write it
output_file <- file.path(CROSSWALK_DIR, paste0(CROSSWALK_FILE,"_",argv$validation_year,".csv"))
write.csv(filter(xwalk, bad_match==FALSE) %>% select(-bad_match), output_file, row.names=FALSE, quote=FALSE)
print(paste("Wrote",nrow(filter(xwalk, bad_match==FALSE)),"rows to",output_file))

output_file <- file.path(CROSSWALK_DIR, paste0(CROSSWALK_FILE,"_",argv$validation_year,".dbf"))
foreign::write.dbf(filter(xwalk, bad_match==FALSE) %>% select(-bad_match), output_file, factor2char=TRUE)
print(paste("Wrote",nrow(filter(xwalk, bad_match==FALSE)),"rows to",output_file))

# write pems_loc joined with xwalk as shapefile
# some pems will correspond to multiple links so they'll show up twice
pems_df <- inner_join(pems_df, xwalk)
print(paste("pems_df after joining to xwalk has",nrow(pems_df),"rows"))
print("head(pems_df)")
print(head(pems_df))
pems_locs <- sf::st_as_sf(pems_df, coords=c("longitude","latitude"), crs = 4326)

output_file <- file.path(CROSSWALK_DIR, "shapefiles", paste0(PEMS_LOCS_WITH_CROSSWALK,"_",argv$validation_year,".shp"))
sf::write_sf(pems_locs, output_file)
print(paste("Wrote", nrow(pems_df), "PEMS locations with crosswalk: ",output_file))

# write links joined with pems as shapefile

# reference: http://www.nickeubank.com/wp-content/uploads/2015/10/RGIS2_MergingSpatialData_part1_Joins.html#spatial-non-spatial

# keeps only route_links associated with pems stations
# and duplicates if they match to multiple pems locations
route_links_with_pems <- inner_join(
  route_links, xwalk, by=join_by(A,B),
  suffix=c("", " pems"))

# iterate over the rows in route_links_with_pems
lines_list <- list()
for (i in 1:nrow(route_links_with_pems)) {
  route_geom <- route_links_with_pems[i,][['geometry']]  # sfc_LINESTRING
  pems_loc <- c(route_links_with_pems[i,][['longitude']],
                route_links_with_pems[i,][['latitude']])
  new_coord <- matrix(NA, nrow=4, ncol=2)
  new_coord[1,] <- pems_loc  # PEMS
  new_coord[2,] <- sf::st_coordinates(route_geom)[1,][1:2] # A
  new_coord[3,] <- sf::st_coordinates(route_geom)[2,][1:2] # B
  new_coord[4,] <- pems_loc  # PEMS
  
  # create a new line
  my_lines <- st_linestring(new_coord)
  lines_list[[i]] <- my_lines
}

feature = sf::st_sf(route_links_with_pems, geom=sf::st_sfc(lines_list))
st_crs(feature) <- 4326

output_file <- file.path(CROSSWALK_DIR, "shapefiles", paste0(TM_LINKS_WITH_PEMS_LOCS,"_",argv$validation_year, ".shp"))
sf::write_sf(feature, output_file)
print(paste("Wrote",nrow(route_links_with_pems),"rows to",output_file))

sink(file=NULL, type=c("output","message"))
