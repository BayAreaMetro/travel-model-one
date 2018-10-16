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
package com.pb.common.daf.test;

import com.pb.common.daf.Message;
import com.pb.common.daf.MessageProcessingTask;
import com.pb.common.util.ResourceUtil;

import java.util.ResourceBundle;

import org.apache.log4j.Logger;


/**
 * This class will extract the composite buy and sell utilities
 * of a commodity in each zone from a message and set those
 * values into the appropriate CommodityZUtility object that
 * exists in memory.
 *
 * @author Christi Willison
 * @version Apr 28, 2004
 */
public class SetupResultProcessorTask extends MessageProcessingTask {
    Logger setupResultProcessorLogger = Logger.getLogger(SetupResultProcessorTask.class);
    static int nodeCounter = 0;
    private int nWorkQueues = 0;
    private ResourceBundle testdafRb;
    String scenarioName;

    public void onStart(){
        setupResultProcessorLogger.info( "***" + getName() + " started");
        
        testdafRb = ResourceUtil.getResourceBundle("testdaf_msgCrazy");
        nWorkQueues = (Integer.parseInt(ResourceUtil.getProperty(testdafRb,"nNodes"))-1);
    }

    public void onMessage(Message msg){
        setupResultProcessorLogger.info( getName() + " received a message from " + msg.getSender() );
        nodeCounter++;
        if(nodeCounter == nWorkQueues){
            setupResultProcessorLogger.info("Signaling that all nodes have been set up.");
            ServerTask.signalResultsProcessed();
        }
     }
}
