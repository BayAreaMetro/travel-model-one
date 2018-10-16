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
package com.pb.common.daf;

import org.apache.log4j.Logger;

/** This class shows what a "Task" looks like in the DAF framework. It represents a
 * discrete flow of execution and may be scheduled on a separate thread.
 *
 * It has the following characteristics:
 *
 * 1.  A public, no arguement, constructor.
 * 2.  A public void run() method.
 * 3.  The run() method is the entry point for the task.
 *
 *
 * @author    Tim Heier
 * @version   1.0, 6/18/2002
 */
public class SampleTask implements Runnable {

    Logger logger = Logger.getLogger("com.pb.common.daf");


    public SampleTask() {
    }

    public void run() {

        logger.info("*** SampleTask is running ***");

        //Do some work here
    }
}