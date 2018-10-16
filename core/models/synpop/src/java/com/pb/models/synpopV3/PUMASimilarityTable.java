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
/*
 * Created on Apr 1, 2005
 * This class represents PUMA similarity table.
 */
package com.pb.models.synpopV3;

import org.apache.log4j.Logger;

import com.pb.common.datafile.TableDataSet;

/**
 * @author Wu Sun
 * <sunw@pbworld.com>
 *
 */
public class PUMASimilarityTable {
	
	protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
	protected TableDataSet table;
	
	public PUMASimilarityTable(TableDataReader designTableReader){
		table=designTableReader.getTable("PUMASimilarityTable.csv");
	}
	
    /**
     * Given a PUMA get its similar PUMA of a given rank.
     * @param puma represents the given PUMA.
     * @param rank represents the desired rank of the similar PUMA. If rank=1, similar PUMA is PUMA itself.
     * @return
     */
    public int getSimilarPUMA(int puma, int rank) {
        //Initialize similar PUMA as PUMA itself.
        //If a similar PUMA of a desired rank is not found, then return PUMA itself as its similar PUMA.
        int result = puma;

        int NRows=table.getRowCount();
        int[] currentPUMA=table.getColumnAsInt("PUMA_1");
        int[] similarPUMA=table.getColumnAsInt("PUMA_2");
        int[] ranks=table.getColumnAsInt("SIMILARRAN");

        //find the similar PUMA
        for (int i = 0; i < NRows; i++) {
            if ((puma == currentPUMA[i]) && (rank == ranks[i])) {
                result = similarPUMA[i];
                break;
            }
        }
 
        return result;
    }
    
    public static void main(String [] args){
    	TableDataReader designReader=new TableDataReader("design");
    	PUMASimilarityTable table=new PUMASimilarityTable(designReader);
    	logger.info("ok, I am done.");
    }

}
