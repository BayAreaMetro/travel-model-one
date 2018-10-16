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

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;
import java.io.IOException;
import org.apache.log4j.Logger;

/**
 * @author Freedman
 *
 */
public class SummitFileWriter {

    protected static Logger logger = Logger.getLogger("com.pb.common.util");
    protected RandomAccessFile file;
    protected FileChannel fc;
    protected long records;
    protected int recordSize;
    
    private String correspFileName;
    
    /**
     * Default constructor
     */
    public SummitFileWriter(){
    }
    
    /**
     * Constructor also opens the file for reading/writing.
     * 
     *@param fileName The path and name of the file to open
     */
    public SummitFileWriter(String fileName){
        
        try{
            this.openFile(fileName);
            
            int charIndex = fileName.indexOf('.');
            correspFileName = fileName.substring(0,charIndex) + ".corresp";
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
        
        String mode = "rw";
        
        logger.debug( "Opening SUMMIT input file: " + fileName );
        
        
        try {
            //delete the file if it already exists
            File f = new File(fileName);
            if(f.exists())
                f.delete();
                
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
     * Write the header to the SUMMIT input file
     *
     *@param header  A summit header record object
     */
    public void writeHeader(SummitHeader header) throws IOException{
        
        //Allocate a byte buffer to hold one row
//        ByteBuffer byteBuffer = ByteBuffer.allocate((int)ObjectUtil.sizeOf(header));
        ByteBuffer byteBuffer = ByteBuffer.allocate((int)88);
        byteBuffer.order(ByteOrder.nativeOrder());
        
        //fill it up with data from the header
        byteBuffer.putInt( header.getZones() );
        byteBuffer.putInt( header.getMarketSegments() );
        byteBuffer.putFloat( header.getTransitInVehicleTime() );
        byteBuffer.putFloat( header.getAutoInVehicleTime() );
        
        StringBuffer purpose = header.getPurpose();
        StringBuffer timeOfDay = header.getTimeOfDay();
        StringBuffer title = header.getTitle();
        
        for(int i=0;i<purpose.length();++i)
            byteBuffer.put((byte)purpose.charAt(i));
        for(int i=0;i<timeOfDay.length();++i)
            byteBuffer.put((byte)timeOfDay.charAt(i));
        for(int i=0;i<title.length();++i)
            byteBuffer.put((byte)title.charAt(i));
      
        //now write data to file
        try{
            file.write( byteBuffer.array() );
        }
        catch(IOException e){
            logger.error("Couldn't write header to summit file");
            throw e;
        }
    }


    /**
     * Write a SUMMIT input file record.
     * 
     * @param record A summit input file record object.
     */
    public void writeRecord(SummitRecord record) throws IOException{
        
        //Allocate a byte buffer to hold one row
        if(recordSize==0)
            recordSize=34;
//            recordSize=(int)ObjectUtil.sizeOf(record);
        
        
        ByteBuffer byteBuffer = ByteBuffer.allocate(recordSize);
        byteBuffer.order(ByteOrder.nativeOrder());
        
        //fill it up with data from the header
        byteBuffer.putShort( record.getPtaz() );
        byteBuffer.putShort( record.getAtaz() );
        byteBuffer.putShort( record.getMarket() );
        byteBuffer.putFloat( record.getTrips() );
        byteBuffer.putFloat( record.getMotorizedTrips() );
        byteBuffer.putFloat( record.getExpAuto() );
        byteBuffer.putFloat( record.getWalkTransitAvailableShare() );
        byteBuffer.putFloat( record.getTransitShareOfWalkTransit() );
        byteBuffer.putFloat( record.getDriveTransitOnlyShare() );
        byteBuffer.putFloat( record.getTransitShareOfDriveTransitOnly());
      
        //now write data to file
        try{
            file.write( byteBuffer.array() );
            ++records;
        }
        catch(IOException e){
            logger.error("Couldn't write record to summit file");
            throw e;
        }
    }

    /**
     * write taz correspondence file.  Userben file record ptaz and ataz are sequential numbers, 1,...,numTazs.
     * correspondence file lists the model taz number corresponding to 1,...,numTazs.
     */
    public void writeCorrespFile( int[] modelTazs ) {
        
        PrintWriter out = null;
        try {
            out = new PrintWriter( new BufferedWriter( new FileWriter( new File( correspFileName ) ) ) );
        }
        catch (IOException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }
                
        // write header record for correspondence file
        out.println( "index,modelTaz" );
        
        for ( int i=1; i < modelTazs.length; i++ )
            out.println( i + "," + modelTazs[i] );
        
        out.close();
        
    }
    
    
    /**
     * Test code
     */
    public static void main(String[] args) {
        
        logger.info("Testing SummitFileWriter");
        
        SummitHeader header = new SummitHeader();
        header.setZones(100);
        header.setMarketSegments(5);
        header.setTransitInVehicleTime((float)-0.025);
        header.setAutoInVehicleTime((float)-0.025);
        header.setPurpose("HBW");
        header.setTimeOfDay("PEAK");
        header.setTitle("Test of the SUMMIT java code");
        
        SummitFileWriter sf = new SummitFileWriter();
        
        try{
            sf.openFile("d:\\projects\\sandag\\ab_model\\summit\\summitFile.dat");
            sf.writeHeader(header);
            
            ConcreteSummitRecord r = new ConcreteSummitRecord();
            
            for(int i=0;i<10;++i){
                r.setPtaz((short)(i+1));
                for(int j=0;j<10;++j){
                    r.setAtaz((short)(j+1));
                    for(int market=0;market<header.getMarketSegments();++market){
                        r.setMarket((short)(market+1));
                        r.setExpAuto((float) -0.2);
                        r.setTrips((float) 100);
                        r.setMotorizedTrips((float)100);
                        r.setWalkTransitAvailableShare((float)30);
                        r.setTransitShareOfWalkTransit((float)0.5);
                        r.setDriveTransitOnlyShare((float)40);
                        r.setTransitShareOfDriveTransitOnly((float)5);
                        
                        sf.writeRecord(r);
                    }
                    
                }
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
