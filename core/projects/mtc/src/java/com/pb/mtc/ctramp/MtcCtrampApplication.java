 package com.pb.mtc.ctramp;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.ResourceBundle;

import org.apache.log4j.Logger;

import com.pb.common.util.ResourceUtil;
import com.pb.models.ctramp.HouseholdDataManagerIf;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.StopFrequencyDMU;
import com.pb.models.ctramp.Tour;
import com.pb.models.ctramp.jppf.CtrampApplication;


public class MtcCtrampApplication extends CtrampApplication{

     public static Logger logger = Logger.getLogger(MtcCtrampApplication.class);

     public static final String PROGRAM_VERSION = "09June2008";
     public static final String PROPERTIES_PROJECT_DIRECTORY = "Project.Directory";



     public MtcCtrampApplication( ResourceBundle rb ){
         super( rb );

         projectDirectory = ResourceUtil.getProperty(rb, PROPERTIES_PROJECT_DIRECTORY);

     }

     /**
      * override method
      * Logs the results of the individual tour stop frequency model.
      *
      */
     public void logStfResults( HouseholdDataManagerIf householdDataManager, Boolean isIndividual){
         if(isIndividual)
             logIndivStfResults( householdDataManager );
     }     
     
     private void logIndivStfResults( HouseholdDataManagerIf householdDataManager ){
         
         logger.info(" ");
         logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
         logger.info("Individual Tour Stop Frequency Model Results");
         
         // count of model results
         logger.info(" ");
         String firstHeader  = "Tour Purpose     ";
         String secondHeader = "---------------   ";
         
         int[] obStopsAlt = StopFrequencyDMU.NUM_OB_STOPS_FOR_ALT;
         int[] ibStopsAlt = StopFrequencyDMU.NUM_IB_STOPS_FOR_ALT;
         
         // 17 purposes
         int[][] chosen = new int[obStopsAlt.length][18];
         HashMap<Integer, String> indexPurposeMap = new HashMap<Integer, String>();
         HashMap<String, Integer> purposeIndexMap = new HashMap<String, Integer>();
         indexPurposeMap.put( 1, "work_low" );
         purposeIndexMap.put( "work_low", 1 );
         indexPurposeMap.put( 2, "work_med" );
         purposeIndexMap.put( "work_med", 2 );
         indexPurposeMap.put( 3, "work_high" );
         purposeIndexMap.put( "work_high", 3 );
         indexPurposeMap.put( 4, "work_very high" );
         purposeIndexMap.put( "work_very high", 4 );
         indexPurposeMap.put( 5, "university" );
         purposeIndexMap.put( "university", 5 );
         indexPurposeMap.put( 6, "school_high" );
         purposeIndexMap.put( "school_high", 6 );
         indexPurposeMap.put( 7, "school_grade" );
         purposeIndexMap.put( "school_grade", 7 );
         indexPurposeMap.put( 8, "escort_kids" );
         purposeIndexMap.put( "escort_kids", 8 );
         indexPurposeMap.put( 9, "escort_no kids" );
         purposeIndexMap.put( "escort_no kids", 9 );
         indexPurposeMap.put( 10, "shopping" );
         purposeIndexMap.put( "shopping", 10 );
         indexPurposeMap.put( 11, "othmaint" );
         purposeIndexMap.put( "othmaint", 11 );
         indexPurposeMap.put( 12, "eatout" );
         purposeIndexMap.put( "eatout", 12 );
         indexPurposeMap.put( 13, "othdiscr" );
         purposeIndexMap.put( "othdiscr", 13 );
         indexPurposeMap.put( 14, "social" );
         purposeIndexMap.put( "social", 14 );
         indexPurposeMap.put( 15, "atwork_business" );
         purposeIndexMap.put( "atwork_business", 15 );
         indexPurposeMap.put( 16, "atwork_eat" );
         purposeIndexMap.put( "atwork_eat", 16 );
         indexPurposeMap.put( 17, "atwork_maint" );
         purposeIndexMap.put( "atwork_maint", 17 );
         
         ArrayList<int[]> startEndTaskIndicesList = getWriteHouseholdRanges( householdDataManager.getNumHouseholds() );

         for ( int[] startEndIndices : startEndTaskIndicesList ) {
         
             int startIndex = startEndIndices[0];
             int endIndex = startEndIndices[1];

         
             // get the array of households
             Household[] householdArray = householdDataManager.getHhArray( startIndex, endIndex );
    
             for(int i=0; i < householdArray.length; ++i){
    
                 Person[] personArray = householdArray[i].getPersons();
                 for(int j=1; j < personArray.length; j++){
                 
                     List<Tour> tourList = new ArrayList<Tour>();
                     
                     // apply stop frequency for all person tours
                     tourList.addAll( personArray[j].getListOfWorkTours() );
                     tourList.addAll( personArray[j].getListOfSchoolTours() );
                     tourList.addAll( personArray[j].getListOfIndividualNonMandatoryTours() );
                     tourList.addAll( personArray[j].getListOfAtWorkSubtours() );

                     for ( Tour t : tourList ) {
                         
                         int index = purposeIndexMap.get( t.getTourPurpose().toLowerCase() );
                         int choice = t.getStopFreqChoice();
                         chosen[choice][index]++;
                         
                     }
                     
                 }    
    
             }
    
    
         }
         
         
         
         for(int i=1;i<chosen[1].length;++i){
             firstHeader  += String.format("%18s", indexPurposeMap.get(i) );
             secondHeader += "  --------------- ";
         }
         
         firstHeader  += String.format("%18s","Total");
         secondHeader += "  --------------- ";

         logger.info(firstHeader);
         logger.info(secondHeader);

         int[] columnTotals = new int[chosen[1].length];


         int lineTotal = 0;
         for(int i=1;i<chosen.length;++i){
             String stringToLog  = String.format("%d out, %d in      ", obStopsAlt[i], ibStopsAlt[i] );

             lineTotal = 0;
             int[] countArray = chosen[i];
             for(int j=1;j<countArray.length;++j){
                 stringToLog += String.format("%18d",countArray[j]);
                 columnTotals[j] += countArray[j];
                 lineTotal += countArray[j];
             } // j

             stringToLog += String.format("%18d",lineTotal);

             logger.info(stringToLog);
             
         } // i
         
         String stringToLog  = String.format("%-17s", "Total");
         lineTotal = 0;
         for(int j=1;j<chosen[1].length;++j){
             stringToLog += String.format("%18d",columnTotals[j]);
             lineTotal += columnTotals[j];
         } // j

         logger.info(secondHeader);
         stringToLog += String.format("%18d",lineTotal);
         logger.info(stringToLog);
         logger.info(" ");
         logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
         logger.info(" ");
         logger.info(" ");

     }

     
 }