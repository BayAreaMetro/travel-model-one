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
package com.pb.common.grid.tests;

import java.io.File;
import java.io.RandomAccessFile;
import java.io.IOException;
import java.nio.channels.FileChannel;
import java.nio.ByteBuffer;

/** This class is used to create large binary files for testing purposes.
 *
 * @author    Tim Heier
 * @version   1.0, 7/03/03
 *
 */
public class CreateBinaryFile {

    public static long ELEMENTS = 1024000;  // 1,024,000 * 4 = 4,096,000

    public static long ELEMENTS2 = 837000000;  // 31000 * 27000 * 2 = 1,674,000,000 bytes

    public static void main(String[] args) {
    
        try {
            File file = new File("test.bin");
            FileChannel channel = new RandomAccessFile(file, "rw").getChannel();

            ByteBuffer buf = ByteBuffer.allocate(8);

            for (int i=0; i < ELEMENTS2; i++) {
                buf.clear();
                //buf.putShort( (short)0);
                buf.putDouble( 1 );
                buf.flip();
                channel.write(buf);
            }
        }
        catch (IOException e) {
            e.printStackTrace();
        }
    
    }
    
}
