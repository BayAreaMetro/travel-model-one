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

import java.io.File;
import java.io.FileOutputStream;

import com.pb.common.util.StreamGobbler;

/**
 * @author Tim
 * 
 */
public class CommandLauncher {

    protected Runtime rt = Runtime.getRuntime();
    protected Process proc;
    protected File redirectFile;
    
    
    public CommandLauncher(File redirectFile) {
        this.redirectFile = redirectFile;
    }
    
    
    public void launch(String args[]) {

        FileOutputStream fos = null;
        try {
            new FileOutputStream(redirectFile);
/*
            String osName = System.getProperty("os.name");
            String[] cmd = new String[3];

            if (osName.equals("Windows NT")) {
                cmd[0] = "cmd.exe";
                cmd[1] = "/C";
                cmd[2] = args[0];
*/
        } catch (Throwable t) {
            t.printStackTrace();
        }
            
        try {
            proc = rt.exec(args, null, null);

            StreamGobbler errorGobbler = new StreamGobbler("ERR", proc.getErrorStream(), System.err);
            StreamGobbler outputGobbler = new StreamGobbler("OUT", proc.getInputStream(), fos);

            errorGobbler.start();
            outputGobbler.start();

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    
    public void killProcess() {
        proc.destroy();
    }

}
