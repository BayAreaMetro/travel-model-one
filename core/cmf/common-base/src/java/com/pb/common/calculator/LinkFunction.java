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
package com.pb.common.calculator;

/**
 *
 * @author    Jim Hicks
 * @version   1.0, 5/7/2004
 */


import java.io.BufferedReader;
import java.io.FileReader;
import java.io.Serializable;
import java.util.ArrayList;
import org.apache.log4j.Logger;


public class LinkFunction implements Serializable {

    protected static Logger logger = Logger.getLogger("com.pb.common.calculator");


	// function strings are read from a link function definition file (e.g. an emme/2 module 4.14 format file for link volume delay function definitions)
	protected String[] fdFunctionStrings;
	protected String[] ftFunctionStrings;
	protected String[] fpFunctionStrings;

	// the indexField is the column label in the linkTable TableDataSet that relates LinkFunction index to links.
	protected String indexField;


	private LinkFunction() {
	    
	}

	public LinkFunction( String fileName, String indexField ) {
		readFunctionDefinitionsFile ( fileName );
		this.indexField = indexField;
	}



	public String getIndexField () {
		return indexField;
	}

	
	
	public String[] getFunctionStrings( String functionPrefix ) {
	    
	    String[] functionStrings = null;
	    
		if ( functionPrefix == "fd" )
		    functionStrings = fdFunctionStrings;
		else if ( functionPrefix == "ft" )
		    functionStrings = ftFunctionStrings;
		else if ( functionPrefix == "fp" )
		    functionStrings = fpFunctionStrings;
		
		return functionStrings;
		
	}

	

	private void readFunctionDefinitionsFile ( String fileName ) {

		// this function reads an emme/2 4.14 format file
		
		ArrayList fdFunctionList = new ArrayList();
		ArrayList fdIndexList = new ArrayList();
		ArrayList ftFunctionList = new ArrayList();
		ArrayList ftIndexList = new ArrayList();
		ArrayList fpFunctionList = new ArrayList();
		ArrayList fpIndexList = new ArrayList();
		int fdIndex = 0;
		int fdMaxIndex = 0;
		int ftIndex = 0;
		int ftMaxIndex = 0;
		int fpIndex = 0;
		int fpMaxIndex = 0;

		try {

			int recCount = 0;
			int startPosition = 0;
			int endPosition = 0;
			String subString;

			BufferedReader in = new BufferedReader(new FileReader(fileName));
			String s = new String();
            
			while ((s = in.readLine()) != null) {

				recCount++;

				if ( s.indexOf("fd") > 0 && s.charAt(0) == 'a' ) {
				
					startPosition = s.indexOf("fd") + 2;
					endPosition = s.indexOf('=', startPosition) - 1;
					subString = s.substring(startPosition, endPosition).trim();
					fdIndex = Integer.parseInt( subString );
					fdIndexList.add ( subString );
					if (fdIndex > fdMaxIndex)
						fdMaxIndex = fdIndex;

					startPosition = s.indexOf("=")+1;
					subString = s.substring(startPosition).trim();
					fdFunctionList.add ( subString );

				}
				else if ( s.indexOf("ft") > 0 && s.charAt(0) == 'a' ) {
				
					startPosition = s.indexOf("ft") + 2;
					endPosition = s.indexOf('=', startPosition) - 1;
					subString = s.substring(startPosition, endPosition).trim();
					ftIndex = Integer.parseInt( subString );
					ftIndexList.add ( subString );
					if (ftIndex > ftMaxIndex)
						ftMaxIndex = ftIndex;

					startPosition = s.indexOf("=")+1;
					subString = s.substring(startPosition).trim();
					ftFunctionList.add ( subString );

				}
				else if ( s.indexOf("fp") > 0 && s.charAt(0) == 'a' ) {
				
					startPosition = s.indexOf("fp") + 2;
					endPosition = s.indexOf('=', startPosition) - 1;
					subString = s.substring(startPosition, endPosition).trim();
					fpIndex = Integer.parseInt( subString );
					fpIndexList.add ( subString );
					if (fpIndex > fpMaxIndex)
						fpMaxIndex = fpIndex;

					startPosition = s.indexOf("=")+1;
					subString = s.substring(startPosition).trim();
					fpFunctionList.add ( subString );

				}
				
			}

		} catch (Exception e) {

		    logger.error ("IO Exception caught reading link function definition file: " + fileName);
			e.printStackTrace();
			
		}

		
		// copy Arraylist of fd function strings to array
		fdFunctionStrings = new String[fdMaxIndex+1];
		for (int i=0; i < fdFunctionList.size(); i++) {
		    fdIndex = Integer.parseInt( (String)fdIndexList.get(i) );
		    fdFunctionStrings[fdIndex] = (String)fdFunctionList.get(i);
		}

		// copy Arraylist of ft function strings to array
		ftFunctionStrings = new String[ftMaxIndex+1];
		for (int i=0; i < ftFunctionList.size(); i++) {
			ftIndex = Integer.parseInt( (String)ftIndexList.get(i) );
			ftFunctionStrings[ftIndex] = (String)ftFunctionList.get(i);
		}

		// copy Arraylist of fp function strings to array
		fpFunctionStrings = new String[fpMaxIndex+1];
		for (int i=0; i < fpFunctionList.size(); i++) {
			fpIndex = Integer.parseInt( (String)fpIndexList.get(i) );
			fpFunctionStrings[fpIndex] = (String)fpFunctionList.get(i);
		}

	}

}
