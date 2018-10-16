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

import java.io.ByteArrayOutputStream;
import java.io.ObjectOutputStream;
import java.io.ObjectInputStream;
import java.io.ByteArrayInputStream;

/**
 * Provides conversion functions for strings, byte arrays, and objects.
 * All methods in the class catch checked exceptions and re-throw them as
 * RuntimeExceptions with the original exception nested.
 *
 * @author   Tim Heier
 * @version  1.0, 8/25/2005
 */
public class Convert {

    /**
     * Converts an object to a byte array using the ObjectOutputStream class.
     *
     * @param object to be converted to byte array
     * @return the byte array representing the serialized object
     */
    public static byte[] toBytes(Object object) {
        return Convert.toBytes(object, 2048);
    }

    /**
     * Converts an object to a byte array using the ObjectOutputStream class.
     *
     * @param object to be converted to byte array
     * @param initialBufferSize buffer size for byte array outputstream
     * @return the byte array representing the serialized object
     */
    public static byte[] toBytes(Object object, int initialBufferSize) {

        byte[] buffer = null;

        try {
            //Serialize object to a byte array
            ByteArrayOutputStream bos = new ByteArrayOutputStream(initialBufferSize);
            ObjectOutputStream out = new ObjectOutputStream(bos);
            out.writeObject(object);
            out.close();

            //Get the bytes for the serialized object
            return bos.toByteArray();
        }
        catch (Exception e) {
            throw new RuntimeException(e);
        }

    }

    /**
     * Converts a byte array into an object using the ObjectInputStream class.
     * An explicit cast is required to cast the returned object to the
     * required type.
     *
     * @param byteArray array of bytes to be converted to an object
     * @return the object represented by the byte array
     */
    public static Object toObject(byte[] byteArray) {
        Object object = null;

        try {
            //Create object from the supplied byte array
            ObjectInputStream in = new ObjectInputStream(new ByteArrayInputStream(byteArray));
            object = in.readObject();
            in.close();
        }
        catch (Exception e) {
            throw new RuntimeException(e);
        }
        return object;
    }

    /**
     * Converts a base64 encoded string to an object. An explicit cast
     * is required to cast the returned object to the required type.
     *
     * @param string the base64 encoded string representing an object
     * @return the base64 encoded string as an object
     */
    public static Object toObject(String string) {
        Object object = null;

        try {
            //Convert the base64 encoded string to a byte array
            byte[] buf = new sun.misc.BASE64Decoder().decodeBuffer(string);

            //Deserialize the object from the byte array
            ObjectInputStream in = new ObjectInputStream(new ByteArrayInputStream(buf));
            object = in.readObject();
            in.close();
        }
        catch (Exception e) {
            throw new RuntimeException(e);
        }
        return object;
    }

    /**
     * Converts an object to a base64 string.
     *
     * @param object the object to be converted to a base64 encoded string
     * @return  base64 encoded string representing the object
     */
    public static String toString(Object object) {
        String string = null;

        try {
            //Serialize object to a byte array
            ByteArrayOutputStream bos = new ByteArrayOutputStream() ;
            ObjectOutputStream out = new ObjectOutputStream(bos) ;
            out.writeObject(object);
            out.close();

            //Get the bytes of the serialized object
            byte[] buf = bos.toByteArray();

            //Convert byte array to base64 encoded string
            string = new sun.misc.BASE64Encoder().encode(buf);
        }
        catch (Exception e) {
            throw new RuntimeException(e);
        }
        return string;
    }
}
