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

import static java.nio.channels.SelectionKey.*;

import java.util.concurrent.atomic.AtomicLong;

import org.jppf.utils.ThreadSynchronization;

/**
 * Wraps a communication channel, no matter what the channel is.
 * @param <S> the type of wrapped channel.
 * @author Laurent Cohen
 */
public abstract class AbstractChannelWrapper<S> extends ThreadSynchronization implements ChannelWrapper<S>
{
	/**
	 * Count of instances of this class.
	 */
	private static AtomicLong instanceCount = new AtomicLong(0);
	/**
	 * Id of this instance.
	 */
	protected final long id = instanceCount.incrementAndGet();
	/**
	 * The channel to wrap.
	 */
	protected S channel;
	/**
	 * The selctor for this channel.
	 */
	protected ChannelSelector selector = null;
	
	/**
	 * Initialize this channel wrapper with the specified channel.
	 * @param channel the channel to wrap.
	 */
	public AbstractChannelWrapper(S channel)
	{
		this.channel = channel;
	}

	/**
	 * {@inheritDoc}
	 */
	public S getChannel()
	{
		return channel;
	}

	/**
	 * {@inheritDoc}
	 * @see org.jppf.server.nio.ChannelWrapper#close()
	 */
	public void close() throws Exception
	{
	}

	/**
	 * {@inheritDoc}
	 */
	public abstract NioContext getContext();

	/**
	 * {@inheritDoc}
	 */
	public boolean isOpen()
	{
		return true;
	}

	/**
	 * {@inheritDoc}
	 */
	public int hashCode()
	{
		return ((channel == null) ? 0 : channel.hashCode());
	}

	/**
	 * Determine whether an other object is equal to this one.
	 * @param obj the object to compare with.
	 * @return true if this object is equal to the other one, false otherwise.
	 * @see java.lang.Object#equals(java.lang.Object)
	 */
	public boolean equals(Object obj)
	{
		if (this == obj) return true;
		if (obj == null) return false;
		if (getClass() != obj.getClass()) return false;
		AbstractChannelWrapper other = (AbstractChannelWrapper) obj;
		if (channel == null) return (other.channel == null);
		return channel.equals(other.channel);
	}

	/**
	 * {@inheritDoc}
	 */
	public String toString()
	{
		//return getClass().getSimpleName() + "[id=" + getId() + ", readyOps=" + getReadyOps() + ", keyOps=" + getKeyOps() + "]";
		StringBuilder sb = new StringBuilder();
		sb.append(getClass().getSimpleName());
		sb.append("[");
		sb.append(getId());
		sb.append(",").append(" readyOps=").append(getReadyOps());
		sb.append(",").append(" keyOps=").append(getKeyOps());
		//sb.append(",").append(" state=").append(getContext().getState());
		sb.append("]");
		return sb.toString();
	}

	/**
	 * {@inheritDoc}
	 * @see org.jppf.server.nio.ChannelWrapper#getKeyOps()
	 */
	public int getKeyOps()
	{
		return 0;
	}

	/**
	 * {@inheritDoc}
	 * @see org.jppf.server.nio.ChannelWrapper#setKeyOps(int)
	 */
	public void setKeyOps(int keyOps)
	{
	}

	/**
	 * Get the operations available for this channel.
	 * @return the operations as an int value.
	 */
	public abstract int getReadyOps();

	/**
	 * {@inheritDoc}
	 * @see org.jppf.server.nio.ChannelWrapper#isReadable()
	 */
	public boolean isReadable()
	{
		return (getReadyOps() & OP_READ) != 0;
	}

	/**
	 * {@inheritDoc}
	 * @see org.jppf.server.nio.ChannelWrapper#isWritable()
	 */
	public boolean isWritable()
	{
		return (getReadyOps() & OP_WRITE) != 0;
	}

	/**
	 * {@inheritDoc}
	 * @see org.jppf.server.nio.ChannelWrapper#isAcceptable()
	 */
	public boolean isAcceptable()
	{
		return (getReadyOps() & OP_ACCEPT) != 0;
	}

	/**
	 * {@inheritDoc}
	 * @see org.jppf.server.nio.ChannelWrapper#isConnectable()
	 */
	public boolean isConnectable()
	{
		return (getReadyOps() & OP_CONNECT) != 0;
	}

	/**
	 * Default implementation of this method returns null.
	 * @return by default this method returns null.
	 * @see org.jppf.server.nio.ChannelWrapper#getSelector()
	 */
	public ChannelSelector getSelector()
	{
		return selector;
	}

	/**
	 * By default, this method does nothing.
	 * Subclasses should override it ot implement their own selection mechanism.
	 * @param selector the selector associated with this mechanism.
	 * @see org.jppf.server.nio.ChannelWrapper#setSelector(org.jppf.server.nio.ChannelSelector)
	 */
	public void setSelector(ChannelSelector selector)
	{
		this.selector = selector;
	}

	/**
	 * Get a string uniquely identifying this channel.
	 * @return a unique id as a string.
	 */
	public String getId()
	{
		return "id=" + id;
	}
}
