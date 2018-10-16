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
package com.pb.common.datafile;

import java.io.File;
import java.io.FileReader;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.Serializable;
import java.util.StringTokenizer;
import java.util.ArrayList;
import org.apache.log4j.Logger;


/**
 * Reads a standard Emme/2 d211 text format file containing node and link records
 * for a transportation network.
 *
 * @author   Jim Hicks
 * @version  1.0, 5/12/2004
 *
 */
public class D211FileReader implements Serializable {

    protected static transient Logger logger = Logger.getLogger("com.pb.common.datafile");

    
    
    public D211FileReader () {
    }

    

	public TableDataSet readNodeTable (File file) throws IOException {

		int record = 0;
		boolean found_t_nodes_init = false;
		boolean found_t_links_init = false;

		ArrayList nList = new ArrayList();
		ArrayList xList = new ArrayList();
		ArrayList yList = new ArrayList();
		
		float[][] dataTable = null;
		
		TableDataSet table = null;

		
		
		try {
			logger.debug( "Opening d211 file to read node records: " + file.getName() );

			//Open the file
			BufferedReader in = new BufferedReader(new FileReader(file));
			
			String s = new String();
			while ((s = in.readLine()) != null) {

				record++;

				if ( s.indexOf("t nodes") >= 0 ) {

					found_t_nodes_init = true;

				}
				else if ( s.indexOf("t links") >= 0 ) {

					found_t_links_init = true;

				}
				else if (found_t_nodes_init && !found_t_links_init) {

					parseNode(s, nList, xList, yList);

				}

			}

		}
		catch (Exception e) {
			System.out.println ("IO Exception caught reading node table data from d211 format file: " + file.getName() + ", record number=" + record );
			e.printStackTrace();
		}

			
			
		dataTable = new float[nList.size()][3];
		for (int i=0; i < nList.size(); i++) {
			dataTable[i][0] = Integer.parseInt ( (String)nList.get(i) );
			dataTable[i][1] = Float.parseFloat ( (String)xList.get(i) );
			dataTable[i][2] = Float.parseFloat ( (String)yList.get(i) );
		}
    	
    	
		ArrayList tableHeadings = new ArrayList();
		tableHeadings.add ("node");
		tableHeadings.add ("x");
		tableHeadings.add ("y");
    	
		
		table = TableDataSet.create( dataTable, tableHeadings );

		return table;
        
	}
    


	public TableDataSet readLinkTable (File file) throws IOException {
		return readLinkTable ( file, 'a' );
	}
	
	    
	public TableDataSet readLinkTableMods (File file) throws IOException {
		return readLinkTable ( file, 'm' );
	}
	
	    
	private TableDataSet readLinkTable (File file, char action) throws IOException {

		int record = 0;
		boolean found_t_links_init = false;

		ArrayList anList = new ArrayList();
		ArrayList bnList = new ArrayList();
		ArrayList distList = new ArrayList();
		ArrayList modeList = new ArrayList();
		ArrayList typeList = new ArrayList();
		ArrayList lanesList = new ArrayList();
		ArrayList vdfList = new ArrayList();
		ArrayList ul1List = new ArrayList();
		ArrayList ul2List = new ArrayList();
		ArrayList ul3List = new ArrayList();
		
		float[][] dataTable = null;
		String[] stringColumn = null;
		
		TableDataSet table = null;

		
		
		try {
			logger.debug( "Opening d211 file to read link records: " + file.getName() );

			//Open the file
			BufferedReader in = new BufferedReader(new FileReader(file));
			
			String s = new String();
			while ((s = in.readLine()) != null) {

				record++;

				if ( s.indexOf("t links") >= 0 ) {

					found_t_links_init = true;

				}
				else if (found_t_links_init) {

					parseLink( s, action, anList, bnList, distList, modeList, typeList, lanesList, vdfList, ul1List, ul2List, ul3List );

				}

			}

		}
		catch (Exception e) {
			System.out.println ("IO Exception caught reading link table data from d211 format file: " + file.getName() + ", record number=" + record );
			e.printStackTrace();
		}

			
			
		dataTable = new float[anList.size()][9];
		stringColumn = new String[anList.size()];
		for (int i=0; i < anList.size(); i++) {
			dataTable[i][0] = Integer.parseInt ( (String)anList.get(i) );
			dataTable[i][1] = Integer.parseInt ( (String)bnList.get(i) );
			dataTable[i][2] = Float.parseFloat ( (String)distList.get(i) );
			stringColumn[i] = (String)modeList.get(i);
			dataTable[i][3] = Integer.parseInt ( (String)typeList.get(i) );
			dataTable[i][4] = Float.parseFloat ( (String)lanesList.get(i) );
			dataTable[i][5] = Integer.parseInt ( (String)vdfList.get(i) );
			
			try {
				dataTable[i][6] = Float.parseFloat ( (String)ul1List.get(i) );
			}
			catch (Exception e) {
				dataTable[i][6] = 0.0f;
			}
			try {
				dataTable[i][7] = Float.parseFloat ( (String)ul2List.get(i) );
			}
			catch (Exception e) {
				dataTable[i][7] = 0.0f;
			}
			try {
				dataTable[i][8] = Float.parseFloat ( (String)ul3List.get(i) );
			}
			catch (Exception e) {
				dataTable[i][8] = 0.0f;
			}
		}
    	
    	
		ArrayList tableHeadings = new ArrayList();
		tableHeadings.add ("anode");
		tableHeadings.add ("bnode");
		tableHeadings.add ("dist");
		tableHeadings.add ("type");
		tableHeadings.add ("lanes");
		tableHeadings.add ("vdf");
		tableHeadings.add ("ul1");
		tableHeadings.add ("ul2");
		tableHeadings.add ("ul3");
		

		table = TableDataSet.create( dataTable, tableHeadings );
		table.appendColumn (stringColumn, "mode");



		return table;
        
	}
    


	void parseNode ( String InputString, ArrayList n, ArrayList x, ArrayList y ) {
	    
	    StringTokenizer st = new StringTokenizer(InputString);
	    
	    if (st.hasMoreTokens()) {
	        
	        if ((st.nextToken()).charAt(0) == 'a') {       // read only add records
	            
	            n.add ( st.nextToken() );
	            x.add ( st.nextToken() );
	            y.add ( st.nextToken() );
	            
	        }
	        
	    }
	    
	}




	void parseLink ( String InputString, char action, ArrayList anList, ArrayList bnList, ArrayList distList, ArrayList modeList, ArrayList typeList, ArrayList lanesList, ArrayList vdfList, ArrayList ul1List, ArrayList ul2List, ArrayList ul3List ) {
	    
		StringTokenizer st = new StringTokenizer(InputString);
		int count = st.countTokens();
	    
		if (st.hasMoreTokens()) {
	        
			if ( (st.nextToken()).charAt(0) == action ) {       // process add or mod records as requested
	            
				anList.add ( st.nextToken() );
				bnList.add ( st.nextToken() );
				distList.add ( st.nextToken() );
				modeList.add ( st.nextToken() );
				typeList.add ( st.nextToken() );
				lanesList.add ( st.nextToken() );
				vdfList.add ( st.nextToken() );
				ul1List.add ( st.nextToken() );
				ul2List.add ( st.nextToken() );
				ul3List.add ( st.nextToken() );
	            
			}
	        
		}
	    
	}

}
