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

public class ModelEntry implements Serializable {

    public String name;
    public String description;
    public String filter;
    public String expression;
    public String index;

    public ModelEntry(String name, String description, String filter, String expression, String index) {
        this.name = name.trim();
        this.description = description;
        this.filter = filter.trim();
        this.expression = expression.trim();
        this.index = index.trim();
    }

    public String toString() {
        return "name="+name+", description="+description+", filter="+filter+
                ", expression="+expression+", index="+index;
    }
}
