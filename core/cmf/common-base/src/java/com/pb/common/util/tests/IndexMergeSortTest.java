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
package com.pb.common.util.tests;

import com.pb.common.util.IndexSort;


public class IndexMergeSortTest {

	static final int LENGTH = 100000;
	static final int MAX_RANDOM = 100000;
	static final int MAX_PRINT = 10;
    
    public IndexMergeSortTest() {
    }


    private void runTest() {

		int[] sortData = new int[LENGTH];
		for (int i=0; i < sortData.length; i++)
			sortData[i] = (int)(Math.random()*MAX_RANDOM);

		int[] index = IndexSort.indexMergeSort ( sortData );

		System.out.println ( "testing indexMergeSort()" );
		System.out.println ( "" );
		System.out.println ( String.format("%-6s", "index") + String.format("%10s", "original") + String.format("%10s", "sorted") );
	
		for (int i=0; i < MAX_PRINT; i++)
            System.out.println ( String.format("%-6d", i) + String.format("%10d", sortData[i]) + String.format("%10d", sortData[index[i]]));

		System.out.println ( "check on order of entire array returned " + IndexSort.checkAscendingOrder(sortData, index) );
    }


    public static void main(String[] args) {
		IndexMergeSortTest test = new IndexMergeSortTest();

		test.runTest();
    }
}
