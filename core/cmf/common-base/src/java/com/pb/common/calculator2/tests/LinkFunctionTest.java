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
package com.pb.common.calculator2.tests;

/**
 *
 * @author    Jim Hicks
 * @version   1.0, 5/7/2004
 */


import com.pb.common.calculator.LinkCalculator;
import com.pb.common.calculator.LinkFunction;
import com.pb.common.datafile.TableDataSet;
import java.util.ArrayList;
import org.apache.log4j.Logger;



public class LinkFunctionTest {

	protected static Logger logger = Logger.getLogger("com.pb.common.calculator.tests");

	
	static TableDataSet linkTable = new TableDataSet();
    
    
	public LinkFunctionTest() {
	}
    
	
    private void setLinkTable () {
        
        ArrayList tableHeadings = new ArrayList();
        tableHeadings.add( "length" );
        tableHeadings.add( "ul1" );
        tableHeadings.add( "volau" );
        tableHeadings.add( "ul2" );
        tableHeadings.add( "lanes" );
        tableHeadings.add( "vdf" );
    	tableHeadings.add( "time" );
    	
        
		float[][] linkValues = { { 2.1f, 45.0f, 1100, 1200, 2, 1, 0 },
								 { 1.4f, 35.0f,  900,  800, 1, 2, 0 },
								 { 1.8f, 25.0f,  400,  450, 2, 3, 0 },
								 { 0.1f, 30.0f,  700,  800, 1, 1, 0 },
								 { 3.4f, 55.0f, 3500, 1400, 4, 2, 0 },
								 { 0.4f, 45.0f,  800,  800, 3, 3, 0 },
								 { 2.5f, 20.0f,  900,  800, 1, 1, 0 },
								 { 1.1f, 15.0f,  400,  800, 1, 2, 0 },
								 { 2.4f, 45.0f,  600,  800, 2, 3, 0 },
								 { 1.9f, 25.0f,  700,  300, 1, 1, 0 } };
        
        
		linkTable = TableDataSet.create ( linkValues, tableHeadings );
        
    }
    
    
    public static void main (String[] args) {
        
        LinkFunctionTest lft = new LinkFunctionTest();
		lft.setLinkTable();

        LinkFunction lf = new LinkFunction ( "c:\\jim\\tlumip\\WoodburnData\\functions.batchout", "vdf");
        
        LinkCalculator lc = new LinkCalculator ( linkTable, lf.getFunctionStrings("fd"), lf.getIndexField() );
     
        double[] results = lc.solve();
        
		logger.info ( "link calculator test results");
        for (int i=0; i < results.length; i++)
            logger.info ( "results[" + i + "] = " + results[i] );

        
/*      
 * these results were produced by this test for network defined above.
 *  
		INFO, link calculator test results
		INFO, results[0] = 2.800057144856745
		INFO, results[1] = 3.9587140248083377
		INFO, results[2] = 4.319999885559082
		INFO, results[3] = 0.20263075878107184
		INFO, results[4] = 3.7158378103777747
		INFO, results[5] = 0.5333333412806193
		INFO, results[6] = 8.717745384550653
		INFO, results[7] = 4.400859470386059
		INFO, results[8] = 3.2000001271565757
		INFO, results[9] = 1095.253423435673
*/
        
    }

}
