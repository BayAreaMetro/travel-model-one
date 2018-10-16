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

import java.net.URLClassLoader;
import java.net.URL;
import java.net.MalformedURLException;

public class ClassFileServerTest {

    public static void main(String[] args) {

        URL url = null;
        try {
            url = new URL("http://localhost:2001/");
        } catch (MalformedURLException e) {
            e.printStackTrace();
        }
        URL[] urls = new URL[] { url };

        URLClassLoader cl = new URLClassLoader(urls);
        Class cls = null;
        try {
            cls = cl.loadClass("com.pb.common.http.TestClass");
            System.out.println(cls.getClassLoader().toString());
        } catch (ClassNotFoundException e) {
            e.printStackTrace();
        }

        Object obj;
        try {
            obj = cls.newInstance();
            ((Runnable)obj).run();
        } catch (InstantiationException e) {
            e.printStackTrace();
        } catch (IllegalAccessException e) {
            e.printStackTrace();
        }

    }
}
