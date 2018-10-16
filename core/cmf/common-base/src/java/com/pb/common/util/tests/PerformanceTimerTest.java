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

import com.pb.common.util.PerformanceTimer;
import com.pb.common.util.PerformanceTimerType;

/**
 * Test cases for the PerformanceTimer class.
 *
 * @author   Tim Heier
 * @version  1.0, 8/6/2005
 *
 */
public class PerformanceTimerTest {

    public void testStartStop() throws InterruptedException {
        PerformanceTimer timer = PerformanceTimer.createNewTimer("Testing Start-Stop methods", PerformanceTimerType.CPU);

        timer.start();
        Thread.sleep(2000); //Sleep to let some time go by
        timer.stop();
    }

    public void testStartPauseStop() throws InterruptedException {
        PerformanceTimer timer = PerformanceTimer.createNewTimer("Testing Start-Pause-Stop methods", PerformanceTimerType.CPU);

        timer.start();
        Thread.sleep(2000); //Sleep to let some time go by
        timer.pause();

        Thread.sleep(1000); //Sleep to let some time go by
        timer.stop();
    }

    public void testStartCancel() throws InterruptedException {
        PerformanceTimer timer = PerformanceTimer.createNewTimer("Testing Start-Cancel methods", PerformanceTimerType.CPU);

        timer.start();
        Thread.sleep(2000); //Sleep to let some time go by
        timer.cancel();
    }

    public void testStartStopCancel() throws InterruptedException {
        PerformanceTimer timer = PerformanceTimer.createNewTimer("Testing Start-Stop-Cancel methods", PerformanceTimerType.CPU);

        timer.start();
        Thread.sleep(2000); //Sleep to let some time go by
        timer.stop();

        //Try cancelling a stopped timer... should generate an exception
        timer.cancel();
    }

    public void testStartExceptionCancel() {
        PerformanceTimer timer = PerformanceTimer.createNewTimer("Testing Start-Exception-Cancel methods", PerformanceTimerType.CPU);

        timer.start();
        try {
            //normally work happens here
            timer.stop();
            throw new RuntimeException("testing a cancel call");
        }
        catch(Exception e) {

            //be sure to cancell a timer if a timing is aborted
            if (timer.isRunning()) {
                timer.cancel();
            }
        }
    }

    public static void main(String[] args) throws Exception {
        PerformanceTimerTest test = new PerformanceTimerTest();
        test.testStartStop();
        test.testStartPauseStop();
        test.testStartCancel();

        //An execption is expected when calling this test
        try {
            test.testStartStopCancel();
            System.out.println("Should have seen an EXCEPTION");
        }
        catch (Exception e) {
            e.printStackTrace();
            System.out.println("***The above exception is expected***");
        }
        test.testStartExceptionCancel();
    }
}
