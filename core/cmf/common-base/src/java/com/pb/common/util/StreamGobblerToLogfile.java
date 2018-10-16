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
package com.pb.common.util;

/**
 * @author Tim
 *  
 */
import java.io.*;

import org.apache.log4j.Level;
import org.apache.log4j.Logger;

public class StreamGobblerToLogfile extends Thread {

    Logger myLogger;
    Level myLevel;
    protected InputStream is;
    
    public StreamGobblerToLogfile(InputStream is, Level level, Logger logger) {
        this.myLevel = level;
        this.is = is;
        myLogger = logger;
    }

    
    public void run() {
        try {
            InputStreamReader isr = new InputStreamReader(is);
            BufferedReader br = new BufferedReader(isr);
            String line = null;
            while ((line = br.readLine()) != null) {
                myLogger.log(myLevel,line);
            }
        } catch (IOException ioe) {
            ioe.printStackTrace();
        }
    }
}
