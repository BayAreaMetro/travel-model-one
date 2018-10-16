/*
 * Created on 8-Sep-2005
 * Copyright  2005 PB Consult Inc, JE Abraham and others.
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

package com.pb.common.matrix;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Hashtable;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

import org.apache.log4j.Logger;

/**
 * @author jabraham
 *
 * This is a Hashtable interface to a zone cross reference.
 * The keys are the alpha zones (smaller zones, larger number of zones)
 * and the values are the beta zones (larger zones, smaller number of zones)
 */
public class HashtableAlphaToBeta extends Hashtable implements AlphaToBetaInterface {
    protected static Logger logger = Logger.getLogger("com.pb.common.matrix");
 
    public HashtableAlphaToBeta() {
        super();
    }

    /* (non-Javadoc)
     * @see com.pb.common.matrix.AlphaToBetaInterface#getAlphaExternals()
     */
    public int[] getAlphaExternals1Based() {
        Integer[] keys = new Integer[this.size()];
        keys = (Integer[]) this.keySet().toArray(keys);
        int[] keysInts= new int[keys.length+1];
        keysInts[0] =0;
        for (int k=1;k<keysInts.length;k++) {
            keysInts[k] = keys[k-1].intValue();
        }
        return keysInts;
    }

    /* (non-Javadoc)
     * @see com.pb.common.matrix.AlphaToBetaInterface#getAlphaExternals()
     */
    public int[] getAlphaExternals0Based() {
        Integer[] keys = new Integer[this.size()];
        keys = (Integer[]) this.keySet().toArray(keys);
        int[] keysInts= new int[keys.length];
        for (int k=0;k<keysInts.length;k++) {
            keysInts[k] = keys[k].intValue();
        }
        return keysInts;
    }
    /* (non-Javadoc)
     * @see com.pb.common.matrix.AlphaToBetaInterface#getBetaExternals()
     */
    public int[] getBetaExternals1Based() {
        TreeSet betaValueSet = new TreeSet();
        Collection betaValues = this.values();
        betaValueSet.addAll(betaValues); // Set takes care of duplicate elements for us.
        int[] betas = new int[betaValueSet.size()+1];
        betas[0] = 0;
        Iterator betaIt = betaValueSet.iterator();
        int b=1;
        while (betaIt.hasNext()) {
            betas[b] = ((Integer) betaIt.next()).intValue();
            b++;
        }
        return betas;
    }

    /* (non-Javadoc)
     * @see com.pb.common.matrix.AlphaToBetaInterface#getBetaExternals()
     */
    public int[] getBetaExternals0Based() {
        TreeSet betaValueSet = new TreeSet();
        Collection betaValues = this.values();
        betaValueSet.addAll(betaValues); // Set takes care of duplicate elements for us.
        int[] betas = new int[betaValueSet.size()];
        Iterator betaIt = betaValueSet.iterator();
        int b=0;
        while (betaIt.hasNext()) {
            betas[b] = ((Integer) betaIt.next()).intValue();
            b++;
        }
        return betas;
    }

    /* (non-Javadoc)
     * @see com.pb.common.matrix.AlphaToBetaInterface#getBetaZone(int)
     */
    public int getBetaZone(int alphaZone) {
        Integer alphaInteger = new Integer(alphaZone);
        Integer betaInteger = (Integer) this.get(alphaInteger);
        if (betaInteger == null) {
        	logger.error("Invalid alpha zone number "+alphaZone+"; no corresponding beta zone");
            throw new RuntimeException("Invalid alpha zone number "+alphaZone+"; no corresponding beta zone");
            // could also return 0, which would be consistent with the way AlphaToBeta works
        }
        return betaInteger.intValue();
    }

    /* (non-Javadoc)
     * @see com.pb.common.matrix.AlphaToBetaInterface#setAlphaToBetaArray(int[], int[])
     */
    public void setAlphaToBetaArray(
        int[] alphaZoneColumn0Based,
        int[] betaZoneColumn0Based) {
        
        for (int i=0;i<alphaZoneColumn0Based.length;i++) {
            Integer alphaInteger = new Integer(alphaZoneColumn0Based[i]);
            Integer betaInteger = new Integer(betaZoneColumn0Based[i]);
            put(alphaInteger,betaInteger);
        }

        
    }

    public int[] getAlphasForBetas(int betaZone) {
        // ENHANCEMENT this isn't very efficient, maybe fix it up 
        Set entrySet = this.entrySet();
        ArrayList<Integer> alphas = new ArrayList<Integer>();
        for (Object e : entrySet) {
            Map.Entry entry = (Map.Entry) e;
            int beta = ((Integer) entry.getValue()).intValue();
            if (beta == betaZone) {
                alphas.add((Integer) entry.getKey());
            }
        }
        int[] alphasArray = new int[alphas.size()];
        for (int i=0;i<alphas.size();i++) {
            alphasArray[i] = alphas.get(i).intValue();
        }
        return alphasArray;
    }
    
    
}
