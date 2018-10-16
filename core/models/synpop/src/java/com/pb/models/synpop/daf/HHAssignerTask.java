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
package com.pb.models.synpop.daf;

import com.pb.common.daf.Message;
import com.pb.common.daf.MessageProcessingTask;
import com.pb.common.util.ResourceUtil;
import com.pb.models.synpop.SPG;
import static com.pb.models.synpop.daf.MESSAGE_IDS.*;
import org.apache.log4j.Logger;

import java.io.File;
import java.util.HashMap;
import java.util.Random;
import java.util.ResourceBundle;

/**
 * HHAssignerTask is a class that ...
 *
 * @author Christi Willison
 * @version 1.0,  May 14, 2009
 */
public class HHAssignerTask extends MessageProcessingTask {

    protected static Logger logger = Logger.getLogger(HHAssignerTask.class);

    SPG spg;
    private static int categoriesProcessed = 0;

    HashMap globalPropertyMap;

    public void onStart(){
        logger.info("*************************" + getName() + " has started ************");
        logger.info("WorkerTask: Reading RunParams.properties file");
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
        globalPropertyMap = ResourceUtil.changeResourceBundleIntoHashMap(globalRb);

        String spgClassName = (String) spgPropertyMap.get("SPGNew.class");
        logger.info("Worker Task: SPG will be using the " + spgClassName + " for the SPG2 algorithm");

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

        spg.spgNewInit( spgPropertyMap, globalPropertyMap,
                Integer.toString(baseYear), Integer.toString(baseYear + timeInterval) );

        logger.info("Worker Task: Setting up SPG2");
        spg.setupSpg2();
        spg.getRegionalDollarsPerJob();



    }

    public void onMessage(Message msg){
        String msgId = msg.getId();
        logger.info(getName() + ", Received messageId=" + msg.getId()
                + " message from=" + msg.getSender());

        if (msgId.equals(HA_WORK_MESSAGE_ID)) {

            int category = msg.getIntValue(MESSAGE_IDS.CATEGORY);
            String categoryLabel = msg.getStringValue(MESSAGE_IDS.CATEGORY_LABEL);
            double[][] regionLaborDollarsPerJob = (double[][]) msg.getValue(MESSAGE_IDS.REGION_DOLLARS);
            logger.info(getName() + " received HH Category " + categoryLabel + " to process");

            Random randomGenerator = new Random();
            randomGenerator.setSeed( Integer.parseInt(globalPropertyMap.get("randomSeed").toString()));

            String[] mtResults = spg.assignZonesForHhCategory( category, regionLaborDollarsPerJob, categoryLabel, randomGenerator );
            categoriesProcessed++;

            Message returnMsg = createMessage();
            returnMsg.setId(MESSAGE_IDS.RP_ASSIGNER_RESULTS_MESSAGE_ID);
            returnMsg.setValue(MESSAGE_IDS.CATEGORY, category);
            returnMsg.setValue(MESSAGE_IDS.CATEGORY_LABEL, categoryLabel);
            returnMsg.setValue(MESSAGE_IDS.RP_ASSIGNER_RESULTS, mtResults);
            sendTo("ResultsQueue", returnMsg);

        } else if (msgId.equals(HA_SEND_SUMMARIES_ID)) {
            Message returnMsg = createMessage();
            returnMsg.setId(RP_ASSIGNER_SUMMARY_RESULTS_ID);
            returnMsg.setIntValue(RP_CATEGORY_COUNT,categoriesProcessed);
            returnMsg.setValue(RP_SUMMARY_HHS,spg.totalHhsByTaz);
            returnMsg.setValue(RP_SUMMARY_HH_INCOME, spg.totalHhIncomeByTaz);
            returnMsg.setValue(RP_SUMMARY_PERSONS,spg.totalPersonsByTaz);
            returnMsg.setValue(RP_SUMMARY_WORKERS,spg.totalWorkersByTaz);
            returnMsg.setValue(RP_SUMMARY_PERSON_AGES,spg.personAgesByTaz);
            returnMsg.setValue(RP_SUMMARY_HHS_BY_CATEGORY,spg.hhsByTazCategory);
            sendTo("ResultsQueue", returnMsg);
        }


    }
    
}
