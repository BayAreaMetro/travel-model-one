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
 * Enumeration class of PerformanceTimerTypes.
 *
 * @author    Tim Heier
 * @version   1.0, 8/6/2005
 */
public enum PerformanceTimerType {

    CPU,              //cpu bound operations

    //--- File IO ---
    FILE_IO,          //general file i/o

    FILE_READ,        //track reading files
    FILE_WRITE,       //track writing files

    CSV_READ,         //track CSV file reads
    CSV_WRITE,        //track CSV file writes

    MATRIX_READ,      //track matrix file reads
    MATRIX_WRITE,     //track matrix file writes

    //--- Database IO ---
    DB_IO,            //database operations
    DB_READ,          //track reading from a database
    DB_WRITE,         //track reading from a database

    //--- Remote calls ---
    RPC,              //Remote call - synchronous
    RPC_ASYNC,        //Remote call - asynchronous
    HTTP,             //Web operations
    RMI,              //Remote method invocation
    INVOKE,           //Method invoked via a remote call

    OTHER             //When you don't know what else to use!
}
