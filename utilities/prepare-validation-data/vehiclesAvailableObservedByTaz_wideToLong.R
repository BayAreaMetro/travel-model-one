# Convert vehiclesAvailableByTazACS.csv to long form
#
# Run this in M:\Data\Census\ACS\ACS2013-2017\B08201 Household Size by Vehicles Available
#
# Relevant asana task: https://app.asana.com/0/0/1160229917303441/f
# lmz 2020.02.07

library(tidyr)
library(dplyr)

data_wide <- read.table("vehiclesAvailableByTazACS.csv", header=TRUE, sep=",", stringsAsFactors = FALSE)

# remove Total
data_wide <- select(data_wide, -Total)

# make it long and create integer column
data_long <- gather(data_wide, 
  key="key_name", value="value", c("No.vehicle","X1.vehicle","X2.vehicles","X3.vehicles","X4.or.more")) %>%
  mutate(num_vehicles=case_when(key_name == "No.vehicle"  ~ 0,
                                key_name == "X1.vehicle"  ~ 1,
                                key_name == "X2.vehicles" ~ 2,
                                key_name == "X3.vehicles" ~ 3,
                                key_name == "X4.or.more"  ~ 4))

# remove key_name column and add source column
data_long <- select(data_long, -key_name) %>% 
  mutate(source = "ACS 2013-2017") %>% 
  rename(TAZ=ZONE, num_hh=value)

write.csv(data_long, "vehiclesAvailableByTazACS_long.csv", row.names=FALSE, quote = TRUE)
