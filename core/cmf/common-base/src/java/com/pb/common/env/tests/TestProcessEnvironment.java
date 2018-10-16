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
package com.pb.common.env.tests;

import com.pb.common.env.ProcessEnvironment;

import java.util.Properties;
import java.util.Enumeration;

public class TestProcessEnvironment {

    public static void main(String[] args){

        ProcessEnvironment pe = new ProcessEnvironment();

        //Read the entire environment
        Properties env = pe.getEnvironment();
        Enumeration names = env.keys();
        while (names.hasMoreElements()) {
            String name = (String)names.nextElement();
            String value = env.getProperty(name);
            System.out.println(name + "=" + value);
        }

        System.out.println("---------------------------------------------------------");

        //Retrieve some standard Windows values
        System.out.println ("Description=" + pe.getProperty("Description"));
        System.out.println ("USERDNSDOMAIN=" + pe.getProperty("USERDNSDOMAIN"));
        System.out.println ("USERDOMAIN=" + pe.getProperty("USERDOMAIN"));
        System.out.println ("USERNAME=" + pe.getProperty("USERNAME"));
        System.out.println ("USERPROFILE=" + pe.getProperty("USERPROFILE"));

    }
}
