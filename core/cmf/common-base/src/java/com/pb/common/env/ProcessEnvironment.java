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
package com.pb.common.env;

import com.pb.common.util.ResourceUtil;

import java.util.Properties;
import java.util.Vector;
import java.util.Enumeration;

/**
 * Retrieves the environment variables from the currently running process.
 *
 * @author    Tim Heier
 * @version   1.0, 1/6/2003
 */
public class ProcessEnvironment {

    protected Properties env = new Properties();

    public ProcessEnvironment() {
        loadEnvironment();
    }

    public String getProperty(String envVarName) {
        return env.getProperty(envVarName);
    }

    /** Return a copy of the process environment.
     */
    public Properties getEnvironment() {
        return (Properties)env.clone();
    }


    /** Read environment variables from current process and update based on
     * System properties.
     */
    protected void loadEnvironment() {
        Vector osEnv = Execute.getProcEnvironment();
        for (Enumeration e = osEnv.elements(); e.hasMoreElements();) {
            String entry = (String) e.nextElement();
            int pos = entry.indexOf('=');
            if (pos == -1) {
                //TODO should probably log this condition
            } else {
                String name  = entry.substring(0, pos);
                String value = entry.substring(pos + 1);

                //check system for an updated value
                String newValue = ResourceUtil.checkSystemProperties(name, value);
                env.put(name, newValue);
            }
        }
    }

}
