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


public class IndexSort {

	/**
	 * take an array of integer values and return an array of indices to the sorted values
	 * 
	 **/
    public static int[] indexSort (int[] sortData) {
    	
    	int[] index = new int[sortData.length];
    	for (int i=0; i < sortData.length; i++)
    		index[i] = i;
    		
        quickIndexSort (0, sortData.length - 1, sortData, index);
        
        return index;
    }

    private static int[] quickIndexSort (int lo, int hi, int[] sortData, int[] index) {

        int i, j;
        int tmp;

        if (hi > lo) {
            tmp = sortData[index[hi]];
            i = lo - 1;
            j = hi;
            while (true) {
                while (lessThan(sortData[index[++i]], tmp))
                    ;
                while (j > 0) {
                    if (lessThanOrEqual(sortData[index[--j]], tmp))
                        break;
                }
                if (i >= j)
                    break;
                swapIndex (i, j, index);
            }
            swapIndex (i, hi, index);
            quickIndexSort (lo, i-1, sortData, index);
            quickIndexSort (i+1, hi, sortData, index);
        }
        
        return index;
    }

    
    /**
     * non-recursive merge sort algorithm returns an array of indices
     * to the sorted sortData array.
     * 
     */
	public static int[] indexMergeSort( int[] sortData ) { // nonrecursive

		int[] indexIn = new int[sortData.length]; // make a new temporary index array
		for (int i=0; i < sortData.length; i++)
			indexIn[i] = i;

		int[] indexOut = null; // output index array

		int n = indexIn.length;

		
		for (int i=1; i < n; i*=2) { // each iteration sorts all length-2*i runs 

		  for (int j=0; j < n; j+=2*i)  // each iteration merges two length-i pairs
			indexIn = merge( sortData, indexIn, j, i ); // merge from in to out two length-i runs at j

		}

		// the "in" array contains the sorted array, so return it

		return indexIn;

	  }

	
		public static boolean checkAscendingOrder ( int[] sortData, int[] index ) {
		
			int count=0;
			int max = sortData[index[0]];
		    
			for (int i=1; i < sortData.length; i++)
				if ( sortData[index[i]] < max )
					count++;
				else
					max = sortData[index[i]];
		    
			return count == 0;
		}
    
    
	  private static int[] merge( int[] sortData, int[] indexIn, int start, int inc) { // merge in[start..start+inc-1] and in[start+inc..start+2*inc-1]

	      int[] indexOut = new int[indexIn.length];
	      System.arraycopy(indexIn, 0, indexOut, 0, indexIn.length);
	      
	      int x = start; // index into run #1
	      int end1 = Math.min(start+inc, indexIn.length); // boundary for run #1
	      int end2 = Math.min(start+2*inc, indexIn.length); // boundary for run #2
	      int y = start+inc; // index into run #2 (could be beyond array boundary)
	      int z = start; // index into the out array

		
	      while ((x < end1) && (y < end2)) { 

	          if ( lessThanOrEqual(sortData[indexIn[x]], sortData[indexIn[y]]) )
	              indexOut[z++] = indexIn[x++];
	          else
	              indexOut[z++] = indexIn[y++];

	      }

	      if (x < end1) // first run didn't finish
	          System.arraycopy(indexIn, x, indexOut, z, end1 - x);
	      else if (y < end2) // second run didn't finish
	          System.arraycopy(indexIn, y, indexOut, z, end2 - y);

	      return indexOut;
	  } 




    private static void swapIndex (int a, int b, int[] index) {
        int tmp = index[a];
        index[a] = index[b];
        index[b] = tmp;
    }

    private static boolean lessThan (int a, int b) {
        return(a < b);
    }

    private static boolean lessThanOrEqual (int a, int b) {
        return(a <= b);
    }
    
}