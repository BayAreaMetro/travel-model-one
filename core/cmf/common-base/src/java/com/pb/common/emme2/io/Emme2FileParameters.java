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
package com.pb.common.emme2.io;

/** Holds information on internal databank files.
 * 
 * History: 
 * Originally written in C by Tim Heier and then ported to Java 
 * by Joel Freedman.
 *
 * @author    Tim Heier
 * @author    Joel Freedman
 * @version   1.0, 9/19/2002
 */
public class Emme2FileParameters {
    public  long  offset;   //in bytes
    public  int   nrecs;
    public  int   reclen;   //in bytes
    public  int   type;

    public Emme2FileParameters() {
    }

}
