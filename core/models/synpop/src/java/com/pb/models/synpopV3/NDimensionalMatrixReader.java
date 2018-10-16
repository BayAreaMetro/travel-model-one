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
 * Created on Dec 3, 2004
 * Use this class to read a NDimensionalMatrix from disk.
 */
package com.pb.models.synpopV3;

import java.io.FileInputStream;
import java.io.ObjectInputStream;
import org.apache.log4j.Logger;
import com.pb.common.matrix.NDimensionalMatrixDouble;

/**
 * @author SunW
 * <sunw@pbworld.com>
 */
public class NDimensionalMatrixReader {
	
	protected FileInputStream in;
	protected ObjectInputStream s;
	protected NDimensionalMatrixDouble matrix;
	protected String fileLocation;
	protected Logger logger = Logger.getLogger("com.pb.models.synpopV3");
	
	public NDimensionalMatrixReader(){
	}
	
	public NDimensionalMatrixDouble read(String fileLocation){
		NDimensionalMatrixDouble result=null;
		try{
			in=new FileInputStream(fileLocation);
			s=new ObjectInputStream(in);
			result=(NDimensionalMatrixDouble)s.readObject();
		}catch(Exception e){
			logger.error("failed reading:"+fileLocation);
			logger.error(e.getMessage());
		}
		return result;
		
	}

}
