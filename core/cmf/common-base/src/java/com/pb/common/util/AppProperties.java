package com.pb.common.util;

/**
 * AppProperties is used to access an application-specific properties file.
 * This class also reads the properties file with a specific character encoding.
 *
 * NOTE: This class doesn't support the "\" escape character at the end 
 * of the input line like the Properties class does.
 *
 * @author    Tim Heier
 * @version   1.0, 7/18/2000
 * @see       java.util.Properties
 * @deprecated
 */

import java.io.BufferedReader;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.util.Enumeration;
import java.util.Hashtable;

public class AppProperties {

    //TODO -  Read from an environment variable?
    // public static final String CHAR_ENC = "SJIS";
    public static final String CHAR_ENC = "ISO8859_1";

    private String propsFile = null;
    private Hashtable props = null;
    private boolean reloadFlag = false;

    /*--------------------------------------------------*/

    /**
     * Creates AppProperties based on the specified property file.
     * 
     * @param pFile path to the application's property file.
     * @throws properties file is invalid or not found.
     */
    public AppProperties(String pFile) throws Exception {
        if (pFile == null) {
            throw new Exception(pFile);
        }
        propsFile = pFile;
        loadProperties();
    }

    /*--------------------------------------------------*/

    /**
     * Enable or disable the reload from properties file. By  default
     * it is disable. Set it to <code>true</code> will cause it to
     * reload every time the '<code>getXXX()</code>' is called.
     * This feature is useful mostly for debugging.
     * 
     * @param b <code>true</code> to call 'always reload'
     *          <code>false</code> to never reload again
     * @return the old setting
     */
    public boolean setReload(boolean b) {
        boolean oldFlag = reloadFlag;
        reloadFlag = b;
        return oldFlag;
    }

    /*--------------------------------------------------*/

    /**
     * Gets the property values from the given key.
     * 
     * @param key key string
     * @return value of the specified key
     */
    public String getProperty(String key) {
        if (reloadFlag) {
            loadProperties();
        }
        String p = (String) props.get(key);
        return p == null ? null : p.trim();
    }

    /*--------------------------------------------------*/

    /**
     * Gets the property values from the given key and if the key
     * is not found, return the specified default value.
     * 
     * @param key    key string
     * @param defVal default value to be returned if not found
     * @return value of the specified key if found, otherwise
     *         returns the specified default value.
     */
    public String getProperty(String key, String defVal) {
        if (reloadFlag) {
            loadProperties();
        }

        String p = (String) props.get(key);
        if (p == null)
            p = defVal;
        return (p.trim());
    }

    /*--------------------------------------------------*/

    /**
     * Gets the property values of type <code>int</code> from the
     * given key string.
     * 
     * @param key key string
     * @return value of the specified key (as <code>int</code>)
     */
    public int getIntProperty(String key) {
        if (reloadFlag) {
            loadProperties();
        }
        String val = (String) props.get(key);
        return (new Integer(val.trim())).intValue();
    }

    /*--------------------------------------------------*/

    /**
     * Gets the property values of type <code>int</code> from the
     * given key string. If the key is not found, return the specified
     * default value.
     * 
     * @param key    key string
     * @param defVal default value to be returned if not found
     * @return value of the specified key (as <code>int</code>)
     *         if found, otherwise, return default value.
     */
    public int getIntProperty(String key, String defVal) {
        if (reloadFlag) {
            loadProperties();
        }

        String val = (String) props.get(key);
        if (val == null)
            val = defVal;
        return (new Integer(val.trim())).intValue();
    }

    /*--------------------------------------------------*/

    /**
     * Returns the number of all the keys in this application property list
     * 
     * @return number of keys in this application property list
     */
    public int size() {
        return (props.size());
    }

    /*--------------------------------------------------*/

    /**
     * Returns a String array of all the keys in this property list
     * 
     * @return array of keys in this property list
     */
    public String[] getKeys() {
        String[] keys = new String[props.size()];
        Enumeration e = props.keys();
        int i = 0;
        while (e.hasMoreElements()) {
            keys[i++] = (String) e.nextElement();
        }
        return (keys);
    }

    /*--------------------------------------------------*/

    /**
     * Load the properties key/value pairs from the specified file.
     */
    private void loadProperties() {
        Hashtable oldProps = props;

        try {
            /* This code will work with Java 1.2 but not 1.1, Ugh...
            InputStreamReader isr = new InputStreamReader ( 
                                         new FileInputStream(propsFile), CHAR_ENC);
            */

            props = readFile();
        } catch (Exception ex) {
            System.err.println("AppProperties: can't load properties: " + ex);
            // failed to load properties file, use the old one.
            props = oldProps;
        }
    }


    /**
     * Returns a Hashtable which can be passed into the load() method of
     * a properties object.
     * 
     * @return Hashtable of key/values from properties file
     */
    private Hashtable readFile() {

        String line = null;
        Hashtable p = new Hashtable();

        try {
            BufferedReader fr = new BufferedReader(
                    new InputStreamReader(
                            new FileInputStream(propsFile), CHAR_ENC));

            while ((line = fr.readLine()) != null) {
                int index = line.indexOf("=");

                if (index >= 0) {
                    String key = line.substring(0, index).trim();
                    String value = line.substring(index + 1, line.length()).trim();
                    p.put(key, value);
                }
            }
            fr.close();
        } catch (Exception e) {
            e.printStackTrace();
            System.err.println("*Error reading properties file: " + propsFile);
        }

        return (p);
    }

}

