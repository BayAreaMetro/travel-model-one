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

/**
 * Represents the model header information in the control file.
 *
 * @author    Tim Heier
 * @version   1.0, 2/28/2003
 */
public class ModelHeader implements Serializable {

    public float number;
    public String description;
    public String dmu;
    public int numberOfAlts;
    public int numberOfLevels;
    public boolean isAlternativesInFile;

    public ModelHeader(float number, String description, String dmu, int numberOfAlts, int numberOfLevels, boolean isAlternativesInFile) {
        this.number = number;
        this.description = description;
        this.dmu = dmu.trim();
        this.numberOfAlts = numberOfAlts;
        this.numberOfLevels = numberOfLevels;
        this.isAlternativesInFile = isAlternativesInFile;
    }

    public String toString() {
        return "number="+number+", description="+description+
                ", dmu="+dmu+", numberOfAlts="+numberOfAlts+", numberOfLevels="+numberOfLevels+
                ", isAlternativesInFile="+isAlternativesInFile;
    }
}
