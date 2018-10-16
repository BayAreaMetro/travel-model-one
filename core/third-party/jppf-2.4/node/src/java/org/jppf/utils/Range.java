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


/**
 * Instances of this class represent a range of values.
 * @param <T> the type of values handled by this object.
 */
public class Range<T extends Comparable<T>>
{
	/**
	 * The lower bound.
	 */
	private T lower;
	/**
	 * The upper bound.
	 */
	private T upper;

	/**
	 * Initialize this range with the specified single value used as both lower and upper bounds.
	 * @param value the value to use for the bounds.
	 */
	public Range(T value)
	{
		this(value, value);
	}

	/**
	 * Initialize this range with the specified lower and upper bounds.
	 * @param lower the lower bound.
	 * @param upper the upper bound.
	 */
	public Range(T lower, T upper)
	{
		this.lower = lower;
		this.upper = upper;
	}

	/**
	 * Determine if the specified value is included in this range.
	 * @param value the value to check.
	 * @return true if the value is in range, false otherwise.
	 */
	public boolean isValueInRange(T value)
	{
		return (value.compareTo(lower) >= 0) && (value.compareTo(upper) <= 0); 
	}

	/**
	 * {@inheritDoc}
	 */
	public String toString()
	{
		StringBuilder sb = new StringBuilder();
		sb.append(lower);
		if (!lower.equals(upper)) sb.append("-").append(upper);
		return sb.toString();
	}

	/**
	 * Get the lower bound.
	 * @return the lower bound.
	 */
	public T getLower()
	{
		return lower;
	}

	/**
	 * Get the upper bound.
	 * @return the upper bound.
	 */
	public T getUpper()
	{
		return upper;
	}

	/**
	 * Determine whether this range and the specified one have at least one value in common.
	 * @param other the range to check against.
	 * @return true if and only if part of <code>other</code> overlaps this range.
	 */
	public boolean intersects(Range<T> other)
	{
		if (other == null) return false;
		return other.isValueInRange(lower) || other.isValueInRange(upper) || includes(other);
	}

	/**
	 * Determine whether this range is a superset of the specified other.<br/>
	 * More formally, this method  returns true if <code>other.lower &gt;= this.lower</code> and <code>other.upper &lt;= this.upper</code>.
	 * @param other the range to check against.
	 * @return true if and only if this range includes all the values from <code>other</code>.
	 */
	public boolean includes(Range<T> other)
	{
		if (other == null) return false;
		return (other.getLower().compareTo(lower) >= 0) && (other.getUpper().compareTo(upper) <= 0);
	}

	/**
	 * Construct a <code>Range</code> that is made of all values between the lowest lower bound and the highest upper bound
	 * of this range and the other specified range. This works even if the ranges are completely disjointed
	 * (i.e if <code>this.{@link #intersects(Range) intersects(other)} == false</code>)<br/>
	 * This is equivalent to building a range object with its lower bound equal to <code>min(this.lower, other.lower)</code>
	 * and its upper bound equal to <code>max(this.upper, other.upper)</code>
	 * @param other the range to merge with.
	 * @return a new <code>Range</code> object that encompasses all values between the lowest lower bound and the highest upper bound,
	 * or a copy of this range if the other is null.
	 */
	public Range<T> merge(Range<T> other)
	{
		if (other == null) return new Range<T>(getLower(), getUpper());
		T minLower = lower.compareTo(other.getLower()) <= 0 ? lower : other.getLower();
		T maxUpper = upper.compareTo(other.getUpper()) >= 0 ? upper : other.getUpper();
		return new Range<T>(minLower, maxUpper);
	}

	/**
	 * Construct a <code>Range</code> that represents the intersection of this range and the other specified one.<br/>
	 * This is equivalent to building a range object with its lower bound equal to <code>max(this.lower, other.lower)</code>
	 * and its upper bound equal to <code>min(this.upper, other.upper)</code>
	 * @param other the range to check against.
	 * @return a Range object representing the intersection of 2 ranges, or null if <code>other</code> is null or the ranges are disjointed
	 * (i.e if <code>this.{@link #intersects(Range) intersects(other)} == false</code>).
	 */
	public Range<T> intersection(Range<T> other)
	{
		if ((other == null) || !intersects(other)) return null;
		T maxLower = lower.compareTo(other.getLower()) >= 0 ? lower : other.getLower();
		T minUpper = upper.compareTo(other.getUpper()) <= 0 ? upper : other.getUpper();
		return new Range<T>(maxLower, minUpper);
	}
}