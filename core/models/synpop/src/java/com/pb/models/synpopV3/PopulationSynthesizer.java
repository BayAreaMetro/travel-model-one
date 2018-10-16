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
package com.pb.models.synpopV3;

import java.util.Random;
import java.util.Vector;

import org.apache.log4j.Logger;

import com.pb.common.matrix.NDimensionalMatrixDouble;

/**
 * @author Erhardt
 * @version 1.0 Oct 3, 2007
 *
 */
public class PopulationSynthesizer {
    
    protected static Logger logger = Logger.getLogger(PopulationSynthesizer.class);

    protected DerivedHHFactory hhFactory; 
    protected double runningTime0;
    protected TableDataManager tableDataManager; 
    protected DataDictionary dd; 
    protected PUMSData pumsData; 
    protected PUMSBucketGroup bucketGroup;
// move to constructor    public static int numberOfInternalZones = ExtTAZtoIntTAZIndex.getNumberOfInternalZones();
    public static int numberOfInternalZones;

    /**
     * Default Constructor
     *
     */
    public PopulationSynthesizer(String resourceBundleName, DerivedHHFactory hhFactory) {
        PropertyParser.setPropertyMap( resourceBundleName );
        this.hhFactory = hhFactory;
    }
    
    /**
     * Main method called to run the population synthesizer.  
     * 
     */
    public Vector[][] runPopulationSynthesizer(){
        
        numberOfInternalZones = ExtTAZtoIntTAZIndex.getNumberOfInternalZones();
//        hhFactory = new DerivedHHFactory();

        // record information
        logger.info("");
        logger.info("Atlanta Regional Commission Population Synthesizer");
        logger.info("       Program Version: 11/05/12");
        logger.info("      Developed by Parsons Brinckerhoff");
        logger.info("   Original Model Design by John L. Bowman");
        logger.info("");
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
     * Read data tables
     *
     */
    protected void readTables() {
        
        runningTime0=System.currentTimeMillis();
        tableDataManager=new TableDataManager();
        double runningTime1 = System.currentTimeMillis() - runningTime0;
        logger.info ("TableDataManager took = " + (float)((runningTime1/1000.0)/60.0)+" minute.");
    }
    
    protected void readPUMSData() {
        
        runningTime0=System.currentTimeMillis();
        // create a random seed generator here to pass down through to set the bucket bins
        Random randomGenerator = new Random(0);
        dd=new DataDictionary(PropertyParser.getPropertyByName("pums.directory")+PropertyParser.getPropertyByName("pums.dictionary"), 5, 120, 170);
        pumsData=new PUMSData(dd,tableDataManager.getTAZtoPUMAIndex(), hhFactory);
        bucketGroup=new PUMSBucketGroup(pumsData, tableDataManager.getTAZtoPUMAIndex(), randomGenerator);
        double runningTime2 = System.currentTimeMillis() - runningTime0;
        logger.info ("PUMSData took = " + (float)((runningTime2/1000.0)/60.0)+" minute.");
    }
    
    /**
     * Runs forecast mode.  
     *
     */
    protected NDimensionalMatrixDouble runForecast() {
        runningTime0=System.currentTimeMillis();
        
        // check if controls are read from table, or if ForecastTazData class is used.
        boolean readControlsFromTable = false;
        if(PropertyParser.getPropertyByName("Forecast.ReadControlsFromTable").equalsIgnoreCase("true")) readControlsFromTable = true;
    
        TazData tazData; 
        float[][] rawControlTargets; 
        
        if (readControlsFromTable) {
            
            // read the targets from what is specified in the FutureYearSourceData table
            BaseTargetGenerator btg=new BaseTargetGenerator(tableDataManager, "FutureYear");
            rawControlTargets = btg.getTargetsFloat(); 
            
            tazData = new BasicTazData("Forecast.TazFile", "Forecast.HouseholdColumn");                
        } else {                
            // create the forecast taz object and read in data
            ForecastTazData forecastTazData = new ForecastTazData();
            
            // generate the control totals for the forecast data (feed number of control totals for now)
            forecastTazData.computeControlTotals(numberOfInternalZones,pumsData.generateForecastControlData(),
                                              tableDataManager.getTableReader("design"));
            rawControlTargets = forecastTazData.getControlTotals();
            
            tazData = (TazData) forecastTazData; 
        }                        
    
        // create the future seed object
        FutureSeedDistribution futureSeed = new FutureSeedDistribution();
        
        // compute the seed
        futureSeed.generateSeed(tazData);
        
        // build the forecast control table
        ControlTable forecastControlTable = new ControlTable("future", rawControlTargets, 
                                                              tableDataManager.getTableReader("design"));
        ControlTableBalancer forecastControlBalancer = new ControlTableBalancer(futureSeed.getSeed(), 
                                                                                forecastControlTable);
        // get the balanced seed
        NDimensionalMatrixDouble balancedSeed=forecastControlBalancer.getBalancedSeedDistribution();
        
        logger.info ("FutureSeedGenerator took = " + (float)((runningTime0/1000.0)/60.0)+" minutes.");

        // write out balanced seed if desired (modify to print out like a matrix rather than a table)
        if(PropertyParser.getPropertyByName("writeBalancedBaseSeedDistribution").equalsIgnoreCase("true")){
            String location=PropertyParser.getPropertyByName("interimResult.directory")+PropertyParser.getPropertyByName("BalancedSeedDistribution");
            balancedSeed.printMatrixDelimited(",",location);
        }
        double runningTime5 = System.currentTimeMillis() - runningTime0;
        logger.info ("ControlTableBalancer took = " + (float)((runningTime5/1000.0)/60.0)+" minute.");
        
        return balancedSeed; 
    }
    
    /** 
     * Run base year application
     *
     */
    protected NDimensionalMatrixDouble runBaseYear() {

        // base year seed generator
        runningTime0=System.currentTimeMillis();
        BaseSeedDistributionGenerator seedGenerator=new BaseSeedDistributionGenerator(tableDataManager, bucketGroup);
        double runningTime3 = System.currentTimeMillis() - runningTime0;
        logger.info ("BaseSeedDistributionGenerator took = " + (float)((runningTime3/1000.0)/60.0)+" minute.");
        
        //compare base seed distribution and bucket group
        PUMSBucket [][] buckets=bucketGroup.getPUMSBuckets();
        double [][] seed=seedGenerator.getBaseSeedDistribution();
        int NoHHCats=buckets[0].length;
        TAZtoPUMAIndex tpIndex=tableDataManager.getTAZtoPUMAIndex();
        
        for(int i=0; i<numberOfInternalZones; i++){
            int extTAZ = ExtTAZtoIntTAZIndex.getExternalTAZ(i+1); 
            int puma=tpIndex.getPUMA(extTAZ);
            int pumaIndex=tpIndex.getPUMAArrayIndex(puma);
            for(int j=0; j<NoHHCats; j++){
                if(buckets[pumaIndex][j].NHHs==0&&seed[j][i]!=0){
                    logger.warn("bucket is empty at puma="+puma+"pumaIndex="+pumaIndex+" and HHCatIndex="+j+" but seed at HHCatIndex="+j+" and TAZIndex="+i+" is "+seed[j][i]);
                }
            }
        }

        // base year target generator
        runningTime0=System.currentTimeMillis();
        BaseTargetGenerator btg=new BaseTargetGenerator(tableDataManager);
        double runningTime4 = System.currentTimeMillis() - runningTime0;
        logger.info ("BaseTargetGenerator took = " + (float)((runningTime4/1000.0)/60.0)+" minute.");
        
        // meta target generator
        runningTime0=System.currentTimeMillis();
        MetaTargetGenerator mtg=new MetaTargetGenerator(btg, tableDataManager.getTableReader("design"));
        double runningTime11 = System.currentTimeMillis() - runningTime0;
        logger.info ("MetaTargetGenerator took = " + (float)((runningTime11/1000.0)/60.0)+" minute.");
        
        // meta balancing
        runningTime0=System.currentTimeMillis();
        ControlTable mControlTable=new ControlTable("baseMeta", mtg.getMetaTargets(), tableDataManager.getTableReader("design"));
        ControlTableBalancer mctb = new ControlTableBalancer(btg.getTargetsNDimimensionalMatrix(), mControlTable);
        double [][] balancedBaseTargets=mctb.getBalancedSeedArray();
        double runningTime10 = System.currentTimeMillis() - runningTime0;
        logger.info ("Meta ControlTableBalancer took = " + (float)((runningTime10/1000.0)/60.0)+" minute.");
        
        // control balancing
        runningTime0=System.currentTimeMillis();
        NDimensionalMatrixDouble balancedSeed;
        ControlTable controlTable=new ControlTable("base", balancedBaseTargets, 
                                                    tableDataManager.getTableReader("design"));
        ControlTableBalancer ctb = new ControlTableBalancer(seedGenerator.getBaseSeedDistributionNMatrix(), 
                                                            controlTable);
        balancedSeed=ctb.getBalancedSeedDistribution();

        // write out balanced seed if desired (modify to print out like a matrix rather than a table)
        if(PropertyParser.getPropertyByName("writeBalancedBaseSeedDistribution").equalsIgnoreCase("true")){
            String location=PropertyParser.getPropertyByName("interimResult.directory")+PropertyParser.getPropertyByName("BalancedSeedDistribution");
            balancedSeed.printMatrixDelimited(",",location);
        }
        double runningTime5 = System.currentTimeMillis() - runningTime0;
        logger.info ("ControlTableBalancer took = " + (float)((runningTime5/1000.0)/60.0)+" minute.");
        
        return balancedSeed; 
    }
    
    /**
     * Dicretize the seed distribution. 
     *
     */    
    protected NDimensionalMatrixDouble discretizeSeedDistribution(NDimensionalMatrixDouble balancedSeed) {

        // write out discretized seed
        runningTime0=System.currentTimeMillis();
        NDimensionalMatrixDouble discretizedSeed=balancedSeed.discretize();
        if(PropertyParser.getPropertyByName("writeDiscretizedBaseSeedDistribution").equalsIgnoreCase("true")){
            String location=PropertyParser.getPropertyByName("interimResult.directory")+PropertyParser.getPropertyByName("DiscretizedSeedDistribution");
            discretizedSeed.printMatrixDelimited(",",location);
        }
        double runningTime6 = System.currentTimeMillis() - runningTime0;
        logger.info ("Discretizer took = " + (float)((runningTime6/1000.0)/60.0)+" minute.");        
        
        return discretizedSeed; 
    }
    
    /**
     * Prints a validation report
     * 
     * @param populationVector the population
     * @param runForecast boolean indicating if in forecast mode
     */
    protected void runValidation(Vector populationVector, boolean runForecast) {
        
        boolean writeDetailedValidation = PropertyParser.getPropertyByName("WriteValidationDetails").equalsIgnoreCase("true");
        
        SynPopValidationStatistics sp=new SynPopValidationStatistics(populationVector);            
        double runningTime14 = System.currentTimeMillis() - runningTime0;
        logger.info ("SynPopStatistics took = " + (float)((runningTime14/1000.0)/60.0)+" minute.");
        
        runningTime0=System.currentTimeMillis();
        String censusYear = "Base";
        if(runForecast) censusYear = "Future";
        CensusValidationStatistics cv=new CensusValidationStatistics(tableDataManager,censusYear);
        double runningTime15 = System.currentTimeMillis() - runningTime0;
        logger.info ("Census Statistics took = " + (float)((runningTime15/1000.0)/60.0)+" minute.");
        
        // added aggregationLevel (from PUMA) to make aggregation more genearlizeable
        runningTime0=System.currentTimeMillis();
        Validator vld=new Validator(cv,sp);
        
        // perform validation level for each specified level of aggregation
        Vector aggregationLevels = new Vector();
        aggregationLevels=PropertyParser.getPropertyElementsByName("AggregationLevels",",");
        for(int i=0;i<aggregationLevels.size();++i) {
            vld.doWork((String)aggregationLevels.get(i));
            if (writeDetailedValidation) {
                vld.writeResultsDetails(); 
            }
        }
        
        double runningTime16 = System.currentTimeMillis() - runningTime0;
        logger.info ("Validator took = " + (float)((runningTime16/1000.0)/60.0)+" minute.");
        
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
    }
    
    /**
     * Print the synthetic population to disk
     * 
     * @param drawer The household drawer object
     */
    protected void runMainPopulationPrinter(HHDrawer drawer) {
        runningTime0=System.currentTimeMillis();
        SynPopPrinter popSynPrinter=new SynPopPrinter(drawer.getPopSyn(), drawer.getNoDrawnHHs(), drawer.getNoDrawnPersons());
        popSynPrinter.print();
        double runningTime12 = System.currentTimeMillis() - runningTime0;
        logger.info ("SynPopPrinter took = " + (float)((runningTime12/1000.0)/60.0)+" minute.");  
    }
    

    public static void main(String [] args){

        // if a property file name is passed as an argument, use it, otherwise use the default ("arc"). 
        String rbName = "arc"; 
        if ( args.length > 0 )
            rbName = args[0]; 
        
        PopulationSynthesizer popsyn = new PopulationSynthesizer(rbName, new DerivedHHFactory()); 
        popsyn.runPopulationSynthesizer(); 
        
    }
}
