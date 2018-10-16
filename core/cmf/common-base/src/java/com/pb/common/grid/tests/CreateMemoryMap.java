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

import com.pb.common.grid.tests.CreateBinaryFile;

import java.io.File;
import java.io.RandomAccessFile;
import java.io.IOException;
import java.nio.channels.FileChannel;
import java.nio.ByteBuffer;

public class CreateMemoryMap {

    public static void ReadUsingMM() {

        long sum = 0;
        long breather = CreateBinaryFile.ELEMENTS / 2;
        long startTime = 0;
        long endTime = 0;

        try {
            File file = new File("test.bin");

            startTime = System.currentTimeMillis();

            // Create a read-write memory-mapped file
            FileChannel channel = new RandomAccessFile(file, "rw").getChannel();
            ByteBuffer buf = channel.map(FileChannel.MapMode.READ_WRITE, 0, (int)channel.size());

            for (int i=0; i < CreateBinaryFile.ELEMENTS; i++) {
                sum += buf.getInt();

                if (i == breather) {
                    //System.out.println("halfway done...");
                    //System.in.read();
                }
            }
            endTime = System.currentTimeMillis();
        }
        catch (IOException e) {
            e.printStackTrace();
        }

        System.out.println("sum = " + sum);
        System.out.println("time = " + (endTime-startTime) );
    }

    public static void main(String[] args) {

        ReadUsingMM();
    }

}
