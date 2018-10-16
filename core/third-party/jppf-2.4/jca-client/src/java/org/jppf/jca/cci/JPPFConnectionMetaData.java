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

package org.jppf.jca.cci;

import javax.resource.cci.ConnectionMetaData;

/**
 * Metadata for a JPPFConnection.
 * @author Laurent Cohen
 */
public class JPPFConnectionMetaData implements ConnectionMetaData
{
	/**
	 * Name of the user fo a conenction
	 */
	private String userName;

	/**
	 * Initialize this metadata with a user name.
	 * @param userName the name as a string.
	 */
	public JPPFConnectionMetaData(final String userName)
	{
		this.userName = userName;
	}

	/**
	 * name.Get the product name. 
	 * @return the name as a string.
	 * @see javax.resource.cci.ConnectionMetaData#getEISProductName()
	 */
	public String getEISProductName()
	{
		return "JPPF";
	}

	/**
	 * Get the product version.
	 * @return the version as a string.
	 * @see javax.resource.cci.ConnectionMetaData#getEISProductVersion()
	 */
	public String getEISProductVersion()
	{
		return "1.0 beta";
	}

	/**
	 * Get the user name.
	 * @return the name as a string.
	 * @see javax.resource.cci.ConnectionMetaData#getUserName()
	 */
	public String getUserName()
	{
		return userName;
	}
}
