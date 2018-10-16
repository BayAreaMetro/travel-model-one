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
 * @author Christi Willison
 * @version Apr 27, 2004
 */
public class MailDeliveryWorkTask extends MessageProcessingTask {
    Logger mdWorkLogger = Logger.getLogger(MailDeliveryWorkTask.class);
    public void onStart() {
        mdWorkLogger.info("************************* " + getName() + " has started ************");
    }

    public void onMessage(Message msg){
        if(mdWorkLogger.isDebugEnabled()) {
            mdWorkLogger.debug( getName() + " received " + msg.getId() + ", from " + msg.getSender() );
        }
        String number = msg.getStringValue("Letter Number");
        String iter = msg.getStringValue("Iteration");

        //create message to send to results queue
        Message resultMsg = mFactory.createMessage();
        resultMsg.setId("Iteration,"+iter+",MDWorkMessage_fromWorker,"+ number);
        resultMsg.setValue("Iteration", iter);
        
        if(mdWorkLogger.isDebugEnabled()) {
            mdWorkLogger.debug( getName() + " sending " + resultMsg.getId() + ", to " + "MDResultsQueue" );
        }

        sendTo("MDResultsQueue",resultMsg);
    }
}
