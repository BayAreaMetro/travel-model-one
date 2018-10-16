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

import java.util.ArrayList;
import java.io.Serializable;

import org.apache.log4j.Logger;

import com.pb.common.datafile.TableDataSet;

/**
 *
 * @author    Tim Heier
 * @version   1.0, 5/6/2004
 */

public class LinkCalculator implements VariableTable,  Serializable {

    static Logger logger = Logger.getLogger( LinkCalculator.class );
    
    protected TableDataSet linkTable;
    protected Expression[] expressions = null;

    protected int nLinks;
    protected int nExpressions;
    protected int resultField;
	protected int currentLink;

	protected String functionIndexFieldName = null;
	
	protected double[] linkResults;


	private LinkCalculator() {

	}


	public LinkCalculator(TableDataSet linkTable, ArrayList expStrings, String functionIndexFieldName) {
		this(linkTable, expStrings, functionIndexFieldName, -1);
		
		this.functionIndexFieldName = functionIndexFieldName;
	}


	public LinkCalculator(TableDataSet linkTable, String[] expStrings, String functionIndexFieldName) {
		this(linkTable, expStrings, functionIndexFieldName, -1);

		this.functionIndexFieldName = functionIndexFieldName;
}


	public LinkCalculator(TableDataSet linkTable, ArrayList expStrings, String functionIndexFieldName, int resultField) {
	    this.linkTable = linkTable;
		this.nLinks = linkTable.getRowCount();
	    this.nExpressions = expStrings.size();
		this.resultField = resultField;

		this.expressions = new Expression[nExpressions];
		this.linkResults = new double[nLinks];

		this.functionIndexFieldName = functionIndexFieldName;

		for (int i=0; i < nExpressions; i++) {
			expressions[i] = new Expression((String)expStrings.get(i), this);
		}
	    
	    parse();
	}


	public LinkCalculator(TableDataSet linkTable, String[] expStrings, String functionIndexFieldName, int resultField) {
	    this.linkTable = linkTable;
		this.nLinks = linkTable.getRowCount();
	    this.nExpressions = expStrings.length;
		this.resultField = resultField;

		this.expressions = new Expression[nExpressions];
		this.linkResults = new double[nLinks];
		
		this.functionIndexFieldName = functionIndexFieldName;

		for (int i=0; i < nExpressions; i++) {
		    if ( expStrings[i] == null )
		        expressions[i] = null;
		    else
		        expressions[i] = new Expression(expStrings[i], this);
		}
	    
	    parse();
	}


	protected void parse() {
		for (int i=0; i < nExpressions; i++) {
			if ( expressions[i] != null) {
			    expressions[i].parse();
            }
		}
	}


	// apply the link calculator to all links in the link TableDataSet
	public double[] solve() {
	    
		int functionIndex = 0;
		int nLinks = linkTable.getRowCount();
		
		
		for (int i=0; i < nLinks; i++) {
			currentLink = i+1;  //may want to change this??
			functionIndex = (int)linkTable.getValueAt(currentLink, functionIndexFieldName);
            linkResults[i] = expressions[functionIndex].solve();
		}

		return linkResults;
		
	}
    
    
	// apply the link calculator to all links i in the link TableDataSet for which validLinks[i] is true
	public double[] solve( boolean[] validLinks ) {
	    
		int functionIndex = 0;
		int nLinks = linkTable.getRowCount();
		
		for (int i=0; i < nLinks; i++) {
                        
			if (validLinks[i]) {
				currentLink = i+1;  //may want to change this??
				functionIndex = (int)linkTable.getValueAt(currentLink, functionIndexFieldName);
				try {
				    linkResults[i] = expressions[functionIndex].solve();
				}
				catch ( Exception e ){
                    int[] anodes = linkTable.getColumnAsInt( "anode" );
                    int[] bnodes = linkTable.getColumnAsInt( "bnode" );
				    logger.error ( String.format("exception caught in LinkCalculator.solve() for link i=%d, [%d,%d]", i, anodes[i], bnodes[i] ), e );
				    throw new RuntimeException();
				}
            }
			else {
				linkResults[i] = Double.NaN;
			}
		}

		return linkResults;
		
	}
    
    
	// apply the link calculator to only the one link specified and for the function index specified
	public double solve( int linkIndex, int functionIndex ) {

		currentLink = linkIndex+1;  //may want to change this??
		double result = expressions[functionIndex].solve();
		return result;
		
	}
    
    
    //------------------------ Variable Table Methods ------------------------

	/**
	 * Called to get an index value for a variable
	 */
	public final int getIndexValue(String variableName) {
		int index = linkTable.getColumnPosition(variableName);

		if (index == -1) {
			System.out.println("getIndexValue, name="+variableName+", index="+index+", not found in variable table");
		}

		return index;
	}

	/**
	 * Called to get a value for an indexed variable
	 */
	public final double getValueForIndex(int variableIndex) {
		return linkTable.getValueAt(currentLink, variableIndex);
	}

    /**
     * Called to get an index value for an assignment variable
     */
    public final int getAssignmentIndexValue(String s) {
        throw new UnsupportedOperationException();
    }


	/**
	 * Called to set a value for a given variable name
	 */
	public final void setValue(String variableName, double variableValue) {
		throw new UnsupportedOperationException();
	}

    /**
     * Called to set a value for a given variable index
     */
    public final void setValue(int variableIndex, double variableValue) {
        throw new UnsupportedOperationException();
    }
    
    /**
     * Called to get an index value for a given variable index
     */
    public final double getValueForIndex(int variableIndex, int arrayIndex) {
        throw new UnsupportedOperationException();
    }
    
}
