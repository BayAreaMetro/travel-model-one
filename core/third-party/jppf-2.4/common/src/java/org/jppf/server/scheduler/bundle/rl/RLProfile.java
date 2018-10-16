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

package org.jppf.server.scheduler.bundle.rl;

import org.jppf.server.scheduler.bundle.LoadBalancingProfile;
import org.jppf.server.scheduler.bundle.autotuned.AbstractAutoTuneProfile;
import org.jppf.utils.*;

/**
 * Parameters profile for a proportional bundler. 
 * @author Laurent Cohen
 */
public class RLProfile extends AbstractAutoTuneProfile
{
	/**
	 * The maximum szie of the performance samples cache.
	 */
	private int performanceCacheSize = 2000;
	/**
	 * Variation of the mean execution time that triggers a change in bundle size.
	 */
	private double performanceVariationThreshold = 0.05d;
	/**
	 * The absolute value of the maximum increase of the the bundle size.
	 */
	private int maxActionRange = 50;

	/**
	 * Initialize this profile with default parameters.
	 */
	public RLProfile()
	{
	}

	/**
	 * Initialize this profile with values read from the configuration file.
	 * @param profileName name of the profile in the configuration file.
	 */
	public RLProfile(String profileName)
	{
		String prefix = "strategy." + profileName + ".";
		TypedProperties props = JPPFConfiguration.getProperties();
		performanceCacheSize = props.getInt(prefix + "performanceCacheSize", 2000);
		performanceVariationThreshold = props.getDouble(prefix + "performanceVariationThreshold", 0.05);
		maxActionRange = props.getInt(prefix + "maxActionRange", 50);
	}

	/**
	 * Initialize this profile with values read from the specified configuration.
	 * @param config contains a mapping of the profile parameters to their value.
	 */
	public RLProfile(TypedProperties config)
	{
		performanceCacheSize = config.getInt("performanceCacheSize", 2000);
		performanceVariationThreshold = config.getDouble("performanceVariationThreshold", 0.05);
		maxActionRange = config.getInt("maxActionRange", 50);
	}

	/**
	 * Make a copy of this profile.
	 * @return a new <code>AutoTuneProfile</code> instance.
	 * @see org.jppf.server.scheduler.bundle.LoadBalancingProfile#copy()
	 */
	public LoadBalancingProfile copy()
	{
		RLProfile other = new RLProfile();
		other.setPerformanceCacheSize(performanceCacheSize);
		other.setPerformanceVariationThreshold(performanceVariationThreshold);
		other.setMaxActionRange(maxActionRange);
		return other;
	}

	/**
	 * Get the maximum size of the performance samples cache.
	 * @return the cache size as an int.
	 */
	public int getPerformanceCacheSize()
	{
		return performanceCacheSize;
	}

	/**
	 * Set the maximum size of the performance samples cache.
	 * @param performanceCacheSize - the cache size as an int.
	 */
	public void setPerformanceCacheSize(int performanceCacheSize)
	{
		this.performanceCacheSize = performanceCacheSize;
	}

	/**
	 * Get the variation of the mean execution time that triggers a change in bundle size.
	 * @return the variation as a double value.
	 */
	public double getPerformanceVariationThreshold()
	{
		return performanceVariationThreshold;
	}

	/**
	 * Get the variation of the mean execution time that triggers a change in bundle size.
	 * @param performanceVariationThreshold - the variation as a double value.
	 */
	public void setPerformanceVariationThreshold(double performanceVariationThreshold)
	{
		this.performanceVariationThreshold = performanceVariationThreshold;
	}

	/**
	 * Get the absolute value of the maximum increase of the the bundle size.
	 * @return the value as an int.
	 */
	public int getMaxActionRange()
	{
		return maxActionRange;
	}

	/**
	 * Get the absolute value of the maximum increase of the the bundle size.
	 * @param maxActionRange - the value as an int.
	 */
	public void setMaxActionRange(int maxActionRange)
	{
		this.maxActionRange = maxActionRange;
	}
}
