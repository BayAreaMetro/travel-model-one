package com.pb.mtc.ctramp;

import java.io.File;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.HashMap;

import org.apache.log4j.Logger;

import com.pb.common.datafile.OLD_CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.Tour;
import com.pb.models.ctramp.jppf.CtrampApplication;

public class MtcModelOutputReader {

    private transient Logger    logger                          = Logger.getLogger(MtcModelOutputReader.class);

    private static final String PROPERTIES_HOUSEHOLD_DATA_FILE  = "Accessibilities.HouseholdDataFile";
    private static final String PROPERTIES_PERSON_DATA_FILE     = "Accessibilities.PersonDataFile";
    private static final String PROPERTIES_INDIV_TOUR_DATA_FILE = "Accessibilities.IndivTourDataFile";
    private static final String PROPERTIES_JOINT_TOUR_DATA_FILE = "Accessibilities.JointTourDataFile";
    private static final String PROPERTIES_INDIV_TRIP_DATA_FILE = "Accessibilities.IndivTripDataFile";
    private static final String PROPERTIES_JOINT_TRIP_DATA_FILE = "Accessibilities.JointTripDataFile";
    private MtcModelStructure      modelStructure;
    private int                 iteration;
    private HashMap<String,String> rbMap;
    private HashMap<Long, HouseholdFileAttributes> householdFileAttributesMap;
    private HashMap<Long, PersonFileAttributes> personFileAttributesMap;
    private HashMap<Long, ArrayList<TourFileAttributes>> individualTourAttributesMap; //by person_id
    private HashMap<Long, ArrayList<TourFileAttributes>> jointTourAttributesMap; //by hh_id
    
    private boolean readIndividualTourFile = false;
    private boolean readJointTourFile = false;
   
    /**
     * Default constructor.
     * @param rbMap          Hashmap of properties
     * @param modelStructure Model structure object
     * @param iteration      Iteration number used for file names
     */
	public MtcModelOutputReader(HashMap<String,String> rbMap, MtcModelStructure modelStructure,
        int iteration)
	{
		logger.info("Writing data structures to files.");
		this.modelStructure = modelStructure;
		this.iteration = iteration;
		this.rbMap = rbMap;
	}
   
	/**
	 * Read household data and store records in householdFileAttributesMap
	 */
    public void readHouseholdDataOutput(){
		
		String baseDir = rbMap.get(CtrampApplication.PROPERTIES_PROJECT_DIRECTORY);
		String hhFile = rbMap.get(PROPERTIES_HOUSEHOLD_DATA_FILE);
		
	    TableDataSet householdData = readTableData(baseDir+hhFile);

	    householdFileAttributesMap = new HashMap<Long, HouseholdFileAttributes>();
	        
	    for(int row = 1; row<=householdData.getRowCount();++row){
	    	
	    	long hhid = (long) householdData.getValueAt(row,"hh_id");
			int taz = (int)householdData.getValueAt(row,"taz");
			int walk_subzone = (int)householdData.getValueAt(row,"walk_subzone");
	        int income = (int) householdData.getValueAt(row,"income");
	        int autos = (int) householdData.getValueAt(row,"autos");
	        int size = (int) householdData.getValueAt(row,"size");
	        int workers = (int) householdData.getValueAt(row,"workers");
	        int automated_vehicles = (int) householdData.getValueAt(row,"autonomousVehicles");
	        int human_vehicles = (int) householdData.getValueAt(row,"humanVehicles");
	        String cdap_pattern =  householdData.getStringValueAt(row,"cdap_pattern");
	        String jtf_pattern = householdData.getStringValueAt(row,"jtf_pattern");

	        HouseholdFileAttributes hhAttributes = new HouseholdFileAttributes(hhid,
	        		taz, walk_subzone, income, autos, size, workers, automated_vehicles,human_vehicles,cdap_pattern,
	        		jtf_pattern);
	        
	        householdFileAttributesMap.put(hhid, hhAttributes);

	    }
	}

    
    /**
     * Read the data from the Results.PersonDataFile.
     * Data is stored in HashMap personFileAttributesMap<person_id,PersonFileAttributes>
     * so that it can be retrieved quickly for a household object.
     * 
     */
	public void readPersonDataOutput(){
		
        //read person data
        String baseDir = rbMap.get(CtrampApplication.PROPERTIES_PROJECT_DIRECTORY);
        String personFile = baseDir + rbMap.get(PROPERTIES_PERSON_DATA_FILE);
        TableDataSet personData = readTableData(personFile);

        personFileAttributesMap = new HashMap<Long, PersonFileAttributes>();
        
        for(int row = 1; row<=personData.getRowCount();++row){
        	
        	
        	//get the values for this person
        	long hhid = (long) personData.getValueAt(row, "hh_id");
        	long person_id = (long) personData.getValueAt(row,"person_id");
        	long personNumber = (long) personData.getValueAt(row,"person_num");
        	int age = (int) personData.getValueAt(row,"age");
        	
        	String genderString = personData.getStringValueAt(row,"gender");
        	int gender = (genderString.compareTo("m")==0 ? 1 : 2);
        	
        	float valueOfTime = personData.getValueAt(row,"value_of_time");
        	String activityPattern = personData.getStringValueAt(row,"activity_pattern");
        	
        	String personTypeString = personData.getStringValueAt(row,"type");
        	int personType = getPersonType(personTypeString);
        	
        	int imfChoice = (int) personData.getValueAt(row, "imf_choice");
        	int inmfChoice = (int) personData.getValueAt(row, "inmf_choice");

        	PersonFileAttributes personFileAttributes = new PersonFileAttributes(hhid,person_id,personNumber,age,gender,valueOfTime,
        			activityPattern,personType,imfChoice,inmfChoice);
        	
        	personFileAttributesMap.put(person_id,personFileAttributes);
        	
        }

	}

	/**
	 * Read both tour files.
	 * 
	 */
	public void readTourDataOutput(){
		
		String baseDir = rbMap.get(CtrampApplication.PROPERTIES_PROJECT_DIRECTORY);
		
		if(rbMap.containsKey(PROPERTIES_INDIV_TOUR_DATA_FILE)){
			String indivTourFile = rbMap.get(PROPERTIES_INDIV_TOUR_DATA_FILE);
			if(indivTourFile != null){
				if(indivTourFile.length()>0){
					individualTourAttributesMap = readTourData(baseDir+indivTourFile, false, individualTourAttributesMap);
					readIndividualTourFile = true;
				}
			}
		}
		if(rbMap.containsKey(PROPERTIES_JOINT_TOUR_DATA_FILE)){
			String jointTourFile = rbMap.get(PROPERTIES_JOINT_TOUR_DATA_FILE);
			if(jointTourFile != null){
				if(jointTourFile.length()>0){
					jointTourAttributesMap = readTourData(baseDir+jointTourFile, true, jointTourAttributesMap);
					readJointTourFile = true;
				}
			}
		}
		if(readIndividualTourFile==false){
			logger.info("No individual tour file to read in MtcModelOutputReader class");
		}
		if(readJointTourFile==false){
			logger.info("No joint tour file to read in MtcModelOutputReader class");
		}
       
	}

	
    /**
     * Read the data from the Results.IndivTourDataFile or Results.JointTourDataFile.
     * Data is stored in HashMap passed into method as an argument. Method handles
     * both individual and joint data. Joint tour data is indexed by hh_id
     * so that it can be retrieved quickly for a household object. Individual tour data is
     * indexed by person_id.
     * 
     */
	public HashMap<Long, ArrayList<TourFileAttributes>> readTourData(String filename, boolean isJoint, HashMap<Long, ArrayList<TourFileAttributes>> tourFileAttributesMap ){
		
        TableDataSet tourData = readTableData(filename);

        tourFileAttributesMap = new HashMap<Long, ArrayList<TourFileAttributes>>();
        
        
        //atWork_freq	num_ob_stops	num_ib_stops	avAvailable

        for(int row = 1; row<=tourData.getRowCount();++row){
        	
    		long hh_id = (long) tourData.getValueAt(row,"hh_id");
    		long person_id = 0;
    		int person_num=0;
    		int person_type=0;
    		if(!isJoint){
    			person_id = (long) tourData.getValueAt(row,"person_id");;
    		    person_num            = (int) tourData.getValueAt(row,"person_num");            
        		person_type           = (int) tourData.getValueAt(row,"person_type");           
    		}
    		int tour_id               = (int) tourData.getValueAt(row,"tour_id");               
    		String tour_category      = tourData.getStringValueAt(row,"tour_category");         
    		String tour_purpose       = tourData.getStringValueAt(row,"tour_purpose");          
    		
    		int tour_composition = 0;
    		String tour_participants = null;
    		if(isJoint){
    			tour_composition = (int) tourData.getValueAt(row,"tour_composition");
    			tour_participants = tourData.getStringValueAt(row,"tour_participants");
    		}
    		
    		int orig_taz             = (int) tourData.getValueAt(row,"orig_taz"); 
    		int orig_walk_segment    = (int) tourData.getValueAt(row,"orig_walk_segment"); 
    		     		
    		int dest_taz             = (int) tourData.getValueAt(row,"dest_taz"); 
    		int dest_walk_segment    = (int) tourData.getValueAt(row,"dest_walk_segment");
    		int start_hour          = (int) tourData.getValueAt(row,"start_hour");          
    		int end_hour            = (int) tourData.getValueAt(row,"end_hour");            
    		int tour_mode             = (int) tourData.getValueAt(row,"tour_mode");             
    		int atWork_freq           = (int) tourData.getValueAt(row,"atWork_freq");           
    		int num_ob_stops          = (int) tourData.getValueAt(row,"num_ob_stops");          
    		int num_ib_stops          = (int) tourData.getValueAt(row,"num_ib_stops");          
    		int avAvailable           = (int) tourData.getValueAt(row,"avAvailable");           
    		
    		TourFileAttributes tourFileAttributes = new TourFileAttributes(hh_id, person_id, person_num, person_type,
    				 tour_id,  tour_category, tour_purpose, orig_taz, orig_walk_segment,
    				 dest_taz, dest_walk_segment, start_hour, end_hour, tour_mode, 
    				 atWork_freq,  num_ob_stops, num_ib_stops, avAvailable,
    				 tour_composition, tour_participants);
        	
        	//if individual tour, map key is person_id, else it is hh_id
        	long key = -1;
        	if(!isJoint)
        		key = person_id;
        	else
        		key = hh_id;
        	
        	//if the not the first tour for this person or hh, add the tour to the existing
        	//arraylist; else create a new arraylist and add the tour attributes to it,
        	//then add the arraylist to the map
        	if(tourFileAttributesMap.containsKey(key)){
        		ArrayList<TourFileAttributes> tourArray = tourFileAttributesMap.get(key);
        		tourArray.add(tourFileAttributes);
        	}else{
        		ArrayList<TourFileAttributes> tourArray = new ArrayList<TourFileAttributes>();
        		tourArray.add(tourFileAttributes);
        		tourFileAttributesMap.put(key, tourArray);
        	}
        	
        }
        return tourFileAttributesMap;

	}

	/**
	 * Create individual tour objects for all persons in the household object based
	 * on the data read in the individual tour file.
	 *
	 * @param household
	 */
	public void createIndividualTours(Household household){
		
		//HashMap<String,Integer> purposeIndexMap = modelStructure.getPrimaryPurposeNameIndexMap();
		Person[] persons = household.getPersons();
		for(int pnum=1;pnum<persons.length;++pnum){
			Person p = persons[pnum];
			long personId = (long) p.getPersonId();
			if(individualTourAttributesMap.containsKey(personId)){

				// Get an ArrayList of tour attributes for this person
				ArrayList<TourFileAttributes> tourAttributesArray = individualTourAttributesMap.get(personId);
				
				// Create ArrayLists for each type of tour
				ArrayList<TourFileAttributes> workTours = new ArrayList<TourFileAttributes>();
				ArrayList<TourFileAttributes> universityTours = new ArrayList<TourFileAttributes>();
				ArrayList<TourFileAttributes> schoolTours = new ArrayList<TourFileAttributes>();
				ArrayList<TourFileAttributes> atWorkSubtours = new ArrayList<TourFileAttributes>();
				ArrayList<TourFileAttributes> nonMandTours = new ArrayList<TourFileAttributes>();
				
				// Go through ArrayList of tour attributes and add the tour to the ArrayList by type
				for(int i=0;i<tourAttributesArray.size();++i){
					
					TourFileAttributes tourAttributes = tourAttributesArray.get(i);
					if(tourAttributes.tour_purpose.compareTo(modelStructure.WORK_PURPOSE_NAME)==0)
						workTours.add(tourAttributes);
					else if(tourAttributes.tour_purpose.compareTo(modelStructure.SCHOOL_PURPOSE_NAME)==0)
						schoolTours.add(tourAttributes);
					else if(tourAttributes.tour_purpose.compareTo(modelStructure.UNIVERSITY_PURPOSE_NAME)==0)
						universityTours.add(tourAttributes);
					else if(tourAttributes.tour_purpose.compareTo(modelStructure.AT_WORK_PURPOSE_NAME)==0)
						atWorkSubtours.add(tourAttributes);
					else
						nonMandTours.add(tourAttributes);
				}
				
				//Now create tours in the person object for each tour type
				
				//create the mandatory tours
				if(workTours.size()>0){
                    String workPurpose = modelStructure.getWorkPurposeFromIncomeInDollars( household.getIncomeInDollars() );
					p.createWorkTours(workTours.size(), 0, workPurpose,
	                    modelStructure);
					ArrayList<Tour> workTourArrayList = p.getListOfWorkTours();
					for(int i=0;i<workTourArrayList.size();++i){
						Tour workTour = workTourArrayList.get(i);
						TourFileAttributes workTourAttributes = workTours.get(i);
						workTourAttributes.setModeledTourAttributes(workTour);
					}
					
				}
				//create school tours
				if(schoolTours.size()>0){
					p.createSchoolTours(schoolTours.size(), 0, modelStructure.SCHOOL_PURPOSE_NAME,
		                    modelStructure);
					ArrayList<Tour> schoolTourArrayList = p.getListOfSchoolTours();
					for(int i=0;i<schoolTourArrayList.size();++i){
						Tour schoolTour = schoolTourArrayList.get(i);
						TourFileAttributes schoolTourAttributes = schoolTours.get(i);
						schoolTourAttributes.setModeledTourAttributes(schoolTour);
					}
				}
				//create university tours
				if(universityTours.size()>0){
					p.createSchoolTours(universityTours.size(), 0, modelStructure.UNIVERSITY_PURPOSE_NAME,
		                    modelStructure);
					ArrayList<Tour> universityTourArrayList = p.getListOfSchoolTours();
					for(int i=0;i<universityTourArrayList.size();++i){
						Tour universityTour = universityTourArrayList.get(i);
						TourFileAttributes universityTourAttributes = universityTours.get(i);
						universityTourAttributes.setModeledTourAttributes(universityTour);
					}
				}
				//create non-mandatory tours
				if(nonMandTours.size()>0){
					for(int i =0; i<nonMandTours.size(); ++i){
						TourFileAttributes nonMandTourAttributes = nonMandTours.get(i);
						p.createIndividualNonMandatoryTours(1, nonMandTourAttributes.tour_purpose, modelStructure);
					}
					ArrayList<Tour> nonMandTourArrayList = p.getListOfIndividualNonMandatoryTours();
					for(int i =0; i<nonMandTours.size(); ++i){
						TourFileAttributes nonMandTourAttributes = nonMandTours.get(i);
						Tour nonMandTour = nonMandTourArrayList.get(i);
						nonMandTourAttributes.setModeledTourAttributes(nonMandTour);
					}
				}
				//create at-work sub-tours
				for(int i =0; i<atWorkSubtours.size(); ++i){
					TourFileAttributes tourAttributes = atWorkSubtours.get(i);
					//TODO: assuming first work tour is location of this at-work tour; write out actual work location or parent tour ID
					//TODO: assuming purpose is eat out; need to write out actual purpose
					p.createAtWorkSubtour(tourAttributes.tour_id, 0, workTours.get(0).dest_taz,workTours.get(0).dest_walk_segment,modelStructure.AT_WORK_EAT_PURPOSE_NAME, modelStructure);
					
					//set tour attributes
					
				}
			}
		}
		
	}
	
	
	/**
	 * Create joint tours in the household object based on data read in the joint tour file.
	 * 
	 * @param household
	 */
	public void createJointTours(Household household){

		//joint tours
		long hhid = household.getHhId();
		if(jointTourAttributesMap.containsKey(hhid)){
			ArrayList<TourFileAttributes> tourArray = jointTourAttributesMap.get(hhid);
			int numberOfJointTours = tourArray.size();
			
			//get the first joint tour
			TourFileAttributes tourAttributes = tourArray.get(0);
			String purposeString = tourAttributes.tour_purpose;
			int purposeIndex = modelStructure.getDcModelPurposeIndex( purposeString );
		    
			int composition = tourAttributes.tour_composition; 
            byte[] tourParticipants = getTourParticipantsArray(tourAttributes.tour_participants);
            //Household hhObj, ModelStructure modelStructure, int purposeIndex, String tourPurpose, byte tourCategoryIndex ) {
            Tour t1 = new Tour(household, modelStructure, purposeIndex, purposeString,modelStructure.JOINT_NON_MANDATORY_CATEGORY_INDEX);
            t1.setJointTourComposition(composition);
            t1.setPersonNumArray(tourParticipants);
           
            //if the household has two joint tours, get the second
         	if(numberOfJointTours==2){
				tourAttributes = tourArray.get(2);
				purposeString = tourAttributes.tour_purpose;
				purposeIndex = modelStructure.getDcModelPurposeIndex( purposeString );
	            composition = tourAttributes.tour_composition; 
	            tourParticipants = getTourParticipantsArray(tourAttributes.tour_participants);
	            
	            Tour t2 = new Tour(household, modelStructure, purposeIndex, purposeString,modelStructure.JOINT_NON_MANDATORY_CATEGORY_INDEX);
	            t2.setJointTourComposition(composition);
				t2.setPersonNumArray(tourParticipants);
				
				//set in hh object
				household.createJointTourArray(t1, t2);
	            tourAttributes.setModeledTourAttributes(t1);
	            tourAttributes.setModeledTourAttributes(t2);
		    }else{
				household.createJointTourArray(t1);
	            tourAttributes.setModeledTourAttributes(t1);
			}
		}
		
		
	}
	
// HELPER METHODS AND CLASSES
	
	/**
	 * Split the participants string around spaces and return the 
	 * integer array of participant numbers.
	 * 
	 * @param tourParticipants
	 * @return
	 */
	public byte[] getTourParticipantsArray(String tourParticipants){
		
		String[] values = tourParticipants.split(" ");
	    byte[] array = new byte[values.length];
	    for (int i = 0; i < array.length; i++)
	       	array[i] = Byte.parseByte(values[i]);
	    return array;
	}
	
	/**
	 * Set household and person attributes for this household object. This method uses
	 * the data in the personFileAttributesMap to set the data members of the
	 * Person objects for all persons in the household.
	 * 
	 * @param hhObject
	 */
	public void setHouseholdAndPersonAttributes(Household hhObject){
		
		long hhid = (long) hhObject.getHhId();
		HouseholdFileAttributes hhAttributes = householdFileAttributesMap.get(hhid);
		hhAttributes.setHouseholdAttributes(hhObject);
		Person[] persons = hhObject.getPersons();
		for(int i=1;i<persons.length;++i){
			Person p = persons[i];
			long person_id = (long) p.getPersonId();
			if(!personFileAttributesMap.containsKey(person_id)){
				logger.error("Error: personFileAttributes map does not contain person_id "+person_id+" in household "+hhid);
				throw new RuntimeException();
			}
			PersonFileAttributes personFileAttributes = personFileAttributesMap.get(person_id);
			personFileAttributes.setPersonAttributes(p);
		}
	}
	
	/**
	 * A class to hold a household file record attributes.
	 * @author joel.freedman
	 *
	 */
	public class HouseholdFileAttributes{
		
		long hhid;
        int taz;
        int walk_subzone;
        int income;
        int autos;
        int size;
        int workers;
        int automated_vehicles;
        int human_vehicles;
        String cdap_pattern;
        String jtf_pattern;
        
        
       
        public HouseholdFileAttributes(long hhid, int taz, int walk_subzone,
        		int income, int autos, int size, int workers, int automated_vehicles, int human_vehicles, 
        		String cdap_pattern, String jtf_pattern){
        	
    		this.hhid = hhid;
            this.taz = taz;
            this.walk_subzone = walk_subzone;
            this.income = income;
            this.autos = autos;
            this.size = size;
            this.workers = workers;
            this.automated_vehicles = automated_vehicles;
            this.human_vehicles = human_vehicles;
            this.cdap_pattern = cdap_pattern;
            this.jtf_pattern = jtf_pattern;
         }
        
        public void setHouseholdAttributes(Household hh){
        	
        	hh.setHhTaz((short) taz);
        	hh.setHhWalkSubzone(walk_subzone);
        	hh.setHhIncomeInDollars(income);
        	hh.setHhAutos(autos);
        	hh.setHhWorkers(workers);
        	hh.setAutonomousVehicles((short)automated_vehicles);
        	hh.setHumanVehicles((short) human_vehicles);
        	hh.setCoordinatedDailyActivityPatternResult(cdap_pattern);
        	String[] jtf = jtf_pattern.split("_");
        	int jtfAlt = new Integer(jtf[0]);
        	hh.setJointTourFreqResult(jtfAlt, jtf[1]);
         }
	}
	
	
	
	/**
	 * A class to hold person file attributes (read in from Results.PersonDataFile)
	 * @author joel.freedman
	 *
	 */
	public class PersonFileAttributes{
       
		long hhid;
    	long person_id;
    	long personNumber;
    	int age;
    	int gender;
    	float valueOfTime;
    	String activityPattern;
    	int personType;
    	int imfChoice;
    	int inmfChoice;
    	
		public PersonFileAttributes(long hhid, long person_id, long personNumber, int age, int gender,float valueOfTime, 
				String activityPattern,int personType,
				int imfChoice,int inmfChoice){
			
			this.hhid=hhid;
			this.person_id = person_id;
			this.personNumber=personNumber;
			this.age=age;
			this.gender=gender;
			this.valueOfTime=valueOfTime;
			this.activityPattern=activityPattern;
			this.personType=personType;
			this.imfChoice=imfChoice;
			this.inmfChoice=inmfChoice;
		
		}
		
		
		public void setPersonAttributes(Person p){
			
			p.setPersAge(age);
			p.setPersGender(gender);
			p.setValueOfTime(valueOfTime);
			p.setDailyActivityResult(activityPattern);
			p.setPersonTypeCategory(personType);
			p.setImtfChoice(imfChoice);
			p.setInmtfChoice(inmfChoice);
				
		}
	}
	
	public class TourFileAttributes{
		
		long hh_id;
		long person_id;
		int person_num;
		int person_type;
		int tour_id;
		String tour_category;
		String tour_purpose;
		int orig_taz;
		int orig_walk_segment;
		int dest_taz;
		int dest_walk_segment;
		int start_hour;
		int end_hour;
		int tour_mode;
		int atWork_freq;
		int num_ob_stops;
		int num_ib_stops;
		int avAvailable;
		
		//for joint tours
		int tour_composition;
		String tour_participants;

		public TourFileAttributes(long hh_id, long person_id, int person_num, int person_type,
				int tour_id, String tour_category,String tour_purpose, int orig_taz, int orig_walk_segment,
				int dest_taz, int dest_walk_segment,
				int start_hour,int end_hour,int tour_mode, 
				int atWork_freq, int num_ob_stops,int num_ib_stops,int avAvailable,
				int tour_composition,String tour_participants){
			
			
			this.hh_id = hh_id;
			this.person_id = person_id;
			this.person_num = person_num;
			this.person_type = person_type;
			this.tour_id = tour_id;
			this.tour_category = tour_category;
			this.tour_purpose = tour_purpose;
			this.orig_taz = orig_taz;
			this.orig_walk_segment = orig_walk_segment;
			this.dest_taz = dest_taz;
			this.dest_walk_segment = dest_walk_segment;
			this.start_hour = start_hour;
			this.end_hour = end_hour;
			this.tour_mode = tour_mode;
			this.atWork_freq = atWork_freq;
			this.num_ob_stops = num_ob_stops;
			this.num_ib_stops = num_ib_stops;
			this.avAvailable = avAvailable;
			this.tour_composition = tour_composition;
			this.tour_participants = tour_participants;
						
		}
		
		/**
		 * Set the tour attributes up through tour destination
		 * and time-of-day choice. Tour mode choice is not
		 * known (requires running tour mode choice).
		 * 
		 * @param tour
		 */
		public void setModeledTourAttributes(Tour tour){
			
			tour.setTourOrigTaz(orig_taz);
			tour.setTourOrigWalkSubzone(orig_walk_segment);
			tour.setTourDestTaz(dest_taz);
			tour.setTourDestWalkSubzone(dest_walk_segment);
			tour.setTourStartHour(start_hour);
			tour.setTourEndHour(end_hour);
			tour.setSubtourFreqChoice(atWork_freq);
			tour.setUseOwnedAV(avAvailable==1 ? true : false);
		}

		
	}
	
	
	
	/**
	 * Calculate person type value based on string.
	 * @param personTypeString
	 * @return
	 */
	private int getPersonType(String personTypeString){
		
		for(int i =0;i<Person.personTypeNameArray.length;++i){
			
			if(personTypeString.compareTo(Person.personTypeNameArray[i])==0)
				return i+1;
			
		}
	   
		logger.error("Error: Cannot find person type "+personTypeString+" in person type array");
		throw new RuntimeException();
		
	}

	
	
	/**
	 * Read data into inputDataTable tabledataset.
	 * 
	 */
	private TableDataSet readTableData(String inputFile){
		
		TableDataSet tableDataSet = null;
		
		logger.info("Begin reading the data in file " + inputFile);
	    
	    try
	    {
	    	OLD_CSVFileReader csvFile = new OLD_CSVFileReader();
	    	tableDataSet = csvFile.readFile(new File(inputFile));
	    } catch (IOException e)
	    {
	    	throw new RuntimeException(e);
        }
        logger.info("End reading the data in file " + inputFile);
        
        return tableDataSet;
	}
	/**
	 * Create a file name with the iteration number appended.
	 * 
	 * @param originalFileName The original file name	
	 * @param iteration The iteration number
	 * @return The reformed file name with the iteration number appended.
	 */
    private String formFileName(String originalFileName, int iteration)
    {
        int lastDot = originalFileName.lastIndexOf('.');

        String returnString = "";
        if (lastDot > 0)
        {
            String base = originalFileName.substring(0, lastDot);
            String ext = originalFileName.substring(lastDot);
            returnString = String.format("%s_%d%s", base, iteration, ext);
        } else
        {
            returnString = String.format("%s_%d.csv", originalFileName, iteration);
        }

        logger.info("writing " + originalFileName + " file to " + returnString);

        return returnString;
    }

	public HashMap<Long, HouseholdFileAttributes> getHouseholdFileAttributesMap() {
		return householdFileAttributesMap;
	}

	public HashMap<Long, PersonFileAttributes> getPersonFileAttributesMap() {
		return personFileAttributesMap;
	}

	public HashMap<Long, ArrayList<TourFileAttributes>> getIndividualTourAttributesMap() {
		return individualTourAttributesMap;
	}

	public HashMap<Long, ArrayList<TourFileAttributes>> getJointTourAttributesMap() {
		return jointTourAttributesMap;
	}

	public boolean hasIndividualTourFile() {
		return readIndividualTourFile;
	}

	public boolean hasJointTourFile() {
		return readJointTourFile;
	}
 


}
