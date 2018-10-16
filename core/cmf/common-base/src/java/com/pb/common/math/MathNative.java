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
package com.pb.common.math;

/**
 * Declares native methods to use native math intrinsic methods
 * instead of default compiled math methods in jdk.
 *
 * @author    Jim Hicks
 * @version   1.0, 1/14/2004
 */
public class MathNative {

    // Load shared library containing native methods
	static {
		System.loadLibrary ("msvcMath");
	}

    public MathNative() {
    }

	public static native double exp ( double arg );
	public static native double log ( double arg );

    public static native void expArray ( double[] arg, double[] result );
}
