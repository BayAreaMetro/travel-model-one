
# Import block group data.R
# Read in CSV "2015" TAZ block group data from ACS 2013-2017, rather than having to run the API import step 
# SI
# December 17, 2018

#Import CSVs getting class right for geographies (so as not to lose leading 0s)

bg_df1 <- read.csv("ACS 2013-2017 Block Group Vars1.csv",header=TRUE, stringsAsFactors = FALSE,
                   colClasses = c("tract" = "character","state" = "character","county" = "character", "block.group" = "character"))


bg_df2 <- read.csv("ACS 2013-2017 Block Group Vars2.csv",header=TRUE, stringsAsFactors = FALSE,
                   colClasses = c("tract" = "character","state" = "character","county" = "character", "block.group" = "character"))



bg_df3 <- read.csv("ACS 2013-2017 Block Group Vars3.csv",header=TRUE, stringsAsFactors = FALSE,
                   colClasses = c("tract" = "character","state" = "character","county" = "character", "block.group" = "character"))

# Rename block.group to block group, so rest of ACS 2013-2017 create TAZ data for 2015.R code works

bg_df1 <- bg_df1 %>%
  rename("block group" = "block.group")

bg_df2 <- bg_df2 %>%
  rename("block group" = "block.group")

bg_df3 <- bg_df3 %>%
  rename("block group" = "block.group")
