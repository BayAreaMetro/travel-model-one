USAGE = r"""

  Replaces MtcProcessAbagData (https://github.com/BayAreaMetro/travel-model-one/blob/master/core/projects/mtc/src/java/com/pb/mtc/ctramp/MtcProcessAbagData.java)

  UrbanSim produces zonal data needed by the MTC travel model.
  This script does some processing to prep it for use, combining the UrbanSim output with baseyear (2000) tazdata

  It does 3 major steps:
  1) create parking costs
  2) creates school enrollment
  3) calculates terminal time
  4) copies columns DISTRICT, TOPOLOGY, ZERO from baseyear (2000) tazdata

  More documentation for each of the three steps inline.

"""

import argparse, logging, os, sys
import numpy, pandas

LOG_FILE                = "buildTazdata.log"
REFERENCE_DIR           = "M:\\Application\\Model One\\Zonal Data\\Plan Bay Area 2040\\2016 12 19 Proposed Plan\\Scenario 0"
BASEYEAR_TAZDATA        = os.path.join(REFERENCE_DIR, "tazData2000.csv")
SCHOOLAGE_DISTRIBUTION  = os.path.join(REFERENCE_DIR, "censusSchoolAgeDistributionsByZone2010.csv")
COLLEGEAGE_DISTRIBUTION = os.path.join(REFERENCE_DIR, "pumsStudentsByAgeDistributionsByZone2010.csv")

def calculateTerminalTime(baseyear_tazdata_df, tazdata_df):
    """
    Terminal time is the time an automobile traveler must take traveling from their vehicle to their final destination.
    This time includes the time spent searching for a parking space and the time spent walking from the parking 
    location to the final destination.

    The BAYCAST model used twelve-separate measures of terminal time that did not change from the base year to the
    forecast year.  The twelve values included three values each for each combination of peak and off-peak, and 
    production end and attraction end.  The three values represented the centroid travel time (which replaced the
    value coded on the network), the parking location search time, and the parking location to final destination
    walk time.  The current travel model does not use peak/off-peak travel time periods and does not generate trip
    productions and attractions.  To simplify the input data, a simple model was created to first replicate the values
    Chuck Purvis had coded for the base year and then forecast these values in application.  The goal was to replicate
    the parking location search time plus the parking location to final destination walk time, while the centroid
    time is now coded directly on the network. 

    The linear model (see ModelTerminalAndAccessTime.sas) is as follows:

    Terminal time (minutes) = 0.8974 + 0.01717 * area type density * no parking cost dummy + 
                                       0.66574 * log(employment density) * parking cost dummy,

    where area type density is the formula Chuck Purvis used to compute area type: 
    (total population + 2.5 * total employment)/(residential acres + commercial acres)  no parking cost dummy is 1 
    if the zone has no parking cost, 0 otherwise; employment density is the total employment divided by the commercial
    acres, the natural logarithm of this value gives the log(employment density variable); and, the parking cost dummy
    is 1 if the zone has a parking cost, 0 otherwise. 
    
    Returns the tazdata_df with TERMINAL column added
    """
    # terminal time model coefficients
    TERMINAL_TIME_MODEL_CONSTANT                 = 89.74158
    TERMINAL_TIME_MODEL_K_AREA_TYPE              = 1.71712
    TERMINAL_TIME_MODEL_K_LOG_employmentDensity  = 66.57370

    # compute the so-called "area type" density, which is what Chuck used to compute area type
    tazdata_df["developedAcres" ] = tazdata_df["CIACRE"] + tazdata_df["RESACRE"]
    tazdata_df["areaTypeDensity"] = 0.0
    tazdata_df.loc[ tazdata_df["developedAcres"] > 0, "areaTypeDensity"] = (tazdata_df["TOTPOP"] + 2.5*tazdata_df["TOTEMP"])/tazdata_df["developedAcres"]

    # compute the logarithm of employment density
    tazdata_df["employmentDensity"] = 0.0
    tazdata_df.loc[ tazdata_df["CIACRE"] > 0, "employmentDensity" ] = tazdata_df["TOTEMP"]/tazdata_df["CIACRE"]
    tazdata_df["logEmploymentDensity"] = numpy.log(tazdata_df["employmentDensity"] + 1.0)

    # set the parking cost dummy variable
    tazdata_df["nonZeroParkingCostDummy"] = 0
    tazdata_df.loc[ tazdata_df["PRKCST"] > 0, "nonZeroParkingCostDummy" ] = 1

    # apply the model (which gives terminal time in minutes x 100)
    tazdata_df["areaTypeDensityForZeroParkingCostZones"]         = tazdata_df["areaTypeDensity"]*(1-tazdata_df["nonZeroParkingCostDummy"])
    tazdata_df["logEmploymentDensityForNonZeroParkingCostZones"] = tazdata_df["logEmploymentDensity"]*tazdata_df["nonZeroParkingCostDummy"]
    tazdata_df["TERMINAL"] =  TERMINAL_TIME_MODEL_CONSTANT + (TERMINAL_TIME_MODEL_K_AREA_TYPE * tazdata_df["areaTypeDensityForZeroParkingCostZones"])  + \
                                       (TERMINAL_TIME_MODEL_K_LOG_employmentDensity * tazdata_df["logEmploymentDensityForNonZeroParkingCostZones"])
            
    # scale the results by 100
    tazdata_df["TERMINAL"] = tazdata_df["TERMINAL"]*0.01

    # remove intermediate variables
    tazdata_df.drop(columns=["developedAcres","areaTypeDensity","employmentDensity","logEmploymentDensity",
                             "nonZeroParkingCostDummy","areaTypeDensityForZeroParkingCostZones",
                             "logEmploymentDensityForNonZeroParkingCostZones"], inplace=True)
    return tazdata_df

def createSchoolEnrollmentDataSet(baseyear_tazdata_df, tazdata_df):
    """
    High school and college enrollment is predicted via a simple model in which high school and college enrollment increases
    by a proportion equal to the increase in the number of high school and college students in each school's county.  Thus,
    high schools and colleges are neither created nor destroyed.  Rather, each increases as student-age population increases.
    Note that factors generated from Census data are used to compute the number of high school and college students from the
    number of persons in different age categories (this data is predicted by ABAG).  As such, these factors do not change from
    the base year to the forecast year. 

    The method implements the simple model long used by Chuck Purvis.  It assumes that high school and college
    enrollment increases with the county-level increase in high school students and college students, respectively.
    For high school enrollment, the software uses the proportions in the SCHOOLAGE_DISTRIBUTION file to
    compute the number of persons age 14 to 17 in each zone.  Next, it is assumed that 96.6 percent of all persons
    this age attend high school outside of the home; this coefficient is hard coded in the software.  The resulting
    number of high school students is then aggregated to the county level of geography.  The ratio between the forecast
    year high school students by county and the base year high school students by county is applied to the base year 
    high school enrollment estimate, by zone, to generate an estimate of forecast year high school enrollment by zone. 
    
    For college enrollment, both full-time and part-time, a similar approach is used.  Here, the software first uses
    the proportions in the COLLEGEAGE_DISTRIBUTION file to compute the number of persons age 18 to 19,
    20 to 24, and 24 to 44 in each zone.  Next, the proportions in the SCHOOLAGE_DISTRIBUTION
    are used to compute the number of college students in each of these age categories.  The resulting number
    of college students is then aggregated to the county level of geography.  The ratio between the forecast year
    number of college students by county and the forecast year number of college students by county is applied to
    the base year estimate of college enrollment, both full-time and part-time, to generate an estimate of forecast
    year college enrollment by zone. 

    Returns tazdata_df with high school enrollment, college full time enrollment and college part time enrollment added.
    """
    HIGH_SCHOOL_ENROLLMENT_MODEL_SHARE_OF_HS_AGE_KIDS_ENROLLED_IN_HS = 0.966

    ageShares            = pandas.read_csv(SCHOOLAGE_DISTRIBUTION)
    collegeStudentShares = pandas.read_csv(COLLEGEAGE_DISTRIBUTION)

    logging.debug("Age shares:\n{}".format(ageShares.head()))
    logging.debug("College Student shares:\n{}".format(collegeStudentShares.head()))

    # join to tazdata, baseyear_tazdata_df
    tazdata_df          = pandas.merge(left=         tazdata_df, right=ageShares,            how="left")
    tazdata_df          = pandas.merge(left=         tazdata_df, right=collegeStudentShares, how="left")
    baseyear_tazdata_df = pandas.merge(left=baseyear_tazdata_df, right=ageShares,            how="left")
    baseyear_tazdata_df = pandas.merge(left=baseyear_tazdata_df, right=collegeStudentShares, how="left")

    # compute the number of high school students -- assume X percent of kids this age attend high school, as calculated by Chuck
    tazdata_df["highSchoolStudents"]          =          tazdata_df["AGE0519"]*         tazdata_df["14to17In05to19"]*HIGH_SCHOOL_ENROLLMENT_MODEL_SHARE_OF_HS_AGE_KIDS_ENROLLED_IN_HS
    baseyear_tazdata_df["highSchoolStudents"] = baseyear_tazdata_df["AGE0519"]*baseyear_tazdata_df["14to17In05to19"]*HIGH_SCHOOL_ENROLLMENT_MODEL_SHARE_OF_HS_AGE_KIDS_ENROLLED_IN_HS

    # compute the number of college students
    tazdata_df["collegeStudents"]          = (         tazdata_df["AGE0519"]*         tazdata_df["18to19In05to19"]*         tazdata_df["StudentsAge18to19"]) + \
                                             (         tazdata_df["AGE2044"]*         tazdata_df["20to24In20to44"]*         tazdata_df["StudentsAge20to24"]) + \
                                             (         tazdata_df["AGE2044"]*         tazdata_df["25to44In20to44"]*         tazdata_df["StudentsAge25to44"])
    baseyear_tazdata_df["collegeStudents"] = (baseyear_tazdata_df["AGE0519"]*baseyear_tazdata_df["18to19In05to19"]*baseyear_tazdata_df["StudentsAge18to19"]) + \
                                             (baseyear_tazdata_df["AGE2044"]*baseyear_tazdata_df["20to24In20to44"]*baseyear_tazdata_df["StudentsAge20to24"]) + \
                                             (baseyear_tazdata_df["AGE2044"]*baseyear_tazdata_df["25to44In20to44"]*baseyear_tazdata_df["StudentsAge25to44"])

    # sum high school and college students by county
    baseyear_students_df = baseyear_tazdata_df[["COUNTY","highSchoolStudents","collegeStudents"]].groupby("COUNTY").agg("sum")
    forecast_students_df =          tazdata_df[["COUNTY","highSchoolStudents","collegeStudents"]].groupby("COUNTY").agg("sum")

    # rename and join baseyear and forecast county tables
    baseyear_students_df.rename(columns={"highSchoolStudents":"highSchoolStudents_baseyear", "collegeStudents":"collegeStudents_baseyear"}, inplace=True)
    forecast_students_df.rename(columns={"highSchoolStudents":"highSchoolStudents_forecast", "collegeStudents":"collegeStudents_forecast"}, inplace=True)
    students_df = pandas.merge(left=baseyear_students_df, right=forecast_students_df, left_index=True, right_index=True)

    students_df["highSchoolGrowthRatio"] = students_df["highSchoolStudents_forecast"]/students_df["highSchoolStudents_baseyear"]
    students_df["collegeGrowthRatio"   ] = students_df["collegeStudents_forecast"]   /students_df["collegeStudents_baseyear"]
    logging.debug("students_df:\n{}".format(students_df))

    # join growth ratios to baseyear_tazdata_df and apply
    baseyear_tazdata_df = pandas.merge(left=baseyear_tazdata_df, right=students_df[["highSchoolGrowthRatio","collegeGrowthRatio"]], how="left", left_on="COUNTY", right_index=True)
    baseyear_tazdata_df["HSENROLL_forecast"] = baseyear_tazdata_df["HSENROLL"]*baseyear_tazdata_df["highSchoolGrowthRatio"]
    baseyear_tazdata_df["COLLFTE_forecast"]  = baseyear_tazdata_df["COLLFTE"] *baseyear_tazdata_df["collegeGrowthRatio"]
    baseyear_tazdata_df["COLLPTE_forecast"]  = baseyear_tazdata_df["COLLPTE"] *baseyear_tazdata_df["collegeGrowthRatio"]

    # join result to tazdata_df
    tazdata_df = pandas.merge(left=tazdata_df, right=baseyear_tazdata_df[["ZONE","HSENROLL_forecast","COLLFTE_forecast","COLLPTE_forecast"]], how="left", on="ZONE")
    tazdata_df.rename(columns={"HSENROLL_forecast":"HSENROLL",
                               "COLLFTE_forecast" :"COLLFTE",
                               "COLLPTE_forecast" :"COLLPTE"}, inplace=True)

    # remove intermediate variables
    tazdata_df.drop(columns=["05to13In05to19","14to17In05to19","18to19In05to19","25to44In20to44","20to24In20to44",
                             "StudentsAge18to19","StudentsAge20to24","StudentsAge25to44",
                             "highSchoolStudents","collegeStudents"], inplace=True)
    return tazdata_df


def createParkingCostDataSet(baseyear_tazdata_df, tazdata_df):
    """
    A simple model is used to predict future year parking cost.  Specifically, the parking cost is increased proportionally
    with the change in employment density (in units of employees per developed commercial/industrial acre).  Zones in which
    employment density decreases retain the base year parking cost.  Note that the model uses two parking costs: (1) the hourly
    rate paid by parkers who pay monthly (assumed for work travel) and (2) the hourly rate paid by parkers who pay hourly. 
    Zones do not go from a zero to a non-zero parking price or vice versa; the model assumes that all zones with a parking cost
    will continue to have a parking cost and all zones without a parking price will continue to not have a parking price.   
    
    The method implements the simple model long used by Chuck Purvis.  It assumes that parking cost increases
    with the change in employment density.  The software computes the employment density (total employees divided
    by commercial/industrial acres) for the base year and employment density for the forecast year, and then 
    computes the ratio of the two.  If the employment density declines, the ratio is reset to 1.0, making the 
    assumption that parking prices are more quicker to increase in the face of demand than decrease.  The growth
    ratio is applied to both the monthly parkers hourly rate and the hourly parkers hourly rate.  Zones with no
    parking cost in the base year do not become priced in the forecast years. 

    @return TableDataSet containing the following data: zone number, hourly rate for parkers who pay monthly (in the same units
    as in the input base year travel model data), and hourly rate for parkers who pay hourly
    """
    # compute the employment density
    tazdata_df["employmentDensity"] = 0.0
    tazdata_df.loc[ tazdata_df["CIACRE"] > 0, "employmentDensity" ] = tazdata_df["TOTEMP"]/tazdata_df["CIACRE"]

    baseyear_tazdata_df["employmentDensity_baseyear"] = 0.0
    baseyear_tazdata_df.loc[ baseyear_tazdata_df["CIACRE"] > 0, "employmentDensity_baseyear" ] = baseyear_tazdata_df["TOTEMP"]/baseyear_tazdata_df["CIACRE"]

    # if these are set, clear them since we'll set them
    if "PRKCST" in list(tazdata_df.columns.values):
        tazdata_df.drop(columns=["PRKCST","OPRKCST"], inplace=True)

    # compute the ratio of densities between the base year and the forecast year
    tazdata_df = pandas.merge(left=tazdata_df, right=baseyear_tazdata_df[["ZONE","employmentDensity_baseyear","PRKCST","OPRKCST"]], how="left", on="ZONE")
    tazdata_df["employmentDensityRatio"] = 0.0
    tazdata_df.loc[ tazdata_df["employmentDensity_baseyear"] > 0, "employmentDensityRatio" ] = tazdata_df["employmentDensity"]/tazdata_df["employmentDensity_baseyear"]
    # do not allow decreasing parking costs
    tazdata_df.loc[ tazdata_df["employmentDensityRatio"] <1.0,  "employmentDensityRatio" ] = 1.0

    tazdata_df["PRKCST"]  = tazdata_df["PRKCST"]*tazdata_df["employmentDensityRatio"]
    tazdata_df["OPRKCST"] = tazdata_df["OPRKCST"]*tazdata_df["employmentDensityRatio"]

    # remove intermediate variables
    baseyear_tazdata_df.drop(columns=["employmentDensity_baseyear"], inplace=True)
    tazdata_df.drop(columns=["employmentDensity","employmentDensity_baseyear","employmentDensityRatio"], inplace=True)
    return tazdata_df

if __name__ == '__main__':
    pandas.options.display.width = 500
    pandas.options.display.max_rows = 1000

    # create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(ch)
    # file handler
    fh = logging.FileHandler(LOG_FILE, mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(fh)

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    # parser.add_argument("model_year", help="Model year")
    parser.add_argument("urbansim_taz_summary", metavar="urbansim_taz_summary.csv", help="UrbanSim output taz summary file")
    args = parser.parse_args()

    # read the baseyear 2000 tazdata
    baseyear_tazdata_df = pandas.read_csv(BASEYEAR_TAZDATA)
    baseyear_tazdata_cols = list(baseyear_tazdata_df.columns.values)

    logging.info("Read {}\n{}".format(BASEYEAR_TAZDATA, baseyear_tazdata_df.head()))
    logging.debug("dtypes:\n{}".format(baseyear_tazdata_df.dtypes))
    # read in the urbansim taz summary
    tazdata_df = pandas.read_csv(args.urbansim_taz_summary)
    logging.info("Read {}\n{}".format(args.urbansim_taz_summary, tazdata_df.head()))
    logging.debug("dtypes:\n{}".format(tazdata_df.dtypes))

    tazdata_df = createParkingCostDataSet(baseyear_tazdata_df, tazdata_df)

    # only createSchoolEnrollmentDataSet() if needed
    taz_cols = list(tazdata_df.columns.values)
    if ('HSENROLL' in taz_cols) and ('COLLFTE' in taz_cols) and ('COLLPTE' in taz_cols):
        logger.info("Skipping createSchoolEnrollmentDataSet() because HSENROLL, COLLFTE, COLLPTE are already present: {}".format(taz_cols))
    else:
        tazdata_df = createSchoolEnrollmentDataSet(baseyear_tazdata_df, tazdata_df)

    tazdata_df = calculateTerminalTime(baseyear_tazdata_df, tazdata_df)

    # for colname in baseyear_tazdata_cols:
    #     if colname not in list(tazdata_df.columns.values):
    #         print("Column {} missing".format(colname))

    # finally pull a few columns directly
    baseyear_copy_cols = ["DISTRICT","TOPOLOGY","ZERO"]
    for col in baseyear_copy_cols:
        if col in list(tazdata_df.columns.values): tazdata_df.drop(columns=[col], inplace=True)

    tazdata_df = pandas.merge(left=tazdata_df, right=baseyear_tazdata_df[["ZONE"]+baseyear_copy_cols], how="left", on="ZONE")
    tazdata_df = tazdata_df[baseyear_tazdata_cols]

    # and set the types to match
    tazdata_dtypes = baseyear_tazdata_df.dtypes.to_dict()
    tazdata_dtypes["TOTACRE"] = "float64"
    tazdata_dtypes["RESACRE"] = "float64"
    tazdata_dtypes["CIACRE" ] = "float64"
    print(tazdata_dtypes)
    tazdata_df = tazdata_df.astype(dtype=tazdata_dtypes)
    tazdata_df.to_csv("tazData.csv", header=True, index=False, float_format='%.5f')

    logging.info("Wrote tazData.csv")
