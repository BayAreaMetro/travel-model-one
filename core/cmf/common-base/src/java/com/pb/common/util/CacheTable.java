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
package com.pb.common.util;

import java.util.Enumeration;
import java.util.Hashtable;

/**
 * A class that can cache objects.  These objects can expire and
 * be cleaned by a clean up thread.
 * 
 * @author Tim Heier
 * @version 1.0, 5/14/2000
 */
public class CacheTable extends Hashtable implements Pingable {

    private long defaultExpireTime;
    private long pingTime;
    private Ping pingThread;


    /**
     * Creat a cache table and specify the default object expiration
     * time. This time will also be used as the ping interval. This
     * is a convenience constructor for simple caches.
     */
    public CacheTable(long defaultExpireTime) {
        this(defaultExpireTime, defaultExpireTime);
    }


    /**
     * Creat a cache table and specify the default object expiration
     * time. Specify the ping time for checking the cache.
     */
    public CacheTable(long defaultExpireTime, long pingTime) {
        super();

        this.defaultExpireTime = defaultExpireTime;
        this.pingTime = pingTime;

        pingThread = new Ping(this, ((long) (pingTime * 0.90)));
        pingThread.start();
    }


    /**
     * Add object to cache.  Use default expiration time.
     */
    public synchronized Object put(Object key, Object value) {
        return (put(key, value, defaultExpireTime));
    }


    /**
     * Add object to cache.  Use specified expiration time.
     */
    public synchronized Object put(Object key, Object value, long expireTime) {
        return (super.put(key, new TimeWrapper(value, expireTime)));
    }


    /**
     * Return an object from the cache.
     */
    public synchronized Object get(Object key) {
        TimeWrapper tw = (TimeWrapper) super.get(key);
        if (tw != null) {
            return tw.getObject();
        }
        return null;
    }

    /**
     * Remove objects which have expired. When expireTime == 0 objects never
     * expire and are never removed from the cache.
     */
    public synchronized void ping() {
        Enumeration e = super.keys();

        while (e.hasMoreElements()) {
            Object key = e.nextElement();
            TimeWrapper tw = (TimeWrapper) super.get(key);

            if ((tw != null) && //valid object
                    (tw.getExpireTime() > 0) && //objects which expire
                    (tw.getAge() > tw.getExpireTime())) {  //object has expired
              
              
                remove(key);
            }
        }

        //Suggest to the VM to clean up
        System.gc();
    }

}
