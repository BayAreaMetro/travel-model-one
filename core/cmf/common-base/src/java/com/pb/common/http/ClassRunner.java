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

import org.apache.log4j.*;
import org.apache.log4j.varia.LevelRangeFilter;
import org.apache.log4j.net.SocketAppender;

import java.net.URL;
import java.net.URLClassLoader;

/**
 * classloader URL can be passed on command-line "http://localhost:2001/"
 */
public class ClassRunner {

    protected static Logger logger = Logger.getLogger(ClassRunner.class);

    public String classLoaderURL = null;

    public ClassRunner() {
        this(null);
    }

    public ClassRunner(String classLoaderURL) {
        this.classLoaderURL = classLoaderURL;
        logger.info("classLoaderURL = " + classLoaderURL);
    }

    public void runClass(String className) {

        try {

            Class cls = null;
            if (classLoaderURL != null) {
                cls = loadFromURL(className);
            } else {
                cls = Class.forName(className);
            }

            Object obj = cls.newInstance();
            ((Runnable) obj).run();
        }
        catch (Exception e) {
            logger.error(e);
        }
    }

    private Class loadFromURL(String className) throws Exception {
        URL url = new URL(classLoaderURL);
        URL[] urls = new URL[]{url};

        URLClassLoader cl = new URLClassLoader(urls);
        Class cls = cl.loadClass(className);

        logger.debug(cls.toString());

        return cls;
    }

    public static void main(String[] args) {

        String classLoaderURL = null;

        if (args.length > 1) {
            classLoaderURL = args[0];
        }

        if (classLoaderURL != null) {
            new ClassRunner(classLoaderURL);
        } else {
            new ClassRunner();
        }
    }
}
