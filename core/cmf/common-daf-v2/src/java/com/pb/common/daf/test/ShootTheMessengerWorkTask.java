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
 * This class will extract the surplus and derivative of a
 * commodity in each exchange zone.  The surplus and derivative
 * will be set in the appropriate exchange zone.
 * 
 * @author Christi Willison
 * @version Apr 28, 2004
 */
public class ShootTheMessengerWorkTask extends MessageProcessingTask {
    Logger stmWorkLogger = Logger.getLogger(ShootTheMessengerWorkTask.class);
    
    public void onStart(){
        stmWorkLogger.info("*************************" + getName() + " has started ************");
    }
    
    public void onMessage(Message msg){
        if(stmWorkLogger.isDebugEnabled()) {
            stmWorkLogger.debug( getName() + " received " + msg.getId() + ", from " + msg.getSender() );
        }
        String number = msg.getStringValue("Bullet Number");

        stmWorkLogger.info(getName() + " sending bullet number " + number + " to STMResultProcessor task.");
        
        Message resultMsg = mFactory.createMessage();
        resultMsg.setId("STMWorkMessage_"+ number + "_fromWorker");
        resultMsg.setValue("Bullet Number", number);
        
        if(stmWorkLogger.isDebugEnabled()) {
            stmWorkLogger.debug( getName() + " sending " + resultMsg.getId() + ", to " + "STMResultsQueue" );
        }
        
        sendTo("STMResultsQueue",resultMsg);

    }
}
