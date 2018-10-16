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
package com.pb.common.daf;

import java.io.Serializable;

/**
 * Used to signal the end of message during serialziation.
 *
 * @author    Tim Heier
 * @version   1.0, 4/18/2002
 */
public class EndOfMessage implements Serializable {

    private static EndOfMessage instance = new EndOfMessage();

    public EndOfMessage() {
    }

    public static EndOfMessage getInstance() {
        return instance;
    }

    public String toString() {
        return "EndOfMessage";
    }

}
