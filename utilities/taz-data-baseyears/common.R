# Pull out some common methods for tazdata preparation here
#

# https://github.com/BayAreaMetro/modeling-website/wiki/InflationAssumptions
DOLLARS_2000_to_202X <- c(
    "2021"=1.72, 
    "2022"=1.81
)

map_ACS5year_household_income_to_TM1_categories <- function(ACS_year) {
  # Because the 2021$ and 2022$ equivalent categories don't align with the 2000$
  # categories, households within these categories will be apportioned above and below.
  # 
  # Using the ACS 5-year PUMS data, 
  # Figure out how to split household income into travel model income categories
  # https://github.com/BayAreaMetro/modeling-website/wiki/TazData
  #
  # Argument: 
  #   ACS_year: pass 2022 to use PUMS 2018-2022
  # Returns:
  #   dataframe with colums:
  #    householdinc_acs_cat: hhinc[lowerbound]_[UBupperbound], ACS category
  #    HHINCQ:               HHINCQ[1-4], travel model cateogry
  #    acs_to_hhincq_share:  In (0.0, 1.0], the share of the ACS category in that HHINQ category
  #  For example:
  #        householdinc_acs_cat HHINCQ  acs_to_hhincq_share
  #        <chr>                <chr>                 <dbl>
  #      1 hhinc000_010         HHINCQ1               1    
  #      2 hhinc010_015         HHINCQ1               1    
  #      3 hhinc015_020         HHINCQ1               1    
  #      4 hhinc020_025         HHINCQ1               1    
  #      5 hhinc025_030         HHINCQ1               1    
  #      6 hhinc030_035         HHINCQ1               1    
  #      7 hhinc035_040         HHINCQ1               1    
  #      8 hhinc040_045         HHINCQ1               1    
  #      9 hhinc045_050         HHINCQ1               1    
  #     10 hhinc050_060         HHINCQ1               0.176
  #     11 hhinc050_060         HHINCQ2               0.824
  #     12 hhinc060_075         HHINCQ2               1    
  #     13 hhinc075_100         HHINCQ2               1    
  #     14 hhinc100_125         HHINCQ2               0.154
  #     15 hhinc100_125         HHINCQ3               0.846
  #     16 hhinc125_150         HHINCQ3               1    
  #     17 hhinc150_200         HHINCQ3               0.499
  #     18 hhinc150_200         HHINCQ4               0.501
  #     19 hhinc200p            HHINCQ4               1    

  print(paste0("########################## map_ACS5year_household_income_to_TM1_categories(",ACS_year,") start ##########################"))
  # Read the PUMS data consistent with the 5-year ACS data
  PUMS_DIR <- sprintf("PUMS %d-%02d", ACS_year-4, ACS_year %% 100)
  PUMS_FILE <-sprintf("hbayarea%02d%02d.Rdata", (ACS_year-4) %% 100, ACS_year %% 100)
  PUMS_FULL_PATH <- file.path("M:/Data/Census/PUMS", PUMS_DIR, PUMS_FILE)
  load(PUMS_FULL_PATH)
  
  if (ACS_year == 2021) {
    PUMS_hhbayarea <- hbayarea1721
    rm(hbayarea1721)
  } else {
    PUMS_hhbayarea <- hbayarea
    rm(hbayarea)
  }
  print(paste0("Loaded ",nrow(PUMS_hhbayarea)," rows from",PUMS_FULL_PATH))

  PUMS_hhbayarea <- PUMS_hhbayarea %>% 
  select(NP, HINCP, ADJINC, WGTP) %>%
  filter(NP > 0) %>%     # filter out vacant units
  filter(WGTP > 0) %>%   # filter out group quarter placeholder records
  filter(HINCP >= 0) %>% # filter out negative household income
  mutate(
    # From AMERICAN COMMUNITY SURVEY 2017-2021 5-YEAR PUMS User Guide and Overview, Page 17
    # G. Note on Income and Earnings Inflation Factor (ADJINC)
    # Divide ADJINC by 1,000,000 to obtain the inflation adjustment factor and multiply it to
    # the PUMS variable value to adjust it to 2021 dollars.
    #
    # From AMERICAN COMMUNITY SURVEY 2018-2022 5-YEAR PUMS User Guide and Overview, Page 17
    # G. Note on Income and Earnings Inflation Factor (ADJINC)
    # Divide ADJINC by 1,000,000 to obtain the inflation adjustment factor and multiply it to
    # the PUMS variable value to adjust it to 2022 dollars.

    # => this is 2021 or 2022 dollars depending on ACS_year
    householdinc_202xdollars = (ADJINC/1000000.0)*HINCP,  
    # this is 2000 dollars
    householdinc_2000dollars = householdinc_202xdollars/DOLLARS_2000_to_202X[[as.character(ACS_year)]],
    # add ACS categories from household income in 202X dollars
    householdinc_acs_cat = case_when(
      (householdinc_202xdollars >=      0) & (householdinc_202xdollars <  10000) ~ "hhinc000_010",
      (householdinc_202xdollars >=  10000) & (householdinc_202xdollars <  15000) ~ "hhinc010_015",
      (householdinc_202xdollars >=  15000) & (householdinc_202xdollars <  20000) ~ "hhinc015_020",
      (householdinc_202xdollars >=  20000) & (householdinc_202xdollars <  25000) ~ "hhinc020_025",
      (householdinc_202xdollars >=  25000) & (householdinc_202xdollars <  30000) ~ "hhinc025_030",
      (householdinc_202xdollars >=  30000) & (householdinc_202xdollars <  35000) ~ "hhinc030_035",
      (householdinc_202xdollars >=  35000) & (householdinc_202xdollars <  40000) ~ "hhinc035_040", 
      (householdinc_202xdollars >=  40000) & (householdinc_202xdollars <  45000) ~ "hhinc040_045", 
      (householdinc_202xdollars >=  45000) & (householdinc_202xdollars <  50000) ~ "hhinc045_050",
      (householdinc_202xdollars >=  50000) & (householdinc_202xdollars <  60000) ~ "hhinc050_060",
      (householdinc_202xdollars >=  60000) & (householdinc_202xdollars <  75000) ~ "hhinc060_075",
      (householdinc_202xdollars >=  75000) & (householdinc_202xdollars < 100000) ~ "hhinc075_100",
      (householdinc_202xdollars >= 100000) & (householdinc_202xdollars < 125000) ~ "hhinc100_125",
      (householdinc_202xdollars >= 125000) & (householdinc_202xdollars < 150000) ~ "hhinc125_150",
      (householdinc_202xdollars >= 150000) & (householdinc_202xdollars < 200000) ~ "hhinc150_200",
      (householdinc_202xdollars >= 200000)                                       ~ "hhinc200p"
    ),
    # add TM1 categories from household income in 2000 dollars
    householdinc_TM1_cat = case_when(
      (householdinc_2000dollars >=      0) & (householdinc_2000dollars <  30000) ~ 'HHINCQ1',
      (householdinc_2000dollars >=  30000) & (householdinc_2000dollars <  60000) ~ 'HHINCQ2',
      (householdinc_2000dollars >=  60000) & (householdinc_2000dollars < 100000) ~ 'HHINCQ3',
      (householdinc_2000dollars >= 100000)                                       ~ 'HHINCQ4',
    )
  )
  print("head(PUMS_hhbayarea, n=10)")
  print(head(PUMS_hhbayarea, n=10))

  # columns are now:
  # NP, HINCP, ADJINC, WGTP, householdinc_202xdollars, householdinc_2000dollars, householdinc_acs_cat, householdinc_TM1_cat
  # calculate weighted shares
  PUMS_hhinc_cat <- PUMS_hhbayarea %>% 
    group_by(householdinc_acs_cat, householdinc_TM1_cat) %>% 
    summarise(WGTP = sum(WGTP))
  print("PUMS_hhinc_cat:")
  print(PUMS_hhinc_cat)

  # columns are now: householdinc_acs_cat, householdinc_TM1_cat, WGTP
  # move householdinc_TM1_cat values to columns
  PUMS_hhinc_cat <- PUMS_hhinc_cat %>%
    pivot_wider(names_from = householdinc_TM1_cat, values_from = WGTP, values_fill = 0) %>%
    mutate(
      TOT_WGTP = HHINCQ1 + HHINCQ2 + HHINCQ3 + HHINCQ4,
      HHINCQ1 = HHINCQ1/TOT_WGTP,
      HHINCQ2 = HHINCQ2/TOT_WGTP,
      HHINCQ3 = HHINCQ3/TOT_WGTP,
      HHINCQ4 = HHINCQ4/TOT_WGTP,
    )

  print("PUMS_hhinc_cat:")
  print(PUMS_hhinc_cat)

  # For ACS 2017-2021:
  #    householdinc_acs_cat HHINCQ1 HHINCQ2 HHINCQ3 HHINCQ4 TOT_WGTP
  #    <chr>                  <dbl>   <dbl>   <dbl>   <dbl>    <int>
  #  1 hhinc000_010           1       0       0       0        95721
  #  2 hhinc010_015           1       0       0       0        76657
  #  3 hhinc015_020           1       0       0       0        55377
  #  4 hhinc020_025           1       0       0       0        60885
  #  5 hhinc025_030           1       0       0       0        65006
  #  6 hhinc030_035           1       0       0       0        62007
  #  7 hhinc035_040           1       0       0       0        60806
  #  8 hhinc040_045           1       0       0       0        66497
  #  9 hhinc045_050           1       0       0       0        52429
  # 10 hhinc050_060           0.176   0.824   0       0       123796
  # 11 hhinc060_075           0       1       0       0       182229
  # 12 hhinc075_100           0       1       0       0       284374
  # 13 hhinc100_125           0       0.154   0.846   0       258129
  # 14 hhinc125_150           0       0       1       0       219125
  # 15 hhinc150_200           0       0       0.499   0.501   337074
  # 16 hhinc200p              0       0       0       1       753256

  # pivot for joining
  PUMS_hhinc_cat <- PUMS_hhinc_cat %>% 
    select(-TOT_WGTP) %>%
    pivot_longer(
      !householdinc_acs_cat,
      names_to  = 'HHINCQ',
      values_to = 'acs_to_hhincq_share'
    ) %>%
    filter(acs_to_hhincq_share > 0)

  print("PUMS_hhinc_cat:")
  print(PUMS_hhinc_cat)
  # Groups:   householdinc_acs_cat [16]
  #    householdinc_acs_cat HHINCQ  acs_to_hhincq_share
  #    <chr>                <chr>                 <dbl>
  #  1 hhinc000_010         HHINCQ1               1    
  #  2 hhinc010_015         HHINCQ1               1    
  #  3 hhinc015_020         HHINCQ1               1    
  #  4 hhinc020_025         HHINCQ1               1    
  #  5 hhinc025_030         HHINCQ1               1    
  #  6 hhinc030_035         HHINCQ1               1    
  #  7 hhinc035_040         HHINCQ1               1    
  #  8 hhinc040_045         HHINCQ1               1    
  #  9 hhinc045_050         HHINCQ1               1    
  # 10 hhinc050_060         HHINCQ1               0.176
  # 11 hhinc050_060         HHINCQ2               0.824
  # 12 hhinc060_075         HHINCQ2               1    
  # 13 hhinc075_100         HHINCQ2               1    
  # 14 hhinc100_125         HHINCQ2               0.154
  # 15 hhinc100_125         HHINCQ3               0.846
  # 16 hhinc125_150         HHINCQ3               1    
  # 17 hhinc150_200         HHINCQ3               0.499
  # 18 hhinc150_200         HHINCQ4               0.501
  # 19 hhinc200p            HHINCQ4               1    

  print(paste0("########################## map_ACS5year_household_income_to_TM1_categories(",ACS_year,") end ##########################"))

  return(PUMS_hhinc_cat)
}