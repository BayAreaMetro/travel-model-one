#
# Script to map the caltrans counts locations
#    github: https://github.com/BayAreaMetro/pems-typical-weekday
#    box:    https://mtcdrive.app.box.com/share-data
# to network links in Travel Model Two (https://github.com/BayAreaMetro/travel-model-two)
# based on crosswalk type, route number and direction (e.g. mainline 101 N) and location.
#
# lmz 2017.08.18

library(sp)
library(rgdal)
library(rgeos)
library(tibble)
library(plyr)
library(dplyr)
library(reshape)

BOX_PEMS_DIR   <- "~/../Box/Share Data/pems-typical-weekday"  # Box Drive default
PEMS_DATA_FILE <- "pems_period.csv"

CROSSWALK_DIR  <- "M:/Crosswalks/PeMSStations_TM2network"
TM2_NETWORK    <- "tm2_freeways_WGS84" # See readme for how this is derived

# output files
CROSSWALK_FILE <- "crosswalk_v2.csv"
PEMS_LOCS_FILE <- "pems_locs"
PEMS_LOCS_WITH_CROSSWALK <- "pems_locs_with_crosswalk"

############# PEMS data processing first

pems_df        <- read.table(file=file.path(BOX_PEMS_DIR, PEMS_DATA_FILE), sep=",", header=TRUE)

# add unique key (e.g. "404594 4 280 N" and select out to key, lat/lon, year
pems_df        <- mutate(pems_df, key=paste(station, district, route, direction)) %>%
  select(key, station, district, route, direction, type, latitude, longitude, year)

# remove the ones without coords
pems_df        <- pems_df[!(is.na(pems_df$longitude)) | !(is.na(pems_df$latitude)),]

# select only the most recent key, so if it moves over time, we only want the most recent lat/lon
# hopefully not many do this
pems_df        <- group_by(pems_df, key) %>% arrange(desc(year))
pems_df        <- distinct(pems_df, key, .keep_all=TRUE)

# add pems_rowid and type_route_dir
pems_df <-  as.data.frame(pems_df) %>% rowid_to_column("pems_rowid") %>%
  mutate(type_route_dir = paste(type, route, direction))

# create the SpatialPointsDataFrame object
pems_locs <- SpatialPointsDataFrame(coords=pems_df[,c("longitude","latitude")], data=pems_df, proj4string = CRS("+proj=longlat +datum=WGS84"))
summary(pems_locs)
writeOGR(obj=pems_locs, dsn=file.path(CROSSWALK_DIR, "shapefiles"), layer=PEMS_LOCS_FILE, driver="ESRI Shapefile")
print(paste0("Wrote PEMS locations: ",file.path(CROSSWALK_DIR, "shapefiles", PEMS_LOCS_FILE),".shp"))

############# TM2 freeway network data processing second

# read the route links shapefile
route_links   <- readOGR(dsn=file.path(CROSSWALK_DIR, "shapefiles"), layer=TM2_NETWORK)
summary(route_links)

# set type to match pems type
route_links$type <- ""
route_links$type[ route_links$FT == 1 ] <- "FF"  # freeway-to-freeway
route_links$type[ route_links$FT == 2 ] <- "ML"  # freeway - mainline
route_links$type[ (route_links$FT == 2)&((route_links$USECLASS==2)|(route_links$USECLASS==3)) ] <- "HV" # HOV
route_links$type[ (route_links$FT==5) ] = "RA"   # generic ramp
route_links$type[ (route_links$FT==5)&(route_links$RAMP==1)] = "FR" # Off-ramp
route_links$type[ (route_links$FT==5)&(route_links$RAMP==2)] = "OR" # On-ramp
# convert to factor
route_links$type <- factor(route_links$type)
summary(route_links)

# find route and direction from the NAME
pat                   <- "(US-|CA-|I-)(\\d+)\\s*([EWNS])*"
does_match            <- grepl(pat,route_links$NAME)
route_links$route     <- sub(pattern=pat, replacement="\\2", x=route_links$NAME, perl=TRUE)
route_links$direction <- sub(pattern=pat, replacement="\\3", x=route_links$NAME, perl=TRUE)
# set to NA if no match or empty
route_links$route[     does_match==FALSE ] <- NA
route_links$direction[ does_match==FALSE ] <- NA
route_links$direction[ route_links$direction==""] <- NA
# make these factors, and routes are numeric
route_links$route     <- factor(as.numeric(route_links$route))
route_links$direction <- factor(route_links$direction)

# these are the non-matching
# route_links$NAME[ does_match==FALSE]

# set A_B
route_links$A_B <- paste0(route_links$A,"_",route_links$B)

summary(route_links)

# add link_rowid for dataframe and select out the relevant fields
route_links_df<- mutate(as.data.frame(route_links)) %>%
  rowid_to_column("link_rowid")
  select(type, route, direction, A, B, NAME, link_rowid)

# For ramps, PEMS labels the ramp route/direction based on the freeway. Try to intelligently update network links similarly.
fwy_links_df   <- route_links_df[ (route_links_df$route != 0)&(!is.na(route_links_df$direction)), ]


# join ramp links B to fwy A for on ramps
route_links_df  <- left_join(route_links_df, fwy_links_df, by=(c("B"="A")), suffix=c("","_tofwy"))
# and A to fwy B for off ramps
route_links_df  <- left_join(route_links_df, fwy_links_df, by=(c("A"="B")), suffix=c("","_frfwy"))

## straightforward on-ramps and off-ramps -- inherite the route and direction and get type
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
xwalk <- select(xwalk, station, district, route, direction, type, latitude, longitude, A, B, distance) %>%
  dplyr::rename(distlink=distance)

# for joins
xwalk <- mutate(xwalk, A_B=paste0(A,"_",B))

# write it
write.csv(xwalk,   file.path(CROSSWALK_DIR, CROSSWALK_FILE), row.names=FALSE, quote=FALSE)
print(paste0("Wrote crosswalk: ",file.path(CROSSWALK_DIR, CROSSWALK_FILE)))

# write pems_loc joined with xwalk as shapefile
pems_df            <- left_join(pems_df, xwalk)
pems_locs$A        <- pems_df$A
pems_locs$B        <- pems_df$B
pems_locs$A_B      <- pems_df$A_B
pems_locs$distlink <- pems_df$distlink

writeOGR(obj=pems_locs, dsn=file.path(CROSSWALK_DIR, "shapefiles"), layer=PEMS_LOCS_WITH_CROSSWALK, driver="ESRI Shapefile")
print(paste0("Wrote PEMS locations with crosswalk: ",file.path(CROSSWALK_DIR, "shapefiles", PEMS_LOCS_WITH_CROSSWALK),".shp"))


