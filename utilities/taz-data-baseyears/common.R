# Pull out some common methods for tazdata preparation here
#

BAY_AREA_COUNTIES = c(
  "Alameda",
  "Contra Costa",
  "Marin",
  "Napa",
  "San Francisco",
  "San Mateo",
  "Santa Clara",
  "Solano",
  "Sonoma"
)
# https://github.com/BayAreaMetro/modeling-website/wiki/InflationAssumptions
DOLLARS_2000_to_202X <- c(
  "2021"=1.72, 
  "2022"=1.81
)

censuskey    <- readLines("M:/Data/Census/API/api-key.txt")
baycounties  <- c("01","13","41","55","75","81","85","95","97")
state_code   <- "06"
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
fix_rounding_artifacts <- function(df, id_var, sum_var, partial_vars, logging=TRUE) {
  print(sprintf("fix_rounding_artifacts(id_var=%s, sum_var=%s, partial_vars=%s)",
    id_var,sum_var,toString(partial_vars)))

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
  if (logging) {
    print("fix_rounding_artifacts(): Rows needing updating:")
    print(filter(my_df, diff_col != 0))
  }

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
scale_data_to_targets <- function(source_df, target_df, id_var, sum_var, partial_vars, logging=FALSE) {
  print(sprintf("scale_data_to_targets(id_var=%s, sum_var=%s, partial_vars=%s)", 
    id_var, sum_var, toString(partial_vars)))

  sum_var_target <- paste0(sum_var,"_target")
  # add the sum_var_target column into the source table
  source_df <- left_join(
    source_df, 
    select(target_df, all_of(c(id_var, sum_var_target))),
    by=id_var
  )
  if (logging) {
    print("scale_data_to_targets(): source_df before:")
    print(select(source_df, all_of(c(id_var, sum_var, sum_var_target, partial_vars))))
  }
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
  # drop this, we're done with it
  source_df <- source_df %>% select(-target_scale)
  # fix rounding artifacts
  source_df <- fix_rounding_artifacts(source_df, id_var, sum_var, partial_vars, logging)

  if (logging) {
    print("scale_data_to_targets(): source_df after:")
    print(select(source_df, all_of(c(id_var, sum_var, sum_var_target, partial_vars))))
  }
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
    modify_sample <- modify_sample %>% group_by(!!sym(disagg_id_var)) %>% summarise(TO_MODIFY = n(), .groups = 'drop')
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

## Combination of the above. This is effectively the generic form of update_empres_to_county_totals()
# 
# Parameters:
#  source_df: a TAZ-based tibble including columns:
#    id variables: County_Name, TAZ1454
#    sum_var comprised of partial_vars 
#        e.g. sum_var = "EMPRES", partial_vars = c("pers_occ_management", "pers_occ_professional", ...)
#  target_df: a county-based tibble including columns: County_Name, [sum_var]_target
#  sum_var: string indicating the sum variable
#  partial_vars: vector of strings indicating the variables which comprise the sum_var
#
update_tazdata_to_county_target <- function(source_df, target_df, sum_var, partial_vars) {
  print(sprintf("########################## update_tazdata_to_county_target(sum_var=%s, partial_vars=c(%s)) ##########################",
    sum_var, toString(partial_vars)))

  # copy only needed target columns
  sum_var_target <- paste0(sum_var, "_target")
  target_df <- target_df %>% select(all_of(c("County_Name", sum_var_target)))
  print(sprintf("target_df %s total=%d:", sum_var_target, 
    target_df %>% summarise(sum = sum(!!sym(sum_var_target))) %>% pull(sum)))

  # summarize current totals for sum_var and partial_vars
  source_county_summary <- source_df %>% group_by(County_Name) %>%
    summarise(across(all_of(c(sum_var, partial_vars)), sum, .names = "{col}"), .groups = 'drop')
  print(sprintf("source_county_summary from source_df (regional total=%d):",
    source_county_summary %>% summarise(sum = sum(!!sym(sum_var))) %>% pull(sum)))
  print(source_county_summary)

  # use this to figure out target partial_vars by county
  target_partials_county <- scale_data_to_targets(
    source_df = source_county_summary, 
    target_df = target_df,
    id_var    = "County_Name",
    sum_var   = sum_var,
    partial_vars = partial_vars) %>%
  rename_with(~ paste0(., "_target"), all_of(c(sum_var, partial_vars)))
  print("target_partials_county before diffs:")
  print(target_partials_county)

  # join with original to calculate diffs
  target_partials_county <- left_join(
    target_partials_county,
    source_county_summary,
    by="County_Name"
  ) %>% mutate(
      across(all_of(c(sum_var, partial_vars)), ~ get(paste0(cur_column(), "_target")) - ., .names = "{.col}_diff"))
  #  EMPRES_diff                = EMPRES_target                - EMPRES,
  #  pers_occ_management_diff   = pers_occ_management_target   - pers_occ_management,
  #  ... etc ...

  print("target_partials_county:")
  print(target_partials_county)

  # apply to TAZs for each partial_var
  for (partial_var in partial_vars) {
    source_df <- update_disaggregate_data_to_aggregate_targets(source_df, target_partials_county, "TAZ1454", "County_Name", partial_var)
  }
  source_df <- source_df %>% mutate(!!sum_var := rowSums(across(all_of(partial_vars))))


  # check result
  print(sprintf("Resulting %s and c(%s) by county:",sum_var,toString(partial_vars)))
  print(source_df %>% group_by(County_Name) %>% 
        summarise(across(all_of(c(sum_var, partial_vars)), sum, .names = "{col}"), .groups = 'drop'))
        
  print("regional_summary of source_df being returned:")
  regional_summary <- source_df %>% summarise(across(where(is.numeric), sum))
  print(format(t(regional_summary), scientific = FALSE))

  print(sprintf("Compare to target_df %s total=%d", sum_var_target, 
    target_df %>% summarise(sum = sum(!!sym(sum_var_target))) %>% pull(sum)))
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
    summarise(WGTP = sum(WGTP), .groups = 'drop')
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

# Updates GQ population in source_df to totals in target_GQ_df.
#
# Parameters:
#   source_df is a TAZ-based tibble including columns:
#     id variables: County_Name, TAZ1454, 
#     GQ variables: gq_type_[univ,mil,othnon], gqpop         
#   target_GQ_df is a tibble with columns County_Name, GQPOP_target
#   ACS_PUMS_1year is the year corresponding to the target; we'll use the ACS PUMS 1-year data
#     distributions for GQ workers to make these updates.
#
# Returns:
#   source_df with updated data in columns gq_type_[mil,othnon,univ], gqpop
#
update_gqpop_to_county_totals <- function(source_df, target_GQ_df, ACS_PUMS_1year) {

  print(sprintf("########################## update_gqpop_to_county_totals(%d) ##########################", ACS_PUMS_1year))
  # copy only needed target columns
  target_df <- select(target_GQ_df, County_Name, GQPOP_target)
  print(sprintf("target_df with GQPOP_target total=%d:", sum(target_df$GQPOP_target)))
  print(target_df)

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
  print("target_df with EMPRES_target refering to gqpop's EMPRES:")
  print(target_df)
  print(target_df %>% summarise(across(where(is.numeric), sum)))

  # Adjust GQ_PUMS1YEAR_SUMMARY to be consistent with the given targets 
  print("Initial GQ_PUMS1YEAR_SUMMARY:")
  print(GQ_PUMS1YEAR_SUMMARY)
  print(GQ_PUMS1YEAR_SUMMARY %>% summarise(across(where(is.numeric), sum)))

  # scale PUMS summary to the target total: gqtype distribution
  detailed_GQ_county_targets <- scale_data_to_targets(
    source_df = GQ_PUMS1YEAR_SUMMARY,
    target_df = target_df %>% rename(gqpop_target = GQPOP_target),
    id_var = "County_Name",
    sum_var = "gqpop",
    partial_vars = c("gq_type_univ", "gq_type_mil", "gq_type_othnon")
  )
  # scale PUMS summary to the target total: age distribution
  detailed_GQ_county_targets <- scale_data_to_targets(
    source_df = detailed_GQ_county_targets %>% mutate(sum_age = AGE0004 + AGE0519 + AGE2044 + AGE4564 + AGE65P),
    target_df = target_df %>% rename(sum_age_target = GQPOP_target),
    id_var = "County_Name",
    sum_var = "sum_age",
    partial_vars = c("AGE0004", "AGE0519", "AGE2044", "AGE4564", "AGE65P")
  )
  # scale PUMS summary to the target total: occupation distribution
  # note here the worker target is worker_share * gq_target
  detailed_GQ_county_targets <- scale_data_to_targets(
    source_df = detailed_GQ_county_targets,
    target_df = target_df,
    id_var = "County_Name",
    sum_var = "EMPRES",
    partial_vars = c("pers_occ_management", "pers_occ_professional", "pers_occ_services", 
                    "pers_occ_retail", "pers_occ_manual","pers_occ_military")
  )
  # drop these
  detailed_GQ_county_targets <- detailed_GQ_county_targets %>% select(-worker_share)

  print("After adjusting to given target, detailed_GQ_county_targets:")
  print(detailed_GQ_county_targets)
  print(detailed_GQ_county_targets %>% summarise(across(where(is.numeric), sum)))

  print("source_df:")
  print(source_df)

  # Now we have detailed targets in detailed_GQ_county_targets, so we'll update source_df to match
  # First, summarize to county and join with targets and calculate diffs
  source_county_df <- source_df %>% group_by(County_Name) %>% summarize(
    gq_type_univ   = sum(gq_type_univ),
    gq_type_mil    = sum(gq_type_mil),
    gq_type_othnon = sum(gq_type_othnon),
    gqpop          = sum(gqpop),
    .groups = 'drop'
  )
  source_county_df <- left_join(
    source_county_df, 
    select(detailed_GQ_county_targets, County_Name, gq_type_univ, gq_type_mil, gq_type_othnon, gqpop) %>% rename(
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

  source_df_bycounty <- source_df %>% 
  group_by(County_Name) %>% summarize(
    gq_type_univ   = sum(gq_type_univ),
    gq_type_mil    = sum(gq_type_mil),
    gq_type_othnon = sum(gq_type_othnon),
    gqpop          = sum(gqpop),
    .groups = 'drop'
  )
  print("Resulting group quarters by county:")
  print(source_df_bycounty)
  print(source_df_bycounty %>% summarise(across(where(is.numeric), sum)))

  print("regional_summary of source_df being returned:")
  regional_summary <- source_df %>% summarise(across(where(is.numeric), sum))
  print(format(t(regional_summary), scientific = FALSE))

  return(source_df)
}

# Update empres population in source_df to totals in target_EMPRES_df.
# 
# Parameters:
#   source_df is a TAZ-based tibble including columns:
#     id variables: County_Name, TAZ1454
#     employed resident variables: pers_occ_[management,professional,services,retail,manual,military], EMPRES
#   target_EMPRES_df is a tibble with columns County_Name, EMPRES_target
#
# Returns:
#   source_df with updated columns pers_occ_[management,professional,services,retail,manual,military], EMPRES
update_empres_to_county_totals <- function(source_df, target_EMPRES_df) {
  print("########################## update_empres_to_county_totals() ##########################")
  # copy only needed target columns
  target_df <- select(target_EMPRES_df, County_Name, EMPRES_target)
  print(sprintf("target_EMPRES_df EMPRES_target total=%d", sum(target_df$EMPRES_target)))

  # first, summarize existing pers_occ by county
  source_empres_county <- source_df %>% group_by(County_Name) %>% summarize(
    EMPRES                = sum(EMPRES),
    pers_occ_management   = sum(pers_occ_management),
    pers_occ_professional = sum(pers_occ_professional),
    pers_occ_services     = sum(pers_occ_services),
    pers_occ_retail       = sum(pers_occ_retail),
    pers_occ_manual       = sum(pers_occ_manual),
    pers_occ_military     = sum(pers_occ_military),
    .groups = 'drop'
  )
  print(sprintf("source_empres_county from source_df (regional total=%d):", sum(source_empres_county$EMPRES)))
  print(source_empres_county)

  # use this to figure out target pers_occ by county
  target_occ_county <- scale_data_to_targets(
    source_df = source_empres_county, 
    target_df = target_df,
    id_var    = "County_Name",
    sum_var   = "EMPRES",
    partial_vars = c("pers_occ_management", "pers_occ_professional", "pers_occ_services", 
                    "pers_occ_retail", "pers_occ_manual","pers_occ_military")) %>%
    rename(
      EMPRES_target                = EMPRES,
      pers_occ_management_target   = pers_occ_management,
      pers_occ_professional_target = pers_occ_professional,
      pers_occ_services_target     = pers_occ_services,
      pers_occ_retail_target       = pers_occ_retail,
      pers_occ_manual_target       = pers_occ_manual,
      pers_occ_military_target     = pers_occ_military
    )
  print("target_occ_county before diffs:")
  print(target_occ_county)

  # join with original to calculate diffs
  target_occ_county <- left_join(
    target_occ_county,
    source_empres_county,
    by="County_Name"
  ) %>% mutate(
    EMPRES_diff                = EMPRES_target                - EMPRES,
    pers_occ_management_diff   = pers_occ_management_target   - pers_occ_management,
    pers_occ_professional_diff = pers_occ_professional_target - pers_occ_professional,
    pers_occ_services_diff     = pers_occ_services_target     - pers_occ_services,
    pers_occ_retail_diff       = pers_occ_retail_target       - pers_occ_retail,
    pers_occ_manual_diff       = pers_occ_manual_target       - pers_occ_manual,
    pers_occ_military_diff     = pers_occ_military_target     - pers_occ_military,
  )
  print("target_occ_county:")
  print(target_occ_county)

  # apply to TAZs
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, target_occ_county, "TAZ1454", "County_Name", "pers_occ_management")
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, target_occ_county, "TAZ1454", "County_Name", "pers_occ_professional")
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, target_occ_county, "TAZ1454", "County_Name", "pers_occ_services")
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, target_occ_county, "TAZ1454", "County_Name", "pers_occ_retail")
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, target_occ_county, "TAZ1454", "County_Name", "pers_occ_manual")
  source_df <- update_disaggregate_data_to_aggregate_targets(source_df, target_occ_county, "TAZ1454", "County_Name", "pers_occ_military")
  source_df <- source_df %>% mutate(EMPRES = pers_occ_management + pers_occ_professional + pers_occ_services +
                                             pers_occ_retail + pers_occ_manual + pers_occ_military)

  print("Resulting empres and pers_occ by county :")
  print(source_df %>% group_by(County_Name) %>% summarize(
    EMPRES                = sum(EMPRES),
    pers_occ_management   = sum(pers_occ_management),
    pers_occ_professional = sum(pers_occ_professional),
    pers_occ_services     = sum(pers_occ_services),
    pers_occ_retail       = sum(pers_occ_retail),
    pers_occ_manual       = sum(pers_occ_manual),
    pers_occ_military     = sum(pers_occ_military),
    .groups = 'drop'
  ))
  print("Regional totals:")
  print(source_df %>% select(EMPRES, starts_with("pers_occ")) %>% summarise(across(where(is.numeric), sum)))

  return(source_df)
}

# After naively updating household size partials (either hh_size_* or hhwrks_*) columns to achieve
# target TOTHH, they may be inconsistent with persons (either HHPOP or EMPRES).
# This keeps total households constant, but shifts households between categories to achieve
# target persons.
#
# Parameters:
#   size_or_workers: one of "hh_size" or "hh_wrks"
#   source_df is a TAZ-based tibble including columns:
#     id variables: County_Name, TAZ1454
#     sum_var and partial_Vars: e.g., sum_size & hh_size_[1,2,3,4_plus] OR 
#                                     sum_hhworkers & hh_wrks_[0,1,2,3_plus]
#     pop_var: pop var to match. e.g., HHPOP or EMPRES
#   target_pop_df: a dataframe with columns County_name, pop_var_target
#   popsyn_ACS_PUMS_5year: the ACS5 year PUMS used for population synthesis. This is used to estimate
#     number of persons or workers in the largest bucket by county
#     e.g. Number of persons in 4+ person households by county
make_hhsizes_consistent_with_population <- function(source_df, target_df, size_or_workers, popsyn_ACS_PUMS_5year) {
  print(sprintf("########################## make_hhsizes_consistent_with_population(%s, popsyn_ACS_PUMS_5year=%d) ##########################",
    size_or_workers, popsyn_ACS_PUMS_5year))

  popsyn_PUMS_summary_dir <- sprintf("M:/Data/Census/PUMS/PUMS %d-%d/summaries", popsyn_ACS_PUMS_5year-4, popsyn_ACS_PUMS_5year %% 100)
  if (size_or_workers == "hh_size") {
    pop_var        <- "HHPOP"
    sum_var        <- "sum_size"
    partial_vars   <- c("hh_size_1", "hh_size_2", "hh_size_3", "hh_size_4_plus")
    big_cat_file   <- file.path(popsyn_PUMS_summary_dir, "county_hh_size_summary_wide.csv")
    big_cat_col    <- "avg_persons.hh.hh_size_4plus"
  } else if (size_or_workers == "hh_wrks") {
    pop_var        <- "EMPRES"
    sum_var        <- "sum_hhworkers"
    partial_vars   <- c("hh_wrks_0", "hh_wrks_1", "hh_wrks_2", "hh_wrks_3_plus")
    big_cat_file   <- file.path(popsyn_PUMS_summary_dir, "county_hh_worker_summary_wide.csv")
    big_cat_col    <- "avg_workers.hh.hh_wrks14_3plus"
  } else {
    stop("Not implemented")
  }
  # copy only needed target columns
  pop_var_target <- paste0(pop_var,"_target")
  target_df <- target_df %>% select(all_of(c("County_Name", pop_var_target)))
  print(sprintf("target_df (%s total=%d):", pop_var_target, 
    target_df %>% summarise(sum = sum(!!sym(pop_var_target))) %>% pull(sum)))
  print(target_df)

  # read the big cat file to get the avg size of the biggest category
  big_cat_df <- read.csv(big_cat_file, header=T)
  print(paste("Read",big_cat_file))
  big_cat_df <- big_cat_df %>% 
    select(all_of(c("County_Name", big_cat_col))) %>%
    rename(big_cat_avg =!!sym(big_cat_col))
  print("big_cat_df:")
  print(big_cat_df)

  # join to source_df and use to estimate pop_var
  pop_var_est  <- paste0(pop_var, "_est")
  source_df <- left_join(source_df, big_cat_df, by="County_Name")
  if (size_or_workers == "hh_size") {
    source_df <- source_df %>% mutate(
      !!pop_var_est := (hh_size_1*1) + (hh_size_2*2) + (hh_size_3*3) + (hh_size_4_plus*big_cat_avg)
    )
  } else if (size_or_workers == "hh_wrks") {
    source_df <- source_df %>% mutate(
      !!pop_var_est := (hh_wrks_1*1) + (hh_wrks_2*2) + (hh_wrks_3_plus*big_cat_avg)
    )
  }
  print("source_df with estimated pop_var")
  print(source_df %>% select(all_of(c("County_Name", sum_var, partial_vars, pop_var_est))))

  # summarize current totals for sum_var and partial_vars
  source_county_summary <- source_df %>% group_by(County_Name, big_cat_avg) %>%
    summarise(across(all_of(c(sum_var, partial_vars, pop_var_est)), sum, .names = "{col}"), .groups = 'drop')
  # join with target_df
  source_county_summary <- left_join(source_county_summary, target_df,  by="County_Name")
  # calculate diff from target
  pop_var_diff <- paste0(pop_var, "_diff")
  source_county_summary <- source_county_summary %>% mutate(
    !!pop_var_diff := !!sym(pop_var_target) - !!sym(pop_var_est)
  )
  # also calculate avg pop value of category change
  if (size_or_workers == "hh_size") {
    source_county_summary <- source_county_summary %>% mutate(
      avg_incr_value = (hh_size_1 + hh_size_2 + (hh_size_3*(big_cat_avg-3)))/(hh_size_1+hh_size_2+hh_size_3),
      avg_decr_value = (hh_size_2 + hh_size_3 + (hh_size_4_plus*(big_cat_avg-3)))/(hh_size_2 + hh_size_3 + hh_size_4_plus)
    )
  } else if (size_or_workers == "hh_wrks") {
    source_county_summary <- source_county_summary %>% mutate(
      avg_incr_value = (hh_wrks_0 + hh_wrks_1 + (hh_wrks_2*(big_cat_avg-2)))/(hh_wrks_0+hh_wrks_1+hh_wrks_2),
      avg_decr_value = (hh_wrks_1 + hh_wrks_2 + (hh_wrks_3_plus*(big_cat_avg-2)))/(hh_wrks_1 + hh_wrks_2 + hh_wrks_3_plus)
    )
  }

  print(sprintf("source_county_summary from source_df (regional %s=%.0f %s=%.0f %s=%.0f):",
    pop_var_est,    source_county_summary %>% summarise(sum = sum(!!sym(pop_var_est)))    %>% pull(sum),
    pop_var_target, source_county_summary %>% summarise(sum = sum(!!sym(pop_var_target))) %>% pull(sum),
    pop_var_diff,   source_county_summary %>% summarise(sum = sum(!!sym(pop_var_diff)))   %>% pull(sum)
  ))
  print(source_county_summary)

  # loop through counties
  county_list <- source_county_summary %>% pull(County_Name)
  new_taz_tibble <- tibble()
  for (county in county_list) {
    diff_value <- source_county_summary %>% filter(County_Name == county) %>% pull(!!sym(pop_var_diff))
    county_big_cat_avg <- big_cat_df %>% filter(County_Name == county) %>% pull(big_cat_avg)

    # these are the rows for this county from which to sample
    filtered_source_df <- source_df %>% 
      select(all_of(c("TAZ1454", "County_Name", sum_var, partial_vars, pop_var_est))) %>% 
      filter(County_Name == county) %>%
      filter(get(pop_var_est) > 0)

    # if the diff is negative, then we're moving households from bigger sizes to smaller sizes
    # for each reduction, we want to sample a household to reduce
    # first, let's distribute our reduction amongst TAZs weighted by pop_var_est
    
    # it won't be 1-to-1 because changes to/from the biggest category count as more than one
    # but let's not worry about that now
    if (diff_value > 0) {
      avg_change <- source_county_summary %>% filter(County_Name == county) %>% pull(avg_incr_value)
    } else {
      avg_change <- source_county_summary %>% filter(County_Name == county) %>% pull(avg_decr_value)
    }
    slice_size <- as.integer(abs(diff_value/avg_change))

    print(sprintf("  Processing county %13s (big_cat_avg=%.2f avg_change=%.2f) with diff=%6.0f slice_size=%6.0f; filtered_source_df has %4d rows",
      county, county_big_cat_avg, avg_change, diff_value, slice_size,nrow(filtered_source_df)))
    # print("filtered_source_df")
    # print(filtered_source_df)

    modify_sample <- filtered_source_df %>% slice_sample(
      n=slice_size,
      replace=TRUE,
      weight_by=!!sym(pop_var_est)
    )
    # aggregate to TAZ
    modify_sample <- modify_sample %>% group_by(TAZ1454) %>% summarise(TO_MODIFY = n(), .groups = 'drop')
    # print(paste("modify_sample len=", nrow(modify_sample)))
    # print(modify_sample)

    diff_value <- source_county_summary %>% filter(County_Name == county) %>% pull(!!sym(pop_var_diff))

    # for each TAZ, if we're removing/adding, we need to pick which category we're moving down/up from
    TAZ_list <- modify_sample %>% pull(TAZ1454)
    for (TAZ in TAZ_list) {

      TAZ_long <- filtered_source_df %>% filter(TAZ1454==TAZ) %>% pivot_longer(
        cols = all_of(partial_vars),
        names_to = "category", 
        values_to = "num_hh"
      ) %>% select(category, num_hh)

      TAZ_diff <- modify_sample %>% filter(TAZ1454 == TAZ) %>% pull(TO_MODIFY)
      # if we're reducing, don't include smallest category - we can't have fewer than that
      # if we're adding, don't include largest category
      if (diff_value < 0) {
        TAZ_diff <- -1*TAZ_diff
        TAZ_long_to_sample <- TAZ_long %>% mutate(num_hh = ifelse(category == head(partial_vars,1), 0, num_hh))
      } else {
        TAZ_long_to_sample <- TAZ_long %>% mutate(num_hh = ifelse(category == tail(partial_vars,1), 0, num_hh))
      }
      # print(sprintf("Targetting diff %.0f in TAZ %d", TAZ_diff, TAZ))

      # sample categories to reduce and aggregate to category
      category_sample <- TAZ_long_to_sample %>% slice_sample(
        n=as.integer(abs(TAZ_diff)),
        replace=TRUE,
        weight_by=num_hh
      ) %>% group_by(category) %>% summarize(move_from = -1*n())
      TAZ_long <- left_join(TAZ_long, category_sample, by="category")

      # if TAZ_diff < 0 then these we're moving them down a category and these are negative
      if (TAZ_diff < 0) {
        TAZ_long <- TAZ_long %>% mutate(move_to = -1*lead(move_from))
      }
      else {
        TAZ_long <- TAZ_long %>% mutate(move_to = -1*lag(move_from))
      }
      TAZ_long <- TAZ_long %>% replace_na(list(move_from = 0, move_to = 0))
      # print("TAZ_long before applying")
      # print(TAZ_long)

      # apply it
      TAZ_long <- TAZ_long %>% 
        mutate(num_hh = num_hh + move_from + move_to)
      # stopf if it goes negative
      negative_hh <- TAZ_long %>% filter(num_hh < 0)
      if (nrow(negative_hh) > 0) {
        print("Negative resuling num_hh:")
        print(TAZ_long)
        TAZ_long <- TAZ_long %>% mutate(num_hh = max(0, num_hh))
      }

      TAZ_wide <- TAZ_long %>% 
        select(-move_from, -move_to) %>%
        pivot_wider(names_from=category, values_from=num_hh) %>%
        mutate(TAZ1454=TAZ, County_Name=county) %>%
        relocate(TAZ1454,     .before = 1) %>%
        relocate(County_Name, .before = 1)
      # print("TAZ_wide after applying")
      # print(TAZ_wide)

      new_taz_tibble <- rbind(new_taz_tibble, TAZ_wide)
    }
  }
  # note: new_taz_tibble doesn't necessarily have all the TAZ rows; some wouldn't have come up in sampling
  print("full new_taz_tibble:")
  print(new_taz_tibble)

  # join to source_df and replace if the join succeeded and the new value isn't na
  new_partial_vars <- paste0(partial_vars, ".new")
  source_df <- left_join(source_df, new_taz_tibble, 
    by=c("County_Name","TAZ1454"), suffix = c("", ".new")) %>%
    mutate(across(all_of(partial_vars), ~ if_else(!is.na(get(paste0(cur_column(), ".new"))), 
                                             get(paste0(cur_column(), ".new")), .))) %>%
    select(-all_of(new_partial_vars))
  print("source_df with new replacements")
  print(source_df %>% select(all_of(c("County_Name","TAZ1454","big_cat_avg",partial_vars))))

  # recalculate sum_var and pop_var (which is now estimated)
  if (size_or_workers == "hh_size") {
    source_df <- source_df %>% mutate(
      !!sum_var     := hh_size_1 + hh_size_2 + hh_size_3 + hh_size_4_plus,
      !!pop_var     := round((hh_size_1*1) + (hh_size_2*2) + (hh_size_3*3) + (hh_size_4_plus*big_cat_avg))
    )
  } else if (size_or_workers == "hh_wrks") {
    source_df <- source_df %>% mutate(
      !!sum_var     := hh_wrks_0 + hh_wrks_1 + hh_wrks_2 + hh_wrks_3_plus,
      !!pop_var     := round((hh_wrks_1*1) + (hh_wrks_2*2) + (hh_wrks_3_plus*big_cat_avg))
    )
  }

  print("Returning source_df:")
  print(source_df %>% select(all_of(c("County_Name","TAZ1454",partial_vars,sum_var,pop_var))))
  source_df <- source_df %>% select(-big_cat_avg) # don't return this column

  # summarize final totals for sum_var and partial_vars
  source_county_summary <- source_df %>% group_by(County_Name) %>%
    summarise(across(all_of(c(sum_var, partial_vars, pop_var)), sum, .names = "{col}"), .groups = 'drop')
  # join with target_df for pop_var_target
  source_county_summary <- left_join(source_county_summary, target_df,  by="County_Name")
  # calculate diff from target
  source_county_summary <- source_county_summary %>% mutate(
    !!pop_var_diff := !!sym(pop_var_target) - !!sym(pop_var)
  )  
  print(sprintf("source_county_summary (regional %s=%.0f %s=%.0f %s=%.0f):",
    pop_var,        source_county_summary %>% summarise(sum = sum(!!sym(pop_var)))        %>% pull(sum),
    pop_var_target, source_county_summary %>% summarise(sum = sum(!!sym(pop_var_target))) %>% pull(sum),
    pop_var_diff,   source_county_summary %>% summarise(sum = sum(!!sym(pop_var_diff)))   %>% pull(sum)
  ))
  print(source_county_summary)

  print("regional_summary of source_df being returned:")
  regional_summary <- source_df %>% summarise(across(where(is.numeric), sum))
  print(format(t(regional_summary), scientific = FALSE))

  return(source_df)
}