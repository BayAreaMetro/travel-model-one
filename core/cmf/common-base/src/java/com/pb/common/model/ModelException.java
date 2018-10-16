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
package com.pb.common.model;

/**
 * Defines an exception used in the model package with messages.
 *
 * @author    Joel Freedman
 * @version   1.0, 2/02/2003
 */
public class ModelException extends RuntimeException {

    public static final String INVALID_UTILITY = "Invalid utility value.";
    public static final String INVALID_EXPUTILITY = "Invalid exponentiated utility value.";
    public static final String INVALID_ALTERNATIVE = "Invalid alternative.";
    public static final String NO_ALTERNATIVES_AVAILABLE = "No alternatives available.";
    public ModelException() {
        super();
    }

    public ModelException(String message) {
        super(message);
    }

    public ModelException(Throwable t) {
        super(t);
    }

    public ModelException(Throwable t, String message) {
        super(message, t);
    }

}
