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

/**
 * Maintains a pool of compressed messages. This pool starts at a user
 * supplied size and can grow as objects are removed from the pool.
 *
 * @author    Tim Heier
 * @version   1.0, 6/20/2002
 */
public class UncompressedMessagePool {

    private UncompressedMessage[] objects;
    private int head;

    public UncompressedMessagePool(int size) {
        if (size <= 0)
            size = 1;

        head = 0;
        objects = new UncompressedMessage[size];
    }


    public int sizeOfPool() {
        return objects.length;
    }


    public UncompressedMessage getMessage() {
        UncompressedMessage msg = null;

        synchronized( this ) {

            //If there is an available object in the pool, return it.
            //Else, create a new object and return it.
            if (head > 0) {
                head--;
                msg = objects[head];
                objects[head] = null;
            }
            else {
                msg = new UncompressedMessage("new_from_pool");
            }
        }
        return msg;
    }

    public void returnMessage(UncompressedMessage msg) {
        synchronized( this ) {

            //If the size of the pool is large enough to fit the returned
            //object, then add it. Else, increase the size of the pool
            //then add the object.
            if (objects.length > head) {
                expandPool();
                objects[head] = msg;
                head++;
            }
        }
    }

    private synchronized void expandPool() {

        UncompressedMessage[] newObjectPool;

        //Allocate a new array of objects
        newObjectPool = new UncompressedMessage[objects.length * 2];

        //Copy objects from original pool to the new array
        System.arraycopy(objects, 0, newObjectPool, 0, objects.length);

        objects = newObjectPool;
    }

}
