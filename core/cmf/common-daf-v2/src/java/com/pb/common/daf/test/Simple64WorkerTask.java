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

import com.pb.common.daf.MessageProcessingTask;
import com.pb.common.daf.Message;
import org.apache.log4j.Logger;

/**
 * Simple64WorkerTask is a class that ...
 *
 * @author Kimberly Grommes
 * @version 1.0, Jan 3, 2008
 *          Created by IntelliJ IDEA.
 */
public class Simple64WorkerTask extends MessageProcessingTask {
    public static Logger logger = Logger.getLogger(Simple64WorkerTask.class);



    /**
     * Onstart method sets up model
     *
     */
    public void onStart() {

         logger.info(getName() + ", Started");
         logger.info(getName() + ", Finished onStart()");

    }

    /**
     * A worker bee that will process a block of households.
     *
     */
    public void onMessage(Message msg) {

        logger.info(getName() + ", Received messageId=" + msg.getId()
                + " message from=" + msg.getSender());

        Message message = mFactory.createMessage();
        message.setId("ReturnMessage");
        sendTo("Simple64ServerQueue", message);


    }
}
