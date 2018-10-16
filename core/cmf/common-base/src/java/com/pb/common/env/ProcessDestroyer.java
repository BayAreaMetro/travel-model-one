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
package com.pb.common.env;

import java.lang.reflect.Method;
import java.util.Enumeration;
import java.util.Vector;

/**
 * Destroys all registered <code>Process</code>es when the VM exits.
 *
 */
class ProcessDestroyer
    extends Thread {

    private Vector processes = new Vector();

    /**
     * Constructs a <code>ProcessDestroyer</code> and registers it as
     * a shutdown hook.
     */
    public ProcessDestroyer() {
        try {
            // check to see if the method exists (support pre-JDK 1.3 VMs)
            //
            Class[] paramTypes = {Thread.class};
            Method addShutdownHook =
                Runtime.class.getMethod("addShutdownHook", paramTypes);

            // add the hook
            //
            Object[] args = {this};
            addShutdownHook.invoke(Runtime.getRuntime(), args);
        } catch (Exception e) {
            // it just won't be added as a shutdown hook... :(
        }
    }

    /**
     * Returns <code>true</code> if the specified <code>Process</code> was
     * successfully added to the list of processes to destroy upon VM exit.
     *
     * @param   process the process to add
     * @return  <code>true</code> if the specified <code>Process</code> was
     *          successfully added
     */
    public boolean add(Process process) {
        processes.addElement(process);
        return processes.contains(process);
    }

    /**
     * Returns <code>true</code> if the specified <code>Process</code> was
     * successfully removed from the list of processes to destroy upon VM exit.
     *
     * @param   process the process to remove
     * @return  <code>true</code> if the specified <code>Process</code> was
     *          successfully removed
     */
    public boolean remove(Process process) {
        return processes.removeElement(process);
    }

    /**
     * Invoked by the VM when it is exiting.
     */
    public void run() {
        synchronized (processes) {
            Enumeration e = processes.elements();
            while (e.hasMoreElements()) {
                ((Process) e.nextElement()).destroy();
            }
        }
    }
}
