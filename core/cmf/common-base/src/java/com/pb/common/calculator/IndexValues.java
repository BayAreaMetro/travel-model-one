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

import java.io.Serializable;

public class IndexValues implements Serializable {

    private int originZone = -1;
    private int destZone = -1;
    private int stopZone = -1;
    private int zoneIndex = -1;
    private int hhIndex = -1;

    private boolean debugUec = false;
    private String debugLabel = "";
    private String choiceModelLabel = "";
    private String decisionMakerLabel = "";


    /**
     * This constructor makes things easy but is dangerous because the user must set all values
     * with getter/setter methods.
     */
    public IndexValues () {

    }

    /**
     * Convenience constructor which omits stop index value. Provided for "historical" reasons.
     *
     * @param originZone
     * @param destZone
     * @param zoneIndex
     * @param hhIndex
     */
    public IndexValues(int originZone, int destZone, int zoneIndex, int hhIndex) {
        this(originZone, destZone, -1, zoneIndex, hhIndex);
    }

    public IndexValues(int originZone, int destZone, int stopZone, int zoneIndex, int hhIndex ) {
        this.originZone = originZone;
        this.destZone = destZone;
        this.stopZone = stopZone;
        this.zoneIndex = zoneIndex;
        this.hhIndex = hhIndex;
    }

    public String toString() {
        return "originZone="+originZone+", destZone="+destZone+", stopZone="+stopZone+
                ", zoneIndex="+zoneIndex+", hhIndex="+hhIndex;
    }

    public int getOriginZone() {
        return originZone;
    }

    public void setOriginZone(int originZone) {
        this.originZone = originZone;
    }

    public int getDestZone() {
        return destZone;
    }

    public void setDestZone(int destZone) {
        this.destZone = destZone;
    }

    public int getStopZone() {
        return stopZone;
    }

    public void setStopZone(int stopZone) {
        this.stopZone = stopZone;
    }

    public int getZoneIndex() {
        return zoneIndex;
    }

    public void setZoneIndex(int zoneIndex) {
        this.zoneIndex = zoneIndex;
    }

    public int getHHIndex() {
        return hhIndex;
    }

    public void setHHIndex(int hhIndex) {
        this.hhIndex = hhIndex;
    }

    public void setDebug( boolean debugUec ) {
        this.debugUec = debugUec;
    }

    public boolean getDebug() {
        return debugUec;
    }

    public void setDebugLabel( String label ){
        debugLabel = label;
    }
    
    public String getDebugLabel(){
        return debugLabel;
    }

    public void setChoiceModelLabel( String label ){
        choiceModelLabel = label;
    }
    
    public String getChoiceModelLabel(){
        return choiceModelLabel;
    }

    public void setDecisionMakerLabel( String label ){
        decisionMakerLabel = label;
    }
    
    public String getDecisionMakerLabel(){
        return decisionMakerLabel;
    }

}
