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

import java.util.NoSuchElementException;

/**
 * A First-in First-out queue. This is a non-blocking queue. Also, the methods
 * on this class are not synchronized. This means this class is not thread-safe.
 * The containing class must ensure thread-safety. 
 * 
 * @author Tim Heier
 * @version 1.0, 5/14/2000
 */
public class FIFOQueue {

    private Object[] queue;
    private int capacity;
    private int size;
    private int head;
    private int tail;

    
    public FIFOQueue(int cap) {
        capacity = (cap > 0) ? cap : 1; // at least 1
        queue = new Object[capacity];
        head = 0;
        tail = 0;
        size = 0;
    }

    
    public int getCapacity() {
        return capacity;
    }

    
    public int getSize() {
        return size;
    }

    
    public boolean isEmpty() {
        return (size == 0);
    }

    
    public boolean isFull() {
        return (size == capacity);
    }

    
    public void add(Object obj) {
        queue[head] = obj;
        head = (head + 1) % capacity;
        size++;
    }

    
    public void addEach(Object[] list) {
        for (int i = 0; i < list.length; i++) {
            add(list[i]);
        }
    }

    
    public Object remove() throws NoSuchElementException {
        if (isEmpty()) {
            throw new NoSuchElementException("queue is empty");
        }
        
        Object obj = queue[tail];

        // don't block GC by keeping unnecessary reference
        queue[tail] = null;

        tail = (tail + 1) % capacity;
        size--;

        return obj;
    }

    
    public Object[] removeAll() throws NoSuchElementException {
        Object[] list = new Object[size]; // use the current size

        for (int i = 0; i < list.length; i++) {
            list[i] = remove();
        }

        // if FIFO was empty, a zero-length array is returned
        return list;
    }

}
