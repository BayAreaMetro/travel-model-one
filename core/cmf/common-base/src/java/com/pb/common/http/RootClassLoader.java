package com.pb.common.http;

import java.net.URL;
import java.net.MalformedURLException;
import java.net.URLClassLoader;
import java.util.Hashtable;

/**
 * This class loads a class from a listens for log events on a socket connection from a Log4j
 *
 * @author    Tim Heier
 * @version   1.0, 9/30/2006
 *
 */
public class RootClassLoader {

    //Default value is localhost port 2001
    public static String ClassLoaderUrl = "http://localhost:2001/";

    //Stores the classloader associated with each className
    //classTable.put(className, classLoader);
    private static Hashtable classTable = new Hashtable();

    /**
     * This method loads a class from a URL given the fully qualified class
     * name includuing package. The ClassLoaderUrl should be set before
     * calling this method or else the default URL will be used.
     *
     * @param className
     * @throws ClassNotFoundException
     */
    public static void loadClassByName(String className) throws ClassNotFoundException {
        URL url = null;
        try {
            url = new URL(ClassLoaderUrl);
        } catch (MalformedURLException e) {
            e.printStackTrace();
        }
        URL[] urls = new URL[] { url };

        URLClassLoader classLoader = new URLClassLoader(urls);
        Class cls = null;
        try {
            cls = classLoader.loadClass( className );
            System.out.println(cls.getClassLoader().toString());
        } catch (ClassNotFoundException e) {
            throw e;
        }

        try {
            Object obj = cls.newInstance();
            ((Runnable)obj).run();
        } catch (InstantiationException e) {
            e.printStackTrace();
        } catch (IllegalAccessException e) {
            e.printStackTrace();
        }

        //Store the classloader associated with a className
        classTable.put(className, classLoader);
    }

    /**
     * This method deletes a reference to a classloader allowing a class to
     * be loaded again.
     *
     * @param className
     */
    public static boolean unLoadClassByName(String className) {
        URLClassLoader classLoader = (URLClassLoader) classTable.remove(className);

        if (classLoader == null) {
            return false;
        }
        classLoader = null;

        return true;
    }
}
