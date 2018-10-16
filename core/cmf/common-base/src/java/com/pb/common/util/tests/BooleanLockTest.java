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

import com.pb.common.util.BooleanLock;

public class BooleanLockTest {

    private BooleanLock readyLock;

    public BooleanLockTest(BooleanLock readyLock) {
        this.readyLock = readyLock;

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

        Thread internalThread = new Thread(r, "internal");
        internalThread.start();
    }

    private void runWork() {
//        try {
//            print("about to wait for readyLock to be true");
//            readyLock.waitUntilTrue(0);  // 0 - wait forever
//            print("readyLock is now true");
//        } catch (InterruptedException x) {
//            print("interrupted while waiting for readyLock " +
//                    "to become true");
//        }

        try {
            print("about to wait for readyLock to switch");
            readyLock.waitUntilStateChanges(0);  // 0 - wait forever
            print("readyLock is now flipped");
            print("waiting for the next switch");
            readyLock.waitUntilStateChanges(0);
            print("readyLock has flipped again");
        } catch (InterruptedException x) {
            print("interrupted while waiting for readyLock " +
                    "to flip");
        }
    }

    private static void print(String msg) {
        String name = Thread.currentThread().getName();
        System.err.println(name + ": " + msg);
    }

    public static void main(String[] args) {
//        try {
//            print("creating BooleanLock instance");
//            BooleanLock ready = new BooleanLock(false);
//
//            print("creating Signaling instance");
//            new BooleanLockTest(ready);
//
//            print("about to sleep for 3 seconds");
//            Thread.sleep(3000);
//
//            print("about to setValue to true");
//            ready.setValue(true);
//            print("ready.isTrue()=" + ready.isTrue());
//        } catch (InterruptedException x) {
//            x.printStackTrace();
//        }

        try {
            print("creating BooleanLock instance");
            BooleanLock ready = new BooleanLock(false);

            print("creating Signaling instance");
            new BooleanLockTest(ready);

            print("about to sleep for 3 seconds");
            Thread.sleep(3000);

            print("about to flipValue");
            ready.flipValue();
            print("ready.isTrue()=" + ready.isTrue());

            print("about to sleep for 3 seconds");
            Thread.sleep(3000);

            print("about to flipValue again");
            ready.flipValue();
            print("ready.isTrue()=" + ready.isTrue());
        } catch (InterruptedException x) {
            x.printStackTrace();
        }
    }
}
