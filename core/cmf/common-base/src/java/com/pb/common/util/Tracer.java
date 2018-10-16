/*
 * Copyright 2006 PB Consult Inc.
 * 
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License. You may obtain a copy of
 * the License at
 * 
 * http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 * 
 * Created on Jun 13, 2006 by Andrew Stryker <stryker@pbworld.com>
 */
package com.pb.common.util;

import com.pb.common.util.ResourceUtil;
import org.apache.log4j.Logger;

import java.io.Serializable;
import java.util.*;

/**
 * Hold a set of tracing options.
 * 
 * This object is implemented as a Singleton so that the tracing options do not
 * need to be set or passed into the code getting traced. When tracing is off,
 * there should be little impact on runtime since the code will not call the
 * ArrayList members.
 * 
 * The class is final to prevent it from being cloned.
 * 
 * @author Andrew Stryker <stryker@pbworld.com>
 * @version 1.0 Jun 29, 2006
 */
final public class Tracer implements Serializable {
    private transient static Logger logger = Logger.getLogger(Tracer.class);

    private transient static Tracer tracer = new Tracer();

    private final static long serialVersionUID = 0;

    private boolean traceOn = false;

    private ArrayList<Integer> rows;

    private ArrayList<Integer> columns;

    private Set<Integer> households;

    private Set<String> persons;

    private HashMap<String, Set<String>> keySets;

    /**
     * Hide the constructor for the Singleton pattern.
     */
    private Tracer() {
    }

    /**
     * Get a reference to the Trace singleton.
     * 
     * @return Tracer
     */
    public static Tracer getTracer() {
        return tracer;
    }

    /**
     * Set trace options from a property file.
     * 
     * Assumes rows are in "trace.itazs" and columns are in "trace.jtazs"
     * 
     * @param bundle
     */
    public void readTraceSettings(ResourceBundle bundle) {
        readTraceSettings(bundle, "sdt.trace.itazs", "sdt.trace.jtazs");
    }

    /**
     * Set the trace options from a property file.
     * 
     * @param bundle ResourceBundle with trace ArrayListings
     */
    public void readTraceSettings(ResourceBundle bundle, String rowProperty,
            String columnProperty) {
        try {
            setTrace(Boolean.parseBoolean(ResourceUtil.getProperty(bundle,
                    "trace")));
        } catch (MissingResourceException e) {
            logger.debug("Could not set trace.");
            return;
        }

        if (!isTraceOn()) {
            logger.info("Tracing is turned off.");   
            return;
        }
        logger.info("Tracing is turned on.");

        households = createSet(bundle, "sdt.trace.households");
        persons = createStringSet(bundle, "sdt.trace.persons");

        ArrayList<Integer> rows = createArrayList(bundle, rowProperty);
        ArrayList<Integer> columns = createArrayList(bundle, columnProperty);

        // ensure that the arrays have the same length
        if (rows != null && columns != null) {
            String pairs = "";
            if (rows.size() != columns.size()) {
                logger.error("Unequal number of rows and columns.");
            } else {
                for (int i = 0; i < rows.size() && i < columns.size(); ++i) {
                    traceZonePair(rows.get(i), columns.get(i));
                    pairs += "(" + rows.get(i) + "," + columns.get(i) + ") ";
                }
            }
            logger.info("Tracing these zone pairs: " + pairs);
        }

    }

    private ArrayList<Integer> createArrayList(ResourceBundle rb,
            String property) {
        ArrayList<Integer> arrayList = null;

        try {
            String[] strings = ResourceUtil.getArray(rb, property);
            arrayList = new ArrayList<Integer>();

            for (String s : strings) {
                arrayList.add(Integer.parseInt(s));
            }

        } catch (MissingResourceException e) {
            if (isTraceOn()) {
                logger.warn("Could not set " + property + " traces.");
            }
        }

        return arrayList;
    }

    private Set<Integer> createSet(ResourceBundle rb, String property) {
        Set<Integer> set = null;

        try {
            String[] strings = ResourceUtil.getArray(rb, property);
            set = new HashSet<Integer>();

            for (String s : strings) {
                set.add(Integer.parseInt(s));
            }

        } catch (MissingResourceException e) {
            if (isTraceOn()) {
                logger.warn("Could not set " + property + " traces.");
            }
            return null;
        }

        logger.info("Traces for " + property);
        for (int s : set) {
            logger.info("\t" + s);
        }

        return set;
    }

    /**
     * Store arbitrary trace sets.
     * 
     * @param bundle
     * @param property
     * @param key
     */
    public void readKeySet(ResourceBundle bundle, String key, String property) {
        Set<String> set;

        if (keySets == null) {
            keySets = new HashMap<String, Set<String>>();
        }

        if (keySets.containsKey(key)) {
            set = keySets.get(key);
        } else {
            logger.info("Adding tracing for " + key);
            set = new HashSet<String>();
        }
        Set stringSet = createStringSet(bundle, property);
        if(stringSet == null) logger.info("Could not create trace set for " + property);
        set.addAll(createStringSet(bundle, property));
        keySets.put(key, set);
    }

    private Set<String> createStringSet(ResourceBundle bundle, String property) {
        Set<String> set = null;

        try {
            String[] strings = ResourceUtil.getArray(bundle, property);
            set = new HashSet<String>();

            for (String s : strings) {
                logger.info("Adding: " + s);
                set.add(s);
            }

        } catch (Exception e) {
            if (isTraceOn()) {
                logger.warn("Could not set " + property + " traces.");
            }
            return null;
        }

        logger.info("Traces for " + property);
        for (String s : set) {
            logger.info("\t" + s);
        }

        return set;
    }

    public boolean isTraceOn() {
        return traceOn;
    }

    public void setTrace(boolean traceOn) {
        if (traceOn && !this.traceOn) {
            logger.info("Tracing on.");
        } else if (!traceOn && this.traceOn) {
            logger.info("Tracing off.");
        }

        this.traceOn = traceOn;
    }

    public void traceHousehold(int household) {
        if (households == null) {
            households = new HashSet<Integer>();
        }

        households.add(household);
    }

    /**
     * Add taz pair to trace list.
     * 
     * @param itaz
     * @param jtaz
     */
    public void traceZonePair(int itaz, int jtaz) {
        if (rows == null || columns == null) {
            rows = new ArrayList<Integer>();
            columns = new ArrayList<Integer>();
        }

        rows.add(itaz);
        columns.add(jtaz);
    }

    /**
     * Add a person to the trace list.
     * 
     * @param person
     */
    public void tracePerson(String person) {
        if (persons == null) {
            persons = new HashSet<String>();
        }

        persons.add(person);
    }

    /**
     * Trace calculations for a household.
     * 
     * @param household
     * @return true if household should be traced, otherwise false
     */
    public boolean isTraceHousehold(int household) {
        return isTraceOn() && households != null
                && households.contains(household);

    }

    /**
     * Trace calculations for a person by person ID only.
     * 
     * Use this when each person has a unique number.
     * 
     * @param person Identifier for the person.
     * @return true if person should be traced, false otherwise
     */
    public boolean isTracePerson(String person) {
        return isTraceOn() && persons != null && persons.contains(person);
    }

    /**
     * Trace calculations for a zone pair.
     * 
     * @param itaz
     * @param jtaz
     * @return true if zone pair should be traced, otherwise false
     */
    public boolean isTraceZonePair(int itaz, int jtaz) {
        if (!isTraceOn() || rows == null || !rows.contains(itaz)
                || !columns.contains(jtaz)) {
            return false;
        }

        assert rows.size() == columns.size();

        for (int i = 0; i < rows.size(); ++i) {
            if (rows.get(i) == itaz && columns.get(i) == jtaz) {
                logger.debug("Tracing zone pair " + itaz + ", " + jtaz);
                return true;
            }
        }

        return false;
    }

    /**
     * Trace calculations for a zone.
     * 
     * @param taz
     * @return true if taz should be traced, otherwise false
     */
    public boolean isTraceZone(int taz) {
        return isTraceOn()
                && ((rows != null && rows.contains(taz)) || (columns != null && columns
                        .contains(taz)));
    }

    /**
     * Clear trace household list.
     */
    public void clearTraceHouseholds() {
        if (households != null) {
            households.clear();
        }
    }

    /**
     * Clear trace person list;
     */
    public void clearTracePersons() {
        if (persons != null) {
            persons.clear();
        }
    }

    /**
     * Clear zone pairs.
     */
    public void clearTraceZonePairs() {
        if (rows != null) {
            rows.clear();
            columns.clear();
        }
    }

    public int getTracePersonCount() {
        if (!isTraceOn() || persons == null) {
            return 0;
        }

        return persons.size();
    }

    public int getZonePairCount() {
        if (!isTraceOn() || rows == null) {
            return 0;
        }

        return rows.size();
    }

    public void clearKey(String key) {
        keySets.remove(key);
    }

    public void clearKeySets() {
        for (String key : keySets.keySet()) {
            clearKey(key);
        }
    }

    public boolean isTraceKeyValueOn(String key, int value) {
        return isTraceOn() && isTraceKeyValue(key, Integer.toString(value));
    }

    public boolean isTraceKeyValueOn(String key, String value) {
        return isTraceOn() && isTraceKeyValue(key, value);
    }

    public boolean isTraceKeyValue(String key, String value) {
        return keySets != null && keySets.containsKey(key)
                && keySets.get(key).contains(value);
    }

    public boolean isTraceKeyValue(String key, int value) {
        return keySets != null && keySets.containsKey(key)
                && keySets.get(key).contains(Integer.toString(value));
    }
}