package com.pb.mtc.ctramp;

import java.io.File;
import java.io.IOException;
import java.util.ResourceBundle;
import java.util.HashMap;

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.CSVFileWriter;
import com.pb.common.datafile.TableDataSet;
import org.apache.log4j.Logger;


/**
 * Association of Bay Area Governments (ABAG) staff delivers zonal data needed by the MTC travel model.
 * Note that data may be delivered by ABAG in two formats.  The first is the Projections format and the
 * second is the Steelhead (PECAS) format.  The class reads in either format and then processes it using 
 * methods developed by Chuck Purvis to build zonal data inputs needed by the MTC travel model.
 * 
 * @author D. Ory
 *
 *  TODO get dummy input from mike
 *  TODO test (different version or some option for mike's pecas inputs?
 *
 */

public class MtcProcessAbagData {
	
	// use logger class to write error messages and status information
	public static Logger logger = Logger.getLogger(MtcTourBasedModel.class);
	
	// the properties (control) file contains these variables
	protected static final String PROPERTIES_PROJECT_DIRECTORY                 = "Project.Directory";
	protected static final String PROPERTIES_ABAG_PROJECTIONS_FILE_NAME        = "ABAG.ProjectionsData.Input.File";
	protected static final String PROPERTIES_BASE_YEAR_FILE_NAME               = "TravelModel.ZonalData.ReferenceYear.Input.File";
	protected static final String PROPERTIES_AGE_SHARES_FILE_NAME              = "DemographicCrosswalk.AgeGroupsByZone.Input.File";
	protected static final String PROPERTIES_COLLEGE_STUDENTS_SHARES_FILE_NAME = "DemographicCrosswalk.StudentsByAgeGroupsByZone.Input.File";
	protected static final String PROPERTIES_FORECAST_YEAR_OUTPUT_FILE_NAME    = "TravelModel.ZonalData.ForecastYear.Output.File";
	
	// the input and output zonal data uses the standard MTC variable names
	private static final String COLUMN_NAME_ZONE                              = MtcTazDataHandler.ZONE_DATA_ZONE_FIELD_NAME;
	private static final String COLUMN_NAME_SUPER_DISTRICT                    = MtcTazDataHandler.ZONE_DATA_DISTRICT_FIELD_NAME;
	private static final String COLUMN_NAME_COUNTY                            = MtcTazDataHandler.ZONE_DATA_COUNTY_FIELD_NAME;
	private static final String COLUMN_NAME_HOUSEHOLDS                        = MtcTazDataHandler.ZONE_DATA_HH_FIELD_NAME;
	private static final String COLUMN_NAME_MONTHLY_PAYER_HOURLY_PARKING_RATE = MtcTazDataHandler.ZONE_DATA_PEAK_HOURLY_PARKING_COST_FIELD_NAME;
	private static final String COLUMN_NAME_HOURLY_PAYER_HOURLY_PARKING_RATE  = MtcTazDataHandler.ZONE_DATA_OFFPEAK_HOURLY_PARKING_COST_FIELD_NAME;
	private static final String COLUMN_NAME_TOTAL_EMPLOYMENT                  = MtcTazDataHandler.ZONE_DATA_EMP_FIELD_NAME;
	private static final String COLUMN_NAME_TOTAL_POPULATION                  = MtcTazDataHandler.ZONE_DATA_POP_FIELD_NAME;
	private static final String COLUMN_NAME_HOUSEHOLD_POPULATION              = MtcTazDataHandler.ZONE_DATA_HH_POP_FIELD_NAME;
	private static final String COLUMN_NAME_COMMERCIAL_ACRES                  = MtcTazDataHandler.ZONE_DATA_COMACRE_FIELD_NAME;
	private static final String COLUMN_NAME_RESIDENTIAL_ACRES                 = MtcTazDataHandler.ZONE_DATA_RESACRE_FIELD_NAME;
	private static final String COLUMN_NAME_STUDENTS_AGE_05_TO_19             = MtcTazDataHandler.ZONE_DATA_PERSONS_AGE_05_TO_19_FIELD_NAME;
	private static final String COLUMN_NAME_STUDENTS_AGE_20_TO_44             = MtcTazDataHandler.ZONE_DATA_PERSONS_AGE_20_TO_44_FIELD_NAME;
	private static final String COLUMN_NAME_HIGH_SCHOOL_ENROLLMENT            = MtcTazDataHandler.ZONE_DATA_HIGH_SCHOOL_ENROLLMENT_FIELD_NAME;
	private static final String COLUMN_NAME_COLLEGE_FULL_TIME_ENROLLMENT      = MtcTazDataHandler.ZONE_DATA_COLLEGE_FULL_TIME_ENROLLMENT_FIELD_NAME;
	private static final String COLUMN_NAME_COLLEGE_PART_TIME_ENROLLMENT      = MtcTazDataHandler.ZONE_DATA_COLLEGE_PART_TIME_ENROLLMENT_FIELD_NAME;
	private static final String COLUMN_NAME_TERMINAL_TIME                     = MtcTazDataHandler.ZONE_DATA_TERMINAL_TIME_FIELD_NAME;
	
	// variables in the PROPERTIES_AGE_SHARES_FILE_NAME data
	protected static final String COLUMN_NAME_AGE_DISTRIBUTION_TO_17 = "14to17In05to19";
	protected static final String COLUMN_NAME_AGE_DISTRIBUTION_TO_19 = "18to19In05to19";
	protected static final String COLUMN_NAME_AGE_DISTRIBUTION_TO_24 = "20to24In20to44";
	protected static final String COLUMN_NAME_AGE_DISTRIBUTION_TO_44 = "25to44In20to44";
	
	// variables in the PROPERTIES_COLLEGE_STUDENTS_SHARES_FILE_NAME data
	protected static final String COLUMN_NAME_COLLEGE_DISTRIBUTION_TO_19 = "StudentsAge18to19";
	protected static final String COLUMN_NAME_COLLEGE_DISTRIBUTION_TO_24 = "StudentsAge20to24";
	protected static final String COLUMN_NAME_COLLEGE_DISTRIBUTION_TO_44 = "StudentsAge25to44";
	
	// terminal time model coefficients
	protected static final float TERMINAL_TIME_MODEL_CONSTANT                 = 89.74158f;
	protected static final float TERMINAL_TIME_MODEL_K_AREA_TYPE              = 1.71712f;
	protected static final float TERMINAL_TIME_MODEL_K_LOG_EMPLOYMENT_DENSITY = 66.57370f;
	
	// number of high school students model coefficients
	protected static final float HIGH_SCHOOL_ENROLLMENT_MODEL_SHARE_OF_HS_AGE_KIDS_ENROLLED_IN_HS = 0.966f;
	
	// label for households in the population synthesizer software
	protected static final String COLUMN_NAME_POPSYN_HOUSEHOLDS = "hhlds";
	protected static final String COLUMN_NAME_POPSYN_SFTAZ = "sftaz";
	protected static final String COLUMN_NAME_POPSYN_GROUP_QUARTERS_POPULATION = "gqpop";
	
	// object variables
	protected ResourceBundle resourceBundle;
	protected String projectDirectory;
	protected int[] baseYearZoneNumbersIntArray;
	protected TableDataSet baseYearDataSet;
	protected TableDataSet abagForecastYearDataSet;
	protected HashMap<Integer,Integer> giveZoneGetCounty;
	
	/**
	 * Sets the project directory from the properties file, reads in the base year TAZ travel model data, 
	 * reads in the forecast year ABAG data, sets the base year TAZ numbers array, and builds the zone-
	 * to-county cross walk.
	 * 
	 * @param passedInResourceBundle must contain all of the PROPERTIES_ variables in the object. 
	 */
	public MtcProcessAbagData(ResourceBundle passedInResourceBundle){
		
		this.resourceBundle = passedInResourceBundle;
		
		// set the project directory
		projectDirectory = resourceBundle.getString(PROPERTIES_PROJECT_DIRECTORY);
		
		// read in the base year data set
		baseYearDataSet = new TableDataSet();
		String baseYearDataFile = resourceBundle.getString( PROPERTIES_BASE_YEAR_FILE_NAME );
		baseYearDataFile = projectDirectory + baseYearDataFile; 
		try{
			CSVFileReader CSVReader = new CSVFileReader();
			baseYearDataSet = CSVReader.readFile(new File(baseYearDataFile));
		} catch (IOException e){
			logger.error("Unable to read CSV file " + baseYearDataFile);
		}
		
		// read in the abag projections data set
		abagForecastYearDataSet = new TableDataSet();
		String abagForecastYearDataFile = resourceBundle.getString(PROPERTIES_ABAG_PROJECTIONS_FILE_NAME);
		abagForecastYearDataFile = projectDirectory + abagForecastYearDataFile; 
		try{
			CSVFileReader CSVReader = new CSVFileReader();
			abagForecastYearDataSet = CSVReader.readFile(new File(abagForecastYearDataFile));
		} catch (IOException e){
			logger.error("Unable to read CSV file " + abagForecastYearDataFile);
		}
		
		// set the base year zone array
		baseYearZoneNumbersIntArray = baseYearDataSet.getColumnAsInt(COLUMN_NAME_ZONE);
		
		// set the zone-to-county hash map
		int[] countyColumn = baseYearDataSet.getColumnAsInt(COLUMN_NAME_COUNTY);
		giveZoneGetCounty = new HashMap<Integer,Integer>(baseYearZoneNumbersIntArray.length);
		for(int i=0;i<baseYearZoneNumbersIntArray.length;++i){
			giveZoneGetCounty.put(baseYearZoneNumbersIntArray[i], countyColumn[i]);
		}

	}
	
	/**
	 * Terminal time is the time an automobile traveler must take traveling from their vehicle to their final destination.
	 * This time includes the time spent searching for a parking space and the time spent walking from the parking 
	 * location to the final destination.  A simple model is used to predict terminal time.  Please see the SAS file
	 * ModelTerminalAndAccessTime.sas for full details.  
	 * 
	 * @return a TableDataSet that contains two variables: zone number and terminal time in minutes. The terminal time is 
	 * the time to travel from a vehicle parking location to a final destination. 
	 */
	private TableDataSet createTerminalTimeDataSet(){
		
		// create hash maps to store the forecast year variables
		HashMap<Integer,Float> areaTypeDensityMap      = new HashMap<Integer,Float>(baseYearZoneNumbersIntArray.length);
		HashMap<Integer,Float> logEmploymentDensityMap = new HashMap<Integer,Float>(baseYearZoneNumbersIntArray.length);
		
		// the application is a model that needs only the forecast year data -- loop through
		for(int i=0;i<abagForecastYearDataSet.getRowCount();i++){
			
			int row = i + 1;
			
			// get the key forecast year inputs
			int zoneNumber = (int) abagForecastYearDataSet.getValueAt(row, COLUMN_NAME_ZONE);
			float residentialAcres = abagForecastYearDataSet.getValueAt(row, COLUMN_NAME_RESIDENTIAL_ACRES);
			float commercialAcres  = abagForecastYearDataSet.getValueAt(row, COLUMN_NAME_COMMERCIAL_ACRES);
			float totalPopulation  = abagForecastYearDataSet.getValueAt(row, COLUMN_NAME_TOTAL_POPULATION);
			float totalEmployment  = abagForecastYearDataSet.getValueAt(row, COLUMN_NAME_TOTAL_EMPLOYMENT);
			
			// compute the so-called "area type" density, which is what Chuck used to compute area type
			float developedAcres = residentialAcres + commercialAcres;
			float areaTypeDensity = 0.0f;
			if(developedAcres>0.0){
				areaTypeDensity = (float) (totalPopulation + 2.5 * totalEmployment)/developedAcres;
			}
			areaTypeDensityMap.put(zoneNumber, areaTypeDensity);
			
			// compute the logarithm of employment density
			double employmentDensity = 0.0;
			if(commercialAcres>0.0){
				employmentDensity = totalEmployment/commercialAcres;
			}
			
			logEmploymentDensityMap.put(zoneNumber,(float) Math.log(employmentDensity + 1.0));
		}
		
		// apply the model to each zone in the base year data set
		float[] terminalTimeModelResults = new float[baseYearZoneNumbersIntArray.length];
		for(int i=0;i<baseYearDataSet.getRowCount();i++){
			
			int row = i + 1;
			
			int zoneNumber = baseYearZoneNumbersIntArray[i];
			
			// set the parking cost dummy variable
			float parkingCost = baseYearDataSet.getValueAt(row, COLUMN_NAME_MONTHLY_PAYER_HOURLY_PARKING_RATE);
			int nonZeroParkingCostDummy = 0;
			if(parkingCost>0.0) nonZeroParkingCostDummy = 1;
			
			// apply the model (which gives terminal time in minutes x 100)
			float areaTypeDensityForZeroParkingCostZones         = areaTypeDensityMap.get(zoneNumber) * (1 - nonZeroParkingCostDummy);
			float logEmploymentDensityForNonZeroParkingCostZones = logEmploymentDensityMap.get(zoneNumber) * nonZeroParkingCostDummy; 
			terminalTimeModelResults[i] = TERMINAL_TIME_MODEL_CONSTANT + TERMINAL_TIME_MODEL_K_AREA_TYPE * areaTypeDensityForZeroParkingCostZones +
			                              TERMINAL_TIME_MODEL_K_LOG_EMPLOYMENT_DENSITY * logEmploymentDensityForNonZeroParkingCostZones;
			
	        // scale the results by 100
			terminalTimeModelResults[i] *= 0.01f;
		}
		
		// build the output file
		String[] columnNames = {COLUMN_NAME_ZONE, COLUMN_NAME_TERMINAL_TIME};
		TableDataSet terminalTimeDataSet = TableDataSet.create(new float[baseYearZoneNumbersIntArray.length][columnNames.length], columnNames);
		terminalTimeDataSet.setColumnLabels(columnNames);
		
		// the output file zones will be the same as the base year zones
		terminalTimeDataSet.setColumnAsInt(terminalTimeDataSet.getColumnPosition(COLUMN_NAME_ZONE), baseYearZoneNumbersIntArray);
		
		// set the model results
		terminalTimeDataSet.setColumnAsFloat(terminalTimeDataSet.getColumnPosition(COLUMN_NAME_TERMINAL_TIME), terminalTimeModelResults);
		
		return (terminalTimeDataSet);
	}
	
	/**
	 * High school and college enrollment is predicted via a simple model in which high school and college enrollment increases
	 * by a proportion equal to the increase in the number of high school and college students in each school's county.  Thus,
	 * high schools and colleges are neither created nor destroyed.  Rather, each increases as student-age population increases.
	 * Note that factors generated from Census data are used to compute the number of high school and college students from the
	 * number of persons in different age categories (this data is predicted by ABAG).  As such, these factors do not change from
	 * the base year to the forecast year. 
	 *  
	 * @return TableDataSet which contains the following variables: zone number, high school enrollment, college full time enrollment
	 * and college part time enrollment. 
	 * 
	 */
	private TableDataSet createSchoolEnrollmentDataSet(){
		
		// read in the refined age category shares
		TableDataSet ageSharesDataSet = new TableDataSet();
		String ageSharesFileName = resourceBundle.getString(PROPERTIES_AGE_SHARES_FILE_NAME);
		ageSharesFileName = projectDirectory + ageSharesFileName; 
		try{
			CSVFileReader CSVReader = new CSVFileReader();
			ageSharesDataSet = CSVReader.readFile(new File(ageSharesFileName));
		} catch (IOException e){
			logger.error("Unable to read CSV file " + ageSharesFileName);
		}
		
		// read in the college students by age category file
		TableDataSet collegeStudentSharesDataSet = new TableDataSet();
		String collegeStudentSharesFileName = resourceBundle.getString(PROPERTIES_COLLEGE_STUDENTS_SHARES_FILE_NAME);
		collegeStudentSharesFileName = projectDirectory + collegeStudentSharesFileName; 
		try{
			CSVFileReader CSVReader = new CSVFileReader();
			collegeStudentSharesDataSet = CSVReader.readFile(new File(collegeStudentSharesFileName));
		} catch (IOException e){
			logger.error("Unable to read CSV file " + collegeStudentSharesFileName);
		}
		
		// build hash maps for the age shares data set
		HashMap<Integer,Float> shareOfPersons14to17In05to19CategoryMap = new HashMap<Integer,Float>(baseYearZoneNumbersIntArray.length);
		HashMap<Integer,Float> shareOfPersons18to19In05to19CategoryMap = new HashMap<Integer,Float>(baseYearZoneNumbersIntArray.length);
		HashMap<Integer,Float> shareOfPersons20to24In20to44CategoryMap = new HashMap<Integer,Float>(baseYearZoneNumbersIntArray.length);
		HashMap<Integer,Float> shareOfPersons25to44In20to44CategoryMap = new HashMap<Integer,Float>(baseYearZoneNumbersIntArray.length);
		
		// fill the hash maps for the age shares
		for(int i=0;i<ageSharesDataSet.getRowCount();++i){
			
			// the get value calls use a 1-based row value
			int row = i+1;
			
			Integer zoneNumber = (int) ageSharesDataSet.getValueAt(row, COLUMN_NAME_ZONE);
			shareOfPersons14to17In05to19CategoryMap.put(zoneNumber, ageSharesDataSet.getValueAt(row, COLUMN_NAME_AGE_DISTRIBUTION_TO_17));
			shareOfPersons18to19In05to19CategoryMap.put(zoneNumber, ageSharesDataSet.getValueAt(row, COLUMN_NAME_AGE_DISTRIBUTION_TO_19));
			shareOfPersons20to24In20to44CategoryMap.put(zoneNumber, ageSharesDataSet.getValueAt(row, COLUMN_NAME_AGE_DISTRIBUTION_TO_24));
			shareOfPersons25to44In20to44CategoryMap.put(zoneNumber, ageSharesDataSet.getValueAt(row, COLUMN_NAME_AGE_DISTRIBUTION_TO_44));
			
		}
		
		// build hash maps for the college students in each age category
		HashMap<Integer,Float> shareOfPersonsAge18to19InCollegeMap = new HashMap<Integer,Float>(baseYearZoneNumbersIntArray.length);
		HashMap<Integer,Float> shareOfPersonsAge20to24InCollegeMap = new HashMap<Integer,Float>(baseYearZoneNumbersIntArray.length);
		HashMap<Integer,Float> shareOfPersonsAge25to44InCollegeMap = new HashMap<Integer,Float>(baseYearZoneNumbersIntArray.length);
		
		// fill in the hash maps for the college students in each age category shares
		for(int i=0;i<collegeStudentSharesDataSet.getRowCount();++i){
			
			// the get value calls use a 1-based row value
			int row = i+1;
			
			Integer zoneNumber = (int) collegeStudentSharesDataSet.getValueAt(row, COLUMN_NAME_ZONE);
			shareOfPersonsAge18to19InCollegeMap.put(zoneNumber, collegeStudentSharesDataSet.getValueAt(row, COLUMN_NAME_COLLEGE_DISTRIBUTION_TO_19));
			shareOfPersonsAge20to24InCollegeMap.put(zoneNumber, collegeStudentSharesDataSet.getValueAt(row, COLUMN_NAME_COLLEGE_DISTRIBUTION_TO_24));
			shareOfPersonsAge25to44InCollegeMap.put(zoneNumber, collegeStudentSharesDataSet.getValueAt(row, COLUMN_NAME_COLLEGE_DISTRIBUTION_TO_44));
			
		}
		
		// sum high school and college students by county (use maps to allow county numbers to vary, though start with nine)
        HashMap<Integer,Float> forecastYearHighSchoolStudentsByCounty = new HashMap<Integer,Float>(9);
		HashMap<Integer,Float> forecastYearCollegeStudentsByCounty    = new HashMap<Integer,Float>(9);
		for(int i=0;i<abagForecastYearDataSet.getRowCount();i++){
			
			// the get value calls use a 1-based row value
			int row = i+1;
			
			Integer zoneNumber = (int) abagForecastYearDataSet.getValueAt(row, COLUMN_NAME_ZONE);
			int countyNumber = giveZoneGetCounty.get(zoneNumber);
			float runningSum = 0.0f;
			
			float personsAge05to19 = abagForecastYearDataSet.getValueAt(row, COLUMN_NAME_STUDENTS_AGE_05_TO_19);
			float personsAge20to44 = abagForecastYearDataSet.getValueAt(row, COLUMN_NAME_STUDENTS_AGE_20_TO_44);
			
			// compute the number of high school students -- assume X percent of kids this age attend high school, as calculated by Chuck
			float highSchoolStudents = personsAge05to19 * shareOfPersons14to17In05to19CategoryMap.get(zoneNumber) * HIGH_SCHOOL_ENROLLMENT_MODEL_SHARE_OF_HS_AGE_KIDS_ENROLLED_IN_HS;
			
			runningSum = highSchoolStudents;
			if(forecastYearHighSchoolStudentsByCounty.containsKey(countyNumber)){
				runningSum += forecastYearHighSchoolStudentsByCounty.get(countyNumber);
			}
			
			forecastYearHighSchoolStudentsByCounty.put(countyNumber,runningSum);
			
			// compute the number of college students
			float collegeStudents = personsAge05to19 * shareOfPersons18to19In05to19CategoryMap.get(zoneNumber) * shareOfPersonsAge18to19InCollegeMap.get(zoneNumber) + 
			                        personsAge20to44 * shareOfPersons20to24In20to44CategoryMap.get(zoneNumber) * shareOfPersonsAge20to24InCollegeMap.get(zoneNumber) +
			                        personsAge20to44 * shareOfPersons25to44In20to44CategoryMap.get(zoneNumber) * shareOfPersonsAge25to44InCollegeMap.get(zoneNumber);
			
			runningSum = collegeStudents;
			if(forecastYearCollegeStudentsByCounty.containsKey(countyNumber)){
				runningSum += forecastYearCollegeStudentsByCounty.get(countyNumber);
			}
			
			forecastYearCollegeStudentsByCounty.put(countyNumber, runningSum);
			
		}
		
		// sum base year high school and college students by county
		HashMap<Integer,Float> baseYearHighSchoolStudentsByCounty = new HashMap<Integer,Float>(9);
		HashMap<Integer,Float> baseYearCollegeStudentsByCounty    = new HashMap<Integer,Float>(9);
		for(int i=0;i<baseYearZoneNumbersIntArray.length;i++){
			
			// the get value calls use a 1-based row value
			int row = i+1;
			
			int zoneNumber   = this.baseYearZoneNumbersIntArray[i];
			int countyNumber = giveZoneGetCounty.get(zoneNumber);
			float runningSum = 0.0f;
			
			float personsAge05to19 = baseYearDataSet.getValueAt(row, COLUMN_NAME_STUDENTS_AGE_05_TO_19);
			float personsAge20to44 = baseYearDataSet.getValueAt(row, COLUMN_NAME_STUDENTS_AGE_20_TO_44);
			
			// compute the number of high school students -- assume X percent of kids this age attend high school, as calculated by Chuck
			float highSchoolStudents = personsAge05to19 * shareOfPersons14to17In05to19CategoryMap.get(zoneNumber) * HIGH_SCHOOL_ENROLLMENT_MODEL_SHARE_OF_HS_AGE_KIDS_ENROLLED_IN_HS;
			
			runningSum = highSchoolStudents;
			if(baseYearHighSchoolStudentsByCounty.containsKey(countyNumber)){
				runningSum += baseYearHighSchoolStudentsByCounty.get(countyNumber);
			}
			
			baseYearHighSchoolStudentsByCounty.put(countyNumber, runningSum);
			
			// compute the number of college students
			float collegeStudents = personsAge05to19 * shareOfPersons18to19In05to19CategoryMap.get(zoneNumber) * shareOfPersonsAge18to19InCollegeMap.get(zoneNumber) + 
                                    personsAge20to44 * shareOfPersons20to24In20to44CategoryMap.get(zoneNumber) * shareOfPersonsAge20to24InCollegeMap.get(zoneNumber) +
                                    personsAge20to44 * shareOfPersons25to44In20to44CategoryMap.get(zoneNumber) * shareOfPersonsAge25to44InCollegeMap.get(zoneNumber); 
			
			runningSum = collegeStudents;
			if(baseYearCollegeStudentsByCounty.containsKey(countyNumber)){
				runningSum += baseYearCollegeStudentsByCounty.get(countyNumber);
			}
			
			baseYearCollegeStudentsByCounty.put(countyNumber, runningSum);
			
		}
		
		// build the output file
        String[] columnNames = {COLUMN_NAME_ZONE, COLUMN_NAME_HIGH_SCHOOL_ENROLLMENT, COLUMN_NAME_COLLEGE_FULL_TIME_ENROLLMENT, COLUMN_NAME_COLLEGE_PART_TIME_ENROLLMENT};
        TableDataSet schoolEnrollmentDataSet = TableDataSet.create(new float[baseYearZoneNumbersIntArray.length][columnNames.length], columnNames);
		schoolEnrollmentDataSet.setColumnLabels(columnNames);
		
		// the output file zones will be the same as the base year zones
		schoolEnrollmentDataSet.setColumnAsInt(schoolEnrollmentDataSet.getColumnPosition(COLUMN_NAME_ZONE), baseYearZoneNumbersIntArray);
		
		// grow the base year enrollment by the growth in students by county
		for(int i=0;i<baseYearZoneNumbersIntArray.length;++i){
			
			// the get value calls use a 1-based row value
			int row = i+1;
			
			int zoneNumber   = this.baseYearZoneNumbersIntArray[i];
			int countyNumber = giveZoneGetCounty.get(zoneNumber);
			
			// high school enrollment
			float baseYearEnrollment   = baseYearDataSet.getValueAt(row, COLUMN_NAME_HIGH_SCHOOL_ENROLLMENT);
			float baseYearStudents     = baseYearHighSchoolStudentsByCounty.get(countyNumber);
			float forecastYearStudents = forecastYearHighSchoolStudentsByCounty.get(countyNumber);
			float growthRatio = 1.0f;
			if(baseYearStudents>0.0) growthRatio = forecastYearStudents/baseYearStudents;
			float forecastYearEnrollment = baseYearEnrollment * growthRatio;
			schoolEnrollmentDataSet.setValueAt(row, COLUMN_NAME_HIGH_SCHOOL_ENROLLMENT, forecastYearEnrollment);
			
			// college enrollment -- full time
			baseYearEnrollment   = baseYearDataSet.getValueAt(row, COLUMN_NAME_COLLEGE_FULL_TIME_ENROLLMENT);
			baseYearStudents     = baseYearCollegeStudentsByCounty.get(countyNumber);
			forecastYearStudents = forecastYearCollegeStudentsByCounty.get(countyNumber);
			growthRatio = 1.0f;
			if(baseYearStudents>0.0) growthRatio = forecastYearStudents/baseYearStudents;
			forecastYearEnrollment = baseYearEnrollment * growthRatio;
			schoolEnrollmentDataSet.setValueAt(row, COLUMN_NAME_COLLEGE_FULL_TIME_ENROLLMENT, forecastYearEnrollment);
			
			// college enrollment -- part time (same growth factor)
			baseYearEnrollment   = baseYearDataSet.getValueAt(row, COLUMN_NAME_COLLEGE_PART_TIME_ENROLLMENT);
			forecastYearEnrollment = baseYearEnrollment * growthRatio;
			schoolEnrollmentDataSet.setValueAt(row, COLUMN_NAME_COLLEGE_PART_TIME_ENROLLMENT, forecastYearEnrollment);
			
		}
		
		return (schoolEnrollmentDataSet);
	}
	
	/**
	 * A simple model is used to predict future year parking cost.  Specifically, the parking cost is increased proportionally
	 * with the change in employment density (in units of employees per developed commercial/industrial acre).  Zones in which
	 * employment density decreases retain the base year parking cost.  Note that the model uses two parking costs: (1) the hourly
	 * rate paid by parkers who pay monthly (assumed for work travel) and (2) the hourly rate paid by parkers who pay hourly. 
	 * Zones do not go from a zero to a non-zero parking price or vice versa; the model assumes that all zones with a parking cost
	 * will continue to have a parking cost and all zones without a parking price will continue to not have a parking price.   
	 * 
	 * @return TableDataSet containing the following data: zone number, hourly rate for parkers who pay monthly (in the same units
	 * as in the input base year travel model data), and hourly rate for parkers who pay hourly
	 * 
	 */
	private TableDataSet createParkingCostDataSet (){
		
		// use a hash map to store the forecast year data in case the table is not sorted
		HashMap<Integer,Float> forecastYearEmploymentDensityMap = new HashMap<Integer,Float>(baseYearZoneNumbersIntArray.length);
		
		// store zone number in an int array to avoid having to cast a float from getValueAt()
		int[] forecastYearZoneNumberIntArray = abagForecastYearDataSet.getColumnAsInt(COLUMN_NAME_ZONE);
		
		// loop through the table to compute the forecast year employment density
		for(int i=0;i<abagForecastYearDataSet.getRowCount();i++){
			
			// the get value calls use a 1-based row
			int row = i+1;
			
			// get the density data from the table data set
			float totalEmployment = abagForecastYearDataSet.getValueAt(row, COLUMN_NAME_TOTAL_EMPLOYMENT); 
			float commercialAcres = abagForecastYearDataSet.getValueAt(row, COLUMN_NAME_COMMERCIAL_ACRES);
			
			// set density to zero if there are no commercial acres
			Float employmentDensity = 0.0f;
			if(commercialAcres>0.0) employmentDensity = totalEmployment/commercialAcres;
			
			forecastYearEmploymentDensityMap.put(forecastYearZoneNumberIntArray[i], employmentDensity);
			
		}
		
        // build the output file
        String[] columnNames = {COLUMN_NAME_ZONE,COLUMN_NAME_MONTHLY_PAYER_HOURLY_PARKING_RATE,COLUMN_NAME_HOURLY_PAYER_HOURLY_PARKING_RATE};
        TableDataSet parkingCostDataSet = TableDataSet.create(new float[baseYearZoneNumbersIntArray.length][columnNames.length], columnNames);  
		parkingCostDataSet.setColumnLabels(columnNames);
		
		// the output file zones will be the same as the base year zones
		parkingCostDataSet.setColumnAsInt(parkingCostDataSet.getColumnPosition(COLUMN_NAME_ZONE), baseYearZoneNumbersIntArray);
		
		// build the base year HashMaps (to avoid any problems with zones out of order) 
		for(int i=0;i<baseYearDataSet.getRowCount();i++){
			
			// the get value calls use a 1-based row
			int row = i+1;
			
			int zoneNumber = baseYearZoneNumbersIntArray[i];
			
			// compute the employment density
			float totalEmployment = baseYearDataSet.getValueAt(row, COLUMN_NAME_TOTAL_EMPLOYMENT); 
			float commercialAcres = baseYearDataSet.getValueAt(row, COLUMN_NAME_COMMERCIAL_ACRES);
			
			float baseYearEmploymentDensity = 0.0f;
			if(commercialAcres>0.0) baseYearEmploymentDensity = totalEmployment/commercialAcres;
			
			// get the base year parking rates
			float baseYearMonthlyPayerHourlyRate = baseYearDataSet.getValueAt(row, COLUMN_NAME_MONTHLY_PAYER_HOURLY_PARKING_RATE);
			float baseYearHourlyPayerHourlyRate  = baseYearDataSet.getValueAt(row, COLUMN_NAME_HOURLY_PAYER_HOURLY_PARKING_RATE);
			
			// compute the ratio of densities between the base year and the forecast year
			float employmentDensityRatio = 1.0f;
		    float forecastYearEmploymentDensity = forecastYearEmploymentDensityMap.get(zoneNumber);
		    if(forecastYearEmploymentDensityMap.get(zoneNumber) == null) logger.error("Zone number "+zoneNumber+" is not included in the ABAG forecast year dataset.");
		    
		    if(baseYearEmploymentDensity>0.0){
		    	employmentDensityRatio = forecastYearEmploymentDensity/baseYearEmploymentDensity;
		    	
		    	// do not allow decreasing parking costs
		    	if(employmentDensityRatio<1.0) employmentDensityRatio = 1.0f;
		    }
		    	
		    float forecastYearMonthlyPayerHourlyRate = baseYearMonthlyPayerHourlyRate * employmentDensityRatio;
		    float forecastYearHourlyPayerHourlyRate  = baseYearHourlyPayerHourlyRate * employmentDensityRatio;
		    
		    parkingCostDataSet.setValueAt(row, COLUMN_NAME_MONTHLY_PAYER_HOURLY_PARKING_RATE, forecastYearMonthlyPayerHourlyRate);
		    parkingCostDataSet.setValueAt(row, COLUMN_NAME_HOURLY_PAYER_HOURLY_PARKING_RATE, forecastYearHourlyPayerHourlyRate);
		    	
		} // for i
		
		return(parkingCostDataSet);
		    
	
	}
		

	/**
	 * Method first calls the models that generate the parking cost data, the school enrollment data, and the terminal time data.
	 * Next, a forecast year travel model zonal data file is created by first noting all the data elements are needed, and then
	 * updating base year data elements if they are present in either the ABAG projections data, the parking cost data, the school
	 * enrollment data, or the terminal time data.  Data items not in these four data sets are held constant to the forecast year 
	 * travel model data (from the base year travel model data).
	 * 
	 * @return TableDataSet with the same data elements as in PROPERTIES_BASE_YEAR_FILE_NAME
	 */
	private TableDataSet createForecastZonalData(){
				
		// compute the parking cost for the new data set
		TableDataSet parkingCostDataSet = createParkingCostDataSet();
		
		// compute high school and college enrollment for the new data set
		TableDataSet schoolEnrollmentDataSet = createSchoolEnrollmentDataSet();
		
		// compute the terminal time for the new data set
		TableDataSet terminalTimeDataSet = createTerminalTimeDataSet();
		
		// build the output file
		String[] columnNames = baseYearDataSet.getColumnLabels();
		TableDataSet forecastYearDataSet = TableDataSet.create(new float[baseYearZoneNumbersIntArray.length][columnNames.length]);
		forecastYearDataSet.setColumnLabels(columnNames);
		
		// loop through each forecast year column
		for(int i=0;i<forecastYearDataSet.getColumnCount();++i){
			
			// TableDataSet calls use a 1-based indexing
			int col = i + 1;
			
			String columnName = forecastYearDataSet.getColumnLabel(col);
			
			// copy zones, super districts, and county code from the base year file
			if(columnName.equalsIgnoreCase(COLUMN_NAME_ZONE)){
				forecastYearDataSet.setColumnAsInt(forecastYearDataSet.getColumnPosition(COLUMN_NAME_ZONE), baseYearZoneNumbersIntArray);
			}
			else if(columnName.equalsIgnoreCase(COLUMN_NAME_SUPER_DISTRICT)){
				forecastYearDataSet.setColumnAsInt(forecastYearDataSet.getColumnPosition(COLUMN_NAME_SUPER_DISTRICT), baseYearDataSet.getColumnAsInt(COLUMN_NAME_SUPER_DISTRICT));
			}
			else if(columnName.equalsIgnoreCase(COLUMN_NAME_COUNTY)){
				forecastYearDataSet.setColumnAsInt(forecastYearDataSet.getColumnPosition(COLUMN_NAME_COUNTY), baseYearDataSet.getColumnAsInt(COLUMN_NAME_COUNTY));
			}
				
			// if the data is in the abag forecast file, then replace it
			else if(abagForecastYearDataSet.containsColumn(columnName)){
				forecastYearDataSet.setColumnAsFloat(col, abagForecastYearDataSet.getColumnAsFloat(columnName));
			} 
			
			// else if the data is in the parking cost data set, then replace it
			else if(parkingCostDataSet.containsColumn(columnName)){
				forecastYearDataSet.setColumnAsFloat(col, parkingCostDataSet.getColumnAsFloat(columnName));
				
			}
			
			// else if the data is in the school enrollment data set, then replace it
			else if(schoolEnrollmentDataSet.containsColumn(columnName)){
				forecastYearDataSet.setColumnAsFloat(col, schoolEnrollmentDataSet.getColumnAsFloat(columnName));
			}
			
			// else if the data is in the terminal time data set, then replace it
			else if(terminalTimeDataSet.containsColumn(columnName)){
				forecastYearDataSet.setColumnAsFloat(col, terminalTimeDataSet.getColumnAsFloat(columnName));
			}
			
			// else just use the base year data (e.g. topology, which does not change)
			else{
				forecastYearDataSet.setColumnAsFloat(col, baseYearDataSet.getColumnAsFloat(columnName));
			}
		}
		
		// add data columns needed by the population synthesizer software
		//   - synthesizer reads households as "hhlds"
		forecastYearDataSet.appendColumn(abagForecastYearDataSet.getColumnAsInt(COLUMN_NAME_HOUSEHOLDS), COLUMN_NAME_POPSYN_HOUSEHOLDS);
		
		//   - synthesizer reads taz field as "sftaz"
		forecastYearDataSet.appendColumn(abagForecastYearDataSet.getColumnAsInt(COLUMN_NAME_ZONE), COLUMN_NAME_POPSYN_SFTAZ);
		
		//   - synthesizer needs group quarters population
		float[] totalPopulation = forecastYearDataSet.getColumnAsFloat(COLUMN_NAME_TOTAL_POPULATION);
		float[] householdPopulation = forecastYearDataSet.getColumnAsFloat(COLUMN_NAME_HOUSEHOLD_POPULATION);
		float[] gqPopulation = new float[totalPopulation.length];
		for(int i=0;i<gqPopulation.length;++i) gqPopulation[i] = totalPopulation[i] - householdPopulation[i];
		forecastYearDataSet.appendColumn(gqPopulation, COLUMN_NAME_POPSYN_GROUP_QUARTERS_POPULATION);
		
		
		
		return forecastYearDataSet;
		
	}
	
	/**
	 * Writes a TableDataSet to disk at PROPERTIES_PROJECT_DIRECTORY + PROPERTIES_FORECAST_YEAR_OUTPUT_FILE_NAME
	 * 
	 * @param passedInDataSet
	 */
	private void writeForecastYearTableToDisk(TableDataSet passedInDataSet){
		
		String outputFile = resourceBundle.getString(PROPERTIES_FORECAST_YEAR_OUTPUT_FILE_NAME);
		outputFile = projectDirectory + outputFile; 
		try{
			CSVFileWriter fileWriter = new CSVFileWriter();
			fileWriter.writeFile(passedInDataSet, new File(outputFile));
		} catch (IOException e){
			logger.error("Unable to write CSV file " + outputFile);
		}
				
	}
	
	/**
	 * Main prints the model version to the screen, calls the create forecast year data set, and then writes
	 * the resulting data set to disk.
	 * 
	 * @param args A single String naming the properties file prefix (i.e. the bit before .properties)
	 */
	public static void main(String[] args) {
		
		 // print the program version information to the screen
        logger.info("");
        logger.info("                      Process ABAG Data                 ");
        logger.info("                  Program Version: 2010Nov18            ");
        logger.info("      Developed by Metropolitan Transportation Commisson");
        logger.info("");
		
		ResourceBundle commandLineBundle = null;
        
		// name of the resource bundle is the first argument
        if (args.length == 0){
            logger.error( String.format( "Command line argument should be: <java command>.MtcProcessAbagData processAbag" ) );
            return;
        }
        else{
        	
        	commandLineBundle = ResourceBundle.getBundle(args[0]);
        	
        }
        
        MtcProcessAbagData mainObject = new MtcProcessAbagData(commandLineBundle);
        
        // create forecast year data
        logger.info(" Creating forecast year zonal data ...");
        TableDataSet forecastYearDataSet = mainObject.createForecastZonalData();
        
        // write the data set to disk
        logger.info(" Writing forecast year data to disk ...");
        mainObject.writeForecastYearTableToDisk(forecastYearDataSet);
        
        logger.info("");
        logger.info("End:  Process ABAG Data");
        
	}

}
