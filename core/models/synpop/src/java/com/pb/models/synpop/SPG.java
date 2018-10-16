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
package com.pb.models.synpop;

import com.pb.common.datafile.*;
import com.pb.common.util.IndexSort;
import com.pb.common.util.SeededRandom;
import com.pb.models.censusdata.*;
import com.pb.models.utils.StatusLogger;
import org.apache.log4j.Logger;

import java.io.*;
import java.util.*;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * The SPG class is used to produce a set of synthetic households
 * from PUMS data consistent with regional employment forecasted by
 * industry category and to assign HHs to alpha zones.
 * 
 * The procedure is implemented in 2 parts:
 * SPG1 - develop a set of PUMS households consistent with the regional distribution
 *        of households by workers per household category where the employed persons
 *        in these households total to the constraints on employemnet by industry category.
 * SPG2 - using zonal dollars of production by occupation and household category,
 *        from AA, allocate households to model area traffic analysis zones .
 *
 */

public class SPG {
    protected static Logger logger = Logger.getLogger(SPG.class);
    
    public static final String ACS_HOUSEHOLD_FILE_PROPERTY_PREFIX = "acs.household.file.";
    public static final String ACS_PERSON_FILE_PROPERTY_PREFIX = "acs.person.file.";
    public static final String USE_ACS_FLAG_PROPERTY = "spg.use.acs";

    static final int HH_SELECTED_INDEX = 0;
    static final int HH_UNEMPLOYED_INDEX = 1;
    static final int PUMS_HH_INDEX = SpgPumsData.PUMS_HHID_INDEX;
    static final int HHID_INDEX = SpgPumsData.HHID_INDEX;
    static final int STATE_ATTRIB_INDEX = SpgPumsData.STATE_INDEX;
    static final int PUMA_ATTRIB_INDEX = SpgPumsData.PUMA_INDEX;
    static final int NUM_PERSONS_ATTRIB_INDEX = SpgPumsData.HHSIZE_INDEX;
    static final int HH_INCOME_ATTRIB_INDEX = SpgPumsData.HHINC_INDEX;
    static final int HH_WEIGHT_ATTRIB_INDEX = SpgPumsData.HHWT_INDEX;
    static final int NUM_WORKERS_ATTRIB_INDEX = SpgPumsData.HHWRKRS_INDEX;
    static final int PERSON_ARRAY_ATTRIB_INDEX = SpgPumsData.PERSON_ARRAY_INDEX;

    static final int NUM_PERSON_ATTRIBUTES = 5;

    static final double MAXIMUM_ALLOWED_CONTROL_DIFFERENCE = 0.05;
    static final int MAX_BALANCING_ITERATION = 30;
    
    static final int SPG2_LOG_FREQ = 500000;

    
    
    // person attributes for person j:
    // industry: PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 0
    // occup:    PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 1
    // employed: PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 2
    // person weight: PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 3
    // person age: PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 4

    
    
    HashMap spgPropertyMap;
    HashMap globalPropertyMap;

    public PumsGeography halo = null;               //needs to be shared with project specific SPG
    SwIndustry ind = null;
    Workers workers = null;
    HhSize hhsize = null;
    private PersonAge personAge;
    public SwOccupation occ = null;                        //needs to be shared with project specific SPG
    public SwIncomeSize incSize = null;                    //needs to be shared with project specific SPG
    
    int[][][] hhArray = null;
    int[][] hhSelectedIndexArray = null;
    
    public double[][] regionLaborDollars = null;      //needs to be shared with project specific SPG

    int[][] hhsAllocated = null;
    int[] hhsAllocatedRegion = null;
    
    float[] tempEmploymentTargets = null;
    int[] employmentTargets = null;
    int[] personAgeTargets = null;
    int[] hhWorkerTargets = null;
    int[] hhSizeTargets = null;
    
    double[][] observedEmployment = null;
    double[][] observedHhWorkers = null;
    double[][] observedHhSize = null;
    double[][] observedPersonAge = null;

    double[][] employmentControls = null;
    double[][] hhWorkerControls = null;
    double[][] hhSizeControls = null;
    double[][] personAgeControls = null;

    double[] employmentControlTotals = null;
    double[] hhWorkerControlTotals = null;
    double[] hhSizeControlTotals = null;
    double[] personAgeControlTotals = null;
    
    double[] hhWeights = null;

    int balancingCount = 0;

    double[] oldEmpFactors;
    double[] oldHhFactors;
    

    // define age range maximums for 0-4, 5-9, 10-14, 15-20, 21-39, 40-59, 60+.
    //these are used for a pi input/report, *not* for age constraints
    final int[] ageRangeMax = { 5, 10, 15, 21, 40, 60, 999 };
    final String[] ageRangeLabels = { "Person0to5", "Person5to10", "Person10to15", "Person15to21", "Person21to40", "Person40to60", "Person60plus" };

    //used by status logger
    private String currentYear;
    
    int origRegionalHHs;
    int[][] origHHsZoneIncomeSizePI = null;
    int[] origHHsIncomeSizePI = null;
    double[][][] origLaborDollarsPI = null;
    double[][][] unallocatedLaborDollarsPI = null;

    public double[][] regionLaborDollarsPerJob = null;    
    
    public static int[][] hhsByTazCategory = null;
    public static int[][] personAgesByTaz = null;
    public static int[] totalHhsByTaz = null;
    public static int[] totalPersonsByTaz = null;
    public static int[] totalWorkersByTaz = null;
    public static int[] totalHhIncomeByTaz = null;
    
    // get correspondence arrays between zone indices and external zone labels
    public int[] zoneIndex = null;
    int[] indexZone = null;

    int badTazCount = 0;
    int employedCount = 0;
    int employedCount0 = 0;
    int employedTotal = 0;
    int unemployedTotal = 0;

    private int populationTotal = -1;

    int maxZone = 0;
    int numZones = 0;

    public int numIncomeSizes;
    int numOccupations;

    
    private static Object objLock = new Object();
    private static int categoryCount = 0;
    private static int cumulativeHhCount = 0;
    public static String[][] mtResults;
    
    public SPG(){} //empty constructor needed for DAF implementation
    
    protected void spgInit ( HashMap spgPropertyMap, HashMap globalPropertyMap, SwIncomeSize incSize, SwIndustry ind, SwOccupation occ, String currentYear ) {
        this.spgPropertyMap = spgPropertyMap;
        this.globalPropertyMap = globalPropertyMap;
        this.incSize = incSize;
        this.ind = ind;
        this.occ = occ;

        this.currentYear = currentYear;
        
        this.numIncomeSizes = this.incSize.getNumberIncomeSizes();
        this.numOccupations = occ.getNumberOccupations();
        boolean sensitivityTestingMode;
        try {
            sensitivityTestingMode = Boolean.parseBoolean((String) globalPropertyMap.get("spg.sensitivity.testing"));
        } catch (Exception ex) {
            sensitivityTestingMode = false;         }

        if(sensitivityTestingMode)
            SeededRandom.setSeed( (int) System.currentTimeMillis() );
        else
            SeededRandom.setSeed( Integer.parseInt(globalPropertyMap.get("randomSeed").toString()));
               
        halo = new PumsGeography();
        halo.setPumaFieldName( (String)globalPropertyMap.get("pumaField.name") );
        halo.setTazFieldName( (String)globalPropertyMap.get("alpha.name") );
        halo.setStateLabelFieldName( (String)globalPropertyMap.get("stateLabelField.name") );
        halo.setStateFipsFieldName( (String)globalPropertyMap.get("stateFipsField.name") );

        // Get list of alpha2beta file field formats to fields will be either NUMERIC or STRING when read into TableDataSet.
//        String formatString = (String)globalPropertyMap.get("alpha2beta.formats");
//        ArrayList formatList = new ArrayList();
//        StringTokenizer st = new StringTokenizer(formatString, ", |");
//        while (st.hasMoreTokens()) {
//            formatList.add(st.nextElement());
//        }
//        String[] alpha2betaColumnFormats = new String[formatList.size()];
//        for (int i=0; i < alpha2betaColumnFormats.length; i++)
//            alpha2betaColumnFormats[i] = (String)formatList.get(i);


        // read the zonal correspondence file into the halo object
        //halo.readZoneIndices ( (String)globalPropertyMap.get("alpha2beta.file"), alpha2betaColumnFormats );
        halo.readZoneIndices ( (String)globalPropertyMap.get("alpha2beta.file"), null);
        
        workers = new Workers();

        hhsize = new HhSize();


        if (spgPropertyMap.containsKey(NED_POPULATION_FORECAST_PROPERTY))
            personAge = new PersonAge((String) spgPropertyMap.get(NED_POPULATION_FORECAST_PROPERTY),Integer.parseInt(currentYear));
        else
            personAge = new PersonAge((String) spgPropertyMap.get("spg.person.age.specification.file"));

    
        // define zonal summary arrays
        numZones = halo.getNumberOfZones();

        // get correspondence arrays between zone indices and external zone labels
        zoneIndex = halo.getZoneIndex();
        indexZone = halo.getIndexZone();
        maxZone = halo.getMaxZoneNumber();
        
        hhsByTazCategory = new int[numZones][incSize.getNumberIncomeSizes()];
        personAgesByTaz = new int[numZones][ageRangeMax.length];
        totalHhsByTaz = new int[numZones];
        totalPersonsByTaz = new int[numZones];
        totalWorkersByTaz = new int[numZones];
        totalHhIncomeByTaz = new int[numZones];
        
    }


    public void disablePersonAgeConstraint() {
        personAge.setEnabled(false);
    }

    public void enablePersonAgeConstraint() {
        personAge.setEnabled(true);
    }

    public boolean isPersonAgeConstraintEnabled() {
        return personAge.isEnabled();
    }

    public void setPopulationTotal(int population) {
        logger.info("Setting spg1 population to " + population);
        populationTotal = population;
    }

    public void resetSPG1BalancingCount() {
        balancingCount = 0;
    }

    //todo: move these to the appropriate location
    public static final String NED_ACTIVITY_FORECAST_PROPERTY = "ned.activity_forecast.path";
    public static final String NED_POPULATION_FORECAST_PROPERTY = "ned.population_forecast.path";

    private float[] getEmploymentTargetsFromNedOutputs(String nedActivityForecast) {
        // read the SW regional employment by industry output file into a TableDataSet
		CSVFileReader reader = new CSVFileReader();

        String[] formats = { "STRING", "NUMBER", "NUMBER" };
		TableDataSet table = null;
		try {
			table = reader.readFileWithFormats(new File(nedActivityForecast),formats);
		} catch (IOException e) {
            logger.error(e);
            throw new RuntimeException(e);
		}
        String[] names = table.getColumnAsString(1);
        float[] employment = table.getColumnAsFloat(2);
        float[] orderedEmployment = new float[employment.length+1];
        for (int i = 0; i < employment.length; i++)
            orderedEmployment[ind.getIndustryIndexFromLabel(names[i])] = employment[i];
        return orderedEmployment;
    }

    // SPG1 - Select households randomly from Pums records in halo.  Keep track of which
    // industry category persons in household belong to.  When enough households have been
    // selected such that the frequency of selected person industry codes matches the
    // employment totals provided by ED, we're done.
    public void spg1 (String currentYear) {
        StatusLogger.logText("spg1","SPG1 started for " + currentYear + " run");
        
        logger.info ("Start of SPG1\n");
        
        int employed = 0;
        int pumsIndustryCode;
        int pumsOccupationCode;
        int pumsIncomeCode;
        int incomeSizeCode;
        int numWorkers;
        int workersCode;
        int pumsHHWeight;
        
        
        
        // get the array of regional employment targets which must be matched by workers in selected households.
        // also apply the factors to reduce employment targets based on multiple jobs per worker and other definitional differences.
        //keys are different for Ohio and Tlumip - we need a more elegant fix but will consider it further
        //when we restructure the TLUMIP directories.
        String nedActivityForecast = (String) spgPropertyMap.get(NED_ACTIVITY_FORECAST_PROPERTY);
        if (nedActivityForecast == null) {
            String employmentFilePath = (String)spgPropertyMap.get("isam.statewide.employment.by.industry");
            if(employmentFilePath == null)
                employmentFilePath = (String)spgPropertyMap.get("statewide.employment.by.industry");
            tempEmploymentTargets = ind.getIndustryEmployment( employmentFilePath, currentYear );
        } else {
            tempEmploymentTargets = getEmploymentTargetsFromNedOutputs(nedActivityForecast);
        }
        employmentTargets = new int[tempEmploymentTargets.length];


        // read the jobs per worker factors for each employment category
        double[] pumsWorkersPerEdJob;
        logger.info("Jobs to Worker factors File Path" + spgPropertyMap.get("spg1.workers.per.job.factors"));
        pumsWorkersPerEdJob = workers.getJobsPerWorkerFactors( (String)spgPropertyMap.get("spg1.workers.per.job.factors"), ind );

        double totalEmployees = 0.0;
        double totalEdEmployment = 0.0;
        double remainder = 0.0;
        double reducedEmployment;
        for (int i=0; i < tempEmploymentTargets.length; i++) {
            reducedEmployment = tempEmploymentTargets[i]*pumsWorkersPerEdJob[i];
            remainder += ( reducedEmployment - (int)reducedEmployment );
            employmentTargets[i] = (int)reducedEmployment;
            if ( remainder >= 1.0 ) {
                employmentTargets[i] += 1;
                remainder -= 1.0;
            }
            totalEmployees += employmentTargets[i];
            totalEdEmployment += tempEmploymentTargets[i];
        }
        if (remainder >= 0.5) {
            employmentTargets[tempEmploymentTargets.length-1] ++; // if remainder > 0.5, add extra employee to last actual employment category (length-1).
            totalEmployees ++;
        }

        logger.info("Done reading employment data.");
        logger.info("Total employment over all industries from target file = " + totalEdEmployment);
        logger.info("Total employment after applying workersPerJob factors = " + totalEmployees);
        logger.info("Overall employment reduced by " + ((totalEdEmployment - totalEmployees)/totalEdEmployment) );
        StatusLogger.logText("spg1","employment from economic model read");

        //deal with person age
        if (personAge.isEnabled()) {
            logger.info("Setting person age targets.");
            if (populationTotal < 1)
                throw new IllegalStateException("Person age constraints population to be set via setPopulationTotal() method");
            personAgeTargets = personAge.getMarginalAgeRangeTargets(Integer.parseInt(currentYear),populationTotal);

            logger.info(String.format("Final persons age targets have %s persons.",populationTotal));
            StatusLogger.logText("spg1","Person age targets calculated.");
        } else {
            logger.info("Person age constraints disabled for spg1.");
        }

        
        
        // read the number of households in each workers per household category.
        logger.info("Worker Marginal File Path = " + spgPropertyMap.get("spg1.workers.per.household.marginals"));
        hhWorkerTargets = workers.getWorkersPerHousehold( (String)spgPropertyMap.get("spg1.workers.per.household.marginals"), currentYear );
        
        // adjust the hh worker targets to be consistent with total employment determined after applying Jobs to Workers factors.
        // calculate the proportions of workers from the input marginals in each hh worker category and the factor to determine number of households
        double totalWorkerTargets = 0.0;
        for (int i=0; i < hhWorkerTargets.length; i++)
            totalWorkerTargets += hhWorkerTargets[i];

        double[] workerProportions = new double[hhWorkerTargets.length];
        double hhFactor = 0.0f;
        for (int i=0; i < hhWorkerTargets.length; i++) {
            workerProportions[i] = hhWorkerTargets[i]/totalWorkerTargets;
            hhFactor += i*workerProportions[i];
        }
        
        // divide total employment by the hhFactor to get number of households consistent with specified employment and hh worker distribution
        double totalHouseholds = (int)(totalEmployees/hhFactor + 0.5);
        
        // calculate the new set of hh worker targets from these proportions and number of households
        double totalWorkers = 0.0;
        remainder = 0.0;
        for (int i=0; i < hhWorkerTargets.length; i++) {
            remainder += ( workerProportions[i]*totalHouseholds - ((int)(workerProportions[i]*totalHouseholds)) );
            hhWorkerTargets[i] = ((int)(workerProportions[i] * totalHouseholds));
            if ( remainder >= 1.0 ) {
                hhWorkerTargets[i] += 1;
                remainder -= 1.0;
            }
            totalWorkers += i*hhWorkerTargets[i];
        }
        if (remainder >= 0.5) {
            hhWorkerTargets[hhWorkerTargets.length-1] += 1;
            totalWorkers += (hhWorkerTargets.length-1);
        }
        
        // adjust targets so that number of workers in employment categories match number of workers in workers per household categories
        int diff = ((int)(totalEmployees - totalWorkers));
        if ( diff > 0 )
            hhWorkerTargets[diff]++;
        else if ( diff < 0 )
            hhWorkerTargets[-diff]--;

        // check adjustment
        totalWorkers = 0.0;
        double totalTargets = 0.0;
        for (int i=0; i < hhWorkerTargets.length; i++) {
            totalWorkers += i*hhWorkerTargets[i];
            totalTargets += hhWorkerTargets[i];
        }        
        
        totalHouseholds = totalTargets;
        
        logger.info ( String.format("final workers per hh targets have %s workers in %s hhs.", totalWorkers, totalTargets ) );
        StatusLogger.logText("spg1","worker targets calculated");




        
        // read the number of households in each persons per household category.
        String tempFileName = (String)spgPropertyMap.get("spg1.persons.per.household.marginals");
        if ( tempFileName == null || tempFileName.length() == 0 ) {
            hhSizeTargets = null;
        }
        else {
            logger.info("Persons Marginal File Path = " + spgPropertyMap.get("spg1.persons.per.household.marginals"));
            hhSizeTargets = hhsize.getHhsByHhSize( (String)spgPropertyMap.get("spg1.persons.per.household.marginals") );

            // adjust the hh size targets to be consistent with total households determined after adjusting workers per household targets.
            // calculate the proportions of persons from the input marginals in each hh size category.
            double totalHhSizeTargets = 0.0;
            for (int i=0; i < hhSizeTargets.length; i++)
                totalHhSizeTargets += hhSizeTargets[i];
    
            double[] hhSizeProportions = new double[hhSizeTargets.length];
            for (int i=0; i < hhSizeTargets.length; i++) {
                hhSizeProportions[i] = hhSizeTargets[i]/totalHhSizeTargets;
            }
            
    
            // calculate the new set of hh size targets from these proportions and number of households
            double totalPersons = 0.0;
            remainder = 0.0;
            for (int i=0; i < hhSizeTargets.length; i++) {
                remainder += ( hhSizeProportions[i]*totalHouseholds - ((int)(hhSizeProportions[i]*totalHouseholds)) );
                hhSizeTargets[i] = ((int)(hhSizeProportions[i] * totalHouseholds));
                if ( remainder >= 1.0 ) {
                    hhSizeTargets[i] += 1;
                    remainder -= 1.0;
                }
                totalPersons += (i+1)*hhSizeTargets[i];
            }
            if (remainder >= 0.5) {
                hhSizeTargets[hhSizeTargets.length-1] += 1;
                totalPersons += (hhSizeTargets.length-1);
            }
            
            // check adjustment
            totalPersons = 0.0;
            totalTargets = 0.0;
            for (int i=0; i < hhSizeTargets.length; i++) {
                totalPersons += (i+1)*hhSizeTargets[i];
                totalTargets += hhSizeTargets[i];
            }        
            
            logger.info ( String.format("final persons per hh targets have %s persons in %s hhs.", totalPersons, totalTargets ) );
            StatusLogger.logText("spg1","hh size targets calculated");
        
        }
        
        
        
        
        // count the total number of unique PUMS household records
        int numHouseholds = getTotalPumsHouseholds();
        int[] pumsTotalWorkers = getTotalWorkers(); // element 0: total sample, element 1: total weighted
        int numWeightedWorkers = pumsTotalWorkers[1];

        // set the dimensions for the control arrays, then initialize their
        initializeTableBalancingArrays(numHouseholds, numWeightedWorkers,getTotalPumsPersons(),employmentTargets,personAgeTargets);
        

        
        oldEmpFactors = new double[employmentControlTotals.length];
        oldHhFactors = new double[hhWorkerControlTotals.length];
        
        StatusLogger.logText("spg1","starting table balancing");
        // iterate over updating balancing factors, and updating balancing arrays
        // when the convergence criteria is met, updateTableBalancingArrays() will return false 
        while ( updateTableBalancingArrays() ) {
        }
        
        // change occupation codes from 0 to a non-zero code for employed persons.
        reassignOccupationCodes();
        
        
        // write comparison of final employment control totals vs control targets to logger
        float targetsTotal = 0.0f;
        float modelTotal = 0.0f;
        String[] categoryLabels = ind.getIndustryLabels();
        logger.info(String.format("%-45s", "Employment Categories") + "  " +    String.format("%12s", "Index") + "  " + String.format("%18s", "Targets") + "  " + String.format("%18s", "Workers" ) );
        for (int i=0; i < employmentTargets.length; i++) {
            String label = categoryLabels[i];
            logger.info( String.format("%-45s", label) + "  " + String.format("%12d", i) + "  " + String.format("%18d", employmentTargets[i] ) + "  " + String.format("%18.1f", employmentControlTotals[i] ) );
            targetsTotal += employmentTargets[i];
            modelTotal += employmentControlTotals[i];
        }
        logger.info(String.format("%-45s", "Total") + "  " +    String.format("%12s", " ") + "  " + String.format("%18.0f", targetsTotal ) + "  " + String.format("%18.1f\n\n\n", modelTotal ) );

        
        // write comparison of final hh worker control totals vs control targets to logger
        targetsTotal = 0.0f;
        modelTotal = 0.0f;
        categoryLabels = workers.getWorkersLabels();
        logger.info(String.format("%-45s", "HH Worker Categories") + "  " + String.format("%12s", "Index") + "  " + String.format("%18s", "Targets") + "  " + String.format("%18s", "Households" ) );
        for (int i=0; i < hhWorkerTargets.length; i++) {
            String label = categoryLabels[i];
            logger.info( String.format("%-45s", label) + "  " + String.format("%12d", i) + "  " + String.format("%18d", hhWorkerTargets[i] ) + "  " + String.format("%18.1f", hhWorkerControlTotals[i] ) );
            targetsTotal += hhWorkerTargets[i];
            modelTotal += hhWorkerControlTotals[i];
        }
        logger.info(String.format("%-45s", "Total") + "  " +    String.format("%12s", " ") + "  " + String.format("%18.0f", targetsTotal ) + "  " + String.format("%18.1f\n\n\n", modelTotal ) );

        
        
        
        // write comparison of final hh size control totals vs control targets to logger
        if ( hhSizeTargets != null ) {
            targetsTotal = 0.0f;
            modelTotal = 0.0f;
            categoryLabels = hhsize.getHhSizeLabels();
            logger.info(String.format("%-45s", "HH Size Categories") + "  " + String.format("%12s", "Index") + "  " + String.format("%18s", "Targets") + "  " + String.format("%18s", "Households" ) );
            for (int i=0; i < hhSizeTargets.length; i++) {
                String label = categoryLabels[i];
                logger.info( String.format("%-45s", label) + "  " + String.format("%12d", i) + "  " + String.format("%18d", hhSizeTargets[i] ) + "  " + String.format("%18.1f", hhSizeControlTotals[i] ) );
                targetsTotal += hhSizeTargets[i];
                modelTotal += hhSizeControlTotals[i];
            }
            logger.info(String.format("%-45s", "Total") + "  " +    String.format("%12s", " ") + "  " + String.format("%18.0f", targetsTotal ) + "  " + String.format("%18.1f\n\n\n", modelTotal ) );
        }



        // write comparison of final person age control totals vs control targets to logger
        if (personAge.isEnabled()) {
            targetsTotal = 0.0f;
            modelTotal = 0.0f;
            categoryLabels = personAge.getAgeRanges();
            logger.info(String.format("%-45s", "Person Age Categories") + "  " + String.format("%12s", "Index") + "  " + String.format("%18s", "Targets") + "  " + String.format("%18s", "Persons" ) );
            for (int i=0; i < personAgeTargets.length; i++) {
                String label = categoryLabels[i];
                logger.info(String.format("%-45s", label) + "  " + String.format("%12d", i) + "  " + String.format("%18d", personAgeTargets[i] ) + "  " + String.format("%18.1f", personAgeControlTotals[i]));
                targetsTotal += personAgeTargets[i];
                modelTotal += personAgeControlTotals[i];
            }
            logger.info(String.format("%-45s", "Total") + "  " +    String.format("%12s", " ") + "  " + String.format("%18.0f", targetsTotal ) + "  " + String.format("%18.1f\n\n\n", modelTotal ) );
        }
        
        
        
        // update hhArray data structure with the final numbers of selected employed and unemployed hhs
        int hhid = 0;
        double[] buckets = new double[observedHhWorkers[0].length];
        for (int i=0; i < hhArray.length; i++) {
            
            for (int k=0; k < hhArray[i].length; k++) {
        
                numWorkers = hhArray[i][k][NUM_WORKERS_ATTRIB_INDEX];
                workersCode = workers.getWorkers(numWorkers); 
                
                // update the hhArray numWorkers values based on categories defined in input workers per households file.
                hhArray[i][k][NUM_WORKERS_ATTRIB_INDEX] = workersCode;
                
                pumsHHWeight = hhArray[i][k][HH_WEIGHT_ATTRIB_INDEX];

                // check the observed zero workers per household category to see if the PUMS household is unemployed or not
                // if so, the integerized final hhWeight is the number of times this unemployed hh is selected.
                if ( workersCode == 0 ) {
                    hhArray[i][k][HH_SELECTED_INDEX] = 0;
                    buckets[0] += hhWeights[hhid]*pumsHHWeight - (int)(hhWeights[hhid]*pumsHHWeight);
                    hhArray[i][k][HH_UNEMPLOYED_INDEX] = (int)(hhWeights[hhid]*pumsHHWeight);
                    if ( buckets[0] >= 1.0 ) {
                        hhArray[i][k][HH_UNEMPLOYED_INDEX] += 1;
                        buckets[0] -= 1.0;
                    }
                }
                // else, the integerized final hhWeight is the number of times this employed hh is selected.
                else {
                    hhArray[i][k][HH_UNEMPLOYED_INDEX] = 0;
                    buckets[workersCode] += hhWeights[hhid]*pumsHHWeight - (int)(hhWeights[hhid]*pumsHHWeight);
                    hhArray[i][k][HH_SELECTED_INDEX] = (int)(hhWeights[hhid]*pumsHHWeight);
                    if ( buckets[workersCode] >= 1.0 ) {
                        hhArray[i][k][HH_SELECTED_INDEX] += 1;
                        buckets[workersCode] -= 1.0;
                    }
                }
                
                hhid++;
                    
            }

        }

//      // count up the final numbers of selected employed and unemployed hhs and persons
//      logger.info ("summarizing households and persons from synthetic population.");
//      for (int i=0; i < hhArray.length; i++) {
//
//          for (int k=0; k < hhArray[i].length; k++) {
//
//              if ( hhArray[i][k][HH_UNEMPLOYED_INDEX] > 0 ) {
////                    finalUnemployedHHs += hhArray[i][k][HH_UNEMPLOYED_INDEX];
//                  finalPersonsInUnemployedHHs += hhArray[i][k][NUM_PERSONS_ATTRIB_INDEX]*hhArray[i][k][HH_UNEMPLOYED_INDEX];
//              }
//              else {
//                  employedHHs += hhArray[i][k][HH_SELECTED_INDEX];
//                  personsInEmployedHHs += hhArray[i][k][NUM_PERSONS_ATTRIB_INDEX]*hhArray[i][k][HH_SELECTED_INDEX];
//              }
//
//          }
//
//      }

        logger.info ("writing hhArray");
        StatusLogger.logText("spg1","writing Household objects to disk");

        writeHhArray ();


        if (((String) spgPropertyMap.get("spg1.write.frequency.tables")).equalsIgnoreCase("true")) {
            int iVar = 0;
            int jVar = 0;
            int kVar = 0;

            int[][] indJobs = new int[4][ind.getNumberIndustries()];
            int[][] occJobs = new int[4][occ.getNumberOccupations()];
            int[][] hhIncSizes = new int[4][incSize.getNumberIncomeSizes()];
            int[][] hhWorkers = new int[4][workers.getNumberWorkerCategories()];

            String[] personAgeCategories = null;
            int[] personsByAge = null;
            if (personAge.isEnabled()) {
                personAgeCategories = personAge.getAgeRanges();
                personsByAge = new int[personAgeCategories.length];
            }

            try {

                // get the regional number of employed persons by industry and occupation in hhArray from SPG1
                for (int i=0; i < hhArray.length; i++) {
                    iVar = i;
                    for (int k=0; k < hhArray[i].length; k++) {
                        kVar = k;
                        int hhSize = hhArray[i][k][NUM_PERSONS_ATTRIB_INDEX];
                        pumsIncomeCode = hhArray[i][k][HH_INCOME_ATTRIB_INDEX];
                        workersCode = hhArray[i][k][NUM_WORKERS_ATTRIB_INDEX];

                        incomeSizeCode = incSize.getIncomeSize(pumsIncomeCode, hhSize);
                        hhIncSizes[1][incomeSizeCode] += hhArray[i][k][HH_SELECTED_INDEX];
                        hhIncSizes[0][incomeSizeCode] += hhArray[i][k][HH_UNEMPLOYED_INDEX];
                        if ( workersCode > 0 )
                            hhIncSizes[3][incomeSizeCode] += hhArray[i][k][HH_WEIGHT_ATTRIB_INDEX];
                        else
                            hhIncSizes[2][incomeSizeCode] += hhArray[i][k][HH_WEIGHT_ATTRIB_INDEX];

                        hhWorkers[1][workersCode] += hhArray[i][k][HH_SELECTED_INDEX];
                        hhWorkers[0][workersCode] += hhArray[i][k][HH_UNEMPLOYED_INDEX];
                        if ( workersCode > 0 )
                            hhWorkers[3][workersCode] += hhArray[i][k][HH_WEIGHT_ATTRIB_INDEX];
                        else
                            hhWorkers[2][workersCode] += hhArray[i][k][HH_WEIGHT_ATTRIB_INDEX];

                        for (int j=0; j < hhSize; j++) {
                            jVar = j;
                            pumsIndustryCode = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 0];
                            pumsOccupationCode = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 1];
                            employed = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 2];

                            int personIndustry = pumsIndustryCode;
                            int personOccupation = pumsOccupationCode;
                            indJobs[employed][personIndustry] += hhArray[i][k][HH_SELECTED_INDEX];
                            occJobs[employed][personOccupation] += hhArray[i][k][HH_SELECTED_INDEX];
                            indJobs[employed+2][personIndustry] += hhArray[i][k][HH_UNEMPLOYED_INDEX];
                            occJobs[employed+2][personOccupation] += hhArray[i][k][HH_UNEMPLOYED_INDEX];

                            if (personAge.isEnabled())
                                personsByAge[personAge.getAgeCategoryIndex(hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 4])] +=
                                        hhArray[i][k][HH_SELECTED_INDEX] + hhArray[i][k][HH_UNEMPLOYED_INDEX];

                        }
                    }
                }

            }
            catch (Exception e) {
                logger.error ( "Exception caught calculating frequency arrays in SPGnew.spg1(), i=" + iVar + ", j=" + jVar + ", k=" + kVar, e );
            }

            // write frequency tables of unemployed and employed persons in employed households by industry and occup.
            logger.info ("");
            writeFreqSummaryToLogger ( "employed persons in employed households by industry category", "INDUSTRY", ind.getIndustryLabels(), indJobs[1] );
            writeFreqSummaryToLogger ( "unemployed persons in employed households by industry category", "INDUSTRY", ind.getIndustryLabels(), indJobs[0] );

            logger.info ("");
            writeFreqSummaryToLogger ( "employed persons in employed households by occupation category", "OCCUPATION", occ.getOccupationLabels(), occJobs[1] );
            writeFreqSummaryToLogger ( "unemployed persons in employed households by occupation category", "OCCUPATION", occ.getOccupationLabels(), occJobs[0] );

            // write frequency tables of unemployed and employed persons in unemployed households by industry and occup.
            logger.info ("");
            writeFreqSummaryToLogger ( "employed persons in unemployed households by industry category", "INDUSTRY", ind.getIndustryLabels(), indJobs[3] );
            writeFreqSummaryToLogger ( "unemployed persons in unemployed households by industry category", "INDUSTRY", ind.getIndustryLabels(), indJobs[2] );

            logger.info ("");
            writeFreqSummaryToLogger ( "employed persons in unemployed households by occupation category", "OCCUPATION", occ.getOccupationLabels(), occJobs[3] );
            writeFreqSummaryToLogger ( "unemployed persons in unemployed households by occupation category", "OCCUPATION", occ.getOccupationLabels(), occJobs[2] );

            // write frequency tables of employed and unemployed households by hh category.
            logger.info ("");
            writeFreqSummaryToLogger ( "employed households by household category", "HH_INCOME_SIZE", incSize.getIncomeSizeLabels(), hhIncSizes[1] );
            writeFreqSummaryToLogger ( "unemployed households by household category", "HH_INCOME_SIZE", incSize.getIncomeSizeLabels(), hhIncSizes[0] );

            logger.info ("");
            writeFreqSummaryToLogger ( "employed PUMS weighted households by household category", "HH_INCOME_SIZE", incSize.getIncomeSizeLabels(), hhIncSizes[3] );
            writeFreqSummaryToLogger ( "unemployed PUMS weighted households by household category", "HH_INCOME_SIZE", incSize.getIncomeSizeLabels(), hhIncSizes[2] );

            logger.info ("");
            writeFreqSummaryToLogger ( "employed households by Number of Workers in Household", "HH_WORKERS", workers.getWorkersLabels(), hhWorkers[1] );
            writeFreqSummaryToLogger ( "unemployed households by Number of Workers in Household", "HH_WORKERS", workers.getWorkersLabels(), hhWorkers[0] );

            logger.info ("");
            writeFreqSummaryToLogger ( "employed PUMS weighted households by Number of Workers in Household", "HH_WORKERS", workers.getWorkersLabels(), hhWorkers[3] );
            writeFreqSummaryToLogger ( "unemployed PUMS weighted households by Number of Workers in Household", "HH_WORKERS", workers.getWorkersLabels(), hhWorkers[2] );

            if (personAge.isEnabled()) {
                logger.info ("");
                writeFreqSummaryToLogger ( "PUMS weighted persons by person age","PERSONS",personAgeCategories,personsByAge);
            }


            logger.info ("summarizing and writing frequency tables by state");
            writeFrequencyTables();
        }


        logger.info ( "" );
        logger.info ("end of spg1");
        StatusLogger.logText("spg1","spg1 done");
    }
    

    


    public int getPopulationTotal() {
        int population = 0;
        for (int i=0; i < hhArray.length; i++)
            for (int k=0; k < hhArray[i].length; k++)
                population += hhArray[i][k][NUM_PERSONS_ATTRIB_INDEX]*(hhArray[i][k][HH_SELECTED_INDEX] + hhArray[i][k][HH_UNEMPLOYED_INDEX]);
        return population;
    }

    public int getHhArraySize() {
        return hhArray.length;
    }

    public void spg2 () {
        
        logger.info ("Start of SPG2\n");
        long time = System.currentTimeMillis();

        StatusLogger.logText("spg2","Starting SPG2 for " + currentYear);
        StatusLogger.logText("spg2","Reading files necessary for spg2");

        setupSpg2();
        
        getRegionalDollarsPerJob();
        
        // the threads results will be saved in the static String[][] mtRresults, where the first dimension
        // in mtResults[][] is the category index, and the second dimension is the number of hhs for that category.
        mtResults = new String[hhArray.length][];
        

        // second implementation of multi-threaded code using Executor and CountDownLatch

        // create a new instance of AssignZonesTask (a Runnable inner class) to assign zones for a category, then call its setup and start it, for each thread.
        // in each thread, the run() will get the list of categories passed to setup(), and assign zones to hhs for those categories.


        ExecutorService exec = Executors.newCachedThreadPool();
        CountDownLatch countdown = new CountDownLatch(numIncomeSizes);

        String[] incSizeLabels = incSize.getIncomeSizeLabels();
        
        for (int i = 0; i < numIncomeSizes; i++) {
            AssignZonesWorker w = new AssignZonesWorker(i, incSizeLabels[i], countdown);
            exec.execute(w);
        }
        
        // wait for all the threads to finish before proceding.
        try {
            countdown.await();
        } catch (InterruptedException e1) {
            logger.fatal ("exception caught waiting for Executor threads to finish.", e1);
        }
        
        // close down ExecutorService after all threads have finished
        exec.shutdown();
        
        
        
        

/*      
        // first implementation of multi-threaded code
         * 
        // get the number of threads this program can use from the number of cores in the machine
        int numberOfThreads = java.lang.Runtime.getRuntime().availableProcessors();
        
        // get an ArrayList of categories to process for each thread where each element of threadCategories[]
        // is an ArrayList of the category indices the thread will work on.
        ArrayList[] threadCategories = getCategoriesForThreads( numberOfThreads );

        // create a new instance of AssignZonesTask (a Runnable inner class) to assign zones for a category, then call its setup and start it, for each thread.
        // in each thread, the run() will get the list of categories passed to setup(), and assign zones to hhs for those categories.
        for (int i = 0; i < numberOfThreads; i++) {
            AssignZonesTask task = new AssignZonesTask();
            task.setup( i, threadCategories[i],  categoryLabels, regionLaborDollarsPerJob );
            new Thread(task).start();
        }
        
        // wait here until all categories have been processed by the tasks started
        while ( categoryCount < hhArray.length ) {
            int waitTime = 10;
            if ( categoryCount < hhArray.length - 1 )
                waitTime = 60;
            
            try {
                TimeUnit.SECONDS.sleep(waitTime);
            }
            catch (InterruptedException e) {
                logger.error("caught exception while sleeping waiting for threads to finish, categoryCount = " + categoryCount, e);
            }
        }
*/
        
        
        
/*
        // This is the single threaded code that was replaced by multi-threaded code above
         
        // allocate synthetic household records to zones by groups of hh categories
        int count = 0;
        for ( int category=0; category < hhArray.length; category++ ) {
            
            mtResults[category] = assignZonesForHhCategory( category, regionLaborDollarsPerJob, categoryLabels[category] );
            count += mtResults[category].length;
            logger.info( String.format("%d of %d households have had zones assigned.", count, origRegionalHHs) );
            
        }
*/

        
        writeSPG2OutputFile();
        
        logger.info( employedCount + " households with at least one employee assigned a zone based on zonal distribution of $Labor density.");
        logger.info( employedCount0 + " households with at least one employee assigned a zone based on zonal distribution of total households.");
        logger.info( employedTotal + " total employed hhs processed.");
        logger.info( unemployedTotal + " total unemployed hhs processed.");

        logger.info("SPG2 runtime: " + (System.currentTimeMillis()-time)/1000.0);
        StatusLogger.logText("spg2","spg2 done");
    }

    public void getRegionalDollarsPerJob(){
        double[][] regionJobs = new double[numOccupations][numIncomeSizes];
                regionLaborDollarsPerJob = new double[numOccupations][numIncomeSizes];

                // get the regional number of employed persons by occupation and incomeSize from SPG1
                for (int i=0; i < hhArray.length; i++) {
                    for (int k=0; k < hhArray[i].length; k++) {
                        int hhSize = hhArray[i][k][NUM_PERSONS_ATTRIB_INDEX];
                        int hhIncome = hhArray[i][k][HH_INCOME_ATTRIB_INDEX];
                        int incomeSize = incSize.getIncomeSize(hhIncome, hhSize);
                        for (int j=0; j < hhSize; j++) {
                            int personEmploymentStatus = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 2];

                            if ( personEmploymentStatus == 1) {
                                int personOccupation = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 1];
                                regionJobs[personOccupation][incomeSize] += hhArray[i][k][HH_SELECTED_INDEX];
                            }

                        }
                    }
                }


                // get the regional mean labor$ per job to use in decrementing labor$ as households are allocated to zones.
                logger.info ("");
                for (int i=0; i < regionLaborDollars.length; i++) {
                    for (int j=0; j < regionLaborDollars[i].length; j++) {
                        regionLaborDollarsPerJob[i][j] = regionLaborDollars[i][j]/regionJobs[i][j];
                        logger.info ( "occup=" + occ.getOccupationLabel(i) + "   incSize=" + incSize.getIncomeSizeLabel(j) + "   laborDollars=" + regionLaborDollars[i][j]+ "   jobs=" + regionJobs[i][j] + "   dollarsPerJob=" +  regionLaborDollarsPerJob[i][j] );
                    }
                }
        
    }

    // open a csv file and write header to save a record for each hh with hhid, state, and zone.
    public void writeSPG2OutputFile(){
        logger.info ("");
        String fileName = (String)spgPropertyMap.get("spg2.hh.record.list");
        try {
            StatusLogger.logText("spg2","Writing SynPop files");
            PrintWriter hhOutStream = new PrintWriter( new BufferedWriter( new FileWriter( fileName ) ) );

            //write household file header record
            String header = "hhid, state, zone";
            hhOutStream.println( header );

            // write the string values saved to the output file
            for (int i=0; i < mtResults.length; i++)
                for (int j=0; j < mtResults[i].length; j++)
                    hhOutStream.println( mtResults[i][j] );

            hhOutStream.close();

        }
        catch (IOException e) {
            logger.fatal("IO Exception writing temp household file with hhid, state, zone: " + fileName, e );
        }
    }
    


    private ArrayList[] getCategoriesForThreads( int numberOfThreads ) {
        
        // sort the categories by the number of hhs to be assigned zones, in descending order:
        int[] sortValues = new int[hhArray.length];
        for (int i=0; i < hhArray.length; i++) {
            int numHHs = origHHsIncomeSizePI[i];
            sortValues[i] = -numHHs;
        }
        int[] categoryOrder = IndexSort.indexSort(sortValues);


        // define set of categories to be computed by each thread
        ArrayList[] categoriesPerThreadLists = new ArrayList[numberOfThreads];
        for ( int i=0; i < numberOfThreads; i++ )
            categoriesPerThreadLists[i] = new ArrayList();
        
        // add the category indices to the lists, in round robin, by descending number of hhs per category. 
        int count = 0;
        for ( int i=hhArray.length-1; i >= 0; i-- ) {
            int j = count % numberOfThreads;
            categoriesPerThreadLists[j].add( categoryOrder[i] );
            count++;
        }
        
        return categoriesPerThreadLists;
        
    }
    
    
    //need the method to be public for use in DAF code
    public void setupSpg2() {
        
        int numOccupations = occ.getNumberOccupations();
        int numIncomeSizes = incSize.getNumberIncomeSizes();

        regionLaborDollars = new double[numOccupations][numIncomeSizes];

        hhsAllocated = new int[indexZone.length][numIncomeSizes];
        hhsAllocatedRegion = new int[numIncomeSizes];
        origHHsIncomeSizePI = new int[numIncomeSizes];
        
        
        // read the DiskObjectArray file into hhArray
        readHhArray();

        
        // read the input files produced by PI which runs after SPG1
        String hhsByCategoryPath = (String)spgPropertyMap.get("seam.hhs.by.category.by.zone");
        if(hhsByCategoryPath == null) hhsByCategoryPath = (String)spgPropertyMap.get("pi.hhs.by.category.by.zone");

        String laborDollarsByZonePath = (String)spgPropertyMap.get("seam.labor.dollars.by.zone");
        if(laborDollarsByZonePath == null) laborDollarsByZonePath = (String)spgPropertyMap.get("pi.labor.dollars.by.zone");
        origHHsZoneIncomeSizePI = readPiIncomeSizeHHs ( hhsByCategoryPath );
        origLaborDollarsPI = readPiLaborDollars ( laborDollarsByZonePath );
      // copy original PI labor$ array to initialize unallocated array
        unallocatedLaborDollarsPI = new double[origLaborDollarsPI.length][][];
        for (int i=0; i < origLaborDollarsPI.length; i++) {
            unallocatedLaborDollarsPI[i] = new double[origLaborDollarsPI[i].length][];
            for (int j=0; j < origLaborDollarsPI[i].length; j++) {
                unallocatedLaborDollarsPI[i][j] = new double[origLaborDollarsPI[i][j].length];
                for (int k=0; k < origLaborDollarsPI[i][j].length; k++) {
                    unallocatedLaborDollarsPI[i][j][k] = origLaborDollarsPI[i][j][k];
                }
            }
        }

        // get summary arrays of hhs from PI - hhs by zone and hhs by incomeSize.
        // used for calculating labor dollar densities or proportions if no labor dollars (labor$ used up, or unemployed hh)
        
        // also keep track of the zone with the highest number of households, by hhCategory.
        // the setupHouseholdIndexLookupArray() method will compare rounded values from the PI file with total hhs by category rom SPG1.
        // if a difference is found, the setupHouseholdIndexLookupArray() method will adjust origHHsZoneIncomeSizePI[i][k] for the k
        // corresponding to the max hh zone.
        origRegionalHHs = 0;
        
        int[] maxHhIndices = new int[origHHsZoneIncomeSizePI.length];
        double[] maxHhValues = new double[origHHsZoneIncomeSizePI.length];
        for (int i=0; i < origHHsZoneIncomeSizePI.length; i++) {
            for (int k=0; k < origHHsZoneIncomeSizePI[i].length; k++) {
                origHHsIncomeSizePI[k] += origHHsZoneIncomeSizePI[i][k];
                origRegionalHHs += origHHsZoneIncomeSizePI[i][k];
                
                if ( origHHsZoneIncomeSizePI[i][k] > maxHhValues[i] )
                    maxHhIndices[i] = k;
            }
        }
        
        
        // set the index lookup arrays by hh categories - pass in the indices for the maximum number of households by category.
        // if an adjustment has to be made so the PI numbers match SPG1 totals by category, the adjustment will be made to the
        // zone with the max hhs.
        setupHouseholdIndexLookupArray( maxHhIndices );

       
    }
    
    
    
    
    public String[] assignZonesForHhCategory( int category, double[][] regionLaborDollarsPerJob, String categoryLabel, Random randomGen ) {
        

        int count = 0;
        int selectedIndex = 0;
        int selectedZone = 0;

        double reduction = 0.0;
        
        
        // get the number of synthetic households for the category
        int numHouseholds = origHHsIncomeSizePI[category];

        // create an array of hh indices (0,...,number of regional households - 1)
        // sorted randomly to control the order in which households are allocated zones
        int[] tempData = new int[numHouseholds];
        for (int i=0; i < numHouseholds; i++)
            tempData[i] = (int)(randomGen.nextDouble()*1000000000);

        int[] hhOrder = IndexSort.indexSort(tempData);
        tempData = null;



        String[] values = new String[numHouseholds];

        // go through the list of households randomly and allocate them to zones.
        for (int h=0; h < hhOrder.length; h++) {

            
            try {
          
                // get the indices into the hhArray for a household drawn at random
                int hhIndex = getHouseholdIndex ( category, hhOrder[h] );

                // get the hh attributes
                int[] hhAttribs = hhArray[category][hhIndex];
                int hhSize = hhAttribs[NUM_PERSONS_ATTRIB_INDEX];
                int incomeSize = category;

                int unallocatedRegionalHHs = (origHHsIncomeSizePI[incomeSize] - hhsAllocatedRegion[incomeSize]);

                // if household has any employeed persons, use labor$ for those occupation categories to allocate hh to alpha zone
                if ( hhAttribs[NUM_WORKERS_ATTRIB_INDEX] > 0 ) {
                    
                    // get the occupations of each person in this household
                    int[] personOccupations = new int[hhSize];
                    for (int j=0; j < hhSize; j++)
                        personOccupations[j] = hhAttribs[PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 1];
                    
                    // candidateZoneInfo[0] - double[] zone indices, candidateZoneInfo[1] - double[] cumulative zone probabilities  
                    double[][] candidateZoneInfo = getCandidateZonesAndProbabilitiesForEmployedHHOnLaborDollars ( personOccupations, incomeSize, unallocatedRegionalHHs);
                    
                    if ( candidateZoneInfo == null ) {
                        candidateZoneInfo = getCandidateZonesAndProbabilitiesOnHouseholds ( incomeSize );
                        employedCount0++;
                    }
                    else {
                        employedCount++;
                    }
                    
                    
                    // get the selected zone from the probabilities

                    int probArrayIndex = getSelectionFromCumProbabilities(candidateZoneInfo[1], randomGen);
                    selectedIndex = (int)candidateZoneInfo[0][probArrayIndex];
                    selectedZone = indexZone[selectedIndex];

                    
                    int unallocated = (origHHsZoneIncomeSizePI[selectedIndex][incomeSize] - hhsAllocated[selectedIndex][incomeSize]);
                    if ( unallocated < 0 ) {
                        logger.warn ( String.format("too many hhs assigned to zone %d, hhcategory %d", selectedIndex, incomeSize) );
                    }
                    
                    
                    // reduce labor$ in selected zone in each person's occupation category by mean labor$/job.
                    for (int j=0; j < hhSize; j++) {
                        int occup = personOccupations[j];
                        if (occup > 0) {
                            if ( unallocatedLaborDollarsPI[selectedIndex][occup][incomeSize] < regionLaborDollarsPerJob[occup][incomeSize] )
                                reduction = unallocatedLaborDollarsPI[selectedIndex][occup][incomeSize];
                            else
                                reduction = regionLaborDollarsPerJob[occup][incomeSize];
                            unallocatedLaborDollarsPI[selectedIndex][occup][incomeSize] -= reduction;


                            regionLaborDollars[occup][incomeSize] -= reduction;
                        }
                    }
                    
                    // increase number of hhs allocated in zone and income/size category
                    hhsAllocated[selectedIndex][incomeSize] ++;
                    hhsAllocatedRegion[incomeSize] ++;
                    
                    employedTotal++;
                    
                }
                else {
                    // this was an unemployed hh
                        
                    double[][] candidateZoneInfo = getCandidateZonesAndProbabilitiesOnHouseholds ( incomeSize );
                    
                    // get the selected zone from the probabilities
                    int probArrayIndex = getSelectionFromCumProbabilities(candidateZoneInfo[1], randomGen);
                    selectedIndex = (int)candidateZoneInfo[0][probArrayIndex];
                    selectedZone = indexZone[selectedIndex];

                    
                    
                    int unallocated = (origHHsZoneIncomeSizePI[selectedIndex][incomeSize] - hhsAllocated[selectedIndex][incomeSize]);
                    if ( unallocated < 0 ) {
                        logger.warn ( String.format("too many hhs assigned to zone %d, hhcategory %d", selectedIndex, incomeSize) );
                    }
                    
                    
                    // increase number of hhs allocated in zone and income/size category
                    hhsAllocated[selectedIndex][incomeSize] ++;
                    hhsAllocatedRegion[incomeSize] ++;
                        
                    unemployedTotal++;
                    
                }

                // save zonal summary information
                accumulateZonalSummaryArrays ( hhAttribs, selectedZone );
                // write zonal summary fields

                // save the selected zone with the pums state and record number so they can be written to a file.
                values[count] = String.format( "%d,%d,%d", hhAttribs[HHID_INDEX], halo.getStateIndex(hhAttribs[STATE_ATTRIB_INDEX]), selectedZone );
                count++;

            }
            catch (Exception e){
                logger.fatal ( String.format( "Exception caught processing household=%d, h=%d of %d, category=%d.", count, h, hhOrder.length, category ), e );
                throw new RuntimeException ();
            }
        }
        
        logger.info( String.format("%d households processed for category %d: %s.", values.length, category, categoryLabel) );

        return values;
        
    }
    
    
    public int binarySearchInt (int[] cumFrequencies, int entry) {
        
        // lookup index for cumFrequencies[0] <= entry < cumFrequencies[cumFequencies.length-1]
    
    
        int hi = cumFrequencies.length;
        int lo = 0;
        int mid = (hi -lo)/2;
        
        int safetyCount = 0;
        
    
        // if mid is 0, 
        if ( mid == 0 ) {
            if ( entry < cumFrequencies[0] )
                return 0;
            else
                return 1;
        }
        else if ( entry < cumFrequencies[mid] && entry >= cumFrequencies[mid-1] ) {
            return mid;
        }
    
        
        while (true) {
        
            if ( entry < cumFrequencies[mid] ) {
                hi = mid;
                mid = (hi + lo)/2;
            }
            else {
                lo = mid;
                mid = (hi + lo)/2;
            }
    
            
            // if mid is 0, 
            if ( mid == 0 ) {
                if ( entry < cumFrequencies[0] )
                    return 0;
                else
                    return 1;
            }
            else if ( entry < cumFrequencies[mid] && entry >= cumFrequencies[mid-1] ) {
                return mid;
            }
        
            
            if ( safetyCount++ > cumFrequencies.length ) {
                logger.error ( "binary search stuck in the while loop" );
                throw new RuntimeException();
            }
                
        }
        
    }


    private double[][] getCandidateZonesAndProbabilitiesForEmployedHHOnLaborDollars ( int[] personOccupations, int incomeSize, int unallocatedRegionalHHs) {
        
        double density = 0.0;
        double cumDensity = 0.0;
        int[] zones = new int[indexZone.length];
        double[] probs = new double[indexZone.length];
        
        int count = 0;
        for (int i=0; i < indexZone.length; i++) {
            
            // determine zonal density and total density
            int unallocatedZonalHHs = origHHsZoneIncomeSizePI[i][incomeSize] - hhsAllocated[i][incomeSize];

            if ( unallocatedZonalHHs > 0 ) {

                // initialize zone density to relative number of unallocated households.
                density = (double)unallocatedZonalHHs/unallocatedRegionalHHs;
                // if labor$ remain for every occupation in household, update density; otherwise zone is not available.
                for (int j=0; j < personOccupations.length; j++) {
                    int occup = personOccupations[j];
                    if ( occup > 0) {
                        if ( unallocatedLaborDollarsPI[i][occup][incomeSize] > 0.0 ) {
                            density *= ( unallocatedLaborDollarsPI[i][occup][incomeSize]/regionLaborDollars[occup][incomeSize] );
                        }
                        else {
                            density = -1.0;
                            break;
                        }

                    }
                }

                
                // if density value is > 0, then unallocated labor$ for each occupation in the household remain; add zone and probability to candidate list
                if ( density > 0 ) {
                    zones[count] = i;
                    probs[count] = density;
                    count++;
                    cumDensity += density;
                }

            }
            
        }

        
        if ( count == 0 )
            return null;
        
        
        double[][] returnArray = getZonesAndProbabilitiesArrays ( zones, probs, cumDensity, count );
        
        return returnArray;
        
    }

    
    
    
    private double[][] getCandidateZonesAndProbabilitiesOnHouseholds ( int incomeSize ) {
        
        double density = 0.0;
        double cumDensity = 0.0;
        int[] zones = new int[indexZone.length];
        double[] probs = new double[indexZone.length];
        
        int count = 0;
        for (int i=0; i < indexZone.length; i++) {
            
            // determine zonal density and total density
            int unallocatedZonalHHs = origHHsZoneIncomeSizePI[i][incomeSize] - hhsAllocated[i][incomeSize];
            
            if ( unallocatedZonalHHs > 0 ) {

                // initialize zone density to relative number of unallocated households.
                density = (double)origHHsZoneIncomeSizePI[i][incomeSize]/origHHsIncomeSizePI[incomeSize];

                // if density value is > 0, then the zone is a candidate; add zone and probability to candidate list
                if ( density > 0 ) {
                    zones[count] = i;
                    probs[count] = density;
                    count++;
                    cumDensity += density;
                }

            }
            
        }
        
        double[][] returnArray = getZonesAndProbabilitiesArrays ( zones, probs, cumDensity, count );
        
        return returnArray;
        
    }
    

    // get arrays of candidate zone indices and corresponding cumulative probabilities from the candidate zones and probs lists
    private double[][] getZonesAndProbabilitiesArrays ( int[] zones, double[] probs, double cumDensity, int count ) {

        double[] candidateZones = new double[count];
        double[] cumProb = new double[count];
        
        cumProb[0] = probs[0]/cumDensity;
        candidateZones[0] = zones[0];
        for (int i=1; i < count-1; i++) {
            cumProb[i] = cumProb[i-1] + probs[i]/cumDensity;;
            candidateZones[i] = zones[i];
        }
        cumProb[count-1] = 1.0;
        candidateZones[count-1] = zones[count-1];
        
        double[][] returnArray = new double[2][];
        returnArray[0] = candidateZones;
        returnArray[1] = cumProb;
        
        return returnArray;
        
    }
    

    
    
    // write the contents of the hhArray array computed in SPG1 to disk so it can read back in
    // and used in SPG2.
    private void writeHhArray () {
        
        try {
            FileOutputStream out = new FileOutputStream( (String)spgPropertyMap.get("spg1.hh.disk.object") );
            ObjectOutputStream s = new ObjectOutputStream(out);
            s.writeObject(hhArray);
            s.flush();
        }
        catch (IOException e) {
            logger.fatal("IO Exception when writing hhArray file: " + (String)spgPropertyMap.get("spg1.hh.disk.object"), e );
        }

    }
    
    

    // read the hhArray array computed in SPG1 so it can be used in SPG2.
    private void readHhArray () {

        try{
            FileInputStream in = new FileInputStream( (String)spgPropertyMap.get("spg1.hh.disk.object") );
            ObjectInputStream s = new ObjectInputStream(in);
            hhArray = (int[][][])s.readObject();
        }catch(IOException e){
            logger.fatal("IO Exception when reading hhArray file: " + spgPropertyMap.get("spg1.hh.disk.object"), e );
        }catch(ClassNotFoundException e){
            logger.fatal("Class Not Found Exception when reading hhArray file: " + spgPropertyMap.get("spg1.hh.disk.object"), e );
        }

    }
    
    

    // for a household index selected at random from [0,...,total number of hhs in hh category - 1],  
    // determine the index into hhArray[][][].
    private int getHouseholdIndex ( int hhCategory, int hhIndex ) {

        // the number of expanded households for PUMS hh 0 is in hhSelectedIndexArray[1], so return looked-up number - 1. 
        int returnValue = binarySearchInt( hhSelectedIndexArray[hhCategory], hhIndex ) - 1;
                    
        return returnValue;
    }
    

    
    // initialize the sample observed employment values, employment controls, 
    // household controls, and hhWeights.
    private void initializeTableBalancingArrays ( int numPUMSHouseholds, int numPUMSWorkers, int numPUMSPersons, int[] employmentTargets, int[] personAgeTargets) {

        int i = 0;
        int j = 0;
        int k = 0;
        int hhid = 0;
        int numPersons;
        int numWorkers;
        int workersCode;
        int hhSizeCode;
        int pumsIndustryCode = 0;
        int industryCode = 0;
        int employmentStatusCode = 0;
        int pumsHHWeight;
        

        hhWeights = new double[numPUMSHouseholds];

        int numEmploymentCategories = ind.getNumberIndustries();
        employmentControlTotals = new double[numEmploymentCategories];
        observedEmployment = new double[numPUMSHouseholds][numEmploymentCategories];
        employmentControls = new double[numPUMSHouseholds][numEmploymentCategories];

        int numWorkerCategories = workers.getNumberWorkerCategories();
        hhWorkerControlTotals = new double[numWorkerCategories];
        observedHhWorkers = new double[numPUMSHouseholds][numWorkerCategories];
        hhWorkerControls = new double[numPUMSHouseholds][numWorkerCategories];
        
        // update all hh size controls for this household, if they are used
        if ( hhSizeTargets != null ) {
            int numHhSizeCategories = hhsize.getNumberHhSizeCategories();
            hhSizeControlTotals = new double[numHhSizeCategories];
            observedHhSize = new double[numPUMSHouseholds][numHhSizeCategories];
            hhSizeControls = new double[numPUMSHouseholds][numHhSizeCategories];
        }

        if (personAge.isEnabled()) {
            int numPersonAgeCategories = personAge.getAgeRanges().length;
            personAgeControlTotals = new double[numPersonAgeCategories];
            observedPersonAge = new double[numPUMSHouseholds][numPersonAgeCategories];
            personAgeControls = new double[numPUMSHouseholds][numPersonAgeCategories];
        }
        
        // calculate initial hhWeight
        float totalRegionalJobs = 0;
        for (i=0; i < employmentTargets.length; i++)
            totalRegionalJobs += employmentTargets[i];
        
        double hhWeight = totalRegionalJobs/numPUMSWorkers;

        double personAgeHHWeight = 0;
        if (personAge.isEnabled()) {
            double totalPopulation = 0;
            for (int p : personAgeTargets)
                totalPopulation += p;
            personAgeHHWeight = totalPopulation / numPUMSPersons;
        }
        
        
        
        try { 
            
            
            // loop over stored hh records with PUMS data
            for (i=0; i < hhArray.length; i++) {
    
                // loop over household records for this state
                for (k=0; k < hhArray[i].length; k++) {
                
                    pumsHHWeight = hhArray[i][k][HH_WEIGHT_ATTRIB_INDEX];
                    numPersons = hhArray[i][k][NUM_PERSONS_ATTRIB_INDEX];
                    numWorkers = hhArray[i][k][NUM_WORKERS_ATTRIB_INDEX];
                    workersCode = workers.getWorkers(numWorkers); 
            
                    // set the initial hhWeights for each hh
                    hhWeights[hhid] = hhWeight; 
    
                    
                    // set the fixed observed number of workers in this hh
                    observedHhWorkers[hhid][workersCode] = pumsHHWeight;
                    hhWorkerControls[hhid][workersCode] = hhWeight*pumsHHWeight;
                    hhWorkerControlTotals[workersCode] += hhWeight*pumsHHWeight;
                    
                    // update all hh size controls for this household, if they are used
                    if ( hhSizeTargets != null ) {
                        hhSizeCode = hhsize.getHhSize(numPersons);
                        observedHhSize[hhid][hhSizeCode] = pumsHHWeight;
                        hhSizeControls[hhid][hhSizeCode] = hhWeight*pumsHHWeight;
                        hhSizeControlTotals[hhSizeCode] += hhWeight*pumsHHWeight;
                    }
    
                    // loop through person attributes for this household 
                    int workerCount = 0;
                    for (j=0; j < numPersons; j++) {
                        
                        // check employment status of person
                        employmentStatusCode = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 2];
                        if ( employmentStatusCode > 0 && workerCount < numWorkerCategories-1 ) {
                            //                           ^^-------------------------------^^--what is this for? doesn't make sense
                            
                            // set the fixed observed employment value for employment category of this worker
                            pumsIndustryCode = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 0];
                            industryCode = pumsIndustryCode;
                            observedEmployment[hhid][industryCode] += pumsHHWeight;
                            employmentControls[hhid][industryCode] += hhWeight*pumsHHWeight;
                            employmentControlTotals[industryCode] += hhWeight*pumsHHWeight;
                            
                            workerCount++;
    
                        }


                        if (personAge.isEnabled()) {
                            int ageIndex = personAge.getAgeCategoryIndex(hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 4]);
                            observedPersonAge[hhid][ageIndex] += pumsHHWeight;
                            personAgeControls[hhid][ageIndex] += personAgeHHWeight*pumsHHWeight;
                            personAgeControlTotals[ageIndex] += personAgeHHWeight*pumsHHWeight;
                        }
                        
                    }
                    
                    hhid++;
    
                }
            }

        }
        catch (Exception e) {
            
            logger.error( "Exception caught in SPGnew.initializeTableBalancingArrays(), i=" + i + ", j=" + j + ", k=" + k + ", hhid=" + hhid, e );
            
        }
    }
    

    
    
    // initialize the sample observed employment values, employment controls, 
    // household controls, and hhWeights.
    private boolean updateTableBalancingArrays ( ) {

        int hhid = 0;
        double balancingFactor = 0.0;

/**
 * use thes statements in debugging as sanity check, but they're not needed in model implementation

        int totalTargetWorkers = 0;
        for (int i=1; i < hhWorkerTargets.length; i++) {
            totalTargetWorkers += i*hhWorkerTargets[i];
        }
        
        // it's possible that no hh size targets were specified, and spg1 will balance on employment and workers per hh only (original model spec). 
        int totalTargetPersons = 0;
        if ( hhSizeTargets != null ) {
            for (int i=1; i < hhSizeTargets.length; i++) {
                totalTargetPersons += i*hhSizeTargets[i];
            }
        }
        
        float totalTargetEmployees = 0;
        for (int i=0; i < employmentTargets.length; i++) {
            totalTargetEmployees += employmentTargets[i];
        }
 */        

        

        //loop over each employment control
        for (int i=0; i < employmentControlTotals.length; i++) {
            
            // if marginal total for this control is not positive, skip update
            if ( employmentTargets[i] <= 0.0 || employmentControlTotals[i] <= 0.0 )
                continue;
            
            // calculate new hhWeight for this control
            balancingFactor = employmentTargets[i]/employmentControlTotals[i];
            
            
            // update the hhWeights for any hh with a worker in the current employment category
            double totalOldWeighted = 0.0;
            double totalNewWeighted = 0.0;
            for (hhid=0; hhid < observedEmployment.length; hhid++) {
                
                if ( observedEmployment[hhid][i] > 0 ) {
                    totalOldWeighted += observedEmployment[hhid][i]*hhWeights[hhid];
                    hhWeights[hhid] *= employmentTargets[i];
                    hhWeights[hhid] /= employmentControlTotals[i];
                    totalNewWeighted += observedEmployment[hhid][i]*hhWeights[hhid];
                }

            }

            oldEmpFactors[i] = balancingFactor;
            
            // update all controls based on this new balancing factor
            updateControls();
            
        }



        if (personAge.isEnabled()) {
            for (int i=0; i < personAgeControlTotals.length; i++) {

                // if marginal total for this control is not positive, skip update
                if (personAgeTargets[i] <= 0.0 || personAgeControlTotals[i] <= 0.0 )
                    continue;

                // calculate new hhWeight for this control
                balancingFactor = personAgeTargets[i]/personAgeControlTotals[i];

                // update the hhWeights for each person age category
                for (hhid=0; hhid < observedPersonAge.length; hhid++)
                    if ( observedPersonAge[hhid][i] > 0 )
                        hhWeights[hhid] *= balancingFactor;

                // update all controls based on this new balancing factor
                updateControls();

            }
        }
        

    
    
        //loop over each hh worker control
        for (int i=0; i < hhWorkerControlTotals.length; i++) {
            
            // if marginal total for this control is not positive, skip update
            if ( hhWorkerTargets[i] <= 0.0 || hhWorkerControlTotals[i] <= 0.0 )
                continue;
            
            // calculate new hhWeight for this control
            balancingFactor = hhWorkerTargets[i]/hhWorkerControlTotals[i];
            
            
            // update the hhWeights for any hh with a worker in the current employment category
            for (hhid=0; hhid < observedHhWorkers.length; hhid++) {
                
                if ( observedHhWorkers[hhid][i] > 0 ) {
                    hhWeights[hhid] *= hhWorkerTargets[i];
                    hhWeights[hhid] /= hhWorkerControlTotals[i];
                }
                
                
            }

            oldHhFactors[i] = balancingFactor;
            
            // update all controls based on this new balancing factor
            updateControls();
            
        }
        
        
        
        //loop over each hh persons control, if any were defined
        if ( hhSizeTargets != null ) {
            
            for (int i=0; i < hhSizeControlTotals.length; i++) {
                
                // if marginal total for this control is not positive, skip update
                if ( hhSizeTargets[i] <= 0.0 || hhSizeControlTotals[i] <= 0.0 )
                    continue;
                
                // calculate new hhWeight for this control
                balancingFactor = hhSizeTargets[i]/hhSizeControlTotals[i];
                
                
                // update the hhWeights for any hh with a worker in the current employment category
                for (hhid=0; hhid < observedHhSize.length; hhid++) {
                    
                    if ( observedHhSize[hhid][i] > 0 ) {
                        hhWeights[hhid] *= hhSizeTargets[i];
                        hhWeights[hhid] /= hhSizeControlTotals[i];
                    }
                    
                    
                }
    
                oldHhFactors[i] = balancingFactor;
                
                // update all controls based on this new balancing factor
                updateControls();
                
            }
        
        }
        
        
        logger.info( "Balancing Factor Difference for iteration " + balancingCount + " =  " + String.format("%18.8f", Math.abs( 1.0 - balancingFactor ) ) );

        StatusLogger.logGraph("spg1.balancing","SPG1 Status: Table Balancing",balancingCount,Math.abs( 1.0 - balancingFactor ),"Iteration","Convergence Factor");

        
        balancingCount++;
        
        // check for convergence and return
        double maxDiff = 0.0;
        double maxEDiff = 0.0;
        double maxHDiff = 0.0;
        for (int i=0; i < employmentTargets.length; i++) {
            if ( Math.abs(employmentControlTotals[i] - employmentTargets[i]) > maxEDiff )
                maxEDiff = Math.abs(employmentControlTotals[i] - employmentTargets[i]);
        }
        for (int i=0; i < hhWorkerTargets.length; i++) {
            if ( Math.abs(hhWorkerControlTotals[i] - hhWorkerTargets[i]) > maxHDiff )
                maxHDiff = Math.abs(hhWorkerControlTotals[i] - hhWorkerTargets[i]);
        }
        maxDiff = Math.max(maxEDiff, maxHDiff);

        if ( hhSizeTargets != null ) {
            double maxSDiff = 0.0;
            for (int i=0; i < hhSizeTargets.length; i++) {
                if ( Math.abs(hhSizeControlTotals[i] - hhSizeTargets[i]) > maxSDiff )
                    maxSDiff = Math.abs(hhSizeControlTotals[i] - hhSizeTargets[i]);
            }
            maxDiff = Math.max(maxSDiff, maxDiff);
        }

        if (personAge.isEnabled()) {
            double maxPDiff = 0.0;
            for (int i=0; i < personAgeTargets.length; i++) {
                if ( Math.abs(personAgeControlTotals[i] - personAgeTargets[i]) > maxPDiff )
                    maxPDiff = Math.abs(personAgeControlTotals[i] - personAgeTargets[i]);
            }
            maxDiff = Math.max(maxPDiff,maxDiff);
        }
        

        
        return ( maxDiff > MAXIMUM_ALLOWED_CONTROL_DIFFERENCE  && balancingCount < MAX_BALANCING_ITERATION );
        
    }
    

    
    
    private void updateControls () {

        // initialize control total arrays
        for (int i=0; i < employmentControlTotals.length; i++)
            employmentControlTotals[i] = 0.0;

        if (personAge.isEnabled()) {
            for (int i=0; i < personAgeControlTotals.length; i++)
                 personAgeControlTotals[i] = 0.0;
        }

        for (int i=0; i < hhWorkerControlTotals.length; i++)
            hhWorkerControlTotals[i] = 0.0; 

        // no need to update hhsize controls if no targets were specified
        if ( hhSizeTargets != null ) {
            for (int i=0; i < hhSizeControlTotals.length; i++)
                hhSizeControlTotals[i] = 0.0; 
        }
        
        
        // loop over all households
        for (int hhid=0; hhid < observedEmployment.length; hhid++) {

            // update all employment controls for this household
            for (int j=0; j < observedEmployment[hhid].length; j++) {
                employmentControls[hhid][j] = observedEmployment[hhid][j] * hhWeights[hhid];
                employmentControlTotals[j] += employmentControls[hhid][j]; 
            }

            if (personAge.isEnabled()) {
                for (int j=0; j < observedPersonAge[hhid].length; j++) {
                    personAgeControls[hhid][j] = observedPersonAge[hhid][j] * hhWeights[hhid];
                    personAgeControlTotals[j] += personAgeControls[hhid][j];
                }
            }
            
            // update all hh worker controls for this household
            for (int j=0; j < observedHhWorkers[hhid].length; j++) {
                hhWorkerControls[hhid][j] = observedHhWorkers[hhid][j] * hhWeights[hhid];               
                hhWorkerControlTotals[j] += hhWorkerControls[hhid][j]; 
            }
        
            // update all hh size controls for this household, if they are used
            if ( hhSizeTargets != null ) {
                for (int j=0; j < observedHhSize[hhid].length; j++) {
                    hhSizeControls[hhid][j] = observedHhSize[hhid][j] * hhWeights[hhid];               
                    hhSizeControlTotals[j] += hhSizeControls[hhid][j]; 
                }
            }
        
        }

        
    }

    private int getTotalPumsPersons() {
        int persons = 0;
        for (int[][] hhSubArray : hhArray)
            for (int[] hh : hhSubArray)
                persons += hh[NUM_PERSONS_ATTRIB_INDEX]*hh[HH_WEIGHT_ATTRIB_INDEX];
        return persons;
    }
            
                
            
    // count the total number of workers in the PUMS sample
    // return an int[] wher the zero element has total sample workers
    // and the ones element has total weighted workers.
    public int[] getTotalWorkers () {

        int w;
        int[] workerBins = new int[workers.getNumberWorkerCategories()];
        
        int[] numWorkers = new int[2];
        
        for (int i=0; i < hhArray.length; i++) {
            for (int k=0; k < hhArray[i].length; k++) {
                numWorkers[0] += hhArray[i][k][NUM_WORKERS_ATTRIB_INDEX];
                numWorkers[1] += ( hhArray[i][k][NUM_WORKERS_ATTRIB_INDEX]*hhArray[i][k][HH_WEIGHT_ATTRIB_INDEX] );
                w = hhArray[i][k][NUM_WORKERS_ATTRIB_INDEX];
                if ( w > workers.getNumberWorkerCategories()-1 )
                    w = workers.getNumberWorkerCategories()-1;
                workerBins[w]++;
            }
        }
        
        return numWorkers;
    }
    
    
    
    
    // count the number of unique PUMS household records in the hhArray over all states
    private int getTotalPumsHouseholds () {
        
        int numHouseholds = 0;
        for (int i=0; i < hhArray.length; i++)
            numHouseholds += hhArray[i].length;
        
        return numHouseholds;
        
    }
    
    

    // create a lookup table of hhArray index values for hhids.
    private void setupHouseholdIndexLookupArray ( int[] maxHhIndices ) {
        
        hhSelectedIndexArray = new int[hhArray.length][];

        int numHouseholds = 0;
        int totalHouseholds = 0;
        for (int i=0; i < hhArray.length; i++) {
            
            hhSelectedIndexArray[i] = new int[hhArray[i].length+1];
            hhSelectedIndexArray[i][0] = 0;
            for (int j=0; j < hhArray[i].length; j++) { 
                numHouseholds = ( hhArray[i][j][HH_SELECTED_INDEX] + hhArray[i][j][HH_UNEMPLOYED_INDEX] );
                hhSelectedIndexArray[i][j+1] = hhSelectedIndexArray[i][j] + numHouseholds;
                totalHouseholds += numHouseholds;
            }
            
            if ( hhSelectedIndexArray[i][hhArray[i].length] != origHHsIncomeSizePI[i] ) {
                
                if ( Math.abs(hhSelectedIndexArray[i][hhArray[i].length] - origHHsIncomeSizePI[i]) == 1 ) {
                    int delta = hhSelectedIndexArray[i][hhArray[i].length] - origHHsIncomeSizePI[i];
                    int k = maxHhIndices[i];
                    origHHsZoneIncomeSizePI[k][i] += delta;
                    origHHsIncomeSizePI[i] += delta;
                    origRegionalHHs += delta;
                }
                else {
                    RuntimeException e = new RuntimeException( String.format("incomesize category %d total hhs in hhArray: %d not equal to hhs in origHHsIncomeSizePI: %d.", i, hhSelectedIndexArray[i][hhArray[i].length], origHHsIncomeSizePI[i]) );
                    throw e;
                }
                
            }
            
        }
        
    }

    protected static boolean useAcs(Map spgPropertyMap) {
        return spgPropertyMap.containsKey(USE_ACS_FLAG_PROPERTY) && ((String) spgPropertyMap.get(USE_ACS_FLAG_PROPERTY)).toLowerCase().equals("true");
    }

    public void getHHAttributeData(String baseYear) {
        if (useAcs(spgPropertyMap))
            getHHAttributesFromACS(baseYear);
        else
            getHHAttributesFromPUMS(baseYear);
    }

    public static final String PUMS_HH_SELECTED_INDUSTRY_FILE_PROPERTY = "pums.hh.selected.industry.file";

    // get the set of hh attributes needed for SPG1 from PUMS files
    public void getHHAttributesFromPUMS ( String baseYear ) {
        
        ArrayList hhList = new ArrayList();
        
        // make an ArrayList[] to hold hh records by hh category, to be transferred later to hhArray.
        ArrayList[] hhCategoryHhList = new ArrayList[incSize.getNumberIncomeSizes()];
        for ( int i=0; i < hhCategoryHhList.length; i++ )
            hhCategoryHhList[i] = new ArrayList();
        
        
        // hhArray is the int[][][] that will hold all PUMS reecord info
        hhArray = new int[incSize.getNumberIncomeSizes()][][];

        
        SpgPumsData pums = new SpgPumsData ( (String)spgPropertyMap.get("pums.dictionary"), baseYear, ind, occ, workers );
        
        String propertyName;
        String[] PUMSFILE = new String[halo.getNumberOfStates()];
        for (int i=0; i < PUMSFILE.length; i++) {
            propertyName = "pums" + halo.getStateLabel(i) + ".fileName";
            PUMSFILE[i] = (String)spgPropertyMap.get( propertyName );
        }

        // create a HashMap of field names to use based on those specified in properties file
        HashMap fieldNameMap = new HashMap();
        fieldNameMap.put( "hhIdField", globalPropertyMap.get( "pums.hhIdField.name" ) );
        fieldNameMap.put( "pumaName", globalPropertyMap.get( "pums.pumaField.name" ) );
        fieldNameMap.put( "stateName", globalPropertyMap.get( "pums.stateField.name" ) );
        fieldNameMap.put( "personsName", globalPropertyMap.get( "pums.personsField.name" ) );
        fieldNameMap.put( "hhWeightName", globalPropertyMap.get( "pums.hhWeightField.name" ) );
        fieldNameMap.put( "hhIncName", globalPropertyMap.get( "pums.hhIncomeField.name" ) );
        fieldNameMap.put( "industryName", globalPropertyMap.get( "pums.industryField.name" ) );
        fieldNameMap.put( "occupationName", globalPropertyMap.get( "pums.occupationField.name" ) );
        fieldNameMap.put( "personAgeName", globalPropertyMap.get( "pums.ageField.name" ) );
        fieldNameMap.put( "empStatName", globalPropertyMap.get( "pums.empStatField.name" ) );
        fieldNameMap.put( "personWeightName", globalPropertyMap.get( "pums.personWeightField.name" ) );

        boolean usingPumsSplitIndustry = globalPropertyMap.containsKey(PumsToSplitIndustry.PUMS_TO_SPLIT_INDUSTRY_FILE_PROPERTY);
        PumsToSplitIndustry pumsToSplitIndustry = null;
        PrintWriter pw = null;
        if (usingPumsSplitIndustry) {
            pumsToSplitIndustry = new PumsToSplitIndustry(globalPropertyMap);
            try {
                pw = new PrintWriter(PUMS_HH_SELECTED_INDUSTRY_FILE_PROPERTY);
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        }

        
        for (int i=0; i < halo.getNumberOfStates(); i++) {
            
            // form the list of hh record arrays SPG needs from the state PUMS files
            logger.info ( "reading " + halo.getStateLabel(i) + " PUMS data file ...");
            hhList = pums.setSpg1Attributes(i,PUMSFILE[i],halo,fieldNameMap,pumsToSplitIndustry);
            logger.info ( hhList.size() + " total household records read from " + halo.getStateLabel(i) + " PUMS data file." ); 

            // save the hh records for the state into the appropriate list based on hh category
            for (int k=0; k < hhList.size(); k++) {
                int[] hhRecord = (int[])hhList.get(k);
                int hhCategory = incSize.getIncomeSize(hhRecord[HH_INCOME_ATTRIB_INDEX], hhRecord[NUM_PERSONS_ATTRIB_INDEX]); 
                hhCategoryHhList[hhCategory].add( hhRecord );
                if (usingPumsSplitIndustry) {
                    //record selected industry for each person
                    int persons = hhRecord[NUM_PERSONS_ATTRIB_INDEX];
                    for (int p = 0; p < persons; p++) {
                        int id = hhRecord[HHID_INDEX];
                        int ind = hhRecord[PERSON_ARRAY_ATTRIB_INDEX + i*SPG.NUM_PERSON_ATTRIBUTES];
                        pw.println(i + " " + id + " " + p + " " + ind);
                    }
                }
            }
        }

        //close hh->industry file
        if (usingPumsSplitIndustry)
            pw.close();
        
        
        // transfer hhRecords from hhCategoryHhList[] to the hhArray[][][].
        for ( int i=0; i < hhCategoryHhList.length; i++ ) {
      
            hhArray[i] = new int[hhCategoryHhList[i].size()][];
            for ( int k=0; k < hhArray[i].length; k++ )
                hhArray[i][k] = (int[])hhCategoryHhList[i].get(k);
            
        }
        
    }

    protected void getHHAttributesFromACS(String baseYear) {

        ArrayList hhList;

        // make an ArrayList[] to hold hh records by hh category, to be transferred later to hhArray.
        ArrayList[] hhCategoryHhList = new ArrayList[incSize.getNumberIncomeSizes()];
        for ( int i=0; i < hhCategoryHhList.length; i++ )
            hhCategoryHhList[i] = new ArrayList();

        // hhArray is the int[][][] that will hold all PUMS (ACS equivalent) record info
        hhArray = new int[incSize.getNumberIncomeSizes()][][];

        SpgAcsData acsData = new SpgAcsData();

        // create a HashMap of field names to use based on those specified in properties file
        HashMap fieldNameMap = new HashMap();
        //hh
        fieldNameMap.put("hhIdField", globalPropertyMap.get("acs.hhIdField.name"));
        fieldNameMap.put("pumaName", globalPropertyMap.get("acs.pumaField.name"));
        fieldNameMap.put("stateName", globalPropertyMap.get("acs.stateField.name"));
        fieldNameMap.put("personsName", globalPropertyMap.get("acs.personsField.name"));
        fieldNameMap.put("hhWeightName", globalPropertyMap.get("acs.hhWeightField.name"));
        fieldNameMap.put("hhIncName", globalPropertyMap.get("acs.hhIncomeField.name"));
        //person
        fieldNameMap.put("industryName", globalPropertyMap.get("acs.industryField.name"));
        fieldNameMap.put("occupationName", globalPropertyMap.get("acs.occupationField.name"));
        fieldNameMap.put("personAgeName", globalPropertyMap.get("acs.ageField.name"));
        fieldNameMap.put("empStatName", globalPropertyMap.get("acs.empStatField.name"));
        fieldNameMap.put("personWeightName", globalPropertyMap.get("acs.personWeightField.name"));

        List<String> hhNumericAttributes = new LinkedList<String>();
        List<String> hhStringAttributes = new LinkedList<String>();
        List<String> personNumericAttributes = new LinkedList<String>();
        List<String> personStringAttributes = new LinkedList<String>();

        hhStringAttributes.add((String) fieldNameMap.get("hhIdField"));
        hhNumericAttributes.add((String) fieldNameMap.get("pumaName"));
        hhNumericAttributes.add((String) fieldNameMap.get("stateName"));
        hhNumericAttributes.add((String) fieldNameMap.get("personsName"));
        hhNumericAttributes.add((String) fieldNameMap.get("hhWeightName"));
        hhNumericAttributes.add((String) fieldNameMap.get("hhIncName"));

        personStringAttributes.add((String) fieldNameMap.get("hhIdField")); //need to add this to have back reference - don't think it will cause problem...
        personNumericAttributes.add((String) fieldNameMap.get("personAgeName"));
        personNumericAttributes.add((String) fieldNameMap.get("empStatName"));
        personNumericAttributes.add((String) fieldNameMap.get("personWeightName"));
        personNumericAttributes.add((String) fieldNameMap.get("industryName"));
        personNumericAttributes.add((String) fieldNameMap.get("occupationName"));

        boolean usingPumsSplitIndustry = globalPropertyMap.containsKey(PumsToSplitIndustry.PUMS_TO_SPLIT_INDUSTRY_FILE_PROPERTY);
        PumsToSplitIndustry pumsToSplitIndustry = null;
        PrintWriter pw = null;
        if (usingPumsSplitIndustry) {
            pumsToSplitIndustry = new PumsToSplitIndustry(globalPropertyMap);
            try {
                pw = new PrintWriter((String)globalPropertyMap.get(PUMS_HH_SELECTED_INDUSTRY_FILE_PROPERTY));
//                pw = new PrintWriter((new BufferedWriter(new OutputStreamWriter(new FileOutputStream(PUMS_HH_SELECTED_INDUSTRY_FILE_PROPERTY)))),false);
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        }

        if (globalPropertyMap.containsKey(PumsToSplitIndustry.PUMS_TO_SPLIT_INDUSTRY_FILE_PROPERTY))
            pumsToSplitIndustry = new PumsToSplitIndustry(globalPropertyMap);

        for (int i=0; i < halo.getNumberOfStates(); i++) {
            TableDataSet[] datas = getNormalizedAcsHHAndPersonData(i,fieldNameMap,hhNumericAttributes,hhStringAttributes,personNumericAttributes,personStringAttributes);


            hhList = SpgPumsData.setSpg1AttributesFromData(datas[0],datas[1],fieldNameMap,baseYear,ind,occ,workers,pumsToSplitIndustry);
            logger.info ( hhList.size() + " total household records read from " + halo.getStateLabel(i) + " PUMS data file." );

            // save the hh records for the state into the appropriate list based on hh category
            for (int k=0; k < hhList.size(); k++) {
                int[] hhRecord = (int[])hhList.get(k);
                int hhCategory = incSize.getIncomeSize(hhRecord[HH_INCOME_ATTRIB_INDEX], hhRecord[NUM_PERSONS_ATTRIB_INDEX]);
                hhCategoryHhList[hhCategory].add( hhRecord );
                if (usingPumsSplitIndustry) {
                    //record selected industry for each person
                    int persons = hhRecord[NUM_PERSONS_ATTRIB_INDEX];
                    for (int p = 0; p < persons; p++) {
                        int id = hhRecord[HHID_INDEX];
                        int ind = hhRecord[PERSON_ARRAY_ATTRIB_INDEX + p*SPG.NUM_PERSON_ATTRIBUTES];
                        pw.println(i + " " + id + " " + p + " " + ind);
                    }
                }
            }
        }

        //close hh->industry file
        if (usingPumsSplitIndustry)
            pw.close();


        // transfer hhRecords from hhCategoryHhList[] to the hhArray[][][].
        for ( int i=0; i < hhCategoryHhList.length; i++ ) {

            hhArray[i] = new int[hhCategoryHhList[i].size()][];
            for ( int k=0; k < hhArray[i].length; k++ )
                hhArray[i][k] = (int[])hhCategoryHhList[i].get(k);

        }
    }

    private int[] getPumaSetFromHalo(int stateIndex) {
        List<Integer> pumaList = new LinkedList<Integer>();
        int[] haloIndices = halo.getStatePumaIndexArray(stateIndex);
        for (int i = 0; i < haloIndices.length; i++)
            if (haloIndices[i] > -1)
                pumaList.add(i);
        int[] pumaSet = new int[pumaList.size()];
        int counter = 0;
        for (int p : pumaList)
            pumaSet[counter++] = p;
        return pumaSet;
    }

    private TableDataSet[] getNormalizedAcsHHAndPersonData(int i, Map<?,?> fieldNameMap,
                      List<String> hhNumericAttributes, List<String> hhStringAttributes,
                      List<String> personNumericAttributes, List<String> personStringAttributes) { //i is state index
        Map<String,SpgAcsData.AcsDataTransfer> transferMap = getAcsDataTransferMap();
        // form the list of hh record arrays SPG needs from the state PUMS files
        String hhFile = (String) spgPropertyMap.get(ACS_HOUSEHOLD_FILE_PROPERTY_PREFIX + halo.getStateLabel(i));
        logger.info("Reading data from household acs file: " + hhFile);
        List<SpgAcsData.AcsFilter> filters = new LinkedList<SpgAcsData.AcsFilter>();
        filters.add(SpgAcsData.getBlockingFilter((String) fieldNameMap.get("personsName"),Arrays.asList("00"))); //todo: hard coded, but ok for now
        filters.add(SpgAcsData.getPassingIntFilter((String) fieldNameMap.get("pumaName"),getPumaSetFromHalo(i)));
        TableDataSet hhData = SpgAcsData.readAcsData(hhFile,hhNumericAttributes,hhStringAttributes,filters,transferMap);

        //get hh serial # fields, and add plain hhid field
        String[] hhIds = hhData.getColumnAsString((String) fieldNameMap.get("hhIdField"));
        float[] hhId = new float[hhIds.length];
        Map<String,Integer> idMap = new HashMap<String,Integer>();
        for (int id = 0; id < hhId.length; id++) {
            hhId[id] = id;
            idMap.put(hhIds[id],id);
        }
        hhData.appendColumn(hhId,"HHID"); //hard-coded, inherited from PUMSDataReader

        //get person data
        String personFile = (String) spgPropertyMap.get(ACS_PERSON_FILE_PROPERTY_PREFIX + halo.getStateLabel(i));
        logger.info("Reading data from person acs file: " + personFile);
        filters = new LinkedList<SpgAcsData.AcsFilter>();
        filters.add(SpgAcsData.getPassingFilter((String) fieldNameMap.get("hhIdField"),Arrays.asList(hhIds)));
        TableDataSet personData = SpgAcsData.readAcsData(personFile,personNumericAttributes,personStringAttributes,filters,transferMap);

        logger.info("Merging acs data");
        float[] personHhId = new float[personData.getRowCount()];
        float[] startingPersonId = new float[hhData.getRowCount()];
        Set<String> usedHh = new HashSet<String>();
        int personCounter = 0;
        for (String id : personData.getColumnAsString((String) fieldNameMap.get("hhIdField"))) {
            int internalHHId = idMap.get(id); //transfer from acs serial ID to internal count
            personHhId[personCounter] = internalHHId;
            if (!usedHh.contains(id)) { //this assumes the person records will be lumped together (they may need to be sorted too, should be, though)
                startingPersonId[internalHHId] = personCounter;
                usedHh.add(id);
            }
            personCounter++;
        }

        hhData.appendColumn(startingPersonId,"FIRSTPERSONID"); //hard-coded, inherited from PUMSDataReader
        personData.appendColumn(personHhId,"HHID");

        return new TableDataSet[] {hhData,personData};
    }

    private Map<String,SpgAcsData.AcsDataTransfer> getAcsDataTransferMap() {
        SpgAcsData acsData = new SpgAcsData();
        Map<String,SpgAcsData.AcsDataTransfer> transferMap = new HashMap<String,SpgAcsData.AcsDataTransfer>();
        transferMap.put("hhIncName",acsData.getHHIncDataTransfer());
        transferMap.put("industryName",acsData.getPersonIndOccDataTransfer());
        transferMap.put("occupationName",acsData.getPersonIndOccDataTransfer());
        transferMap.put("empStatName",acsData.getPersonLaborTransfer());
        transferMap.put((String) spgPropertyMap.get("acs.units.field.name"),acsData.getHHUnitsDataTransfer());
        transferMap.put((String) spgPropertyMap.get("acs.vehs.field.name"),acsData.getHHVehDataTransfer());
        transferMap.put((String) spgPropertyMap.get("acs.sex.field.name"),acsData.getPersonSexTransfer());
        transferMap.put((String) spgPropertyMap.get("acs.school.field.name"),acsData.getPersonSchoolTransfer());
        return transferMap;
    }

    public void writeHHOutputAttributesFromACS(String baseYear) {
        //output output file writers
        PrintWriter hhOutStream = null;
        PrintWriter personOutStream = null;

        try {
            hhOutStream = new PrintWriter(new BufferedWriter(new FileWriter((String)spgPropertyMap.get("spg2.synpopH"))));
            personOutStream = new PrintWriter(new BufferedWriter(new FileWriter( (String)spgPropertyMap.get("spg2.synpopP"))));
            writeHHOutputAttributesFromACS(baseYear,hhOutStream,personOutStream);
        } catch (IOException e) {
            logger.error("Exception thrown while writing spg2/acs results");
            throw new RuntimeException(e);
        } finally {
            if (hhOutStream != null) {
                try {
                    hhOutStream.close();
                } catch (Exception e) {
                    logger.warn("Problem closing spg2 hh output stream",e);
                }
            }
            if (personOutStream != null) {
                try {
                    personOutStream.close();
                } catch (Exception e) {
                    logger.warn("Problem closing spg2 person output stream",e);
                }
            }
        }
    }

    private void writeHHOutputAttributesFromACS(String baseYear, PrintWriter hhOutStream, PrintWriter personOutStream) throws IOException {
        logger.info ("");
        logger.info ("");
        logger.info ("Writing SynPopH and SynPopP files.");
        logger.info ("");

        //Parse list of hh variables from properties file.
        List<String> hhVariables = Arrays.asList(((String) spgPropertyMap.get("acs.hh.variables")).trim().split("\\s"));
        List<String> personVariables = Arrays.asList(((String) spgPropertyMap.get("acs.person.variables")).trim().split("\\s"));

        // read the SPG2 output file of synthetic household records into a TableDataSet
        logger.info ("reading the SPG2 output file of household index and state index into a TableDataSet.");
        TableDataSet table = new OLD_CSVFileReader().readFile(new File( (String)spgPropertyMap.get("spg2.hh.record.list")));


        //write headers
        int hhVariableCount = hhVariables.size() + 2;
        String[] fieldNames = new String[hhVariableCount];
        int counter = 0;
        fieldNames[counter++] = "HH_ID";
        for (String hhVariable : Arrays.asList(((String) spgPropertyMap.get("pumsHH.variables")).trim().split("\\s")))  //have to keep header names from pums for consistency
            fieldNames[counter++] = hhVariable;
        fieldNames[fieldNames.length-1] = halo.getTazFieldName();
        writePumsData(hhOutStream,fieldNames);

        int personVariableCount = personVariables.size() + 5;
        fieldNames = new String[personVariableCount];
        counter = 0;
        fieldNames[counter++] = "HH_ID";
        fieldNames[counter++] = "PERS_ID";
        for (String personVariable : Arrays.asList(((String) spgPropertyMap.get("pumsPerson.variables")).trim().split("\\s"))) //have to keep header names from pums for consistency
            fieldNames[counter++] = personVariable;
        fieldNames[fieldNames.length-3] = "SW_UNSPLIT_IND";
        fieldNames[fieldNames.length-2] = "SW_OCCUP";
        fieldNames[fieldNames.length-1] = "SW_SPLIT_IND";
        writePumsData(personOutStream,fieldNames);

        //read necessary variables
        Map<String,String> fieldNameMap = new HashMap<String,String>();
        fieldNameMap.put("pumaName",(String) globalPropertyMap.get("acs.pumaField.name"));
        fieldNameMap.put("stateName",(String) globalPropertyMap.get("acs.stateField.name"));
        fieldNameMap.put("personsName",(String) globalPropertyMap.get("acs.personsField.name"));
        fieldNameMap.put("hhIdField",(String) globalPropertyMap.get("acs.hhIdField.name"));

        List<String> hhNumericAttributes = new LinkedList<String>();
        List<String> hhStringAttributes = new LinkedList<String>();
        List<String> personNumericAttributes = new LinkedList<String>();
        List<String> personStringAttributes = new LinkedList<String>();

        //need mainly strings this time
        hhStringAttributes.add(fieldNameMap.get("pumaName"));
        hhStringAttributes.add(fieldNameMap.get("stateName"));
        hhStringAttributes.add(fieldNameMap.get("hhIdField")); //need to add this to have back reference - don't think it will cause problem...
        hhStringAttributes.add(fieldNameMap.get("personsName"));
        for (String hhVariable : hhVariables)
            hhStringAttributes.add(hhVariable);

        personStringAttributes.add(fieldNameMap.get("hhIdField")); //need to add this to have back reference - don't think it will cause problem...
        for (String personVariable : personVariables)
            personStringAttributes.add(personVariable);


        int noIndNoOccCount = 0;
        int hhCount = 1;
        String[] hhFieldValues = new String[hhVariableCount];
        String[] personFieldValues = new String[personVariableCount];


        boolean usingPumsSplitIndustry = globalPropertyMap.containsKey(PumsToSplitIndustry.PUMS_TO_SPLIT_INDUSTRY_FILE_PROPERTY);
        Map<Integer,Map<Integer,Map<Integer,Integer>>> pumsSplitIndustryMap = null; //state->hhid->person->industry
        
        if (usingPumsSplitIndustry) {
            pumsSplitIndustryMap = new HashMap<Integer,Map<Integer,Map<Integer,Integer>>>();
            BufferedReader reader = null;
            try {
                reader = new BufferedReader(new FileReader((String) globalPropertyMap.get(PUMS_HH_SELECTED_INDUSTRY_FILE_PROPERTY)));
                String line;
                while ((line = reader.readLine()) != null) {
                    if (line.length() == 0)
                        continue;
                    String[] data = line.split(" ");
                    int stateId = Integer.parseInt(data[0]);
                    int hhId = Integer.parseInt(data[1]);
                    int personId = Integer.parseInt(data[2]);
                    int indId = Integer.parseInt(data[3]);
                    if (!pumsSplitIndustryMap.containsKey(stateId))
                        pumsSplitIndustryMap.put(stateId, new HashMap<Integer,Map<Integer,Integer>>());
                    if (!pumsSplitIndustryMap.get(stateId).containsKey(hhId))
                        pumsSplitIndustryMap.get(stateId).put(hhId, new HashMap<Integer,Integer>());
                    Integer pr = pumsSplitIndustryMap.get(stateId).get(hhId).put(personId,indId);
                    if (pr != null)
                        throw new IllegalStateException(String.format("Illegally repeated hh/person id combo for split industry lookup: %d/%d",hhId,personId));
                }
            } catch (IOException e) {
                throw new RuntimeException(e);
            } finally {
                if (reader != null) {
                    try {
                        reader.close();
                    } catch (IOException e) {}
                }
            }
        }

        for (int i=0; i < halo.getNumberOfStates(); i++) {
            Map<Integer,Map<Integer,Integer>> pumsSplitIndustryStateMap = usingPumsSplitIndustry ? pumsSplitIndustryMap.get(i) : null;
            TableDataSet[] datas = getNormalizedAcsHHAndPersonData(i,fieldNameMap,hhNumericAttributes,hhStringAttributes,personNumericAttributes,personStringAttributes);
            TableDataSet hhData = datas[0];
            TableDataSet personData = datas[1];
            hhData.buildIndex(hhData.getColumnPosition("HHID"));

            for (int k=0; k < table.getRowCount(); k++) {
                int state = (int) table.getValueAt(k+1,2);
                if (state != i)
                    continue; //wrong state
                int hhid = (int) table.getValueAt(k+1,1);
                int zone = (int) table.getValueAt(k+1,3);

                //fill in hh data
                int f = 0;
                hhFieldValues[f++] = Integer.toString(hhCount);
                for (String hhVariable : hhVariables)
                    hhFieldValues[f++] = hhData.getStringValueAt(hhData.getIndexedRowNumber(hhid),hhVariable);
                hhFieldValues[hhFieldValues.length-1] = Integer.toString(zone);
                writePumsData(hhOutStream,hhFieldValues);

                //find persons in person table
                int startingPerson = ((int) hhData.getValueAt(hhData.getIndexedRowNumber(hhid),"FIRSTPERSONID"))+1;
                int persons = Integer.parseInt(hhData.getStringValueAt(hhData.getIndexedRowNumber(hhid),fieldNameMap.get("personsName")));
                //fill in person data
                for (int p = 0; p < persons; p++) {
                    //person data row is startingPerson+p
                    f = 0;
                    personFieldValues[f++] = Integer.toString(hhCount);
                    personFieldValues[f++] = Integer.toString(p+1);
//                    int industry = ind.getIndustryIndexFromPumsCode(Integer.parseInt(personData.getStringValueAt(startingPerson+p,(String) globalPropertyMap.get("acs.industryField.name"))));
                    int industry = usingPumsSplitIndustry ? pumsSplitIndustryStateMap.get(hhid).get(p) : ind.getIndustryIndexFromPumsCode(Integer.parseInt(personData.getStringValueAt(startingPerson+p,(String) globalPropertyMap.get("acs.industryField.name"))));
                    int occupation = occ.getOccupationIndexFromPumsCode(Integer.parseInt(personData.getStringValueAt(startingPerson+p,(String) globalPropertyMap.get("acs.occupationField.name"))));
                    if(industry==0 && occupation==0)
                        noIndNoOccCount++;
                    int splitIndustry = ind.getSplitIndustryIndex( industry, occupation );
                    for (String personVariable : personVariables)
                        personFieldValues[f++] = personData.getStringValueAt(startingPerson+p,personVariable);

                    personFieldValues[personFieldValues.length-3] = Integer.toString(industry);
                    personFieldValues[personFieldValues.length-2] = Integer.toString(occupation);
                    personFieldValues[personFieldValues.length-1] = Integer.toString(splitIndustry);
                    writePumsData(personOutStream,personFieldValues);
                }
                hhCount++;
            }
        }
        logger.info("Number of people who listed no occupation, no index " + noIndNoOccCount);
    }

    public void writeHHOutputAttributes(String baseYear) {
        if (useAcs(spgPropertyMap))
            writeHHOutputAttributesFromACS(baseYear);
        else
            writeHHOutputAttributesFromPUMS(baseYear);
    }

    
    // get the set of PUMS attributes that SPG2 will write to household output file.
    public void writeHHOutputAttributesFromPUMS ( String baseYear ) {
        
        int hhid;
        int state;
        int zone;
        
        logger.info ("");
        logger.info ("");
        logger.info ("Writing SynPopH and SynPopP files.");
        logger.info ("");

        
        //Parse list of hh variables from properties file.
        String variableString = (String)spgPropertyMap.get("pumsHH.variables");
        ArrayList variableList = new ArrayList();
        StringTokenizer st = new StringTokenizer(variableString, ", |");
        while (st.hasMoreTokens()) {
            variableList.add(st.nextElement());
        }
        String[] hhVariables = new String[variableList.size()];
        for (int i=0; i < hhVariables.length; i++)
            hhVariables[i] = (String)variableList.get(i);

        //Parse list of person variables from properties file.
        variableString = (String)spgPropertyMap.get("pumsPerson.variables");
        variableList.clear();
        st = new StringTokenizer(variableString, ", |");
        while (st.hasMoreTokens()) {
            variableList.add(st.nextElement());
        }
        String[] personVariables = new String[variableList.size()];
        for (int i=0; i < personVariables.length; i++)
            personVariables[i] = (String)variableList.get(i);

        
        String[] hhFieldValues = new String[hhVariables.length + 2];
        String[][] personFieldValues;
        String[][] pumsAttributeValues;

        PrintWriter hhOutStream = null;
        PrintWriter personOutStream = null;
        
        String propertyName;
        String[] PUMSFILE = new String[halo.getNumberOfStates()];
        for (int i=0; i < PUMSFILE.length; i++) {
            propertyName = "pums" + halo.getStateLabel(i) + ".fileName";
            PUMSFILE[i] = (String)spgPropertyMap.get( propertyName );
        }
        
        SpgPumsData pums = new SpgPumsData ( (String)spgPropertyMap.get("pums.dictionary"), baseYear, ind, occ, workers );


        
        
        // read the SPG2 output file of synthetic household records into a TableDataSet
        logger.info ("reading the SPG2 output file of household index and state index into a TableDataSet.");
        OLD_CSVFileReader reader = new OLD_CSVFileReader();
        
        TableDataSet table = null;
        try {
            table = reader.readFile(new File( (String)spgPropertyMap.get("spg2.hh.record.list") ));
        } catch (IOException e) {
            logger.fatal("could not read file of hh and state index from SPG2", e);
        }

        
        
        // write the synthetic household attributes file.
        
        try {
            hhOutStream = new PrintWriter(new BufferedWriter(
                new FileWriter( (String)spgPropertyMap.get("spg2.synpopH") )));

            //write household attributes file header record
            String[] fieldNames = new String[hhVariables.length + 2];
            fieldNames[0] = "HH_ID";
            for (int i=0; i < hhVariables.length; i++)
                fieldNames[i+1] = hhVariables[i];
            fieldNames[fieldNames.length-1] = halo.getTazFieldName();
            writePumsData( hhOutStream, fieldNames);
        }
        catch (Exception e) {
            logger.fatal("Exception when opening synthetic household attributes file.", e);
        }

        try {
            personOutStream = new PrintWriter(new BufferedWriter(
                new FileWriter( (String)spgPropertyMap.get("spg2.synpopP") )));

            //write household attributes file header record
            String[] fieldNames = new String[personVariables.length + 5];
            fieldNames[0] = "HH_ID";
            fieldNames[1] = "PERS_ID";
            for (int i=0; i < personVariables.length; i++)
                fieldNames[i+2] = personVariables[i];
            fieldNames[fieldNames.length-3] = "SW_UNSPLIT_IND";
            fieldNames[fieldNames.length-2] = "SW_OCCUP";
            fieldNames[fieldNames.length-1] = "SW_SPLIT_IND";
            writePumsData( personOutStream, fieldNames);
        }
        catch (Exception e) {
            logger.fatal("Exception when opening synthetic person attributes file.", e);
        }


        
        
        // create a HashMap of field names to use based on those specified in properties file
        HashMap fieldNameMap = new HashMap();
        fieldNameMap.put( "pumaName", globalPropertyMap.get( "pums.pumaField.name" ) );
        fieldNameMap.put( "stateName", globalPropertyMap.get( "pums.stateField.name" ) );
        fieldNameMap.put( "personsName", globalPropertyMap.get( "pums.personsField.name" ) );
        
        
        String indFieldName = (String)globalPropertyMap.get("pums.industryField.name");
        String occFieldName = (String)globalPropertyMap.get("pums.occupationField.name");
        if (indFieldName == null) {
            logger.error ( "no entry in spg properties file for pums.industryField.name.");
            logger.error ( "pums.industryField.name must be defined so that split industries can be associated with un-split industries.");
            throw new RuntimeException();
        }
        if (occFieldName == null) {
            logger.error ( "no entry in spg properties file for pums.occupationField.name.");
            logger.error ( "pums.occupationField.name must be defined so that split industries can be associated with un-split industries.");
            throw new RuntimeException();
        }
        int indFieldNum = -1;
        int occFieldNum = -1;
        for (int i=0; i < personVariables.length; i++) {
            if (personVariables[i].equals(indFieldName))
                indFieldNum = i;
            if (personVariables[i].equals(occFieldName))
                occFieldNum = i;
        }
        if (indFieldNum < 0) {
            logger.error ( "industry variable must be listed in spg properties file for pumsPerson.variables.");
            throw new RuntimeException();
        }
        if (occFieldNum < 0) {
            logger.error ( "occupation variable must be listed in spg properties file for pumsPerson.variables.");
            throw new RuntimeException();
        }
        
        int noIndNoOccCount = 0;
        int hhCount = 1;


        boolean usingPumsSplitIndustry = globalPropertyMap.containsKey(PumsToSplitIndustry.PUMS_TO_SPLIT_INDUSTRY_FILE_PROPERTY);
        Map<Integer,Map<Integer,Map<Integer,Integer>>> pumsSplitIndustryMap = null; //state->hhid->person->industry

        if (usingPumsSplitIndustry) {
            pumsSplitIndustryMap = new HashMap<Integer,Map<Integer,Map<Integer,Integer>>>();
            BufferedReader preader = null;
            try {
                preader = new BufferedReader(new FileReader(PUMS_HH_SELECTED_INDUSTRY_FILE_PROPERTY));
                String line;
                while ((line = preader.readLine()) != null) {
                    String[] data = line.split(" ");
                    int stateId = Integer.parseInt(data[0]);
                    int hhId = Integer.parseInt(data[1]);
                    int personId = Integer.parseInt(data[2]);
                    int indId = Integer.parseInt(data[3]);
                    if (!pumsSplitIndustryMap.containsKey(stateId))
                        pumsSplitIndustryMap.put(stateId, new HashMap<Integer,Map<Integer,Integer>>());
                    if (!pumsSplitIndustryMap.get(stateId).containsKey(hhId))
                        pumsSplitIndustryMap.get(stateId).put(hhId, new HashMap<Integer,Integer>());
                    Integer pr = pumsSplitIndustryMap.get(stateId).get(hhId).put(personId,indId);
                    if (pr != null)
                        throw new IllegalStateException(String.format("Illegally repeated hh/person id combo for split industry lookup: %d/%d",hhId,personId));
                }
            } catch (IOException e) {
                throw new RuntimeException(e);
            } finally {
                if (preader != null) {
                    try {
                        preader.close();
                    } catch (IOException e) {}
                }
            }
        }

        for (int i=0; i < halo.getNumberOfStates(); i++) {
            Map<Integer,Map<Integer,Integer>> pumsSplitIndustryStateMap = usingPumsSplitIndustry ? pumsSplitIndustryMap.get(i) : null;

            logger.info ("reading PUMS data file for " + halo.getStateLabel(i));
            ArrayList pumsList = pums.readSpg2OutputAttributes ( PUMSFILE[i], hhVariables, personVariables, halo, fieldNameMap );

            logger.info ("looking up PUMS records corresponding to household/state indices in TableDataSet.");
            for (int k=0; k < table.getRowCount(); k++) {
                
                state = (int)table.getValueAt( k+1, 2 );
                if (state == i) {

                    hhid = (int)table.getValueAt( k+1, 1 );
                    zone = (int)table.getValueAt( k+1, 3 );
                    
                    pumsAttributeValues = (String[][])pumsList.get( hhid );

                    
                    hhFieldValues[0] = Integer.toString( hhCount );
                    for (int j=0; j < pumsAttributeValues[0].length; j++)
                        hhFieldValues[j+1] = pumsAttributeValues[0][j];
                    hhFieldValues[hhFieldValues.length-1] = Integer.toString( zone );

                    
                    personFieldValues = new String[pumsAttributeValues.length][personVariables.length + 5];
                    for (int p=1; p < pumsAttributeValues.length; p++) {
                        personFieldValues[p][0] = Integer.toString( hhCount );
                        personFieldValues[p][1] = Integer.toString( p );
                        
                        for (int j=0; j < pumsAttributeValues[p].length; j++)
                            personFieldValues[p][j+2] = pumsAttributeValues[p][j];
                        
                        int industry;
                        int occupation;
                        if(baseYear.equals("1990")){

                            //industry = ind.getIndustryIndexFromPumsCode(Integer.parseInt(pumsAttributeValues[p][indFieldNum]));
                            industry = usingPumsSplitIndustry ? pumsSplitIndustryStateMap.get(hhid).get(p-1) : ind.getIndustryIndexFromPumsCode(Integer.parseInt(pumsAttributeValues[p][indFieldNum]));
                            occupation = occ.getOccupationIndexFromPumsCode(Integer.parseInt(pumsAttributeValues[p][occFieldNum]));
                        }else{
                            //industry = ind.getIndustryIndexFromPumsCode((pumsAttributeValues[p][indFieldNum]).trim());
                            industry = usingPumsSplitIndustry ? pumsSplitIndustryStateMap.get(hhid).get(p-1) : ind.getIndustryIndexFromPumsCode((pumsAttributeValues[p][indFieldNum]).trim());
                            occupation = occ.getOccupationIndexFromPumsCode((pumsAttributeValues[p][occFieldNum]).trim());
                        }

                        if(industry==0 && occupation==0) noIndNoOccCount++;
                        int splitIndustry = ind.getSplitIndustryIndex( industry, occupation );
                        personFieldValues[p][personFieldValues[p].length-3] = Integer.toString( industry );
                        personFieldValues[p][personFieldValues[p].length-2] = Integer.toString( occupation );
                        personFieldValues[p][personFieldValues[p].length-1] = Integer.toString( splitIndustry );
                        
                    }
                    
                    hhCount++;
                    
                    
                    try {
                        writePumsData( hhOutStream, hhFieldValues );
                    }
                    catch (Exception e) {
                        logger.fatal("Exception when writing synthetic household attributes file.", e);
                    }
                    
                    try {
                        for (int p=1; p < pumsAttributeValues.length; p++)
                            writePumsData( personOutStream, personFieldValues[p] );
                    }
                    catch (Exception e) {
                        logger.fatal("Exception when writing synthetic person attributes file.", e);
                    }
                    
                }
            
            }

        }

        logger.info("Number of people who listed no occupation, no index " + noIndNoOccCount);


        try {
            hhOutStream.close();
        }
        catch (Exception e) {
            logger.fatal("Exception when closing synthetic household attributes file.", e);
        }
        
        try {
            personOutStream.close();
        }
        catch (Exception e) {
            logger.fatal("Exception when closing synthetic person attributes file.", e);
        }
        
    }



    
    // write category frequency tables by state to logger
    public void writeFrequencyTables () {

        int numPersons;
        int numWorkers;
        int pumsIndustryCode;
        int pumsOccupationCode;
        int pumsIncomeCode;
        int industryCode;
        int occupationCode;
        int incomeSizeCode;
        int pumsHHWeight;
        int employmentStatusCode;
        

        int[] indFreq = new int[ind.getNumberIndustries()];
        int[] pumsIndFreq = new int[ind.getNumberIndustries()];
        int[] pumsWtIndFreq = new int[ind.getNumberIndustries()];

        int[] occFreq = new int[occ.getNumberOccupations()];
        int[] pumsOccFreq = new int[occ.getNumberOccupations()];
        int[] pumsWtOccFreq = new int[occ.getNumberOccupations()];

        int[][] incSizeFreq = new int[2][incSize.getNumberIncomeSizes()];
        int[] pumsIncSizeFreq = new int[incSize.getNumberIncomeSizes()];
        int[][] pumsWtIncSizeFreq = new int[2][incSize.getNumberIncomeSizes()];

        int[][] workersFreq = new int[2][workers.getNumberWorkerCategories()];
        int[] pumsWorkersFreq = new int[workers.getNumberWorkerCategories()];
        int[][] pumsWtWorkersFreq = new int[2][workers.getNumberWorkerCategories()];




        // Write frequency tables of total workers by industry and occupation codes
        // and total households by household category and number of workers in all final synthetic households,
        // PUMS records, and weighted PUMS records for each state in the halo area
        for (int s=0; s < halo.getNumberOfStates(); s++) {
            
            Arrays.fill (indFreq, 0);
            Arrays.fill (occFreq, 0);
            Arrays.fill (incSizeFreq[0], 0);
            Arrays.fill (workersFreq[0], 0);
            Arrays.fill (incSizeFreq[1], 0);
            Arrays.fill (workersFreq[1], 0);
            Arrays.fill (pumsIndFreq, 0);
            Arrays.fill (pumsOccFreq, 0);
            Arrays.fill (pumsIncSizeFreq, 0);
            Arrays.fill (pumsWorkersFreq, 0);
            Arrays.fill (pumsWtIndFreq, 0);
            Arrays.fill (pumsWtOccFreq, 0);
            Arrays.fill (pumsWtIncSizeFreq[0], 0);
            Arrays.fill (pumsWtWorkersFreq[0], 0);
            Arrays.fill (pumsWtIncSizeFreq[1], 0);
            Arrays.fill (pumsWtWorkersFreq[1], 0);
            
            for (int i=0; i < hhArray.length; i++) {

                for (int k=0; k < hhArray[i].length; k++) {

                    if ( halo.getStateIndex(hhArray[i][k][STATE_ATTRIB_INDEX]) != s )
                        continue;
                    
                    numPersons = hhArray[i][k][NUM_PERSONS_ATTRIB_INDEX];
                    numWorkers = hhArray[i][k][NUM_WORKERS_ATTRIB_INDEX];
                    pumsIncomeCode = hhArray[i][k][HH_INCOME_ATTRIB_INDEX];
                    pumsHHWeight = hhArray[i][k][HH_WEIGHT_ATTRIB_INDEX];

                    incomeSizeCode = incSize.getIncomeSize(pumsIncomeCode, numPersons); 
                    if ( numWorkers > 0 )
                        incSizeFreq[0][incomeSizeCode] += hhArray[i][k][HH_SELECTED_INDEX];
                    else
                        incSizeFreq[1][incomeSizeCode] += hhArray[i][k][HH_UNEMPLOYED_INDEX];
                    pumsIncSizeFreq[incomeSizeCode]++;
                    if ( numWorkers > 0 )
                        pumsWtIncSizeFreq[0][incomeSizeCode] += pumsHHWeight;
                    else
                        pumsWtIncSizeFreq[1][incomeSizeCode] += pumsHHWeight;

                    if ( numWorkers > 0 )
                        workersFreq[0][numWorkers] += hhArray[i][k][HH_SELECTED_INDEX];
                    else
                        workersFreq[1][numWorkers] += hhArray[i][k][HH_UNEMPLOYED_INDEX];
                    pumsWorkersFreq[numWorkers]++;
                    if ( numWorkers > 0 )
                        pumsWtWorkersFreq[0][numWorkers] += pumsHHWeight;
                    else
                        pumsWtWorkersFreq[1][numWorkers] += pumsHHWeight;

                    for (int j=0; j < numPersons; j++) {

                        employmentStatusCode = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 2];
                        if ( employmentStatusCode > 0 ) {
                            
                            pumsIndustryCode = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 0];
                            pumsOccupationCode = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 1];
                            industryCode = pumsIndustryCode;
                            occupationCode = pumsOccupationCode; 
                            
                            indFreq[industryCode] += ( hhArray[i][k][HH_SELECTED_INDEX] );
                            pumsIndFreq[industryCode]++;
                            pumsWtIndFreq[industryCode] += pumsHHWeight;
        
                            occFreq[occupationCode] += ( hhArray[i][k][HH_SELECTED_INDEX] );
                            pumsOccFreq[occupationCode]++;
                            pumsWtOccFreq[occupationCode] += pumsHHWeight;
                        
                        }
                        
                    }
                    
                }

                writeFreqSummaryToLogger( halo.getStateLabel(s) + " Employed Persons by ED Industry categories for all households in final sample", "Industry", ind.getIndustryLabels(), indFreq );
                writeFreqSummaryToLogger( halo.getStateLabel(s) + " Employed Persons by Occupation categories for all households in final sample", "Occupation", occ.getOccupationLabels(), occFreq );
                writeFreqSummaryToLogger( halo.getStateLabel(s) + " Households by Income/Household Size categories for all employed households in final sample", "IncomeSize", incSize.getIncomeSizeLabels(), incSizeFreq[0] );
                writeFreqSummaryToLogger( halo.getStateLabel(s) + " Households by Income/Household Size categories for all unemployed households in final sample", "IncomeSize", incSize.getIncomeSizeLabels(), incSizeFreq[1] );
                writeFreqSummaryToLogger( halo.getStateLabel(s) + " Households by Workers categories for all employed households in final sample", "Workers", workers.getWorkersLabels(), workersFreq[0] );
                writeFreqSummaryToLogger( halo.getStateLabel(s) + " Households by Workers categories for all unemployed households in final sample", "Workers", workers.getWorkersLabels(), workersFreq[1] );
                writeFreqSummaryToLogger( halo.getStateLabel(s) + " Employed Persons by ED Industry categories for all PUMS households", "Industry", ind.getIndustryLabels(), pumsIndFreq );
                writeFreqSummaryToLogger( halo.getStateLabel(s) + " Employed Persons by Occupation categories for all PUMS households", "Occupation", occ.getOccupationLabels(), pumsOccFreq );
                writeFreqSummaryToLogger( halo.getStateLabel(s) + " Households by Income/Household Size categories for all PUMS households", "IncomeSize", incSize.getIncomeSizeLabels(), pumsIncSizeFreq );
                writeFreqSummaryToLogger( halo.getStateLabel(s) + " Households by Workers categories for all PUMS households", "Workers", workers.getWorkersLabels(), pumsWorkersFreq );
                writeFreqSummaryToLogger( halo.getStateLabel(s) + " Employed Persons by ED Industry categories for all Weighted PUMS households", "Industry", ind.getIndustryLabels(), pumsWtIndFreq );
                writeFreqSummaryToLogger( halo.getStateLabel(s) + " Employed Persons by Occupation categories for all Weighted PUMS households", "Occupation", occ.getOccupationLabels(), pumsWtOccFreq );
                writeFreqSummaryToLogger( halo.getStateLabel(s) + " Households by Income/Household Size categories for all Weighted PUMS employed households", "IncomeSize", incSize.getIncomeSizeLabels(), pumsWtIncSizeFreq[0] );
                writeFreqSummaryToLogger( halo.getStateLabel(s) + " Households by Income/Household Size categories for all Weighted PUMS unemployed households", "IncomeSize", incSize.getIncomeSizeLabels(), pumsWtIncSizeFreq[1] );
                writeFreqSummaryToLogger( halo.getStateLabel(s) + " Households by Workers categories for all Weighted PUMS employed households", "Workers", workers.getWorkersLabels(), pumsWtWorkersFreq[0] );
                writeFreqSummaryToLogger( halo.getStateLabel(s) + " Households by Workers categories for all Weighted PUMS unemployed households", "Workers", workers.getWorkersLabels(), pumsWtWorkersFreq[1] );
            
            }
            
        }
        

        
        // Now repeat, but for all states combined:
        // Write frequency tables of total person industry and occupation codes
        // and household category and number of workers in all final synthetic households,
        // PUMS records, and weighted PUMS records over all states combined in the halo area.
        Arrays.fill (indFreq, 0);
        Arrays.fill (occFreq, 0);
        Arrays.fill (incSizeFreq[0], 0);
        Arrays.fill (workersFreq[0], 0);
        Arrays.fill (incSizeFreq[1], 0);
        Arrays.fill (workersFreq[1], 0);
        Arrays.fill (pumsIndFreq, 0);
        Arrays.fill (pumsOccFreq, 0);
        Arrays.fill (pumsIncSizeFreq, 0);
        Arrays.fill (pumsWorkersFreq, 0);
        Arrays.fill (pumsWtIndFreq, 0);
        Arrays.fill (pumsWtOccFreq, 0);
        Arrays.fill (pumsWtIncSizeFreq[0], 0);
        Arrays.fill (pumsWtWorkersFreq[0], 0);
        Arrays.fill (pumsWtIncSizeFreq[1], 0);
        Arrays.fill (pumsWtWorkersFreq[1], 0);
        
        for (int i=0; i < hhArray.length; i++) {

            for (int k=0; k < hhArray[i].length; k++) {
        
                numPersons = hhArray[i][k][NUM_PERSONS_ATTRIB_INDEX];
                numWorkers = hhArray[i][k][NUM_WORKERS_ATTRIB_INDEX];
                pumsIncomeCode = hhArray[i][k][HH_INCOME_ATTRIB_INDEX];
                pumsHHWeight = hhArray[i][k][HH_WEIGHT_ATTRIB_INDEX];

                incomeSizeCode = incSize.getIncomeSize(pumsIncomeCode, numPersons);
                if ( numWorkers > 0 ) {
                    incSizeFreq[0][incomeSizeCode] += hhArray[i][k][HH_SELECTED_INDEX];
                }
                else {
                    incSizeFreq[1][incomeSizeCode] += hhArray[i][k][HH_UNEMPLOYED_INDEX];
                }
                pumsIncSizeFreq[incomeSizeCode]++;
                if ( numWorkers > 0 )
                    pumsWtIncSizeFreq[0][incomeSizeCode] += pumsHHWeight;
                else
                    pumsWtIncSizeFreq[1][incomeSizeCode] += pumsHHWeight;

                if ( numWorkers > 0 )
                    workersFreq[0][numWorkers] += hhArray[i][k][HH_SELECTED_INDEX];
                else
                    workersFreq[1][numWorkers] += hhArray[i][k][HH_UNEMPLOYED_INDEX];
                pumsWorkersFreq[numWorkers]++;
                if ( numWorkers > 0 )
                    pumsWtWorkersFreq[0][numWorkers] += pumsHHWeight;
                else
                    pumsWtWorkersFreq[1][numWorkers] += pumsHHWeight;

                for (int j=0; j < numPersons; j++) {

                    employmentStatusCode = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 2];
                    if ( employmentStatusCode > 0 ) {
                        
                        pumsIndustryCode = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 0];
                        pumsOccupationCode = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 1];
                        industryCode = pumsIndustryCode;
                        occupationCode = pumsOccupationCode; 
                        
                        indFreq[industryCode] += ( hhArray[i][k][HH_SELECTED_INDEX] );
                        pumsIndFreq[industryCode]++;
                        pumsWtIndFreq[industryCode] += pumsHHWeight;
    
                        occFreq[occupationCode] += ( hhArray[i][k][HH_SELECTED_INDEX] );
                        pumsOccFreq[occupationCode]++;
                        pumsWtOccFreq[occupationCode] += pumsHHWeight;

                    }
                    
                }
                
            }
            
        }

        writeFreqSummaryToLogger( " Regional Employed Persons by ED Industry categories for all households in final sample", "Industry", ind.getIndustryLabels(), indFreq );
        writeFreqSummaryToLogger( " Regional Employed Persons by Occupation categories for all households in final sample", "Occupation", occ.getOccupationLabels(), occFreq );
        writeFreqSummaryToLogger( " Regional Households by Income/Household Size categories for all employed households in final sample", "IncomeSize", incSize.getIncomeSizeLabels(), incSizeFreq[0] );
        writeFreqSummaryToLogger( " Regional Households by Income/Household Size categories for all unemployed households in final sample", "IncomeSize", incSize.getIncomeSizeLabels(), incSizeFreq[1] );
        writeFreqSummaryToLogger( " Regional Households by Workers categories for all employed households in final sample", "Workers", workers.getWorkersLabels(), workersFreq[0] );
        writeFreqSummaryToLogger( " Regional Households by Workers categories for all unemployed households in final sample", "Workers", workers.getWorkersLabels(), workersFreq[1] );
        writeFreqSummaryToLogger( " Regional Employed Persons by ED Industry categories for all PUMS households", "Industry", ind.getIndustryLabels(), pumsIndFreq );
        writeFreqSummaryToLogger( " Regional Employed Persons by Occupation categories for all PUMS households", "Occupation", occ.getOccupationLabels(), pumsOccFreq );
        writeFreqSummaryToLogger( " Regional Households by Income/Household Size categories for all PUMS households", "IncomeSize", incSize.getIncomeSizeLabels(), pumsIncSizeFreq );
        writeFreqSummaryToLogger( " Regional Households by Workers categories for all PUMS households", "Workers", workers.getWorkersLabels(), pumsWorkersFreq );
        writeFreqSummaryToLogger( " Regional Employed Persons by ED Industry categories for all Weighted PUMS households", "Industry", ind.getIndustryLabels(), pumsWtIndFreq );
        writeFreqSummaryToLogger( " Regional Employed Persons by Occupation categories for all Weighted PUMS households", "Occupation", occ.getOccupationLabels(), pumsWtOccFreq );
        writeFreqSummaryToLogger( " Regional Households by Income/Household Size categories for all Weighted PUMS employed households", "IncomeSize", incSize.getIncomeSizeLabels(), pumsWtIncSizeFreq[0] );
        writeFreqSummaryToLogger( " Regional Households by Income/Household Size categories for all Weighted PUMS unemployed households", "IncomeSize", incSize.getIncomeSizeLabels(), pumsWtIncSizeFreq[1] );
        writeFreqSummaryToLogger( " Regional Households by Workers categories for all Weighted PUMS employed households", "Workers", workers.getWorkersLabels(), pumsWtWorkersFreq[0] );
        writeFreqSummaryToLogger( " Regional Households by Workers categories for all Weighted PUMS unemployed households", "Workers", workers.getWorkersLabels(), pumsWtWorkersFreq[1] );
    
    }
        
    

    // summarize households by incomeSize category for updating PI input file.
    public TableDataSet sumHouseholdsByIncomeSize () {

        int numPersons;
        int pumsIncomeCode;
        int incomeSizeCode;
        


        int numIncomeSizes = incSize.getNumberIncomeSizes();
        int[] householdsByIncomeSize = new int[numIncomeSizes];
        

        // get frequency table of total households by household category codes in all final synthetic households
        Arrays.fill (householdsByIncomeSize, 0);
        for (int i=0; i < hhArray.length; i++) {

            for (int k=0; k < hhArray[i].length; k++) {
        
                numPersons = hhArray[i][k][NUM_PERSONS_ATTRIB_INDEX];
                pumsIncomeCode = hhArray[i][k][HH_INCOME_ATTRIB_INDEX];

                incomeSizeCode = incSize.getIncomeSize(pumsIncomeCode, numPersons); 
                householdsByIncomeSize[incomeSizeCode] += ( hhArray[i][k][HH_SELECTED_INDEX] + hhArray[i][k][HH_UNEMPLOYED_INDEX] );

            }
            
        }


        // save the total households in TableDataSet for writing later
        float[] tableData = new float[numIncomeSizes];
        String[][] labels = new String[numIncomeSizes][1];
        for (int i=0; i < householdsByIncomeSize.length; i++) {
            labels[i][0] = incSize.getIncomeSizeLabel(i);
            tableData[i] = householdsByIncomeSize[i];
        }
        ArrayList headings = new ArrayList();
        headings.add("hhCategory");
        
        TableDataSet table = TableDataSet.create ( labels, headings );
        table.appendColumn ( tableData, "spg1Households");

        
        
        
        return table;
        
    }
        
    

    private void writeFreqSummaryToLogger ( String tableTitle, String fieldName, String[] freqDescriptions, int[] freqs ) {
        
            // print a simple summary table
            logger.info( "Frequency Report table: " + tableTitle );
            logger.info( "Frequency for field " + fieldName );
            logger.info(String.format("%8s", "Value") + String.format("%13s", "Description") + String.format("%45s", "Frequency"));
            
            int total = 0;
            for (int i = 0; i < freqs.length; i++) {
                if (freqs[i] > 0) {
                    String description = freqDescriptions[i];
                    logger.info( String.format("%8d", i) + "  " + String.format("%-45s", description) + String.format("%11d", freqs[i] ) );
                    total += freqs[i];
                }
            }
            
            logger.info(String.format("%15s", "Total") +    String.format("%51d\n\n\n", total));
        }
        
        

    // write out the summary statistics for the final synthetic population and the corresponding weighted PUMS summaries
    // statistics are summarized for various categories by PUMA
    protected void writeFreqSummaryToCsvFile () {

        String state;
        int puma;
        int st;
        String incomeSizeLabel;
        String industryLabel;
        String occupationLabel;
        int value;
        
        int stIndex;
        int pumaIndex;
        int numPersons;
        int numWorkers;
        int pumsIncomeCode;
        int pumsIndustryCode;
        int pumsOccupationCode;
        int incomeSizeCode;
        int industryCode;
        int occupationCode;
        int employmentStatusCode;
        

        
        int[][] pumas = halo.getPumas();
        int numIncomeSizes = incSize.getNumberIncomeSizes();
        int numOccupations = occ.getNumberOccupations();
        int numIndustries = ind.getNumberIndustries();
        
        // define array of states by pumas for summarizing data
        int[][][][] hhsByStatePumaCategory = new int[pumas.length][][][];
        int[][][][] personsByStatePumaIndOcc = new int[pumas.length][][][];
        for (int i=0; i < pumas.length; i++) {
            hhsByStatePumaCategory[i] = new int[pumas[i].length][][];
            personsByStatePumaIndOcc[i] = new int[pumas[i].length][][];
        }
        
        
        

        // summarize households by household size/income categories over all final synthetic households
        // and summarize persons by industryt by occupation;
        // i index loops over states, j index loops over pumas in states
        for (int i=0; i < pumas.length; i++) {
            for (int j=0; j < pumas[i].length; j++) {
                hhsByStatePumaCategory[i][j] = new int[numIncomeSizes][workers.getNumberWorkerCategories()];
                personsByStatePumaIndOcc[i][j] = new int[numIndustries][numOccupations];
            }
        }
        
        

        // loop over all PUMS records used in making synthetic population and summarize
        // by incomeSize and industry/occupation categories by state and puma
        for (int i=0; i < hhArray.length; i++) {

            for (int k=0; k < hhArray[i].length; k++) {
        
                st = hhArray[i][k][STATE_ATTRIB_INDEX];
                puma = hhArray[i][k][PUMA_ATTRIB_INDEX];
                
                stIndex = halo.getStateIndex( st );
                pumaIndex = halo.getPumaIndex(stIndex, puma);
                
                numPersons = hhArray[i][k][NUM_PERSONS_ATTRIB_INDEX];
                pumsIncomeCode = hhArray[i][k][HH_INCOME_ATTRIB_INDEX];
                numWorkers = hhArray[i][k][NUM_WORKERS_ATTRIB_INDEX];
                if (numWorkers > workers.getNumberWorkerCategories()-1)
                    numWorkers = workers.getNumberWorkerCategories()-1;

                incomeSizeCode = incSize.getIncomeSize(pumsIncomeCode, numPersons);

                for (int j=0; j < numPersons; j++) {

                    employmentStatusCode = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 2];
                    if ( employmentStatusCode > 0 ) {
                        
                        pumsIndustryCode = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 0];
                        pumsOccupationCode = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 1];
                        industryCode = pumsIndustryCode;
                        occupationCode = pumsOccupationCode;
    
                        personsByStatePumaIndOcc[stIndex][pumaIndex][industryCode][occupationCode] += ( hhArray[i][k][HH_SELECTED_INDEX] );
                    
                    }
                }
                
                hhsByStatePumaCategory[stIndex][pumaIndex][incomeSizeCode][numWorkers] += ( hhArray[i][k][HH_SELECTED_INDEX] + hhArray[i][k][HH_UNEMPLOYED_INDEX] );

            }
            
        }


        
        String incomeSizeFileName = (String)spgPropertyMap.get("incomeSizeCalibration.fileName");
        String industryOccupationFileName = (String)spgPropertyMap.get("industryOccupationCalibration.fileName");
        
        
        PrintWriter outStream = null;

        // open output stream for writing SPG1 calibration results file
        try {
            
            if ( incomeSizeFileName != null ) {

                // write csv file header record
                outStream = new PrintWriter (new BufferedWriter( new FileWriter(incomeSizeFileName) ) );
                outStream.println ( "State,PUMA,IncomeSize,Workers,HH_Frequency");

                // write hh size/income category descriptions and frequencies by state and puma
                for (int i=0; i < hhsByStatePumaCategory.length; i++) {
                    for (int j=0; j < hhsByStatePumaCategory[i].length; j++) {
                        for (int k=0; k < hhsByStatePumaCategory[i][j].length; k++) {
                            for (int m=0; m < hhsByStatePumaCategory[i][j][k].length; m++) {
                            
                                state = halo.getStateLabel(i);
                                puma = halo.getPumaLabel(i, j);
                                incomeSizeLabel = incSize.getIncomeSizeLabel(k);
                                value = hhsByStatePumaCategory[i][j][k][m];
                            
                                if (value > 0)
                                    outStream.println( state + "," + puma + "," + incomeSizeLabel + "," + (m < workers.getNumberWorkerCategories()-1 ? Integer.toString(m) : (workers.getNumberWorkerCategories()-1 + "+")) + "," + value );
                            }
                        }
                    }
                }
                outStream.close();
                
            }


        
        
            if ( industryOccupationFileName != null ) {
                
                // write csv file header record
                outStream = new PrintWriter (new BufferedWriter( new FileWriter(industryOccupationFileName) ) );
                outStream.println ( "State,PUMA,Industry,Occupation,Worker_Frequency");

                // write hh size/income category descriptions and frequencies by state and puma
                for (int i=0; i < personsByStatePumaIndOcc.length; i++) {
                    for (int j=0; j < personsByStatePumaIndOcc[i].length; j++) {
                        for (int k=0; k < personsByStatePumaIndOcc[i][j].length; k++) {
                            for (int m=0; m < personsByStatePumaIndOcc[i][j][k].length; m++) {
                                state = halo.getStateLabel(i);
                                puma = halo.getPumaLabel(i, j);
                                industryLabel = ind.getIndustryLabel(k);
                                occupationLabel = occ.getOccupationLabel(m);
                                value = personsByStatePumaIndOcc[i][j][k][m];
                                
                                if (value > 0)
                                    outStream.println( state + "," + puma + "," + industryLabel + "," + occupationLabel + "," + value );
                            }
                        }
                    }
                }
                outStream.close();
                
            }


        }
        catch (IOException e) {
            logger.fatal ("I/O exception writing SPG calibration results file.", e);
        }


    }
            
        
        
        
    // accumulate the zonal summary statistics for the final synthetic population 
    // that are needed by PT and DCOM components.
    private void accumulateZonalSummaryArrays (int[] hhAttribs, int taz) {

        if ( taz <= 0 || taz > maxZone ) {
            if ( hhAttribs[HH_WEIGHT_ATTRIB_INDEX] > 0 ) {
                badTazCount++;
            }
            return;
        }
                
        int tazIndex = zoneIndex[taz];
        
        int numPersons = hhAttribs[NUM_PERSONS_ATTRIB_INDEX];
        int pumsIncome = hhAttribs[HH_INCOME_ATTRIB_INDEX];
        int numWorkers = hhAttribs[NUM_WORKERS_ATTRIB_INDEX];
        int incomeSize = incSize.getIncomeSize(pumsIncome, numPersons);

        
        totalHhsByTaz[tazIndex] ++;
        totalPersonsByTaz[tazIndex] += numPersons;
        totalWorkersByTaz[tazIndex] += numWorkers;
        totalHhIncomeByTaz[tazIndex] += pumsIncome;
        hhsByTazCategory[tazIndex][incomeSize] ++;
                
                
        for (int j=0; j < numPersons; j++) {

            int age = hhAttribs[PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 4];
            int ageCategory = -1;
            for ( int a=0; a < ageRangeMax.length; a++ ) {
                if ( age < ageRangeMax[a] ) {
                    ageCategory = a;
                    break;
                }
            }
            if ( ageCategory < 0 ) {
                throw new RuntimeException("age=" + age + " for person " + j + " in hh " + hhAttribs[HHID_INDEX] + " in state " + halo.getStateIndex(hhAttribs[STATE_ATTRIB_INDEX]) + " is invalid.");
            }
            
            personAgesByTaz[tazIndex][ageCategory]++;
        }
                
    }
            
        
        
        
    // write out the accumulated zonal summary statistics for the final synthetic population 
    // that are needed by PT and DCOM components.
    public void writeZonalSummaryToCsvFile () {

        String zonalSummaryFileName = (String)spgPropertyMap.get("spg2.current.synpop.summary");
        
        PrintWriter outStream = null;

        // open output stream for writing zonal summary file
        try {
            
            if ( zonalSummaryFileName != null ) {

                // write csv file header record
                outStream = new PrintWriter (new BufferedWriter( new FileWriter(zonalSummaryFileName) ) );
                
                ArrayList headerLabels = new ArrayList();
                headerLabels.add( "TAZ" );
                headerLabels.add( "AvgHHInc" );
                headerLabels.add( "TotalHHs" );
                headerLabels.add( "TotalPersons" );
                headerLabels.add( "TotalWorkers" );
                for (int i=0; i < incSize.getNumberIncomeSizes(); i++)
                    headerLabels.add( incSize.getIncomeSizeLabel(i) );
                for (int i=0; i < ageRangeLabels.length; i++)
                    headerLabels.add( ageRangeLabels[i] );
                

                for (int i=0; i < headerLabels.size()-1; i++)
                    outStream.print ( headerLabels.get(i) + "," );
                outStream.println ( headerLabels.get(headerLabels.size()-1) );
                

                
                
                // write zonal summary fields
                for (int i=0; i < numZones; i++) {

                    int[] values = new int[headerLabels.size()];
                    values[0] = indexZone[i];
                    values[1] = totalHhsByTaz[i] > 0 ? totalHhIncomeByTaz[i]/totalHhsByTaz[i] : 0;
                    values[2] = totalHhsByTaz[i];
                    values[3] = totalPersonsByTaz[i];
                    values[4] = totalWorkersByTaz[i];
                    for (int j=0; j < incSize.getNumberIncomeSizes(); j++)
                        values[5+j] = hhsByTazCategory[i][j];
                    for (int j=0; j < ageRangeLabels.length; j++)
                        values[5+incSize.getNumberIncomeSizes()+j] = personAgesByTaz[i][j];
                    
                    for (int j=0; j < values.length-1; j++)
                        outStream.print ( values[j] + "," );
                    outStream.println ( values[values.length-1] );

                }
                outStream.close();
                
            }

        }
        catch (IOException e) {
            logger.fatal ( "I/O exception writing SPG zonal summary results file.", e );
        }

        
        logger.info( badTazCount + " bad TAZs assigned.");

    }
            
        
        
        
    // write out the final hhArray to a csv file
    public void writeFinalHhArrayToCsvFile () {

        // person attributes for person j:
        // industry: PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 0
        // occup:    PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 1
        // employed: PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 2
        // person weight: PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 3
        

        
        PrintWriter outStream = null;

        // open output stream for writing SPG1 calibration results file
        try {
            
            // write csv file header record
            String fileName = (String)spgPropertyMap.get("hhArrayCsv.fileName");
            if ( fileName == null )
                return;

            outStream = new PrintWriter (new BufferedWriter( new FileWriter( fileName ) ) );
            outStream.println ( "pumsHhId,hhid,state,stateIndex,puma,pumaIndex,persons,income,workers,incomeSize,person,empStat,industry,occupation,empHhWeight,unEmpHhWeight,pumsHhWeight");

            // loop over all PUMS records used in making synthetic population and write out attrbutes
            for (int i=0; i < hhArray.length; i++) {

                for (int k=0; k < hhArray[i].length; k++) {
            
                    int empHhs = hhArray[i][k][HH_SELECTED_INDEX];
                    int unEmpHhs = hhArray[i][k][HH_UNEMPLOYED_INDEX];
                    int hhId = hhArray[i][k][HHID_INDEX];
                    int pumsHhId = hhArray[i][k][PUMS_HH_INDEX];
                    int hhState = hhArray[i][k][STATE_ATTRIB_INDEX];
                    int hhPuma = hhArray[i][k][PUMA_ATTRIB_INDEX];
                    int hhPersons = hhArray[i][k][NUM_PERSONS_ATTRIB_INDEX];
                    int hhIncome = hhArray[i][k][HH_INCOME_ATTRIB_INDEX];
                    int hhWeight = hhArray[i][k][HH_WEIGHT_ATTRIB_INDEX];
                    int hhWorkers = hhArray[i][k][NUM_WORKERS_ATTRIB_INDEX];
                    
                    int pumaIndex = halo.getPumaIndex(i,hhPuma);
                    int incomeSizeCode = incSize.getIncomeSize(hhIncome, hhPersons);

                    for (int j=0; j < hhPersons; j++) {

                        int personIndustry = 0;
                        int personOccupation = 0;
                        int personEmpStat = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 2];
                        if ( personEmpStat > 0 ) {
                            personIndustry = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 0];
                            personOccupation = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 1];
                        }
                        
                        outStream.println( pumsHhId + "," + hhId + "," + hhState + "," + i + "," + hhPuma + "," + pumaIndex + "," + hhPersons + "," + hhIncome + "," + hhWorkers + "," + incomeSizeCode + "," + (j+1) + "," + personEmpStat + "," + personIndustry + "," + personOccupation + "," + empHhs + "," + unEmpHhs + "," + hhWeight );

                    }
                    
                }
                
            }

            outStream.close();
        }
        catch (IOException e) {
            logger.fatal ("I/O exception writing final hhArray to csv file.", e);
        }


    }
            
        
        
        

    
    
    
    // return a selection from the range [0,...,probabilities.length-1] given a cumulative probability distribution
    // a return value of -1 indicates no selection alternatives had a positive probability.
    public int getSelectionFromCumProbabilities (double[] cumProbabilities, Random randomGen) {
        
        double randomNumber = randomGen.nextDouble();
        return binarySearchDouble (cumProbabilities, randomNumber);

        

        
    }

    // return a selection from the range [0,...,probabilities.length-1] given a cumulative probability distribution
    // a return value of -1 indicates no selection alternatives had a positive probability.
    public int getSelectionFromCumProbabilities (double[] cumProbabilities) {
        double randomNumber = SeededRandom.getRandom();
        return binarySearchDouble (cumProbabilities, randomNumber);

    }
    
    
    
    public int binarySearchDouble (double[] cumProbabilities, double entry) {
        
        // lookup index for 0 <= entry < 1.0 in cumPrbabilities
        // cumProbabilities values are assumed to be in range: [0,1], and
        // cumProbabilities[cumProbabilities.length-1] must equal 1.0


        // if entry is outside the allowed range, return -1
        if ( entry < 0 || entry >= 1.0 ) {
            logger.error ( "entry = " + entry + " is outside of allowable range for cumulative distribution [0,...,1.0)" );
            return -1;
        }

        // if cumProbabilities[cumProbabilities.length-1] is not equal to 1.0, return -1
        if ( cumProbabilities[cumProbabilities.length-1] != 1.0 ) {
            logger.error ( "cumProbabilities[cumProbabilities.length-1] = " + cumProbabilities[cumProbabilities.length-1] + " must equal 1.0" );
            return -1;
        }
        
        
        int hi = cumProbabilities.length;
        int lo = 0;
        int mid = (hi -lo)/2;
        
        int safetyCount = 0;
        

        // if mid is 0, 
        if ( mid == 0 ) {
            if ( entry < cumProbabilities[0] )
                return 0;
            else
                return 1;
        }
        else if ( entry < cumProbabilities[mid] && entry >= cumProbabilities[mid-1] ) {
            return mid;
        }

        
        while (true) {
        
            if ( entry < cumProbabilities[mid] ) {
                hi = mid;
                mid = (hi + lo)/2;
            }
            else {
                lo = mid;
                mid = (hi + lo)/2;
            }

            
            // if mid is 0, 
            if ( mid == 0 ) {
                if ( entry < cumProbabilities[0] )
                    return 0;
                else
                    return 1;
            }
            else if ( entry < cumProbabilities[mid] && entry >= cumProbabilities[mid-1] ) {
                return mid;
            }
        
            
            if ( safetyCount++ > cumProbabilities.length ) {
                logger.error ( "binary search stuck in the while loop" );
                throw new RuntimeException();
            }
                
        }
        
    }
    
    
    
    private void writePumsData(PrintWriter outStream, String[] record) {
        
        outStream.print(record[0]);

        for (int i = 1; i < record.length; i++)
            outStream.print("," + record[i]);

        outStream.println();
        
    }


    /**
     * This method has been over-ridden in the tlumip/SPGnew class due to the addition of the
     * world zones in the tlumip pi outputs.  In Ohio, this method is the one that is used and
     * any other SPG class that extends this class would use this method unless explicitly over-ridden.
     * @param fileName
     * @return
     */
    public double[][][] readPiLaborDollars ( String fileName ) {
        
        int index;
        int zone;
        int occup;
        double dollars;
        
        // read the PI output file into a TableDataSet
        OLD_CSVFileReader reader = new OLD_CSVFileReader();
        
        TableDataSet table = null;
        try {
            table = reader.readFile(new File( fileName ));
        } catch (IOException e) {
            logger.fatal("could not read PI Labor Dollars file: " + fileName, e);
        }
        
        
        // get values from TableDataSet into array to return
        double[][][] laborDollars = new double[halo.getNumberOfZones()][occ.getNumberOccupations()][incSize.getNumberIncomeSizes()];

        
        
        for (int r=0; r < table.getRowCount(); r++) {
        
            try {
                occup = occ.getOccupationIndexFromLabel( table.getStringValueAt(r+1, 2) );
                zone = (int)table.getValueAt(r+1, 1);

                index = halo.getZoneIndex(zone);
    
                if (index < 0)
                    continue;
    
                dollars = 0.0;
                for (int c=0; c < incSize.getNumberIncomeSizes(); c++) {
                    dollars = table.getValueAt(r+1, c+3);
                    laborDollars[index][occup][c] = dollars;
                    regionLaborDollars[occup][c] += dollars;
                }
            }
            catch (Exception e) {
                String msg = "Error processing file " + fileName + " in row: " + r;
                throw new RuntimeException(msg, e);
            }
            
        }
        
        return laborDollars;
        
    }
    
    

    private int[][] readPiIncomeSizeHHs ( String fileName ) {
        
        // read the PI output file into a TableDataSet
        OLD_CSVFileReader reader = new OLD_CSVFileReader();
        
        TableDataSet table = null;
        try {
            table = reader.readFile(new File( fileName ));
        } catch (IOException e) {
            logger.fatal("could not read the PI hhs by incomesize category file: fileName", e);
        }
        
        
        // get values from TableDataSet into array to return
        int[][] dataTable = new int[halo.getNumberOfZones()][incSize.getNumberIncomeSizes()];
        int[] categoryTotals = new int[incSize.getNumberIncomeSizes()];
        int[] maxZoneCategoryValue = new int[incSize.getNumberIncomeSizes()];
        int[] maxZoneCategoryIndex = new int[incSize.getNumberIncomeSizes()];
        

        float[] remainders = new float[incSize.getNumberIncomeSizes()];
        for (int r=0; r < table.getRowCount(); r++) {
            int incomeSize = incSize.getIncomeSizeIndex( table.getStringValueAt(r+1, "Activity") );
            
            if (incomeSize >= 0) {
                
                int zone = (int)table.getValueAt(r+1, "ZoneNumber");
                if (halo.isHaloZone(zone)) {
                    
                    float piHhs = table.getValueAt(r+1, "Quantity");

                    int hhs = (int)( piHhs + remainders[incomeSize] );
                    remainders[incomeSize] = piHhs - hhs + remainders[incomeSize];

                    int index = halo.getZoneIndex(zone);

                    if (index < 0 || index >= halo.getNumberOfZones())
                        logger.info ("r="+r + ", index="+index + ", zone="+zone);

                    dataTable[index][incomeSize] = hhs;
                    categoryTotals[incomeSize] += hhs;
                    
                    
                    if ( hhs > maxZoneCategoryValue[incomeSize] ) {
                        maxZoneCategoryValue[incomeSize] = hhs;
                        maxZoneCategoryIndex[incomeSize] = index;
                    }

                }

            }

        }
        
        
        // sum zonal households by hh category and compare to total households by hh category from SPG1.  They must match.
        for (int i=0; i < hhArray.length; i++) {
            
            // add one more to max zone if remainder still has a household
            if ( remainders[i] > 0.5 ) {
                int index = maxZoneCategoryIndex[i];
                dataTable[index][i] ++;
                categoryTotals[i] ++;
            }
            
            // add up total households from SPG1 by category
            int spg1Households = 0;
            for (int j=0; j < hhArray[i].length; j++) { 
                int numHouseholds = ( hhArray[i][j][HH_SELECTED_INDEX] + hhArray[i][j][HH_UNEMPLOYED_INDEX] );
                spg1Households += numHouseholds;
            }

            // check for excessive difference and throw error if found.
            if ( Math.abs( spg1Households - categoryTotals[i] ) >= 10 ) {
                RuntimeException e = new RuntimeException( String.format("incomesize category %d total hhs in SPG1 hhArray: %d not equal to hhs from input file, origHHsIncomeSizePI: %d.", i, spg1Households, categoryTotals[i]) );
                throw e;
            }

            
            // compare SPG1 total to input file total, and adjust input file table if necessary.
            if ( spg1Households != categoryTotals[i] ) {
                int delta = spg1Households - categoryTotals[i];
                int index = maxZoneCategoryIndex[i];
                if ( dataTable[index][i] + delta > 0 ) {
                    dataTable[index][i] += delta;
                }
                else {
                    RuntimeException e = new RuntimeException( String.format("incomesize category %d total hhs in SPG1 hhArray: %d not equal to hhs from input file, origHHsIncomeSizePI: %d.", i, spg1Households, categoryTotals[i]) );
                    throw e;
                }

            }
            
        }
        
        return dataTable;
        
    }
    
    

    public void writePiInputFile ( TableDataSet table ) {
        
        
        String fileName = (String)spgPropertyMap.get("spg1.hhs.by.hh.category");
        
        // write the PI input file from a TableDataSet
        CSVFileWriter writer = new CSVFileWriter();
        
        try {
            writer.writeFile( table, new File( fileName ), new GeneralDecimalFormat("0.#####E0",10000000,.01 ) );
        } catch (IOException e) {
            logger.fatal("could not write the households by household category need by PI or AA", e);
        }
        
    }

    

    private void reassignOccupationCodes() {
        
        // get the regional number of employed persons by incomesize, industry and occupation in hhArray from SPG1.
        // use the relative frequencies from this table as weights to draw an occupation for persons with
        // occupation code 0 ("No Occupation"), given their household incomesize and their industry.
        // if industry is also 0, ("Unemployed"), cage the person's employment status to unemployed,
        // and the household to unemployed, if no other persons are employed.
        
        int ivar=-1, kvar=-1, jvar=-1;
        try {
            
            // add up the number of employed persons in each category
            int[][][] occJobs = new int[incSize.getNumberIncomeSizes()][ind.getNumberIndustries()][occ.getNumberOccupations()];
            int[][] totJobs = new int[incSize.getNumberIncomeSizes()][ind.getNumberIndustries()];
            
            for (int i=0; i < hhArray.length; i++) {
                ivar = i;

                for (int k=0; k < hhArray[i].length; k++) {
                    kvar = k;

                    int hhSize = hhArray[i][k][NUM_PERSONS_ATTRIB_INDEX];
                    int pumsIncomeCode = hhArray[i][k][HH_INCOME_ATTRIB_INDEX];

                    int incomeSizeCode = incSize.getIncomeSize(pumsIncomeCode, hhSize);
                    
                    for (int j=0; j < hhSize; j++) {
                        jvar = j;

                        int pumsIndustryCode = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 0];
                        int pumsOccupationCode = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 1];
                        int employed = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 2];

                        if ( employed > 0 ) {
                            occJobs[incomeSizeCode][pumsIndustryCode][pumsOccupationCode] += hhArray[i][k][HH_SELECTED_INDEX];
                            totJobs[incomeSizeCode][pumsIndustryCode] += hhArray[i][k][HH_SELECTED_INDEX];
                        }

                    }
                }
            }

            
            // calculate the cumulative frequencies by incsize, industry
            double[][][] occCumFreqs = new double[incSize.getNumberIncomeSizes()][ind.getNumberIndustries()][occ.getNumberOccupations()];

            for (int i=0; i < occCumFreqs.length; i++) {
                ivar = i;

                for (int j=0; j < occCumFreqs[i].length; j++) {
                    jvar = j;

                    if (totJobs[i][j] > 0)
                        occCumFreqs[i][j][0] = occJobs[i][j][0]/totJobs[i][j];
                    for (int k=1; k < occCumFreqs[i][j].length; k++) {
                        kvar = k;
                        
                        if (totJobs[i][j] > 0)
                            occCumFreqs[i][j][k] = occJobs[i][j][k]/totJobs[i][j];
                        occCumFreqs[i][j][k] += occCumFreqs[i][j][k-1];
                        
                    }
                    
                }
                
            }
            

            // loop back through the synthetic population.
            // if industry and occupation for an employed person are both 0,
            // make that person unemployed and make the household unemployed if necessary.
            // otherwise, if occupation is 0, choose an occupation from the relative frequencies
            // for the person's hh incsize and industry. 
            for (int i=0; i < hhArray.length; i++) {
                ivar = i;

                for (int k=0; k < hhArray[i].length; k++) {
                    kvar = k;

                    int hhSize = hhArray[i][k][NUM_PERSONS_ATTRIB_INDEX];
                    int pumsIncomeCode = hhArray[i][k][HH_INCOME_ATTRIB_INDEX];

                    int incomeSizeCode = incSize.getIncomeSize(pumsIncomeCode, hhSize);
                    
                    int numWorkers = 0;
                    for (int j=0; j < hhSize; j++) {
                        jvar = j;

                        int pumsIndustryCode = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 0];
                        int pumsOccupationCode = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 1];
                        int employed = hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 2];

                        if ( employed > 0 ) {
                            
                            if ( pumsIndustryCode == 0 && pumsOccupationCode == 0 ) {
                                // change person's employment status to 0
                                employed = 0;
                                hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 2] = 0;
                            }
                            else if ( pumsIndustryCode == 0 && pumsOccupationCode > 0 ) {
                                // do nothing, just check these cases
                                employed = 1;
                            }
                            else if ( pumsIndustryCode > 0 && pumsOccupationCode == 0 ) {
                                // change the occupation code na set employment status to 1.
                                employed = 1;
                                hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 2] = 1;
                                pumsOccupationCode = getSelectionFromCumProbabilities(occCumFreqs[incomeSizeCode][pumsIndustryCode]);
                                hhArray[i][k][PERSON_ARRAY_ATTRIB_INDEX + j*NUM_PERSON_ATTRIBUTES + 1] = pumsOccupationCode;
                            }
                            
                        }

                        if ( employed > 0 )
                            numWorkers++;
                        
                    }
                    
                    // if there are now no workers in household, where there were before,
                    // change household type from employed to unemployed.
                    if ( numWorkers == 0 && hhArray[i][k][HH_SELECTED_INDEX] > 0 ) {
                        hhArray[i][k][HH_UNEMPLOYED_INDEX] = hhArray[i][k][HH_SELECTED_INDEX];
                        hhArray[i][k][HH_SELECTED_INDEX] = 0;
                    }

                }
            }

        }
        catch (Exception e) {
            logger.error ( "Exception caught calculating frequency of employed persons by incsize, industry, aoccupation in SPGnew.spg1(), i=" + ivar + ", j=" + jvar + ", k=" + kvar, e );
        }
        
    }

    //This method is used for the DAF implementation.
    public void spgNewInit( HashMap spgPropertyMap, HashMap globalPropertyMap, String baseYear, String currentYear ) {
      //this method is implemented in the Tlumip and Ohio SPGNew class.
    }

    
    


    
    
    public class AssignZonesWorker implements Runnable {
        
        private final int category;
        private final String categoryLabel;
        private final CountDownLatch countdown;
        private Random randomGenerator = new Random();
        
        public AssignZonesWorker(int category, String categoryLabel, CountDownLatch countdown) {
            this.category = category;
            this.categoryLabel = categoryLabel;
            this.countdown = countdown;
            this.randomGenerator.setSeed(Integer.parseInt(globalPropertyMap.get("randomSeed").toString()));
        }
        
        public void run() {

            // do the assignment of zones to households
            mtResults[category] = assignZonesForHhCategory( category, regionLaborDollarsPerJob, categoryLabel, randomGenerator );

            // update the gobal counters and log message
            synchronized (objLock) {
                categoryCount ++;
                cumulativeHhCount += mtResults[category].length;
                logger.info( String.format("Category %d:  %d of %d households have had zones assigned.", category, cumulativeHhCount, origRegionalHHs) );
                StatusLogger.logHistogram("spg2.households.assigned","SPG2 Status: Households Assigned",origRegionalHHs,cumulativeHhCount,"Households Assigned","Households");
            }

            countdown.countDown();
            
        }
        
    }
    
}

