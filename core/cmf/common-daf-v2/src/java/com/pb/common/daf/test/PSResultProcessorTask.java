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

import org.apache.log4j.Logger;

import com.pb.common.daf.Message;
import com.pb.common.daf.MessageProcessingTask;

/**
 * This class will extract the composite buy and sell utilities
 * of a commodity in each zone from a message and set those
 * values into the appropriate CommodityZUtility object that
 * exists in memory.
 *
 * @author Christi Willison
 * @version Apr 28, 2004
 */
public class PSResultProcessorTask extends MessageProcessingTask {
    Logger PSResultProcessorLogger = Logger.getLogger(PSResultProcessorTask.class);
    static int slipCounter = 0;
    
    public void onStart(){
        PSResultProcessorLogger.info( "***" + getName() + " started");
    }

    public void onMessage(Message msg){
        if(PSResultProcessorLogger.isDebugEnabled()) {
            PSResultProcessorLogger.debug( getName() + " received " + msg.getId() + ", from " + msg.getSender() );
        }
        
        slipCounter++;
        String number = msg.getStringValue("Slip Number");
        
        //check to see if we have received all commmodity values.  If so, send the signal
        //queue a message that we are complete.
        if(slipCounter >= ServerTask.nPinkSlips){
            slipCounter=0;
            PSResultProcessorLogger.info("Signaling that all pink slips have been processed.");
            ServerTask.signalResultsProcessed();
        }
    }
}
