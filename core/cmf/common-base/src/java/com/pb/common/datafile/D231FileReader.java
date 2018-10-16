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
 * Reads a standard Emme/2 d231 text format file containing turn definitions
 * for a transportation network.
 *
 * @author   Jim Hicks
 * @version  1.0, 5/12/2004
 *
 */
public class D231FileReader implements Serializable {

    protected static transient Logger logger = Logger.getLogger("com.pb.common.datafile");

    
    
    public D231FileReader () {
    }

    

	public float[][] readTurnTable (File file) throws IOException {

		int record = 0;
		boolean found_t_turns_init = false;

		ArrayList values = new ArrayList();
		
		float[][] dataTable = null;

		
		try {
			logger.debug( "Opening d231 file to read turn records: " + file.getName() );

			//Open the file
			BufferedReader in = new BufferedReader(new FileReader(file));
			
			String s = new String();
			while ((s = in.readLine()) != null) {

				record++;

				if ( s.indexOf("t turns") >= 0 ) {

					found_t_turns_init = true;

				}
				else if (found_t_turns_init) {

					values.add ( parseRecord ( s ) );

				}

			}

		}
		catch (Exception e) {
			System.out.println ("IO Exception caught reading node table data from d211 format file: " + file.getName() + ", record number=" + record );
			e.printStackTrace();
		}

			
			
		dataTable = new float[values.size()][((float[])values.get(0)).length];
		for (int i=0; i < values.size(); i++) {
			dataTable[i] = (float[])values.get(i);
		}
    	
    	
		return dataTable;
        
	}

	
	
	private float[] parseRecord ( String InputString ) {
	    
		float[] values = new float[8];
	    
	    StringTokenizer st = new StringTokenizer(InputString);
	

	    int i = 0;
	    
	    if (st.hasMoreTokens()) {
	        
	        if ((st.nextToken()).charAt(0) == 'a') {       // read only add records
	            
				while (st.hasMoreTokens()) {

				    values[i] = Float.parseFloat ( st.nextToken() );
				    i++;
				
				}
	        }
	        
	    }
	    
	    return values;
	    
	}

}
