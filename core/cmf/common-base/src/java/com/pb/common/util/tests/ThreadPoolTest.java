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

import com.pb.common.util.ThreadPool;

/**
 * A test class for the ThreadPool class.
 * 
 * @author Tim Heier
 * @version 1.0, 5/14/2000
 */
public class ThreadPoolTest {

    public static Runnable makeRunnable(final String name, final long firstDelay) {

        return new Runnable() {
            public void run() {
                try {
                    System.out.println(name + ": starting up");
                    Thread.sleep(firstDelay);
                    System.out.println(name + ": doing some stuff");
                    Thread.sleep(2000);
                    System.out.println(name + ": leaving");
                } catch (InterruptedException ix) {
                    System.out.println(name + ": got interrupted!");
                    return;
                } catch (Exception x) {
                    x.printStackTrace();
                }
            }

            public String toString() {
                return name;
            }
        };
    }

    public static void main(String[] args) {
        try {
            ThreadPool pool = new ThreadPool(3);

            Runnable t1 = makeRunnable("Thread_1", 3000);
            pool.execute(t1);

            Runnable t2 = makeRunnable("Thread_2", 1000);
            pool.execute(t2);

            Runnable t3 = makeRunnable("Thread_3", 2000);
            pool.execute(t3);

            Runnable t4 = makeRunnable("Thread_4", 60000);
            pool.execute(t4);

            Runnable t5 = makeRunnable("Thread_5", 1000);
            pool.execute(t5);

            pool.stopRequestIdleWorkers();
            Thread.sleep(2000);
            pool.stopRequestIdleWorkers();

            Thread.sleep(5000);
            pool.stopRequestAllWorkers();
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }
}
