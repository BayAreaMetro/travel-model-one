# Pull out some common methods for tazdata preparation here
#

# https://github.com/BayAreaMetro/modeling-website/wiki/InflationAssumptions
DOLLARS_2000_to_202X <- c(
  "2021"=1.72, 
  "2022"=1.81
)

censuskey    <- readLines("M:/Data/Census/API/api-key.txt")
baycounties  <- c("01","13","41","55","75","81","85","95","97")
state        <- "06"
census_api_key(censuskey, install = TRUE, overwrite = TRUE)

# Bring in 2020 block/TAZ equivalency, create block group ID and tract ID fields for later joining to ACS data
# Add zero on that is lost in CSV conversion
# Remove San Quentin block from file and move other blocks with population in TAZ 1439 to adjacent 1438

BLOCK2020_to_TAZ1454_FILE <- "M:/Data/GIS layers/TM1_taz_census2020/2020block_to_TAZ1454.csv"
BLOCK2020_TAZ1454 <- read.csv(
  BLOCK2020_to_TAZ1454_FILE,
  header=TRUE, 
  colClasses=c("GEOID"="character","blockgroup"="character","tract"="character")) %>% 
filter (!(NAME=="Block 1007, Block Group 1, Census Tract 1220, Marin County, California")) %>%  # San Quentin block
mutate(TAZ1454=case_when(
  NAME=="Block 1006, Block Group 1, Census Tract 1220, Marin County, California"   ~ as.integer(1438),
  NAME=="Block 1002, Block Group 1, Census Tract 1220, Marin County, California"   ~ as.integer(1438),
  TRUE                                                                             ~ TAZ1454)
)

# columns are: GEOID, NAME, variable, blockgroup, tract, TAZ1454, SUPERD, block_POPULATION
# e.g.
#               GEOID                                                                         NAME variable   blockgroup       tract TAZ1454 SUPERD block_POPULATION
#   1 060855017001008 Block 1008, Block Group 1, Census Tract 5017, Santa Clara County, California  P1_001N 060855017001 06085501700     560     11                0
#   2 060855109001003 Block 1003, Block Group 1, Census Tract 5109, Santa Clara County, California  P1_001N 060855109001 06085510900     360      8               81
#   3 060014351032020  Block 2020, Block Group 2, Census Tract 4351.03, Alameda County, California  P1_001N 060014351032 06001435103     820     17                0
#   4 060014305003017     Block 3017, Block Group 3, Census Tract 4305, Alameda County, California  P1_001N 060014305003 06001430500     853     17              116
#   5 060014506071030  Block 1030, Block Group 1, Census Tract 4506.07, Alameda County, California  P1_001N 060014506071 06001450607     739     15                0
#   6 060014507451018  Block 1018, Block Group 1, Census Tract 4507.45, Alameda County, California  P1_001N 060014507451 06001450745     743     15              140

print("BLOCK2020_TAZ1454:")
print(head(BLOCK2020_TAZ1454))

### Function to fix rounding artifacts for columns which should sum to a total column
# For example, if we have col_a = 2.3 => 2, col_b = 3.4 => 3, col_c = 4.3 => 4, tot_col = 10 
# but the sum of the rounded cols is only 9. So this would allocate the additional 1 to the largest col, or col_c.
#
# usage: adjusted <- fix_rounding_artifacts(my_data, "tot_col", c("col_a", "col_b", "col_c"))
fix_rounding_artifacts <- function(df, id_var, sum_var, partial_vars) {
  print(paste("fix_rounding_artifacts(id_var=", id_var, ", sum_var=", sum_var, 
    ", partial_vars=",toString(partial_vars),")"))

  original_order <- colnames(df)

  # select the columns we care about
  my_df <- df %>% select(all_of(c(id_var, sum_var, partial_vars)))
  my_df <- my_df %>%
    rowwise() %>%
    mutate(
      # this will be the column name with the max value out of the columns listed in partial_vars
      max_col = names(my_df)[which.max(c_across(all_of(partial_vars)))+2],
      # this is the discrepancy between partial vars and sum_var to be resolved
      diff_col = get(sum_var) - sum(c_across(all_of(partial_vars)))
    ) %>% ungroup()
  # these are the rows that need updating
  print("Rows needing updating:")
  print(filter(my_df, diff_col != 0))

  # for each column in partial_vars, update the value by diff if max_col matches
  for (partial_name in partial_vars) {
    my_df <- my_df %>% mutate(
      my_diff_col = ifelse(max_col==partial_name, diff_col, 0),
      !!sym(partial_name) := .data[[partial_name]] + my_diff_col,
    )
  }
  # print(filter(my_df, diff_col != 0))

  # verify things worked by recalculating diff_col
  my_df <- my_df %>% 
    rowwise() %>%
    mutate(
      diff_col = get(sum_var) - sum(c_across(all_of(partial_vars)))
    ) %>% ungroup()
  stopifnot(all(my_df$diff_col == 0))
  # verified!

  # select to just id_var, partial_vars
  my_df <- my_df %>% select(all_of(c(id_var, partial_vars)))

  # replace the partial_vars in the original df
  df <- df %>% select(-any_of(partial_vars)) %>% 
    left_join(., my_df, by=id_var)

  # keep columns in same order
  df <- df %>% select(all_of(original_order))

  return(df)
}

# Scales a column in a source dataframe to match a target dataframe, including component columns
# source_df: a dataframe with columns id_var, sum_var, partial_vars where partial_vars sum to sum_var
# target_df: a dataframe with columns id_var, sum_var_target
# returns: source_df with sum_var == sum_var_target and partial_vars have the same distribution but still add to sum_var
scale_data_to_targets <- function(source_df, target_df, id_var, sum_var, partial_vars) {
  print(paste("scale_data_to_targets(id_var=",id_var,", sum_var=",sum_var,", partial_vars=",toString(partial_vars),")"))

  sum_var_target <- paste0(sum_var,"_target")
  # add the sum_var_target column into the source table
  source_df <- left_join(
    source_df, 
    select(target_df, all_of(c(id_var, sum_var_target))),
    by=id_var
  )
  print("source_df before:")
  print(select(source_df, all_of(c(id_var, sum_var, sum_var_target, partial_vars))))
  # scale the sum_var
  source_df <- source_df %>% mutate(
    target_scale = get(sum_var_target) / get(sum_var),
    !!sym(sum_var) := as.integer(round(.data[[sum_var]] * target_scale))
  )
  # and the partial vars and round
  for (partial_name in partial_vars) {
    source_df <- source_df %>% mutate(
      !!sym(partial_name) := as.integer(round(.data[[partial_name]] * target_scale))
    )
  }
  # fix rounding artifacts
  source_df <- fix_rounding_artifacts(source_df, id_var, sum_var, partial_vars)

  print("source_df after:")
  print(select(source_df, all_of(c(id_var, sum_var, sum_var_target, partial_vars))))
  source_df <- source_df %>% select(-all_of(sum_var_target)) # remove target column from source

  return(source_df)
}

# Given a disaggregate source_df (e.g. TAZ-level) and a more aggregate (county-level) target_df, 
# this function updates source_df by modifying the column named by col_name so the source_df
# matches the target_df for aggregate_id_var.
# * source_df must have columns: disagg_id_var (unique), agg_id_var (not unique), col_name
# * target_df must have columns: agg_id_var (unique), col_name_diff
# This function will increase or decrease component source_df rows by col_name_diff,
# keeping the distribution the same across rows (TAZs)
update_disaggregate_data_to_aggregate_targets <- function(source_df, target_df, disagg_id_var, agg_id_var, col_name) {
  print(sprintf("update_disaggregate_data_to_aggregate_targets(disagg_id_var=%s, agg_id_var=%s, col_name=%s)",
    disagg_id_var, agg_id_var, col_name))

  diff_col_name <- paste0(col_name,"_diff")
  # loop through aggregate_id_var
  agg_id_var_list <- target_df %>% pull(!!sym(agg_id_var))
  for (agg_id_value in agg_id_var_list) {
    diff_value <- target_df %>% filter(get(agg_id_var) == agg_id_value) %>% pull(!!sym(diff_col_name))
    if (diff_value == 0) { next }

    # these are the rows for this agg_id_value from which to sample
    filtered_source_df <- source_df %>% 
      select(all_of(c(disagg_id_var, agg_id_var, col_name))) %>% 
      filter(get(agg_id_var) == agg_id_value) %>%
      filter(get(col_name) > 0)

    print(sprintf("  Processing agg_id_value=%20s with diff=%8d; filtered_source_df has %4d rows",
      agg_id_value,diff_value,nrow(filtered_source_df)))
    # nothing to draw from
    if (nrow(filtered_source_df) == 0) { next }

    # sample the rows to modify (add or remove) - these are the TAZs
    modify_sample <- filtered_source_df %>% slice_sample(
      n=abs(diff_value),
      replace=TRUE,
      weight_by=!!sym(col_name)
    )
    # aggregate to TAZ
    modify_sample <- modify_sample %>% group_by(!!sym(disagg_id_var)) %>% summarise(TO_MODIFY = n())
    # print(paste("modify_sample len=", nrow(modify_sample)))
    # print(modify_sample)

    # join to source, which now has column TO_MODIFY
    source_df <- left_join(source_df, modify_sample, by=disagg_id_var) %>% 
      mutate(TO_MODIFY = replace_na(TO_MODIFY, 0))

    # make the modification
    if (diff_value > 0) {
      source_df <- source_df %>% mutate(!!sym(col_name) := .data[[col_name]] + TO_MODIFY)
    } else if (diff_value < 0) {
      source_df <- source_df %>% mutate(!!sym(col_name) := .data[[col_name]] - TO_MODIFY)
      source_df <- source_df %>% mutate(!!sym(col_name) := ifelse(!!sym(col_name) < 0, 0, !!sym(col_name)))
    }
    source_df <- source_df %>% select(-TO_MODIFY)
  }
  
  # verify
  # print("Result:")
  # print(source_df %>% group_by(!!sym(agg_id_var)) %>% summarise(total = sum(!!sym(col_name))))
  return(source_df)
}

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
map_ACS5year_household_income_to_TM1_categories <- function(ACS_year) {

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

# Perform a simple check of consistency between EMPRES and hh_wrks_0, hh_wrks_1, hh_wrks_2, hh_wrks_3_plus
# by looking at implied number of workers in households with 3+ workers
# and implied number of workers per household in those households
# Required df columns: ZONE, County_Name, EMPRES, TOTHH, hh_wrks_0, hh_wrks_1, hh_wrks_2, hh_wrks_3_plus
# PUMS_COUNTY_3P_WORKERS has columns County_Name, avg3p
check_consistency_empres_hhworkers <- function(df, PUMS_COUNTY_3P_WORKERS) {

  df_with_check <- df %>% 
  select(ZONE, County_Name, EMPRES, TOTHH, hh_wrks_0, hh_wrks_1, hh_wrks_2, hh_wrks_3_plus) %>% 
  left_join(., PUMS_COUNTY_3P_WORKERS, by=c("County_Name")) %>%
  mutate(
    # verify (hh_wrks_0 + hh_wrks_1 + hh_wrks_2 + hh_wrks_3_plus == TOTHH)
    sum_hh_wrks = hh_wrks_0 + hh_wrks_1 + hh_wrks_2 + hh_wrks_3_plus,
    # number of workers in households with 3+ workers
    implied_min_workers     = (1*hh_wrks_1) + (2*hh_wrks_2) + (3*hh_wrks_3_plus),
    estimated_total_workers = (1*hh_wrks_1) + (2*hh_wrks_2) + (avg3p*hh_wrks_3_plus),
  ) %>% 
  select( # reorder
    ZONE, County_Name, hh_wrks_0, hh_wrks_1, hh_wrks_2, hh_wrks_3_plus, 
    TOTHH, sum_hh_wrks, 
    EMPRES, implied_min_workers, estimated_total_workers)
  print("###### check_consistency_empres_hhworkers: implied_min_workers, estimate_total_workers:")
  print(df_with_check)

  print("by county:")
  print(df_with_check %>% group_by(County_Name) %>% summarize(
    TOTHH                  =sum(TOTHH),
    sum_hh_wrks            =sum(sum_hh_wrks),
    EMPRES                 =sum(EMPRES),
    implied_min_workers    =sum(implied_min_workers),
    estimated_total_workers=sum(estimated_total_workers))
  )

  # print out lines with EMPRES < implied_min_workers
  print("df_with_check with EMPRES < implied_min_workers")
  print(filter(df_with_check, EMPRES < implied_min_workers))

  # print out lines with EMPRES > estimated_total_workers
  print("df_with_check with EMPRES > estimated_total_workers")
  print(filter(df_with_check, EMPRES > estimated_total_workers))
}

# Apply households by number of workers correction factors
# The initial table values are actually households by number of "commuters" 
# (people at work - not sick, vacation - in the ACS reference week)
# This overstates 0-worker households and understates 3+-worker households.
# A correction needs to be applied.
correct_households_by_number_of_workers <- function(df) {

  # TODO: Implement this directly rather in excel
  counties  <- c(1,2,3,4,5,6,7,8,9)  # Matching county values for factor ordering

  workers0  <- c(0.80949, 0.73872, 0.71114, 0.64334, 0.83551, 0.81965, 0.79384, 0.86188, 0.84022)
  workers1  <- c(1.04803, 1.02080, 1.04346, 1.05696, 1.00905, 1.03175, 1.08663, 1.02549, 1.04765)
  workers2	<- c(1.04826, 1.07896, 1.05444, 1.11641, 1.06367, 1.04932, 1.03722, 1.06810, 1.06777)
  workers3p	<- c(1.12707, 1.16442, 1.15440, 1.22406, 1.15324, 1.18291, 1.14513, 1.10387, 1.11526)

  df <- df %>%
    left_join(.,select(TAZ_SD_COUNTY,ZONE,COUNTY,County_Name),by=c("TAZ1454"="ZONE")) %>% 
    mutate(
      hh_wrks_0      = hh_wrks_0*workers0[match(COUNTY,counties)], # Apply the above index values for correction factors
      hh_wrks_1      = hh_wrks_1*workers1[match(COUNTY,counties)],
      hh_wrks_2      = hh_wrks_2*workers2[match(COUNTY,counties)],
      hh_wrks_3_plus = hh_wrks_3_plus*workers3p[match(COUNTY,counties)]) 
    
  return(df)
}

# source_df is a TAZ-based tibble including columns:
#   id variables: County_Name, TAZ1454, 
#   GQ variables: gq_type_[univ,mil,othnon], gqpop         
#   total population variables: AGE[0004,0519,2044,4564,65P], sum_age 
#   total employed resident variables: pers_occ_[management,professional,services,retail,manual,military], EMPRES
#   TODO: race/ethnicity variables should be done as well but I don't think they're used
# target_GQ_df is a tibble with columns County_Name, GQPOP, GQPOP_target, GQPOP_diff
# ACS_PUMS_1year is the year corresponding to the target; we'll use the ACS PUMS 1-year data
#   distributions for GQ workers to make these updates.
update_gqop_to_county_totals <- function(source_df, target_GQ_df, ACS_PUMS_1year) {

  print(paste0("########################## update_ggop_to_county_totals(",ACS_PUMS_1year,") ##########################"))
  # copy only needed target columns
  target_df <- select(target_GQ_df, County_Name, GQPOP, GQPOP_target, GQPOP_diff)

  # this file is output by 
  # GitHub\census-tools-for-planning\analysis_by_topic\summarize_noninst_group_quarters.R
  GQ_PUMS1YEAR_FILE <- file.path("M:/Data/Census/PUMS",
    sprintf("PUMS %d", ACS_PUMS_1year),"summaries","noninst_gq_summary.csv")
  GQ_PUMS1YEAR_SUMMARY <- read.csv(GQ_PUMS1YEAR_FILE, header=T)
  print(paste("Read",nrow(GQ_PUMS1YEAR_SUMMARY),"rows from",GQ_PUMS1YEAR_FILE))
  # calculate gq worker share of total
  GQ_PUMS1YEAR_SUMMARY <- GQ_PUMS1YEAR_SUMMARY %>% mutate(
    worker_share = EMPRES / gqpop
  )
  
  # target_EMPRES will be target * worker_share
  target_df <- left_join(target_df, select(GQ_PUMS1YEAR_SUMMARY, County_Name, worker_share), by="County_Name") %>%
    mutate(EMPRES_target = as.integer(round(GQPOP_target*worker_share)))
  print("target_df:")
  print(target_df)
  print(target_df %>% summarise(across(where(is.numeric), sum)))

  # Adjust GQ_PUMS1YEAR_SUMMARY to be consistent with the given targets 
  print("GQ_PUMS1YEAR_SUMMARY:")
  print(GQ_PUMS1YEAR_SUMMARY)
  print(GQ_PUMS1YEAR_SUMMARY %>% summarise(across(where(is.numeric), sum)))

  # scale PUMS summary to the target total: gqtype distribution
  GQ_PUMS1YEAR_SUMMARY <- scale_data_to_targets(
    source_df = GQ_PUMS1YEAR_SUMMARY,
    target_df = target_df %>% rename(gqpop_target = GQPOP_target),
    id_var = "County_Name",
    sum_var = "gqpop",
    partial_vars = c("gq_type_univ", "gq_type_mil", "gq_type_othnon")
  )
  # scale PUMS summary to the target total: age distribution
  GQ_PUMS1YEAR_SUMMARY <- scale_data_to_targets(
    source_df = GQ_PUMS1YEAR_SUMMARY %>% mutate(sum_age = AGE0004 + AGE0519 + AGE2044 + AGE4564 + AGE65P),
    target_df = target_df %>% rename(sum_age_target = GQPOP_target),
    id_var = "County_Name",
    sum_var = "sum_age",
    partial_vars = c("AGE0004", "AGE0519", "AGE2044", "AGE4564", "AGE65P")
  )
  # scale PUMS summary to the target total: occupation distribution
  # note here the worker target is worker_share * gq_target
  GQ_PUMS1YEAR_SUMMARY <- scale_data_to_targets(
    source_df = GQ_PUMS1YEAR_SUMMARY,
    target_df = target_df,
    id_var = "County_Name",
    sum_var = "EMPRES",
    partial_vars = c("pers_occ_management", "pers_occ_professional", "pers_occ_services", 
                    "pers_occ_retail", "pers_occ_manual","pers_occ_military")
  )

  print("After adjusting to given target, GQ_PUMS1YEAR_SUMMARY:")
  print(GQ_PUMS1YEAR_SUMMARY)
  print(GQ_PUMS1YEAR_SUMMARY %>% summarise(across(where(is.numeric), sum)))

  print("source_df:")
  print(source_df)

  # Now we have detailed targets in GQ_PUMS1YEAR_SUMMARY, so we'll update source_df to match
  # First, summarize to county and join with targets and calculate diffs
  source_county_df <- source_df %>% group_by(County_Name) %>% summarize(
    gq_type_univ   = sum(gq_type_univ),
    gq_type_mil    = sum(gq_type_mil),
    gq_type_othnon = sum(gq_type_othnon),
    gqpop          = sum(gqpop)
  )
  source_county_df <- left_join(
    source_county_df, 
    select(GQ_PUMS1YEAR_SUMMARY, County_Name, gq_type_univ, gq_type_mil, gq_type_othnon, gqpop) %>% rename(
      gq_type_univ_target   = gq_type_univ,
      gq_type_mil_target    = gq_type_mil,
      gq_type_othnon_target = gq_type_othnon,
      gqpop_target          = gqpop
    ),
    by="County_Name"
  ) %>% mutate(
    gq_type_univ_diff   = gq_type_univ_target    - gq_type_univ,
    gq_type_mil_diff    =  gq_type_mil_target    - gq_type_mil,
    gq_type_othnon_diff =  gq_type_othnon_target - gq_type_othnon,
    gqpop_diff          =  gqpop_target          - gqpop
  )
  print("source_county_df:")
  print(source_county_df)
  print(source_county_df %>% summarise(across(where(is.numeric), sum)))

  # modify gq types based on diffs
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, source_county_df, "TAZ1454", "County_Name", "gq_type_univ")
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, source_county_df, "TAZ1454", "County_Name", "gq_type_mil")
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, source_county_df, "TAZ1454", "County_Name", "gq_type_othnon")
  source_df <- source_df %>% mutate(gqpop = gq_type_univ + gq_type_mil + gq_type_othnon)
  print("Resuting group quarters by county:")
  print(source_df %>% group_by(County_Name) %>% summarize(
    gq_type_univ   = sum(gq_type_univ),
    gq_type_mil    = sum(gq_type_mil),
    gq_type_othnon = sum(gq_type_othnon),
    gqpop          = sum(gqpop)
  ))

  # Now the gq_type_* and gqpop columns in source_df are ok
  # So lets decrease totpop by age as well as we can
  # First, apply the gqpop_diff to age categories (so these can be positive or negative)
  age_diffs_county <- scale_data_to_targets(
    source_df = select(GQ_PUMS1YEAR_SUMMARY, County_Name, sum_age, AGE0004, AGE0519, AGE2044, AGE4564, AGE65P), 
    target_df = source_county_df %>% select(County_Name, gqpop_diff) %>% rename(sum_age_target = gqpop_diff),
    id_var    = "County_Name",
    sum_var   = "sum_age",
    partial_vars = c("AGE0004", "AGE0519", "AGE2044", "AGE4564", "AGE65P")
  )
  # these are diffs -- relabel them as such
  age_diffs_county <- age_diffs_county %>% rename(
    sum_age_diff = sum_age,
    AGE0004_diff = AGE0004,
    AGE0519_diff = AGE0519,
    AGE2044_diff = AGE2044,
    AGE4564_diff = AGE4564,
    AGE65P_diff  = AGE65P
  )
  print("age_diffs_county:")
  print(age_diffs_county)
  print(age_diffs_county %>% summarise(across(where(is.numeric), sum)))

  prev_sum_age <- sum(source_df$sum_age)
  print(sprintf("Total sum_age is now %d", prev_sum_age))

  # apply them to the tazdata
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, age_diffs_county, "TAZ1454", "County_Name", "AGE0004")
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, age_diffs_county, "TAZ1454", "County_Name", "AGE0519")
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, age_diffs_county, "TAZ1454", "County_Name", "AGE2044")
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, age_diffs_county, "TAZ1454", "County_Name", "AGE4564")
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, age_diffs_county, "TAZ1454", "County_Name", "AGE65P")
  source_df <- source_df %>% mutate(sum_age = AGE0004 + AGE0519 + AGE2044 + AGE4564 + AGE65P)
  print(sprintf("Total sum_age is now %d, diff from previous is %d", 
    sum(source_df$sum_age), sum(source_df$sum_age)-prev_sum_age))


  # Now lets decrease EMPRES by occupation as well as we can
  # First, apply the gqpop_diff to pers_occ categories (so these can be positive or negative) -- these are diffs
  pers_occ_diffs_county <- scale_data_to_targets(
    source_df = select(GQ_PUMS1YEAR_SUMMARY, County_Name, EMPRES, 
                       pers_occ_management, pers_occ_professional, pers_occ_services, 
                       pers_occ_retail, pers_occ_manual, pers_occ_military), 
    target_df = source_county_df %>% select(County_Name, gqpop_diff) %>% rename(EMPRES_target = gqpop_diff),
    id_var    = "County_Name",
    sum_var   = "EMPRES",
    partial_vars = c("pers_occ_management", "pers_occ_professional", "pers_occ_services", 
                     "pers_occ_retail", "pers_occ_manual", "pers_occ_military")
  )
  # these are diffs -- relabel them as such
  pers_occ_diffs_county <- pers_occ_diffs_county %>% rename(
    EMPRES_diff                = EMPRES,
    pers_occ_management_diff   = pers_occ_management,
    pers_occ_professional_diff = pers_occ_professional,
    pers_occ_services_diff     = pers_occ_services,
    pers_occ_retail_diff       = pers_occ_retail,
    pers_occ_manual_diff       = pers_occ_manual,
    pers_occ_military_diff     = pers_occ_military
  )
  print("pers_occ_diffs_county:")
  print(pers_occ_diffs_county)
  print(pers_occ_diffs_county %>% summarise(across(where(is.numeric), sum)))

  prev_EMPRES <- sum(source_df$EMPRES)
  print(sprintf("Total EMPRES is now %d", prev_EMPRES))

  # apply them to the tazdata
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, pers_occ_diffs_county, "TAZ1454", "County_Name", "pers_occ_management")
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, pers_occ_diffs_county, "TAZ1454", "County_Name", "pers_occ_professional")
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, pers_occ_diffs_county, "TAZ1454", "County_Name", "pers_occ_services")
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, pers_occ_diffs_county, "TAZ1454", "County_Name", "pers_occ_retail")
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, pers_occ_diffs_county, "TAZ1454", "County_Name", "pers_occ_manual")
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, pers_occ_diffs_county, "TAZ1454", "County_Name", "pers_occ_military")
  source_df <- source_df %>% mutate(EMPRES = pers_occ_management + pers_occ_professional + pers_occ_services +
                                             pers_occ_retail + pers_occ_manual + pers_occ_military)
  print(sprintf("Total EMPRES is now %d, diff from previous is %d", 
    sum(source_df$EMPRES), sum(source_df$EMPRES)-prev_EMPRES))

  return(source_df)
}

