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

import java.util.Random;

/**
 * This class will give the user a seeded random number.  By
 * default the random number will be seeded by 2002.
 * 
 * There is a "setSeed() method that can be called if you want
 * to override this seed with a different seed.
 * 
 * 
 * Created 2002 
 * @author Joel Freedman
 */
public class SeededRandom {

    private static Random thisRandom = new Random(2002);


    public static double getRandom() {
        return thisRandom.nextDouble();
    }

    public static float getRandomFloat() {
        return thisRandom.nextFloat();
    }


    public static void setSeed(int seed) {
        thisRandom.setSeed(seed);
    }


    public static void main(String[] args) {
        //no seed is set -the default is used.
        SeededRandom.getRandom();
        double value = SeededRandom.getRandom();
        System.out.println("Random number with default seed: " + value);
        
        //user overides the default seed with their own seed
        //BEFORE calling the getRandom() method.
  //      SeededRandom.setSeed(2003);
        SeededRandom.getRandom();

        value = SeededRandom.getRandom();
        System.out.println("Random number with user-defined seed: " + value);
        System.out.println("random "+value);

    }

}
