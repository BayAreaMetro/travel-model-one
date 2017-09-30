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
pems_df        <- read.table(file=file.path(BOX_PEMS_DIR, "pems_period.csv"), sep=",", header=TRUE)

# add unique key (e.g. "404594 4 280 N" and select out to key, lat/lon, year
pems_df        <- mutate(pems_df, key=paste(station, district, route, direction)) %>%
  select(key, station, district, route, direction, type, latitude, longitude, year)

# remove the ones without coords
pems_df        <- pems_df[!(is.na(pems_df$longitude)) | !(is.na(pems_df$latitude)),]

# select only the most recent key, so if it moves over time, we only want the most recent lat/lon
# hopefully not many do this
pems_df        <- group_by(pems_df, key) %>% arrange(desc(year))
pems_df        <- distinct(pems_df, key, .keep_all=TRUE)

# define cwtype to match the one on the shapefile
#  type  =FF FR HV ML OR
#  cwtype=FF RA HV ML RA
pems_df$cwtype <- revalue(pems_df$type, c("FF"="FF","HV"="HV","ML"="ML","FR"="RA","OR"="RA"))

# add pems_rowid and type_route_dir
pems_df <-  as.data.frame(pems_df) %>% rowid_to_column("pems_rowid") %>%
  mutate(type_route_dir = paste(cwtype, route, direction))

# pems has route/direction for ramps but tm2 links don't -- type_route_dir should just be RA
pems_df$type_route_dir[ pems_df$cwtype=="RA" ] <- "RA"

# create the SpatialPointsDataFrame object
pems_locs <- SpatialPointsDataFrame(coords=pems_df[,c("longitude","latitude")], data=pems_df, proj4string = CRS("+proj=longlat +datum=WGS84"))


CROSSWALK_DIR  = "M:/Crosswalks/PeMSStations_TM2network"
CROSSWALK_FILE = "crosswalk_v2.csv"
CROSSWALK_DBF  = "crosswalk_v2.dbf"

# pems_locs     <- readOGR(dsn=file.path(CROSSWALK_DIR, "shapefiles"), layer="pems_stations_NAD198StatePlaneVIFIPS0406")
route_links   <- readOGR(dsn=file.path(CROSSWALK_DIR, "shapefiles"), layer="tm2_freeways_WGS84")

route_links_df<- mutate(as.data.frame(route_links),
                           type_route_dir = paste(cwtype, route, direction)) %>%
  rowid_to_column("link_rowid")

# RA links should just be RA
route_links_df$type_route_dir[ route_links_df$cwtype=="RA" ] <- "RA"

route_links_df <- select(route_links_df, type_route_dir, A, B, NAME, link_rowid)

# this produces rows (caltrans locs) x columns (route_links)
distances <- gDistance(route_links, pems_locs, byid=TRUE)
# transform them so we can join to the inner join
distances_long <- melt(distances) %>% mutate(pems_rowid=X1, link_rowid=X2+1) %>% dplyr::rename(distance=value) %>% select(-X1,-X2)

print(dim(distances))


matching_routes <- inner_join(pems_df, route_links_df, by="type_route_dir")
matching_routes <- left_join(matching_routes, distances_long)

# for each pems_rowid which has the minimum distance
xwalk <- matching_routes %>% group_by(pems_rowid) %>% slice(which.min(distance)) %>% as.data.frame()

# go back to original columns, plus A, B, distance
xwalk <- select(xwalk, station, district, route, direction, type, cwtype, latitude, longitude, A, B, distance) %>%
  dplyr::rename(distlink=distance)

# for joins
xwalk <- mutate(xwalk, A_B=paste0(A,"_",B))

# write it
write.csv(xwalk, file.path(CROSSWALK_DIR, CROSSWALK_FILE), row.names=FALSE, quote=FALSE)

library(foreign)
write.dbf(xwalk, file.path(CROSSWALK_DIR, CROSSWALK_DBF))