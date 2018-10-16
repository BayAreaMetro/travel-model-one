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
package com.pb.common.datafile.tests;

import java.io.IOException;

import com.pb.common.datafile.DiskObjectArray;
import com.pb.common.util.ObjectUtil;

/**
 *
 * @author    Tim Heier
 * @version   1.0, 8/13/2003
 *
 */

public class DiskObjectArrayTest {

    public static final int ARRAY_SIZE = 500000;
    public static final int DATA_SIZE = 1000;


	public static void main(String[] args) {

		DiskObjectArrayTest test = new DiskObjectArrayTest();
		test.testCreate();
		test.testAddElements();
        test.testFillArray();
        test.testUpdateArray();
        test.testAddLargeElement();
	}


	public void testCreate() {
		
		//Create a large object array
		DiskObjectArray ba = null;
        try {
            ba = new DiskObjectArray("test.array", ARRAY_SIZE, DATA_SIZE);
        }
        catch (IOException e) {
            e.printStackTrace();
        }

		System.out.println("testCreate() done. sizeOf DiskObjectArray = " + ObjectUtil.sizeOf(ba) + " bytes");

		ba.close();
	}


	public void testAddElements() {
		
		//Create a large object array
		DiskObjectArray ba = null;
        try {
            ba = new DiskObjectArray("test.array");
        }
        catch (IOException e) {
            e.printStackTrace();
        }

		//----- Add elements to array

		ba.add( 1, new Integer(1) );
		ba.add( 1, new Integer(2) );  //try adding to same location

		int[] intArray = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9 };
		ba.add( 2, intArray);

		ba.add( 1000, new Integer(1000) );

		//----- Read elements from array
		
		System.out.println("element 1 = " + ba.get( 1 ));

		intArray = (int[]) ba.get( 2 );
		for (int i=0; i < 10; i++) {
			System.out.println("element 2["+i+"]" + " = " + intArray[i]);
		}

		System.out.println("element 1000 = " + ba.get( 1000 ));

		System.out.println("testAddElements() done. sizeOf DiskObjectArray = " + ObjectUtil.sizeOf(ba) + " bytes");

		ba.close();
	}


	public void testFillArray() {
		
        long startTime=System.currentTimeMillis(), endTime;

		//Create a large object array
		DiskObjectArray ba = null;
		try {
			ba = new DiskObjectArray("test.array");
		}
		catch (IOException e) {
			e.printStackTrace();
		}

		//----- Add a small object to each location in array
        for (int i=0; i < ARRAY_SIZE; i++) {
        //for (int i=0; i < 5000; i++) {
            if ((i % 500) == 0) {
                endTime = System.currentTimeMillis();
                System.out.println("adding="+ i + ", time="+(endTime-startTime));
                startTime = System.currentTimeMillis();
            }
			ba.add( i, new Integer(i));
		}

		System.out.println("testFillArray() done. sizeOf DiskObjectArray = " + ObjectUtil.sizeOf(ba) + " bytes");

		//Close it
		ba.close();
	}


    public void testUpdateArray() {

        long startTime=System.currentTimeMillis(), endTime;

        //Create a large object array
        DiskObjectArray ba = null;
        try {
            ba = new DiskObjectArray("test.array");
        }
        catch (IOException e) {
            e.printStackTrace();
        }

        //Update an element in the middle of the array
        int[] intArray = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19 };
        ba.add( 250000, intArray);

        intArray = (int[]) ba.get( 250000 );

        System.out.println("element 250000[5]" + " = " + intArray[5]);

        System.out.println("testUpdateArray() done.");

        //Close it
        ba.close();
    }


    public void testAddLargeElement() {

        //Create a large object array
        DiskObjectArray ba = null;
        try {
            ba = new DiskObjectArray("test.array");
        }
        catch (IOException e) {
            e.printStackTrace();
        }

        //----- Add elements to array

        ba.add( 1, new Integer(1) );
        ba.add( 2, new Integer(2) );
        ba.add( 3, new Integer(3) );

        int[] intArray = new int[210];
        System.out.println("size of new element 2 = " + ObjectUtil.sizeOf(intArray));

        ba.add( 2, intArray);

        System.out.println("Trying to read element 3...");
        System.out.println("element 3 = " + ba.get( 3 ));

        System.out.println("testAddLargeElement() done.");

        ba.close();
    }


}
