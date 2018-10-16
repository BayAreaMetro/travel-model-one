/*
 * Copyright  2007 PB Consult Inc.
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
package com.pb.mtc.synpop;

import java.util.Vector;

import com.pb.common.matrix.NDimensionalMatrixDouble;
import com.pb.models.synpopV3.ExtTAZtoIntTAZIndex;
import com.pb.models.synpopV3.HHDrawer;
import com.pb.models.synpopV3.PopulationSynthesizer;
import com.pb.models.synpopV3.PropertyParser;
import com.pb.models.synpopV3.SynPopPrinter;

/**
 * Calls the synpopV3 model for use with the MTC project.
 * 
 * @author Erhardt
 * @version 1.0 Oct 2, 2007
 *
 */
public class MTCPopulationSynthesizer extends PopulationSynthesizer {

    public MTCPopulationSynthesizer() {
        super("populationSynthesizer", new DerivedHHSFFactory()); 
    }
    
    public MTCPopulationSynthesizer(String propertiesRoot){
    	super(propertiesRoot, new DerivedHHSFFactory());
    }
    
    
   /**
    * Overwrite method to remove the version/owner header, which has been 
    * moved to the main method
    */
   public Vector[][] runPopulationSynthesizer(){
        
        numberOfInternalZones = ExtTAZtoIntTAZIndex.getNumberOfInternalZones();

        double runningTime00=System.currentTimeMillis();
        
        readTables(); 
        
        readPUMSData(); 
        
        // declare the discretized seed for base and future year application
        NDimensionalMatrixDouble balancedSeed;        
        
        // check for forecast switch, and do forecast application (dto)
        boolean runForecast = false;
        if(PropertyParser.getPropertyByName("Forecast.RunForecast").equalsIgnoreCase("true")) runForecast = true;
        
        if(runForecast){
            balancedSeed = runForecast(); 
        } else{
            balancedSeed = runBaseYear(); 
        }
                
        NDimensionalMatrixDouble discretizedSeed = discretizeSeedDistribution(balancedSeed); 
        
        
        runningTime0=System.currentTimeMillis();
        HHDrawer drawer=new HHDrawer(pumsData, bucketGroup, discretizedSeed, tableDataManager);
        double runningTime7 = System.currentTimeMillis() - runningTime0;
        logger.info ("HHDrawer took = " + (float)((runningTime7/1000.0)/60.0)+" minute.");
        
        Vector v=new Vector();
        Vector [][] synPop=drawer.getPopSyn();
        for(int i=0; i<synPop.length; i++){
            for(int j=0; j<synPop[0].length; j++){
                v.addAll(synPop[i][j]);
            }
        }     
        
        // run validation if requested
        if(PropertyParser.getPropertyByName("RunValidation").equalsIgnoreCase("true")){
            runValidation(v, runForecast); 
        }
        
        // only if requested
        printPopulation(drawer); 
        
        double runningTime8 = System.currentTimeMillis() - runningTime00;
        logger.info ("Total running time = " + (float)((runningTime8/1000.0)/60.0)+" minute.");
        logger.info("Finished with population synthesizer!");
        
        return(synPop);
    }
    

    /**
     * Main population printer that looks at options
     * 
     * @param drawer
     */
    protected void printPopulation(HHDrawer drawer) {
        if(PropertyParser.getPropertyByName("RunPopulationPrinter").equalsIgnoreCase("true")){
            runMainPopulationPrinter(drawer); 
        }
        
        if(PropertyParser.getPropertyByName("PrintJointHHPersonFile").equalsIgnoreCase("true")){
            printJointHHPersonFile(drawer); 
        }
    }
    
    
    protected void printJointHHPersonFile(HHDrawer drawer) {
        runningTime0=System.currentTimeMillis();
        SynPopPrinter popSynPrinter=new SynPopPrinter(drawer.getPopSyn(), drawer.getNoDrawnHHs(), drawer.getNoDrawnPersons());
        popSynPrinter.printJointHHPersonAttributes();
        double runningTime12 = System.currentTimeMillis() - runningTime0;
        logger.info ("SynPopPrinter joint file took = " + (float)((runningTime12/1000.0)/60.0)+" minute.");   
    }
    
    
    public static void main(String[] args) {
    	
        // record information
        logger.info("");
        logger.info("            Population Synthesizer         ");
        logger.info("         Program Version: 2010Mar2009      ");
        logger.info("      Developed by Parsons Brinckerhoff    ");
        logger.info("   Original Model Design by John L. Bowman ");
        logger.info("");
        
        // use "mtc" resource bundle, and inherited derived household class
        PopulationSynthesizer popsyn = new MTCPopulationSynthesizer(); 
        popsyn.runPopulationSynthesizer(); 

    }
}
