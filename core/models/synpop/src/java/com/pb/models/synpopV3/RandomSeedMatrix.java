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
 */
package com.pb.models.synpopV3;

import java.util.Random;

import org.apache.log4j.Logger;

/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Wu Sun
 * @version 1.0, Jan. 9, 2004
 */

public class RandomSeedMatrix {
    protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
  protected static int NTAZ;
  protected static int NHHCat;
  //randome seed matrix, 1st dimension number of HHCat, 2nd dimension number of TAZ
  protected static long [][] matrix;
  protected static long seed;

  static {
    NTAZ=PopulationSynthesizer.numberOfInternalZones;
    NHHCat=HHCatTable.NHHCat;
    matrix=new long [NHHCat][NTAZ];
    seed=(new Long(PropertyParser.getPropertyByName("RandomSeed"))).longValue();
    logger.info("Random seed set to: " + seed);
    setSeedMatrix();
  }

  /**
   * Get random seed matrix.  First dimension TAZ, second dimension HHCat.
   * @return
   */
  public static long [][] getSeedMatrix(){
    return matrix;
  }

  /**
   * Get a random seed from one cell in the random matrix.
   * @param TAZ represents the internal TAZ ID (starts from 0).
   * @param HHCat represents the internal HHCat ID (starts from 0).
   * @return
   */
  public static long getSeed(int HHCat, int TAZ){
    return matrix[HHCat][TAZ];
  }

  /**
   * Populate random seed matrix.
   */
  private static void setSeedMatrix(){
    Random generator=new Random(seed);
    for(int i=0; i<NHHCat; i++){
      for(int j=0; j<NTAZ; j++){
        matrix[i][j]=generator.nextLong();
      }
    }
  }
}