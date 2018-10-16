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

import java.io.ByteArrayOutputStream;
import java.io.DataOutput;
import java.io.IOException;

/**
 * Extends ByteArrayOutputStream to provide a way of writing the buffer to
 * a DataOutput without re-allocating it.
 */
public class DbByteArrayOutputStream extends ByteArrayOutputStream {

    public DbByteArrayOutputStream() {
        super();
    }


    public DbByteArrayOutputStream(int size) {
        super(size);
    }

    /**
     * Writes the full contents of the buffer a DataOutput stream.
     */
    public synchronized void writeTo(DataOutput dstr) throws IOException {
        byte[] data = super.buf;
        int l = super.size();

        dstr.write(data, 0, l);
    }
}
