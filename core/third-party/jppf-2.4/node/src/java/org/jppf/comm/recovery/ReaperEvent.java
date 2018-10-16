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

package org.jppf.comm.recovery;

import java.util.EventObject;

/**
 * Event emitted when a connection failure is detected.
 * @author Laurent Cohen
 */
public class ReaperEvent extends EventObject
{
	/**
	 * Initialize this event with the specified connection to a remote peer.
	 * @param connection the source of this event.
	 */
	public ReaperEvent(ServerConnection connection)
	{
		super(connection);
	}

	/**
	 * Get the connection for which this event is emitted.
	 * @return a {@link ServerConnection} instance.
	 */
	public ServerConnection getConnection()
	{
		return (ServerConnection) getSource();
	}
}
