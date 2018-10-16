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
package com.pb.common.matrix;

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import org.apache.log4j.Logger;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Iterator;
import java.util.TreeSet;

/**
 * A class to store alphaZone to betaZone key.
 *
 * @author Steve Hansen
 * @version 1.0 02/09/2004
 *
 */

public class AlphaToBeta implements AlphaToBetaInterface{
    protected static Logger logger = Logger.getLogger(AlphaToBeta.class);

    //alphaToBeta - mapping of alpha to beta zones column vector values = beta zone, external numbers = alphaZone
    protected int[] alphaToBeta;
    protected int[][] betaZoneArray;

    //1-indexed array containing the external numbers for an alphaZone matrix
    protected int[] alphaExternals;
    //1-indexed array containing the external numbers for a betaZone matrix
    protected int[] betaExternals;

    protected int maxAlphaZone;
    protected int maxBetaZone;


    /**
     * Constructor processes the TableDataSet containing the alphaZone to betaZone lookup information
     * @param table contains the alpha to beta correspondence
     * @param alphaZoneColumnName name of the column with the alphazone numbers
     * @param betaZoneColumnName name of the column with the betazone numbers
     */
    public AlphaToBeta(TableDataSet table, String alphaZoneColumnName, String betaZoneColumnName) {
        initialize(table.getColumnAsInt(table.checkColumnPosition(alphaZoneColumnName)),
                table.getColumnAsInt(table.checkColumnPosition(betaZoneColumnName)));
    }

    /**
     * Constructor processes the TableDataSet containing the alphaZone to betaZone lookup information
     * @param table  "AZone" columm has alpha zones, "BZone" column has beta zones
     */
    public AlphaToBeta(TableDataSet table){

        initialize(table.getColumnAsInt(table.getColumnPosition("AZone")),
                   table.getColumnAsInt(table.getColumnPosition("BZone")));

    }

    /**
     * Constructor processes the arrays containing the alphaZone to betaZone lookup information
     * @param alphaZoneColumn0Based - array of alphazone numbers
     * @param betaZoneColumn0Based - array of betazone numbers
     */
    public AlphaToBeta(int[] alphaZoneColumn0Based, int[]betaZoneColumn0Based){

            initialize(alphaZoneColumn0Based, betaZoneColumn0Based);
    }

    /**
     * Constructor reads the table data set from the file
     * @param csvFile - file containing the alpha to beta correspondence
     */
    public AlphaToBeta(File csvFile){

        TableDataSet table;
        CSVFileReader reader = new CSVFileReader();
        try {
            table = reader.readFile(csvFile);
            initialize(table.getColumnAsInt(table.getColumnPosition("AZone")),
                                    table.getColumnAsInt(table.getColumnPosition("BZone")));
        } catch (IOException e) {
            logger.error(csvFile.getAbsolutePath() + " could not be found - check path");
            e.printStackTrace();
        }

    }

    /**
     * Constructor reads the table data set from the file with columns specified
     * by the user.  This is the most flexible constructor since you can define
     * any column in any file as the alpha zones and any column in the same file as the
     * beta zones.
     * @param csvFile - file containing the alpha to beta correspondence
     * @param alphaColumnName - user specified header name for column to use as alpha zones
     * @param betaColumnName - user specified header name for column to use as beta zones
     * 
     */
    public AlphaToBeta(File csvFile, String alphaColumnName, String betaColumnName){

        TableDataSet table;
        CSVFileReader reader = new CSVFileReader();
        try {
            table = reader.readFile(csvFile);
            int alphaColumn = table.getColumnPosition(alphaColumnName);
            if(alphaColumn == -1 ) throw new RuntimeException("Column " + alphaColumnName + "does not exist in the file");
            
            int betaColumn = table.getColumnPosition(betaColumnName);
            if(betaColumn == -1 ) throw new RuntimeException("Column " + alphaColumnName + "does not exist in the file");
            
            initialize(table.getColumnAsInt(alphaColumn), table.getColumnAsInt(betaColumn));
            
        } catch (IOException e) {
            logger.fatal(csvFile.getAbsolutePath() + " could not be found - check path");
            logger.fatal(e);
            e.printStackTrace();
            System.exit(1);
        }catch (RuntimeException e) {
            logger.fatal(e.getMessage());
            System.exit(1);
        }

    }

    protected void initialize(int[] alphaZoneColumn0Based, int[]betaZoneColumn0Based){
        
        maxAlphaZone = getMaxZoneNumber(alphaZoneColumn0Based);
        maxBetaZone = getMaxZoneNumber(betaZoneColumn0Based);

        alphaToBeta = new int[maxAlphaZone+1];
        //initialize to -1
        Arrays.fill(alphaToBeta, -1);

        // set it to null unitl we need it.
        betaZoneArray = null;
        setAlphaToBetaArray(alphaZoneColumn0Based, betaZoneColumn0Based);
        //setBetaZoneArray(alphaZoneColumn, betaZoneColumn);
        setAlphaExternals(alphaZoneColumn0Based);
        setBetaExternals(betaZoneColumn0Based);
        
    }
    /** Get the highest value in an array
     * 
     * @return int - largest value in array
     * @param array array of zone numbers
     */
    
    static int getMaxZoneNumber(int[] array){
        int largest = array[0];
        for(int i=1;i<array.length;i++){
            if(array[i]>largest)
                largest = array[i];       
        }
    	logger.debug("Largest value = "+array[array.length-1]);
    	return largest;
    	

        
    }
    /**
     * Get the alphaZone external array
     * @return alphaExternals - the alphaZone externalNumber array
     */    
    public int[] getAlphaExternals1Based(){
        return alphaExternals;
    }
    /**
     * Get the alphaZone external array 0 based regular java array
     * @return alphaExternals - the alphaZone externalNumber array, 0 based
     */    
    public int[] getAlphaExternals0Based(){
        int[] ext = new int[alphaExternals.length-1];
        System.arraycopy(alphaExternals, 1, ext, 0, ext.length);
        return ext;
    }
    
    /**
     * Get the betaZone external array
     * @return betaExternals - the betaZone externalNumber array
     */
    public int[] getBetaExternals1Based(){
        return betaExternals;
    }
    
    /**
     * Get the betaZone external array as a 0 based regular java array
     * @return betaExternals - the betaZone externalNumber array
     */
    public int[] getBetaExternals0Based(){
        int[] ext = new int[betaExternals.length-1];
        System.arraycopy(betaExternals, 1, ext, 0, ext.length);
        return ext;
    }
    
    /**
     * Get the betaZone that contains the alphaZone
     * @param alphaZone
     * @return betaZone
     */
    public int getBetaZone(int alphaZone){    	
        return alphaToBeta[alphaZone];
    }
    
    /**
     * betaSize()
     * @return the number of unique betaZones
     */
    public int betaSize(){
    	return betaExternals.length-1;
    }
    
    /**
     * alphaSize()
     * @return the number of unique alphaZones
     */
    public int alphaSize(){
    	return alphaExternals.length-1;
    }

    public int getNumAlphaZones() {
        return alphaExternals.length-1;
    }

    public int getNumBetaZones() {
        return betaExternals.length-1;
    }

    public int getMaxAlphaZone() {
        return maxAlphaZone;
    }

    public int getMaxBetaZone() {
        return maxBetaZone;
    }

    /**
     * sets the values of alphaToBeta[aZone] = bZone
     * where aZone is an alphaZone, and bZone is the betaZone that contains the corresponding alphaZone
     * @param alphaZoneColumn0Based - array of
     * @param betaZoneColumn0Based
     *
     */
    public void setAlphaToBetaArray(int[] alphaZoneColumn0Based, int[] betaZoneColumn0Based){

        for(int i=0;i<alphaZoneColumn0Based.length;i++){
           alphaToBeta[alphaZoneColumn0Based[i]]=betaZoneColumn0Based[i];
        }        
    }
    
    /**
     * TODO need to fill the betaZone array with corresponding alphaZones
     * @param table
     */
  /*  public void setBetaZoneArray(int[] alphaZoneColumn, int[]betaZoneColumn){
        int bZone;
        int[] bZoneCount = new int[MAX_BETAZONE_NUMBER+1];
        for(int i=1;i<=table.getRowCount();i++){
            bZone= (int)table.getValueAt(i,table.getColumnPosition("BZone"));
            bZoneCount[bZone]++;
        }
        for(int i=0;i<MAX_BETAZONE_NUMBER;i++){
            betaZoneArray[i] = new int[bZoneCount[i]];
        }
        for(int i=0;i<MAX_ALPHAZONE_NUMBER;i++){
            //TODO fill betaZoneArray
        }        
    }*/
    
    /**
     * sets the value of the betaZone externalNumber array
     * @param betaZoneColumn0Based  column of beta zone numbers
     */
    public void setBetaExternals(int[]betaZoneColumn0Based){
        int bZone;
        TreeSet<Integer> list = new TreeSet<Integer>();
        for (int aBetaZone : betaZoneColumn0Based) {
            bZone = aBetaZone;
            list.add(bZone);
        }
        betaExternals = new int[list.size()+1];
        Iterator listIterator=list.iterator();
        int count = 1;
        while(listIterator.hasNext()){
            Integer value = (Integer) listIterator.next();
            betaExternals[count] = value;
            count++;
        }
        
    }
    
    public int[] getAlphaToBeta() {
        return alphaToBeta;
    }

    /**
     * sets the value of the alphaZone externalNumber array
     * @param alphaZoneColumn0Based column of alpha zones
     */
    public void setAlphaExternals(int[] alphaZoneColumn0Based){
        int aZone;
        TreeSet<Integer> list = new TreeSet<Integer>();
        for (int anAlphaZoneColumn : alphaZoneColumn0Based) {
            aZone = anAlphaZoneColumn;
            list.add(aZone);
        }
        alphaExternals = new int[list.size()+1];
        Iterator listIterator=list.iterator();
        int count = 1;
        while(listIterator.hasNext()){
            Integer value = (Integer) listIterator.next();
            alphaExternals[count] = value;
            count++;
        }     
    }    
    
    public static void main(String[] args){
        //read the taz data from csv to TableDataSet
        
        try{
            logger.debug("Adding AlphaToBetaTaz");
            //ResourceBundle rb = ResourceUtil.getResourceBundle( "pt" );
            //String file = ResourceUtil.getProperty(rb, "alphatobeta.file");
            CSVFileReader reader = new CSVFileReader();
            TableDataSet table = reader.readFile(new File("i:/development/tlumip-data/azonebzone.csv"));
            
            AlphaToBeta aTob = new AlphaToBeta(table.getColumnAsInt(table.getColumnPosition("AZone")),
            								   table.getColumnAsInt(table.getColumnPosition("BZone")));
            
        }catch(IOException e) {
           	   logger.error("Error reading alphazone to betazone file.");
           	   e.printStackTrace();
        }
    }

    public int[] getAlphasForBetas(int betaZone) {
        logger.fatal("AlphaToBeta.getAlphasForBetas() has been written but not yet tested -- terminating...");
        if (betaZoneArray == null) {
            betaZoneArray = new int[maxBetaZone+1][];
            ArrayList alphaZonesIntegers[] = new ArrayList[maxBetaZone+1];
            for (int a = 1;a<alphaExternals.length;a++) {
                int alpha = alphaExternals[a];
                int beta = getBetaZone(alphaExternals[a]);
                if (alphaZonesIntegers[beta]==null) alphaZonesIntegers[beta] = new ArrayList();
                alphaZonesIntegers[beta].add(new Integer(alpha));
            }
            for (int b=1;b<betaExternals.length;b++) {
                int beta = betaExternals[b];
                betaZoneArray[beta] = new int[alphaZonesIntegers[beta].size()];
                for (int i=0;i<alphaZonesIntegers[beta].size();i++) {
                    betaZoneArray[beta][i] = ((Integer) alphaZonesIntegers[beta].get(i)).intValue();
                }
            }
        }
        throw new RuntimeException("AlphaToBeta.getAlphasForBetas() has been written but not yet tested -- terminating...");
//        return betaZoneArray[betaZone];
    }
}