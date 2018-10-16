/*
 * Copyright  2005 PB Consult Inc.
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

import java.io.EOFException;
import java.io.File;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;
import java.io.IOException;
import org.apache.log4j.Logger;

/**
 * @author tad
 *
 * (c) 2004 San Francisco County Transportation Authority.
 */
/**
 * This reader only works sequentially. Random-access reading is still TO-DO.
 * Usage: You can use readRecord sequentially, to retrieve the stream of
 * i-j-s records in the order they were written.  Or, you can use getSpecificRecord
 * to pull the exact i,j,s record you want.  To use getSpecificRecord, you MUST 
 * ask for the records in incremental order, or it will bail. 
 * 
 * @author Charlton
 */
public class SummitFileReader {

    static final int RECORD_IS_CORRECT = 0;
    static final int RECORD_IS_NEEDED = 1;
    static final int RECORD_NOT_IN_FILE = 2;
    
    protected static Logger logger = Logger.getLogger("com.pb.common.util");
    protected RandomAccessFile file;
    protected FileChannel fc;
    protected long records = 0;
    protected int recordSize = 34;
    protected short curPtaz = -1;
    protected short curAtaz = -1;
    protected short curMarket = -1;
    protected SummitRecord curRecord = null;
    
    /**
     * Default constructor
     */
    public SummitFileReader(){
    }
    
    /**
     * Constructor also opens the file for reading/writing.
     * 
     *@param fileName The path and name of the file to open
     */
    public SummitFileReader(String fileName){
        
        try{
            this.openFile(fileName);
        }
        catch(IOException e){
            logger.error("Error trying to open SummitFile "+fileName);
            System.exit(1);
        }         
    }
   
    /**
     * Open a Summit File for reading/writing
     * 
     *@param fileName The path and name of the file to open
     * 
     */
    public void openFile(String fileName) throws IOException{
        
        String mode = "r"; // read-only
        logger.debug( "Opening SUMMIT input file: " + fileName );
        
        
        try {
            File f = new File(fileName);
                
            //create a random access file
            this.file = new RandomAccessFile( f, mode );
            this.fc = file.getChannel();
        }
        catch (IOException e) {
            logger.error( "Error opening: " + fileName );
            throw e;
        }
    }
    
    /**
     * Read the header from the SUMMIT input file
     *
     *@return A summit header record object
     */
    public SummitHeader getHeader() throws IOException{

        SummitHeader header = new SummitHeader();

        //Allocate a byte buffer to hold one row
        ByteBuffer byteBuffer = ByteBuffer.allocate((int)88);
        byteBuffer.order(ByteOrder.nativeOrder());

        //now read data file
        try{
            file.read( byteBuffer.array() );
        }
        catch(IOException e){
            logger.error("Couldn't read header from summit file");
            throw e;
        }

        //fill it up with data from the header

        header.setZones(byteBuffer.getInt());
        header.setMarketSegments(byteBuffer.getInt());
        header.setTransitInVehicleTime(byteBuffer.getFloat());
        header.setAutoInVehicleTime(byteBuffer.getFloat());
        
        // the following is just to get the lengths of the fields:
        StringBuffer purpose = header.getPurpose();
        StringBuffer timeOfDay = header.getTimeOfDay();
        StringBuffer title = header.getTitle();
        
        // now actually populate the fields
        for(int i=0;i<purpose.length(); ++i)
            purpose.setCharAt(i,(char)byteBuffer.get());
        for(int i=0;i<timeOfDay.length(); ++i)
            timeOfDay.setCharAt(i,(char)byteBuffer.get());
        for(int i=0; i<title.length(); ++i)
            title.setCharAt(i,(char)byteBuffer.get());

        header.setPurpose(purpose.toString());
        header.setTimeOfDay(timeOfDay.toString());
        header.setTitle(title.toString());
        
        return header;
    }


    /**
     * Get a specific i,j,s record.  
     * @param i origin/production zone number 
     * @param j destination/attraction zone number
     * @param s market segment
     * @return full summit record if this i,j,s triplet exists in this file,
     * or null if it does not 
     */
    public SummitRecord getSpecificRecord(int i, int j, int s) throws IOException {
        // if incoming i,j,s are greater than current i,j,s then read the next record
        // if incoming i,j,s are less than the current i,j,s then return null
        // if incoming i,j,s are equal to current i,j,s then return the current record

        SummitRecord rec = null;

        switch (compareRequestedRecord(i,j,s)) {

        	case RECORD_IS_CORRECT:
        	    // Found it!
        	    rec = curRecord;
        	    break;

        	case RECORD_IS_NEEDED:
        	    // Need to get the next record from the file.  Store it
        	    // as the new current record, then compare again.
        	    // Don't do a recursive call because we should never have
        	    // to read more than one record at a time.
        	    curRecord = readRecord();
        	    if (compareRequestedRecord(i,j,s)==RECORD_IS_CORRECT)
        	        rec = curRecord;
        	    else
        	        rec = null;
        	    break;
        	    
        	case RECORD_NOT_IN_FILE:
        	    // This i,j,s pair is not in the file.
        	    rec = null;
        	    break;
        }
        
        return rec;
    }

    /**
     * Compare the requested i,j,s to the current i,j,s from file.
     * @param i
     * @param j
     * @param s
     * @return
     */
    int compareRequestedRecord(int i, int j, int s) {

        if (i == curPtaz) {
            if (j == curAtaz) {
                if (s == curMarket) {
                    return RECORD_IS_CORRECT;
                }
                return ( s < curMarket ? RECORD_NOT_IN_FILE : RECORD_IS_NEEDED);
            }
            return ( j < curAtaz ? RECORD_NOT_IN_FILE : RECORD_IS_NEEDED);
        }
        return ( i < curPtaz ? RECORD_NOT_IN_FILE : RECORD_IS_NEEDED);
    }

    /**
     * Read a SUMMIT input file record.
     * 
     * @return A summit input file record object.
     */
    public SummitRecord readRecord() throws EOFException {

        SummitRecord record = new ConcreteSummitRecord();

        ByteBuffer rBuffer = ByteBuffer.allocate(recordSize);
        rBuffer.order(ByteOrder.nativeOrder());
        int bytesRead = recordSize;

        //read data from file
        try{
            bytesRead = file.read( rBuffer.array() );
            ++records;
            
        } catch(IOException e){
        	if(bytesRead == -1) throw new EOFException(); //EOF has been reached.  Calling method will handle
        	throw new RuntimeException("Couldn't read record from summit file "+file, e); //something other than EOF happened
        }
        
        //have to check for this outside catch block since the previous record read may not have thrown an EOFException
        if(bytesRead == -1) throw new EOFException(); //EOF has been reached.  Calling method will handle
       
        //fill up with data
        record.setPtaz(rBuffer.getShort());
        record.setAtaz(rBuffer.getShort());
        record.setMarket(rBuffer.getShort());
        record.setTrips(rBuffer.getFloat());
        record.setMotorizedTrips(rBuffer.getFloat());
        record.setExpAuto(rBuffer.getFloat());
        record.setWalkTransitAvailableShare(rBuffer.getFloat());
        record.setTransitShareOfWalkTransit(rBuffer.getFloat());
        record.setDriveTransitOnlyShare(rBuffer.getFloat());
        record.setTransitShareOfDriveTransitOnly(rBuffer.getFloat());

        this.curPtaz = record.getPtaz();
        this.curAtaz = record.getAtaz();
        this.curMarket = record.getMarket();
        
        return record;
    }

    /**
     * Test code
     */
    public static void main(String[] args) {
        logger.info("Testing SummitFileReader");

        SummitFileReader sf = new SummitFileReader();
               
        try{
            sf.openFile(args[0]);

            SummitHeader header = sf.getHeader();
            
            int zones = header.getZones();
            int segments = header.getMarketSegments();
            float tivt = header.getTransitInVehicleTime();
            float aivt = header.getAutoInVehicleTime();
            StringBuffer purp = header.getPurpose();
            StringBuffer tod = header.getTimeOfDay();
            StringBuffer title = header.getTitle();
            
            logger.info("Zones: "+zones+"  Segments: "+segments+
            "\nTivt: "+tivt+"  Aivt: "+aivt+
            "\nPurpose: "+purp+
            "\nTime Of Day: "+tod+
            "\nTitle: "+title);
            
            while (true) {
                SummitRecord r = sf.readRecord();
                
				logger.info("-------------\nP:"+r.getPtaz()+" A:"+r.getAtaz()+" Mkt:"+r.getMarket()+
				        "\nExpAuto: "+r.getExpAuto()+"\tTrips: "+r.getTrips()+"\tMotorizedTrips: "+
					r.getMotorizedTrips()+
					"\nWlk-Trn-Avail-Share: "+r.getWalkTransitAvailableShare()+
					"\tTrn-Share-Wlk-Transit: "+r.getTransitShareOfWalkTransit()+
					"\nDrv-Trn-Only-Share: "+r.getDriveTransitOnlyShare()+
					"\tTrn-Share-Drv-Transit: "+r.getTransitShareOfDriveTransitOnly());
            }
             
        }
        catch(IOException e){
            logger.error("Error trying to test Summit java code");
        }
        
        logger.info("Success writing "+sf.getRecords()+" records of size "+sf.getRecordSize());                
        }

    /**
     * Returns the number of records written.
     * @return long
     */
    public long getRecords() {
        return records;
    }


    /**
     * Returns the recordSize.
     * @return int
     */
    public int getRecordSize() {
        return recordSize;
    }

}
