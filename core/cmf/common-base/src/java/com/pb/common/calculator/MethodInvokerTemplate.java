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
package com.pb.common.calculator;

import java.io.*;

import java.lang.reflect.Method;

import java.net.URL;
import java.net.URLClassLoader;

import java.security.CodeSource;
import java.security.ProtectionDomain;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.Map;
import java.util.Properties;

import org.apache.log4j.Logger;

/**
 * A template class used to build the MethodInvoker class.
 *
 * @author    Tim Heier
 * @version   1.0, 9/03/2003
 */
public class MethodInvokerTemplate implements Serializable {

    private static Logger logger = Logger.getLogger("com.pb.common.calculator");

    private String className;

    private String sourceCode;

    //System properties
    private String tempDir = System.getProperty("java.io.tmpdir");
    private String fileSeparator = System.getProperty("file.separator");

    private static String pathString;

    private Class clazz;

    //List of methods that takes no arguements
    private ArrayList methodList = new ArrayList();

    
    public MethodInvokerTemplate( Class clazz ) {
        setup( clazz );
    }

    public MethodInvokerTemplate( Object obj ) {
        setup( obj.getClass() );
    }

    
    private void setup ( Class clazz ) {
        this.clazz = clazz;
        if(clazz == null) {
        	return;
        }
        if ( pathString == null )
            pathString = getCompileClasspath();
    }

	synchronized public int addMethod(String methodName, boolean intArguement) throws NoSuchMethodException {
        //No user class was supplied
        if (clazz == null) {
            return 0;
        }

        Method method = null;
        Class[] argTypes = new Class[1];

        if (intArguement) {
            argTypes[0] = int.class;
        } else {
            argTypes = null;
        }

        try {
            method = clazz.getMethod(methodName, argTypes);
        } catch (SecurityException e) {
            logger.error("caught exception in MethodInvokerTemplate.addMethod()", e);
        } catch (NoSuchMethodException e) {
            throw e;
        }

        //Add method to list of methods
        methodList.add(method);

        return methodList.size()-1;
    }


    synchronized public MethodInvoker generateAndLoadClass() {

        if (clazz == null) {
            logger.debug("No DMU class supplied in UEC constructor");
            return null;
        }

        //Make sure that tempDir ends with a "/" or "\"
        if (! tempDir.endsWith(fileSeparator)) {
            tempDir = tempDir + fileSeparator;
        }

        logger.debug("temp directory: " + tempDir);

        File sourceFile = null;
        try {
             sourceFile = File.createTempFile("MethodInvokerImpl", ".java", new File(tempDir));
        } catch (IOException e) {
            logger.error("caught exception in MethodInvokerTemplate.generateAndLoadClass()", e);
        }
        
        //Strip off the ".java" ending to isolate just the class name
        int end = sourceFile.getName().indexOf(".java");
        className = sourceFile.getName().substring(0,end);
        
        createSourceFile(sourceFile);

        compileSourceFile(tempDir, sourceFile);

        //Load compiled class file 
        try {
            //Convert File to a URL
            URL url = (new File(tempDir)).toURL();  // file:/c:/%temp%/
            URL[] urls = new URL[] { url };

            logger.debug("loading " + "scratch."+className + ".class from: " + url);

            
            
            //Create a new class loader with the directory
            ClassLoader cl = new URLClassLoader(urls, Thread.currentThread().getContextClassLoader() );
            //ClassLoader cl = new URLClassLoader(urls);

            //Load in the class MethodInvoker.class
            Class cls = cl.loadClass("scratch."+className);

            //Create an instance of the class
            MethodInvoker methodInvoker = (MethodInvoker) cls.newInstance();

            //Delete Java source file
            deleteFiles(sourceFile, tempDir, className);
            
            return methodInvoker;
        } catch (Throwable t) {
            logger.error("caught exception in MethodInvokerTemplate.generateAndLoadClass()", t);
        }

        return null;
    }


    /**
     * Generate MethodInvoker class source file - done in two steps:
     * 1. Generate source code as a string so it can be saved for debugging
     * 2. Write string out to a new file
     */
    private void createSourceFile(File sourceFile) {

        logger.debug("creating "+className+".java at: " + sourceFile);

        StringWriter sWriter = new StringWriter(4096);
        PrintWriter out = new PrintWriter(sWriter);

        out.println("package scratch;");
        out.println();
        out.println("import com.pb.common.calculator.MethodInvoker;");
        out.println();
        out.println("import java.io.Serializable;");
        out.println("import org.apache.log4j.Logger;");

        out.println();
        out.println("public class "+className+" implements MethodInvoker, Serializable {");
        out.println();
        out.println("protected transient Logger logger = Logger.getLogger(\"com.pb.common.calculator\");");
        out.println();
        out.println("    public double invoke(Object obj, int methodNumber, int alternativeNumber) {");
        out.println();
        out.println("        "+clazz.getName()+ " dmu = ("+clazz.getName()+") obj;" );
        out.println();
        out.println("        switch (methodNumber) {");
        out.println();

        for (int i = 0; i < methodList.size(); i++) {
            Method m = (Method) methodList.get(i);
            if (m.getParameterTypes().length > 0)
                out.println("            case " + i + ": return dmu." + m.getName() + "(alternativeNumber);");
            else
                out.println("            case " + i + ": return dmu." + m.getName() + "();");

        }

        out.println("            default:");
        out.println("                logger.error(\"method number = \"+methodNumber+\" not found\");");
        out.println("                throw new RuntimeException(\"method number = \"+methodNumber+\" not found\");");
        out.println("        }");
        out.println("    }");
        out.println("}");

        out.close();

        sourceCode = sWriter.toString();

        //Write file to temporary location - reuse PrinterWriter
        try {
            PrintWriter pout = new PrintWriter(new FileWriter(sourceFile));
            pout.print(sourceCode);
            pout.close();
        } catch (IOException e) {
            logger.error("caught exception in MethodInvokerTemplate.createSourceFile()", e);
        }

    }


    private void compileSourceFile(String tempDir, File sourceFile) {

        
        //Compile source file by exec'ing a javac process
        try {
            String command = "javac -classpath " + pathString + " -d " + tempDir + " " + sourceFile;

            logger.debug("compiling: " + command);

            Process child = Runtime.getRuntime().exec( command );
            try {
                child.waitFor();
            }
            catch (InterruptedException e) {
                logger.error("caught exception in MethodInvokerTemplate.compileSourceFile() - inner", e);
            }
        }
        catch (IOException e) {
            logger.error("caught exception in MethodInvokerTemplate.compileSourceFile() - outer", e);
        }
    }

    

    private String getCompileClasspath() {

        ProtectionDomain pDomain;
        CodeSource cSource;
        URL loc;

        String miClasspath = null;
        
        Properties sysProps = System.getProperties();
        Enumeration names = sysProps.propertyNames();
        while (names.hasMoreElements()) {
            String key = (String) names.nextElement();
            String value = (String) sysProps.get(key);

            // if -DmethodInvokerClasspath=... was defined for this VM, use the path specified,
            // else use the default procedure below.
            if ( key.equalsIgnoreCase( "methodInvokerClasspath" ) ) {
                miClasspath = value;
                break;
            }
        }
        
        String ps = System.getProperty("path.separator");
        
        if ( miClasspath == null ) {
          
            //Need to know where MethodInvoker interface can be loaded from
            pDomain = com.pb.common.calculator.MethodInvoker.class.getProtectionDomain();
            cSource = pDomain.getCodeSource();
            loc = cSource.getLocation();
            String miClassLoc = loc.getFile();
            miClassLoc = adjustString(miClassLoc);

            logger.debug("MethodInvoker interface loaded from: " + miClassLoc);

            //Need to know where DMU class can be loaded from
            pDomain = clazz.getProtectionDomain();
            cSource = pDomain.getCodeSource();
            loc = cSource.getLocation();
            String dmuClassLoc = loc.getFile();
            dmuClassLoc = adjustString(dmuClassLoc);

            logger.debug("DMU class loaded from: " + dmuClassLoc);

            // get location from which DMU base class can be loaded - could be null if DMU is not a derived class
            // ignore it if it's the same location as the derived class
            pDomain = clazz.getSuperclass().getProtectionDomain();
            cSource = pDomain.getCodeSource();
            String dmuSuperClassLoc = "";
            if ( cSource != null ) {
                loc = cSource.getLocation();
                dmuSuperClassLoc = loc.getFile();
                dmuSuperClassLoc = adjustString(dmuSuperClassLoc);

                if ( dmuSuperClassLoc.equalsIgnoreCase(dmuClassLoc) )
                    dmuSuperClassLoc = "";
            }

            logger.debug("DMU base class loaded from: " + dmuSuperClassLoc);

            miClasspath = miClassLoc + ps + dmuClassLoc + ps + dmuSuperClassLoc;
        }
        

        //Need to know where Logger class can be loaded from
        pDomain = org.apache.log4j.Logger.class.getProtectionDomain();
        cSource = pDomain.getCodeSource();
        loc = cSource.getLocation();
        String loggerClassLoc = loc.getFile();
        loggerClassLoc = adjustString(loggerClassLoc);

        logger.debug("Logger class loaded from: " + loggerClassLoc);
        

        String miClasspathString = miClasspath + ps + loggerClassLoc;
        
        return miClasspathString;

    }


    //Delete the Java source file
    private void deleteFiles(File sourceFile, String tempDir, String className) {

        logger.debug("deleting " + sourceFile);
        try {
            sourceFile.delete();
        } catch (Exception e) {
            logger.error("could delete source file", e);
        }

        File classFile = new File(tempDir + fileSeparator + "scratch" + fileSeparator + className + ".class");
        logger.debug("deleting " + classFile);
        try {
            classFile.delete();
        } catch (Exception e) {
            logger.error("could delete class file", e);
        }
    }


    private String adjustString(String str) {

        //Look for this /C:/files/pbdev/classes/
        //Trim the first / from the beginning of the string - must be a VM bug
        if ((fileSeparator.equals("\\")) && (str.startsWith("/"))  ) {
            str = str.substring(1);
        }

        return str;
    }

    /**
     * Returns the source code generated by the createSourceFile() method.
     *
     * @return source code for generated class
     */
    public String getGeneratedSourceCode() {
        return sourceCode;
    }

    /**
     * Returns the name of the source code and class file prefix generated by the createSourceFile() method.
     *
     * @return prefix of temp filenames generated (prefix.java and scratch/prefix.class)
     */
    public String getGeneratedSourceCodePrefix() {
        return className;
    }

}
