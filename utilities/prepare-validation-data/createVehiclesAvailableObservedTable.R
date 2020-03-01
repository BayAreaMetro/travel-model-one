# Simple script to convert the downloaded text file for ACS 2013-2017 table B08201 to a simple table with
# tracts and households per vehicles available.  Saved in dbf for easy joining in ArcGIS.
#
# Run this in M:\Data\Census\ACS\ACS2013-2017\B08201 Household Size by Vehicles Available
#
# Relevant asana task: https://app.asana.com/0/0/1160229917303441/f
# lmz 2020.02.06

library(dplyr)
library(foreign) # for dbf

# read the data file
DATA_FILE     <- file.path("downloaded", "ACSDT5Y2017.B08201_data_with_overlays_2020-02-05T184915.csv")
b08201_head   <- read.table(file=DATA_FILE, sep=",", header=TRUE, nrows=2)              # read the header
b08201_df     <- read.table(file=DATA_FILE, sep=",", skip=2, stringsAsFactors=FALSE)    # and the actual data

colnames(b08201_df) <- colnames(b08201_head)

# just keep a few columns and rename
b08201_df <- select(b08201_df, GEO_ID, NAME, B08201_001E, B08201_002E, B08201_003E, B08201_004E, B08201_005E, B08201_006E) %>%
  rename("Total"                       =B08201_001E,
         "No vehicle available"        =B08201_002E,
         "1 vehicle available"         =B08201_003E,
         "2 vehicles available"        =B08201_004E,
         "3 vehicles available"        =B08201_005E,
         "4 or more vehciles available"=B08201_006E)

# tract shapefile has geod starting after US: 1400000US06001400100
b08201_df <- mutate(b08201_df, geoid_short=substr(GEO_ID,10,40))

write.csv(b08201_df, "vehiclesAvailable.csv", row.names=FALSE, quote = TRUE)
write.dbf(b08201_df, "vehiclesAvailable.dbf", factor2char=TRUE)
