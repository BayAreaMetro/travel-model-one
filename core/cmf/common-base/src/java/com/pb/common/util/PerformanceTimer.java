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

import org.apache.log4j.Logger;

import java.util.Calendar;
import java.util.GregorianCalendar;
import java.net.InetAddress;

/**
 * A general purpose performance timer class.
 *
 * @author   Tim Heier
 * @version  1.0, 8/6/2005
 *
 */
public class PerformanceTimer {

    protected static Logger performanceLogger = Logger.getLogger("performance");
    protected static Logger logger = Logger.getLogger(PerformanceTimer.class);

    private static String SEPARATOR = ",";

    private String timerName;
    private PerformanceTimerType timerType;

    private String correlator = "";
    private int stackFrameCount = 0;
    private int stackFrameHash = 0;
    private int origThreadId = 0;
    private int callStackCounter = 0;

    private long startTime = 0;
    private long elapsedTime = 0;
    private long pauseStart = 0;
    private long pauseStop = 0;

    private boolean isPaused = false;
    private boolean isRunning = false;
    private boolean isCancelled = false;
    private boolean shouldLog = true;

    private PerformanceTimer(String timerName, PerformanceTimerType timerType, String correlator, int frameCount,
                             int frameHash, int origThreadId, int callStackCounter) {

        this.timerName = timerName;
        //timerName.replace('\r', ' ');
        //timerName.replace('\n', ' ');

        this.timerType = timerType;
        this.correlator = correlator;
        this.stackFrameCount= frameCount;
        this.stackFrameHash = frameHash;
        this.origThreadId = origThreadId;
        this.callStackCounter = callStackCounter;
    }

    public static PerformanceTimer createNewTimer(String timerName, PerformanceTimerType timerType,
                                                  boolean shouldLog) {

        PerformanceTimer newTimer = new PerformanceTimer(timerName, timerType, "correlator", 0, 0, 0, 0);
        newTimer.shouldLog = shouldLog;

        return newTimer;

        //threadHash is a hashtable with a key of ThreadId that contains a stackList arraylist
        //stackList is an arraylist that contains an arraylist of timers (timerList)
        //All timers in a given timerList have the same correlator

        //insert this timer into thread stack
    }

    public static PerformanceTimer createNewTimer(String timerName, PerformanceTimerType timerType) {

        return PerformanceTimer.createNewTimer(timerName, timerType, true);
    }

    public void start() {
        if(isCancelled) {
            throw new RuntimeException("Timer \"" + timerName + "\" was cancelled. Cannot start a cancelled timer");
        }

        if(!isPaused) {
            startTime = System.currentTimeMillis();
            isRunning = true;
        }
        else {
            unPause();
        }
    }

    public void stop() {
        if(isRunning) {
            if(isPaused) {
                unPause();
            }

            //nothing here on in should affect performance times as all numbers have been captured
            isRunning = false;
            elapsedTime = (System.currentTimeMillis() - startTime) - (pauseStop - pauseStart);
            log();

            //pop timer stack
        }
    }

    public void cancel() {
        if(isRunning) {
            elapsedTime = 0;
            isPaused = false;
            isRunning = false;
            isCancelled = true;

            //pop timer stack
        }
        else
        {
            throw new RuntimeException("Timer \"" + timerName + "\" has already been stopped and cannot be cancelled.");
        }

    }

    public void pause() {
        if(!isPaused) {
            isPaused = true;
            pauseStart = System.currentTimeMillis();
        }
    }

    public void unPause() {
        isPaused = false;
        pauseStop = System.currentTimeMillis();
    }

    public long getTotalElapsedMilliseconds() {
        if(!isRunning) {
            return elapsedTime;
        }
        else {
            throw new RuntimeException("Cannot return Total Elapsed Milliseconds because timer \"" + timerName + "\" is still running");
        }
    }

    public boolean isRunning() {
        return isRunning;
    }

    public void clear() {
        startTime = 0;
        elapsedTime = 0;
        pauseStart = 0;
        pauseStop = 0;

        isPaused = false;
        isRunning = false;
        isCancelled = true;

        //pop timer from stack
    }

    private void log()
    {
        if (!shouldLog || !performanceLogger.isInfoEnabled() ) 
            return;

        //MachineName,ThreadName,CorrelatorId,StackDepth,TimerType,ElapsedTime,Message

        try {
            StringBuilder sb = new StringBuilder(256);

            //Timestamp is provided by logger

            sb.append(InetAddress.getLocalHost().getHostName());
            sb.append(SEPARATOR);

            sb.append(Thread.currentThread().getName());
            sb.append(SEPARATOR);

            sb.append(timerType.toString());
            sb.append(SEPARATOR);

            sb.append(elapsedTime);
            sb.append(SEPARATOR);

            sb.append(timerName);
            performanceLogger.info(sb.toString());
        }
        catch (Exception e)
        {
            logger.error("Exception in PerformanceTimer.log()", e);
        }
    }

}
