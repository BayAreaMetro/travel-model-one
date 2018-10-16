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

import java.io.*;
import java.util.*;

/**
 * This class represents a text file and has convenience methods for working 
 * with lines of text in the file.
 *  
 * @author Tim Heier
 * @version  1.0, 7/23/2006
 */
public class TextFile extends ArrayList<String> {

    //Holds end-of-line separator for current platform
    public static String EOL;
    
    //Get end-of-line separator from operating system
    static {
        EOL = System.getProperty("line.separator");
    }
    
    String fileName;
    
    
    /**
     * Constructor to create a brand new text file.
     * 
     */
    public TextFile() {
        
    }
    
    /**
     * Basic constructor which reads file line by line.
     * 
     * @param fileName name of file to open and read
     */
    public TextFile(String fileName) {
        this(fileName, EOL);
    }

    /**
     * Read a file and split by any regular expression. Default splitter
     * is the platform dependent end-of-line character.
     * 
     * @param fileName name of file to open and read
     * @param splitter end-of-line separator, default is EOL for system
     */
    public TextFile(String fileName, String splitter) {
        super(Arrays.asList(readFrom(fileName).split(splitter)));
        
        //Remember file name for write() method
        this.fileName = fileName;
        
        //Regular expression split() often leaves an empty
        //String at the first position:
        if (get(0).equals(""))
            remove(0);
    }

    /**
     * Adds a string to the current TextFile object. Wrapper for underlying
     * ArrayList.add() method.
     * 
     * @param line string to add to file
     */
    public void addLine(String line) {
        add(line);
    }
    
    /**
     * Returns a line from the current TextFile object given a line number. Line
     * numbers start at 0. Wrapper for underlying ArrayList.get() method.
     * 
     * @param lineNumber string to add to file
     */
    public String getLine(int lineNumber) {
        return get(lineNumber);
    }
    
    /**
     * Updates a line in the current TextFile object given a line number. Line
     * numbers start at 0. The old line is returned. Wrapper for underlying 
     * ArrayList.set() method.
     * 
     * @param lineNumber string to add to file
     * @param newLine represents the new line character
     * @return the old line
     */
    public String setLine(int lineNumber, String newLine) {
        return set(lineNumber, newLine);
    }
    
    /**
     * Read a file as a single string. This method is static and can
     * be called directly without creating a TextFile object.
     * 
     * @param fileName name of the file to read from 
     */
    public static String readFrom(String fileName) {
        StringBuilder sb = new StringBuilder(4096);
        try {
            BufferedReader in = new BufferedReader(
                                    new FileReader(
                                        new File(fileName).getAbsoluteFile()));
            try {
                String s;
                while ((s = in.readLine()) != null) {
                    sb.append(s);
                    sb.append(EOL);
                }
            } finally {
                in.close();
            }
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        return sb.toString();
    }

    synchronized public void write() {
        writeTo(this.fileName, false);
    }
    
    synchronized public void write(boolean append) {
        writeTo(this.fileName, append);
    }
    
    /**
     * Write a single file in one method call. This method is static and can
     * be called directly without creating a TextFile object.
     * 
     * @param fileName name of file to create and write to
     * @param text contents of file
     */
    synchronized public static void writeTo(String fileName, String text) {
        try {
            PrintWriter out = new PrintWriter(
                                  new File(fileName).getAbsoluteFile());
            try {
                out.print(text);
            } finally {
                out.close();
            }
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }
    
    /**
     * Writes the contents of a TextFile object to a specified file. The 
     * destination file can be opened in append mode otherwise it will be
     * created if it does not exist.
     * 
     * @param fileName name of file to write to
     * @param append flag, true to open file for appending 
     */
    synchronized public void writeTo(String fileName, boolean append) {
        try {
            FileWriter fWriter = 
                    new FileWriter(new File(fileName).getAbsoluteFile(), append);
            BufferedWriter bWriter = new BufferedWriter(fWriter);
            PrintWriter out = new PrintWriter(bWriter);
            try {
                for (String item : this)
                    out.println(item);
            } finally {
                out.close();
            }
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    synchronized public void writeTo(String fileName) {
        writeTo(fileName, false);
    }
    
    //Used for testing
    public static void main(String[] args) {
        
        //Create a text file in memory and then write it to a file
        TextFile newFile = new TextFile();
        newFile.addLine("line #1");
        newFile.addLine("line #2");
        newFile.addLine("line #3");
        newFile.addLine("line #4");
        newFile.setLine(2, "line #3 was replaced with this line");
        newFile.writeTo("testfile.txt");
        
        //Example #1: Read previous file into one string
        String fileContents = TextFile.readFrom("testfile.txt");
        
        //Example #2: Write a string to a new file
        TextFile.writeTo("copy of test.txt", fileContents);

        //Example #3: Read a file into an Arraylist based on separator
        TextFile txtFile = new TextFile("testfile.txt");

        System.out.println("number of lines="+ txtFile.size());
        
        //Example #3 (cont'd): Change a line by directly accessing it
        txtFile.setLine(2, "line #3 has been changed");
        
        //Print out to console to check
        for (String s : txtFile) {
            System.out.println(s);
        }
    }
}
/*Output:
number of lines=10
49   35   91   41   82   58   63   46   32   21   
68   33   20   17   43   58   49   89   21   37   
line #2 has been changed
17   30   58   86   83   42   43   50   41   18   
75   20   17   88   49   46   68   60   58   23   
61   31   36   58   42   74   42   72   71   44   
30   47   67   18   94   51   61   78   72   58   
35   84   15   97   98   20   49   61   70   63   
67   39   12   87   34   88   47   47   12   43   
70   15   87   95   77   55   76   55   93   36   
*/
