/*
 * JPPF.
 * Copyright (C) 2005-2010 JPPF Team.
 * http://www.jppf.org
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.jppf.server.nio;

import java.nio.ByteBuffer;

/**
 * Instances of this class are wrappers for the data to send to or receive from nodes.
 * @author Laurent Cohen
 */
public class NioMessage
{
	/**
	 * Total length of the message to read.
	 */
	public int length = 0;
	/**
	 * Buffer containg the message's data. 
	 */
	public ByteBuffer buffer = null;
	/**
	 * Determines whether the buffer length has already been sent.
	 */
	public boolean lengthWritten = false;

	/**
	 * Get a string representation of this message.
	 * @return a string representing this <code>NioMessage</code> instance.
	 * @see java.lang.Object#toString()
	 */
	public String toString()
	{
		StringBuilder sb = new StringBuilder("NioMessage [length = ").append(length).append(", lengthWritten = ").append(lengthWritten);
		return sb.append(", buffer = ").append(buffer).append("]").toString();
	}
}
