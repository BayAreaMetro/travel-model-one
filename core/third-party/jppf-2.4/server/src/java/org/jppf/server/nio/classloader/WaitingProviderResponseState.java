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

import java.io.IOException;

import org.jppf.classloader.JPPFResourceWrapper;
import org.jppf.server.nio.ChannelWrapper;
import org.slf4j.*;

/**
 * This class represents the state of waiting for the response from a provider.
 * @author Laurent Cohen
 */
class WaitingProviderResponseState extends ClassServerState
{
	/**
	 * Logger for this class.
	 */
	private static Logger log = LoggerFactory.getLogger(WaitingProviderResponseState.class);
	/**
	 * Determines whether DEBUG logging level is enabled.
	 */
	private static boolean debugEnabled = log.isDebugEnabled();

	/**
	 * Initialize this state with a specified NioServer.
	 * @param server the NioServer this state relates to.
	 */
	public WaitingProviderResponseState(ClassNioServer server)
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
		boolean messageRead = false;
		try
		{
			messageRead = context.readMessage(wrapper);
		}
		catch(IOException e)
		{
			if (debugEnabled) log.debug("an exception occurred while reading response from provider: " + wrapper);
			server.removeProviderConnection(context.getUuid(), wrapper);
			ChannelWrapper currentRequest = context.getCurrentRequest();
			if ((currentRequest != null) || !context.getPendingRequests().isEmpty())
			{
				if (debugEnabled) log.debug("provider: " + wrapper + " sending null response for disconnected provider");
				if (currentRequest != null)
				{
					context.setCurrentRequest(null);
					sendNullResponse(currentRequest);
				}
				for (int i=0; i<context.getPendingRequests().size(); i++)
					sendNullResponse(context.getPendingRequests().remove(0));
			}
			throw e;
		}
		if (messageRead)
		{
			if (debugEnabled) log.debug("read response from provider: " + wrapper + " complete, sending to node " + context.getCurrentRequest() + 
				", resource: " + context.getResource().getName());
			JPPFResourceWrapper resource = context.deserializeResource();
			// putting the definition in cache
			if ((resource.getDefinition() != null) && (resource.getCallable() == null))
				server.setCacheContent(context.getUuid(), resource.getName(), resource.getDefinition());
			// fowarding it to channel that requested
			ChannelWrapper destinationKey = context.getCurrentRequest();
			ClassContext destinationContext = (ClassContext) destinationKey.getContext();
			resource.setState(JPPFResourceWrapper.State.NODE_RESPONSE);
			//destinationContext.setMessage(null);
			destinationContext.setResource(resource);
			destinationContext.serializeResource(destinationKey);
			server.getTransitionManager().transitionChannel(destinationKey, TO_SENDING_NODE_RESPONSE);
			//context.setMessage(null);
			context.setCurrentRequest(null);
			return TO_SENDING_PROVIDER_REQUEST;
		}
		return TO_WAITING_PROVIDER_RESPONSE;
	}
}
