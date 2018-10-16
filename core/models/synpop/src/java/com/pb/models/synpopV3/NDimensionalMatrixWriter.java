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
 * Created on Dec 2, 2004
 * 
 * Use this class to write a NDimensionalMatrix to disk
 */
package com.pb.models.synpopV3;

import java.io.FileOutputStream;
import java.io.ObjectOutputStream;
import java.io.IOException;
import org.apache.log4j.Logger;
import com.pb.common.matrix.NDimensionalMatrixDouble;

import com.pb.common.datafile.TableDataSet;
import com.pb.common.datafile.CSVFileWriter;

import java.io.File;

/**
 * @author SunW
 * <sunw@pbworld.com>
 */
public class NDimensionalMatrixWriter {
	
	protected FileOutputStream out;
	protected ObjectOutputStream s;
	protected NDimensionalMatrixDouble matrix;
	protected Logger logger = Logger.getLogger("com.pb.models.synpopV3");
	
	public NDimensionalMatrixWriter(NDimensionalMatrixDouble matrix){
		this.matrix=matrix;
	}
	
	public void write(String fileLocation){
		try{
			out=new FileOutputStream(fileLocation);
			s=new ObjectOutputStream(out);
			s.writeObject(matrix);
			s.flush();
		}catch(IOException e){
			logger.error("failed writing:"+fileLocation);
		}
	}
	
	public void writeCSVFile(String fileLocation){
		int [] shape=matrix.getShape();
		int NoRows=shape[0];
		int NoCols=shape[1];
		float [][] array=new float[NoRows][NoCols];
		int []position=new int[2];
		for(int i=0; i<NoRows; i++){
			for(int j=0; j<NoCols; j++){
				position[0]=i;
				position[1]=j;
				array[i][j]=(float)matrix.getValue(position);
			}
		}
		
		CSVFileWriter writer=new CSVFileWriter();
		File file=new File(fileLocation);
		try{
			writer.writeFile(TableDataSet.create(array),file);
		}catch(IOException e){
			logger.fatal("failed writing:"+fileLocation);
		}
	}
}
