/*
 * Created on 8-Sep-2005
 *
 *  Copyright  2005 PB Consult Inc.
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

/**
 * @author jabraham
 */

public interface AlphaToBetaInterface {
    /**
     * Get the alphaZone external array
     * @return alphaExternals - the alphaZone externalNumber array
     */
    public abstract int[] getAlphaExternals1Based();
    /**
     * Get the alphaZone external array
     * @return alphaExternals - the alphaZone externalNumber array
     */
    public abstract int[] getAlphaExternals0Based();
    /**
     * Get the betaZone external array
     * @return betaExternals - the betaZone externalNumber array
     */
    public abstract int[] getBetaExternals1Based();
    /**
     * Get the betaZone external array 0 based
     * @return betaExternals - the betaZone externalNumber array 0 based
     */
    public abstract int[] getBetaExternals0Based();
    /**
     * Get the betaZone that contains the alphaZone
     * @param alphaZone
     * @return betaZone
     */
    public abstract int getBetaZone(int alphaZone);
    
    /**
     * Return all the alphazones the correspond to one betazone
     * @param betaZone the betazone to get the alphazones for
     * @return the alphazones
     */
    public abstract int[] getAlphasForBetas(int betaZone);
    /**
     * sets the values of alphaToBeta[aZone] = bZone
     * where aZone is an alphaZone, and bZone is the betaZone that contains the corresponding alphaZone
     * @param alphaZoneColumn - array of
     *
     */
    public abstract void setAlphaToBetaArray(
        int[] alphaZoneColumn0Based,
        int[] betaZoneColumn0Based);
}