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
package org.jppf.utils;

import java.io.Serializable;

/**
 * Utility class holding a pair of references to two objects.
 * @param <U> the type of the first element in the pair.
 * @param <V> the type of the second element in the pair.
 * @author Laurent Cohen
 */
public class Pair<U, V> implements Serializable
{
	/**
	 * Explicit serialVersionUID.
	 */
	private static final long serialVersionUID = 1L;
	/**
	 * The first object of this pair.
	 */
	private U first = null;
	/**
	 * The second object of this pair.
	 */
	private V second = null;
	
	/**
	 * Initialize this pair with two values.
	 * @param first the first value of the new pair.
	 * @param second the second value of the new pair.
	 */
	public Pair(U first, V second)
	{
		this.first = first;
		this.second = second;
	}

	/**
	 * Get the first value of this pair.
	 * @return an object of type U.
	 */
	public U first()
	{
		return first;
	}

	/**
	 * Get the second value of this pair.
	 * @return an object of type V.
	 */
	public V second()
	{
		return second;
	}

	/**
	 * Get the hashcode for this object.
	 * @return the hashcode as an int value.
	 * @see java.lang.Object#hashCode()
	 */
	public int hashCode()
	{
		final int prime = 31;
		int result = 1;
		result = prime * result + ((first == null) ? 0 : first.hashCode());
		result = prime * result + ((second == null) ? 0 : second.hashCode());
		return result;
	}

	/**
	 * Indicates whether some other object is "equal to" this one.
	 * @param obj the reference object with which to compare.
	 * @return <code>true</code> if this object is the same as the obj.
	 * @see java.lang.Object#equals(java.lang.Object)
	 */
	public boolean equals(Object obj)
	{
		if (this == obj) return true;
		if (obj == null) return false;
		if (getClass() != obj.getClass()) return false;
		Pair other = (Pair) obj;
		if (first == null)
		{
			if (other.first != null) return false;
		}
		else if (!first.equals(other.first)) return false;
		if (second == null)
		{
			if (other.second != null) return false;
		}
		else if (!second.equals(other.second)) return false;
		return true;
	}
}
