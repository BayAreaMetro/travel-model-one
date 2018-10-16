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

import com.pb.common.util.BlockingFIFOQueue;

/**
 * A test class for the CacheTable class.
 * 
 * @author Tim Heier
 * @version 1.0, 5/14/2000
 */
public class ObjectFIFOTest {

    private static void fullCheck(BlockingFIFOQueue fifo) {
        try {
            // Sync'd to allow messages to print while 
            // condition is still true.
            synchronized (fifo) {
                while (true) {
                    fifo.waitUntilFull();
                    print("FULL");
                    fifo.waitWhileFull();
                    print("NO LONGER FULL");
                }
            }
        } catch (InterruptedException ix) {
            return;
        }
    }

    private static void emptyCheck(BlockingFIFOQueue fifo) {
        try {
            // Sync'd to allow messages to print while 
            // condition is still true.
            synchronized (fifo) {
                while (true) {
                    fifo.waitUntilEmpty();
                    print("EMPTY");
                    fifo.waitWhileEmpty();
                    print("NO LONGER EMPTY");
                }
            }
        } catch (InterruptedException ix) {
            return;
        }
    }

    private static void consumer(BlockingFIFOQueue fifo) {
        try {
            print("just entered consumer()");

            for (int i = 0; i < 3; i++) {
                synchronized (fifo) {
                    Object obj = fifo.remove();
                    print("DATA-OUT - did remove(), obj=" + obj);
                }
                Thread.sleep(3000);
            }

            synchronized (fifo) {
                boolean resultOfWait = fifo.waitUntilEmpty(500);
                print("did waitUntilEmpty(500), resultOfWait=" +
                        resultOfWait + ", getSize()=" +
                        fifo.getSize());
            }

            for (int i = 0; i < 3; i++) {
                synchronized (fifo) {
                    Object[] list = fifo.removeAll();
                    print("did removeAll(), list.length=" +
                            list.length);

                    for (int j = 0; j < list.length; j++) {
                        print("DATA-OUT - list[" + j + "]=" +
                                list[j]);
                    }
                }
                Thread.sleep(100);
            }

            for (int i = 0; i < 3; i++) {
                synchronized (fifo) {
                    Object[] list = fifo.removeAtLeastOne();
                    print(
                            "did removeAtLeastOne(), list.length=" +
                            list.length);

                    for (int j = 0; j < list.length; j++) {
                        print("DATA-OUT - list[" + j + "]=" +
                                list[j]);
                    }
                }
                Thread.sleep(1000);
            }

            while (!fifo.isEmpty()) {
                synchronized (fifo) {
                    Object obj = fifo.remove();
                    print("DATA-OUT - did remove(), obj=" + obj);
                }
                Thread.sleep(1000);
            }

            print("leaving consumer()");
        } catch (InterruptedException ix) {
            return;
        }
    }

    private static void producer(BlockingFIFOQueue fifo) {
        try {
            print("just entered producer()");
            int count = 0;

            Object obj0 = new Integer(count);
            count++;
            synchronized (fifo) {
                fifo.add(obj0);
                print("DATA-IN - did add(), obj0=" + obj0);

                boolean resultOfWait = fifo.waitUntilEmpty(500);
                print("did waitUntilEmpty(500), resultOfWait=" +
                        resultOfWait + ", getSize()=" +
                        fifo.getSize());
            }

            for (int i = 0; i < 10; i++) {
                Object obj = new Integer(count);
                count++;
                synchronized (fifo) {
                    fifo.add(obj);
                    print("DATA-IN - did add(), obj=" + obj);
                }
                Thread.sleep(1000);
            }

            Thread.sleep(2000);

            Object obj = new Integer(count);
            count++;
            synchronized (fifo) {
                fifo.add(obj);
                print("DATA-IN - did add(), obj=" + obj);
            }
            Thread.sleep(500);

            Integer[] list1 = new Integer[3];
            for (int i = 0; i < list1.length; i++) {
                list1[i] = new Integer(count);
                count++;
            }

            synchronized (fifo) {
                fifo.addEach(list1);
                print("did addEach(), list1.length=" +
                        list1.length);
            }

            Integer[] list2 = new Integer[8];
            for (int i = 0; i < list2.length; i++) {
                list2[i] = new Integer(count);
                count++;
            }

            synchronized (fifo) {
                fifo.addEach(list2);
                print("did addEach(), list2.length=" +
                        list2.length);
            }

            synchronized (fifo) {
                fifo.waitUntilEmpty();
                print("fifo.isEmpty()=" + fifo.isEmpty());
            }

            print("leaving producer()");
        } catch (InterruptedException ix) {
            return;
        }
    }

    private static synchronized void print(String msg) {
        System.out.println(
                Thread.currentThread().getName() + ": " + msg);
    }

    public static void main(String[] args) {
        final BlockingFIFOQueue fifo = new BlockingFIFOQueue(5);

        Runnable fullCheckRunnable = new Runnable() {
            public void run() {
                fullCheck(fifo);
            }
        };

        Thread fullCheckThread =
                new Thread(fullCheckRunnable, "fchk");
        fullCheckThread.setPriority(9);
        fullCheckThread.setDaemon(true); // die automatically
        fullCheckThread.start();

        Runnable emptyCheckRunnable = new Runnable() {
            public void run() {
                emptyCheck(fifo);
            }
        };

        Thread emptyCheckThread =
                new Thread(emptyCheckRunnable, "echk");
        emptyCheckThread.setPriority(8);
        emptyCheckThread.setDaemon(true); // die automatically
        emptyCheckThread.start();

        Runnable consumerRunnable = new Runnable() {
            public void run() {
                consumer(fifo);
            }
        };

        Thread consumerThread =
                new Thread(consumerRunnable, "cons");
        consumerThread.setPriority(7);
        consumerThread.start();

        Runnable producerRunnable = new Runnable() {
            public void run() {
                producer(fifo);
            }
        };

        Thread producerThread =
                new Thread(producerRunnable, "prod");
        producerThread.setPriority(6);
        producerThread.start();
    }
}
