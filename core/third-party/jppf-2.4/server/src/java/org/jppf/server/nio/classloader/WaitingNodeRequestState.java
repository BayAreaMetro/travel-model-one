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

package org.jppf.server.nio.classloader;

import static org.jppf.server.nio.classloader.ClassTransition.*;

import java.util.List;

import org.jppf.classloader.JPPFResourceWrapper;
import org.jppf.server.nio.ChannelWrapper;
import org.jppf.utils.*;
import org.slf4j.*;

/**
 * This class represents the state of waiting for a request from a node.
 * @author Laurent Cohen
 */
class WaitingNodeRequestState extends ClassServerState
{
	/**
	 * Logger for this class.
	 */
	private static Logger log = LoggerFactory.getLogger(WaitingNodeRequestState.class);
	/**
	 * Determines whether DEBUG logging level is enabled.
	 */
	private static boolean debugEnabled = log.isDebugEnabled();

	/**
	 * Initialize this state with a specified NioServer.
	 * @param server the JPPFNIOServer this state relates to.
	 */
	public WaitingNodeRequestState(ClassNioServer server)
	{
		super(server);
	}

	/**
	 * Execute the action associated with this channel state.
	 * @param wrapper the selection key corresponding to the channel and selector for this state.
	 * @return a state transition as an <code>NioTransition</code> instance.
	 * @throws Exception if an error occurs while transitioning to another state.
	 * @see org.jppf.server.nio.NioState#performTransition(java.nio.channels.SelectionKey)
	 */
	public ClassTransition performTransition(ChannelWrapper<?> wrapper) throws Exception
	{
		ClassContext context = (ClassContext) wrapper.getContext();
		if (context.readMessage(wrapper))
		{
			if (debugEnabled) log.debug("read resource request from node: " + wrapper);
			JPPFResourceWrapper resource = context.deserializeResource();
			TraversalList<String> uuidPath = resource.getUuidPath();
			boolean dynamic = resource.isDynamic();
			String name = resource.getName();
			byte[] b = null;
			String uuid = (uuidPath.size() > 0) ? uuidPath.getCurrentElement() : null; 
			ByteTransitionPair p = processNonDynamic(wrapper, resource);
			if (p.second() != null) return p.second();
			b = p.first();
			if ((b == null) && dynamic)
			{
				p = processDynamic(wrapper, resource);
				if (p.second() != null) return p.second();
				//b = p.first();
			}
			if (debugEnabled) log.debug("resource [" + name + "] not found for node: " + wrapper);
			resource.setDefinition(null);
			context.serializeResource(wrapper);
			return TO_SENDING_NODE_RESPONSE;
		}
		return TO_WAITING_NODE_REQUEST;
	}

	/**
	 * Process a request to the driver's resource provider.
	 * @param wrapper encapsulates the context and channel.
	 * @param resource the resource request description
	 * @return a pair of an array of bytes and the resulting state transition.
	 * @throws Exception if any error occurs.
	 */
	private ByteTransitionPair processNonDynamic(ChannelWrapper<?> wrapper, JPPFResourceWrapper resource) throws Exception
	{
		byte[] b = null;
		ClassTransition t = null;
		String name = resource.getName();
		ClassContext context = (ClassContext) wrapper.getContext();
		TraversalList<String> uuidPath = resource.getUuidPath();

		String uuid = (uuidPath.size() > 0) ? uuidPath.getCurrentElement() : null; 
		if (((uuid == null) || uuid.equals(driver.getUuid())) && (resource.getCallable() == null))
		{
			if (resource.getData("multiple") != null)
			{
				List<byte[]> list = server.getResourceProvider().getMultipleResourcesAsBytes(name, null);
				if (list != null)
				{
					resource.setData("resource_list", list);
					context.serializeResource(wrapper);
					t = TO_SENDING_NODE_RESPONSE;
				}
				if (debugEnabled) log.debug("multiple resources " + (list != null ? "" : "not ") + "found [" + name + "] in driver's classpath for node: " + wrapper);
			}
			else
			{
				if ((uuid == null) && !resource.isDynamic()) uuid = driver.getUuid();
				if (uuid != null) b = server.getCacheContent(uuid, name);
				boolean alreadyInCache = (b != null);
				if (debugEnabled) log.debug("resource " + (alreadyInCache ? "" : "not ") + "found [" + name + "] in cache for node: " + wrapper);
				if (!alreadyInCache) b = server.getResourceProvider().getResourceAsBytes(name);
				if ((b != null) || !resource.isDynamic())
				{
					if (debugEnabled) log.debug("resource " + (b == null ? "not " : "") + "found [" + name + "] in the driver's classpath for node: " + wrapper);
					if ((b != null) && !alreadyInCache) server.setCacheContent(driver.getUuid(), name, b);
					resource.setDefinition(b);
					context.serializeResource(wrapper);
					t = TO_SENDING_NODE_RESPONSE;
				}
			}
		}
		return new ByteTransitionPair(b, t);
	}

	/**
	 * Process a request to the client's resource provider.
	 * @param wrapper encapsulates the context and channel.
	 * @param resource - the resource request description
	 * @return a pair of an array of bytes and the resulting state transition.
	 * @throws Exception if any error occurs.
	 */
	private ByteTransitionPair processDynamic(ChannelWrapper<?> wrapper, JPPFResourceWrapper resource) throws Exception
	{
		byte[] b = null;
		ClassTransition t = null;
		String name = resource.getName();
		TraversalList<String> uuidPath = resource.getUuidPath();
		ClassContext context = (ClassContext) wrapper.getContext();

		if (resource.getCallable() == null) b = server.getCacheContent(uuidPath.getFirst(), name);
		if (b != null)
		{
			if (debugEnabled) log.debug("found cached resource [" + name + "] for node: " + wrapper);
			resource.setDefinition(b);
			context.serializeResource(wrapper);
			t = TO_SENDING_NODE_RESPONSE;
		}
		else
		{
			uuidPath.decPosition();
			String uuid = uuidPath.getCurrentElement();
			ChannelWrapper provider = findProviderConnection(uuid);
			if (provider != null)
			{
				synchronized(provider)
				{
					if (debugEnabled) log.debug("request resource [" + name + "] from client: " + provider + " for node: " + wrapper);
					ClassContext providerContext = (ClassContext) provider.getContext();
					providerContext.addRequest(wrapper);
					/*
					if (ClassState.IDLE_PROVIDER.equals(providerContext.getState()))
					{
						server.getTransitionManager().transitionChannel(provider, TO_SENDING_PROVIDER_REQUEST);
						if (debugEnabled) log.debug("node " + wrapper + " transitioned provider " + provider);
					}
					*/
					t = TO_IDLE_NODE;
				}
			}
		}
		return new ByteTransitionPair(b, t);
	}

	/**
	 * Find a provider connection for the specified provider uuid.
	 * @param uuid the uuid for which to find a conenction.
	 * @return a <code>SelectableChannel</code> instance.
	 * @throws Exception if an error occurs while searching for a connection.
	 */
	private ChannelWrapper findProviderConnection(String uuid) throws Exception
	{
		ChannelWrapper result = null;
		List<ChannelWrapper<?>> connections = server.providerConnections.get(uuid);
		int minRequests = Integer.MAX_VALUE;
		for (ChannelWrapper channel: connections)
		{
			ClassContext ctx = (ClassContext) channel.getContext();
			int size = ctx.getNbPendingRequests();
			if (size < minRequests)
			{
				minRequests = size;
				result = channel;
			}
		}
		return result;
	}

	/**
	 * A pair of array of bytes and class transition.
	 */
	private static class ByteTransitionPair extends Pair<byte[], ClassTransition>
	{
		/**
		 * Initialize this pair with the specified array of bytes and class transition.
		 * @param first - an array of bytes.
		 * @param second - a class transition.
		 */
		public ByteTransitionPair(byte[] first, ClassTransition second)
		{
			super(first, second);
		}
	}
}
