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
package com.pb.common.daf;

/** 
 * This class holds the properties for a single node.
 *
 * @author    Tim Heier
 * @version   1.0, 9/16/2002
 */

public class NodeDef implements java.io.Serializable {

    String name;
    String address;
    int messagePort;
    int adminPort;
    boolean connected;

    
    private NodeDef() {
    }


    public NodeDef (String name, String address, int messagePort, int adminPort) {
        this.name = name;
        this.address = address;
        this.messagePort = messagePort;
        this.adminPort = adminPort;
        connected = false;
    }


    public String toString() {
        return
            "name=" + name + ", " +
            "address=" + address + ", " +
            "messagePort=" + messagePort + ", " +
            "adminPort=" + adminPort + ", " +
            "connected=" + connected;
    }
    
    /**
     * @return Returns the address.
     */
    public String getAddress() {
        return address;
    }

    /**
     * @return Returns the connected.
     */
    public boolean isConnected() {
        return connected;
    }

    /**
     * @return Returns the name.
     */
    public String getName() {
        return name;
    }

    /**
     * @return Returns the port.
     */
    public int getMessagePort() {
        return messagePort;
    }

    /**
     * @return Returns the adminPort.
     */
    public int getAdminPort() {
        return adminPort;
    }

}