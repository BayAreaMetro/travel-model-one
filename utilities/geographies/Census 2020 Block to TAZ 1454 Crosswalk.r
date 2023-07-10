# Census 2020 Block to TAZ 1454 Crosswalk.r

# Packages and output directory

library(tidycensus)
library(tidyverse)
library(sf)

output_location <- "M:/Data/GIS layers/TM1_taz_census2020/2020block_to_TAZ1454.csv"

# Set your Census API key
api_key <- readLines("M:/Data/Census/API/api-key.txt")

# Assign county and state variables

baycounties <- c("01","13","41","55","75","81","85","95","97")
state_code <- "06" 

# Retrieve the Census data and geometry

block <- get_decennial(geography = "block", 
                       state = state_code,
                       county = baycounties,
                       variables = "P1_001N",
                       geometry = TRUE,
                       year = 2020,
                       sumfile = "dhc")

# Bring in TAZ 1454 shapefile and project block file to same projection (26910) 
# Convert block geometries to centroids and join to TAZ1454 file using "nearest feature" to prevent duplicates
# Add block group and tract IDs, remove geometry, output file

TAZ1454_shapefile_path <- "M:/Data/GIS layers/Travel_Analysis_Zones_(TAZ1454)/Travel Analysis Zones.shp"
TAZ1454_shapefile <- st_read(TAZ1454_shapefile_path) %>% 
  select(SUPERD,TAZ1454)

block_proj <- st_transform(block,crs = st_crs(TAZ1454_shapefile))

# Convert block to centroid for easier spatial matching

block_proj <- st_centroid(block_proj)

output <- st_join(block_proj,TAZ1454_shapefile,join = st_nearest_feature, maxdist=1) %>% 
  mutate(
    blockgroup = substr(GEOID,1,12),
    tract = substr(GEOID,1,11)) %>% 
  rename(block_POPULATION=value) %>% 
  relocate(c(TAZ1454,SUPERD,block_POPULATION),.after = tract) 

st_geometry(output) <- NULL

write.csv(output,output_location,row.names = FALSE)
