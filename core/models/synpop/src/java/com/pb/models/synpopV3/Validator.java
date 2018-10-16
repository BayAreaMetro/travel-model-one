/*
 * Copyright 2006 PB Consult Inc.
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
 */
/*
 * Created on May 4, 2005
 *
 */
package com.pb.models.synpopV3;

import java.util.Vector;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.datafile.CSVFileWriter;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;

import org.apache.log4j.Logger;

/**
 * @author Wu Sun
 * <sunw@pbworld.com>
 */
public class Validator {
	
    protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
	protected CensusValidationStatistics cStatistics;
	protected SynPopValidationStatistics spStatistics;
	protected int NoStatistics;
	//aggregated census statistics, 1D:validation statistics,2D:aggregate level element, e.g. PUMA
	protected float [][] aggregatedC;
	//aggregated SynPop statistics, 1D:validation statistics,2D:aggregate level element, e.g. PUMA
	protected float [][] aggregatedSP;
	protected int [] universeIDs;
	protected LookUpTable ltable;
	protected int numberOfInternalZones;
	//number of aggregate level elements, e.g. number of PUMAs
	protected int NoAggregateLevelElements;
	protected String levelName;
    protected String[] labels;
	protected float [] meanDiff;
	protected float [] stdDev;
	protected float [] maxDiff;
	protected float [] minDiff;
	// add arrays to hold the sum of each variable for popSyn and census variables (dto)
	protected float [] popSynSum;
	protected float [] censusSum;
	
	public Validator(CensusValidationStatistics cStatistics, SynPopValidationStatistics spStatistics){
		this.cStatistics=cStatistics;
		this.spStatistics=spStatistics;
		numberOfInternalZones=PopulationSynthesizer.numberOfInternalZones;
		NoStatistics=cStatistics.getNoStatistics();
	}
	
	public void doWork(String aggregationLevel){
		levelName = aggregationLevel;
		ltable=new LookUpTable("file",levelName);
		NoAggregateLevelElements = ltable.numberOfIndices();
		universeIDs=makeUniverseIDs();
		aggregate();
		calculate();
		writeResult();
	}
	
	public int getNoAggregateLevelElements(){
		return NoAggregateLevelElements;
	}
	
	public float [] getMeanDiff(){
		return meanDiff;
	}
	
	public float [] getStdDev(){
		return stdDev;
	}
	
	public float [] getMaxDiff(){
		return maxDiff;
	}
	
	public float [] getMinDiff(){
		return minDiff;
	}
	
	public float [] getPopSynSum(){
		return popSynSum;
	}
	
	public float [] getCensusSum(){
		return censusSum;
	}
	
	public float [][] getAggregatedCensusStatistics(){
		return aggregatedC;
	}
	
	public float [][] getAggregatedSynPopStatistics(){
		return aggregatedSP;
	}
	
	private void aggregate(){
		
		aggregatedC=new float[NoStatistics][NoAggregateLevelElements];
		aggregatedSP=new float[NoStatistics][NoAggregateLevelElements];
		
		//initialize aggregatedC and aggregatedSP
		for(int i=0; i<NoStatistics; i++){
			for(int j=0; j<NoAggregateLevelElements; j++){
				aggregatedC[i][j]=0;
				aggregatedSP[i][j]=0;
			}
		}
		
		//aggregate from TAZ to given level, e.g. PUMA level
		// modify to read index from HashMap (dto)
		for(int i=0; i<numberOfInternalZones; i++){
            int extTAZ = ExtTAZtoIntTAZIndex.getExternalTAZ(i+1); 
			int index = ltable.tazToAggregateIndex(extTAZ);
			for(int j=0; j<NoStatistics; j++){
				aggregatedC[j][index]+=cStatistics.getVStatistics(j,i);
				aggregatedSP[j][index]+=spStatistics.getVStatistics(j,i);
			}
		}
	}
	
	private int [] makeUniverseIDs(){
		
		Vector universeIDs=PropertyParser.getPropertyElementsByName("universeIDs",",");
		int NoUniverses=universeIDs.size();
		int [] uIDs=new int[NoUniverses];
		
		for(int i=0; i<NoUniverses; i++){
			uIDs[i]=new Integer((String)universeIDs.get(i)).intValue()-1;
		}
		return uIDs;
	}
	
	/**
	 * calculate mean difference,  standard deviation, maximum difference and minimum difference
	 * 
	 */
	private void calculate(){
		
        labels = cStatistics.getLabels(); 
		meanDiff=new float[NoStatistics];
		stdDev=new float[NoStatistics];
		maxDiff=new float[NoStatistics];
		minDiff=new float[NoStatistics];
		
		// add sums for the variables
		popSynSum = new float[NoStatistics];
		censusSum = new float[NoStatistics];
		
		float [] sum=new float[NoStatistics];
		float [][] diff=new float[NoStatistics][NoAggregateLevelElements];

		for(int i=0; i<NoStatistics; i++){
			maxDiff[i]=-9999999f;
			minDiff[i]=9999999f;
			sum[i]=0;
			popSynSum[i]=0;
			censusSum[i]=0;
		}
		
		// sum the variables across aggregation levels (dto) (xxx need to make percentages in next step)
		for(int i=0;i<NoStatistics;i++){
			for(int j=0;j<NoAggregateLevelElements;j++){
				popSynSum[i] += aggregatedSP[i][j];
				censusSum[i] += aggregatedC[i][j];
			}
		}
		
		int universe=-1;
		for(int i=0; i<NoStatistics; i++){
			universe=findUniverse(i);
			if(i!=universe){
				
                // compute percentages across aggregation levels (dto)
				if(popSynSum[universe]!=0) popSynSum[i] = (popSynSum[i]/popSynSum[universe])*100f;
				else popSynSum[i]=0;
				
				if(censusSum[universe]!=0) censusSum[i] = (censusSum[i]/censusSum[universe])*100f;
				else censusSum[i]=0;
				
				for(int j=0; j<NoAggregateLevelElements; j++){
					
					if(aggregatedSP[universe][j]!=0){
						aggregatedSP[i][j]=(aggregatedSP[i][j]/aggregatedSP[universe][j])*100f;
					}
					else{
						aggregatedSP[i][j]=0;
					}
					if(aggregatedC[universe][j]!=0){
						aggregatedC[i][j]=(aggregatedC[i][j]/aggregatedC[universe][j])*100f;
					}
					else{
						aggregatedC[i][j]=0;
					}
					
				}
			}
		}
		
		for(int i=0; i<NoStatistics; i++){
            int numZero = 0; 
			for(int j=0; j<NoAggregateLevelElements; j++){
                
				if(aggregatedC[i][j]!=0){
					diff[i][j]=((aggregatedSP[i][j]-aggregatedC[i][j])/aggregatedC[i][j])*100.0f;
				}
				else{
                    numZero++;
                    if (numZero < 5) {
                        logger.info("Validator: Aggregated ("+levelName+") census at statistic ID="+
                                 (i+1)+" Index="+j+" is 0.");                        
                    } else if (numZero==5) {
                        logger.info("           too many to count...");
                    }
					
					if(aggregatedSP[i][j]==0){
						diff[i][j]=0;
					}
					else{
						diff[i][j]=100;
					}
				}
				
				sum[i]+=diff[i][j];
								
				if(diff[i][j]>maxDiff[i]){
					maxDiff[i]=diff[i][j];
				}
				if(diff[i][j]<minDiff[i]){
					minDiff[i]=diff[i][j];
				}

			}
			meanDiff[i]=sum[i]/NoAggregateLevelElements;

		}
				
		for(int i=0; i<NoStatistics; i++){
			sum[i]=0;
			for(int j=0; j<NoAggregateLevelElements; j++){
				sum[i]+=Math.pow(diff[i][j]-meanDiff[i],2.0);
			}
			stdDev[i]=(float)Math.sqrt(sum[i]/(NoAggregateLevelElements-1));	
		}
	}
	
	//result should be 0-based
	private int findUniverse(int index){
		int result=-1;
		
		if(index>=universeIDs[universeIDs.length-1]){
			result=universeIDs[universeIDs.length-1];
		}else{
			for(int i=0; i<universeIDs.length-1; i++){
					if(index>=universeIDs[i]&&index<universeIDs[i+1]){
						result=universeIDs[i];
						break;
					}
			}
		}
		return result;
	}
	
	private void writeResult(){
		
		String validationDir=PropertyParser.getPropertyByName("validationResult.directory");
		String validationResults=PropertyParser.getPropertyByName("validationResults");
		CSVFileWriter writer=new CSVFileWriter();
		TableDataSet table=new TableDataSet();
        table.appendColumn(labels, "Label");
		table.appendColumn(popSynSum,"popSynSum");
		table.appendColumn(censusSum,"censusSum");
		table.appendColumn(meanDiff, "meanDiff");
		table.appendColumn(stdDev, "stdDev");
		table.appendColumn(minDiff, "minDiff");
		table.appendColumn(maxDiff, "maxDiff");

		try{
			writer.writeFile(table,new File(validationDir+levelName+"."+validationResults));
			//writer.writeTable(table,validationDir+validationResults);
		}catch(IOException e){
			logger.fatal("could not open "+validationResults+" for writing!");
		}
	}
    
    /**
     * Writes detailed validation results for each geographic unit, not just the means.  
     *
     */
    public void writeResultsDetails() {
        String validationDir=PropertyParser.getPropertyByName("validationResult.directory");
        String validationResultsDetails=PropertyParser.getPropertyByName("validationResultsDetails");
        PrintWriter writer = createWriter(new File(validationDir+levelName+"."+validationResultsDetails));
        
        // write the header, one column for each statistic
        writer.print(levelName + ",type");
        for (int i=0; i<NoStatistics; i++) {
            writer.print("," + labels[i]);
        }          
        writer.print("\n");
        
        // write the data with the statistics going down, and the geographies across
        for (int j=0; j<NoAggregateLevelElements; j++) {
            String aggregation = ltable.getAggregationFromIndex(j);
            
            // write the modeled
            writer.print(aggregation + ",popSyn");
            for (int i=0; i<NoStatistics; i++) {
                writer.print("," + aggregatedSP[i][j]);
            }          
            writer.print("\n");         
            
            // and the observed
            writer.print(aggregation + ",census");
            for (int i=0; i<NoStatistics; i++) {
                writer.print("," + aggregatedC[i][j]);
            }          
            writer.print("\n");  
        }
        writer.close();
    }
    
    /**
     * Creates a buffered print writer, pointing to the output file
     * specified in the property.  
     * 
     * @param property The property in the resource bundle with the file
     *                 name.  
     * @return a writer pointing to that file.  
     */
    private PrintWriter createWriter(File file) {
        logger.info("Writing to file " + file);
 
        PrintWriter writer; 
        try {
            FileWriter fw = new FileWriter(file);
            BufferedWriter bw = new BufferedWriter(fw);
            writer = new PrintWriter(bw);
        } catch (IOException e) {
            logger.fatal("Could not create file" + file);
            throw new RuntimeException(e);
        }
        return writer; 
    }
}
