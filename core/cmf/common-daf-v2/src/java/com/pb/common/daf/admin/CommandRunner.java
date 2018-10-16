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
package com.pb.common.daf.admin;


/**
 * @author Tim
 *
 */
public class CommandRunner implements Runnable {

    private Thread internalThread;
    private CommandLauncher launcher;
    private String[] args;
    
    
    public CommandRunner(CommandLauncher launcher, String[] args) {
        this.launcher = launcher;
        this.args = args;
        
        internalThread = new Thread(this);
        internalThread.setDaemon(false);
        internalThread.start();
    }
        
    public void run() {
        if (Thread.currentThread() != internalThread) {
            throw new RuntimeException("only the internal thread is allowd to invoke run()");
        }

        launcher.launch(args);
    }
    
    public void killProcess() {
        launcher.killProcess();
        StartNode.stop32BitMatrixIoServer(0);
        internalThread = null;
    }
    
}
