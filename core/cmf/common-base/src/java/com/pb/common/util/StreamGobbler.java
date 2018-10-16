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

public class StreamGobbler extends Thread {

    protected String type;
    protected InputStream is;
    protected OutputStream os;

    
    StreamGobbler(InputStream is, String type) {
        this(type, is, null);
    }

    
    public StreamGobbler(String type, InputStream is, OutputStream redirect) {
        this.type = type;
        this.is = is;
        this.os = redirect;
    }

    
    public void run() {
        try {
            //Wrap output stream with a text stream
            PrintWriter pw = null;
            if (os != null)
                pw = new PrintWriter(os);

            InputStreamReader isr = new InputStreamReader(is);
            BufferedReader br = new BufferedReader(isr);
            String line = null;
            while ((line = br.readLine()) != null) {
                if (pw != null) { 
                    pw.println(line);
                }
                //Send to console as well
                System.out.println(type + ">" + line);
            }
            if (pw != null) pw.flush();
        } catch (IOException ioe) {
            ioe.printStackTrace();
        }
    }
}
