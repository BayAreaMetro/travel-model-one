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

import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;

public class ThreadRunner {

    // nested internal class for stop request entries
    private static class Entry extends Object {
        private Thread thread;
        private long stopTime;

        private Entry(Thread t, long stop) {
            thread = t;
            stopTime = stop;
        }
    }

    // static reference to the singleton instance
    private static ThreadRunner ss;

    static {
        // When class is loaded, create exactly one instance 
        // using the private constructor.
        ss = new ThreadRunner();
    }

    private List stopList;
    private List pendingList;
    private Thread internalThread;

    private ThreadRunner() {
        // using a linked list for fast deletions
        stopList = new LinkedList();

        // Enough initial capacity for 20 pending additions, 
        // will grow automatically if necessary to keep 
        // ensureStop() from blocking.
        pendingList = new ArrayList(20);

        Runnable r = new Runnable() {
            public void run() {
                try {
                    runWork();
                } catch (Exception x) {
                    // in case ANY exception slips through
                    x.printStackTrace();
                }
            }
        };

        internalThread = new Thread(r);
        internalThread.setDaemon(true); // no need to run alone
        internalThread.setPriority(Thread.MAX_PRIORITY); // high
        internalThread.start();
    }

    private void runWork() {
        try {
            while (true) {
                // Since this is a super-high priority thread, 
                // be sure to give other threads a chance to 
                // run each time through in case the wait on 
                // pendingList is very short.
                Thread.sleep(500);

                // Stop expired threads and determine the 
                // amount of time until the next thread is
                // due to expire.
                long sleepTime = checkStopList();

                synchronized (pendingList) {
                    if (pendingList.size() < 1) {
                        pendingList.wait(sleepTime);
                    }

                    if (pendingList.size() > 0) {
                        // Copy into stopList and then remove 
                        // from pendingList.
                        stopList.addAll(pendingList);
                        pendingList.clear();
                    }
                }
            } // while
        } catch (InterruptedException x) {
            // ignore
        } catch (Exception x) {
            // Never expect this, but print a trace in case 
            // it happens.
            x.printStackTrace();
        }
    }

    private long checkStopList() {
        // called from runWork() by the internal thread 

        long currTime = System.currentTimeMillis();
        long minTime = Long.MAX_VALUE;

        Iterator iter = stopList.iterator();
        while (iter.hasNext()) {
            Entry entry = (Entry) iter.next();

            if (entry.thread.isAlive()) {
                if (entry.stopTime < currTime) {
                    // timed out, stop it abruptly right now
                    try {
                        entry.thread.stop();
                    } catch (SecurityException x) {
                        // Catch this here so that other 
                        // operations are not disrupted. Warn
                        // that thread could not be stopped.
                        System.err.println(
                                "ThreadRunner was not permitted to " +
                                "stop thread=" + entry.thread);
                        x.printStackTrace();
                    }

                    // Since it has stopped, remove it 
                    // from stopList.
                    iter.remove();
                } else {
                    // Not yet expired, check to see if this 
                    // is the new minimum.
                    minTime = Math.min(entry.stopTime, minTime);
                }
            } else {
                // Thread died on its own, remove it from 
                // stopList.
                iter.remove();
            } // if alive
        } // while

        long sleepTime = minTime - System.currentTimeMillis();

        // ensure that it is a least a little bit of time
        sleepTime = Math.max(50, sleepTime);

        return sleepTime;
    }

    private void addEntry(Entry entry) {
        // called from ensureStop() by external thread

        synchronized (pendingList) {
            pendingList.add(entry);

            // no need for notifyAll(), one waiter
            pendingList.notify();
        }
    }

    public static void ensureStop(Thread t, long msGracePeriod) {
        if (!t.isAlive()) {
            // thread is already stopped, return right away
            return;
        }

        long stopTime =
                System.currentTimeMillis() + msGracePeriod;

        Entry entry = new Entry(t, stopTime);
        ss.addEntry(entry);
    }
}
