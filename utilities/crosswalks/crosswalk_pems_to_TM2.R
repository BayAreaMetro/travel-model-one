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
library(dplyr)
library(reshape)

CROSSWALK_DIR  = "M:/Crosswalks/PeMSStations_TM2network"
CROSSWALK_FILE = "crosswalk_v2.csv"
CROSSWALK_DBF  = "crosswalk_v2.dbf"

pems_locs     <- readOGR(dsn=file.path(CROSSWALK_DIR, "shapefiles"), layer="pems_stations_NAD198StatePlaneVIFIPS0406")
route_links   <- readOGR(dsn=file.path(CROSSWALK_DIR, "shapefiles"), layer="tm2_freeways")

pems_locs_df  <- as.data.frame(pems_locs) %>%
  rowid_to_column("pems_rowid") %>% 
  mutate(A_B_v1=paste0(a,"_",b))

route_links_df<- mutate(as.data.frame(route_links),
                           type_route_dir = paste(cwtype, route, direction)) %>%
  rowid_to_column("link_rowid") %>% 
  select(type_route_dir, A, B, NAME, link_rowid)

# pems has route/direction for ramps but tm2 links don't
pems_locs_df$route[     which(pems_locs_df$cwtype == "RA") ] <- NA
pems_locs_df$direction[ which(pems_locs_df$cwtype == "RA") ] <- NA

pems_locs_df <- mutate(pems_locs_df,
                       type_route_dir = paste(cwtype, route, direction))


# this produces rows (caltrans locs) x columns (route_links)
distances <- gDistance(route_links, pems_locs, byid=TRUE)
# transform them so we can join to the inner join
distances_long <- melt(distances) %>% mutate(pems_rowid=X1, link_rowid=X2+1) %>% dplyr::rename(distance=value) %>% select(-X1,-X2)

print(dim(distances))

# drop the pems locations with no lat/long since those distances will be invalid
pems_locs_df    <- pems_locs_df[ which (pems_locs_df$longitude != 0), ]

matching_routes <- inner_join(pems_locs_df, route_links_df, by="type_route_dir")
matching_routes <- left_join(matching_routes, distances_long)

# for each pems_rowid which has the minimum distance
xwalk <- matching_routes %>% group_by(pems_rowid) %>% slice(which.min(distance)) %>% as.data.frame()

# go back to original columns, plus A, B, distance
xwalk <- select(xwalk, pems_id, district, route, direction, type, cwtype, latitude, longitude, A_B_v1, A, B, distance) %>%
  dplyr::rename(distlink=distance)

# for joins
xwalk <- mutate(xwalk, A_B=paste0(A,"_",B))

# write it
write.csv(xwalk, file.path(CROSSWALK_DIR, CROSSWALK_FILE), row.names=FALSE, quote=FALSE)

library(foreign)
write.dbf(xwalk, file.path(CROSSWALK_DIR, CROSSWALK_DBF))