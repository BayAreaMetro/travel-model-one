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
package com.pb.common.calculator2;

import java.io.Serializable;

public class IndexValues implements Serializable {

    public int o = -1;
    public int d = -1;
    public int s = -1;
    public int z = -1;
    public int h = -1;
    public int i = -1;
    public int j = -1;

    public String toString() {
        return "[o="+o +", d="+d +", s="+s +"z="+z +", h="+h +", i="+i +", j="+j +"]";
    }

}
