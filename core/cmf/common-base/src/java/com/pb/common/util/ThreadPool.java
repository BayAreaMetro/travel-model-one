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

public class ThreadPool {

    private BlockingFIFOQueue idleWorkers;
    private ThreadPoolWorker[] workerList;

    public ThreadPool(int numberOfThreads) {
        //Make sure that it's at least one
        numberOfThreads = Math.max(1, numberOfThreads);

        idleWorkers = new BlockingFIFOQueue(numberOfThreads);
        workerList = new ThreadPoolWorker[numberOfThreads];

        for (int i = 0; i < workerList.length; i++) {
            workerList[i] = new ThreadPoolWorker(idleWorkers);
        }
    }

    public void execute(Runnable target) throws InterruptedException {
        //Block (forever) until a worker is available
        ThreadPoolWorker worker = (ThreadPoolWorker) idleWorkers.remove();
        worker.process(target);
    }

    public void stopRequestIdleWorkers() {
        try {
            Object[] idle = idleWorkers.removeAll();
            for (int i = 0; i < idle.length; i++) {
                ((ThreadPoolWorker) idle[i]).stopRequest();
            }
        } catch (InterruptedException x) {
            Thread.currentThread().interrupt(); // re-assert
        }
    }

    public void stopRequestAllWorkers() {
        //Stop the idle one's first since that won't interfere with anything
        //productive.
        stopRequestIdleWorkers();

        //Give the idle workers a quick chance to die 
        try {
            Thread.sleep(250);
        } catch (InterruptedException x) {
        }

        //Step through the list of ALL workers that are still alive.
        for (int i = 0; i < workerList.length; i++) {
            if (workerList[i].isAlive()) {
                workerList[i].stopRequest();
            }
        }
    }

    public void waitForAllWorkers() {
        try {
            idleWorkers.waitUntilFull();
        } catch (InterruptedException x) {
            Thread.currentThread().interrupt(); // re-assert
        }
    }

}
