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

import java.util.Hashtable;
import java.util.Vector;

/**
 * This class is used to process the command line arguements and store
 * the list of options and parameters supplied on the command-line. The
 * difference between an option and a command line is that an option
 * is a boolean value (true if it is specified and false otherwise)
 * and a parameter always has an associated value.
 * 
 * @author Tim Heier
 * @version 1.0, 9/30/2003
 */
public class CommandLine {

    /**
     * A list of option of switches on the command line. A switch
     * is either set or not
     */
    private Vector switches = new Vector();

    /** A dictionary of all the options and their associated values */
    private Hashtable options = new Hashtable();

    /**
     * Construct an instance of this class with the specified string
     * array.
     * 
     * @param args command line argument
     */
    public CommandLine(String[] args) {
        processCommandLine(args);
    }

    /**
     * Default constructor
     */
    public CommandLine() {
    }

    /**
     * Check if the following option or command has been specified
     * 
     * @param name name of option or command
     * @return boolean  true if it has been specified
     */
    public boolean exists(String name) {
        return switches.contains(name) || options.containsKey(name);
    }

    /**
     * Check if the following option has been specified
     * 
     * @param name name of the option
     * @return boolean   true if it has been specified
     */
    public boolean isSwitch(String name) {
        return switches.contains(name);
    }

    /**
     * Check if the following parameter has been specified
     * 
     * @param name name of the parameter
     * @return boolean  true if it has been specified
     */
    public boolean isParameter(String name) {
        return options.containsKey(name);
    }

    /**
     * Return the value of the parameter or option. If the string nominates
     * an option then return null
     * 
     * @param name name of option or parameter
     * @return String   value of parameter or null
     */
    public String value(String name) {
        String result = null;

        if (options.containsKey(name)) {
            result = (String) options.get(name);
        }

        return result;
    }

    /**
     * Return the value of the parameter or option, returning a default
     * value if none is specified
     * 
     * @param name         name of option or parameter
     * @param defaultValue the default value
     * @return String   value of parameter
     */
    public String value(String name, String defaultValue) {
        String result = value(name);
        return (result != null) ? result : defaultValue;
    }

    /**
     * Add the following option or parameter to the list. An option will
     * have a null value, whereas a parameter will have a non-null value.
     * <p/>
     * This will automatically overwrite the previous value, if one has been
     * specified.
     * 
     * @param name  name of option or parameter
     * @param value value of name
     * @return boolean   true if it was successfully added
     */
    public boolean add(String name, String value) {
        return add(name, value, true);
    }

    /**
     * Add the following option or parameter to the list. An option will
     * have a null value, whereas a parameter will have a non-null value.
     * <p/>
     * If the overwrite flag is true then this value will overwrite the
     * previous value. If the overwrite flag is false and the name already
     * exists then it will not overwrite it and the function will return
     * false. In all other circumstances it will return true.
     * 
     * @param name      name of option or parameter
     * @param value     value of name
     * @param overwrite true to overwrite previous value
     * @return boolean   true if it was successfully added
     */
    public boolean add(String name, String value, boolean overwrite) {
        boolean result = false;

        if (value == null) {
            // it is an option
            if ((switches.contains(name)) &&
                    (overwrite)) {
                switches.addElement(name);
                result = true;
            } else if (!switches.contains(name)) {
                switches.addElement(name);
                result = true;
            }
        } else {
            // parameter
            if ((options.containsKey(name)) &&
                    (overwrite)) {
                options.put(name, value);
                result = true;
            } else if (!options.containsKey(name)) {
                options.put(name, value);
                result = true;
            }
        }

        return result;
    }

    /**
     * This method processes the command line and extracts the list of
     * options and command lines. It doesn't intepret the meaning of the
     * entities, which is left to the application.
     * 
     * @param args command line as a collection of tokens
     */
    private void processCommandLine(String[] args) {
        boolean prev_was_hyphen = false;
        String prev_key = null;

        for (int index = 0; index < args.length; index++) {
            if (args[index].startsWith("-")) {
                // if the previous string started with a hyphen then
                // it was an option store store it, without the hyphen
                // in the switches vector. Otherwise if the previous was
                // not a hyphen then store key and value in the options
                // hashtable
                if (prev_was_hyphen) {
                    add(prev_key, null);
                }

                prev_key = args[index].substring(1);
                prev_was_hyphen = true;

                // check to see whether it is the last element in the
                // arg list. If it is then assume it is an option and
                // break the processing
                if (index == args.length - 1) {
                    add(prev_key, null);
                    break;
                }
            } else {
                // it does not start with a hyphen. If the prev_key is
                // not null then set the value to the prev_value.
                if (prev_key != null) {
                    add(prev_key, args[index]);
                    prev_key = null;
                }
                prev_was_hyphen = false;
            }
        }
    }

}
