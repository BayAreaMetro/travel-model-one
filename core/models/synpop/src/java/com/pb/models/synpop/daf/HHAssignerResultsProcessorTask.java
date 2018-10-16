package com.pb.models.synpop.daf;

import com.pb.common.util.ResourceUtil;
import com.pb.common.daf.MessageProcessingTask;
import com.pb.common.daf.Message;
import com.pb.models.synpop.SPG;
import static com.pb.models.synpop.daf.MESSAGE_IDS.*;

import java.util.ResourceBundle;
import java.util.HashMap;
import java.io.File;

import org.apache.log4j.Logger;

/**
 * This class takes the results from the worker tasks
 * and compiles the results.  it will write out several output
 * files that are needed by other modules.
 */
public class HHAssignerResultsProcessorTask extends MessageProcessingTask {
    private static final Logger logger = Logger.getLogger(HHAssignerResultsProcessorTask.class);

    private SPG spg;
    private int haResultsRemaining;
    private int haSummariesRemaining;

    public void onStart(){
        logger.info("Reading RunParams.properties file");
        ResourceBundle runParamsRb = ResourceUtil.getResourceBundle("RunParams");
        int timeInterval = Integer.parseInt(ResourceUtil.getProperty(runParamsRb,"timeInterval"));
        logger.info("\tTime Interval: " + timeInterval);
        int baseYear = ResourceUtil.getIntegerProperty(runParamsRb,"baseYear",1990);
        logger.info("\tBase Year: " + baseYear);
        String pathToSpgRb = ResourceUtil.getProperty(runParamsRb,"pathToAppRb");
        logger.info("\tResourceBundle Path: " + pathToSpgRb);
        String pathToGlobalRb = ResourceUtil.getProperty(runParamsRb,"pathToGlobalRb");
        logger.info("\tResourceBundle Path: " + pathToGlobalRb);

        ResourceBundle spgRb = ResourceUtil.getPropertyBundle(new File(pathToSpgRb));
        ResourceBundle globalRb = ResourceUtil.getPropertyBundle(new File(pathToGlobalRb));

        HashMap spgPropertyMap = ResourceUtil.changeResourceBundleIntoHashMap(spgRb);
        HashMap globalPropertyMap = ResourceUtil.changeResourceBundleIntoHashMap(globalRb);

        String spgClassName = (String) spgPropertyMap.get("SPGNew.class");
        logger.info("SPG will be using the " + spgClassName + " for the SPG2 algorithm");

        Class spgClass = null;
        spg = null;
        try {
            spgClass = Class.forName(spgClassName);
            spg = (SPG) spgClass.newInstance();
        } catch (ClassNotFoundException e) {
            e.printStackTrace();
        } catch (InstantiationException e) {
            logger.fatal("Can't create new instance of SPGNew of type "+spgClass.getName());
            e.printStackTrace();
            throw new RuntimeException(e);
        } catch (IllegalAccessException e) {
            logger.fatal("Can't create new instance of SPGNew of type "+spgClass.getName());
            e.printStackTrace();
            throw new RuntimeException(e);
        }

        spg.spgNewInit( spgPropertyMap, globalPropertyMap,Integer.toString(baseYear), Integer.toString(baseYear + timeInterval) );



        haResultsRemaining = spg.numIncomeSizes;
        haSummariesRemaining = spg.numIncomeSizes;
    }

    public void onMessage(Message msg) {
        logger.info(getName() + ", Received messageId=" + msg.getId()
                + " message from=" + msg.getSender());
        String msgId = msg.getId();

        if (msgId.equals(RP_ASSIGNER_HH_ARRAY_SIZE_ID)) {
            int hhArraySize = msg.getIntValue(RP_ARRAY_SIZE);
            SPG.mtResults = new String[hhArraySize][];
            SPGMasterTask.signalResultsProcessed();
        } else if (msgId.equals(RP_ASSIGNER_RESULTS_MESSAGE_ID)) {
            logger.info("ResultsProcessor: Processing HH Category " + msg.getStringValue(CATEGORY_LABEL));
            SPG.mtResults[msg.getIntValue(CATEGORY)] =
                    (String[]) msg.getValue(RP_ASSIGNER_RESULTS);
            haResultsRemaining--;
            if (haResultsRemaining == 0) {
                SPGMasterTask.signalResultsProcessed();
            }
        } else if (msgId.equals(RP_WRITE_SPG2_OUTPUT_FILE_MESSAGE_ID)) {
            logger.info("ResultsProcessor: Writing spg2 output file.");
            spg.writeSPG2OutputFile();
            SPGMasterTask.signalResultsProcessed();
        } else if (msgId.equals(RP_ASSIGNER_SUMMARY_RESULTS_ID)) {
            int[] hhs = (int[]) msg.getValue(RP_SUMMARY_HHS);
            int[] hhIncome = (int[]) msg.getValue(RP_SUMMARY_HH_INCOME);
            int[] persons = (int[]) msg.getValue(RP_SUMMARY_PERSONS);
            int[] workers = (int[]) msg.getValue(RP_SUMMARY_WORKERS);
            int[][] personAges = (int[][]) msg.getValue(RP_SUMMARY_PERSON_AGES);
            int[][] hhCategories = (int[][]) msg.getValue(RP_SUMMARY_HHS_BY_CATEGORY);
            for (int i = 0; i < hhs.length; i++) {
                spg.totalHhsByTaz[i] += hhs[i];
                spg.totalHhIncomeByTaz[i] += hhIncome[i];
                spg.totalPersonsByTaz[i] += persons[i];
                spg.totalWorkersByTaz[i] += workers[i];
                for (int j = 0; j < personAges[i].length; j++)
                    spg.personAgesByTaz[i][j] += personAges[i][j];
                for (int j = 0; j < hhCategories[i].length; j++)
                    spg.hhsByTazCategory[i][j] += hhCategories[i][j];
            }
            haSummariesRemaining -= msg.getIntValue(RP_CATEGORY_COUNT);
            if (haSummariesRemaining == 0) {
                spg.writeZonalSummaryToCsvFile();
                SPGMasterTask.signalResultsProcessed();
            }
        }
    }



}
