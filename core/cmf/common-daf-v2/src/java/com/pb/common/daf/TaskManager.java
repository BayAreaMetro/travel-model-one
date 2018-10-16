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

import java.net.URLClassLoader;
import java.util.HashMap;
import org.apache.log4j.Logger;

/** 
 * This class manages tasks in DAF. Several classes interct with this
 * class to start/stop and query tasks.
 *
 * @author    Tim Heier
 * @version   1.0, 9/16/2002
 */
public class TaskManager {

    private static Logger logger = Logger.getLogger(TaskManager.class);
    private static HashMap runningTaskMap = new HashMap();
    private static HashMap taskToNodeMap = new HashMap(100);
    

    private TaskManager() {
    }


    protected synchronized static void startTasks(URLClassLoader urlClassLoader, ApplicationDef appDef) {
        String thisNodeName = DAF.getNodeName();

        TaskDef[] taskDefinitions = appDef.taskDefinitions;

        //Loop through all of the tasks defined in the application
        for (int i=0; i < taskDefinitions.length; i++) {
            String taskName  = taskDefinitions[i].name;
            String nodeName  = taskDefinitions[i].nodeName;
            String className = taskDefinitions[i].className;
            String queueName = taskDefinitions[i].queueName;
            
            taskToNodeMap.put(taskName, nodeName);
            
            //Start the tasks that are supposed to run on this node
            if ( nodeName.equals(thisNodeName) || nodeName.equals("*") ) {
                TaskManager.startTask(urlClassLoader, taskName, className, queueName);
            }
        }
    }

    
    /** 
     * Start a task running.
     */
    protected synchronized static void startTask(ClassLoader classLoader, String taskName, String className, String queueName) {
        logger.info("Loading task=" + taskName + ", " + className);

        try {
            //Load the class
            Class clazz = classLoader.loadClass(className);

            Task task = (Task) clazz.newInstance();
            task.init(taskName);

            //Set default work queue for an instance of MessageProcessing task
            if (task instanceof com.pb.common.daf.MessageProcessingTask) {
                MessageProcessingTask mpt = (MessageProcessingTask)task;
                mpt.setDefaultQueue(queueName);
            }
            
            if(logger.isDebugEnabled()) { //CHRISTI
                logger.debug("TaskManager is trying to create a thread for " + taskName + " in startTask()" );
                System.out.println("TaskManager is trying to create a thread for " + taskName + " in startTask()");
                System.out.flush();
            }

            //Create a thread to run this task on
            Thread runner = new Thread(task, task.getName());

            //Add task to list of running tasks
            runningTaskMap.put(taskName, task);

            logger.info("Starting task=" + taskName);
            runner.start();
            
        } catch (Exception e) {
            logger.error("TaskManager.runTask", e);
            throw new RuntimeException(e);
        }
    }


    protected synchronized static void stopTasks(ApplicationDef appDef) {
        String className;
        String taskName;
        String nodeName;
        String queueName;
        String thisNodeName = DAF.getNodeName();

        TaskDef[] taskDefinitions = appDef.taskDefinitions;

        //Loop through all of the tasks defined in the application
        for (int i=0; i < taskDefinitions.length; i++) {
            taskName  = taskDefinitions[i].name;
            nodeName = taskDefinitions[i].nodeName;
            className = taskDefinitions[i].className;
            queueName = taskDefinitions[i].queueName;
            
            taskToNodeMap.remove(taskName);
            
            //Stop the tasks that are supposed to run on this node
            if ( nodeName.equals(thisNodeName) || nodeName.equals("*") ) {
                TaskManager.stopTask(taskName);
            }
        }
    }


    /** Stop a task running.
     */
    protected synchronized static void stopTask(String taskName) {
        logger.info("Stopping task=" + taskName);

        Task task = (Task) runningTaskMap.remove(taskName);
        task.requestStop();
    }

    
    protected static String getNodeNameForTaskName(String taskName) {
        String nodeName = (String) taskToNodeMap.get(taskName);
        
        if (nodeName == null) {
            logger.error("TaskManager.getNodeNameForTaskName, nodeName is null for taskName="+
                            taskName);
        }
        
        return nodeName;
    }
}