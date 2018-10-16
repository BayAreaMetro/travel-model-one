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
 * This class will receive a message from the ShootTheMessengerWorkTask
 * that a commodity's buying and selling flows have been written out.  When
 * all commodities have been processed it will signal to the ServerTask
 * that we are finished.
 *
 * @author Christi Willison
 * @version Apr 28, 2004
 */
public class STMResultProcessorTask extends MessageProcessingTask {
    Logger STMResultProcessorLogger = Logger.getLogger(STMResultProcessorTask.class);
    static int bulletCounter = 0;
    
    public void onStart(){
        STMResultProcessorLogger.info( "***" + getName() + " started");
    }

    public void onMessage(Message msg){
        if(STMResultProcessorLogger.isDebugEnabled()) {
            STMResultProcessorLogger.debug( getName() + " received " + msg.getId() + ", from " + msg.getSender() );
        }
        bulletCounter++;
        String number = msg.getStringValue("Bullet Number");
        
        //check to see if we have received all commmodity values.  If so, send the signal
        //queue a message that we are complete.
        if(bulletCounter >= ServerTask.nBullets){
            bulletCounter=0;
            STMResultProcessorLogger.info("Signaling that all bullets have been received.");
            ServerTask.signalResultsProcessed();
        }
    }
}
