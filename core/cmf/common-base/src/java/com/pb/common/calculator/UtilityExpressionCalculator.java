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
package com.pb.common.calculator;

import java.io.File;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.Serializable;
import java.io.StringWriter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.ResourceBundle;
import java.util.Set;

import org.apache.log4j.Logger;

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.util.ResourceUtil;

/**
 * Provides generic calculator functionality for evaluating utility equations.
 * style expressions.
 *
 * @author    Tim Heier
 * @version   1.0, 2/13/2003
 */

public class UtilityExpressionCalculator implements VariableTable, Serializable {

    private static final long serialVersionUID = 7497158488337652487L;
    protected static Logger logger = Logger.getLogger(UtilityExpressionCalculator.class);
    protected static Logger debugLogger = Logger.getLogger("debug");
    protected static Logger traceLogger =  Logger.getLogger("trace");

    protected static Object objLock = new Object();

    private static int OZ_INDEX = 0;
    private static int DZ_INDEX = 1;
    private static int SZ_INDEX = 2;
    private static int ZONE_INDEX = 3;
    private static int HH_INDEX = 4;
    private static int ALT_INDEX = 5;

    protected char[] indexSynonyms = { 'o', 'd', 's', 'z', 'h', 'a' };

    private boolean indexDebug = false;
    private String indexDebugLabel = "";

    private boolean loggerDebug = false;

    private boolean debugLoggerDebug = false;
    private String variableTableAsString = "not generated";

    //Constructor parameters
    private File file;
    private ControlFileReader controlFile;
    private int modelSheet;
    private int dataSheet;
    private Class userClass;

    private int nModelEntries;
    private int nAlternatives;
    private ModelAlternative[] alternativeNames;
    private String[] altNames;

    private int[][] nestedAlternatives;
    private double[][] nestingCoefficients;


    private Expression[] modelExpressions;
    private Expression[] filterExpressions;
    private ExpressionFlags[] expressionFlags;
    private ExpressionIndex[] expressionIndex;
    private float[][] coefficients;
    private double[] answers;
    private double[][] altAnswers;
    private double[] results;

    //Used as global variables during parsing - this is kind of a hack
    private int currentMatrixVariable;
    private int expressionBeingParsed;
    private boolean expressionBeingParsedIsFilter;

    //Used to track matrices and indices that change by alternative
    private boolean matrixIndexChangesByAlternative = false;
    private Set<String> indexChangedByAlternative = new HashSet<String>();

    //Internal variables available to user as $var
    private int[] available;

    //Alternative data
    private TableDataSet altTableData = null;
    private String[] altColumnName = new String[0];

    //Data structure variables
    private ArrayList<String> scalarIndex = new ArrayList<String>();
    private double[] scalarValue;

    //User object
    private transient Object dmuObject;
    private transient MethodInvokerTemplate invokerTemplate;
    private transient MethodInvoker methodInvoker;


    //Determines if alterantives are to be found in a file
    private boolean isAlternativesInFile = false;

    /*Hold a list of VariableInfo objects while expressions are being parsed.
     * This array list is converted into an array of VariableInfo after all
     * parsing is done.
     */
    protected ArrayList<VariableInfo> varInfoList = new ArrayList<VariableInfo>();
    protected VariableInfo[] varInfo;


    //Hold values of internal variables during the scope of a solve method call
    protected int[] internalVariable = new int[6];

    protected MatrixDataManager matrixDataManager = MatrixDataManager.getInstance();
    protected TableDataSetManager tableDataManager = TableDataSetManager.getInstance();


    /**
     * Instances of UEC get their inputs from a control file in Excel
     * format.
     *
     * This constructor assumes model is on the first sheet and the data is
     * on the second sheet.
     *
     * @param file a File object which represents the Excel file
     * location.
     */
    public UtilityExpressionCalculator(File file) {
        this(file, 0, 1, null);
    }

    /**
     * Instances of UEC get their inputs from a control file in Excel
     * format.
     *
     * This constructor assumes model is on the first sheet and there is no
     * data sheet at all.
     *
     * @param file a File object which represents the Excel file
     * location.
     * @param modelSheet the sheet with the model definition (zero based)
     */
    public UtilityExpressionCalculator(File file, int modelSheet) {

        //pass null for userClass
        this(file, modelSheet, -1, null);
    }

    /**
     * Instances of UEC get their inputs from a control file in Excel
     * format.
     *
     * @param file a File object which represents the Excel file
     * location.
     * @param modelSheet the sheet with the model definition (zero based)
     * @param dataSheet the sheet with the data entries (zero based)
     */
    public UtilityExpressionCalculator(File file, int modelSheet,
            int dataSheet, Class<?> userClass) {
        this(file, modelSheet, dataSheet, new HashMap<String, String>(),
                userClass);
    }

    /**
     * Instances of UEC get their inputs from a control file in Excel
     * format.
     *
     * @param file a File object which represents the Excel file
     * location.
     * @param modelSheet the sheet with the model definition (zero based)
     * @param dataSheet the sheet with the data entries (zero based)
     */
    public UtilityExpressionCalculator(File file, int modelSheet,
            int dataSheet, ResourceBundle rb, Class<?> userClass) {
        this(file, modelSheet, dataSheet, ResourceUtil.changeResourceBundleIntoHashMap( rb ), userClass );
    }

    /**
     * Instances of UEC get their inputs from a control file in Excel
     * format.
     *
     * @param file a File object which represents the Excel file
     * location.
     * @param modelSheet the sheet with the model definition (zero based)
     * @param dataSheet the sheet with the data entries (zero based)
     */
    public UtilityExpressionCalculator(File file, int modelSheet,
            int dataSheet, HashMap<String, String> env, Class<?> userClass) {
        this.file = file;
        this.modelSheet = modelSheet;
        this.dataSheet = dataSheet;
        this.userClass = userClass;

        //This is a debugging optimization
        if (logger.isDebugEnabled()) {
            loggerDebug = true;
        }

        //This is a debugging optimization
        if (debugLogger.isDebugEnabled()) {
            debugLoggerDebug = true;
        }

        if (loggerDebug) {
            logger.debug("Excel file: "+this.file);
            logger.debug("Model sheet: "+this.modelSheet);
            logger.debug("Data sheet: "+this.dataSheet);
        }

        //Mark critical section of code
        if (loggerDebug)
            logger.debug("About to enter critical section for: " + file.getName());

        synchronized (objLock) {
            if (loggerDebug)
                logger.debug("In critical section for: " + file.getName());

            //Reads control file when instantiated
            this.controlFile = new ControlFileReader(file, env, modelSheet, dataSheet);

            nestedAlternatives = this.controlFile.nestedAlternatives;
            nestingCoefficients = this.controlFile.nestingCoefficients;

            //User class with getXXX() methods
            this.userClass = userClass;
            this.invokerTemplate = new MethodInvokerTemplate(userClass);

            readData();

            parseExpressions();

            methodInvoker = invokerTemplate.generateAndLoadClass();

            if (loggerDebug)
                logger.debug ("MethodInvoker source file: "+invokerTemplate.getGeneratedSourceCodePrefix());
        }

        if (loggerDebug)
            logger.debug("Left critical section for: " + file.getName());

        //Set number of alternatives based on alternatives in file
        if (controlFile.header.isAlternativesInFile) {
            isAlternativesInFile = true;
            nAlternatives = altTableData.getRowCount();
        }

        //Holds the results from expression.solve()
        answers = new double[nModelEntries];
        altAnswers = new double[nModelEntries][nAlternatives];

        //Holds the sum of each expression*coefficient for an alternative
        results = new double[nAlternatives];

        //Holds the availabilty of each alternative - available by default
        available = new int[nAlternatives+1];
        Arrays.fill(available, 1);

        //Optimization for the getAlternativeNames method
        altNames = new String[alternativeNames.length];
        for(int i=0; i < alternativeNames.length; i++) {
            altNames[i]=alternativeNames[i].name;
        }

    }


    /**
     * @return Logger used in UEC to log detailed trace information
     */
    public Logger getTraceLogger() {
        return traceLogger;
    }



    /**
     * Build list of expressions and parse each.
     */
    private void parseExpressions() {

        modelExpressions = new Expression[nModelEntries];
        filterExpressions = new Expression[nModelEntries];

        expressionFlags = new ExpressionFlags[nModelEntries];
        expressionIndex = new ExpressionIndex[nModelEntries];

        if (loggerDebug) {
            logger.debug("");
            logger.debug("---------- Parsing expressions ----------");
        }

        for (int i=0; i < nModelEntries; i++) {
            modelExpressions[i] = new Expression(controlFile.modelEntries[i].expression, this);
            filterExpressions[i] = new Expression(controlFile.modelEntries[i].filter, this);
            expressionFlags[i] = new ExpressionFlags();
            expressionIndex[i] = new ExpressionIndex(controlFile.modelEntries[i].index);

            checkForScalarExpression( i );
            checkForFilterExpression( i );
            checkForAlternativeVariable( i );

            //Set global variable so getXXXVariableIndex will know what expression is being parsed
            expressionBeingParsed = i;
            currentMatrixVariable = 0;
            expressionBeingParsedIsFilter = false;

            try {
                modelExpressions[i].parse();
            } catch (RuntimeException e) {
                throw new RuntimeException("Parsing error in expression["+(i+1)+"]: "+modelExpressions[i].getExpression(),e);
            }

            checkForScalarResultChangingByAlternative( i );

            if (expressionFlags[i].hasFilter) {
                expressionBeingParsedIsFilter = true;
                try {
                    filterExpressions[i].parse();
                } catch (RuntimeException e) {
                    throw new RuntimeException("Parsing error in filter expression["+(i+1)+"]: "+filterExpressions[i].getExpression(),e);
                }
            }
        }

        //Create scalar value array - do this after parsing because all of the
        //variables have been identified
        scalarValue = new double[scalarIndex.size()];

        //Create variableInfo array out of list.
        varInfo = varInfoList.toArray( new VariableInfo[varInfoList.size()] );

        if(debugLoggerDebug)
            printVariableTable();

    }

    /**
     * Log the data values for a given origin, destination, and zone.
     * 
     * @param origTaz
     * @param destTaz
     * @param zone
     */
    public void logDataValues(int origTaz, int destTaz, int zone){

        if(origTaz>0 && destTaz>0)
            matrixDataManager.logMatrixValues(origTaz,destTaz);

        if(zone>0)
            tableDataManager.logZoneTableValues(zone);

    }

    /**
     * Log the data values for a given origin, destination, and zone.
     * 
     * @param localLogger - the logger to send the results to
     * @param origTaz
     * @param destTaz
     * @param zone
     */
    public void logDataValues(Logger localLogger, int origTaz, int destTaz, int zone){

        if(origTaz>0 && destTaz>0)
            matrixDataManager.logMatrixValues(localLogger, origTaz,destTaz);

        if(zone>0)
            tableDataManager.logZoneTableValues(localLogger, zone);

    }

    /**
     * Log the current values in the answers array.
     * 
     *  @param localLogger = the logger to send the results to
     *  @param uecName = user defined input
     * 
     *  no limit to the number of alternatives logged. If a max number of alts logged
     *  is desired, use the other method.
     */
    public void logAnswersArray(Logger localLogger, String uecName) {
        int numAlts = altAnswers[0].length;
        int[] specificAlts = new int[numAlts+1];
        Arrays.fill(specificAlts, 1);
        logAnswersArray(localLogger, uecName, specificAlts, Integer.MAX_VALUE);
    }

    public void logAnswersArray(Logger localLogger, String uecName, int maxAlt) {
        int numAlts = altAnswers[0].length;
        int[] specificAlts = new int[numAlts+1];
        Arrays.fill(specificAlts, 1);
        logAnswersArray(localLogger, uecName, specificAlts, maxAlt);
    }

    public void logAnswersArray(Logger localLogger, String uecName, int[] specificAlts) {
        logAnswersArray(localLogger, uecName, specificAlts, Integer.MAX_VALUE);
    }

    public void logAnswersArray(Logger localLogger, String uecName, int[] specificAlts, int maxAlts) {

        // create the header
        localLogger.info( "*******************************************************************************************" );
        localLogger.info( "Utility Expressions for " + uecName);
        localLogger.info( "*******************************************************************************************" );



        // log the answers for each expression and each alternative
        int numAlts = altAnswers[0].length;
        int numExps = altAnswers.length;

        double coeff = 0.0;
        double[] cumValues = new double[numAlts];

        localLogger.info ( "For each model expression, 'coeff * expressionValue' pairs are listed for each available alternative.  At the end, total utility is listed." );
        localLogger.info ( "The last line shows total utility for each available alternative." );
        String logString = String.format( "%-8s", "Exp" );
        int count = 0;
        for (int alt=0; alt < numAlts; alt++) {
            // available uses 1-based indexing
            if ( available[alt+1] == 0 && specificAlts[alt+1] == 0 )
                continue;

            logString += String.format( " %26d   ", alt+1 );

            count++;
            if ( count == maxAlts )
                break;
        }
        localLogger.info( logString );

        String separator = "";
        for (int i=0; i < logString.length(); i++)
            separator += "-";
        localLogger.info( separator );



        for (int exp=0; exp < numExps; exp++) {

            logString = String.format( "%-8d", exp+1 );

            count = 0;
            for (int alt=0; alt < numAlts; alt++) {

                // available uses 1-based indexing
                if ( available[alt+1] == 0 && specificAlts[alt+1] == 0 )
                    continue;

                if ( coefficients[exp].length > 1 )
                    coeff = coefficients[exp][alt];
                else
                    coeff = coefficients[exp][0];

                // altAnswers uses 0-based indexing
                double value = altAnswers[exp][alt] * coeff;
                cumValues[alt] += value;

                logString += String.format( " %10.5f * %13.5e   ", coeff, altAnswers[exp][alt] );

                count++;
                if ( count == maxAlts )
                    break;

            }

            localLogger.info( logString );

        }

        localLogger.info( separator );

        logString = String.format( "%11s", "Alt Utility" );

        boolean firstNotLogged = true;
        count = 0;
        for (int alt=0; alt < numAlts; alt++) {

            // available uses 1-based indexing
            if ( available[alt+1] == 0 && specificAlts[alt+1] == 0 )
                continue;

            if ( firstNotLogged ) {
                logString += String.format( " %23.8e   ", cumValues[alt] );
                firstNotLogged = false;
            }
            else {
                logString += String.format( " %26.8e   ", cumValues[alt] );
            }

            count++;
            if ( count == maxAlts )
                break;
        }

        localLogger.info( logString );
        localLogger.info( "" );
        localLogger.info( "" );
    }

    /**
     * Log the current values in the answers array.
     *
     *  @param localLogger = the logger to send the results to
     */
    public void logResultsArray(Logger localLogger, int origin, int destination) {

        // create the header
        String header = String.format("%16s", "Alternatives:");
        for (String altName : altNames) {
            header = header + String.format("  %16s", altName);
        }
        localLogger.info("Utility Calculations for origin "+origin+" destination "+destination);
        localLogger.info(header);

        String line = String.format("%16s", "");
        for (double result : results) {
            line = line + String.format("  %16.4f", result);

        }
        localLogger.info(line);

    }

    public void logSelectTokens(Logger localLogger, int[] tokenNums, int origin, int destination){
        //sort the user-specified token Nums
        Arrays.sort(tokenNums);

        // create the header
        String header = String.format("%16s", "Token Number");
        localLogger.info("Token Values for origin "+origin+" destination "+destination);
        localLogger.info(header);


        // log the values for each token and each alternative
        for (int tokNum: tokenNums) {
            String line = String.format("%16d", tokNum);
            line = line + String.format("  %16.2f", altAnswers[tokNum-1][0]);
            localLogger.info(line);
        }

        localLogger.info("\n");
    }

    /**
     * Prints a variable table to an internal string and the debug logger.
     */

    public void printVariableTable() {
        StringWriter sWriter = new StringWriter(4096);
        PrintWriter out = new PrintWriter(sWriter);

        out.println("");
        out.println("----------------------------------- Variable Table --------------------------------------------");
        out.println("");
        out.println("                                                           value    orig    dest    name  chg by");
        out.println("Index   Name                         Type                  index   index   index   index     alt");
        out.println("");
        for (int i=0; i < varInfo.length; i++) {
            StringBuffer sb = new StringBuffer(256);
            sb.append( String.format("%5d", i) );
            sb.append( "   ");
            sb.append( String.format("%-26s", varInfo[i].getName()) );
            sb.append( "   ");
            sb.append( String.format("%-17s", varInfo[i].getTypeName()) );
            sb.append( String.format("%10d", varInfo[i].getValueIndexValue()) );
            sb.append( String.format("%8d", varInfo[i].getOrigIndexValue()) );
            sb.append( String.format("%8d", varInfo[i].getDestIndexValue()) );
            sb.append( String.format("%8d", varInfo[i].getNameIndexValue()) );
            sb.append( String.format("%8s", (varInfo[i].isChangesByAlternative() ? "T" : "F")) );
            out.println(sb.toString());
        }
        out.close();

        //Save printout of variable table so it can be returned with a getXXX method
        variableTableAsString = sWriter.toString();

        logger.info(variableTableAsString);
    }


    /**
     * Main solve method that should be called by clients.
     *
     * @param indexValues
     * @param dmuObject
     * @param availFlag
     * @return  solution of the utility expression
     */
    public double[] solve(IndexValues indexValues, Object dmuObject, int[] availFlag) {
        if (availFlag != null) {
            System.arraycopy(availFlag, 1, available, 1, nAlternatives);
        }

        indexDebug = indexValues.getDebug();
        indexDebugLabel = indexValues.getDebugLabel();

        internalVariable[SZ_INDEX] = indexValues.getStopZone();

        return solve(indexValues.getOriginZone(), indexValues.getDestZone(),
                indexValues.getZoneIndex(), indexValues.getHHIndex(), dmuObject);
    }


    /**
     * Solves the expressions listed on the specified model sheet. This method allows
     * for an availability flag to be supplied.
     *
     * @deprecated  This method is replaced by solve(IndexValues, Object, int[])
     *
     * @param orig
     * @param dest
     * @param zoneIndex
     * @param hhIndex
     * @param dmuObject
     * @param availFlag
     */
    public double[] solve(int orig, int dest, int zoneIndex, int hhIndex, Object dmuObject, int[] availFlag) {
        System.arraycopy(availFlag, 1, available, 1, nAlternatives);
        return solve( orig, dest, zoneIndex, hhIndex, dmuObject);
    }


    /**
     * Solves the expressions listed on the specified model sheet.
     *
     * @deprecated  This method is replaced by solve(IndexValues, Object)
     *
     * @param orig
     * @param dest
     * @param zoneIndex
     * @param hhIndex
     * @param dmuObject
     */
    public double[] solve(int orig, int dest, int zoneIndex, int hhIndex, Object dmuObject) {
        this.dmuObject = dmuObject;

        // if debug logging, only log values when indexDebug has been set to true
        boolean oldDebugLoggerDebug = debugLoggerDebug;
        if ( ! indexDebug )
            debugLoggerDebug = false;


        internalVariable[OZ_INDEX] = orig;
        internalVariable[DZ_INDEX] = dest;
        //internalVariable[SZ_INDEX] = zoneIndex;  //set in new solve() method
        internalVariable[ZONE_INDEX] = zoneIndex;
        internalVariable[HH_INDEX]   = hhIndex;

        if (debugLoggerDebug) {
            debugLogger.debug("");
            debugLogger.debug("---------- Solving expressions ----------");
            debugLogger.debug("Orig zone : "+ orig);
            debugLogger.debug("Dest zone : "+ dest);
            debugLogger.debug("Data Zone : "+ zoneIndex);
            debugLogger.debug("Household : "+ hhIndex);
            debugLogger.debug("DMU obj   : "+ dmuObject);
            debugLogger.debug("Alternatives : "+ nAlternatives);
        }

        //Reset arrays before solving
        Arrays.fill(answers, 0.0);
        Arrays.fill(results, 0.0);
        Arrays.fill(scalarValue, 0.0);

        int alternativeNumber, coeffIndex;
        boolean firstAlternative = true;

        for (int a=0; a < nAlternatives; a++) {

            if (isAlternativesInFile) {
                alternativeNumber = (int) altTableData.getIndexedValueAt(a+1, 1);
                coeffIndex = 0;
            } else {
                alternativeNumber = a+1;
                coeffIndex = a;
            }

            internalVariable[ALT_INDEX]  = alternativeNumber;


            if (debugLoggerDebug) {
                debugLogger.debug("");
                debugLogger.debug("---------- ALTERNATIVE: "+alternativeNumber);
                if (available[alternativeNumber] <= 0) {
                    debugLogger.debug("not available");
                }
            }

            if (available[alternativeNumber] <= 0)
                continue;

            solveExpressions(firstAlternative, a, coeffIndex);
            firstAlternative = false;
        }


        if (debugLoggerDebug) {
            StringBuffer sb = new StringBuffer(256);
            sb.append("MODEL RESULTS ==> ");
            for (int i = 0; i < nAlternatives; i++) {
                sb.append( String.format("%.3f",results[i]) + ", " );
            }
            debugLogger.debug("");
            debugLogger.debug(sb.toString());
        }

        //Make a copy of results array to avoid reference side effects
        double[] returnResults = new double[results.length];
        System.arraycopy(results, 0, returnResults, 0, results.length);

        debugLoggerDebug = oldDebugLoggerDebug;

        return returnResults;
    }


    /**
     *
     * @param firstAlternative  flag to indicate that the first alternative is being processed
     * @param altIndex  alternative number eg. 0, 1, 2, ...
     * @param coeffIndex  index into coefficient value array
     */
    private void solveExpressions(boolean firstAlternative, int altIndex, int coeffIndex) {

        double filterResult;

        for (int e=0; e < nModelEntries; e++) {
            if (debugLoggerDebug) {
                debugLogger.debug("");
                debugLogger.debug("entry: "+(e+1)+", "+controlFile.modelEntries[e].name);
            }

            //Solve expressions the first time through the alternative loop or
            //if there is an alternative variable in the expression
            if ( (firstAlternative) || (expressionFlags[e].hasAlternativeVariable) ) {

                //Solve filter expression first if it exists
                if (expressionFlags[e].hasFilter) {

                    if ( indexDebug && traceLogger.isDebugEnabled() ) {
                        traceLogger.debug( String.format("%s [%d]:  alt = %d, name = %s, filter expression = %s.", indexDebugLabel, e+1, altIndex+1, controlFile.modelEntries[e].name, filterExpressions[e].getExpression()) );
                        filterExpressions[e].setTraceLogging( true );
                        filterResult = filterExpressions[e].solve();
                        filterExpressions[e].setTraceLogging( false );
                    }
                    else {
                        filterResult = filterExpressions[e].solve();
                    }

                    if (debugLoggerDebug) {
                        debugLogger.debug( String.format("filter result alt=%d, expression=%d = %.3f", altIndex+1, e+1, filterResult));
                    }
                    if (filterResult > 0) {
                        try {

                            if ( indexDebug && traceLogger.isDebugEnabled() ) {
                                traceLogger.debug( String.format("%s [%d]:  alt = %d, name = %s, model expression = %s.", indexDebugLabel, e+1, altIndex+1, controlFile.modelEntries[e].name, modelExpressions[e].getExpression()) );
                                modelExpressions[e].setTraceLogging( true );
                                answers[e] = modelExpressions[e].solve();
                                modelExpressions[e].setTraceLogging( false );
                            }
                            else {
                                answers[e] = modelExpressions[e].solve();
                            }
                        }
                        catch ( Exception ex ) {
                            logger.error( String.format( "Exception thrown evaluating expression for: alt=%d, e=%d, expression=%s.",
                                    altIndex+1, e+1, modelExpressions[e].getExpression() ), ex );
                            throw new RuntimeException();
                        }
                    }
                    else {
                        if ( indexDebug && traceLogger.isDebugEnabled() ) {
                            traceLogger.debug( String.format("%s [%d]:  alt = %d, filter result was 0, so model expression result is 0.", indexDebugLabel, e+1, altIndex+1) );
                        }
                        answers[e] = 0;
                    }
                }
                else {
                    try {
                        if ( indexDebug && traceLogger.isDebugEnabled() ) {
                            traceLogger.debug( String.format("%s [%d]:  alt = %d, name = %s, model expression = %s.", indexDebugLabel, e+1, altIndex+1, controlFile.modelEntries[e].name, modelExpressions[e].getExpression()) );
                            modelExpressions[e].setTraceLogging( true );
                            answers[e] = modelExpressions[e].solve();
                            modelExpressions[e].setTraceLogging( false );
                        }
                        else {
                            answers[e] = modelExpressions[e].solve();
                        }
                    }
                    catch ( Exception ex ) {
                        logger.error( String.format( "Exception thrown evaluating expression for: alt=%d, e=%d, expression=%s.",
                                altIndex+1, e+1, modelExpressions[e].getExpression() ), ex );
                        throw new RuntimeException();
                    }
                }
            }

            //Multiply answer from expression.solve() if expression is part of a model entry
            //Accumulate results for alternative
            if (expressionFlags[e].isModelEntry) {
                results[altIndex] += answers[e] * coefficients[e][coeffIndex];

                if ( indexDebug && traceLogger.isDebugEnabled() ) {
                    String traceString = String.format("%s [%d]:  alt = %d, model expression = %.8f, coefficient = %.8f, cumulative utility = %.8f.", indexDebugLabel, e+1, altIndex+1, answers[e], coefficients[e][coeffIndex], results[altIndex] );
                    traceLogger.debug( traceString );
                }

            }

            // save the computed answers by alternative which can be returned to calling method if so desired.
            altAnswers[e][altIndex] = answers[e];


            //Show utility calculation for alternative
            if (debugLoggerDebug) {
                if (expressionFlags[e].isModelEntry) {
                    debugLogger.debug("alt=" + (altIndex+1) + ", expression=" + (e+1) + "entry result = " +
                            String.format("%.3f", answers[e]) + " * " +
                            String.format("%.3f", coefficients[e][coeffIndex]) + " = " +
                            (answers[e] * coefficients[e][coeffIndex]));
                }
            }

        }

    }


    /**
     * return the number of alternatives defined in the UEC control file
     */
    public int getNumberOfAlternatives () {
        return nAlternatives;
    }


    /**
     * return the number of records in the zonal data file defined in the UEC control file
     */
    public int getNumberOfZones () {

        return tableDataManager.getNumberOfZones();

    }


    public String[] getAlternativeNames() {
        return altNames;
    }


    /**
     * return the number of NL levels specified
     */
    public int getNumberOfNestedLogitLevels() {
        if ( nestedAlternatives == null )
            return 1;
        else
            return nestedAlternatives.length;
    }


    /**
     * return the array that defines NL nesting structure
     */
    public int[][] getNestedLogitNestingStructure() {
        return nestedAlternatives;
    }


    /**
     * return the array that defines NL nesting coefficients
     */
    public double[][] getNestedLogitNestingCoefficients() {
        return nestingCoefficients;
    }



    /* Distinguish scalar expressions from model expressions
     *
     * If the name field is filled in then the expression is a scalar
     * (i.e. will not be multiplied by the coefficients and returned
     */
    private void checkForScalarExpression(int expNumber) {

        String variableName = controlFile.modelEntries[expNumber].name;

        if ( (variableName != null) && (variableName.length() > 0) ) {
            expressionFlags[expNumber].isModelEntry = false;

            //Create an assignment expression
            String newExpression = variableName + "=" + modelExpressions[expNumber].getExpression();
            modelExpressions[expNumber].setExpression( newExpression );
        }
    }


    /* Check for alternative specific variable in expression
     */
    private void checkForAlternativeVariable(int expNumber) {

        String expString = modelExpressions[expNumber].getExpression().toUpperCase();

        //Check for use of built in alternative number or user defined alternative array (@@)
        if ( (expString.indexOf("$ALT") != -1 ) || (expString.indexOf("@@") != -1) ) {
            expressionFlags[expNumber].hasAlternativeVariable = true;

            //Check if orig, dest, or stop variables are the assignment variables, if so,
            //expressions with matrices need to be recalculated for each alternative if
            //they have an index that is changing
            if ( expString.startsWith("$ORIG") || expString.startsWith("$DEST") || expString.startsWith("$STOP")) {
                matrixIndexChangesByAlternative = true;

                //Keep track of which specific index is changing
                if (expString.startsWith("$ORIG")) {
                    indexChangedByAlternative.add("o");
                }
                else if (expString.startsWith("$DEST")) {
                    indexChangedByAlternative.add("d");
                }
                else if (expString.startsWith("$STOP")) {
                    indexChangedByAlternative.add("s");
                }
                else {
                    RuntimeException e = new RuntimeException("Could not determine index type");
                    logger.error("expString="+expString, e);
                }
            }
        }

        //Check for alternative variables in expression as next step
        if (! expressionFlags[expNumber].hasAlternativeVariable) {
            for (int i=0; i < altColumnName.length; i++) {
                if ( modelExpressions[expNumber].getExpression().indexOf( altColumnName[i]) != -1 ) {
                    expressionFlags[expNumber].hasAlternativeVariable = true;
                    break;
                }
            }
        }

        /*
        //Check for variables in the expression that will be updated for each alternative
        //This means the expression should be marked as needing update
        String expression = controlFile.modelEntries[expNumber].expression;
        VariableInfo[] varInfo = (VariableInfo[]) varInfoList.toArray( new VariableInfo[varInfoList.size()] );
        for (int i=0; i < varInfo.length; i++) {
            if (expression.indexOf(varInfo[i].getName()) != -1 ) {
                //logger.debug("");
                expressionFlags[expNumber].hasAlternativeVariable = true;
                break;
            }
        }
         */
    }


    /* Check for a filter expression
     */
    private void checkForFilterExpression(int expNumber) {

        String filterString = filterExpressions[expNumber].getExpression().toUpperCase();

        if ( (filterString != null) && (filterString.length() > 0) ) {
            expressionFlags[expNumber].hasFilter = true;
        }
    }



    /* Check if the result of an expression is stored in a scalar variable and the
     * expression is updated for each alternative then the variable needs to be flagged
     * so downstream expressions using this alternative will be updated for each
     * alternative.
     */
    private void checkForScalarResultChangingByAlternative(int expNumber) {

        //Check if expression is stored in a scalar variable and changes with each alternative
        if ( (! expressionFlags[expNumber].isModelEntry) && (expressionFlags[expNumber].hasAlternativeVariable) ) {

            String variableName = controlFile.modelEntries[expNumber].name;
            if (loggerDebug)
                logger.debug(variableName + ", changes by alternative");

            //Update the variable that stores the result of this expression
            int index = lookupVariableIndex(variableName);
            VariableInfo varInfo = varInfoList.get(index);
            varInfo.setChangesByAlternative(true);
        }
    }


    /** Unloads the Matrix and TableDataSet data that is being stored in memory
     * so it heap can be reclaimed by the garbage collector.
     */
    public static void clearData() {
        TableDataSetManager.getInstance().clearData();
        MatrixDataManager.getInstance().clearData();
    }

    public void setDebugOutput(boolean showDebugOutput) {
        this.debugLoggerDebug = showDebugOutput;
    }

    //------------------------ Data Reading Methods ------------------------

    public void readData() {

        //Gather information about model
        nModelEntries = controlFile.modelEntries.length;
        nAlternatives = controlFile.header.numberOfAlts;
        alternativeNames = controlFile.alternatives;
        coefficients = controlFile.coefficients;

        long startTime, endTime;
        startTime = System.currentTimeMillis();

        //TableDataSetManager handles zone, household, alternative data entries
        tableDataManager.addTableEntries( controlFile.tableEntries );

        //Read alternative entries and store relative to this UEC instance
        readAlternativeData( controlFile.tableEntries );

        //MatrixDatatManager handles zone, household, alternative data entries
        matrixDataManager.addMatrixEntries( controlFile.matrixEntries );

        endTime = System.currentTimeMillis();
        if (loggerDebug)
            logger.debug("Total time reading input files: "+(endTime-startTime) + " ms");
    }


    /*
     * Read Alternatives data.
     */
    private void readAlternativeData(DataEntry[] tableEntries) {

        long startTime, endTime;
        String fileName = null;

        int nEntries = tableEntries.length;

        startTime = System.currentTimeMillis();
        for (int i=0; i < nEntries; i++) {

            if (tableEntries[i].type.toUpperCase().startsWith("A") ) {
                try {
                    fileName = tableEntries[i].fileName;

                    CSVFileReader reader = new CSVFileReader();
                    altTableData = reader.readFile(new File(fileName));

                    altTableData.buildIndex(1);
                    altColumnName = altTableData.getColumnLabels();

                    // get the index of the alternatives field
                    int altPosition = altTableData.getColumnPosition( "a" );
                    if (altPosition <= 0) {
                        logger.error( "No alternative field, a, was found as a field in the alternatives TableDataSet.");
                        System.exit(1);
                    }

                    // save the String representation of the integer alternative number as its name when read from a file.
                    alternativeNames = new ModelAlternative[altTableData.getRowCount()];
                    for (int j=1; j <= alternativeNames.length; j++) {
                        int a = (int)altTableData.getValueAt( j, altPosition );
                        alternativeNames[j-1] = new ModelAlternative(a, Integer.toString(a));
                    }

                }
                catch (IOException e) {
                    e.printStackTrace();
                    System.exit(1);
                }
                endTime = System.currentTimeMillis();
                if (loggerDebug)
                    logger.debug("Read "+ fileName + " : "+(endTime-startTime) + " ms");

                break;  //read the first file only
            }
        }

        if ( loggerDebug ) {
            StringBuffer sb = new StringBuffer(256);
            sb.append("Alternative data columns: ");
            for (int i = 0; i < altColumnName.length; i++) {
                sb.append( altColumnName[i] + ", " );
            }
            logger.debug(sb.toString());
        }
    }


    //------------------------ Value Methods ------------------------

    private double getScalarValue(int variableIndex) {
        return scalarValue[varInfo[ variableIndex].getValueIndex() ];
    }


    private double getZoneValue(int variableIndex) {

        //returns a value from the zoneDataTable indexed by zone or stop
        return tableDataManager.getZoneValueForIndex( internalVariable[ varInfo[variableIndex].getInternalIndex() ],
                varInfo[variableIndex].getValueIndex() );

        //return tableDataManager.getZoneValueForIndex( internalVariable[ZONE_INDEX], varInfo[variableIndex].getValueIndex() );
    }


    private double getHouseHoldValue(int variableIndex) {
        return tableDataManager.getHouseholdValueForIndex( internalVariable[HH_INDEX], varInfo[variableIndex].getValueIndex() );
    }


    private double getAlternativeValue(int variableIndex) {
        return altTableData.getIndexedValueAt( internalVariable[ALT_INDEX], varInfo[variableIndex].getValueIndex() );
    }


    private double getMatrixValue(int variableIndex) {

        return  matrixDataManager.getValueForIndex( varInfo[variableIndex].getValueIndex(),
                varInfo[variableIndex].getOrigIndex(),
                varInfo[variableIndex].getDestIndex() );
    }


    private double getMatrixCollectionValue(int variableIndex) {

        return  matrixDataManager.getValueForIndex( varInfo[variableIndex].getValueIndex(),
                varInfo[variableIndex].getOrigIndex(),
                varInfo[variableIndex].getDestIndex(),
                varInfo[variableIndex].getNameIndex());
    }

    private double getMatrixArrayValue(int variableIndex, int arrayIndex) {

        return matrixDataManager.getArrayValueForIndex(
                varInfo[variableIndex].getValueIndex(),
                varInfo[variableIndex].getOrigIndex(),
                varInfo[variableIndex].getDestIndex(), arrayIndex);
    }

    private double getMatrixCollectionArrayValue(int variableIndex,
            int arrayIndex) {

        return matrixDataManager.getArrayValueForIndex(
                varInfo[variableIndex].getValueIndex(),
                varInfo[variableIndex].getOrigIndex(),
                varInfo[variableIndex].getDestIndex(),
                varInfo[variableIndex].getNameIndex(), arrayIndex);
    }

    private double getObjectMethodValue(int variableIndex) {
        double value = 0;

        int index = varInfo[variableIndex].getValueIndex();

        //Invoke method on user defined object
        value = methodInvoker.invoke( dmuObject, index, internalVariable[ALT_INDEX]);

        return value;
    }


    private double getInternalValue(int variableIndex) {

        return internalVariable[ varInfo[variableIndex].getValueIndex() ];
    }


    private void setInternalValue(int variableIndex, double value) {

        internalVariable[ varInfo[variableIndex].getValueIndex() ] = (int)value;
    }

    //------------------------ Indexing Methods ------------------------


    private int lookupVariableIndex(String variableName) {

        int index = -1;

        //Do a linear search to find first occurrance of requested variable name
        //in variable table and return the index
        for (int i=0; i < varInfoList.size(); i++) {
            VariableInfo varInfo = varInfoList.get(i);
            if (varInfo.getName().equalsIgnoreCase(variableName)) {
                index = i;
                break;
            }
        }

        return index;
    }


    private int getScalarVariableIndex(String variableName) {

        int index = -1;

        //Do a linear search to find requested variable name and return the index
        for (int i=0; i < scalarIndex.size(); i++) {
            String name = scalarIndex.get(i);
            if (name.equalsIgnoreCase(variableName)) {
                index = i;
                break;
            }
        }
        //Didn't find variableName - add name to list of scalars and to list of variables
        if (index == -1) {
            scalarIndex.add(variableName);

            VariableInfo varInfo = new VariableInfo(variableName, "", VariableType.SCALAR);
            varInfo.setValueIndex( scalarIndex.size()-1 );  //zero based

            varInfoList.add(varInfo);
        }

        //return position of last element added as index
        return varInfoList.size() - 1;
    }


    private int getObjectMethodIndex(String variableName) {

        int index = -1;
        boolean arrayInd = false;

        String modifiedName;
        String getterName;

        //Check whether this variable is of type array
        if (variableName.startsWith("@@")) {
            arrayInd = true;
        }

        //Strip off the special symbol
        if (variableName.startsWith("@@")) {
            arrayInd = true;
            modifiedName = variableName.substring(2); //Strip @@ from beginning
        }
        else {
            arrayInd = false;
            modifiedName = variableName.substring(1); //Strip @ from beginning
        }

        //Construct a java getter method name
        getterName = "get" + Character.toUpperCase( modifiedName.charAt(0) ) +
                modifiedName.substring( 1 );

        try {
            index = invokerTemplate.addMethod( getterName, arrayInd );
        }
        catch (NoSuchMethodException e) {
            String msg = "Could not find method in user class, " + getterName + "()";
            logger.error(msg);
            throw new RuntimeException(msg);
        }

        return index;
    }


    private int getInternalVariableIndex(String variableName) {

        int index = -1;

        String modifiedName = variableName.substring(1); //Strip $ from beginning

        //indexSynonyms = { 'o', 'd', 's', 'z', 'h', 'a' };

        if (modifiedName.toUpperCase().startsWith("ORIG")) {
            index = lookupSynonymIndex('o');
        }
        else
            if (modifiedName.toUpperCase().startsWith("DEST")) {
                index = lookupSynonymIndex('d');
            }
            else
                if (modifiedName.toUpperCase().startsWith("STOP")) {
                    index = lookupSynonymIndex('s');
                }
                else
                    if (modifiedName.toUpperCase().startsWith("ZONE")) {
                        index = lookupSynonymIndex('z');
                    }
                    else
                        if (modifiedName.toUpperCase().startsWith("HH")) {
                            index = lookupSynonymIndex('h');
                        }
                        else
                            if (modifiedName.toUpperCase().equals("ALT")) {
                                index = lookupSynonymIndex('a');
                            }
                            else {
                                throw new RuntimeException("getInternalVariableIndex, unknown variableIndex: "+variableName);
                            }

        return index;
    }


    private int lookupSynonymIndex(char c) {

        int index = -1;
        for (int i=0; i < indexSynonyms.length; i++ ) {
            if (indexSynonyms[i] == c) {
                index = i;
                break;
            }
        }

        return index;
    }


    /**
     * Returns the index of a variable in the varInfo list. After all expressions are
     * parsed, this will be the index in the varInfo array.
     *
     * A VariableInfo object is created for each new variable to build up a list of
     * variables. As new variables are added to the list the index values are determined.
     *
     * @param variableName
     * @return the index of the variable
     */
    private int getVariableIndex(String variableName) {

        boolean found = false;

        VariableInfo varInfo = new VariableInfo(variableName, "");

        //Check scalar variables
        if (!found) {
            for (int i=0; i < scalarIndex.size(); i++) {
                String name = scalarIndex.get(i);
                if (name.equalsIgnoreCase(variableName)) {
                    varInfo.setType(VariableType.SCALAR);
                    varInfo.setValueIndex(i);
                    found=true;
                }
            }
        }

        //Check zone variables
        if (! found) {
            int zoneIndex = tableDataManager.findZoneIndex(variableName);

            if (zoneIndex >= 0) {
                varInfo.setType(VariableType.ZONE);
                varInfo.setValueIndex(zoneIndex);

                computeZoneIndex(varInfo);
                found=true;
            }
        }
        //Check household variables
        if (! found) {
            int hhIndex = tableDataManager.findHouseholdIndex(variableName);

            if (hhIndex >= 0) {
                varInfo.setType(VariableType.HOUSEHOLD);
                varInfo.setValueIndex(hhIndex);
                found=true;
            }
        }
        //Check alternative variables
        if (! found)
            for (int i = 0; i < altColumnName.length; i++) {
                if (altColumnName[i].equalsIgnoreCase(variableName)) {
                    varInfo.setType(VariableType.ALTERNATIVE);
                    varInfo.setValueIndex(i+1);   //TableDataSet set is 1 based
                    found=true;

                    //Flag this expression as having an alternative specific variable
                    expressionFlags[expressionBeingParsed].hasAlternativeVariable = true;
                }
            }
        //Check matrix variables
        if (! found) {
            int matrixIndex = matrixDataManager.findMatrixIndex(variableName);

            if (matrixIndex >= 0) {
                varInfo.setType(VariableType.MATRIX);
                varInfo.setValueIndex( matrixIndex );

                computeMatrixIndex(varInfo);
                found=true;
            }
        }
        //Check matrix collection variables
        if (! found) {
            int collectionIndex = matrixDataManager.findMatrixCollectionIndex(variableName);

            if (collectionIndex >= 0) {
                varInfo.setType(VariableType.MATRIX_COLLECTION);
                varInfo.setValueIndex( collectionIndex );
                varInfo.setNameIndex( matrixDataManager.findMatrixCollectionNameIndex(variableName) );

                computeMatrixIndex(varInfo);
                found=true;
            }

        }
        //Check object field variables
        if (! found) {
            if (variableName.startsWith("@")) {
                varInfo.setType(VariableType.OBJECT);
                varInfo.setValueIndex( getObjectMethodIndex(variableName) );
                found=true;
            }
        }
        //Check internal variables
        if (! found) {
            if (variableName.startsWith("$")) {
                varInfo.setType(VariableType.INTERNAL);
                varInfo.setValueIndex( getInternalVariableIndex(variableName) );
                found=true;
            }
        }

        //Signal that variable was not identified
        if (! found) {
            return -1;
        }

        //Store variable information
        varInfoList.add( varInfo );

        //return position of last element added as index
        return ( varInfoList.size()-1 );
    }


    /*
     * Determine the index values for the current zone variable - zone variables can
     * be indexed by zone number or stop number
     */
    private void computeZoneIndex(VariableInfo varInfo) {

        //Set default index for zone variables to zone
        varInfo.setInternalIndex(ZONE_INDEX);

        //A small hack so that all zone filter expressions will be indexed by "z"
        if (expressionBeingParsedIsFilter) {
            //already set a few lines up
            return;
        }

        //Select the first index value out of the index column
        String indexString = expressionIndex[expressionBeingParsed].getIndexEntry(0);

        //Index by zone variable by stop value if specified
        if ( (indexString != null) && (indexString.equalsIgnoreCase("s")) ) {
            varInfo.setInternalIndex(SZ_INDEX);
        }

        logger.debug("zone variable=" + varInfo.name + " using index=" + indexSynonyms[varInfo.internalIndex]);
    }


    /*
     * Determine the index values for the current matrix variable
     */
    private void computeMatrixIndex(VariableInfo varInfo) {

        //A small hack so that all filter expressions will be indexed by "od"
        if (expressionBeingParsedIsFilter) {
            varInfo.setOrigIndex(OZ_INDEX);
            varInfo.setDestIndex(DZ_INDEX);
            return;
        }

        String indexString = expressionIndex[expressionBeingParsed].getIndexEntry(currentMatrixVariable);

        if ( (indexString == null) || (indexString.length() < 2) ) {
            logger.warn("Incomplete indexing information for expression: "+(expressionBeingParsed+1)+
                    ", matrix="+varInfo.getName());
        }

        //If $orig, $dest, or $stop has been set then see if this matrix variable has an
        //index that is affected
        if (matrixIndexChangesByAlternative) {

            boolean flag = false;
            if ( indexChangedByAlternative.contains(indexString.substring(0,1)) )
                flag = true;
            if (  indexChangedByAlternative.contains(indexString.substring(1,2)) )
                flag = true;

            //Mark this expression as needing to be solved for each alternative
            if (flag) {
                //varInfo.setChangesByAlternative(true);
                expressionFlags[expressionBeingParsed].hasAlternativeVariable = true;
            }
        }

        int index;

        //Find the origin index
        index =  lookupSynonymIndex(indexString.charAt(0));
        varInfo.setOrigIndex(index);

        //Find the destination index
        index =  lookupSynonymIndex(indexString.charAt(1));
        varInfo.setDestIndex(index);

        //Increment matrix variable pointer
        currentMatrixVariable++;
    }


    public TableDataSet getZoneData() {
        return tableDataManager.getZoneData();
    }

    public MatrixDataManager getMatrixData() {
        return MatrixDataManager.getInstance();
    }


    public TableDataSet getHouseholdData() {
        return tableDataManager.getHouseholdData();
    }

    public TableDataSet getAlternativeData() {
        return altTableData;
    }

    public String getMethodInvokerSourceCode() {
        return invokerTemplate.getGeneratedSourceCode();
    }

    public String getVariableTable() {
        return variableTableAsString;
    }

    public double[][] getAnswersArray() {
        return altAnswers;
    }


    //------------------------ Variable Table Methods ------------------------

    /**
     * Called to get an index value for a variable
     */
    @Override
    public final int getIndexValue(String variableName) {

        int index = getVariableIndex(variableName);

        if (index < 0) {
            throw new RuntimeException("getIndexValue, could not calculate index: "+variableName);
        }

        if ( loggerDebug ) {
            logger.debug(variableName+", index=" + index);
        }

        //Check if variable is updated by alternative - find the first occurance of the
        //variable in the table
        int firstIndex = lookupVariableIndex(variableName);
        VariableInfo firstVarInfo = varInfoList.get(firstIndex);

        if (firstVarInfo.isChangesByAlternative()) {

            //Update this occurrance of the variable
            VariableInfo varInfo = varInfoList.get(index);
            varInfo.setChangesByAlternative(true);

            //Flag the expression as having an alternative specific variable
            expressionFlags[expressionBeingParsed].hasAlternativeVariable = true;
        }

        return index;
    }

    /**
     * Called to get an index value for an assignment variable
     */
    @Override
    public final int getAssignmentIndexValue(String variableName) {

        int index = getVariableIndex(variableName);

        //Treat as a new scalar variable
        if (index == -1) {
            index = getScalarVariableIndex(variableName);
        }

        if (loggerDebug) {
            logger.debug(variableName+", index: "+index+"  (will hold assignment result)");
        }

        return index;
    }

    /**
     *  Called to get a value for an indexed variable
     */
    @Override
    public final double getValueForIndex(int variableIndex) {

        int type = varInfo[variableIndex].getType();

        switch (type) {
        case VariableType.SCALAR:            return getScalarValue(variableIndex);
        case VariableType.ZONE:              return getZoneValue(variableIndex);
        case VariableType.HOUSEHOLD:         return getHouseHoldValue(variableIndex);
        case VariableType.ALTERNATIVE:       return getAlternativeValue(variableIndex);
        case VariableType.MATRIX:            return getMatrixValue(variableIndex);
        case VariableType.MATRIX_COLLECTION: return getMatrixCollectionValue(variableIndex);
        case VariableType.OBJECT:            return getObjectMethodValue(variableIndex);
        case VariableType.INTERNAL:          return getInternalValue(variableIndex);
        default:
            throw new RuntimeException("getValueForIndex, unknown variableIndex: "+variableIndex);
        }
    }

    /**
     * Called to set a value for a given variable name
     */
    @Override
    public final void setValue(String variableName, double variableValue) {
        throw new UnsupportedOperationException("setValue(String, double) not supported");
    }

    /**
     * Called to set a value for a given variable index. For now, this method
     * only handles scalar values returned from an expression
     */
    @Override
    public final void setValue(int variableIndex, double variableValue) {

        int type = varInfo[variableIndex].getType();

        switch (type) {
        case VariableType.SCALAR:
            scalarValue[ varInfo[variableIndex].getValueIndex() ] = variableValue;
            break;
        case VariableType.INTERNAL:
            setInternalValue(variableIndex, variableValue);
            break;
        default:
            throw new RuntimeException("settValue(int, double) unknown variableIndex: "+variableIndex);
        }
    }


    /**
     * Defines information that describes a variable. Most notably information
     * about indexing is stored.
     *
     */
    public class VariableInfo implements Serializable {

        private static final long serialVersionUID = 1473236201543329597L;
        private String name;

        private int type;

        //Holds value of internal index eg. zone, stop - allows a zone variable to
        // be indexed by zone or stop number
        private int internalIndex = -1;

        //Holds index values for scalar variables
        private int valueIndex = -1;

        //Holds index values for two dimensional variables, eg. matrices
        //The value of these variables points to the internalVariable[]
        private int origIndex = -1;
        private int destIndex = -1;

        //Used to index named variables, eg. matrices in matrix collection
        private int nameIndex = -1;

        private boolean changesByAlternative = false;

        public VariableInfo(String name, String description) {
            this(name, description, -1);
        }

        public VariableInfo(String name, String description, int type) {
            this.name = name;
            this.type = type;
        }

        public String getName() {
            return name;
        }

        public int getType() {
            return type;
        }

        public void setType(int type) {
            this.type = type;
        }

        public int getInternalIndex() {
            return internalIndex;
        }

        public void setInternalIndex(int internalIndex) {
            this.internalIndex = internalIndex;
        }

        public int getOrigIndex() {
            return internalVariable[origIndex];
        }

        public void setOrigIndex(int origIndex) {
            this.origIndex = origIndex;
        }

        public int getDestIndex() {
            return internalVariable[destIndex];
        }

        public void setDestIndex(int destIndex) {
            this.destIndex = destIndex;
        }

        public int getNameIndex() {
            return nameIndex;
        }

        public void setNameIndex(int nameIndex) {
            this.nameIndex = nameIndex;
        }

        public int getValueIndex() {
            return valueIndex;
        }

        public void setValueIndex(int valueIndex) {
            this.valueIndex = valueIndex;
        }

        public boolean isChangesByAlternative() {
            return changesByAlternative;
        }

        public void setChangesByAlternative(boolean changesByAlternative) {
            this.changesByAlternative = changesByAlternative;
        }

        //-------- Return the absolute values of each index

        public String getTypeName() {

            switch (type) {
            case VariableType.SCALAR:            return "Scalar";
            case VariableType.ZONE:              return "Zone";
            case VariableType.HOUSEHOLD:         return "Household";
            case VariableType.ALTERNATIVE:       return "Alternative";
            case VariableType.MATRIX:            return "Matrix";
            case VariableType.MATRIX_COLLECTION: return "Matrix Collection";
            case VariableType.OBJECT:            return "Object";
            case VariableType.INTERNAL:          return "Internal";
            }

            return "unknown";
        }

        public int getValueIndexValue() {
            return valueIndex;
        }

        public int getOrigIndexValue() {
            //return indexSynonyms[origIndex];
            return origIndex;
        }

        public int getDestIndexValue() {
            //return indexSynonyms[destIndex];
            return destIndex;
        }

        public int getNameIndexValue() {
            return nameIndex;
        }

    }

    /**
     * Called to get an value for an indexed, arrayed variable e.g. IVT[PERIOD]
     */
    @Override
    public final double getValueForIndex(int variableIndex, int arrayIndex) {
        int type = varInfo[variableIndex].getType();

        switch (type) {
        case VariableType.MATRIX:
            return getMatrixArrayValue(variableIndex, arrayIndex);
        case VariableType.MATRIX_COLLECTION:
            return getMatrixCollectionArrayValue(variableIndex, arrayIndex);
        default:
            throw new RuntimeException(
                    "getValueForIndex, array subscript only works on MATRIX types: "
                            + variableIndex);
        }
    }

}
