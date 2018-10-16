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
package com.pb.models.censusdata;

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import org.apache.log4j.Logger;

import java.io.File;
import java.io.IOException;
import java.util.Arrays;
import java.util.HashMap;

/*
 * 
 * The PumsGeography object contains geographical correspondence information about the Study Area including Halo.
 * Most of the info is read in from the zoneIndexFile passed to the constructor.
 */

public class PumsGeography {
    private static Logger logger = Logger.getLogger(PumsGeography.class);


	int maxAlphaZone = 0;
	int numAlphaZones = 0;
	int numberOfStates = 0;

	final int MAX_STATE_FIPS = 200;
	final int NUM_STATES = 50;
	final int MAX_PUMA = 99999 + 1;

	int[] indexFips = null;
	int[] fipsIndex = null;
	int[] indexZone = null;
	int[] zoneIndex = null;
		
	int[][] pumas = null;
    int[][] pumaIndex = null;
    int[][] indexPuma = null;
    String[] stateLabels = null;
    String[] zoneLabels = null;

    // default field names
    String pumaFieldName = "PUMA5pct";
    String stateFipsFieldName = "STATEFIPS";
    String tazFieldName = "Taz";
    String stateLabelFieldName = "State";
    
    HashMap <Integer, int[] > zoneCorrespondence = new HashMap<Integer, int[]>();
    
    
    public PumsGeography () {
    }

    
    
    public void setPumaFieldName ( String pumaFieldName ) {
        this.pumaFieldName = pumaFieldName;
    }
    
    public void setTazFieldName ( String tazFieldName ) {
        this.tazFieldName = tazFieldName;
    }
    
    public void setStateFipsFieldName ( String stateFipsFieldName ) {
        this.stateFipsFieldName = stateFipsFieldName;
    }
    
    public void setStateLabelFieldName ( String stateLabelFieldName ) {
        this.stateLabelFieldName = stateLabelFieldName;
    }
    
	public int getNumberOfStates() {
		return numberOfStates;
	}
    
    
	public int getMaxZoneNumber() {
		return maxAlphaZone;
	}
    
    
    public int getNumberOfZones() {
        return numAlphaZones;
    }
    
    
    public int getNumberOfPumas(int stateIndex) {
        return pumas[stateIndex].length;
    }

    public int getTotalNumberOfPumas(){
        int total = 0;
        for(int s =0 ; s < numberOfStates; s++){
            total += getNumberOfPumas(s);
        }
        return total;
    }


    public String getStateLabel( int i ) {
        return stateLabels[i];
    }

    public int getStateFIPS( int i ) {
        return indexFips[i];
    }
    
    
    public int getStateIndex( int i ) {
        return fipsIndex[i];
    }
    
    
    public String getTazFieldName() {
        return tazFieldName;
    }
    
    public int[] getStatePumaIndicesFromZoneIndex ( int i ) {


        int[] returnValues = new int[2];
        
        int zone = getIndexZone(i);
        int[] zoneCorrespondenceArray = (int[])zoneCorrespondence.get( Integer.valueOf(zone) );

        returnValues[0] =  getStateIndex( zoneCorrespondenceArray[0] );
        returnValues[1] =  getPumaIndex( returnValues[0], zoneCorrespondenceArray[1] );

        return returnValues;
        
    }
    
    
	public int[][] getPumas() {
		return pumas;
	}
    
    
    
    public boolean isFipsPumaInHalo (int stFips, int puma) {
        
        int stIndex = fipsIndex[stFips];
        
        for (int i=0; i < pumas[stIndex].length; i++) {
            
            if (puma == pumas[stIndex][i])
                return true;
            
        }
        
        return false;
            
    }


    public int getPumaIndex (int stateIndex, int puma) {
        
        for (int i=0; i < pumas[stateIndex].length; i++) {
            
            if (puma == pumas[stateIndex][i])
                return i;
            
        }
        
        return -1;
            
    }
    
    
    
    public int[] getStatePumaIndexArray (int stateIndex) {
        return pumaIndex[stateIndex];
    }
    
    
    
    public int getPumaLabel (int stateIndex, int pumaIndex) {
    	return pumas[stateIndex][pumaIndex];
    }


    public String[] getZoneLabels () {
        return zoneLabels;
    }
    

    public int[] getZoneIndex () {
        return zoneIndex;
    }
    

	public int getZoneIndex (int zone) {
		return zoneIndex[zone];
	}
    

	public int[] getIndexZone () {
		return indexZone;
	}
    

	public int getIndexZone (int index) {
		return indexZone[index];
	}
    
    
    

	public void readZoneIndices ( String fileName, String[] columnFormats ) {
	    
		int zone;
		int puma;
		int stateFips;
		
		
		CSVFileReader reader = new CSVFileReader();
        
		TableDataSet table = null;
		try {
            if(columnFormats != null)
                table = reader.readFileWithFormats( new File(fileName), columnFormats );
            else
                table = reader.readFile(new File(fileName));
        } catch (IOException e) {
			e.printStackTrace();
		}

		
		// get the number of zones in the table and declare int[] indexZone with that size
		numAlphaZones = table.getRowCount();

		
		// get the maximum alpha zone number and declare large enough int[] zoneIndex for than value
		for (int i=0; i < numAlphaZones; i++)
			if ( (int)table.getValueAt(i+1, tazFieldName ) > maxAlphaZone ) 
				maxAlphaZone = (int)table.getValueAt(i+1, tazFieldName );


			
        logger.info("Num alpha zones: " +  numAlphaZones);
        logger.info("Max alpha zone: " + maxAlphaZone);
		
		

		// process the alpha zone records in the table and create state correspondence indices;
		// also, each record has a unique alpha zone, so create zone correspondence indices.
		fipsIndex = new int[MAX_STATE_FIPS];
		int[] tempIndexFips = new int[NUM_STATES];
		Arrays.fill (tempIndexFips, -1);
		Arrays.fill (fipsIndex, -1);

		zoneIndex = new int[maxAlphaZone+1];
		indexZone = new int[numAlphaZones];
        zoneLabels = new String[numAlphaZones];
		Arrays.fill (zoneIndex, -1);
		Arrays.fill (indexZone, -1);



        
        
		int stateIndex = -1;
		int tazIndex = -1;
		for (int r=0; r < numAlphaZones; r++) {
		    
            puma = (int)table.getValueAt(r+1, pumaFieldName );
            stateFips = (int)table.getValueAt(r+1, stateFipsFieldName );
            
            if ( fipsIndex[stateFips] < 0 ) {
            	stateIndex++;
            	fipsIndex[stateFips] = stateIndex;
            	tempIndexFips[stateIndex] = stateFips;
            }
            
			zone = (int)table.getValueAt(r+1, tazFieldName);
            
           	tazIndex++;
           	zoneIndex[zone] = tazIndex;
            indexZone[tazIndex] = zone;
            zoneLabels[tazIndex] = Integer.toString( zone );
            
		}

		indexFips = new int[stateIndex+1];
		Arrays.fill (indexFips, -1);
		for (int i=0; i <= stateIndex; i++)
			indexFips[i] = tempIndexFips[i];
        
		numberOfStates = indexFips.length;
		
		
		// process the alpha zone records in the table again and create puma correspondence indices by state
		pumaIndex = new int[indexFips.length][MAX_PUMA];
		indexPuma = new int[indexFips.length][numAlphaZones];  // won't be more pumas than tazs so use numAlphaZones to declare array.
		int[] pumaIndices = new int[indexFips.length];	// increment index by state as correspondence arrays are built
		stateLabels = new String[indexFips.length];
		for (int i=0; i < indexFips.length; i++) {
			Arrays.fill (pumaIndex[i], -1);
			Arrays.fill (indexPuma[i], -1);
		}
		Arrays.fill (pumaIndices, -1);

		for (int r=0; r < numAlphaZones; r++) {

            zone = (int)table.getValueAt(r+1, tazFieldName);
            puma = (int)table.getValueAt(r+1, pumaFieldName );
            stateFips = (int)table.getValueAt(r+1, stateFipsFieldName );

            stateLabels[fipsIndex[stateFips]] = table.getStringValueAt(r+1, stateLabelFieldName );

            int[] correspondence = new int[2];
            correspondence[0] = stateFips;
            correspondence[1] = puma;
            
            zoneCorrespondence.put( Integer.valueOf(zone), correspondence );

            if ( pumaIndex[fipsIndex[stateFips]][puma] < 0 ) {
            	pumaIndices[fipsIndex[stateFips]]++;
            	pumaIndex[fipsIndex[stateFips]][puma] = pumaIndices[fipsIndex[stateFips]];
            	indexPuma[fipsIndex[stateFips]][pumaIndices[fipsIndex[stateFips]]] = puma;
            }
            
		}

        // declare the pumas[][] array based on number of states involved in study area and number of pumas in each state
		// and set the values of the pumas from the above correespondence arrays.
        pumas = new int[indexFips.length][];
        for (int i=0; i < indexFips.length; i++) {
        	pumas[i] = new int[pumaIndices[i]+1];
        	for (int j=0; j < pumas[i].length; j++)
        		pumas[i][j] = indexPuma[i][j];
        }
        		
		
	}

    /**
     * This method is used when reading in the PI outputs
     * since the ActivityLocations2 file (that lists quantities
     * of hhs in each zone) contains external zones that have
     * garbage data in them.  All the external zones (and world zones) will
     * be numbers greater than the internal alphazones.
     * @param zone the zone you are testing
     * @return whether of not this is a zone in our model area.
     */
    public boolean isHaloZone(int zone){
        return zone <= maxAlphaZone;
    }
	
	
}

