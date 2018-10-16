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
package com.pb.common.graph;

import java.util.ArrayList;

public class XYGraphData extends GraphData {

    protected String xLabelName;
    protected String yLabelName;

    protected ArrayList data = new ArrayList();

    public XYGraphData() {
    }

    public String getxLabelName() {
        return xLabelName;
    }

    public void setxLabelName(String xLabelName) {
        this.xLabelName = xLabelName;
    }

    public String getyLabelName() {
        return yLabelName;
    }

    public void setyLabelName(String yLabelName) {
        this.yLabelName = yLabelName;
    }

    public void addDataPoint(DataPoint dp) {
        data.add( dp );
    }

    public DataPoint[] getDataPoints() {
        return (DataPoint[]) data.toArray();
    }

}
