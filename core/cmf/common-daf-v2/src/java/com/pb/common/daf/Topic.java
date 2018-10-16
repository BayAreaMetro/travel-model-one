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

import java.io.Serializable;

/** Enumerates the types of topics that are defined in the system.
 *
 * @author    Tim Heier
 * @version   1.0, 6/25/2002
 */
public final class Topic implements Serializable {

    public static final Topic APPLICATION_START = new Topic("TOPIC_APPLICATION_START");
    public static final Topic APPLICATION_STOP = new Topic("TOPIC_APPLICATION_STOP");
    public static final Topic LOGGING = new Topic("TOPIC_LOGGING");
    public static final Topic STATUS = new Topic("TOPIC_STATUS");

    private String id;

    //This method is hard coded for now.
    protected static String[] getTopicNames() {
        String[] topicNames = { Topic.APPLICATION_START.getId() ,
                                Topic.APPLICATION_STOP.getId() ,
                                Topic.LOGGING.getId(),
                                Topic.STATUS.getId() };
        return topicNames;
    }
    
    /** Keep this class from being created with "new".
     *
     */
    private Topic(String id) {
        this.id = id;
    }

    public String toString() {
        return this.id;
    }

    public boolean equals(Topic type) {
        boolean result = false;

        int index = type.toString().indexOf(this.id);
        if (index == 0)
            result = true;

        return result;
    }

    public String getId() {
        return id;
    }
    
}
