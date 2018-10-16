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

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;

/**
 * A class that returns a Print Writer object. Takes as its argument a
 * path\filename string.
 */
public class OutTextFile {


    PrintWriter pwFile;

    public OutTextFile() {
    }

    public PrintWriter open(String f) {
        try {
            pwFile = new PrintWriter(
                    new BufferedWriter(
                            new FileWriter(f)));
        } catch (IOException e) {
            System.out.println("Could not open file " + f + " for writing\n");
            System.exit(1);
        }
        return pwFile;
    }

    public void writeLine(String line) throws IOException {
        pwFile.println(line);
    }

    public void println(String line) throws IOException {
        pwFile.println(line);
    }

    public void println() throws IOException {
        pwFile.println();
    }

    public void print(String line) throws IOException {
        pwFile.print(line);
    }


    public void close() throws IOException {
        pwFile.close();
    }
}
