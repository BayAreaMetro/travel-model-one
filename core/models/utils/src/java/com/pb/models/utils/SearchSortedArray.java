/*
 * Copyright 2006 PB Consult Inc.
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
 * Created on Mar 22, 2006 by Andrew Stryker <stryker@pbworld.com>
 */
/**
 * 
 */
package com.pb.models.utils;

import com.pb.common.util.SeededRandom;

import java.util.Arrays;
import java.util.Random;


/**
 * The current purpose of this class is to search for
 * the position of a random number (between 0 and 1) in a
 * cumulative probability array (also between 0 and 1)
 * but it could also be used to search any sorted array
 * for a number
 *
 *
 * @author Andrew Stryker, Christi Willison, Ofir Cohen
 * @version 0.2 Apr 12, 2006
 */
public class SearchSortedArray {

    /**
     * Basically a MonteCarlo selection.
     *
     * @param cumulativeProbabilties
     * @return  Will return the position of a random number in the cum. prob array or will
     *          return the insertion point.
     */
    public static int searchForInsertionPoint(float[] cumulativeProbabilties) {
        float rn = SeededRandom.getRandomFloat();
        return binarySearch(cumulativeProbabilties, rn);
    }

    /**
     * Same as above method but takes a double array instead of
     * a float.  Also uses the Arrays.binarySearch algorithm (for
     * no particular reason)
     * The Arrays.binarySearch will return a negative index
     * if the target is not found in the array. Since
     * we are only looking for the index of the number
     * closest to our random number we can do a little
     * math to get back to that index.
     * @param cumulativeProbabilities
     * @return postion in array that contains a value bigger
     *          than our random number.
     */
    public static int searchForInsertionPoint(double[] cumulativeProbabilities) {
        double rn = new Random().nextDouble();
        int searchResult = Arrays.binarySearch(cumulativeProbabilities, rn);

        if(searchResult < 0 ){
            searchResult = -1*(searchResult+1);
        }
        return searchResult;
    }

    /**
     * This method will look for the target in the array.  If
     * it doesn't find the exact number it will return a negative
     * index that is 1 less than the insertion point.
     * (-(insertion point) -1 )
     * @param anySortedArray
     * @param target
     * @return either position of value in the array or a negative
     *         number indicating where the value would have been if
     *         if were in the array.
     */
    public static int search(float[] anySortedArray, float target){
        return Arrays.binarySearch(anySortedArray, target);
    }

    /**
     * This method will look for the target in the array.  If it finds it,
     * it will return that position in the array, otherwise it will return
     * the position where the number would have been inserted.
     * @param anySortedArray
     * @param target
     * @return the position where the target would be inserted
     */
    public static int searchForInsertionPoint(float[] anySortedArray, float target){
        return binarySearch(anySortedArray, target);
    }


    /**
     * Binary search on target.  If value is found
     * it returns that position, otherwise it
     * returns the insertion point.
     *
     * @param array
     * @param target
     * @return index of array
     */

    private static int binarySearch(float[] array, float target) {
        int low = 0;
        int high = array.length - 1;
        while (high > low) {
            int mid = (low + high) / 2;
            if (array[mid] <= target) {
                low = mid + 1;
            } else {
                high = mid;
            }
        }
        return high;
    }
}
