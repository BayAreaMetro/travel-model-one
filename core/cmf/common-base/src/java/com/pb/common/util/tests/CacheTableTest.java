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
package com.pb.common.util.tests;

import com.pb.common.util.CacheTable;

/**
 * A test class for the CacheTable class.
 * 
 * @author Tim Heier
 * @version 1.0, 5/14/2000
 */
public class CacheTableTest {

    public static void main(String args[]) throws InterruptedException {

        long defaultExpireTime = 2000;
        long sleepTime = 5000;

        CacheTable ct = new CacheTable(defaultExpireTime);
        System.out.println("CacheTable, defaultExpireTime = " + defaultExpireTime);

        /* o1 uses the default expireTime
         * o2 uses a specified expireTime
         * o3 never expires
         */
        ct.put("o1", new String("Object1"));
        ct.put("o2", new String("Object2"), 6000);
        ct.put("o3", new String("Object3"), 0);

        System.out.println("Sleeping for " + sleepTime);
        Thread.sleep(sleepTime);
        System.out.println("Waking up");

        /* Get objects from cache */
        String s1 = (String) ct.get("o1");
        String s2 = (String) ct.get("o2");
        String s3 = (String) ct.get("o3");
      
        /* o1 will be null, o2 will be valid, o3 should be valid */
        System.out.print("o1=");
        if (s1 == null)
            System.out.println("null");
        else
            System.out.println(s1);

        System.out.print("o2=");
        if (s2 == null)
            System.out.println("null");
        else
            System.out.println(s2);

        System.out.print("o3=");
        if (s3 == null)
            System.out.println("null");
        else
            System.out.println(s3);

        System.exit(0);
    }
}
