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
package com.pb.common.datafile;

import java.io.Serializable;

/**
 * Supported data types in table oriented data set classes.
 *
 * @author   Tim Heier
 * @version  1.0, 1/30/2003
 *
 */

public interface DataTypes extends Serializable {

      //Supported data types
      public final static int NULL      =  0;
      public final static int BOOLEAN   =  1;
      public final static int STRING    =  2;
      public final static int NUMBER    =  3;
      public final static int DOUBLE    =  4;
      public final static int OTHER     =  1111;
}
