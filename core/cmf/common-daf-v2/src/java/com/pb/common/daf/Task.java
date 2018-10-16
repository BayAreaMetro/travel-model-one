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

/**
 * Represents a running Task. User tasks should extend this class and implement
 * the doWork() method.
 *
 * @author    Tim Heier
 * @version   1.0, 9/30/2003
 */
public abstract class Task implements Runnable {

    protected Logger logger = Logger.getLogger("com.pb.common.daf");
    protected String name;
    protected boolean running = false;

    protected volatile boolean stopRequested;
    protected Thread runThread;


    public Task() {
    }


    public void init(String name) {
        this.name = name;
        onInit();
    }


    /**
     * The underlying thread will call this method.
     */
    public void run() {
        running = true;
        try {

            if(logger.isDebugEnabled()) {
                logger.debug( "Task.getName()= " + getName() + " in Task.run() before Thread.currentThread() call." );
                System.out.println( "Task.getName()= " + getName() + " in Task.run() before Thread.currentThread() call." );
                System.out.flush();
            }

            runThread = Thread.currentThread();
            stopRequested = false;

            
            if(logger.isDebugEnabled()) {
                logger.debug( "Task.getName()= " + getName() + " in Task.run() before onStart() call for thread = " + runThread.getName() );
                System.out.println( "Task.getName()= " + getName() + " in Task.run() before onStart() call for thread = " + runThread.getName() );
                System.out.flush();
            }
            onStart();  //template method

            doWork();   //template method

            onStop();   //template method
        } catch (Throwable t) {
            logger.error("caught in Task.run() method", t);
        }

        running = false;
        logger.info("Task="+name+" is exiting");
    }


    /**
     * This method is called when the class is intialized (eg. constructor) It has not been
     * assigned to a thread yet.
     */
    public void onInit() {
    }


    /**
     * This method is called before the doWork method. A task may override this
     * method to do some initiaization work.
     */
    public void onStart() {
    }


    /**
     * This must be overriden to provide the core functionality of the task.
     */
    public abstract void doWork();


    /**
     * A task may optionally override this method
     */
    public void onStop() {
    }


    public String getName() {
        return name;
    }


    public void requestStop() {
        logger.info("Requesting stop for task="+ name);

        stopRequested = true;
//        if (runThread != null) {
//            runThread.interrupt();  //wake a sleeping thread
//        }
    }

}
