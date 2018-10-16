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
//here is a class that returns a Buffered Reader object,
//takes as its argument a path\filename string

package com.pb.common.util;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;

public class InTextFile {

    BufferedReader brFile;

    public InTextFile() {
    }

    public BufferedReader open(String f) {
        try {
            brFile = new BufferedReader(new FileReader(f));
        } catch (IOException e) {
            System.out.println("Could not open file " + f + " for reading\n");
            System.exit(1);
        }
        return brFile;
    }

    public String readLine() throws IOException {

        String line = new String();

        if (brFile.ready()) {
            //skip comments
            do {
                line = brFile.readLine();
            } while (line.startsWith("*"));
        }
        return line;
    }

    public void close() throws IOException {
        brFile.close();
    }
}
