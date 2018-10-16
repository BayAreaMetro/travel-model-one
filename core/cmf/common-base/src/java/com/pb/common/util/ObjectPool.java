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
 * Internal storage of the pooled objects will be handled with two Hashtable
 * objects, one for locked objects and the other for unlocked. The objects
 * themselves will be the keys of the hashtable and their last-usage time
 * (in milliseconds) will be the value.
 * 
 * @author Tim Heier
 * @version 1.0, 3/31/2000
 */
public abstract class ObjectPool {
    private long expireTime;
    private long minimumSize;
    private long maximumSize;

    private Hashtable locked, unlocked;

    //Subclass provides functionallity
    protected abstract Object create() throws Exception;

    protected abstract boolean validate(Object o);

    protected abstract void expire(Object o);


    protected ObjectPool() {
        expireTime = 60000;    // 60 seconds
        maximumSize = 100;
        locked = new Hashtable();
        unlocked = new Hashtable();
    }

    protected ObjectPool(long expireTime, long maximumSize) {
        this.expireTime = expireTime;
        this.maximumSize = maximumSize;
        locked = new Hashtable();
        unlocked = new Hashtable();
    }

    public void setExpireTime(long expireTime) {
        this.expireTime = expireTime;
    }

    public long getExpireTime() {
        return (expireTime);
    }

    public void setMinimumSize(long minimumSize) {
        this.minimumSize = minimumSize;
    }

    public long getMinimumSize() {
        return (minimumSize);
    }

    public void setMaximumSize(long maximumSize) {
        this.maximumSize = maximumSize;
    }

    public long getMaximumSize() {
        return (maximumSize);
    }

    public long getTotalSize() {
        return (unlocked.size() + locked.size());
    }

    public long getLockedSize() {
        return (locked.size());
    }

    public long getUnLockedSize() {
        return (unlocked.size());
    }

    /**
     * The checkOut() method first checks to see if there are any objects in the
     * unlocked hashtable. If so, it cycles through them and looks for a valid
     * one. Validation depends on two things. First, the object pool checks to
     * see that the object's last-usage time does not exceed the expiration time
     * specified by the subclass. Second, the object pool calls the abstract
     * validate() method, which does any class-specific checking or
     * reinitialization that is needed to re-use the object. If the object fails
     * validation, it is freed and the loop continues to the next object in the
     * hashtable. When an object is found that passes validation, it is moved into
     * the locked hashtable and returned to the process that requested it. If the
     * unlocked hashtable is empty, or none of its objects pass validation, a new
     * object is instantiated and returned.
     */
    protected synchronized Object checkOut() throws Exception {
        long now = System.currentTimeMillis();
        Object o;

        if ((locked.size()) > maximumSize) {
            throw new Exception("NotAvailable");
        }

        if (unlocked.size() > 0) {

            Enumeration e = unlocked.keys();
            while (e.hasMoreElements()) {
                o = e.nextElement();
                if ((now - ((Long) unlocked.get(o)).longValue()) > expireTime) {

                    // object has expired
                    unlocked.remove(o);
                    expire(o);
                    o = null;
                } else {
                    if (validate(o)) {
                        unlocked.remove(o);
                        locked.put(o, new Long(now));
                        return (o);
                    } else {
                        // object failed validation
                        unlocked.remove(o);
                        expire(o);
                        o = null;
                    }
                }
            }
        } 
        // no objects available, create a new one
        o = create();
        locked.put(o, new Long(now));
        return (o);
    }

    /**
     * The checkIn() method moves the passed-in object from the locked hashtable
     * into the unlocked hashtable.
     */
    protected synchronized void checkIn(Object o) {
        locked.remove(o);
        unlocked.put(o, new Long(System.currentTimeMillis()));
    }


    /**
     * The cleanUp() method releases all the old objects in the pool and
     * asks the garbage collector to reclaim them.
     */
    protected void cleanUp() {
        Object o;

        long now = System.currentTimeMillis();

        synchronized (ObjectPool.class) {
            Enumeration e;

            //Iterate through unused objects
            e = unlocked.keys();
            while (e.hasMoreElements()) {
                o = e.nextElement();
                unlocked.remove(o);
                expire(o);
                o = null;
            }

            //Iterate through objects which are checked out
            e = locked.keys();
            while (e.hasMoreElements()) {
                o = e.nextElement();
                locked.remove(o);
                expire(o);
                o = null;
            }

        }
    }

    /**
     * The removeResource() method removes the object from the pool so it
     * will not be checked out again. Useful if the object is suspected
     * of being broken.
     */
    protected synchronized void removeObject(Object o) {
        locked.remove(o);
    }

}
