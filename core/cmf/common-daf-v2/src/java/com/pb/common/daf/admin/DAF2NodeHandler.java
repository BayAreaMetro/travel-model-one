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
package com.pb.common.daf.admin;

import com.pb.common.daf.DAF;
import com.pb.common.daf.ApplicationDef;
import com.pb.common.daf.ApplicationManager;
import org.apache.log4j.Logger;

/**
 * This class replaces the classes in the daf2.admin package and allows DAF2
 * applications to be started and stopped with the DAF-RPC package. This class
 * makes a DAF2 application look like a DAF-RPC Handler.
 *
 * @author   Tim Heier
 * @version  1.0, 8/15/2007
 *
 */
public class DAF2NodeHandler {

    protected static Logger logger = Logger.getLogger(DAF2NodeHandler.class);

    public DAF2NodeHandler() {
    }

    public String echo(String message) {
        logger.info("echo: " + message);
        return message;
    }

    public boolean startCluster(String dummy) {
        try {
            DAF.getInstance();
        }
        catch (Exception e) {
            logger.error("DAF.getInstance call failed", e);
        }
        try {
            DAF.startNode();
        }
        catch (Exception e) {
            logger.error("DAF.startNode call failed", e);
        }

        return true;
    }

    public boolean startApplication(String applicationName) {

        ApplicationManager appManager = ApplicationManager.getInstance();
        ApplicationDef appDef = null;

        //Try to read ApplicationDef file
        try {
            appDef = appManager.readApplicationDef(applicationName);
        }
        catch (Exception e) {
            logger.error("Error reading ApplicationDef, " + applicationName, e);
        }

        //Try to start application
        try {
            ApplicationManager.getInstance().startApplication(appDef);
        }
        catch (Exception e) {
            logger.error("Error starting application, " + applicationName, e);
        }

        return true;
    }

}
