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
package com.pb.common.daf;

import java.io.*;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.Properties;
import org.apache.log4j.Logger;

/**
 * Contains utility operations for working with Class files.
 * 
 * @author Tim Heier
 * @version 1.0, 11/9/2003
 */
public class ClassUtil {

    private static Logger logger = Logger.getLogger(ClassUtil.class);
    
    /**
     * Create a classloader with the parent being the extension class loader.
     * 
     * Default classloader in a VM is:
     * boot classloader-->extension classloader-->system classloader
     *  
     * @return class loader rooted at extension classloader
     */
    public static URLClassLoader createURLClassLoader(URL[] urls) {
        URLClassLoader urlLoader = null;
        try {
            //Get a reference to the extension classloader
            ClassLoader extClassLoader = Thread.currentThread().getContextClassLoader().getParent();
            
            //Create a new class loader from a list of URLs
            urlLoader = new URLClassLoader(urls, extClassLoader);
        } catch (Exception e) {
            logger.error("Error creating ClassLoader", e);
        }

        return urlLoader;
    }

    
    public static String classToPath(String name) {
        Properties properties = System.getProperties();
        String fileSeparator = properties.getProperty("file.separator");
        char fsc = fileSeparator.charAt(0);
        String path = name.replace('.', fsc);
        path += ".class";
        return path;
    }

    
    public static byte[] readFile(String filename) throws IOException {
        File file = new File(filename);
        long len = file.length();
        byte data[] = new byte[(int) len];
        FileInputStream fin = new FileInputStream(file);
        int r = fin.read(data);
        if (r != len) {
            throw new IOException("Only read " + r + " of " + len + " for " + file);
        }
        fin.close();
        return data;
    }

    
    public static byte[] getClassBytes(String name) throws IOException {
        String path = classToPath(name);
        return readFile(path);
    }

    
    public static void copyFile(OutputStream out, InputStream in) throws IOException {
        byte buffer[] = new byte[4096];

        while (true) {
            int r = in.read(buffer);
            if (r <= 0) {
                break;
            }
            out.write(buffer, 0, r);
        }
    }

    
    protected static void copyFile(OutputStream out, String infile) throws IOException {
        FileInputStream fin = new FileInputStream(infile);
        copyFile(out, fin);
        fin.close();
    }
}
