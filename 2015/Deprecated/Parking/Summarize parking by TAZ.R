# Summarize parking by TAZ.R
# SUmmarize MAZ to TAZ parking for 2015 TAZ data
# SI
# December 17, 2018

# Import Libraries

suppressMessages(library(tidyverse))

# Set working directory

wd                   <- "X:/petrale/output/"
setwd(wd)

# Bring in data

USERPROFILE          <- Sys.getenv("USERPROFILE")
BOX_TM               <- file.path(USERPROFILE, "Box", "Modeling and Surveys", "Development", "Travel Model Two Development")
Parking_MAZ_2010     <- file.path(BOX_TM, "Observed Data",   "Parking Inventory", "parkingData.csv")

# File path for MAZ/TAZ equivalency

EQ                   <- "M:/Crosswalks/taz1454/MAZ2.2_TAZ1454_equiv.csv"

# Import data and equivalency

parking_raw <- read.csv(Parking_MAZ_2010, header = TRUE, stringsAsFactors = FALSE)
equiv <- read.csv(EQ,header = TRUE,stringsAsFactors = FALSE) %>%
  rename(MAZ=maz)

# CPI for 2000 and 2010 to convert parking to 2000$

CPI_2000 <- 180.20 # CPI value for 2000
CPI_2010 <- 227.47  # CPI value for 2010
CPI_00_10 <- CPI_2000/CPI_2010 # 2017 CPI/2000 CPI

# Join equivalency to parking data
# Summarize MAZ parking data to TAZ
# Apply weighted median to price, by number of parking spaces
# Discount costs (in cents) by 2010 to 2000 CPI adjustment

parking_raw_eq <- left_join(parking_raw,equiv,by="MAZ") %>%
  mutate(hparkcost = if_else(hparkcost>dparkcost,dparkcost,hparkcost))      # If hourly > than daily, make hourly = daily

parking2000 <- parking_raw_eq %>%
  group_by(TAZ1454) %>%                                                     # Group by TAZ
  summarize(freq=n(),average_hourly=weighted.mean(hparkcost,hstallsoth),    # Weighted mean by number of parking stalls
            average_daily=(weighted.mean(dparkcost,dstallsoth))/8) %>%      # Divide by 8 hours for daily -> hourly
  mutate_if(is.numeric, replace_na, 0) %>% mutate(                          # Convert divide by zero errors to 0
    PRKCST=CPI_00_10*average_daily,                                         # Deflate 2010$ to 2000$ for long-term
    OPRKCST=CPI_00_10*average_hourly                                        # Deflate 2010$ to 2000$ for short-term 
      )

output <- data.frame(TAZ1454=1:1454) %>%                                    # Create full TAZ file for merging
  left_join(.,parking2000, by="TAZ1454") %>%                                # Create clean output file for later merging
  mutate_if(is.numeric, replace_na, 0) %>%                                  # Replace missing values with 0
  select(TAZ1454,PRKCST,OPRKCST)                                            # Select only parking cost fields

# Output file

write.csv(output, "TAZ1454 2015 Parking Cost.csv", row.names = FALSE, quote = T)

