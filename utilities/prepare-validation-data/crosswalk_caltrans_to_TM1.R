#
# Script to map the caltrans counts locations
#    github: https://github.com/BayAreaMetro/caltrans-typical-weekday-counts
#    box:    https://mtcdrive.app.box.com/share-data
# to network links in Travel Model One (https://github.com/BayAreaMetro/travel-model-one)
# based on route number and direction (e.g. 101 N) and location.
#
# lmz 2017.08.18

library(sp)
library(rgdal)
library(rgeos)
library(tibble)
library(dplyr)
library(reshape)

CROSSWALK_DIR  <- "M:/Crosswalks/CaltransCountLocations_TM1network"
TM_NETWORK_DIR <- "M:/Application/Model One/Networks/TM1_2015_Base_Network"
TM_NETWORK     <- "TM1_numberedRoutes_wgs84"

# output files
CROSSWALK_FILE <- "typical-weekday-counts-xy-TM1link.csv"

caltrans_locs <- readOGR(dsn=file.path(CROSSWALK_DIR,  "shapefiles"), layer="caltrans_locations_nad1983UTMzone10N")
route_links   <- readOGR(dsn=file.path(TM_NETWORK_DIR, "shapefile"),  layer=TM_NETWORK)

caltrans_locs_df <- mutate(as.data.frame(caltrans_locs), 
                           route_dir = paste(routeNumbe, direction)) %>% rowid_to_column("caltrans_rowid")
route_links_df   <- mutate(as.data.frame(route_links),
                           route_dir = paste(ROUTENUM, ROUTEDIR)) %>% rowid_to_column("link_rowid")

# recode some of these
caltrans_locs_df$route_dir[caltrans_locs_df$route_dir=="84 N"] <- "84 W"
caltrans_locs_df$route_dir[caltrans_locs_df$route_dir=="84 S"] <- "84 E"

# this produces rows (caltrans locs) x columns (route_links)
distances <- gDistance(route_links, caltrans_locs, byid=TRUE)
# transform them so we can join to the inner join
distances_long <- melt(distances) %>% mutate(caltrans_rowid=X1, link_rowid=X2+1) %>% dplyr::rename(distance=value)

print(dim(distances))

matching_routes <- inner_join(caltrans_locs_df, route_links_df, by="route_dir")
matching_routes <- left_join(matching_routes, distances_long)

# for each caltrans_rowid which has the minimum distance
xwalk <- matching_routes %>% group_by(caltrans_rowid) %>% slice(which.min(distance)) %>% as.data.frame()

# go back to original columns, plus A, B, distance
xwalk <- select(xwalk, latitude, longitude, countyCode, postmileVa, routeNumbe, direction, postmileSu, link_rowid, A, B, distance) %>%
  dplyr::rename(routeNumber=routeNumbe, postmileValue=postmileVa, postmileSuffix=postmileSu, dist_from_link=distance)

# for joins
xwalk <- mutate(xwalk, A_B=paste0(A,"_",B))

# write it
write.csv(xwalk, file.path(CROSSWALK_DIR, CROSSWALK_FILE), row.names=FALSE, quote=FALSE)