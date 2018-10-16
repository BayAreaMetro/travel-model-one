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

/**
 * A class that can ping a pingable object.
 * 
 * @author Tim Heier
 * @version 1.0, 5/14/2000
 */
public class Ping extends Thread {
    private long sleepTime;
    private Pingable target;


    public Ping(Pingable target, long sleepTime) {
        this.target = target;
        this.sleepTime = sleepTime;
    }


    public void run() {
        while (true) {
            try {
                sleep(sleepTime);
            } catch (InterruptedException e) {
                // ignore it!
            }
            target.ping();
        }
    }
}
