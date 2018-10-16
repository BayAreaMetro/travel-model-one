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
package com.pb.common.http;

import java.io.*;

/**
 * The ClassFileServer implements a ClassServer that reads class files from the
 * file system. See the doc for the "Main" method for how to run this server.
 */
public class ClassFileServer extends ClassServer {

    private String classpath;

    private static int DefaultServerPort = 2001;

    /**
     * Constructs a ClassFileServer.
     * 
     * @param classpath
     *            the classpath where the server locates classes
     */
    public ClassFileServer(int port, String classpath) throws IOException {
        super(port);
        this.classpath = classpath;
    }

    /**
     * Returns an array of bytes containing the bytecodes for the class
     * represented by the argument <b>path</b>. The <b>path</b> is a dot
     * separated class name with the ".class" extension removed.
     * 
     * @return the bytecodes for the class
     * @exception ClassNotFoundException
     *                if the class corresponding to <b>path</b> could not be
     *                loaded.
     */
    public byte[] getBytes(String path) throws IOException, ClassNotFoundException {
        File f = new File(classpath + File.separator +
                                path.replace('.', File.separatorChar) + ".class");
        System.out.println("reading: " + f);

        int length = (int) (f.length());
        if (length == 0) {
            System.out.println("size = 0");
            throw new IOException("File length is zero: " + path);
        } else {
            System.out.println("size = " + f.length());
            FileInputStream fin = new FileInputStream(f);
            DataInputStream in = new DataInputStream(fin);

            byte[] bytecodes = new byte[length];
            in.readFully(bytecodes);
            return bytecodes;
        }
    }

    /**
     * Main method to create the class server that reads class files. This takes
     * two command line arguments, the port on which the server accepts requests
     * and the root of the classpath. To start up the server: <br>
     * <br>
     * 
     * <code>   java ClassFileServer <port> <classpath>
     * </code><br>
     * <br>
     * 
     * The codebase of an RMI server using this webserver would simply contain a
     * URL with the host and port of the web server (if the webserver's
     * classpath is the same as the RMI server's classpath): <br>
     * <br>
     * 
     * <code>   java -Djava.rmi.server.codebase=http://zaphod:2001/ RMIServer
     * </code>
     * <br>
     * <br>
     * 
     * You can create your own class server inside your RMI server application
     * instead of running one separately. In your server main simply create a
     * ClassFileServer: <br>
     * <br>
     * 
     * <code>   new ClassFileServer(port, classpath);
     * </code>
     */
    public static void main(String args[]) {
        if (args.length < 2) {
            System.out.println("ClassFileServer port classpath");
            return;
        }

        int port = Integer.parseInt(args[0]);
        String classpath = args[1];

        try {
            new ClassFileServer(port, classpath);
            System.out.println("ClassFileServer listening on port " + port);
        } catch (IOException e) {
            System.out.println("Unable to start ClassServer: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
