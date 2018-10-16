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

import javax.resource.ResourceException;
import javax.resource.cci.*;

/**
 * Implementation of the Interaction interface.
 * @author Laurent Cohen
 */
public class JPPFInteraction implements Interaction
{
	/**
	 * The connection associated with this interaction
	 */
	private JPPFConnectionImpl conn;

	/**
	 * Intialize this interaction with a specified connection.
	 * @param conn a <code>Connection</code> instance.
	 */
	public JPPFInteraction(JPPFConnectionImpl conn)
	{
		this.conn = conn;
	}

	/**
	 * 
	 * @see javax.resource.cci.Interaction#clearWarnings()
	 */
	public void clearWarnings()
	{
	}

	/**
	 * 
	 * @see javax.resource.cci.Interaction#close()
	 */
	public void close()
	{
	}

	/**
	 * This method does nothing. 
	 * @param ispec not used.
	 * @param input not used.
	 * @return null.
	 * @throws ResourceException .
	 * @see javax.resource.cci.Interaction#execute(javax.resource.cci.InteractionSpec, javax.resource.cci.Record)
	 */
	public Record execute(InteractionSpec ispec, Record input) throws ResourceException
	{
		return null;
	}

	/**
	 * This method does nothing.
	 * @param ispec not used.
	 * @param input not used.
	 * @param output not used.
	 * @return false.
	 * @throws ResourceException .
	 * @see javax.resource.cci.Interaction#execute(javax.resource.cci.InteractionSpec, javax.resource.cci.Record, javax.resource.cci.Record)
	 */
	public boolean execute(InteractionSpec ispec, Record input, Record output) throws ResourceException
	{
		return false;
	}

	/**
	 * Get the connection.
	 * @return a <code>Connection</code> instance.
	 * @see javax.resource.cci.Interaction#getConnection()
	 */
	public Connection getConnection()
	{
		return conn;
	}

	/**
	 * This method does nothing. 
	 * @return null;
	 * @see javax.resource.cci.Interaction#getWarnings()
	 */
	public ResourceWarning getWarnings()
	{
		return null;
	}
}
