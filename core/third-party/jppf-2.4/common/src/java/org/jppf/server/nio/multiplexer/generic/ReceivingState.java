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

package org.jppf.server.nio.multiplexer.generic;

import static org.jppf.server.nio.multiplexer.generic.MultiplexerTransition.*;

import java.nio.ByteBuffer;

import org.jppf.server.nio.ChannelWrapper;
import org.slf4j.*;

/**
 * State of receiving data on a channel.
 * When data is received, it is forwarded to the linked channel, so that it can be
 * sent to the other side of the multiplexer connection.
 * @author Laurent Cohen
 */
public class ReceivingState extends MultiplexerServerState
{
	/**
	 * Logger for this class.
	 */
	private static Logger log = LoggerFactory.getLogger(ReceivingState.class);
	/**
	 * Determines whether DEBUG logging level is enabled.
	 */
	private static boolean debugEnabled = log.isDebugEnabled();

	/**
	 * Initialize this state.
	 * @param server the server that handles this state.
	 */
	public ReceivingState(MultiplexerNioServer server)
	{
		super(server);
	}

	/**
	 * {@inheritDoc}
	 */
	public MultiplexerTransition performTransition(ChannelWrapper<?> wrapper) throws Exception
	{
		MultiplexerContext context = (MultiplexerContext) wrapper.getContext();
		if (debugEnabled) log.debug("exec() for " + wrapper);
		ByteBuffer message = context.readMultiplexerMessage(wrapper);
		if (message != null)
		{
			if (debugEnabled) log.debug("read message for " + wrapper + " done");
			ChannelWrapper linkedKey = context.getLinkedKey();
			MultiplexerContext linkedContext = (MultiplexerContext) linkedKey.getContext();
			linkedContext.addPendingMessage(new ByteBufferWrapper(message, context.newReadMessageCount()));
			if (!MultiplexerState.SENDING.equals(linkedContext.getState()))
				server.getTransitionManager().transitionChannel(linkedKey, MultiplexerTransition.TO_SENDING);
			if (!context.isEof()) return TO_SENDING_OR_RECEIVING;
		}
		if (context.isEof())
		{
			context.setEof(false);
			return TO_IDLE;
		}
		return TO_RECEIVING;
	}
}
