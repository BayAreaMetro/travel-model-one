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

import com.pb.common.util.ResourceUtil;

import java.io.File;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.ResourceBundle;
import org.apache.log4j.Logger;

/** 
 * This class manages applications in DAF. This class knows about
 * applications but is not concerned with low level tasks.
 *
 * @author    Tim Heier
 * @version   1.0, 9/16/2002
 */
public class ApplicationManager {

    protected static Logger logger = Logger.getLogger("com.pb.common.daf");

    //List of applications running
    protected static ArrayList appDefList = new ArrayList();

    private static ApplicationManager instance = new ApplicationManager();

    //TODO this was based on sending messages to tasks, should be deleted now 
    protected static HashMap taskToNodeMap = new HashMap();
        
    
    private ApplicationManager() {
    }


    /** 
     * Returns an instance to the singleton.
     */
    public static ApplicationManager getInstance() {
        return instance;
    }


    //----------------------- Public Methods ----------------------------------
    //Used by application code
    //

    /** 
     * This method is called when a message is read from the start application
     * topic.
     */
    public synchronized void startApplication(ApplicationDef appDef) {
        logger.info("--------- Starting application=" + appDef.name);
        
        if (isApplicationRunning(appDef.getName())) {
            logger.warn("Application=" + appDef.name + " is already running");
            return;
        }

//        DAF.printMemoryUsage(); //CHRISTI
        
        //-----Create queues
        try {
            QueueManager.getInstance().createMessageQueues(appDef.getQueueDefinitions());
        } catch (Exception e) {
            logger.error("exception occured while creating message queues", e);
            return;
        }

        //Sleep and give other nodes in the cluster a chance to start 
        try {
            Thread.sleep(2000);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        
        //-----Create a URL classloader for the application - classes will be 
        //loaded from the parent first and then the supplied application URLs   
        URLClassLoader urlClassLoader = new URLClassLoader(appDef.classpathURLs);
        int length = urlClassLoader.getURLs().length;
        URL[] urls = urlClassLoader.getURLs();
        
        logger.info("Application classpath:");
        for (int i=0; i < length; i++) {
            logger.info("classpath["+i+"]="+ urls[i].getPath());
        }
        
        //------Set classloader
        appDef.setClassLoader(urlClassLoader);
        
        //-----Start all tasks destined for this node
        try {
            TaskManager.startTasks(urlClassLoader, appDef);
        
            //Start-up work done, add application to list of running apps if
            //there were no exceptions while starting tasks 
            appDef.setClassLoader(urlClassLoader);
            appDefList.add( appDef );
        } catch (Exception e) {
            //Make sure this classloader can be garbage collected on error
            urlClassLoader = null;
            logger.error("exception occured while starting tasks", e);
            return;
        }
        
        logger.info("--------- Finished starting application=" + appDef.name);
//        DAF.printMemoryUsage();  //CHRISTI

    }


    /** 
     * This method is called by the System task when a message arrives
     * to stop an application.
     */
    public synchronized void stopApplication(ApplicationDef appDef) {
        logger.info("--------- Stopping application=" + appDef.name);
//        DAF.printMemoryUsage();  //CHRISTI

        //-----Remove application from appDefList if it's running
        boolean found = false;
        for (int i=0; i < appDefList.size(); i++) {
            ApplicationDef existingApp = (ApplicationDef) appDefList.get(i);
            if (existingApp.name.equals(appDef.name)) {
                appDefList.remove(i);
                found = true;
                break;
            }
        }

        //If application was not running then print a warning
        if (! found) {
            logger.warn("Application=" + appDef.name + " was not running");
            return;
        }

        //-----Stop all tasks running on this node
        TaskManager.stopTasks(appDef);

        //-----Remove queues
        try {
            QueueManager.getInstance().removeMessageQueues(appDef.getQueueDefinitions());
        } catch (Exception e) {
            logger.error("exception occured while removing message queues", e);
            return;
        }

        //-----Remove classloader
        appDef.setClassLoader(null);
        
//        System.gc(); //CHRISTI
        
        logger.info("--------- Finished stopping application=" + appDef.name);
//        DAF.printMemoryUsage(); //CHRISTI
    
    }


    public synchronized boolean isApplicationRunning(String appName) {

        boolean isRunning = false;

        //Loop over all the running applications
        for (int i = 0; i < appDefList.size(); i++) {
            String name = ((ApplicationDef) appDefList.get(i)).name;

            if (name.equals(appName)) {
                isRunning = true;
                break;
            }
        }

        return isRunning;
    }


    /** 
     * Return the list of current applications.
     */
    public synchronized ArrayList getAppDefList() {
        return (ArrayList) appDefList.clone();
    }


    /** Return an AppDef given the name.
     */
    public synchronized ApplicationDef getAppDef(String appName) {

        ApplicationDef appDef = null;

        for (int i = 0; i < appDefList.size(); i++) {
            String name = ((ApplicationDef) appDefList.get(i)).name;

            if (name.equals(appName)) {
                appDef = (ApplicationDef) appDefList.get(i);
                break;
            }
        }

        return appDef;
    }


    /** 
     * Find the properties file in the classpath and create an application 
     * definition object.
     * 
     */
    public ApplicationDef readApplicationDef(String appName) throws Exception {

        //Load resource bundle from properties file
        ResourceBundle rb = ResourceUtil.getResourceBundle( appName );
        
        //Read classpath property
        List urlList  = ResourceUtil.getList (rb, "classpath");
        URL[] classpathURLs = new URL[urlList.size()];
        
        //Convert the classpath entries which are strings to URL objects
        for (int i=0; i < urlList.size(); i++) {
            String entry = (String) urlList.get(i);
            File file = new File(entry);
            classpathURLs[i] = file.toURL();
        }
                
        TaskDef[] taskDefinitions = readTaskDefinitions(rb);
        QueueDef[] queueDefinitions = readQueueDefinitions(rb);
        
        ApplicationDef appDef = 
            new ApplicationDef(appName, taskDefinitions, queueDefinitions, classpathURLs);
        
        logger.info("ApplicationDef=" + appDef.toString());

        return appDef;
    }


    /**
     * Read the list of tasks and properties.
     */
    protected TaskDef[] readTaskDefinitions(ResourceBundle rb) {
        List taskNames  = ResourceUtil.getList (rb, "taskList");
        TaskDef[] taskDefinitions = new TaskDef[ taskNames.size() ];

        //Read properties for each task
        for (int i=0; i < taskNames.size(); i++) {
            String taskName = (String) taskNames.get(i);
            String classNameKey = taskName  + ".className";
            String nodeNameKey = taskName + ".nodeName";
            String queueNameKey = taskName + ".queueName";
            String topicNameKey = taskName + ".topicName";

            String className = ResourceUtil.getProperty( rb, classNameKey );
            String nodeName = ResourceUtil.getProperty( rb, nodeNameKey );
            String queueName = ResourceUtil.getProperty( rb, queueNameKey );
            String topicName = ResourceUtil.getProperty( rb, topicNameKey );

            taskDefinitions[i] = new TaskDef(taskName, className, nodeName, queueName);
            logger.debug("Setting up task "+taskName+" using class "+className+" on node "+nodeName+" receiving messages on queue "+queueName);
        }
        
        return taskDefinitions;
    }
    
    
    /**
     * Read the list of queues and properties.
     */
    protected QueueDef[] readQueueDefinitions(ResourceBundle rb) {
        List queueNames  = ResourceUtil.getList (rb, "queueList");
        QueueDef[] queueDefinitions = new QueueDef[ queueNames.size() ];
        
        String defaultQueueSize = Integer.toString( DAF.getDefaultQueueSize() );
        
        //Read properites for each queue
        for (int i=0; i < queueNames.size(); i++) {
            String queueName = (String) queueNames.get(i);
            String nodeNameKey = queueName  + ".nodeName";
            String sizeKey = queueName  + ".size";
            
            String nodeName = ResourceUtil.getProperty( rb, nodeNameKey );
            int size = Integer.parseInt(ResourceUtil.getProperty(rb, sizeKey, defaultQueueSize) );
            
            queueDefinitions[i] = new QueueDef(queueName, nodeName, size);
        }
        
        return queueDefinitions;
    }
    
}