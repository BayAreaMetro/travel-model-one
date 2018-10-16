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

public class BooleanLock extends Object {
    private boolean value;

    public BooleanLock(boolean initialValue) {
        value = initialValue;
    }

    public BooleanLock() {
        this(false);
    }

    public synchronized void setValue(boolean newValue) {
        if (newValue != value) {
            value = newValue;
            notifyAll();
        }
    }

    public synchronized void flipValue() {
        value = (!value);
        notifyAll();
    }

    public synchronized boolean waitToSetTrue(long msTimeout)
            throws InterruptedException {

        boolean success = waitUntilFalse(msTimeout);
        if (success) {
            setValue(true);
        }

        return success;
    }

    public synchronized boolean waitToSetFalse(long msTimeout)
            throws InterruptedException {

        boolean success = waitUntilTrue(msTimeout);
        if (success) {
            setValue(false);
        }

        return success;
    }

    public synchronized boolean isTrue() {
        return value;
    }

    public synchronized boolean isFalse() {
        return !value;
    }

    public synchronized boolean waitUntilTrue(long msTimeout)
            throws InterruptedException {

        return waitUntilStateIs(true, msTimeout);
    }

    public synchronized boolean waitUntilFalse(long msTimeout)
            throws InterruptedException {

        return waitUntilStateIs(false, msTimeout);
    }

    public synchronized boolean waitUntilStateIs(
            boolean state,
            long msTimeout
            ) throws InterruptedException {

        if (msTimeout == 0L) {
            while (value != state) {
                wait();  // wait indefinitely until notified
            }

            // condition has finally been met
            return true;
        }

        // only wait for the specified amount of time
        long endTime = System.currentTimeMillis() + msTimeout;
        long msRemaining = msTimeout;

        while ((value != state) && (msRemaining > 0L)) {
            wait(msRemaining);
            msRemaining = endTime - System.currentTimeMillis();
        }

        // May have timed out, or may have met value, 
        // calculate return value.
        return (value == state);
    }

    public synchronized void waitUntilStateChanges(long msTimeout)
            throws InterruptedException {

        boolean waitValue = value;
    	
        if (msTimeout == 0L) {
            while (waitValue == value) {
                wait();  // wait indefinitely until notified
            }

            // condition has finally been met
            return;
        }

        // only wait for the specified amount of time
        long endTime = System.currentTimeMillis() + msTimeout;
        long msRemaining = msTimeout;

        while ((waitValue == value) && (msRemaining > 0L)) {
            wait(msRemaining);
            msRemaining = endTime - System.currentTimeMillis();
        }

        // may have timed out so return
    }


    public boolean getValue() {
    	return value;
    }

}
