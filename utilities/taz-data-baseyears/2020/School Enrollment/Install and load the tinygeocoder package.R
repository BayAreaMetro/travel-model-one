# Install and load the 'tidygeocoder' package
library(tidygeocoder)

# Function to convert addresses to latitude and longitude
geocode_address <- function(address) {
  result <- geocode(address)
  if (!is.na(result$lat) & !is.na(result$lon)) {
    return(c(result$lat, result$lon))
  } else {
    return(NA)
  }
}

# Example usage
address <- "2050 Lincoln Avenue,Alameda,CA"
geo(address = address,method="census")
coordinates <- geocode_address(address)

library(dplyr)
library(tidygeocoder)
dc_addresses <- tribble( ~name,~addr,
                         "White House", "2050 Lincoln Avenue,Alameda,CA",
                         "National Academy of Sciences", "2101 Constitution Ave NW, Washington, DC 20418",
                         "Department of Justice", "950 Pennsylvania Ave NW, Washington, DC 20530",
                         "Supreme Court", "1 1st St NE, Washington, DC 20543",
                         "Washington Monument", "2 15th St NW, Washington, DC 20024")
coordinates <- dc_addresses %>%
  geocode(addr)
