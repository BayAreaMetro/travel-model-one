library(tidycensus)
library(tidyverse)
library(sf)

# Set your Census API key
api_key <- readLines("M:/Data/Census/API/api-key.txt")

# Get county and state variables

baycounties <- c("01","13","41","55","75","81","85","95","97")
state       <- "06" 

# Retrieve the Census data
data <- get_decennial(
  year = year,
  dataset = dataset,
  variables = c("NAME", "P001001"),
  geography = "block",
  state = state,
  key = api_key
)

# Convert the data to a tibble (tidy data frame)
df <- as_tibble(data)

# Rename the columns for clarity
df <- rename(df, Geography = NAME, Population = P001001)

# Save the tibble to a CSV file
write.csv(df, file = "census_block_population.csv", row.names = FALSE)

# Display the first few rows of the tibble
head(df)

v16 <- load_variables(2020,dataset = "dhc")

block <- get_decennial(geography = "block", 
                       state = "06",
                       county = baycounties,
                       variables = "P1_001N",
                       geometry = TRUE,
                       year = 2020,
                       sumfile = "dhc")

block_group <- get_decennial(geography = "block group", 
                             state = "06",
                             county = baycounties,
                             variables = "P1_001N",
                             geometry = TRUE,
                             year = 2020,
                             sumfile = "dhc")

county <- get_decennial(geography = "county", 
                       state = "06",
                       county = baycounties,
                       variables = "P1_001N", 
                       year = 2020,
                       sumfile = "dhc")

block_proj <- st_transform(block,crs = 26910)

TAZ1454_shapefile_path <- "M:/Data/GIS layers/Travel_Analysis_Zones_(TAZ1454)/Travel Analysis Zones.shp"
TAZ1454_shapefile <- st_read(TAZ1454_shapefile_path) %>% 
  select(SUPERD,TAZ1454)

block_centroid <- st_centroid(block_proj)

trial <- st_join(block_centroid,TAZ1454_shapefile,join = st_nearest_feature, maxdist=1) 

st_join(survey_coords_spatial, tracts_proj, join = st_nearest_feature, maxdist=100)

block2010 <- get_decennial(geography = "block", 
                       state = "06",
                       county = baycounties,
                       variables = "P001001",
                       year = 2010,
                       sumfile = "sf1")

block <- get_decennial(geography = "block", 
                       state = "06",
                       county = baycounties,
                       variables = "P1_001N",
                       year = 2020,
                       sumfile = "dhc")

block_group <- get_decennial(geography = "block group", 
                             state = "06",
                             county = baycounties,
                             variables = "P1_001N",
                             year = 2020,
                             sumfile = "dhc")

tract <- get_decennial(geography = "tract", 
                             state = "06",
                             county = baycounties,
                             variables = "P1_001N",
                             year = 2020,
                             sumfile = "dhc")


block_analyze <- block %>% mutate(
    blockgroup = substr(GEOID,1,12),
    tract = substr(GEOID,1,11)) %>% 
  group_by(blockgroup) %>% 
  summarize(total_summed=sum(value))

trial2 <- left_join(block_group,block_analyze,by=c("GEOID"="blockgroup"))

block_analyze2 <- block %>% mutate(
  blockgroup = substr(GEOID,1,12),
  tract = substr(GEOID,1,11)) %>% 
  group_by(tract) %>% 
  summarize(total_summed=sum(value))

trial2 <- left_join(tract,block_analyze2,by=c("GEOID"="tract"))
