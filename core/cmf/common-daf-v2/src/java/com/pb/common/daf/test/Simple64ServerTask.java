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

import java.io.File;
import java.io.IOException;

/**
 * Simple64ServerTask is a class that ...
 *
 * @author Kimberly Grommes
 * @version 1.0, Jan 3, 2008
 *          Created by IntelliJ IDEA.
 */
public class Simple64ServerTask extends MessageProcessingTask {

    Logger serverLogger = Logger.getLogger(Simple64ServerTask.class);

    String[] queueNames = {"Worker64Queue1", "Worker64Queue2"};

    int counter = 0;

    public void onStart(){
        serverLogger.info("***" + getName() + ", started");

        for (String queueName: queueNames) {
            Message message = mFactory.createMessage();
            message.setId("KickOff");
            message.setValue("msgNum", queueName.substring(queueName.length()-1));
            sendTo(queueName, message);

        }
    }

    public void onMessage(Message msg){
        serverLogger.info(getName() + " received messageId=" + msg.getId()
                + " message from=" + msg.getSender());
        counter++;

        if (counter == queueNames.length) {
            serverLogger.info("App is done.");

            File doneFile = new File("/osmp_gui/java_files/daf/64daf_done.txt");
            if(!doneFile.exists()){
                try {
                    doneFile.createNewFile();
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }
            serverLogger.info("Done File has been written");
        }

    }

}
