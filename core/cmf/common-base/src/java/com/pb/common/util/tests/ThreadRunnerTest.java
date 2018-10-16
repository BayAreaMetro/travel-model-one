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

import com.pb.common.util.ThreadRunner;

/**
 * A test class for the CacheTable class.
 * 
 * @author Tim Heier
 * @version 1.0, 5/14/2000
 */
public class ThreadRunnerTest {

    private static Thread launch(final String name, long lifeTime) {
        final int loopCount = (int) (lifeTime / 1000);

        Runnable r = new Runnable() {
            public void run() {
                try {
                    for (int i = 0; i < loopCount; i++) {
                        Thread.sleep(1000);
                        System.out.println("-> Running - " + name);
                    }
                } catch (InterruptedException x) {
                    // ignore
                }
            }
        };

        Thread t = new Thread(r);
        t.setName(name);
        t.start();

        return t;
    }

    public static void main(String[] args) {
        Thread t0 = launch("T0", 1000);
        Thread t1 = launch("T1", 5000);
        Thread t2 = launch("T2", 15000);

        try {
            Thread.sleep(2000);
        } catch (InterruptedException x) {
        }

        ThreadRunner.ensureStop(t0, 9000);
        ThreadRunner.ensureStop(t1, 10000);
        ThreadRunner.ensureStop(t2, 12000);

        try {
            Thread.sleep(20000);
        } catch (InterruptedException x) {
        }

        Thread t3 = launch("T3", 15000);
        ThreadRunner.ensureStop(t3, 5000);

        try {
            Thread.sleep(1000);
        } catch (InterruptedException x) {
        }

        Thread t4 = launch("T4", 15000);
        ThreadRunner.ensureStop(t4, 3000);
    }
}
