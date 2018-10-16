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

import java.net.URL;
import java.net.URLClassLoader;

/** This class holds the properties for an application.
 *
 * @author    Tim Heier
 * @version   1.0, 9/16/2002
 */
public class ApplicationDef implements java.io.Serializable {

    String name;
    TaskDef[] taskDefinitions;
    QueueDef[] queueDefinitions;
    URL[] classpathURLs;
    URLClassLoader urlClassLoader;

    
    private ApplicationDef() {
    }


    public ApplicationDef (String name, TaskDef[] taskDefinitions, QueueDef[] queueDefinitions, URL[] urls) {
        this.name = name;
        this.taskDefinitions = taskDefinitions;
        this.queueDefinitions = queueDefinitions;
        this.classpathURLs = urls;
    }


    public String getName() {
        return name;
    }

    
    public TaskDef[] getTaskDefinitions() {
        return taskDefinitions;
    }

    
    public QueueDef[] getQueueDefinitions() {
        return queueDefinitions;
    }
    
    
    public URL[] getClasspathURLs() {
        return classpathURLs;
    }
    
    
    protected void setClassLoader(URLClassLoader urlClassLoader) {
        this.urlClassLoader = urlClassLoader;
    }

    
    public URLClassLoader getClassLoader() {
        return urlClassLoader;
    }

    
    /**
     * Returns an array of queue names for a given node name.
     * 
     * @param nodeName
     * @return
     */
//    public String[] getQueueNamesForNode(String nodeName) {
//        
//        for(int i=0; i < queueDefinitions.length; i++) {
//            if (queueDefinitions[i].nodeName.equalsIgnoreCase(nodeName)) {
//                return 
//            }
//        }
//        List list = (List)queueToNodeMap.get(nodeName);
//
//        String[] queueNames = new String[list.size()];
//        list.toArray(queueNames);
//        
//        return queueNames;
//
//        return null;
//    }
    
    
    public String toString() {
        
        String str = "\n" + " name=" + name + "\n";
        
        //Task Definitions
        for (int i=0; i < taskDefinitions.length; i++) {
            str += " " + taskDefinitions[i].toString() + "\n";
        }

        //Queue Definitions
        for (int i=0; i < queueDefinitions.length; i++) {
            str += " " + queueDefinitions[i].toString() + "\n";
        }

        //Classpath
        str += " classpath=[";
        for (int i=0; i < classpathURLs.length; i++) {
            str += classpathURLs[i].toString();
            if (i != (classpathURLs.length-1))
                str += ", ";
        }
        str += "]\n";

        //Queue to node map
//        Iterator iter = queueToNodeMap.keySet().iterator();
//        while (iter.hasNext()) {
//            String nodeName = (String) iter.next();
//            List queueList = (List) queueToNodeMap.get(nodeName);
//            
//            str += " " + nodeName + "=[";
//            for (int i=0; i < queueList.size(); i++) {
//                str += (String)queueList.get(i);
//                if (i != (queueList.size()-1))
//                    str += ", ";
//            }
//            str += "]\n";
//        }
        
        return str;
    }

}