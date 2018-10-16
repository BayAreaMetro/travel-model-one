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

public class TimeWrapper {
    private long age;
    private long expireTime;
    private Object object;


    public TimeWrapper(Object object) {
        this.object = object;
        updateAge();
    }


    public TimeWrapper(Object object, long expireTime) {
        this.object = object;
        this.expireTime = expireTime;
        updateAge();
    }


    private void updateAge() {
        age = System.currentTimeMillis();
    }


    public long getAge() {
        return (System.currentTimeMillis() - age);
    }


    public long getExpireTime() {
        return (expireTime);
    }


    public Object getObject() {
        updateAge();
        return (object);
    }
}
