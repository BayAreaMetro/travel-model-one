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

public class ThreadPoolWorker {

    public static boolean VERBOSE = false;
    private static int nextWorkerID = 0;

    private BlockingFIFOQueue idleWorkers;
    private int workerID;
    private BlockingFIFOQueue handoffBox;

    private Thread internalThread;
    private volatile boolean noStopRequested;

    public ThreadPoolWorker(BlockingFIFOQueue idleWorkers) {
        this.idleWorkers = idleWorkers;

        workerID = getNextWorkerID();
        handoffBox = new BlockingFIFOQueue(1); // only one slot

        // just before returning, the thread should be created and started.
        noStopRequested = true;

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
        internalThread.start();
    }

    public static synchronized int getNextWorkerID() {
        // notice: synchronized at the class level to ensure uniqueness
        int id = nextWorkerID;
        nextWorkerID++;
        return id;
    }

    public void process(Runnable target) throws InterruptedException {
        handoffBox.add(target);
    }

    private void runWork() {
        while (noStopRequested) {
            try {
                if (VERBOSE)
                    System.out.println("workerID=" + workerID +
                            ", ready for work");
                // Worker is ready work. This will never block since the
                // idleWorker FIFO queue has enough capacity for all of
                // the workers.
                idleWorkers.add(this);

                // wait here until the server puts a request into the box
                Runnable r = (Runnable) handoffBox.remove();

                if (VERBOSE)
                    System.out.println("workerID=" + workerID +
                            ", starting execution of: " + r);
                runIt(r); // catches all exceptions
            } catch (InterruptedException x) {
                Thread.currentThread().interrupt(); // re-assert
            }
        }
    }

    private void runIt(Runnable r) {
        try {
            r.run();
        } catch (Exception runex) {
            // catch any and all exceptions 
            System.err.println("Uncaught exception fell through from run()");
            runex.printStackTrace();
        } finally {
            // Clear the interrupted flag (in case it comes back set)
            // so that if the loop goes again, the 
            // handoffBox.remove() does not mistakenly throw
            // an InterruptedException.
            Thread.interrupted();
        }
    }

    public void stopRequest() {
        if (VERBOSE)
            System.out.println("workerID=" + workerID +
                    ", stopRequest() received");
        noStopRequested = false;
        internalThread.interrupt();
    }

    public boolean isAlive() {
        return internalThread.isAlive();
    }
}
