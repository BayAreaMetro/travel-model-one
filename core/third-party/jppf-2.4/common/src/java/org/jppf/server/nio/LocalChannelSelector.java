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

import java.util.concurrent.locks.ReentrantLock;

import org.jppf.utils.ThreadSynchronization;

/**
 * Instances of this class act as a NIO selector for local (in-VM) channels.
 * @author Laurent Cohen
 */
public class LocalChannelSelector extends ThreadSynchronization implements ChannelSelector
{
	/**
	 * The channel polled by this selector.
	 */
	private ChannelWrapper<?> channel = null;
	/**
	 * The server that handles the channel.
	 */
	private NioServer<?, ?> server = null;
	/**
	 * 
	 */
	private ReentrantLock lock = new ReentrantLock(); 

	/**
	 * Initialize this selector with the specified channel.
	 * @param channel the channel polled by this selector.
	 * @param server the server that handles the channel.
	 */
	public LocalChannelSelector(ChannelWrapper<?> channel, NioServer<?, ?> server)
	{
		this.channel = channel;
		this.server = server;
	}

	/**
	 * {@inheritDoc}
	 */
	public boolean select()
	{
		return select(0);
	}

	/**
	 * {@inheritDoc}
	 */
	public boolean select(long timeout)
	{
		if (timeout < 0L) throw new IllegalArgumentException("timeout must be >= 0");
		long start = System.currentTimeMillis();
		long elapsed = 0;
		boolean selected = channelSelected();
		while (((timeout == 0L) || (elapsed < timeout)) && !selected)
		{
			goToSleep(timeout == 0L ? 0 : timeout - elapsed);
			elapsed = System.currentTimeMillis() - start;
			selected = channelSelected();
		}
		return selected;
	}

	/**
	 * {@inheritDoc}
	 */
	public boolean selectNow()
	{
		return (channel.getKeyOps() & channel.getReadyOps()) != 0;
	}

	/**
	 * {@inheritDoc}
	 */
	public ChannelWrapper<?> getChannel()
	{
		return channel;
	}

	/**
	 * Determine whether the channel should be set as selected.
	 * @return tre if the channel is selected, false otherwisze.
	 */
	private boolean channelSelected()
	{
		synchronized(channel)
		{
			return (channel.getKeyOps() & channel.getReadyOps()) != 0;
		}
	}
}
