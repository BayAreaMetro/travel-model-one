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
 * This class will calculate the composite buy and sell utilities
 * of a commodity in each zone when a message bearing a commodity
 * name is received.  It will return the buy and sell CUs in an array.
 * 
 * @author Christi Willison
 * @version Apr 27, 2004
 */
public class PinkSlipWorkTask extends MessageProcessingTask {
    Logger psWorkLogger = Logger.getLogger(PinkSlipWorkTask.class);
    public void onStart() {
        psWorkLogger.info("*************************" + getName() + " has started ************");
    }

    public void onMessage(Message msg) {
        if(psWorkLogger.isDebugEnabled()) {
            psWorkLogger.debug( getName() + " received " + msg.getId() + ", from" + msg.getSender() );
        }
        
        String number = msg.getStringValue("Slip Number");
        String iter = msg.getStringValue("Iteration");
        
        Message resultMsg = mFactory.createMessage();
        resultMsg.setId("Iteration,"+iter+",PSWorkMessage_fromWorker," + number);
        resultMsg.setValue("Slip Number",number);
        resultMsg.setValue("Iteration", iter);
        
        if(psWorkLogger.isDebugEnabled()) {
            psWorkLogger.debug( getName() + " sending " + resultMsg.getId() + ", to " + "PSResultsQueue" );
        }
        
        sendTo("PSResultsQueue",resultMsg);
    }


}
