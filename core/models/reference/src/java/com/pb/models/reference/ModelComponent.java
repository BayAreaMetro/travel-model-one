/*
 * Copyright 2006 PB Consult Inc.
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
package com.pb.models.reference;

import java.util.ResourceBundle;


/**
 * This is the base class for model components.
 *
 * @author    Tim Heier
 * @version   1.0, 4/15/2000
 *
 */

public abstract class ModelComponent {

    //Name of model component
    String name;
    public ResourceBundle appRb; //this resource bundle holds application specific properties
    public ResourceBundle globalRb; //this resource bundle holds global definitions that are common
                                    //to several applications.

    public String getName() {
        return name;
    }


    public void setName(String name) {
        this.name = name;
    }

    abstract public void startModel(int baseYear, int timeInterval);

    public void setApplicationResourceBundle(ResourceBundle appRb){
        this.appRb = appRb;
    }

    public void setResourceBundles(ResourceBundle appRb, ResourceBundle globalRb){
        setApplicationResourceBundle(appRb);
        this.globalRb = globalRb;
    }

}
