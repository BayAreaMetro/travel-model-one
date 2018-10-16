/* Copyright  2005 PB Americas, Inc.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 */
package com.pb.common.summit;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Iterator;
import java.util.Set;
import java.util.TreeMap;

import org.apache.log4j.Logger;


public class SummitRecordTable {

	protected double expUtilityScaler=1.0;
    TreeMap<Long, ArrayList<ConcreteSummitRecord>> recordMap = null;
    TreeMap<Long, ConcreteSummitRecord> aggregateMap = null;
    boolean finalized = false;
    protected static Logger logger = Logger.getLogger("com.pb.summit");
   
     /**
     * Default constructor.
     * 
     */
    public SummitRecordTable(){
    	
    	recordMap = new TreeMap<Long, ArrayList<ConcreteSummitRecord>>();
    	aggregateMap = new TreeMap<Long, ConcreteSummitRecord>();
   	
    }
 
    /**
     * Write the records in the table to a file.
     * 
     * @param fileName The path/name of the SUMMIT file.
     * @param header   A header record.
     */
    public void writeTable(String fileName, SummitHeader header){
    	
    	if(!finalized){
    		logger.fatal("Error: Writing SUMMIT table before finalization!");
    		throw new RuntimeException("Error: Writing SUMMIT table before finalization!");
    	}
       SummitFileWriter sf = new SummitFileWriter();
        
        try{
            sf.openFile(fileName);
            sf.writeHeader(header);
            
            Set<Long> set = aggregateMap.keySet();
            Iterator i = set.iterator();
            while(i.hasNext()){
                       
            	ConcreteSummitRecord r = aggregateMap.get(i.next());
                sf.writeRecord(r);
                
            }
        } catch(IOException e){
            logger.error("Error trying to write to Summit file "+fileName);
        }

    }
    
    /**
     * Insert a record into the record table.
     * 
     * @param record  The record to insert.
     */
    public void insertRecord(ConcreteSummitRecord record){
    	
    	// scale the record shares by trips
    	scaleByTrips(record);
     	
    	//check if there is already a record in the table for this origin, destination, market segment
        if ( recordMap.containsKey( record.getKey() ) ){
        	ArrayList<ConcreteSummitRecord> recordArray = recordMap.get( record.getKey() );
        	recordArray.add(record);
         }else{
        	 ArrayList<ConcreteSummitRecord> recordArray = new ArrayList<ConcreteSummitRecord>();
         	 recordArray.add(record);
             recordMap.put(record.getKey(), recordArray);
         }
    }
    
    
    /**
     * Scale the transit shares and availabilities by the number of trips per record.
     * This is important for tours in which there are multiple participants, where the 
     * number of trips per record is greater than 1.0, because when the table of records is 
     * finalized, the shares will be divided by the number of trips.
     * 
     * @param record  The record to scale.
     */
    public void scaleByTrips(ConcreteSummitRecord record){
    	
       	//scale shares by trips
    	float trips = record.getTrips();
    	
    	if(trips==1.0)
    		return;
    	
    	float wtAvail = record.getWalkTransitAvailableShare();
    	float dtAvail = record.getDriveTransitOnlyShare();
    	float wtShare = record.getTransitShareOfWalkTransit();
    	float dtShare = record.getTransitShareOfDriveTransitOnly();
    	record.setWalkTransitAvailableShare(trips*wtAvail);
    	record.setDriveTransitOnlyShare(trips*dtAvail);
    	record.setTransitShareOfWalkTransit(trips*wtShare);
    	record.setTransitShareOfDriveTransitOnly(trips*dtShare);
    }
    
    
    /**
     * Aggregate the values for a set of summit records.  Divide shares and probabilities by trips, and calculate the
     * exponentiated auto utility according to the following formula:
     * 
     * {1-P(WT)-P(DT)}*{(Exp(LS1)**w1)(Exp(LS2)**w2)...(Exp(LSn)**wn)}**(1.0/W)
     * 
     * Where:
     * 
     * PT(WT) is the walk-transit probability
     * PT(DT) is the drive-only transit probability
     * LS1...n is the logsum for the nth record for the given origin, destination, and market
     * w1...n is the weight for the logsum, equal to number of trips/scaler.
     * W is the total number of trips   
     * 
     * @param recordList  An ArrayList of ConcreteSummitRecords to aggregate
     * @return A single ConcreteSummitRecord for all records in ArrayList.
     */
    public ConcreteSummitRecord aggregate(ArrayList<ConcreteSummitRecord> recordList){
    	
    	ConcreteSummitRecord newRecord = new ConcreteSummitRecord();
    	
    	int records = recordList.size();
    	
    	short ptaz = 0;
    	short ataz = 0;
    	short market = 0;
    	float trips = 0;
    	float motorTrips = 0;
    	float wtAvailShare = 0;
    	float dtAvailShare = 0;
    	float wtProb = 0;
    	float dtProb = 0;
 
    	//calculate total trips and other key variables
    	for(int i = 0; i< records; ++i){
    		
    		ConcreteSummitRecord record = recordList.get(i);
    		
    		if(i==0){
    			ptaz = record.getPtaz();
    			ataz = record.getAtaz();
    			market = record.getMarket();
    			
    		}
    		
            // aggregate values
        	trips += record.getTrips();
        	motorTrips += record.getMotorizedTrips();
        	wtAvailShare += record.getWalkTransitAvailableShare();
        	dtAvailShare += record.getDriveTransitOnlyShare();
        	wtProb += record.getTransitShareOfWalkTransit();
        	dtProb += record.getTransitShareOfDriveTransitOnly();
    	}
    	
    	//scale by trips
    	wtProb = wtProb/trips;
    	dtProb = dtProb/trips;
    	wtAvailShare = wtAvailShare/trips;
    	dtAvailShare = dtAvailShare/trips;

    	//calculate exponential utility
    	float product = 1.0f;
    	for(int i = 0; i < records; ++i){
    		ConcreteSummitRecord record = recordList.get(i);
    		float scaledLogsum = (float) Math.pow(record.getExpAuto(),record.getTrips()/trips);
    		product *= scaledLogsum;
    	}
        
    	float expAuto = (float) (1.0 - wtProb - dtProb ) * product ;

    	// set values
    	newRecord.setPtaz(ptaz);
    	newRecord.setAtaz(ataz);
    	newRecord.setMarket(market);
    	newRecord.setTrips( trips );
        newRecord.setMotorizedTrips( motorTrips  );
        newRecord.setExpAuto( expAuto  );
        newRecord.setWalkTransitAvailableShare(wtAvailShare);
        newRecord.setDriveTransitOnlyShare(dtAvailShare);
        newRecord.setTransitShareOfWalkTransit(wtProb);
        newRecord.setTransitShareOfDriveTransitOnly(dtProb);
        
        // return record
    	return newRecord;
    	
    }
    
    /**
     * Finalize the table of records by iterating through the recordMap, aggregating
     * the records for each ptaz, ataz, and market using the aggregate() method, and
     * storing the aggregate ConcreteSummitRecord in the aggregateMap.
     * 
     */
    public void finalizeTable(){
    	
        //get Collection of values contained in recordMap     
        Collection<ArrayList<ConcreteSummitRecord>> c = recordMap.values();     
        Iterator<ArrayList<ConcreteSummitRecord>> itr = c.iterator();     
         
         //iterate through recordMap, aggregate all records in each arraylist and put the new record in the aggregate map. 
         while(itr.hasNext()){
        	 ArrayList<ConcreteSummitRecord> recordList =  itr.next();
        	 ConcreteSummitRecord aggregateRecord = aggregate(recordList);
        	 long key = aggregateRecord.getKey();
        	 aggregateMap.put(key, aggregateRecord);
 
          }
         finalized = true;
    }
 
}
