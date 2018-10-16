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
 * Defines a type-safe enumeration of file types supported in the datafile package.
 *
 * @author    Tim Heier
 * @version   1.0, 5/08/2004
 */
public final class FileType implements Serializable {

    public static final FileType BINARY = new FileType("Binary");
    public static final FileType ZIP = new FileType("ZIP");
    public static final FileType CSV = new FileType("CSV");

    private String id;

    /** Keep this class from being created with "new".
     *
     */
    private FileType(String id) {
        this.id = id;
    }

    public String toString() {
        return this.id;
    }

    public boolean equals(FileType type) {
        boolean result = false;

        int index = type.toString().indexOf(this.id);
        if (index == 0)
            result = true;

        return result;
    }
}
