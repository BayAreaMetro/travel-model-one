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
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.ObjectInput;
import java.io.ObjectOutput;
import java.io.ObjectOutputStream;
import java.io.PrintWriter;
import java.io.Serializable;

/**
 * Provides utility operations that operate on objects.
 *
 * @author Tim Heier
 * @version 1.0, 6/21/2002
 */
public class ObjectUtil {

    /**
     * Returns the size of an object. The object is serialized to a file and
     * the size of the file is returned. This allows the size of any object
     * to be determined. i.e. This method does not consume any heap.
     */
    public static long sizeOf(Object obj) {

        long objSize = 0;

        try {
            /* Works but uses memory equal to size of object!
            ByteArrayOutputStream bos = new ByteArrayOutputStream( 256*1024 );
            ObjectOutputStream out = new ObjectOutputStream( bos );
            out.writeObject( obj );
            out.flush();
            out.close();
            objSize = bos.size();
            */

            File file = File.createTempFile("obj", "tmp");

            FileOutputStream fos = new FileOutputStream(file);
            ObjectOutputStream out = new ObjectOutputStream(fos);
            out.writeObject(obj);
            out.flush();
            out.close();
            fos.close();

            objSize = file.length();

            file.delete();
        }
        catch (Exception e) {
            e.printStackTrace();
        }

        return objSize;
    }

    /**
     * Returns the size of an object.
     * Works but uses memory equal to size of object!
     * sizeOf method above takes longer because that
     * method writes the object to disk.
     * @return the size of an object.
     */
    public static int checkObjectSize(Serializable obj) throws IOException {
        int objSize;

        ByteArrayOutputStream bos = new ByteArrayOutputStream( 256*1024 );
        ObjectOutputStream out = new ObjectOutputStream( bos );
        out.writeObject( obj );
        out.flush();
        out.close();
        objSize = bos.size();

        return objSize;
    }


    /**
     * Helper method used by objects implementing the Externalizable interface.
     * 
     * @param out
     * @param array
     * @throws IOException
     */
    public static void writeShortArray(ObjectOutput out, short[] array) throws IOException {
        if (array == null) {
            out.writeInt(-1);
        }
        else {
            out.writeInt(array.length);
            for (int i=0; i < array.length; i++) {
                out.writeShort(array[i]);
            }
        }
    }

    /**
     * Helper method used by objects implementing the Externalizable interface.
     * 
     * @param out
     * @param array
     * @throws IOException
     */
    public static void writeBooleanArray(ObjectOutput out, boolean[] array) throws IOException {
        if (array == null) {
            out.writeInt(-1);
        }
        else {
            out.writeInt(array.length);
            for (int i=0; i < array.length; i++) {
                out.writeBoolean(array[i]);
            }
        }
    }

    /**
     * Helper method used by objects implementing the Externalizable interface.
     * 
     * @param out
     * @param array
     * @throws IOException
     */
    public static void writeObjectArray(ObjectOutput out, Object[] array) throws IOException {
        if (array == null) {
            out.writeInt(-1);
        }
        else {
            out.writeInt(array.length);
            for (int i=0; i < array.length; i++) {
                out.writeObject(array[i]);
            }
        }
    }

    /**
     * Helper method used by objects implementing the Externalizable interface.
     * 
     * @param in
     * @throws IOException
     */
    public static boolean[] readBooleanArray(ObjectInput in) throws IOException {
        int length = in.readInt();
        if (length == -1) {
            return null;
        }

        boolean[] boolArray = new boolean[length];
        for (int i=0; i < length; i++) {
            boolArray[i] = in.readBoolean();
        }

        return boolArray;
    }

    /**
     * Helper method used by objects implementing the Externalizable interface.
     * 
     * @param in
     * @throws IOException
     */
    public static short[] readShortArray(ObjectInput in) throws IOException {
        int length = in.readInt();
        if (length == -1) {
            return null;
        }

        short[] shortArray = new short[length];
        for (int i=0; i < length; i++) {
            shortArray[i] = in.readShort();
        }

        return shortArray;
    }

    public static void printArray(String[] labels, int[] values, int minimumValue, PrintWriter file) throws
        IOException{

        if(labels.length != values.length){
            System.out.println("PrintArray error: label array size not equal to values array size");
            System.exit(1);
        }

        for(int i=0;i<values.length;++i)
            if(values[i]>=minimumValue)
                file.println(i + ":"+labels[i] + "    " +values[i]);
    }

    /**
     * For testing the sizeOf method.
     *
     * @param args from system
     */
    public static void main(String[] args) {

        int[] array = new int[1000];

        //Find the size of the array in memory
        long size = ObjectUtil.sizeOf(array);

        System.out.print("size of array = " + size + " bytes");
    }
}
