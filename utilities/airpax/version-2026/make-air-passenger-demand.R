# ============================================================
# Author: Sushreeta Mishra, Sujith Rapolu
# Date: 2026-04-09
#
# Builds 2023 and 2050 airport ground access OD matrices (.dbf) for SFO, OAK, SJC by expanding
# total ground access trips at the airport level to TAZ-level flows using inputs in Parameters.xlsx:
#
#   SHEET 1: Airport_File_Map
#     - mapping output file names to airport, direction, year, and TAZ range
#
#   SHEET 2: Air_Pax_Targets
#     - total ground access passenger trip targets for each airport by direction and year
#
#   SHEET 3: Super_Dist_Shares
#     - Splits by MTC's super districts for each airport by direction and year
#     
#   SHEET 4: Zone_Shares
#     - each district share is distributed to TAZs using access-mode-specific
#       shares in this sheet
#
#   SHEET 5: TOD_Access_Submode_Shares
#     - Splits by TOD, Access mode, and submode for each airport by direction and year
#     - Time of Day: EA, AM, MD, PM, EV
#     - Access Mode: ES (Escort), PK (Park), RN (Rental),
#                    TX (Taxi), LI (TNC), VN (Van),
#                    HT (Hotel), CH (Charter/Other)
#     - Submode: DA (Drive Alone), S2 (2-person), S3 (3+ person)
#	  - These are the TOD, access mode and submodes in the "Gosling Summaries" used in the MTC model.
#	  - The transit mode share added as part of the 2026 update is defined in a different sheet
#
#   SHEET 6: Transit_TOD_Access_Shares
#	  - Mode share for transit including splits by TOD for each airport by direction and year
#     - Time of Day: EA, AM, MD, PM, EV
#     - Transit Mode: TR (Transit)
#
#   SHEET 7: Transit_Zone_Shares
#     - Transit zonal shares by airport, direction, and zone
#     - Used for zonal allocation of transit person trips
#
#   SHEET 8: Veh_Occupancy
#     - Factors to convert person trips to vehicle trips:
#         DA = 1.0, S2 = 2.0, S3 = 3.2
#     - VN, HT, and CH with S3 use a separate factor: VN_HT_CH_S3
#
# Final values are calculated by applying all of the above
# to each FILE NAME and TAZ pair.
#
# INPUTS
# - Parameters.xlsx
# - TAZ shapefile:
#   .\Input\transportation_analysis_zones_1454_4706804472013361522\
#   transportation_analysis_zones_1454.shp
#
# OUTPUTS
# - Main DBFs in "Gosling Summaries Format" (.\Output) - 12 files (3 airports × 2 directions × 2 years)
#   Based on:
#     Super_Dist_Shares × TOD_Access_Submode_Shares × Air_Pax_Targets / Veh_Occupancy
#
# - Transit DBFs (.\Output_Transit) - 12 files
#   Based on:
#     Transit_TOD_Access_Shares × Transit_Zone_Shares x Air_Pax_Targets
#
# ============================================================


rm(list = ls())

# -----------------------------
# Load packages
# -----------------------------
pkgs <- c("readxl", "dplyr", "tidyr", "stringr", "sf", "foreign", "janitor")
to_install <- pkgs[!pkgs %in% installed.packages()[, "Package"]]
if (length(to_install) > 0) install.packages(to_install)
invisible(lapply(pkgs, library, character.only = TRUE))

# -----------------------------
# Set paths
# -----------------------------
wd <- getwd()
xlsx_file <- file.path(wd, "Parameters.xlsx")

shp_file <- file.path(
  wd,
  "Input",
  "transportation_analysis_zones_1454_4706804472013361522",
  "transportation_analysis_zones_1454.shp"
)

output_dir_main <- file.path(wd, "Output")
output_dir_transit <- file.path(wd, "Output_Transit")

if (!file.exists(xlsx_file)) {
  stop(paste("Parameters.xlsx not found at:", xlsx_file))
}

if (!file.exists(shp_file)) {
  stop(paste("Shapefile not found at:", shp_file))
}

if (!dir.exists(output_dir_main)) dir.create(output_dir_main, recursive = TRUE)
if (!dir.exists(output_dir_transit)) dir.create(output_dir_transit, recursive = TRUE)

# -----------------------------
# Helper functions
# -----------------------------
clean_names_upper <- function(df) {
  df %>%
    janitor::clean_names() %>%
    rename_with(toupper)
}

# Convert share values to decimals
to_share <- function(x) {
  if (is.numeric(x)) {
    return(ifelse(x > 1, x / 100, x))
  }
  x <- trimws(as.character(x))
  x <- gsub("%", "", x)
  x <- gsub(",", "", x)
  x_num <- suppressWarnings(as.numeric(x))
  ifelse(x_num > 1, x_num / 100, x_num)
}

# Convert output fields to DBF-safe types
make_dbf_safe <- function(df) {
  df <- as.data.frame(df, stringsAsFactors = FALSE)
  
  if ("ORIG" %in% names(df)) df$ORIG <- as.integer(df$ORIG)
  if ("DEST" %in% names(df)) df$DEST <- as.integer(df$DEST)
  
  for (nm in names(df)) {
    if (nm %in% c("ORIG", "DEST")) next
    
    if (inherits(df[[nm]], "integer64")) {
      df[[nm]] <- as.numeric(df[[nm]])
    } else if (is.factor(df[[nm]])) {
      suppressWarnings(tmp_num <- as.numeric(as.character(df[[nm]])))
      if (all(is.na(tmp_num) == is.na(df[[nm]]))) {
        df[[nm]] <- tmp_num
      } else {
        df[[nm]] <- as.character(df[[nm]])
      }
    } else if (inherits(df[[nm]], c("Date", "POSIXct", "POSIXt"))) {
      df[[nm]] <- as.character(df[[nm]])
    } else if (!is.numeric(df[[nm]]) &&
               !is.integer(df[[nm]]) &&
               !is.character(df[[nm]]) &&
               !is.logical(df[[nm]])) {
      df[[nm]] <- as.character(df[[nm]])
    }
  }
  
  df
}

# Round numeric output fields to a fixed number of decimals
round_dbf_numeric <- function(df, digits = 2) {
  for (nm in names(df)) {
    if (nm %in% c("ORIG", "DEST")) next
    if (is.numeric(df[[nm]]) || is.integer(df[[nm]])) {
      df[[nm]] <- round(df[[nm]], digits)
    }
  }
  df
}

# Get conversion factor for a non-transit access mode / submode combination
get_conv_factor <- function(access_mode, submode, conv_vec) {
  if (submode == "S3" && access_mode %in% c("VN", "HT", "CH")) {
    conv_factor <- conv_vec["VN_HT_CH_S3"]
    if (is.na(conv_factor) || conv_factor == 0) {
      stop("Missing or invalid conversion factor for SUBMODE: VN_HT_CH_S3")
    }
    return(conv_factor)
  }
  
  conv_factor <- conv_vec[submode]
  if (is.na(conv_factor) || conv_factor == 0) {
    stop(paste("Missing or invalid conversion factor for SUBMODE:", submode))
  }
  
  conv_factor
}

# Build non-transit person-trip table for one FILE_NAME
build_nontransit_person_df <- function(file_name, expanded_od, column_share, target_lookup) {
  
  base_df <- expanded_od %>%
    filter(FILE_NAME == file_name) %>%
    select(
      ORIG, DEST,
      ROW_SHARE_ES, ROW_SHARE_PK, ROW_SHARE_RN, ROW_SHARE_TX,
      ROW_SHARE_LI, ROW_SHARE_VN, ROW_SHARE_HT, ROW_SHARE_CH
    )
  
  tgt <- target_lookup %>%
    filter(FILE_NAME == file_name) %>%
    pull(TARGET)
  
  if (length(tgt) != 1) {
    stop(paste("Could not find exactly one target for FILE_NAME:", file_name))
  }
  
  file_col_share <- column_share %>%
    filter(FILE_NAME == file_name)
  
  out_df <- base_df %>%
    select(ORIG, DEST)
  
  for (j in seq_len(nrow(file_col_share))) {
    col_nm <- file_col_share$COLUMN_NAME[j]
    access_mode_val <- as.character(file_col_share$ACCESS_MODE[j])
    col_share_val <- file_col_share$COLUMN_SHARE[j]
    
    row_share_col <- paste0("ROW_SHARE_", access_mode_val)
    
    if (!row_share_col %in% names(base_df)) {
      stop(paste("Missing row share column for ACCESS_MODE:", access_mode_val, "in FILE_NAME:", file_name))
    }
    
    out_df[[col_nm]] <- base_df[[row_share_col]] * col_share_val * tgt
  }
  
  out_df
}

# Convert a non-transit person-trip table to vehicle trips
person_to_vehicle_df <- function(person_df, file_name, column_share, conv_vec) {
  
  file_col_share <- column_share %>%
    filter(FILE_NAME == file_name)
  
  out_df <- person_df
  
  for (j in seq_len(nrow(file_col_share))) {
    col_nm <- file_col_share$COLUMN_NAME[j]
    access_mode_val <- as.character(file_col_share$ACCESS_MODE[j])
    submode_val <- as.character(file_col_share$SUBMODE[j])
    
    conv_factor <- get_conv_factor(access_mode_val, submode_val, conv_vec)
    out_df[[col_nm]] <- out_df[[col_nm]] / conv_factor
  }
  
  out_df
}

# Build transit person-trip table for one transit FILE_NAME
build_transit_person_df <- function(transit_file_name, transit_share, expanded_od, target_lookup, transit_zone_share) {
  
  file_transit_share <- transit_share %>%
    filter(TRANSIT_FILE_NAME == transit_file_name) %>%
    arrange(match(COLUMN_NAME, c("EA_TR", "AM_TR", "MD_TR", "PM_TR", "EV_TR")))
  
  base_file <- unique(file_transit_share$BASE_FILE_NAME)
  
  if (length(base_file) != 1) {
    stop(paste("Could not determine one base file for transit file:", transit_file_name))
  }
  
  base_rows <- expanded_od %>%
    filter(FILE_NAME == base_file) %>%
    select(FILE_NAME, AIRPORT, DIRECTION, ORIG, DEST, ZONE)
  
  if (nrow(base_rows) == 0) {
    stop(paste("No OD rows found for base file:", base_file, "used by transit file:", transit_file_name))
  }
  
  base_df <- base_rows %>%
    left_join(
      transit_zone_share,
      by = c("AIRPORT", "DIRECTION", "ZONE")
    )
  
  if (any(is.na(base_df$ROW_SHARE_TR))) {
    warning(paste("Some transit ROW_SHARE_TR values are missing after join for transit file:", transit_file_name,
                  "- check AIRPORT, DIRECTION, and ZONE matches in Transit_Zone_Shares."))
  }
  
  tgt <- target_lookup %>%
    filter(FILE_NAME == base_file) %>%
    pull(TARGET)
  
  if (length(tgt) != 1) {
    stop(paste("Could not find exactly one target for base file:", base_file))
  }
  
  out_df <- base_df %>%
    select(ORIG, DEST)
  
  for (j in seq_len(nrow(file_transit_share))) {
    col_nm <- file_transit_share$COLUMN_NAME[j]
    col_share_val <- file_transit_share$COLUMN_SHARE[j]
    
    out_df[[col_nm]] <- base_df$ROW_SHARE_TR * col_share_val * tgt
  }
  
  wanted_cols <- c("ORIG", "DEST", "EA_TR", "AM_TR", "MD_TR", "PM_TR", "EV_TR")
  for (nm in wanted_cols) {
    if (!nm %in% names(out_df)) out_df[[nm]] <- 0
  }
  
  out_df[, wanted_cols]
}

# Prepare a table for DBF writing
prepare_dbf_output <- function(df, digits = 2) {
  names(df) <- make.unique(substr(names(df), 1, 10), sep = "")
  df <- make_dbf_safe(df)
  df <- round_dbf_numeric(df, digits = digits)
  df
}

# -----------------------------
# Read input sheets
# -----------------------------
zone_def <- read_excel(xlsx_file, sheet = "Airport_File_Map") %>%
  clean_names_upper()

target_df <- read_excel(xlsx_file, sheet = "Air_Pax_Targets") %>%
  clean_names_upper()

zone_share <- read_excel(xlsx_file, sheet = "Super_Dist_Shares") %>%
  clean_names_upper()

zone_share_detail <- read_excel(xlsx_file, sheet = "Zone_Shares") %>%
  clean_names_upper()

col_share_raw <- read_excel(xlsx_file, sheet = "TOD_Access_Submode_Shares") %>%
  clean_names_upper()

transit_share_raw <- read_excel(xlsx_file, sheet = "Transit_TOD_Access_Shares") %>%
  clean_names_upper()

transit_zone_share_raw <- read_excel(xlsx_file, sheet = "Transit_Zone_Shares") %>%
  clean_names_upper()

conv_df <- read_excel(xlsx_file, sheet = "Veh_Occupancy") %>%
  clean_names_upper()

# -----------------------------
# Check required columns
# -----------------------------
req_zone_def <- c("FILE_NAME", "AIRPORT", "DIRECTION", "YEAR", "AIRPORT_TAZ", "TAZ_MIN", "TAZ_MAX")
if (!all(req_zone_def %in% names(zone_def))) {
  stop("Sheet Airport_File_Map is missing one or more required columns.")
}

req_target <- c("FILE_NAME", "AIRPORT", "DIRECTION", "YEAR", "TARGET")
if (!all(req_target %in% names(target_df))) {
  stop("Sheet Air_Pax_Targets is missing one or more required columns.")
}

req_zone_share <- c("FILE_NAME", "AIRPORT", "DIRECTION", "YEAR", "DISTRICT", "SHARE")
if (!all(req_zone_share %in% names(zone_share))) {
  stop("Sheet Super_Dist_Shares is missing one or more required columns.")
}

req_zone_share_detail <- c(
  "AIRPORT", "DIRECTION", "ZONE", "DISTRICT",
  "ZDIST_SHARE_ES", "ZDIST_SHARE_PK", "ZDIST_SHARE_RN", "ZDIST_SHARE_TX",
  "ZDIST_SHARE_LI", "ZDIST_SHARE_VN", "ZDIST_SHARE_HT", "ZDIST_SHARE_CH"
)
if (!all(req_zone_share_detail %in% names(zone_share_detail))) {
  stop("Sheet Zone_Shares is missing one or more required columns.")
}

req_col_share <- c(
  "FILE_NAME", "AIRPORT", "DIRECTION", "YEAR",
  "TOD", "ACCESS_MODE", "SUBMODE",
  "SHARE_TOD", "SHARE_ACCESSMODE", "SHARE_SUBMODE"
)
if (!all(req_col_share %in% names(col_share_raw))) {
  stop("Sheet TOD_Access_Submode_Shares is missing one or more required columns.")
}

req_transit <- c("FILE_NAME", "ACCESS_MODE", "TOD", "SHARE_ACCESSMODE", "SHARE_TOD")
if (!all(req_transit %in% names(transit_share_raw))) {
  stop("Sheet Transit_Shares is missing one or more required columns.")
}

req_transit_zone_share <- c("AIRPORT", "DIRECTION", "ZONE", "ZSHARE_TR")
if (!all(req_transit_zone_share %in% names(transit_zone_share_raw))) {
  stop("Sheet Transit_Zone_Shares is missing one or more required columns.")
}

req_conv <- c("SUBMODE", "CONVERSION_FACTOR")
if (!all(req_conv %in% names(conv_df))) {
  stop("Sheet Veh_Occupancy is missing one or more required columns.")
}

if (!"VN_HT_CH_S3" %in% conv_df$SUBMODE) {
  warning("Veh_Occupancy does not contain SUBMODE = 'VN_HT_CH_S3'. VN/HT/CH S3 trips will fall back to the default S3 factor if present.")
}

# -----------------------------
# Read shapefile and build TAZ-DISTRICT lookup
# -----------------------------
taz_shp <- st_read(shp_file, quiet = TRUE) %>%
  clean_names_upper()

taz_col <- names(taz_shp)[names(taz_shp) %in% c("TAZ1454", "TAZ", "ZONE", "ZONE_ID", "TAZ_ID")][1]
district_col <- names(taz_shp)[names(taz_shp) %in% c("DISTRICT", "SUPERDIST", "SUPERDISTID", "DISTRICT_ID")][1]

if (is.na(taz_col) || is.na(district_col)) {
  stop("Could not find TAZ and DISTRICT fields in shapefile.")
}

taz_lookup <- taz_shp %>%
  st_drop_geometry() %>%
  transmute(
    TAZ = as.integer(.data[[taz_col]]),
    DISTRICT = as.character(.data[[district_col]])
  ) %>%
  distinct()

# -----------------------------
# Prepare DISTRICT SHARE values
# -----------------------------
zone_share2 <- zone_share %>%
  transmute(
    FILE_NAME = as.character(FILE_NAME),
    AIRPORT = as.character(AIRPORT),
    DIRECTION = tolower(trimws(as.character(DIRECTION))),
    YEAR = as.character(YEAR),
    DISTRICT = as.character(DISTRICT),
    SHARE = to_share(SHARE)
  )

# -----------------------------
# Prepare access-mode-specific within-district zone shares
# Same zone shares are used for both 2023 and 2050.
# -----------------------------
zone_share_detail2 <- zone_share_detail %>%
  transmute(
    AIRPORT = as.character(AIRPORT),
    DIRECTION = tolower(trimws(as.character(DIRECTION))),
    ZONE = as.integer(ZONE),
    DISTRICT = as.character(DISTRICT),
    ZDIST_SHARE_ES = to_share(ZDIST_SHARE_ES),
    ZDIST_SHARE_PK = to_share(ZDIST_SHARE_PK),
    ZDIST_SHARE_RN = to_share(ZDIST_SHARE_RN),
    ZDIST_SHARE_TX = to_share(ZDIST_SHARE_TX),
    ZDIST_SHARE_LI = to_share(ZDIST_SHARE_LI),
    ZDIST_SHARE_VN = to_share(ZDIST_SHARE_VN),
    ZDIST_SHARE_HT = to_share(ZDIST_SHARE_HT),
    ZDIST_SHARE_CH = to_share(ZDIST_SHARE_CH)
  )

# -----------------------------
# Prepare transit zone shares
# -----------------------------
transit_zone_share <- transit_zone_share_raw %>%
  transmute(
    AIRPORT = as.character(AIRPORT),
    DIRECTION = tolower(trimws(as.character(DIRECTION))),
    ZONE = as.integer(ZONE),
    ROW_SHARE_TR = to_share(ZSHARE_TR)
  )

# Warning for districts where the within-district sums are zero
# i.e. no trips in the Gosling data
zone_share_check <- zone_share_detail2 %>%
  group_by(AIRPORT, DIRECTION, DISTRICT) %>%
  summarise(
    SUM_ES = sum(ZDIST_SHARE_ES, na.rm = TRUE),
    SUM_PK = sum(ZDIST_SHARE_PK, na.rm = TRUE),
    SUM_RN = sum(ZDIST_SHARE_RN, na.rm = TRUE),
    SUM_TX = sum(ZDIST_SHARE_TX, na.rm = TRUE),
    SUM_LI = sum(ZDIST_SHARE_LI, na.rm = TRUE),
    SUM_VN = sum(ZDIST_SHARE_VN, na.rm = TRUE),
    SUM_HT = sum(ZDIST_SHARE_HT, na.rm = TRUE),
    SUM_CH = sum(ZDIST_SHARE_CH, na.rm = TRUE),
    .groups = "drop"
  )

if (any(zone_share_check$SUM_ES == 0 |
        zone_share_check$SUM_PK == 0 |
        zone_share_check$SUM_RN == 0 |
        zone_share_check$SUM_TX == 0 |
        zone_share_check$SUM_LI == 0 |
        zone_share_check$SUM_VN == 0 |
        zone_share_check$SUM_HT == 0 |
        zone_share_check$SUM_CH == 0)) {
  warning("Some Zone_Shares groups sum to 0 for one or more access modes. Those district/mode combinations will produce all-zero outputs.")
}

# Warning for AIRPORT/DIRECTION groups where transit zonal shares sum to zero
transit_zone_share_check <- transit_zone_share %>%
  group_by(AIRPORT, DIRECTION) %>%
  summarise(
    SUM_TR = sum(ROW_SHARE_TR, na.rm = TRUE),
    .groups = "drop"
  )

if (any(transit_zone_share_check$SUM_TR == 0)) {
  warning("Some Transit_Zone_Shares groups sum to 0. Those AIRPORT/DIRECTION combinations will produce all-zero transit outputs.")
}

# -----------------------------
# Build ORIG and DEST pairs
# from: ORIG = AIRPORT_TAZ, DEST = TAZ range
# to:   ORIG = TAZ range,   DEST = AIRPORT_TAZ
# -----------------------------
expanded_list <- vector("list", nrow(zone_def))

for (i in seq_len(nrow(zone_def))) {
  
  file_name   <- as.character(zone_def$FILE_NAME[i])
  airport     <- as.character(zone_def$AIRPORT[i])
  direction   <- tolower(trimws(as.character(zone_def$DIRECTION[i])))
  year_val    <- as.character(zone_def$YEAR[i])
  airport_taz <- as.integer(zone_def$AIRPORT_TAZ[i])
  taz_min     <- as.integer(zone_def$TAZ_MIN[i])
  taz_max     <- as.integer(zone_def$TAZ_MAX[i])
  
  taz_seq <- seq(taz_min, taz_max)
  
  if (direction == "from") {
    tmp <- tibble(
      FILE_NAME = file_name,
      AIRPORT = airport,
      DIRECTION = direction,
      YEAR = year_val,
      ORIG = airport_taz,
      DEST = taz_seq
    )
  } else if (direction == "to") {
    tmp <- tibble(
      FILE_NAME = file_name,
      AIRPORT = airport,
      DIRECTION = direction,
      YEAR = year_val,
      ORIG = taz_seq,
      DEST = airport_taz
    )
  } else {
    stop(paste("Unexpected DIRECTION value for FILE_NAME:", file_name))
  }
  
  expanded_list[[i]] <- tmp
}

expanded_od <- bind_rows(expanded_list)

# -----------------------------
# Attach DISTRICT
# from-files use DEST district
# to-files use ORIG district
# -----------------------------
expanded_od <- expanded_od %>%
  left_join(
    taz_lookup %>% rename(ORIG = TAZ, ORIG_DISTRICT = DISTRICT),
    by = "ORIG"
  ) %>%
  left_join(
    taz_lookup %>% rename(DEST = TAZ, DEST_DISTRICT = DISTRICT),
    by = "DEST"
  ) %>%
  mutate(
    DISTRICT = if_else(DIRECTION == "from", DEST_DISTRICT, ORIG_DISTRICT),
    ZONE = if_else(DIRECTION == "from", DEST, ORIG)
  )

# -----------------------------
# Join DISTRICT SHARE and access-mode-specific ZONE SHARE values
# ROW_SHARE_<mode> = district share × within-district zone share for that access mode
# -----------------------------
expanded_od <- expanded_od %>%
  left_join(
    zone_share2 %>% select(FILE_NAME, DISTRICT, SHARE),
    by = c("FILE_NAME", "DISTRICT")
  ) %>%
  left_join(
    zone_share_detail2,
    by = c("AIRPORT", "DIRECTION", "ZONE", "DISTRICT")
  ) %>%
  mutate(
    ROW_SHARE_ES = SHARE * ZDIST_SHARE_ES,
    ROW_SHARE_PK = SHARE * ZDIST_SHARE_PK,
    ROW_SHARE_RN = SHARE * ZDIST_SHARE_RN,
    ROW_SHARE_TX = SHARE * ZDIST_SHARE_TX,
    ROW_SHARE_LI = SHARE * ZDIST_SHARE_LI,
    ROW_SHARE_VN = SHARE * ZDIST_SHARE_VN,
    ROW_SHARE_HT = SHARE * ZDIST_SHARE_HT,
    ROW_SHARE_CH = SHARE * ZDIST_SHARE_CH
  )

if (any(is.na(expanded_od$SHARE))) {
  warning("Some district SHARE values are missing after join. Check FILE_NAME and DISTRICT matches.")
}

if (any(is.na(expanded_od$ROW_SHARE_ES)) ||
    any(is.na(expanded_od$ROW_SHARE_PK)) ||
    any(is.na(expanded_od$ROW_SHARE_RN)) ||
    any(is.na(expanded_od$ROW_SHARE_TX)) ||
    any(is.na(expanded_od$ROW_SHARE_LI)) ||
    any(is.na(expanded_od$ROW_SHARE_VN)) ||
    any(is.na(expanded_od$ROW_SHARE_HT)) ||
    any(is.na(expanded_od$ROW_SHARE_CH))) {
  warning("Some access-mode-specific ROW_SHARE values are missing after join. Check AIRPORT, DIRECTION, ZONE, and DISTRICT matches in Zone_Shares.")
}

# -----------------------------
# Prepare main output shares
# SHARE_TOD × SHARE_ACCESSMODE × SHARE_SUBMODE
# -----------------------------
column_share <- col_share_raw %>%
  transmute(
    FILE_NAME = as.character(FILE_NAME),
    TOD = as.character(TOD),
    ACCESS_MODE = as.character(ACCESS_MODE),
    SUBMODE = as.character(SUBMODE),
    SHARE_TOD = to_share(SHARE_TOD),
    SHARE_ACCESSMODE = to_share(SHARE_ACCESSMODE),
    SHARE_SUBMODE = to_share(SHARE_SUBMODE)
  ) %>%
  mutate(
    COLUMN_NAME = paste(TOD, ACCESS_MODE, SUBMODE, sep = "_"),
    COLUMN_SHARE = SHARE_TOD * SHARE_ACCESSMODE * SHARE_SUBMODE
  ) %>%
  select(FILE_NAME, COLUMN_NAME, ACCESS_MODE, SUBMODE, COLUMN_SHARE)

# -----------------------------
# Prepare transit output shares
# SHARE_ACCESSMODE × SHARE_TOD
# -----------------------------
transit_share <- transit_share_raw %>%
  transmute(
    FILE_NAME = as.character(FILE_NAME),
    ACCESS_MODE = as.character(ACCESS_MODE),
    TOD = as.character(TOD),
    SHARE_ACCESSMODE = to_share(SHARE_ACCESSMODE),
    SHARE_TOD = to_share(SHARE_TOD)
  ) %>%
  mutate(
    COLUMN_NAME = paste(TOD, ACCESS_MODE, sep = "_"),
    COLUMN_SHARE = SHARE_ACCESSMODE * SHARE_TOD
  ) %>%
  select(FILE_NAME, COLUMN_NAME, COLUMN_SHARE)

# -----------------------------
# Prepare TARGET lookup
# -----------------------------
target_lookup <- target_df %>%
  transmute(
    FILE_NAME = as.character(FILE_NAME),
    TARGET = as.numeric(TARGET)
  )

# -----------------------------
# Prepare CONVERSION lookup
# -----------------------------
conv_lookup <- conv_df %>%
  transmute(
    SUBMODE = as.character(SUBMODE),
    CONVERSION_FACTOR = as.numeric(CONVERSION_FACTOR)
  )

conv_vec <- setNames(conv_lookup$CONVERSION_FACTOR, conv_lookup$SUBMODE)

# ============================================================
# PART A: Build main 12 files
# First calculate person trips, then convert to vehicle trips
# ============================================================
file_list <- unique(zone_def$FILE_NAME)

# Optional: store person-trip tables in memory for QA/debugging
nontransit_person_tables <- list()
nontransit_vehicle_tables <- list()

for (f in file_list) {
  
  # Step 1: person trips
  person_df <- build_nontransit_person_df(
    file_name = f,
    expanded_od = expanded_od,
    column_share = column_share,
    target_lookup = target_lookup
  )
  
  if (nrow(person_df) != 1454) {
    warning(paste("Main person-trip table", f, "has", nrow(person_df), "rows. Expected 1454."))
  }
  
  nontransit_person_tables[[f]] <- person_df
  
  # Step 2: convert to vehicle trips
  vehicle_df <- person_to_vehicle_df(
    person_df = person_df,
    file_name = f,
    column_share = column_share,
    conv_vec = conv_vec
  )
  
  if (nrow(vehicle_df) != 1454) {
    warning(paste("Main vehicle-trip table", f, "has", nrow(vehicle_df), "rows. Expected 1454."))
  }
  
  nontransit_vehicle_tables[[f]] <- vehicle_df
  
  # Step 3: write vehicle DBF
  out_df <- prepare_dbf_output(vehicle_df, digits = 2)
  
  out_file <- file.path(output_dir_main, paste0(f, ".dbf"))
  foreign::write.dbf(out_df, out_file)
  
  message("Written main DBF: ", out_file)
}

# ============================================================
# PART B: Build additional 12 transit-only files
# Transit outputs are person trips
# ============================================================

transit_share <- transit_share_raw %>%
  transmute(
    TRANSIT_FILE_NAME = as.character(FILE_NAME),
    BASE_FILE_NAME = sub("^TR_", "", as.character(FILE_NAME)),
    ACCESS_MODE = as.character(ACCESS_MODE),
    TOD = as.character(TOD),
    SHARE_ACCESSMODE = to_share(SHARE_ACCESSMODE),
    SHARE_TOD = to_share(SHARE_TOD)
  ) %>%
  mutate(
    COLUMN_NAME = paste0(TOD, "_TR"),
    COLUMN_SHARE = SHARE_ACCESSMODE * SHARE_TOD
  ) %>%
  select(TRANSIT_FILE_NAME, BASE_FILE_NAME, COLUMN_NAME, COLUMN_SHARE)

transit_file_list <- unique(transit_share$TRANSIT_FILE_NAME)

# Optional: store transit person-trip tables in memory for QA/debugging
transit_person_tables <- list()

for (f_tr in transit_file_list) {
  
  person_df_tr <- build_transit_person_df(
    transit_file_name = f_tr,
    transit_share = transit_share,
    expanded_od = expanded_od,
    target_lookup = target_lookup,
    transit_zone_share = transit_zone_share
  )
  
  if (nrow(person_df_tr) != 1454) {
    warning(paste("Transit person-trip table", f_tr, "has", nrow(person_df_tr), "rows. Expected 1454."))
  }
  
  transit_person_tables[[f_tr]] <- person_df_tr
  
  out_df_tr <- prepare_dbf_output(person_df_tr, digits = 2)
  
  out_file_tr <- file.path(output_dir_transit, paste0(f_tr, ".dbf"))
  foreign::write.dbf(out_df_tr, out_file_tr)
  
  message("Written transit DBF: ", out_file_tr)
}

# -----------------------------
# WRITE NON-TRANSIT PERSON-TRIP DBFs
# Stand-alone block to run AFTER the full script has been run for debugging
# -----------------------------

# Assumes these objects already exist from the main script:
#   - nontransit_person_tables
#   - output_dir_main
#   - prepare_dbf_output()
#
# message("Writing person-trip DBFs with file names prefixed by 'PER'...")
#
# for (f in names(nontransit_person_tables)) {
#   out_df_per <- prepare_dbf_output(nontransit_person_tables[[f]], digits = 2)
#   out_file_per <- file.path(output_dir_main, paste0("PER", f, ".dbf"))
#   foreign::write.dbf(out_df_per, out_file_per)
#   message("Wrote person-trip DBF: ", out_file_per)
# }
# 
# message("Done writing person-trip DBFs.")

# -----------------------------
# WRITE TRANSIT PERSON-TRIP DBFs
# Stand-alone block to run AFTER the full script has been run
# -----------------------------

# Assumes these objects already exist from the main script:
#   - transit_person_tables
#   - output_dir_transit
#   - prepare_dbf_output()
#
# message("Writing transit person-trip DBFs with file names prefixed by 'PER'...")
#
# for (f_tr in names(transit_person_tables)) {
#   out_df_tr_per <- prepare_dbf_output(transit_person_tables[[f_tr]], digits = 2)
#   out_file_tr_per <- file.path(output_dir_transit, paste0("PER", f_tr, ".dbf"))
#   foreign::write.dbf(out_df_tr_per, out_file_tr_per)
#   message("Wrote transit person-trip DBF: ", out_file_tr_per)
# }
#
# message("Done writing transit person-trip DBFs.")