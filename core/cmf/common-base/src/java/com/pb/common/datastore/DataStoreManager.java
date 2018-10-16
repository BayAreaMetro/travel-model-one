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
package com.pb.common.datastore;

/**
 * Defines methods for interacting with a DataStore.
 *
 * @author    Tim Heier
 * @version   1.0, 7/30/2000
 *
 */
public interface DataStoreManager {

    /**
     * Add an object to data-store.
     */
    public void addObject(String objName, Object obj);
    
    /**
     * Return a TableDataSet object.
     */
    public Object getObject(String name);

    /**
     * Open underlying data-store.
     */
    public void openStore();
    
    /**
     * Close the underlying data-store.
     */
    public void closeStore();
    
    /**
     * Create a new data-store.
     */
    public void createStore();
    
}


